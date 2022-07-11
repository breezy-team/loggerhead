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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

import json

from paste.httpexceptions import HTTPServerError

from breezy import urlutils

from .. import util
from ..controllers import TemplatedBranchView
from ..controllers.filediff_ui import diff_chunks_for_file


DEFAULT_LINE_COUNT_LIMIT = 3000


def dq(p):
    if not isinstance(p, bytes):
        p = p.encode('UTF-8')
    return urlutils.quote(urlutils.quote_from_bytes(p, safe=''))


class RevisionUI(TemplatedBranchView):

    template_name = 'revision'
    supports_json = True

    def get_values(self, path, kwargs, headers):
        h = self._history
        revid = self.get_revid()

        filter_path = kwargs.get('filter_path', None)
        start_revid = h.fix_revid(kwargs.get('start_revid', None))
        query = kwargs.get('q', None)
        compare_revid = h.fix_revid(kwargs.get('compare_revid', None))

        # TODO: This try/except looks to date before real exception handling
        # and should be removed
        try:
            revid, start_revid, revid_list = h.get_view(revid,
                                                        start_revid,
                                                        filter_path,
                                                        query)
        except BaseException:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')
        # XXX: Some concern about namespace collisions. These are only stored
        # here so they can be expanded into the template later. Should probably
        # be stored in a specific dict/etc.
        self.revid_list = revid_list
        self.compare_revid = compare_revid
        self.path = path
        kwargs['start_revid'] = start_revid

        change = h.get_changes([revid])[0]

        if compare_revid is None:
            file_changes = h.get_file_changes(change)
        else:
            file_changes = h.file_changes_for_revision_ids(
                compare_revid, change.revid)

        h.add_branch_nicks(change)

        if '.' in change.revno:
            # Walk "up" though the merge-sorted graph until we find a
            # revision with merge depth 0: this is the revision that merged
            # this one to mainline.
            ri = self._history._rev_info
            i = self._history._rev_indices[change.revid]
            while ri[i][0][2] > 0:
                i -= 1
            merged_in = ri[i][0][3]
        else:
            merged_in = None

        return {
            'revid': revid.decode('utf-8'),
            'change': change,
            'file_changes': file_changes,
            'merged_in': merged_in,
        }

    def add_template_values(self, values):
        super(RevisionUI, self).add_template_values(values)
        remember = self._history.fix_revid(self.kwargs.get('remember', None))
        query = self.kwargs.get('q', None)
        filter_path = self.kwargs.get('filter_path', None)
        start_revid = self.kwargs['start_revid']
        navigation = util.Container(
            revid_list=self.revid_list, revid=values['revid'],
            start_revid=start_revid,
            filter_path=filter_path, pagesize=1,
            scan_url='/revision', branch=self._branch, feed=True,
            history=self._history)
        if query is not None:
            navigation.query = query
        util.fill_in_navigation(navigation)
        path = self.path
        if path in ('', '/'):
            path = None

        file_changes = values['file_changes']
        link_data = {}
        path_to_id = {}
        if path:
            items = [x for x in file_changes.text_changes
                     if x.filename == path]
            if len(items) > 0:
                item = items[0]
                try:
                    context_lines = int(self.kwargs['context'])
                except (KeyError, ValueError):
                    context_lines = None
                diff_chunks = diff_chunks_for_file(
                    self._history._branch.repository, path,
                    item.old_revision, item.new_revision,
                    context_lines=context_lines)
            else:
                diff_chunks = None
        else:
            diff_chunks = None
            for i, item in enumerate(file_changes.text_changes):
                item.index = i
                link_data['diff-' + str(i)] = '%s/%s/%s' % (
                    dq(item.new_revision), dq(item.old_revision),
                    dq(item.filename))
                path_to_id[item.filename] = 'diff-' + str(i)

        # Directory Breadcrumbs
        directory_breadcrumbs = (
            util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'changes'))
        can_export = self._branch.export_tarballs

        values.update({
            'history': self._history,
            'link_data': json.dumps(link_data),
            'json_specific_path': json.dumps(path),
            'path_to_id': json.dumps(path_to_id),
            'directory_breadcrumbs': directory_breadcrumbs,
            'navigation': navigation,
            'remember': remember,
            'compare_revid': self.compare_revid,
            'filter_path': filter_path,
            'diff_chunks': diff_chunks,
            'query': query,
            'can_export': can_export,
            'specific_path': path,
            'start_revid': start_revid,
        })
