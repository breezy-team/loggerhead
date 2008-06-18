import logging
import os
import urllib

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

from loggerhead import util

static = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), 'static')

static_app = urlparser.make_static(None, static)

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

class BranchWSGIApp(object):

    def __init__(self, history, friendly_name=None):
        self.history = history
        self.friendly_name = friendly_name
        self.log = logging.getLogger(friendly_name)

    def url(self, *args, **kw):
        if isinstance(args[0], list):
            args = args[0]
        qs = []
        for k, v in kw.iteritems():
            if v is not None:
                qs.append('%s=%s'%(k, urllib.quote(v)))
        qs = '&'.join(qs)
        return request.construct_url(
            self._environ, script_name=self._url_base,
            path_info='/'.join(args),
            querystring=qs)

    def context_url(self, *args, **kw):
        kw = util.get_context(**kw)
        return self.url(*args, **kw)

    def static_url(self, path):
        return self._static_url_base + path

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
        self._static_url_base = environ.get('loggerhead.static.url')
        if self._static_url_base is None:
            self._static_url_base = self._url_base
        self._environ = environ
        path = request.path_info_pop(environ)
        if not path:
            raise httpexceptions.HTTPMovedPermanently(self._url_base + '/changes')
        if path == 'static':
            return static_app(environ, start_response)
        cls = self.controllers_dict.get(path)
        if cls is None:
            raise httpexceptions.HTTPNotFound()
        c = cls(self)
        c.default(req, response)
        return response(environ, start_response)

