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

import re
from StringIO import StringIO

import bzrlib.diff

from paste.httpexceptions import HTTPServerError

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView
from loggerhead.history import rich_filename


DEFAULT_LINE_COUNT_LIMIT = 3000

def _process_side_by_side_buffers(line_list, delete_list, insert_list):
    while len(delete_list) < len(insert_list):
        delete_list.append((None, '', 'context'))
    while len(insert_list) < len(delete_list):
        insert_list.append((None, '', 'context'))
    while len(delete_list) > 0:
        d = delete_list.pop(0)
        i = insert_list.pop(0)
        line_list.append(util.Container(old_lineno=d[0], new_lineno=i[0],
                                        old_line=d[1], new_line=i[1],
                                        old_type=d[2], new_type=i[2]))


def _make_side_by_side(chunk_list):
    """
    turn a normal unified-style diff (post-processed by parse_delta) into a
    side-by-side diff structure.  the new structure is::

        chunks: list(
            diff: list(
                old_lineno: int,
                new_lineno: int,
                old_line: str,
                new_line: str,
                type: str('context' or 'changed'),
            )
        )
    """
    out_chunk_list = []
    for chunk in chunk_list:
        line_list = []
        wrap_char = '<wbr/>'
        delete_list, insert_list = [], []
        for line in chunk.diff:
            # Add <wbr/> every X characters so we can wrap properly
            wrap_line = re.findall(r'.{%d}|.+$' % 78, line.line)
            wrap_lines = [util.html_clean(_line) for _line in wrap_line]
            wrapped_line = wrap_char.join(wrap_lines)

            if line.type == 'context':
                if len(delete_list) or len(insert_list):
                    _process_side_by_side_buffers(line_list, delete_list,
                                                  insert_list)
                    delete_list, insert_list = [], []
                line_list.append(util.Container(old_lineno=line.old_lineno,
                                                new_lineno=line.new_lineno,
                                                old_line=wrapped_line,
                                                new_line=wrapped_line,
                                                old_type=line.type,
                                                new_type=line.type))
            elif line.type == 'delete':
                delete_list.append((line.old_lineno, wrapped_line, line.type))
            elif line.type == 'insert':
                insert_list.append((line.new_lineno, wrapped_line, line.type))
        if len(delete_list) or len(insert_list):
            _process_side_by_side_buffers(line_list, delete_list, insert_list)
        out_chunk_list.append(util.Container(diff=line_list))
    return out_chunk_list

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

    def _parse_diffs(self, old_tree, new_tree, delta):
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

        for old_path, new_path, fid, \
            kind, text_modified, meta_modified in delta.renamed:
            if text_modified:
                process.append((old_path, new_path, fid, kind))
        for path, fid, kind, text_modified, meta_modified in delta.modified:
            process.append((path, path, fid, kind))

        for old_path, new_path, fid, kind in process:
            old_lines = old_tree.get_file_lines(fid)
            new_lines = new_tree.get_file_lines(fid)
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
                          filename=rich_filename(new_path, kind),
                          file_id=fid,
                          chunks=self._process_diff(diff),
                          raw_diff=diff))

        return out

    def get_change_with_diff(self, revid, compare_revid):
        h = self._history
        change = h.get_changes([revid])[0]

        if compare_revid is None:
            if change.parents:
                compare_revid = change.parents[0].revid
            else:
                compare_revid = 'null:'

        rev_tree1 = h._branch.repository.revision_tree(compare_revid)
        rev_tree2 = h._branch.repository.revision_tree(revid)
        delta = rev_tree2.changes_from(rev_tree1)

        change.changes = h.parse_delta(delta)
        change.changes.modified = self._parse_diffs(rev_tree1,
                                                    rev_tree2,
                                                    delta)

        return change

    @staticmethod
    def add_side_by_side(changes):
        # FIXME: this is a rotten API.
        for change in changes:
            for m in change.changes.modified:
                m.sbs_chunks = _make_side_by_side(m.chunks)

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

        change = self.get_change_with_diff(revid, compare_revid)
        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks([change])

        line_count_limit = DEFAULT_LINE_COUNT_LIMIT
        line_count = 0
        for file in change.changes.modified:
            for chunk in file.chunks:
                line_count += len(chunk.diff)

        # let's make side-by-side diff be the default
        # FIXME: not currently in use. Should be
        side_by_side = not kwargs.get('unified', False)
        if side_by_side:
            self.add_side_by_side([change])

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
            'start_revid': start_revid,
            'filter_file_id': filter_file_id,
            'util': util,
            'history': h,
            'navigation': navigation,
            'query': query,
            'remember': remember,
            'compare_revid': compare_revid,
            'side_by_side': side_by_side,
            'url': self._branch.context_url,
            'line_count': line_count,
            'line_count_limit': line_count_limit,
            'show_plain_diffs': line_count > line_count_limit,
            'directory_breadcrumbs': directory_breadcrumbs,
        }
