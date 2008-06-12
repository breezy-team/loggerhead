import logging
import os

from paste import urlparser
from paste.request import path_info_pop
from paste.wsgiwrappers import WSGIRequest, WSGIResponse

from loggerhead.controllers.changelog_ui import ChangeLogUI


static = os.path.join(
    os.path.dirname(__file__), 'static')

static_app = urlparser.make_static(None, static)

logging.basicConfig()

class BranchWSGIApp(object):

    def __init__(self, history):
        self.history = history
        self.friendly_name = 'hello'
        self.log = logging.getLogger('hi')

    def url(self, *args, **kw):
        return 'not yet'

    context_url = url

    def app(self, environ, start_response):
        request = WSGIRequest(environ)
        response = WSGIResponse()
        response.headers['Content-Type'] = 'text/plain'
        path = path_info_pop(environ)
        if not path or path == 'changes':
            c = ChangeLogUI(self)
            c.default(request, response)
        elif path == 'static':
            return static_app(environ, start_response)
        return response(environ, start_response)

