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

import cgi
import datetime
import textwrap
from StringIO import StringIO

import bzrlib
import bzrlib.branch
import bzrlib.diff
import bzrlib.errors
import bzrlib.textfile
import bzrlib.tsort

from loggerhead import util


class History (object):
    
    def __init__(self):
        pass

    @classmethod
    def from_branch(cls, branch):
        self = cls()
        self._branch = branch
        self._history = branch.revision_history()
        self._revision_graph = branch.repository.get_revision_graph()
        self._last_revid = self._history[-1]
        
        self._full_history = []
        self._revision_info = {}
        self._revno_revid = {}
        self._merge_sort = bzrlib.tsort.merge_sort(self._revision_graph, self._last_revid, generate_revno=True)
        count = 0
        for (seq, revid, merge_depth, revno, end_of_merge) in self._merge_sort:
            self._full_history.append(revid)
            revno_str = '.'.join(str(n) for n in revno)
            self._revno_revid[revno_str] = revid
            self._revision_info[revid] = (seq, revid, merge_depth, revno_str, end_of_merge)
            count += 1
        self._count = count

        # cache merge info
        self._where_merged = {}
        for revid in self._revision_graph.keys():
            if not revid in self._full_history: 
                continue
            for parent in self._revision_graph[revid]:
                self._where_merged.setdefault(parent, set()).add(revid)

        return self
    
    @classmethod
    def from_folder(cls, path):
        b = bzrlib.branch.Branch.open(path)
        return cls.from_branch(b)
    
    last_revid = property(lambda self: self._last_revid, None, None)
    
    count = property(lambda self: self._count, None, None)
    
    def get_revision(self, revid):
        return self._branch.repository.get_revision(revid)
    
    def get_revno(self, revid):
        seq, revid, merge_depth, revno_str, end_of_merge = self._revision_info[revid]
        return revno_str

    def get_sequence(self, revid):
        seq, revid, merge_depth, revno_str, end_of_merge = self._revision_info[revid]
        return seq
        
    def get_short_revision_history(self):
        return self.get_short_revision_history_from(self._last_revid)
    
    def get_short_revision_history_from(self, revid):
        """return the short revision_history, starting from revid"""
        while True:
            yield revid
            if not self._revision_graph.has_key(revid):
                return
            parents = self._revision_graph[revid]
            if len(parents) == 0:
                return
            revid = self._revision_graph[revid][0]

    def get_where_merged(self, revid):
        try:
            return self._where_merged[revid]
        except:
            return []

    def get_merge_point_list(self, revid):
        """
        Return the list of revids that have merged this node.
        """
        if revid in self._history:
            return []
        
        merge_point = []
        while True:
            children = self.get_where_merged(revid)
            nexts = []
            for child in children:
                child_parents = self._revision_graph[child]
                if child_parents[0] == revid:
                    nexts.append(child)
                else:
                    merge_point.append(child)

            if len(nexts) == 0:
                # only merge
                return merge_point

            while len(nexts) > 1:
                # branch
                next = nexts.pop()
                merge_point_next = self.get_merge_point_list(next)
                merge_point.extend(merge_point_next)

            revid = nexts[0]
            
    def simplify_merge_point_list(self, revids):
        """if a revision is already merged, don't show further merge points"""
        d = {}
        for revid in revids:
            revno = self.get_revno(revid)
            revnol = revno.split(".")
            revnos = ".".join(revnol[:-2])
            revnolast = int(revnol[-1])
            if d.has_key(revnos):
                m = d[revnos][0]
                if revnolast < m:
                    d[revnos] = ( revnolast, revid )
            else:
                d[revnos] = ( revnolast, revid )

        return [ d[revnos][1] for revnos in d.keys() ]
            
    def get_changelist(self, revid_list):
        for revid in revid_list:
            yield self.get_change(revid)
    
    def get_change(self, revid, parity=0):
        try:
            rev = self._branch.repository.get_revision(revid)
        except (KeyError, bzrlib.errors.NoSuchRevision):
            # ghosted parent?
            entry = {
                'revid': 'missing',
                'revno': '',
                'date': datetime.datetime.fromtimestamp(0),
                'author': 'missing',
                'age': 'unknown',
                'short_comment': 'missing',
                'parents': [],
            }
            return util.Container(entry)
            
        now = datetime.datetime.now()
        commit_time = datetime.datetime.fromtimestamp(rev.timestamp)
        
        # make short form of commit message
        short_comment = rev.message.splitlines(1)[0]
        if len(short_comment) >= 80:
            short_comment = textwrap.wrap(short_comment)[0] + '...'
        
        parents = [{
            'revid': parent_revid,
            'revno': self.get_revno(parent_revid),
        } for parent_revid in rev.parent_ids]

        if len(parents) == 0:
            left_parent = None
        else:
            left_parent = rev.parent_ids[-1]
            
        entry = {
            'revid': revid,
            'revno': self.get_revno(revid),
            'date': commit_time,
            'author': rev.committer,
            'age': util.timespan(now - commit_time) + ' ago',
            'short_comment': short_comment,
            'comment': rev.message,
            'comment_clean': util.html_clean(rev.message),
            'parents': [util.Container(p) for p in parents],
            'changes': self.diff_revisions(revid, left_parent, get_diffs=False),
        }
        return util.Container(entry)
    
    def scan_range(self, revid, pagesize=20):
        """
        yield a list of (label, title, revid) for a scan range through the full
        branch history, centered around the given revid.
        
        example: [ ('(1)', 'Oldest', 'first-revid'), ('-300', 'Back 300', '...'), ... ]
        """
        count = self._count
        pos = self.get_sequence(revid)
        if pos < count - 1:
            yield ('<', 'Back %d' % (pagesize,),
                   self._full_history[min(count - 1, pos + pagesize)])
        else:
            yield ('<', None, None)
        yield ('(1)', 'Oldest', self._full_history[-1])
        for offset in reversed([-x for x in util.scan_range(pos, count)]):
            if offset < 0:
                title = 'Back %d' % (-offset,)
            else:
                title = 'Forward %d' % (offset,)
            yield ('%+d' % (offset,), title, self._full_history[pos - offset])
        if pos > 0:
            yield ('>', 'Forward %d' % (pagesize,),
                   self._full_history[max(0, pos - pagesize)])
        else:
            yield ('>', None, None)
    
    def diff_revisions(self, revid, otherrevid, get_diffs=True):
        """
        Return a nested data structure containing the changes between two
        revisions::
        
            added: list(filename),
            renamed: list((old_filename, new_filename)),
            deleted: list(filename),
            modified: list(
                filename: str,
                chunks: list(
                    diff: list(
                        old_lineno: int,
                        new_lineno: int,
                        type: str('context', 'delete', or 'insert'),
                        line: str,
                    ),
                ),
            )
        
        if C{get_diffs} is false, the C{chunks} will be omitted.
        """

        new_tree = self._branch.repository.revision_tree(revid)
        old_tree = self._branch.repository.revision_tree(otherrevid)
        delta = new_tree.changes_from(old_tree)
        
        added = []
        modified = []
        renamed = []
        removed = []
        
        def rich_filename(path, kind):
            if kind == 'directory':
                path += '/'
            if kind == 'symlink':
                path += '@'
            return path
        
        def tree_lines(tree, fid):
            if not fid in tree:
                return []
            tree_file = bzrlib.textfile.text_file(tree.get_file(fid))
            return tree_file.readlines()
        
        def process_diff(diff):
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
                    lines = [int(x.split(',')[0][1:]) for x in line.split(' ')[1:3]]
                    old_lineno = lines[0]
                    new_lineno = lines[1]
                elif line.startswith('  '):
                    chunk.diff.append(util.Container(old_lineno=old_lineno, new_lineno=new_lineno,
                                                     type='context', line=util.html_clean(line[2:])))
                    old_lineno += 1
                    new_lineno += 1
                elif line.startswith('+ '):
                    chunk.diff.append(util.Container(old_lineno=None, new_lineno=new_lineno,
                                                     type='insert', line=util.html_clean(line[2:])))
                    new_lineno += 1
                elif line.startswith('- '):
                    chunk.diff.append(util.Container(old_lineno=old_lineno, new_lineno=None,
                                                     type='delete', line=util.html_clean(line[2:])))
                    old_lineno += 1
                elif line.startswith(' '):
                    # why does this happen?
                    chunk.diff.append(util.Container(old_lineno=old_lineno, new_lineno=new_lineno,
                                                     type='context', line=util.html_clean(line[1:])))
                    old_lineno += 1
                    new_lineno += 1
                elif line.startswith('+'):
                    # why does this happen?
                    chunk.diff.append(util.Container(old_lineno=None, new_lineno=new_lineno,
                                                     type='insert', line=util.html_clean(line[1:])))
                    new_lineno += 1
                elif line.startswith('-'):
                    # why does this happen?
                    chunk.diff.append(util.Container(old_lineno=old_lineno, new_lineno=None,
                                                     type='delete', line=util.html_clean(line[1:])))
                    old_lineno += 1
                else:
                    chunk.diff.append(util.Container(old_lineno=None, new_lineno=None,
                                                     type='unknown', line=util.html_clean(repr(line))))
            if chunk is not None:
                chunks.append(chunk)
            return chunks
                    
        def handle_modify(old_path, new_path, fid, kind):
            if not get_diffs:
                modified.append(util.Container(filename=rich_filename(new_path, kind)))
                return
            old_lines = tree_lines(old_tree, fid)
            new_lines = tree_lines(new_tree, fid)
            buffer = StringIO()
            bzrlib.diff.internal_diff(old_path, old_lines, new_path, new_lines, buffer)
            diff = buffer.getvalue()
            modified.append(util.Container(filename=rich_filename(new_path, kind), chunks=process_diff(diff)))

        for path, fid, kind in delta.added:
            added.append(rich_filename(path, kind))
        
        for path, fid, kind, text_modified, meta_modified in delta.modified:
            handle_modify(path, path, fid, kind)
        
        for oldpath, newpath, fid, kind, text_modified, meta_modified in delta.renamed:
            renamed.append((rich_filename(oldpath, kind), rich_filename(newpath, kind)))
            if meta_modified or text_modified:
                handle_modify(oldpath, newpath, fid, kind)
        
        for path, fid, kind in delta.removed:
            removed.append(rich_filename(path, kind))
        
        return util.Container(added=added, renamed=renamed, removed=removed, modified=modified)
