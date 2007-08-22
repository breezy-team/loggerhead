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
from cherrypy import InternalError, session

from loggerhead import util


log = logging.getLogger("loggerhead.controllers")

def dirname(path):
    while path.endswith('/'):
        path = path[:-1]
    path = posixpath.dirname(path)
    return path

        
class InventoryUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    @util.strip_whitespace
    @turbogears.expose(html='loggerhead.templates.inventory')
    def default(self, *args, **kw):
        z = time.time()
        h = self._branch.get_history()
        util.set_context(kw)
        
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = h.last_revid

        try:
            inv = h.get_inventory(revid)
        except:
            self.log.exception('Exception fetching changes')
            raise InternalError('Could not fetch changes')

        file_id = kw.get('file_id', inv.root.file_id)
        sort_type = kw.get('sort', None)

        # no navbar for revisions
        navigation = util.Container()

        change = h.get_changes([ revid ])[0]
        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks([ change ])

        path = inv.id2path(file_id)
        if not path.startswith('/'):
            path = '/' + path
        idpath = inv.get_idpath(file_id)
        if len(idpath) > 1:
            updir = dirname(path)
            updir_file_id = idpath[-2]
        else:
            updir = None
            updir_file_id = None
        if updir == '/':
            updir_file_id = None

        vals = {
            'branch': self._branch,
            'util': util,
            'revid': revid,
            'change': change,
            'file_id': file_id,
            'path': path,
            'updir': updir,
            'updir_file_id': updir_file_id,
            'filelist': h.get_filelist(inv, file_id, sort_type),
            'history': h,
            'posixpath': posixpath,
            'navigation': navigation,
        }
        h.flush_cache()
        self.log.info('/inventory %r: %r secs' % (revid, time.time() - z))
        return vals
