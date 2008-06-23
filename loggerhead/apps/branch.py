import logging
import urllib

from paste import request
from paste import httpexceptions
from paste.wsgiwrappers import WSGIRequest, WSGIResponse

from loggerhead.apps import static_app
from loggerhead.changecache import FileChangeCache
from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.download_ui import DownloadUI
from loggerhead.history import History
from loggerhead import util

logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

class BranchWSGIApp(object):

    def __init__(self, branch_url, friendly_name=None, config={}):
        self.branch_url = branch_url
        self._history = None
        self._config = config
        self.friendly_name = friendly_name
        self.log = logging.getLogger(friendly_name)

    @property
    def history(self):
        if (self._history is None) or self._history.out_of_date():
            self.log.debug('Reload branch history...')
            _history = self._history = History.from_folder(self.branch_url)
            cache_path = self._config.get('cachepath', None)
            if cache_path is not None:
                _history.use_file_cache(FileChangeCache(_history, cache_path))
        return self._history

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
        }

    def last_updated(self):
        h = self.history
        change = h.get_changes([ h.last_revid ])[0]
        return change.date

    def branch_url(self):
        return self.history.get_config().get_user_option('public_branch')

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
            raise httpexceptions.HTTPMovedPermanently(
                self._url_base + '/changes')
        if path == 'static':
            return static_app(environ, start_response)
        cls = self.controllers_dict.get(path)
        if cls is None:
            raise httpexceptions.HTTPNotFound()
        c = cls(self)
        c.default(req, response)
        return response(environ, start_response)
