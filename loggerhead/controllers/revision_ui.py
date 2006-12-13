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
import logging
import os
import textwrap
import time

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead import util

log = logging.getLogger("loggerhead.controllers")


class RevisionUI (object):

    @turbogears.expose(html='loggerhead.templates.revision')
    def default(self, *args, **kw):
        z = time.time()
        h = util.get_history()
        
        if len(args) > 0:
            revid = args[0]
        else:
            revid = None
        
        path = kw.get('path', None)
        start_revid = kw.get('start_revid', None)
        
        try:
            revlist, start_revid = h.get_navigation(start_revid, path)
            if revid is None:
                revid = start_revid
        except Exception, x:
            log.error('Exception fetching changes: %r, %s' % (x, x))
            raise HTTPRedirect(turbogears.url('/changes'))

        buttons = [
            ('top', turbogears.url('/changes')),
            ('files', turbogears.url([ '/files', revid ])),
            ('history', turbogears.url('/changes', start_revid=revid)),
        ]
        
        navigation = util.Container(buttons=buttons, revlist=revlist, revid=revid, start_revid=start_revid, path=path,
                                    pagesize=1, scan_url='/revision')
        
        vals = {
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'revid': revid,
            'change': h.get_change(revid, get_diffs=True),
            'util': util,
            'history': h,
            'navigation': navigation,
        }
        h.flush_cache()
        log.info('/revision: %r seconds' % (time.time() - z,))
        return vals
