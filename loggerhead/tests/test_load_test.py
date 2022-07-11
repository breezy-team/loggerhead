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
#

"""Tests for the load testing code."""

import socket
import time
import threading
from queue import Empty

from breezy import tests
from breezy.tests import http_server

from .. import load_test


empty_script = """{
    "parameters": {},
    "requests": []
}"""

class TestRequestDescription(tests.TestCase):

    def test_init_from_dict(self):
        rd = load_test.RequestDescription({'thread': '10', 'relpath': '/foo'})
        self.assertEqual('10', rd.thread)
        self.assertEqual('/foo', rd.relpath)

    def test_default_thread_is_1(self):
        rd = load_test.RequestDescription({'relpath': '/bar'})
        self.assertEqual('1', rd.thread)
        self.assertEqual('/bar', rd.relpath)


_cur_time = time.time()
def one_sec_timer():
    """Every time this timer is called, it increments by 1 second."""
    global _cur_time
    _cur_time += 1.0
    return _cur_time


class NoopRequestWorker(load_test.RequestWorker):

    # Every call to _timer will increment by one
    _timer = staticmethod(one_sec_timer)

    # Ensure that process never does anything
    def process(self, url):
        return True


class TestRequestWorkerInfrastructure(tests.TestCase):
    """Tests various infrastructure bits, without doing actual requests."""

    def test_step_next_tracks_time(self):
        rt = NoopRequestWorker('id')
        rt.queue.put('item')
        rt.step_next()
        self.assertTrue(rt.queue.empty())
        self.assertEqual([('item', True, 1.0)], rt.stats)

    def test_step_multiple_items(self):
        rt = NoopRequestWorker('id')
        rt.queue.put('item')
        rt.step_next()
        rt.queue.put('next-item')
        rt.step_next()
        self.assertTrue(rt.queue.empty())
        self.assertEqual([('item', True, 1.0), ('next-item', True, 1.0)],
                         rt.stats)

    def test_step_next_does_nothing_for_noop(self):
        rt = NoopRequestWorker('id')
        rt.queue.put('item')
        rt.step_next()
        rt.queue.put('<noop>')
        rt.step_next()
        self.assertEqual([('item', True, 1.0)], rt.stats)

    def test_step_next_will_timeout(self):
        # We don't want step_next to block forever
        rt = NoopRequestWorker('id', blocking_time=0.001)
        self.assertRaises(Empty, rt.step_next)

    def test_run_stops_for_stop_event(self):
        rt = NoopRequestWorker('id', blocking_time=0.001, _queue_size=2)
        rt.queue.put('item1')
        rt.queue.put('item2')
        event = threading.Event()
        t = threading.Thread(target=rt.run, args=(event,))
        t.start()
        # Wait for the queue to be processed
        rt.queue.join()
        # Now we can queue up another one, and wait for it
        rt.queue.put('item3')
        rt.queue.join()
        # Now set the stopping event
        event.set()
        # Add another item to the queue, which might get processed, but the
        # next item won't
        rt.queue.put('item4')
        rt.queue.put('item5')
        t.join()
        self.assertEqual([('item1', True, 1.0), ('item2', True, 1.0),
                          ('item3', True, 1.0)],
                         rt.stats[:3])
        # The last event might be item4 or might be item3, the important thing
        # is that even though there are still queued events, we won't
        # process anything past the first
        self.assertNotEqual('item5', rt.stats[-1][0])


class TestRequestWorker(tests.TestCaseWithTransport):

    def setUp(self):
        super(TestRequestWorker, self).setUp()
        self.transport_readonly_server = http_server.HttpServer

    def test_request_items(self):
        rt = load_test.RequestWorker('id', blocking_time=0.01, _queue_size=2)
        self.build_tree(['file1', 'file2'])
        readonly_url1 = self.get_readonly_url('file1')
        self.assertStartsWith(readonly_url1, 'http://')
        readonly_url2 = self.get_readonly_url('file2')
        rt.queue.put(readonly_url1)
        rt.queue.put(readonly_url2)
        rt.step_next()
        rt.step_next()
        self.assertEqual(readonly_url1, rt.stats[0][0])
        self.assertEqual(readonly_url2, rt.stats[1][0])

    def test_request_nonexistant_items(self):
        rt = load_test.RequestWorker('id', blocking_time=0.01, _queue_size=2)
        readonly_url1 = self.get_readonly_url('no-file1')
        rt.queue.put(readonly_url1)
        rt.step_next()
        self.assertEqual(readonly_url1, rt.stats[0][0])
        self.assertEqual(False, rt.stats[0][1])

    def test_no_server(self):
        s = socket.socket()
        # Bind to a port, but don't listen on it
        s.bind(('localhost', 0))
        url = 'http://%s:%s/path' % s.getsockname()
        rt = load_test.RequestWorker('id', blocking_time=0.01, _queue_size=2)
        rt.queue.put(url)
        rt.step_next()
        self.assertEqual((url, False), rt.stats[0][:2])


class NoActionScript(load_test.ActionScript):

    _thread_class = NoopRequestWorker
    _default_blocking_timeout = 0.01


