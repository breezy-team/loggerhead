# Copyright (C) 2011 Canonical Ltd.
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
#
"""WSGI apps tend to return body content as part of a HEAD request.

We should definitely not do that.
"""

class HeadMiddleware(object):
    """When we get a HEAD request, we should not return body content.

    WSGI defaults to just generating everything, and not paying attention to
    whether it is a GET or a HEAD request. It does that because of potential
    issues getting the Headers correct.

    This middleware works by just omitting the body if the request method is
    HEAD.
    """

    def __init__(self, app):
        self._wrapped_app = app
        self._real_environ = None
        self._real_start_response = None
        self._real_writer = None

    def noop_write(self, chunk):
        """We intentionally ignore all body content that is returned."""
        pass

    def start_response(self, status, response_headers, exc_info=None):
        if exc_info is None:
            self._real_writer = self._real_start_response(status,
                response_headers)
        else:
            self._real_writer = self._real_start_response(status,
                response_headers, exc_info)
        return self.noop_write

    def __call__(self, environ, start_response):
        self._real_environ = environ
        self._real_start_response = start_response
        if environ.get('REQUEST_METHOD', 'GET') == 'HEAD':
            result = self._wrapped_app(environ, self.start_response)
            for chunk in result:
                pass
        else:
            result = self._wrapped_app(environ, start_response)
            for chunk in result:
                yield chunk
