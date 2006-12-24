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
import textwrap
import time

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead import util


class RevisionUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    @turbogears.expose(html='loggerhead.templates.revision')
    def default(self, *args, **kw):
        z = time.time()
        h = self._branch.get_history()
        
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = None
        
        file_id = kw.get('file_id', None)
        start_revid = h.fix_revid(kw.get('start_revid', None))
        query = kw.get('q', None)
        
        try:
            revid, start_revid, revid_list = h.get_view(revid, start_revid, file_id, query)
        except Exception, x:
            self.log.error('Exception fetching changes: %s' % (x,))
            util.log_exception(self.log)
            raise HTTPRedirect(self._branch.url('/changes'))
        
        navigation = util.Container(revid_list=revid_list, revid=revid, start_revid=start_revid, file_id=file_id,
                                    pagesize=1, scan_url='/revision', branch=self._branch, feed=True)
        if query is not None:
            navigation.query = query
        util.fill_in_navigation(h, navigation)

        change = h.get_changes([ revid ], get_diffs=True)[0]
        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks([ change ])
        
        vals = {
            'branch': self._branch,
            'revid': revid,
            'change': change,
            'start_revid': start_revid,
            'file_id': file_id,
            'util': util,
            'history': h,
            'navigation': navigation,
            'query': query,
        }
        h.flush_cache()
        self.log.info('/revision: %r seconds' % (time.time() - z,))
        return vals
