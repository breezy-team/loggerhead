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


class Root (controllers.RootController):
    def __init__(self):
        global my_config
        self._views = []
        for branch_name in my_config.sections:
            log.debug('Configuring branch %r...', branch_name)
            view = BranchView(branch_name, my_config[branch_name])
            setattr(self, branch_name, view)
            self._views.append(view)
        
    @turbogears.expose()
    def index(self):
        # FIXME - display list of branches
        raise HTTPRedirect(turbogears.url('/bazaar-dev/changes'))

    def check_rebuild(self):
        for v in self._views:
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

