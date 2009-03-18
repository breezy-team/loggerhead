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

import simplejson
import urllib

from paste.httpexceptions import HTTPServerError

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView
from loggerhead.controllers.filediff_ui import diff_chunks_for_file


DEFAULT_LINE_COUNT_LIMIT = 3000

def dq(p):
    return urllib.quote(urllib.quote(p, safe=''))

class RevisionUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.revision'

    def get_values(self, path, kwargs, headers):
        h = self._history
        revid = self.get_revid()

        filter_file_id = kwargs.get('filter_file_id', None)
        start_revid = h.fix_revid(kwargs.get('start_revid', None))
        query = kwargs.get('q', None)
        remember = h.fix_revid(kwargs.get('remember', None))
        compare_revid = h.fix_revid(kwargs.get('compare_revid', None))

        try:
            revid, start_revid, revid_list = h.get_view(revid,
                                                        start_revid,
                                                        filter_file_id,
                                                        query)
        except:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')

        navigation = util.Container(
            revid_list=revid_list, revid=revid, start_revid=start_revid,
            filter_file_id=filter_file_id, pagesize=1,
            scan_url='/revision', branch=self._branch, feed=True, history=h)
        if query is not None:
            navigation.query = query
        util.fill_in_navigation(navigation)

        change = h.get_changes([revid])[0]

        if compare_revid is None:
            if change.parents:
                cr = change.parents[0].revid
            else:
                cr = 'null:'
        else:
            cr = compare_revid

        if path in ('', '/'):
            path = None

        old_tree = h._branch.repository.revision_tree(cr)
        new_tree = h._branch.repository.revision_tree(change.revid)
        delta = new_tree.changes_from(old_tree)
        change.changes = h.parse_delta(delta)

        link_data = {}
        path_to_id = {}
        if path:
            diff_chunks = diff_chunks_for_file(
                new_tree.path2id(path), old_tree, new_tree)
        else:
            diff_chunks = None
            for i, item in enumerate(change.changes.text_changes):
                item.index = i
                link_data['diff-' + str(i)] = '%s/%s/%s' % (
                    dq(revid), dq(cr), dq(item.file_id))
                path_to_id[item.filename] = 'diff-' + str(i)

        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks([change])

        # Directory Breadcrumbs
        directory_breadcrumbs = (
            util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'changes'))

        return {
            'branch': self._branch,
            'revid': revid,
            'change': change,
            'diff_chunks': diff_chunks,
            'link_data': simplejson.dumps(link_data),
            'specific_path': path,
            'json_specific_path': simplejson.dumps(path),
            'path_to_id': simplejson.dumps(path_to_id),
            'start_revid': start_revid,
            'filter_file_id': filter_file_id,
            'util': util,
            'history': h,
            'navigation': navigation,
            'query': query,
            'remember': remember,
            'compare_revid': compare_revid,
            'url': self._branch.context_url,
            'directory_breadcrumbs': directory_breadcrumbs,
        }
