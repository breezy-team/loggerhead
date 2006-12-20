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
import time

from configobj import ConfigObj

import turbogears
from turbogears import controllers
from cherrypy import HTTPRedirect, NotFound

from loggerhead import util

my_config = ConfigObj('loggerhead.conf', encoding='utf-8')
util.set_config(my_config)

from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.download_ui import DownloadUI
from loggerhead.history import History

log = logging.getLogger("loggerhead.controllers")

class Root (controllers.RootController):
    changes = ChangeLogUI()
    atom = AtomUI()
    revision = RevisionUI()
    files = InventoryUI()
    annotate = AnnotateUI()
    download = DownloadUI()
    
    @turbogears.expose()
    def index(self):
        raise HTTPRedirect(turbogears.url('/changes'))


# force history to be read:
util.get_history()


# re-index every 6 hours
index_freq = 6 * 3600

turbogears.scheduler.add_interval_task(initialdelay=1, interval=index_freq, action=util.check_rebuild)

# for use in profiling the very-slow get_change() method:
#h = util.get_history()
#w = list(h.get_revision_history())
#h._get_changes_profiled(w[:100])

