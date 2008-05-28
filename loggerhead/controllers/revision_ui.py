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

import time

import turbogears
from cherrypy import InternalError

from loggerhead import util
from loggerhead.templatefunctions import templatefunctions


DEFAULT_LINE_COUNT_LIMIT = 3000


class RevisionUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log
    
#    @util.lsprof
    @util.strip_whitespace
    @turbogears.expose(html='zpt:loggerhead.templates.revision')
    def default(self, *args, **kw):
        z = time.time()
        h = self._branch.get_history()
        util.set_context(kw)
        
        h._branch.lock_read()
        try:
            if len(args) > 0:
                revid = h.fix_revid(args[0])
            else:
                revid = None

            filter_file_id = kw.get('filter_file_id', None)
            start_revid = h.fix_revid(kw.get('start_revid', None))
            query = kw.get('q', None)
            remember = kw.get('remember', None)
            compare_revid = kw.get('compare_revid', None)

            try:
                revid, start_revid, revid_list = h.get_view(revid, start_revid, filter_file_id, query)
            except:
                self.log.exception('Exception fetching changes')
                raise InternalError('Could not fetch changes')

            navigation = util.Container(
                revid_list=revid_list, revid=revid, start_revid=start_revid,
                filter_file_id=filter_file_id, pagesize=1,
                scan_url='/revision', branch=self._branch, feed=True)
            if query is not None:
                navigation.query = query
            util.fill_in_navigation(navigation)

            change = h.get_change_with_diff(revid, compare_revid)
            # add parent & merge-point branch-nick info, in case it's useful
            h.get_branch_nicks([ change ])

            line_count_limit = int(self._branch.get_config_item(
                'line_count_limit', DEFAULT_LINE_COUNT_LIMIT))
            line_count = 0
            for file in change.changes.modified:
                for chunk in file.chunks:
                    line_count += len(chunk.diff)

            # let's make side-by-side diff be the default
            side_by_side = not kw.get('unified', False)
            if side_by_side:
                h.add_side_by_side([ change ])

            def url(pathargs, **kw):
                return self._branch.url(pathargs, **util.get_context(**kw))

            vals = {
                'branch': self._branch,
                'revid': revid,
                'change': change,
                'start_revid': start_revid,
                'filter_file_id': filter_file_id,
                'util': util,
                'history': h,
                'navigation': navigation,
                'query': query,
                'remember': remember,
                'compare_revid': compare_revid,
                'side_by_side': side_by_side,
                'url': url,
                'line_count': line_count,
                'line_count_limit': line_count_limit,
                'show_plain_diffs': line_count > line_count_limit,
            }
            vals.update(templatefunctions)
            h.flush_cache()
            self.log.info('/revision: %r seconds' % (time.time() - z,))
            return vals
        finally:
            h._branch.unlock()
