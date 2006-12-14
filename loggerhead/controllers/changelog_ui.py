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

import base64
import logging
import os
import posixpath
import time

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead import util

log = logging.getLogger("loggerhead.controllers")


# just thinking out loud here...
#
# so, when browsing around, there are 3 pieces of context:
#     - starting revid 
#         the current beginning of navigation (navigation continues back to
#         the original revision) -- this may not be along the primary revision
#         path since the user may have navigated into a branch
#     - path
#         if navigating the revisions that touched a file
#     - current revid
#         current location along the navigation path (while browsing)
#
# current revid is given on the url path.  'path' and 'starting revid' are
# handed along as params.


class ChangeLogUI (object):
    
    @turbogears.expose(html='loggerhead.templates.changelog')
    def default(self, *args, **kw):
        z = time.time()
        h = util.get_history()
        
        if len(args) > 0:
            revid = args[0]
        else:
            revid = None

        path = kw.get('path', None)
        start_revid = kw.get('start_revid', None)
        pagesize = int(turbogears.config.get('loggerhead.pagesize', '20'))
        
        try:
            revlist, start_revid = h.get_navigation(start_revid, path)
            if revid is None:
                revid = start_revid
            entry_list = list(h.get_revids_from(revlist, revid))[:pagesize]
            entries = h.get_changelist(entry_list)
        except Exception, x:
            log.error('Exception fetching changes: %r, %s' % (x, x))
            raise HTTPRedirect(turbogears.url('/changes'))

        buttons = [
            ('home', turbogears.url('/changes')),
            ('files', turbogears.url([ '/files', revid ])),
            ('feed', turbogears.url('/atom')),
        ]

        navigation = util.Container(pagesize=pagesize, revid=revid, start_revid=start_revid, revlist=revlist,
                                    path=path, buttons=buttons, scan_url='/changes')
        next_page_revid = h.get_revlist_offset(revlist, revid, pagesize)
        prev_page_revid = h.get_revlist_offset(revlist, revid, -pagesize)
        
        entries = list(entries)
        # add parent & merge-point branch-nick info, in case it's useful
        for change in entries:
            for p in change.parents:
                p.branch_nick = h.get_change(p.revid).branch_nick
            for p in change.merge_points:
                p.branch_nick = h.get_change(p.revid).branch_nick

        vals = {
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'changes': list(entries),
            'util': util,
            'history': h,
            'revid': revid,
            'navigation': navigation,
            'path': path,
            'next_page_revid': next_page_revid,
            'prev_page_revid': prev_page_revid,
            'last_revid': h.last_revid,
            'start_revid': start_revid,
        }
        h.flush_cache()
        log.info('/changes %r: %r secs' % (revid, time.time() - z))
        return vals
