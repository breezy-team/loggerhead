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

import logging
import time

import turbogears
from turbogears import controllers
from cherrypy import HTTPRedirect, NotFound

from loggerhead.controllers.changelog_ui import ChangeLogUI
from loggerhead.controllers.atom_ui import AtomUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.history import History
from loggerhead import util


log = logging.getLogger("loggerhead.controllers")

class Root (controllers.RootController):
    changes = ChangeLogUI()
    atom = AtomUI()
    revision = RevisionUI()
    files = InventoryUI()
    annotate = AnnotateUI()
    
    @turbogears.expose()
    def index(self):
        raise HTTPRedirect(turbogears.url('/changes'))


# force history to be read:
util.get_history()

def rebuild_cache():
    log.info('Rebuilding revision cache...')
    last_update = time.time()
    h = util.get_history()
    count = 0
    
    work = h.get_revision_history()
    for r in work:
        h.get_change(r)
        if h.out_of_date():
            return
        count += 1
        if time.time() - last_update > 60:
            log.info('Revision cache rebuilding continues: %d/%d' % (count, len(work)))
            last_update = time.time()
            h.flush_cache()
    log.info('Revision cache rebuild completed.')


# re-index every hour (for now -- maybe should be even longer?)
index_freq = 3600

#turbogears.scheduler.add_interval_task(initialdelay=1, interval=index_freq, action=rebuild_cache)

# for use in profiling the very-slow get_change() method:
#h = util.get_history()
#h._get_change_profiled(h.last_revid)

