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

import datetime
import os
import posixpath
import textwrap

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead.history import History
from loggerhead import util


def dirname(path):
    while path.endswith('/'):
        path = path[:-1]
    path = posixpath.dirname(path)
    return path

        
class InventoryUI (object):

    @turbogears.expose(html='loggerhead.templates.inventory')
    def default(self, *args, **kw):
        h = History.from_folder(turbogears.config.get('loggerhead.folder'))
        if len(args) > 0:
            revid = args[0]
        else:
            revid = h.last_revid

        try:
            rev = h.get_revision(revid)
            inv = h.get_inventory(revid)
        except:
            raise HTTPRedirect(turbogears.url('/changes'))
        
        path = kw.get('path', None)
        if path is None:
            path = '/'
            file_id = None
        else:
            file_id = inv.path2id(path)
            
        buttons = [
            ('top', turbogears.url('/changes')),
            ('revision', turbogears.url([ '/revision', revid ])),
            ('history', turbogears.url([ '/changes', revid ])),
        ]

        vals = {
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'util': util,
            'buttons': buttons,
            'revid': revid,
            'change': h.get_change(revid),
            'path': path,
            'updir': dirname(path),
            'filelist': h.get_filelist(inv, path),
            'history': h,
            'scan_url': '/revision',
            'pagesize': 1,
            'posixpath': posixpath,
        }
        return vals
