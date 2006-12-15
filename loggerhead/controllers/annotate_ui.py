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

        
class AnnotateUI (object):

    @turbogears.expose(html='loggerhead.templates.annotate')
    def default(self, *args, **kw):
        z = time.time()
        h = util.get_history()
        
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = None
        
        path = kw.get('path', None)
        if (path == '/') or (path == '') or (path is None):
            raise HTTPRedirect(turbogears.url('/changes'))

        try:
            revlist, revid = h.get_navigation(revid, path)
            file_id = h.get_inventory(revid).path2id(path)
        except Exception, x:
            log.error('Exception fetching changes: %r, %s' % (x, x))
            raise HTTPRedirect(turbogears.url('/changes'))
            
        # no navbar for revisions
        navigation = util.Container()

        vals = {
            'branch_name': util.get_config().get('branch_name'),
            'util': util,
            'revid': revid,
            'path': path,
            'history': h,
            'navigation': navigation,
            'change': h.get_change(revid),
            'contents': list(h.annotate_file(file_id, revid)),
        }
        h.flush_cache()
        log.info('/annotate: %r secs' % (time.time() - z,))
        return vals