class TestActionScriptInfrastructure(tests.TestCase):

    def test_parse_requires_parameters_and_requests(self):
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '{}')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '{"parameters": {}}')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '{"requests": []}')
        load_test.ActionScript.parse(
            '{"parameters": {}, "requests": [], "comment": "section"}')
        script = load_test.ActionScript.parse(
            empty_script)
        self.assertIsNot(None, script)

    def test_parse_default_base_url(self):
        script = load_test.ActionScript.parse(empty_script)
        self.assertEqual('http://localhost:8080', script.base_url)

    def test_parse_find_base_url(self):
        script = load_test.ActionScript.parse(
            '{"parameters": {"base_url": "http://example.com"},'
            ' "requests": []}')
        self.assertEqual('http://example.com', script.base_url)

    def test_parse_default_blocking_timeout(self):
        script = load_test.ActionScript.parse(empty_script)
        self.assertEqual(60.0, script.blocking_timeout)

    def test_parse_find_blocking_timeout(self):
        script = load_test.ActionScript.parse(
            '{"parameters": {"blocking_timeout": 10.0},'
            ' "requests": []}'
        )
        self.assertEqual(10.0, script.blocking_timeout)

    def test_parse_finds_requests(self):
        script = load_test.ActionScript.parse(
            '{"parameters": {}, "requests": ['
            ' {"relpath": "/foo"},'
            ' {"relpath": "/bar"}'
            ' ]}')
        self.assertEqual(2, len(script._requests))
        self.assertEqual("/foo", script._requests[0].relpath)
        self.assertEqual("/bar", script._requests[1].relpath)

    def test__get_worker(self):
        script = NoActionScript()
        # If an id is found, then we should create it
        self.assertEqual({}, script._threads)
        worker = script._get_worker('id')
        self.assertTrue('id' in script._threads)
        # We should have set the blocking timeout
        self.assertEqual(script.blocking_timeout / 10.0,
                         worker.blocking_time)

        # Another request will return the identical object
        self.assertIs(worker, script._get_worker('id'))

        # And the stop event will stop the thread
        script.stop_and_join()

    def test__full_url(self):
        script = NoActionScript()
        self.assertEqual('http://localhost:8080/path',
                         script._full_url('/path'))
        self.assertEqual('http://localhost:8080/path/to/foo',
                         script._full_url('/path/to/foo'))
        script.base_url = 'http://example.com'
        self.assertEqual('http://example.com/path/to/foo',
                         script._full_url('/path/to/foo'))
        script.base_url = 'http://example.com/base'
        self.assertEqual('http://example.com/base/path/to/foo',
                         script._full_url('/path/to/foo'))
        script.base_url = 'http://example.com'
        self.assertEqual('http://example.com:8080/path',
                         script._full_url(':8080/path'))

    def test_single_threaded(self):
        script = NoActionScript.parse("""{
            "parameters": {"base_url": ""},
            "requests": [
                {"thread": "1", "relpath": "first"},
                {"thread": "1", "relpath": "second"},
                {"thread": "1", "relpath": "third"},
                {"thread": "1", "relpath": "fourth"}
            ]}""")
        script.run()
        worker = script._get_worker("1")
        self.assertEqual(["first", "second", "third", "fourth"],
                         [s[0] for s in worker.stats])

    def test_two_threads(self):
        script = NoActionScript.parse("""{
            "parameters": {"base_url": ""},
            "requests": [
                {"thread": "1", "relpath": "first"},
                {"thread": "2", "relpath": "second"},
                {"thread": "1", "relpath": "third"},
                {"thread": "2", "relpath": "fourth"}
            ]}""")
        script.run()
        worker = script._get_worker("1")
        self.assertEqual(["first", "third"],
                         [s[0] for s in worker.stats])
        worker = script._get_worker("2")
        self.assertEqual(["second", "fourth"],
                         [s[0] for s in worker.stats])


class TestActionScriptIntegration(tests.TestCaseWithTransport):

    def setUp(self):
        super(TestActionScriptIntegration, self).setUp()
        self.transport_readonly_server = http_server.HttpServer

    def test_full_integration(self):
        self.build_tree(['first', 'second', 'third', 'fourth'])
        url = self.get_readonly_url()
        script = load_test.ActionScript.parse("""{
            "parameters": {"base_url": "%s", "blocking_timeout": 2.0},
            "requests": [
                {"thread": "1", "relpath": "first"},
                {"thread": "2", "relpath": "second"},
                {"thread": "1", "relpath": "no-this"},
                {"thread": "2", "relpath": "or-this"},
                {"thread": "1", "relpath": "third"},
                {"thread": "2", "relpath": "fourth"}
            ]}""" % (url,))
        script.run()
        worker = script._get_worker("1")
        self.assertEqual([("first", True), ('no-this', False),
                          ("third", True)],
                         [(s[0].rsplit('/', 1)[1], s[1])
                          for s in worker.stats])
        worker = script._get_worker("2")
        self.assertEqual([("second", True), ('or-this', False),
                          ("fourth", True)],
                         [(s[0].rsplit('/', 1)[1], s[1])
                          for s in worker.stats])


class TestRunScript(tests.TestCaseWithTransport):

    def setUp(self):
        super(TestRunScript, self).setUp()
        self.transport_readonly_server = http_server.HttpServer

    def test_run_script(self):
        self.build_tree(['file1', 'file2', 'file3', 'file4'])
        url = self.get_readonly_url()
        self.build_tree_contents([('localhost.script', """{
    "parameters": {"base_url": "%s", "blocking_timeout": 0.1},
    "requests": [
        {"thread": "1", "relpath": "file1"},
        {"thread": "2", "relpath": "file2"},
        {"thread": "1", "relpath": "file3"},
        {"thread": "2", "relpath": "file4"}
    ]
}""" % (url,))])
        script = load_test.run_script('localhost.script')
        worker = script._threads["1"][0]
        self.assertEqual([("file1", True), ('file3', True)],
                         [(s[0].rsplit('/', 1)[1], s[1])
                          for s in worker.stats])
        worker = script._threads["2"][0]
        self.assertEqual([("file2", True), ("file4", True)],
                         [(s[0].rsplit('/', 1)[1], s[1])
                          for s in worker.stats])
