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
from loggerhead.changecache import FileChangeCache
from loggerhead.history import History
from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.download_ui import DownloadUI
from loggerhead.controllers.bundle_ui import BundleUI


with_history_lock = util.with_lock('_history_lock', 'History')


class BranchView (object):
    def __init__(self, group_name, name, subfolder, absfolder, config,
                 project_config, root_config):
        self._group_name = group_name
        self._name = name
        self._folder = subfolder
        self._absfolder = absfolder
        self._config = config
        self._project_config = project_config
        self._root_config = root_config
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
        self.bundle = BundleUI(self)

        # force history object to be loaded:
        self.get_history()

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

    def get_config_item(self, item, default=None):
        for conf in self._config, self._project_config, self._root_config:
            if item in conf:
                return conf[item]
        return default

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
            _history = self._history = History.from_folder(
                self._absfolder, self._name)
            cache_path = self._config.get('cachepath', None)
            if cache_path is None:
                # try the project config
                cache_path = self._project_config.get('cachepath', None)
            if cache_path is not None:
                _history.use_file_cache(FileChangeCache(_history, cache_path))
        return self._history

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
