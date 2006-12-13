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
import posixpath
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
        if revid not in self._revision_info:
            # ghost parent?
            return 'unknown'
        seq, revid, merge_depth, revno_str, end_of_merge = self._revision_info[revid]
        return revno_str

    def get_sequence(self, revid):
        seq, revid, merge_depth, revno_str, end_of_merge = self._revision_info[revid]
        return seq
    
    def get_revision_history(self):
        return self._full_history
    
    def get_revid_sequence(self, revid_list, revid):
        """
        given a list of revision ids, return the sequence # of this revid in
        the list.
        """
        seq = 0
        for r in revid_list:
            if revid == r:
                return seq
            seq += 1
    
    def get_revids_from(self, revid_list, revid):
        """
        given a list of revision ids, yield revisions in graph order,
        starting from revid.  the list can be None if you just want to travel
        across all revisions.
        """
        while True:
            if (revid_list is None) or (revid in revid_list):
                yield revid
            if not self._revision_graph.has_key(revid):
                return
            parents = self._revision_graph[revid]
            if len(parents) == 0:
                return
            revid = parents[0]
        
    def get_short_revision_history_by_fileid(self, file_id):
        # wow.  is this really the only way we can get this list?  by
        # man-handling the weave store directly? :-0
        # FIXME: would be awesome if we could get, for a folder, the list of
        # revisions where items within that folder changed.
        w = self._branch.repository.weave_store.get_weave(file_id, self._branch.repository.get_transaction())
        w_revids = w.versions()
        revids = [r for r in self._full_history if r in w_revids]
        return revids

    def get_navigation(self, revid, path):
        """
        Given an optional revid and optional path, return a (revlist, revid)
        for navigation through the current scope.
        
        If path is None, the entire revision history is the list scope.
        If revid is None, the latest revid is used.
        """
        if path is not None:
            inv = self._branch.repository.get_revision_inventory(revid)
            revlist = list(self.get_short_revision_history_by_fileid(inv.path2id(path)))
        else:
            revlist = self._full_history
        if revid is None:
            revid = revlist[0]
        return revlist, revid

    def get_inventory(self, revid):
        return self._branch.repository.get_revision_inventory(revid)

    def get_where_merged(self, revid):
        try:
            return self._where_merged[revid]
        except:
            return []
    
    def get_left_child(self, revid):
        for r in self.get_where_merged(revid):
            if self._revision_graph[r][0] == revid:
                return r
        return None

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
    
    def get_change(self, revid, get_diffs=False):
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
        
        parents = [util.Container(revid=r, revno=self.get_revno(r)) for r in rev.parent_ids]

        merge_revids = self.simplify_merge_point_list(self.get_merge_point_list(revid))
        merge_points = [util.Container(revid=r, revno=self.get_revno(r)) for r in merge_revids]
        
        if len(parents) == 0:
            left_parent = None
        else:
            left_parent = rev.parent_ids[0]
        
        message = rev.message.splitlines()
        if len(message) == 1:
            # robey-style 1-line long message
            message = textwrap.wrap(message[0])
        
        # make short form of commit message
        short_message = message[0]
        if len(short_message) > 60:
            short_message = short_message[:60] + '...'

        entry = {
            'revid': revid,
            'revno': self.get_revno(revid),
            'date': commit_time,
            'author': rev.committer,
            'age': util.timespan(now - commit_time) + ' ago',
            'short_comment': short_message,
            'comment': rev.message,
            'comment_clean': [util.html_clean(s) for s in message],
            'parents': parents,
            'merge_points': merge_points,
            'left_child': self.get_left_child(revid),
            'changes': self.diff_revisions(revid, left_parent, get_diffs=get_diffs),
        }
        return util.Container(entry)
    
    def scan_range(self, revlist, revid, pagesize=20):
        """
        yield a list of (label, title, revid) for a scan range through the full
        branch history, centered around the given revid.
        
        example: [ ('(425)', 'Latest', 'rrrr'), ('+1', 'Forward 1', 'rrrr'), ...
                   ('-300', 'Back 300', 'rrrr'), ('(1)', 'Oldest', 'first-revid') ]
        """
        count = len(revlist)
        pos = self.get_revid_sequence(revlist, revid)
        if pos < count - 1:
            yield ('<', 'Back %d' % (pagesize,),
                   revlist[min(count - 1, pos + pagesize)])
        else:
            yield ('<', None, None)
        yield ('(1)', 'Oldest', revlist[-1])
        for offset in reversed([-x for x in util.scan_range(pos, count)]):
            if offset < 0:
                title = 'Back %d' % (-offset,)
            else:
                title = 'Forward %d' % (offset,)
            yield ('%+d' % (offset,), title, revlist[pos - offset])
        yield ('(%d)' % (len(revlist),) , 'Latest', revlist[0])
        if pos > 0:
            yield ('>', 'Forward %d' % (pagesize,),
                   revlist[max(0, pos - pagesize)])
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

    def get_filelist(self, inv, path):
        """
        return the list of all files (and their attributes) within a given
        path subtree.
        """
        while path.endswith('/'):
            path = path[:-1]
        if path.startswith('/'):
            path = path[1:]
        parity = 0
        for filepath, entry in inv.entries():
            if posixpath.dirname(filepath) != path:
                continue
            filename = posixpath.basename(filepath)
            rich_filename = filename
            pathname = filename
            if entry.kind == 'directory':
                pathname += '/'
            
            # last change:
            revid = entry.revision
            
            yield util.Container(filename=filename, rich_filename=rich_filename, executable=entry.executable, kind=entry.kind,
                                 pathname=pathname, revid=revid, revno=self.get_revno(revid), parity=parity)
            parity ^= 1
        pass

