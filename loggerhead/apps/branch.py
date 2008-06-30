import logging
import urllib

import bzrlib.branch

from paste import request
from paste import httpexceptions

from loggerhead.apps import static_app

from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.download_ui import DownloadUI
from loggerhead.history import History
from loggerhead import util


class BranchWSGIApp(object):

    def __init__(self, branch_url, friendly_name=None, config={}):
        self.branch_url = branch_url
        self._config = config
        self.friendly_name = friendly_name
        self.log = logging.getLogger('loggerhead.%s' % (friendly_name,))

    def get_history(self, b):
        _history = History.from_branch(b)
        cache_path = self._config.get('cachepath', None)
        if cache_path is not None:
            # Only import the cache if we're going to use it.
            # This makes sqlite optional
            try:
                from loggerhead.changecache import FileChangeCache
            except ImportError:
                self.log.debug("Couldn't load python-sqlite," 
                               " continuing without using a cache")
            else:
                _history.use_file_cache(
                    FileChangeCache(_history, cache_path))
        return _history

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
        h = self.get_history()
        change = h.get_changes([ h.last_revid ])[0]
        return change.date

    def branch_url(self):
        return self.history.get_config().get_user_option('public_branch')

    def app(self, environ, start_response):
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
        b = bzrlib.branch.Branch.open(self.branch_url)
        b.lock_read()
        try:
            c = cls(self, self.get_history(b))
            return c(environ, start_response)
        finally:
            b.unlock()
