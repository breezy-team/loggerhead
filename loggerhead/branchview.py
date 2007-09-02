#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
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
#

"""
collection of configuration and objects related to a bazaar branch.
"""

import logging
import posixpath
import threading
import urllib

import turbogears
from cherrypy import HTTPRedirect

from loggerhead import util
from loggerhead.changecache import ChangeCache
from loggerhead.history import History
from loggerhead.textindex import TextIndex
from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.download_ui import DownloadUI
from loggerhead.controllers.bundle_ui import BundleUI


with_history_lock = util.with_lock('_history_lock', 'History')


class BranchView (object):
    def __init__(self, group_name, name, subfolder, absfolder, config, project_config):
        self._group_name = group_name
        self._name = name
        self._folder = subfolder
        self._absfolder = absfolder
        self._config = config
        self._project_config = project_config
        self.log = logging.getLogger('loggerhead.%s' % (name,))
        
        # branch history
        self._history_lock = threading.RLock()
        self._history = None
        self._closed = False
        
        self.changes = ChangeLogUI(self)
        self.revision = RevisionUI(self)
        self.files = InventoryUI(self)
        self.annotate = AnnotateUI(self)
        self.download = DownloadUI(self)
        self.atom = AtomUI(self)
        self.bundle = BundleUI(self)
        
        # force history object to be loaded:
        self.get_history()
        
        turbogears.startup.call_on_shutdown.append(self.close)
    
    @with_history_lock
    def close(self):
        # it's important that we cleanly detach the history, so the cache
        # files can be closed correctly and hopefully remain uncorrupted.
        # this should also stop any ongoing indexing.
        self._history.detach()
        self._history = None
        self._closed = True
            
    config = property(lambda self: self._config)
    
    name = property(lambda self: self._name)

    group_name = property(lambda self: self._group_name)
    
    def _get_friendly_name(self):
        name = self._config.get('branch_name', None)
        if name is not None:
            return name
        # try branch-specific config?
        name = self.get_history().get_config().get_nickname()
        if name is not None:
            return name
        return self._name

    friendly_name = property(_get_friendly_name)

    def _get_description(self):
        description = self._config.get('description', None)
        if description is not None:
            return description
        # try branch-specific config?
        description = self.get_history().get_config().get_user_option('description')
        return description
        
    description = property(_get_description)
    
    def _get_branch_url(self):
        url = self._config.get('url', None)
        if url is not None:
            return url
        # try to assemble one from the project, if an url_prefix was defined.
        url = self._project_config.get('url_prefix', None)
        if url is not None:
            return posixpath.join(url, self._folder) + '/'
        # try branch-specific config?
        url = self.get_history().get_config().get_user_option('public_branch')
        return url
        
    branch_url = property(_get_branch_url)
    
    @turbogears.expose()
    def index(self):
        raise HTTPRedirect(self.url('/changes'))

    @with_history_lock
    def get_history(self):
        """
        get an up-to-date History object, safely.  each page-view calls this
        method, and normally it will get the same History object as on previous
        calls.  but if the bazaar branch on-disk has been updated since this
        History was created, a new object will be created and returned.
        """
        if self._closed:
            return None
        if (self._history is None) or self._history.out_of_date():
            self.log.debug('Reload branch history...')
            if self._history is not None:
                self._history.detach()
            self._history = History.from_folder(self._absfolder, self._name)
            cache_path = self._config.get('cachepath', None)
            if cache_path is None:
                # try the project config
                cache_path = self._project_config.get('cachepath', None)
            if cache_path is not None:
                self._history.use_cache(ChangeCache(self._history, cache_path))
                self._history.use_search_index(TextIndex(self._history, cache_path))
        return self._history
    
    def check_rebuild(self):
        h = self.get_history()
        if h is not None:
            h.check_rebuild()
    
    def url(self, elements, **kw):
        "build an url relative to this branch"
        if not isinstance(elements, list):
            elements = [elements]
        if elements[0].startswith('/'):
            elements[0] = elements[0][1:]
        elements = [urllib.quote(x) for x in elements]
        return turbogears.url([ '/' + self.group_name, self.name ] + elements, **kw)

    def context_url(self, elements, **kw):
        "build an url relative to this branch, bringing along browsing context"
        return self.url(elements, **util.get_context(**kw))
    
    def last_updated(self):
        h = self.get_history()
        change = h.get_changes([ h.last_revid ])[0]
        return change.date
