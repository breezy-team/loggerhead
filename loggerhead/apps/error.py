# Copyright (C) 2008  Guillermo Gonzalez <guillo.gonzo@gmail.com>
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

from loggerhead.controllers.error_ui import ErrorUI


class ErrorHandlerApp(object):
    """Class for WSGI error logging middleware."""

    msg = " %s.%s: %s \n"

    def __init__(self, application, **kwargs):
        self.application = application

    def __call__(self, environ, start_response):
        try:
            return self.application(environ, start_response)
        except:
            # test if exc_info has been set, in the case that
            # the error is caused before BranchWSGGIApp middleware
            if 'exc_info' in environ.keys() and 'branch' in environ.keys():
                # Log and/or report any application errors
                return self.handle_error(environ, start_response)
            else:
                # simply propagate the error, this is logged
                # by paste.httpexceptions.TransLogger middleware
                raise

    def handle_error(self, environ, start_response):
        """Exception hanlder."""
        self.log_error(environ)
        return errapp(environ, start_response)

    def log_error(self, environ):
        exc_type, exc_object, exc_tb = environ['exc_info']
        logger = environ['branch'].log
        logger.exception(self.msg, exc_type.__module__,
                              exc_type.__name__, exc_object)


def errapp(environ, start_response):
    """Default (and trivial) error handling WSGI application."""
    c = ErrorUI(environ['branch'], environ['exc_info'])
    return c(environ, start_response)
