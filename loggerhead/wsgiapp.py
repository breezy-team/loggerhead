import logging
import os

from paste import urlparser
from paste import request
from paste import httpexceptions
from paste.wsgiwrappers import WSGIRequest, WSGIResponse

from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.download_ui import DownloadUI
from loggerhead.controllers.bundle_ui import BundleUI


static = os.path.join(
    os.path.dirname(__file__), 'static')

static_app = urlparser.make_static(None, static)

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

class BranchWSGIApp(object):

    def __init__(self, history):
        self.history = history
        self.friendly_name = 'hello'
        self.log = logging.getLogger('hi')

    def url(self, *args, **kw):
        if isinstance(args[0], list):
            args = args[0]
        qs = ''
        for k, v in kw.iteritems():
            qs += '%s=%s'%(k, v)
        return request.construct_url(
            self._environ, script_name=self._url_base,
            path_info=self._url_base + '/'.join(args),
            querystring=qs)

    context_url = url

    controllers_dict = {
        'annotate': AnnotateUI,
        'changes': ChangeLogUI,
        'files': InventoryUI,
        'revision': RevisionUI,
        'download': DownloadUI,
        'atom': AtomUI,
        'bundle': BundleUI,
        }

    def app(self, environ, start_response):
        req = WSGIRequest(environ)
        response = WSGIResponse()
        response.headers['Content-Type'] = 'text/plain'
        self._url_base = environ['SCRIPT_NAME']
        self._environ = environ
        path = request.path_info_pop(environ)
        if not path:
            raise httpexceptions.HTTPMovedPermanently('changes')
        if path == 'static':
            return static_app(environ, start_response)
        cls = self.controllers_dict.get(path)
        if cls is None:
            raise httpexceptions.HTTPNotFound()
        c = cls(self)
        c.default(req, response)
        return response(environ, start_response)

