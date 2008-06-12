from paste.wsgiwrappers import WSGIRequest, WSGIResponse

from loggerhead.controllers.changelog_ui import ChangeLogUI

import logging

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
        c = ChangeLogUI(self)
        c.default(request, response)
        return response(environ, start_response)

