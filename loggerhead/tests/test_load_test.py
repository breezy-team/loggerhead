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

import time
import threading
import Queue

from bzrlib import tests

from bzrlib.plugins.loggerhead.loggerhead import load_test


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


class TestActionScript(tests.TestCase):

    def test_parse_requires_parameters_and_requests(self):
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '{}')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '{"parameters": {}}')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse, '{"requests": []}')
        self.assertRaises(ValueError,
            load_test.ActionScript.parse,
                '{"parameters": {}, "requests": [], "garbage": "section"}')
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
        self.assertEqual(2, len(script.requests))
        self.assertEqual("/foo", script.requests[0].relpath)
        self.assertEqual("/bar", script.requests[1].relpath)


_cur_time = time.time()
def one_sec_timer():
    """Every time this timer is called, it increments by 1 second."""
    global _cur_time
    _cur_time += 1.0
    return _cur_time


class NoopRequestThread(load_test.RequestThread):

    # Every call to _timer will increment by one
    _timer = staticmethod(one_sec_timer)

    # Ensure that process never does anything
    def process(self, item):
        pass


class TestRequestThread(tests.TestCase):

    def test_step_next_tracks_time(self):
        rt = NoopRequestThread('id')
        rt.queue.put('item')
        rt.step_next()
        self.assertTrue(rt.queue.empty())
        self.assertEqual([('item', 1.0)], rt.stats)

    def test_step_multiple_items(self):
        rt = NoopRequestThread('id')
        rt.queue.put('item')
        rt.step_next()
        rt.queue.put('next-item')
        rt.step_next()
        self.assertTrue(rt.queue.empty())
        self.assertEqual([('item', 1.0), ('next-item', 1.0)], rt.stats)

    def test_step_next_will_timeout(self):
        # We don't want step_next to block forever
        rt = NoopRequestThread('id', blocking_time=0.001)
        self.assertRaises(Queue.Empty, rt.step_next)

    def test_run_stops_for_stop_event(self):
        rt = NoopRequestThread('id', blocking_time=0.001, _queue_size=2)
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
        self.assertEqual([('item1', 1.0), ('item2', 1.0), ('item3', 1.0)],
                         rt.stats[:3])
        # The last event might be item4 or might be item3, the important thing
        # is that even though there are still queued events, we won't
        # process anything past the first
        self.assertNotEqual('item5', rt.stats[-1][0])
