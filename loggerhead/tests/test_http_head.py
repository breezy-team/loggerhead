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

"""Tests for the HeadMiddleware app."""

from io import BytesIO

from breezy import tests

from ..apps import http_head


content = [b"<html>",
           b"<head><title>Listed</title></head>",
           b"<body>Content</body>",
           b"</html>",
          ]
headers = {'X-Ignored-Header': 'Value'}

def yielding_app(environ, start_response):
    writer = start_response('200 OK', headers)
    for chunk in content:
        yield chunk


def list_app(environ, start_response):
    writer = start_response('200 OK', headers)
    return content


def writer_app(environ, start_response):
    writer = start_response('200 OK', headers)
    for chunk in content:
        writer(chunk)
    return []


class TestHeadMiddleware(tests.TestCase):

    def _trap_start_response(self, status, response_headers, exc_info=None):
        self._write_buffer = BytesIO()
        self._start_response_passed = (status, response_headers, exc_info)
        return self._write_buffer.write

    def _consume_app(self, app, request_method):
        environ = {'REQUEST_METHOD': request_method}
        value = list(app(environ, self._trap_start_response))
        self._write_buffer.writelines(value)

    def _verify_get_passthrough(self, app):
        app = http_head.HeadMiddleware(app)
        self._consume_app(app, 'GET')
        self.assertEqual(('200 OK', headers, None), self._start_response_passed)
        self.assertEqualDiff(b''.join(content), self._write_buffer.getvalue())

    def _verify_head_no_body(self, app):
        app = http_head.HeadMiddleware(app)
        self._consume_app(app, 'HEAD')
        self.assertEqual(('200 OK', headers, None), self._start_response_passed)
        self.assertEqualDiff(b'', self._write_buffer.getvalue())

    def test_get_passthrough_yielding(self):
        self._verify_get_passthrough(yielding_app)

    def test_head_passthrough_yielding(self):
        self._verify_head_no_body(yielding_app)

    def test_get_passthrough_list(self):
        self._verify_get_passthrough(list_app)

    def test_head_passthrough_list(self):
        self._verify_head_no_body(list_app)

    def test_get_passthrough_writer(self):
        self._verify_get_passthrough(writer_app)

    def test_head_passthrough_writer(self):
        self._verify_head_no_body(writer_app)

