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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

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

import time
import Queue

try:
    import simplejson
except ImportError:
    import json as simplejson


class RequestDescription(object):
    """Describes info about a request."""

    def __init__(self, descrip_dict):
        self.thread = descrip_dict.get('thread', '1')
        self.relpath = descrip_dict['relpath']


class RequestThread(object):
    """Process requests in a worker thread."""

    _timer = time.time

    def __init__(self, identifier, blocking_time=1.0, _queue_size=1):
        self.identifier = identifier
        self.queue = Queue.Queue(_queue_size)
        self.start_time = self.end_time = None
        self.stats = []
        self.blocking_time = blocking_time

    def step_next(self):
        item = self.queue.get(True, self.blocking_time)
        self.start_time = self._timer()
        self.process(item)
        self.end_time = self._timer()
        self.update_stats(item)
        self.queue.task_done()

    def run(self, stop_event):
        while not stop_event.isSet():
            try:
                self.step_next()
            except Queue.Empty:
                pass

    def join(self):
        """Wait until all requests are finished."""
        self.queue.join()

    def process(self, item):
        pass

    def update_stats(self, item):
        self.stats.append((item, self.end_time - self.start_time))


class ActionScript(object):
    """This tracks the actions that we want to perform."""

    _thread_class = RequestThread

    def __init__(self):
        self.base_url = 'http://localhost:8080'
        self.blocking_timeout = 60.0
        self.requests = []

    @classmethod
    def parse(cls, content):
        script = cls()
        json_dict = simplejson.loads(content)
        if 'parameters' not in json_dict:
            raise ValueError('Missing "parameters" section')
        if 'requests' not in json_dict:
            raise ValueError('Missing "requests" section')
        if sorted(json_dict.keys()) != ['parameters', 'requests']:
            raise ValueError('unknown entries present.')
        param_dict = json_dict['parameters']
        request_list = json_dict['requests']
        base_url = param_dict.get('base_url', None)
        if base_url is not None:
            script.base_url = base_url
        blocking_timeout = param_dict.get('blocking_timeout', None)
        if blocking_timeout is not None:
            script.blocking_timeout = blocking_timeout
        for request_dict in request_list:
            request = RequestDescription(request_dict)
            script.requests.append(request)
        return script
