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

import os
import time

import turbogears
from cherrypy import InternalError, session

from loggerhead import util


class ChangeLogUI (object):
    
    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log
        
    @util.strip_whitespace
    @turbogears.expose(html='loggerhead.templates.changelog')
    def default(self, *args, **kw):
        z = time.time()
        h = self._branch.get_history()
        config = self._branch.config
        
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = None

        file_id = kw.get('file_id', None)
        query = kw.get('q', None)
        start_revid = h.fix_revid(kw.get('start_revid', None))
        orig_start_revid = start_revid
        pagesize = int(config.get('pagesize', '20'))
        search_failed = False
        
        try:
            revid, start_revid, revid_list = h.get_view(revid, start_revid, file_id, query)
            kw['start_revid'] = start_revid
            util.set_context(kw)
            
            if (query is not None) and (len(revid_list) == 0):
                search_failed = True

            if len(revid_list) == 0:
                scan_list = revid_list
            else:
                if revid in revid_list: # XXX is this always true?
                    i = revid_list.index(revid)
                else:
                    i = None
                scan_list = revid_list[i:]
            entry_list = scan_list[:pagesize]
            entries = h.get_changes(entry_list)
            h.add_changes(entries)
        except:
            self.log.exception('Exception fetching changes')
            raise InternalError('Could not fetch changes')

        navigation = util.Container(pagesize=pagesize, revid=revid, start_revid=start_revid, revid_list=revid_list,
                                    file_id=file_id, scan_url='/changes', branch=self._branch, feed=True)
        if query is not None:
            navigation.query = query
        util.fill_in_navigation(navigation)
        
        entries = list(entries)
        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks(entries)
        
        # does every change on this page have the same committer?  if so,
        # tell the template to show committer info in the "details block"
        # instead of on each line.
        all_same_author = True

        if entries:
            author = entries[0].author
            for e in entries[1:]:
                if e.author != author:
                    all_same_author = False
                    break

        vals = {
            'branch': self._branch,
            'changes': entries,
            'util': util,
            'history': h,
            'revid': revid,
            'navigation': navigation,
            'file_id': file_id,
            'start_revid': start_revid,
            'viewing_from': (orig_start_revid is not None) and (orig_start_revid != h.last_revid),
            'query': query,
            'search_failed': search_failed,
            'all_same_author': all_same_author,
        }
        h.flush_cache()
        self.log.info('/changes %r: %r secs' % (revid, time.time() - z))
        return vals
