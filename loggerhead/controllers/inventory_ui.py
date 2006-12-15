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

import datetime
import logging
import os
import posixpath
import textwrap
import time

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead import util


log = logging.getLogger("loggerhead.controllers")

def dirname(path):
    while path.endswith('/'):
        path = path[:-1]
    path = posixpath.dirname(path)
    return path

        
class InventoryUI (object):

    @turbogears.expose(html='loggerhead.templates.inventory')
    def default(self, *args, **kw):
        z = time.time()
        h = util.get_history()
        
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = None
        
        path = kw.get('path', None)
        if (path == '/') or (path == ''):
            path = None

        try:
            revlist, revid = h.get_navigation(revid, path)
            rev = h.get_revision(revid)
            inv = h.get_inventory(revid)
        except Exception, x:
            log.error('Exception fetching changes: %r, %s' % (x, x))
            raise HTTPRedirect(turbogears.url('/changes'))

        if path is None:
            path = '/'
            file_id = None
        else:
            file_id = inv.path2id(path)
            
        # no navbar for revisions
        navigation = util.Container()

        # add parent & merge-point branch-nick info, in case it's useful
        change = h.get_change(revid)
        for p in change.parents:
            p.branch_nick = h.get_change(p.revid).branch_nick
        for p in change.merge_points:
            p.branch_nick = h.get_change(p.revid).branch_nick

        vals = {
            'branch_name': util.get_config().get('branch_name'),
            'util': util,
            'revid': revid,
            'change': change,
            'path': path,
            'updir': dirname(path),
            'filelist': h.get_filelist(inv, path),
            'history': h,
            'posixpath': posixpath,
            'navigation': navigation,
        }
        h.flush_cache()
        log.info('/inventory %r: %r secs' % (revid, time.time() - z))
        return vals
