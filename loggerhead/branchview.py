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
import threading

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


with_history_lock = util.with_lock('_history_lock')


class BranchView (object):
    def __init__(self, name, config):
        self._name = name
        self._config = config
        self.log = logging.getLogger('loggerhead.%s' % (name,))
        
        # branch history
        self._history_lock = threading.RLock()
        self._history = None
        
        self.changes = ChangeLogUI(self)
        self.revision = RevisionUI(self)
        self.files = InventoryUI(self)
        self.annotate = AnnotateUI(self)
        self.download = DownloadUI(self)
        self.atom = AtomUI(self)
        
        # force history object to be loaded:
        self.get_history()
    
    config = property(lambda self: self._config)
    
    name = property(lambda self: self._name)
    
    friendly_name = property(lambda self: self._config.get('branch_name', self._name))

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
        if (self._history is None) or self._history.out_of_date():
            self.log.debug('Reload branch history...')
            if self._history is not None:
                self._history.detach()
            self._history = History.from_folder(self._config.get('folder'), self._name)
            cache_path = self._config.get('cachepath', None)
            if cache_path is not None:
                self._history.use_cache(ChangeCache(self._history, cache_path))
                self._history.use_search_index(TextIndex(self._history, cache_path))
        return self._history
    
    def check_rebuild(self):
        h = self.get_history()
        h.check_rebuild()
    
    def url(self, elements, **kw):
        if not isinstance(elements, list):
            elements = [elements]
        if elements[0].startswith('/'):
            elements[0] = elements[0][1:]
        return turbogears.url([ '/' + self.name ] + elements, **kw)

