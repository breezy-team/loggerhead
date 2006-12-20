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
import sys
import time

from configobj import ConfigObj

import turbogears
from turbogears import controllers
from cherrypy import HTTPRedirect, NotFound

my_config = ConfigObj('loggerhead.conf', encoding='utf-8')
extra_path = my_config.get('bzrpath', None)
if extra_path:
    sys.path.insert(0, extra_path)

from loggerhead import util
from loggerhead.branchview import BranchView
from loggerhead.history import History

log = logging.getLogger("loggerhead.controllers")


class Group (object):
    def __init__(self, name, config):
        self.name = name
        self.friendly_name = config.get('name', name)
        self.description = config.get('description', '')
        
        self._views = []
        for view_name in config.sections:
            log.debug('Configuring (group %r) branch %r...', name, view_name)
            view = BranchView(name, view_name, config[view_name])
            setattr(self, view_name, view)
            self._views.append(view)
    
    views = property(lambda self: self._views)


class Root (controllers.RootController):
    def __init__(self):
        global my_config
        self._groups = []
        for group_name in my_config.sections:
            group = Group(group_name, my_config[group_name])
            self._groups.append(group)
            setattr(self, group_name, group)
        
    @turbogears.expose(template='loggerhead.templates.browse')
    def index(self):
        return {
            'groups': self._groups,
            'util': util,
            'title': my_config.get('title', ''),
        }

    def check_rebuild(self):
        for g in self._groups:
            for v in g.views:
                v.check_rebuild()


# singleton:
Root = Root()

# re-index every 6 hours
index_freq = 6 * 3600

turbogears.scheduler.add_interval_task(initialdelay=1, interval=index_freq, action=Root.check_rebuild)

# for use in profiling the very-slow get_change() method:
#h = util.get_history()
#w = list(h.get_revision_history())
#h._get_changes_profiled(w[:100])

