# Copyright 2011 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA

"""Code to do some load testing against a loggerhead instance.

This is basically meant to take a list of actions to take, and run it against a
real host, and see how the results respond.::

    {"parameters": {
         "base_url": "http://localhost:8080",
     },
     "requests": [
        {"thread": "1", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"}
     ],
    }

All threads have a Queue length of 1. When a third request for a given thread
is seen, no more requests are queued until that thread finishes its current
job. So this results in all requests being issued sequentially::

        {"thread": "1", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"}

While this would cause all requests to be sent in parallel:

        {"thread": "1", "relpath": "/changes"},
        {"thread": "2", "relpath": "/changes"},
        {"thread": "3", "relpath": "/changes"},
        {"thread": "4", "relpath": "/changes"}

This should keep 2 threads pipelined with activity, as long as they finish in
approximately the same speed. We'll start the first thread running, and the
second thread, and queue up both with a second request once the first finishes.
When we get to the third request for thread "1", we block on queuing up more
work until the first thread 1 request has finished.
        {"thread": "1", "relpath": "/changes"},
        {"thread": "2", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"},
        {"thread": "2", "relpath": "/changes"},
        {"thread": "1", "relpath": "/changes"},
        {"thread": "2", "relpath": "/changes"}

There is not currently a way to say "run all these requests keeping exactly 2
threads active". Though if you know the load pattern, you could approximate
this.
"""

import threading
import time
import Queue

import simplejson

from bzrlib import (
    errors,
    transport,
    urlutils,
    )

# This code will be doing multi-threaded requests against bzrlib.transport
# code. We want to make sure to load everything ahead of time, so we don't get
# lazy-import failures
_ = transport.get_transport('http://example.com')


class RequestDescription(object):
    """Describes info about a request."""

    def __init__(self, descrip_dict):
        self.thread = descrip_dict.get('thread', '1')
        self.relpath = descrip_dict['relpath']


class RequestWorker(object):
    """Process requests in a worker thread."""

    _timer = time.time

    def __init__(self, identifier, blocking_time=1.0, _queue_size=1):
        self.identifier = identifier
        self.queue = Queue.Queue(_queue_size)
        self.start_time = self.end_time = None
        self.stats = []
        self.blocking_time = blocking_time

    def step_next(self):
        url = self.queue.get(True, self.blocking_time)
        if url == '<noop>':
            # This is usually an indicator that we want to stop, so just skip
            # this one.
            self.queue.task_done()
            return
        self.start_time = self._timer()
        success = self.process(url)
        self.end_time = self._timer()
        self.update_stats(url, success)
        self.queue.task_done()

    def run(self, stop_event):
        while not stop_event.isSet():
            try:
                self.step_next()
            except Queue.Empty:
                pass

    def process(self, url):
        base, path = urlutils.split(url)
        t = transport.get_transport(base)
        try:
            # TODO: We should probably look into using some part of
            #       blocking_timeout to decide when to stop trying to read
            #       content
            content = t.get_bytes(path)
        except (errors.TransportError, errors.NoSuchFile):
            return False
        return True

    def update_stats(self, url, success):
        self.stats.append((url, success, self.end_time - self.start_time))


class ActionScript(object):
    """This tracks the actions that we want to perform."""

    _worker_class = RequestWorker
    _default_base_url = 'http://localhost:8080'
    _default_blocking_timeout = 60.0

    def __init__(self):
        self.base_url = self._default_base_url
        self.blocking_timeout = self._default_blocking_timeout
        self._requests = []
        self._threads = {}
        self.stop_event = threading.Event()

    @classmethod
    def parse(cls, content):
        script = cls()
        json_dict = simplejson.loads(content)
        if 'parameters' not in json_dict:
            raise ValueError('Missing "parameters" section')
        if 'requests' not in json_dict:
            raise ValueError('Missing "requests" section')
        param_dict = json_dict['parameters']
        request_list = json_dict['requests']
        base_url = param_dict.get('base_url', None)
        if base_url is not None:
            script.base_url = base_url
        blocking_timeout = param_dict.get('blocking_timeout', None)
        if blocking_timeout is not None:
            script.blocking_timeout = blocking_timeout
        for request_dict in request_list:
            script.add_request(request_dict)
        return script

    def add_request(self, request_dict):
        request = RequestDescription(request_dict)
        self._requests.append(request)

    def _get_worker(self, thread_id):
        if thread_id in self._threads:
            return self._threads[thread_id][0]
        handler = self._worker_class(thread_id,
                                     blocking_time=self.blocking_timeout/10.0)

        t = threading.Thread(target=handler.run, args=(self.stop_event,),
                             name='Thread-%s' % (thread_id,))
        self._threads[thread_id] = (handler, t)
        t.start()
        return handler

    def finish_queues(self):
        """Wait for all queues of all children to finish."""
        for h, t in self._threads.itervalues():
            h.queue.join()

    def stop_and_join(self):
        """Stop all running workers, and return.

        This will stop even if workers still have work items.
        """
        self.stop_event.set()
        for h, t in self._threads.itervalues():
            # Signal the queue that it should stop blocking, we don't have to
            # wait for the queue to empty, because we may see stop_event before
            # we see the <noop>
            h.queue.put('<noop>')
            # And join the controlling thread
            for i in range(10):
                t.join(self.blocking_timeout / 10.0)
                if not t.isAlive():
                    break

    def _full_url(self, relpath):
        return self.base_url + relpath

    def run(self):
        self.stop_event.clear()
        for request in self._requests:
            full_url = self._full_url(request.relpath)
            worker = self._get_worker(request.thread)
            worker.queue.put(full_url, True, self.blocking_timeout)
        self.finish_queues()
        self.stop_and_join()


def run_script(filename):
    with open(filename, 'rb') as f:
        content = f.read()
    script = ActionScript.parse(content)
    script.run()
    return script
