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
from StringIO import StringIO

import bzrlib.diff
from bzrlib import errors

from paste.httpexceptions import HTTPServerError

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView
from loggerhead.history import rich_filename


DEFAULT_LINE_COUNT_LIMIT = 3000


class RevisionUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.revision'

    def _process_diff(self, diff):
        # doesn't really need to be a method; could be static.
        chunks = []
        chunk = None
        for line in diff.splitlines():
            if len(line) == 0:
                continue
            if line.startswith('+++ ') or line.startswith('--- '):
                continue
            if line.startswith('@@ '):
                # new chunk
                if chunk is not None:
                    chunks.append(chunk)
                chunk = util.Container()
                chunk.diff = []
                split_lines = line.split(' ')[1:3]
                lines = [int(x.split(',')[0][1:]) for x in split_lines]
                old_lineno = lines[0]
                new_lineno = lines[1]
            elif line.startswith(' '):
                chunk.diff.append(util.Container(old_lineno=old_lineno,
                                                 new_lineno=new_lineno,
                                                 type='context',
                                                 line=line[1:]))
                old_lineno += 1
                new_lineno += 1
            elif line.startswith('+'):
                chunk.diff.append(util.Container(old_lineno=None,
                                                 new_lineno=new_lineno,
                                                 type='insert', line=line[1:]))
                new_lineno += 1
            elif line.startswith('-'):
                chunk.diff.append(util.Container(old_lineno=old_lineno,
                                                 new_lineno=None,
                                                 type='delete', line=line[1:]))
                old_lineno += 1
            else:
                chunk.diff.append(util.Container(old_lineno=None,
                                                 new_lineno=None,
                                                 type='unknown',
                                                 line=repr(line)))
        if chunk is not None:
            chunks.append(chunk)
        return chunks

    def _parse_diffs(self, old_tree, new_tree, delta, specific_path):
        """
        Return a list of processed diffs, in the format::

            list(
                filename: str,
                file_id: str,
                chunks: list(
                    diff: list(
                        old_lineno: int,
                        new_lineno: int,
                        type: str('context', 'delete', or 'insert'),
                        line: str,
                    ),
                ),
            )
        """
        process = []
        out = []

        def include_specific_path(path):
            return specific_path == path
        def include_all_paths(path):
            return True
        if specific_path:
            include_path = include_specific_path
        else:
            include_path = include_all_paths

        for old_path, new_path, fid, \
            kind, text_modified, meta_modified in delta.renamed:
            if text_modified and include_path(new_path):
                process.append((old_path, new_path, fid, kind))
        for path, fid, kind, text_modified, meta_modified in delta.modified:
            if include_path(path):
                process.append((path, path, fid, kind))
        for path, fid, kind in delta.added:
            if kind == 'file' and include_path(path):
                process.append((path, path, fid, kind))
        for path, fid, kind in delta.removed:
            if kind == 'file' and include_path(path):
                process.append((path, path, fid, kind))

        process.sort(key=lambda x:x[1])

        for old_path, new_path, fid, kind in process:
            try:
                old_lines = old_tree.get_file_lines(fid)
            except errors.NoSuchId:
                old_lines = []
            try:
                new_lines = new_tree.get_file_lines(fid)
            except errors.NoSuchId:
                new_lines = []
            buffer = StringIO()
            if old_lines != new_lines:
                try:
                    bzrlib.diff.internal_diff(old_path, old_lines,
                                              new_path, new_lines, buffer)
                except bzrlib.errors.BinaryFile:
                    diff = ''
                else:
                    diff = buffer.getvalue()
            else:
                diff = ''
            out.append(util.Container(
                filename=rich_filename(new_path, kind), file_id=fid,
                chunks=self._process_diff(diff)))

        return out

    def get_changes_with_diff(self, change, compare_revid, specific_path):
        h = self._history
        if compare_revid is None:
            if change.parents:
                compare_revid = change.parents[0].revid
            else:
                compare_revid = 'null:'

        rev_tree1 = h._branch.repository.revision_tree(compare_revid)
        rev_tree2 = h._branch.repository.revision_tree(change.revid)
        delta = rev_tree2.changes_from(rev_tree1)

        changes = h.parse_delta(delta)

        return changes, self._parse_diffs(
            rev_tree1, rev_tree2, delta, specific_path)

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
        if path in ('', '/'):
            path = None
        change.changes, diffs = self.get_changes_with_diff(change, compare_revid, path)
        link_data = {}
        path_to_id = {}
        if compare_revid is None:
            if change.parents:
                cr = change.parents[0].revid
            else:
                cr = 'null:'
        else:
            cr = compare_revid
        for i, item in enumerate(diffs):
            item.index = i
            link_data['diff-' + str(i)] = '%s/%s/%s' % (revid, cr, item.file_id)
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
            'diffs': diffs,
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
