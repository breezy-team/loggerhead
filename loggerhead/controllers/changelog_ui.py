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
#     - file_id
#         if navigating the revisions that touched a file
#     - current revid
#         current location along the navigation path (while browsing)
#
# current revid is given on the url path.  'file_id' and 'starting revid' are
# handed along as params.


class ChangeLogUI (object):
    
    @turbogears.expose(html='loggerhead.templates.changelog')
    def default(self, *args, **kw):
        z = time.time()
        h = util.get_history()
        
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = None

        file_id = kw.get('file_id', None)
        query = kw.get('q', None)
        start_revid = h.fix_revid(kw.get('start_revid', None))
        pagesize = int(util.get_config().get('pagesize', '20'))
        search_failed = False
        
        try:
            if query is None:
                revlist, start_revid = h.get_navigation(start_revid, file_id)
                if revid is None:
                    revid = start_revid
                if revid not in revlist:
                    # if the given revid is not in the revlist, use a revlist that
                    # starts at the given revid.
                    revlist, start_revid = h.get_navigation(revid, file_id)
                # scanning in direct-parent order
                scan_list = list(h.get_revids_from(revlist, revid))
            else:
                # potentially limit the search
                if (start_revid is not None) or (file_id is not None):
                    revlist, start_revid = h.get_navigation(start_revid, file_id)
                else:
                    revlist = None

                revlist = h.get_search_revid_list(query, revlist)
                if len(revlist) > 0:
                    start_revid = revlist[0]
                    if revid not in revlist:
                        revid = start_revid
                    scan_list = revlist[h.get_revid_sequence(revlist, revid):]
                else:
                    # no results
                    search_failed = True
                    start_revid = None
                    revid = None
                    scan_list = []

            entry_list = scan_list[:pagesize]
            entries = h.get_changes(entry_list)
        except Exception, x:
            log.error('Exception fetching changes: %s' % (x,))
            util.log_exception(log)
            raise HTTPRedirect(turbogears.url('/changes'))

        navigation = util.Container(pagesize=pagesize, revid=revid, start_revid=start_revid, revlist=revlist,
                                    file_id=file_id, scan_url='/changes', feed=True)
        if query is not None:
            navigation.query = query
        util.fill_in_navigation(h, navigation)
        
        entries = list(entries)
        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks(entries)

        vals = {
            'branch_name': util.get_config().get('branch_name'),
            'changes': list(entries),
            'util': util,
            'history': h,
            'revid': revid,
            'navigation': navigation,
            'file_id': file_id,
            'last_revid': h.last_revid,
            'start_revid': start_revid,
            'query': query,
            'search_failed': search_failed,
        }
        h.flush_cache()
        log.info('/changes %r: %r secs' % (revid, time.time() - z))
        return vals
