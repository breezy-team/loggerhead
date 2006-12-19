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
util.get_index()


def rebuild_cache():
    h = util.get_history()
    if h.cache_full():
        return
    
    log.info('Building revision cache...')
    start_time = time.time()
    last_update = time.time()
    count = 0
    
    work = list(h.get_revision_history())
    jump = 100
    for i in xrange(0, len(work), jump):
        r = work[i:i + jump]
        list(h.get_changes(r))
        if h.out_of_date():
            return
        count += jump
        now = time.time()
        if now - start_time > 3600:
            # there's no point working for hours.  eventually we might even
            # hit the next re-index interval, which would suck mightily.
            log.info('Cache rebuilding has worked for an hour; giving up for now.')
            h.flush_cache()
            return
        if now - last_update > 60:
            log.info('Revision cache rebuilding continues: %d/%d' % (min(count, len(work)), len(work)))
            last_update = time.time()
            h.flush_cache()
    log.info('Revision cache rebuild completed.')


def check_index():
    index = util.get_index()
    h = util.get_history()
    work = list(h.get_revision_history())
    if len(work) == len(index):
        # all done
        return

    log.info('Building search index...')
    start_time = time.time()
    last_update = time.time()
    count = 0
    
    for revid in work:
        if not index.is_indexed(revid):
            index.index_change(h.get_changes([ revid ])[0])

        count += 1
        now = time.time()
        if now - start_time > 3600:
            # there's no point working for hours.  eventually we might even
            # hit the next re-index interval, which would suck mightily.
            log.info('Search indexing has worked for an hour; giving up for now.')
            index.flush()
            return
        if now - last_update > 60:
            log.info('Search indexing continues: %d/%d' % (min(count, len(work)), len(work)))
            last_update = time.time()
            index.flush()
    log.info('Search index completed.')


def rebuild():
    rebuild_cache()
    check_index()


# re-index every 6 hours
index_freq = 6 * 3600

turbogears.scheduler.add_interval_task(initialdelay=1, interval=index_freq, action=rebuild)

# for use in profiling the very-slow get_change() method:
#h = util.get_history()
#w = list(h.get_revision_history())
#h._get_changes_profiled(w[:100])

