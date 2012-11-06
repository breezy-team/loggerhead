#
# Copyright (C) 2008, 2009 Canonical Ltd.
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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

import urllib

import simplejson

from paste.httpexceptions import HTTPServerError

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView


class ChangeLogUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.changelog'

    def get_values(self, path, kwargs, headers):
        history = self._history
        revid = self.get_revid()
        filter_file_id = kwargs.get('filter_file_id', None)
        query = kwargs.get('q', None)
        start_revid = history.fix_revid(kwargs.get('start_revid', None))
        orig_start_revid = start_revid
        pagesize = 20#int(config.get('pagesize', '20'))
        search_failed = False

        if filter_file_id is None and path is not None:
            filter_file_id = history.get_file_id(revid, path)

        try:
            revid, start_revid, revid_list = history.get_view(
                revid, start_revid, filter_file_id, query,
                extra_rev_count=pagesize+1)
            util.set_context(kwargs)

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
            change_list = scan_list[:pagesize]
            changes = list(history.get_changes(change_list))
            data = {}
            for i, c in enumerate(changes):
                c.index = i
                data[str(i)] = urllib.quote(urllib.quote(c.revid, safe=''))
        except:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')

        navigation = util.Container(
            pagesize=pagesize, revid=revid, start_revid=start_revid,
            revid_list=revid_list, filter_file_id=filter_file_id,
            scan_url='/changes', branch=self._branch, feed=True, history=history)
        if query is not None:
            navigation.query = query
        util.fill_in_navigation(navigation)

        # Directory Breadcrumbs
        directory_breadcrumbs = (
            util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'changes'))

        show_tag_col = False
        for change in changes:
            if change.tags is not None:
                show_tag_col = True
                break

        return {
            'branch': self._branch,
            'changes': changes,
            'show_tag_col': show_tag_col,
            'data': simplejson.dumps(data),
            'util': util,
            'history': history,
            'revid': revid,
            'navigation': navigation,
            'filter_file_id': filter_file_id,
            'start_revid': start_revid,
            'viewing_from': (orig_start_revid is not None) and
                            (orig_start_revid != history.last_revid),
            'query': query,
            'search_failed': search_failed,
            'url': self._branch.context_url,
            'directory_breadcrumbs': directory_breadcrumbs,
        }
