#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
# Copyright (C) 2006  Goffredo Baroncelli <kreijack@inwind.it>
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

import logging
import os
import re
import sys
import time

import turbogears
from turbogears import controllers
from cherrypy import NotFound
from configobj import ConfigObj

from loggerhead import util
from loggerhead.branchview import BranchView
from loggerhead.history import History, is_branch

log = logging.getLogger("loggerhead.controllers")


def cherrypy_friendly(s):
    """
    convert a config section name into a name that pleases cherrypy.
    """
    return re.sub(r'[^\w\d_]', '_', s)


class Project (object):
    def __init__(self, name, config):
        self.name = name
        self.friendly_name = config.get('name', name)
        self.description = config.get('description', '')
        self.long_description = config.get('long_description', '')
        self._config = config
        
        self._views = []
        for view_name in config.sections:
            log.debug('Configuring (project %s) branch %s...', name, view_name)
            self._add_view(view_name, config[view_name], config[view_name].get('folder'))
        
        self._auto_folder = config.get('auto_publish_folder', None)
        self._auto_list = []
        if self._auto_folder is not None:
            self._recheck_auto_folders()
    
    def _recheck_auto_folders(self):
        log.debug('recheck...')
        if self._auto_folder is None:
            return
        auto_list = []
        # scan a folder for bazaar branches, and add them automatically
        for path, folders, filenames in os.walk(self._auto_folder):
            for folder in folders:
                folder = os.path.join(path, folder)
                if is_branch(folder):
                    auto_list.append(folder)
        auto_list.sort()
        if auto_list == self._auto_list:
            # nothing has changed; do nothing.
            log.debug('ok')
            return

        # rebuild views:
        log.debug('Rescanning auto-folder for project %s ...', self.name)
        self._views = []
        for folder in auto_list:
            view_name = os.path.basename(folder)
            log.debug('Auto-configuring (project %s) branch %s...', self.name, view_name)
            self._add_view(view_name, ConfigObj(), folder)
        self._auto_list = auto_list
        
    def _add_view(self, view_name, view_config, folder):
        c_view_name = cherrypy_friendly(view_name)
        view = BranchView(self.name, c_view_name, view_name, folder, view_config, self._config)
        self._views.append(view)
        setattr(self, c_view_name, view)
        
    views = property(lambda self: self._views)


class Root (controllers.RootController):
    def __init__(self, config):
        self._projects = []
        self._config = config
        for project_name in self._config.sections:
            c_project_name = cherrypy_friendly(project_name)
            project = Project(c_project_name, self._config[project_name])
            self._projects.append(project)
            setattr(self, c_project_name, project)
        
    @turbogears.expose(template='loggerhead.templates.browse')
    def index(self):
        for p in self._projects:
            p._recheck_auto_folders()
        log.debug('%r' % {
            'projects': self._projects,
            'util': util,
            'title': self._config.get('title', ''),
        })
        return {}

    def _check_rebuild(self):
        for p in self._projects:
            for v in p.views:
                v.check_rebuild()



# for use in profiling the very-slow get_change() method:
#h = Root.bazaar.bzr_dev.get_history()
#w = list(h.get_revision_history())
#h._get_changes_profiled(w[:100])

