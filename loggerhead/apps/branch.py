# Copyright (C) 2008-2011 Canonical Ltd.
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

"""The WSGI application for serving a Bazaar branch."""

import logging
import urllib
import sys

import bzrlib.branch
import bzrlib.errors
from bzrlib.hooks import Hooks
import bzrlib.lru_cache

from paste import request
from paste import httpexceptions

from loggerhead.apps import static_app
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.view_ui import ViewUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.diff_ui import DiffUI
from loggerhead.controllers.download_ui import DownloadUI, DownloadTarballUI
from loggerhead.controllers.filediff_ui import FileDiffUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.revlog_ui import RevLogUI
from loggerhead.controllers.search_ui import SearchUI
from loggerhead.history import History
from loggerhead import util


_DEFAULT = object()

class BranchWSGIApp(object):

    def __init__(self, branch, friendly_name=None, config={},
                 graph_cache=None, branch_link=None, is_root=False,
                 served_url=_DEFAULT, use_cdn=False, private=False,
                 export_tarballs=True):
        """Create branch-publishing WSGI app.

        :param export_tarballs: If true, allow downloading snapshots of revisions
            as tarballs.
        """
        self.branch = branch
        self._config = config
        self.friendly_name = friendly_name
        self.branch_link = branch_link  # Currently only used in Launchpad
        self.log = logging.getLogger('loggerhead.%s' % (friendly_name,))
        if graph_cache is None:
            graph_cache = bzrlib.lru_cache.LRUCache(10)
        self.graph_cache = graph_cache
        self.is_root = is_root
        self.served_url = served_url
        self.use_cdn = use_cdn
        self.private = private
        self.export_tarballs = export_tarballs

    def public_private_css(self):
        if self.private:
            return "private"
        else:
            return "public"

    def get_history(self):
        revinfo_disk_cache = None
        cache_path = self._config.get('cachepath', None)
        if cache_path is not None:
            # Only import the cache if we're going to use it.
            # This makes sqlite optional
            try:
                from loggerhead.changecache import RevInfoDiskCache
            except ImportError:
                self.log.debug("Couldn't load python-sqlite,"
                               " continuing without using a cache")
            else:
                revinfo_disk_cache = RevInfoDiskCache(cache_path)
        return History(
            self.branch, self.graph_cache,
            revinfo_disk_cache=revinfo_disk_cache, cache_key=self.friendly_name)

    def url(self, *args, **kw):
        if isinstance(args[0], list):
            args = args[0]
        qs = []
        for k, v in kw.iteritems():
            if v is not None:
                qs.append('%s=%s' % (k, urllib.quote(v)))
        qs = '&'.join(qs)
        path_info = urllib.quote(
            unicode('/'.join(args)).encode('utf-8'), safe='/~:')
        if qs:
            path_info += '?' + qs
        return self._url_base + path_info

    def absolute_url(self, *args, **kw):
        rel_url = self.url(*args, **kw)
        return request.resolve_relative_url(rel_url, self._environ)

    def context_url(self, *args, **kw):
        kw = util.get_context(**kw)
        return self.url(*args, **kw)

    def static_url(self, path):
        return self._static_url_base + path

    def yui_url(self, path):
        if self.use_cdn:
            base = 'http://yui.yahooapis.com/3.0.0pr2/build/'
        else:
            base = self.static_url('/static/javascript/yui/build/')
        return base + path

    controllers_dict = {
        '+filediff': FileDiffUI,
        '+revlog': RevLogUI,
        'annotate': AnnotateUI,
        'atom': AtomUI,
        'changes': ChangeLogUI,
        'diff': DiffUI,
        'download': DownloadUI,
        'files': InventoryUI,
        'revision': RevisionUI,
        'search': SearchUI,
        'view': ViewUI,
        'tarball': DownloadTarballUI,
        }

    def last_updated(self):
        h = self.get_history()
        change = h.get_changes([h.last_revid])[0]
        return change.date

    def public_branch_url(self):
        return self.branch.get_config().get_user_option('public_branch')

    def lookup_app(self, environ):
        # Check again if the branch is blocked from being served, this is
        # mostly for tests. It's already checked in apps/transport.py
        if self.branch.get_config().get_user_option('http_serve') == 'False':
            raise httpexceptions.HTTPNotFound()
        self._url_base = environ['SCRIPT_NAME']
        self._static_url_base = environ.get('loggerhead.static.url')
        if self._static_url_base is None:
            self._static_url_base = self._url_base
        self._environ = environ
        if self.served_url is _DEFAULT:
            public_branch = self.public_branch_url()
            if public_branch is not None:
                self.served_url = public_branch
            else:
                # Loggerhead only supports serving .bzr/ on local branches, so
                # we shouldn't suggest something that won't work.
                try:
                    util.local_path_from_url(self.branch.base)
                    self.served_url = self.url([])
                except bzrlib.errors.InvalidURL:
                    self.served_url = None
        for hook in self.hooks['controller']:
            controller = hook(self, environ)
            if controller is not None:
                return controller
        path = request.path_info_pop(environ)
        if not path:
            raise httpexceptions.HTTPMovedPermanently(
                self.absolute_url('/changes'))
        if path == 'static':
            return static_app
        elif path == '+json':
            environ['loggerhead.as_json'] = True
            path = request.path_info_pop(environ)
        cls = self.controllers_dict.get(path)
        if cls is not None:
            return cls(self, self.get_history)
        raise httpexceptions.HTTPNotFound()

    def app(self, environ, start_response):
        self.branch.lock_read()
        try:
            try:
                c = self.lookup_app(environ)
                return c(environ, start_response)
            except:
                environ['exc_info'] = sys.exc_info()
                environ['branch'] = self
                raise
        finally:
            self.branch.unlock()


class BranchWSGIAppHooks(Hooks):
    """A dictionary mapping hook name to a list of callables for WSGI app branch hooks.
    """

    def __init__(self):
        """Create the default hooks.
        """
        Hooks.__init__(self, "bzrlib.plugins.loggerhead.apps.branch",
            "BranchWSGIApp.hooks")
        self.add_hook('controller',
            "Invoked when looking for the controller to use for a "
            "branch subpage. The api signature is (branch_app, environ)."
            "If a hook can provide a controller, it should return one, "
            "as a standard WSGI app. If it can't provide a controller, "
            "it should return None", (1, 19))


BranchWSGIApp.hooks = BranchWSGIAppHooks()
