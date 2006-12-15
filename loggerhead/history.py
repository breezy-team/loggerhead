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
import logging
import os
import posixpath
import shelve
import sys
import textwrap
import threading
import time
from StringIO import StringIO

import turbogears
sys.path.insert(0, turbogears.config.get('loggerhead.bzrpath', ''))

import bzrlib
import bzrlib.annotate
import bzrlib.branch
import bzrlib.diff
import bzrlib.errors
import bzrlib.progress
import bzrlib.textfile
import bzrlib.tsort
import bzrlib.ui

from loggerhead import util

log = logging.getLogger("loggerhead.controllers")


# cache lock binds tighter than branch lock
def with_cache_lock(unbound):
    def cache_locked(self, *args, **kw):
        self._cache_lock.acquire()
        try:
            return unbound(self, *args, **kw)
        finally:
            self._cache_lock.release()
    cache_locked.__doc__ = unbound.__doc__
    cache_locked.__name__ = unbound.__name__
    return cache_locked


def with_branch_lock(unbound):
    def branch_locked(self, *args, **kw):
        self._lock.acquire()
        try:
            return unbound(self, *args, **kw)
        finally:
            self._lock.release()
    branch_locked.__doc__ = unbound.__doc__
    branch_locked.__name__ = unbound.__name__
    return branch_locked


# bzrlib's UIFactory is not thread-safe
uihack = threading.local()

class ThreadSafeUIFactory (bzrlib.ui.SilentUIFactory):
    def nested_progress_bar(self):
        if getattr(uihack, '_progress_bar_stack', None) is None:
            uihack._progress_bar_stack = bzrlib.progress.ProgressBarStack(klass=bzrlib.progress.DummyProgress)
        return uihack._progress_bar_stack.get_nested()

bzrlib.ui.ui_factory = ThreadSafeUIFactory()


class History (object):
    
    def __init__(self):
        self._change_cache = None
        self._cache_lock = threading.Lock()
        self._lock = threading.RLock()
    
    def __del__(self):
        if self._change_cache is not None:
            self._change_cache.close()
            self._change_cache_diffs.close()
            self._change_cache = None
            self._change_cache_diffs = None

    @classmethod
    def from_branch(cls, branch):
        z = time.time()
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

        log.info('built revision graph cache: %r secs' % (time.time() - z,))
        return self
    
    @classmethod
    def from_folder(cls, path):
        b = bzrlib.branch.Branch.open(path)
        return cls.from_branch(b)

    @with_branch_lock
    def out_of_date(self):
        if self._branch.revision_history()[-1] != self._last_revid:
            return True
        return False

    @with_cache_lock
    def use_cache(self, path):
        if not os.path.exists(path):
            os.mkdir(path)
        # keep a separate cache for the diffs, because they're very time-consuming to fetch.
        cachefile = os.path.join(path, 'changes')
        cachefile_diffs = os.path.join(path, 'changes-diffs')
        
        # why can't shelve allow 'cw'?
        if not os.path.exists(cachefile):
            self._change_cache = shelve.open(cachefile, 'c', protocol=2)
        else:
            self._change_cache = shelve.open(cachefile, 'w', protocol=2)
        if not os.path.exists(cachefile_diffs):
            self._change_cache_diffs = shelve.open(cachefile_diffs, 'c', protocol=2)
        else:
            self._change_cache_diffs = shelve.open(cachefile_diffs, 'w', protocol=2)
            
        # once we process a change (revision), it should be the same forever.
        log.info('Using change cache %s; %d, %d entries.' % (path, len(self._change_cache), len(self._change_cache_diffs)))
        self._change_cache_filename = cachefile
        self._change_cache_diffs_filename = cachefile_diffs

    @with_cache_lock
    def dont_use_cache(self):
        # called when a new history object needs to be created.  we can't use
        # the cache files anymore; they belong to the new history object.
        if self._change_cache is None:
            return
        self._change_cache.close()
        self._change_cache_diffs.close()
        self._change_cache = None
        self._change_cache_diffs = None

    @with_cache_lock
    def flush_cache(self):
        if self._change_cache is None:
            return
        self._change_cache.sync()
        self._change_cache_diffs.sync()
    
    last_revid = property(lambda self: self._last_revid, None, None)
    
    count = property(lambda self: self._count, None, None)

    @with_branch_lock
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

    @with_branch_lock
    def get_short_revision_history_by_fileid(self, file_id):
        # wow.  is this really the only way we can get this list?  by
        # man-handling the weave store directly? :-0
        # FIXME: would be awesome if we could get, for a folder, the list of
        # revisions where items within that folder changed.
        w = self._branch.repository.weave_store.get_weave(file_id, self._branch.repository.get_transaction())
        w_revids = w.versions()
        revids = [r for r in self._full_history if r in w_revids]
        return revids

    @with_branch_lock
    def get_navigation(self, revid, path):
        """
        Given an optional revid and optional path, return a (revlist, revid)
        for navigation through the current scope: from the revid (or the
        latest revision) back to the original revision.
        
        If path is None, the entire revision history is the list scope.
        If revid is None, the latest revision is used.
        """
        if revid is None:
            revid = self._last_revid
        if path is not None:
            # since revid is 'start_revid', possibly should start the path tracing from revid... FIXME
            inv = self._branch.repository.get_revision_inventory(revid)
            revlist = list(self.get_short_revision_history_by_fileid(inv.path2id(path)))
        else:
            revlist = list(self.get_revids_from(None, revid))
        if revid is None:
            revid = revlist[0]
        return revlist, revid

    @with_branch_lock
    def get_inventory(self, revid):
        return self._branch.repository.get_revision_inventory(revid)

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
    
    @with_branch_lock
    def get_change(self, revid, get_diffs=False):
        if self._change_cache is None:
            return self._get_change(revid, get_diffs)

        # if the revid is in unicode, use the utf-8 encoding as the key
        srevid = revid
        if isinstance(revid, unicode):
            srevid = revid.encode('utf-8')
        return self._get_change_from_cache(revid, srevid, get_diffs)

    @with_cache_lock
    def _get_change_from_cache(self, revid, srevid, get_diffs):
        if get_diffs:
            cache = self._change_cache_diffs
        else:
            cache = self._change_cache
            
        if srevid in cache:
            c = cache[srevid]
        else:
            if get_diffs and (srevid in self._change_cache):
                # salvage the non-diff entry for a jump-start
                c = self._change_cache[srevid]
                if len(c.parents) == 0:
                    left_parent = None
                else:
                    left_parent = c.parents[0].revid
                c.changes = self.diff_revisions(revid, left_parent, get_diffs=True)
                cache[srevid] = c
            else:
                #log.debug('Entry cache miss: %r' % (revid,))
                c = self._get_change(revid, get_diffs=get_diffs)
                cache[srevid] = c
            
        # some data needs to be recalculated each time, because it may
        # change as new revisions are added.
        merge_revids = self.simplify_merge_point_list(self.get_merge_point_list(revid))
        c.merge_points = [util.Container(revid=r, revno=self.get_revno(r)) for r in merge_revids]
        
        return c
    
    # alright, let's profile this sucka.
    def _get_change_profiled(self, revid, get_diffs=False):
        from loggerhead.lsprof import profile
        import cPickle
        ret, stats = profile(self._get_change, revid, get_diffs)
        stats.sort()
        stats.freeze()
        cPickle.dump(stats, open('lsprof.stats', 'w'), 2)
        return ret

    def _get_change(self, revid, get_diffs=False):
        try:
            rev = self._branch.repository.get_revision(revid)
        except (KeyError, bzrlib.errors.NoSuchRevision):
            # ghosted parent?
            entry = {
                'revid': 'missing',
                'revno': '',
                'date': datetime.datetime.fromtimestamp(0),
                'author': 'missing',
                'branch_nick': None,
                'short_comment': 'missing',
                'comment': 'missing',
                'comment_clean': 'missing',
                'parents': [],
                'merge_points': [],
                'changes': [],
            }
            log.error('ghost entry: %r' % (revid,))
            return util.Container(entry)
            
        commit_time = datetime.datetime.fromtimestamp(rev.timestamp)
        
        parents = [util.Container(revid=r, revno=self.get_revno(r)) for r in rev.parent_ids]

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
            'branch_nick': rev.properties.get('branch-nick', None),
            'short_comment': short_message,
            'comment': rev.message,
            'comment_clean': [util.html_clean(s) for s in message],
            'parents': parents,
            'changes': self.diff_revisions(revid, left_parent, get_diffs=get_diffs),
        }
        return util.Container(entry)
    
    def scan_range(self, revlist, revid, pagesize=20):
        """
        yield a list of (label, title, revid) for a scan range through the full
        branch history, centered around the given revid.
        
        example: [ ('<<', 'Previous page', 'rrr'), ('-10', 'Forward 10', 'rrr'),
                   ('*', None, None), ('+10', 'Back 10', 'rrr'),
                   ('+30', 'Back 30', 'rrr'), ('>>', 'Next page', 'rrr') ]
        
        next/prev page are always using the pagesize.
        """
        count = len(revlist)
        pos = self.get_revid_sequence(revlist, revid)

        if pos > 0:
            yield (u'\xab', 'Previous page', revlist[max(0, pos - pagesize)])
        else:
            yield (u'\xab', None, None)
        
        offset_sign = -1
        for offset in util.scan_range(pos, count, pagesize):
            if (offset > 0) and (offset_sign < 0):
                offset_sign = 0
                # show current position
#                yield ('[%s]' % (self.get_revno(revlist[pos]),), None, None)
#                yield (u'\u2022', None, None)
                yield (u'\u00b7', None, None)
            if offset < 0:
                title = 'Back %d' % (-offset,)
            else:
                title = 'Forward %d' % (offset,)
            yield ('%+d' % (offset,), title, revlist[pos + offset])
        
        if pos < count - 1:
            yield (u'\xbb', 'Next page', revlist[min(count - 1, pos + pagesize)])
        else:
            yield (u'\xbb', None, None)
    
    def get_revlist_offset(self, revlist, revid, offset):
        count = len(revlist)
        pos = self.get_revid_sequence(revlist, revid)
        if offset < 0:
            return revlist[max(0, pos + offset)]
        return revlist[min(count - 1, pos + offset)]
    
    @with_branch_lock
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
                elif line.startswith(' '):
                    chunk.diff.append(util.Container(old_lineno=old_lineno, new_lineno=new_lineno,
                                                     type='context', line=util.html_clean(line[1:])))
                    old_lineno += 1
                    new_lineno += 1
                elif line.startswith('+'):
                    chunk.diff.append(util.Container(old_lineno=None, new_lineno=new_lineno,
                                                     type='insert', line=util.html_clean(line[1:])))
                    new_lineno += 1
                elif line.startswith('-'):
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

    @with_branch_lock
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

    @with_branch_lock
    def annotate_file(self, file_id, revid):
        z = time.time()
        lineno = 1
        parity = 0
        
        file_revid = self.get_inventory(revid)[file_id].revision
        oldvalues = None
        revision_cache = {}
        
        # because we cache revision metadata ourselves, it's actually much
        # faster to call 'annotate_iter' on the weave directly than it is to
        # ask bzrlib to annotate for us.
        w = self._branch.repository.weave_store.get_weave(file_id, self._branch.repository.get_transaction())
        last_line_revid = None
        for line_revid, text in w.annotate_iter(file_revid):
            if line_revid == last_line_revid:
                # remember which lines have a new revno and which don't
                status = 'same'
            else:
                status = 'changed'
                parity ^= 1
                last_line_revid = line_revid
                change = revision_cache.get(line_revid, None)
                if change is None:
                    change = self.get_change(line_revid)
                    revision_cache[line_revid] = change
                trunc_revno = change.revno
                if len(trunc_revno) > 10:
                    trunc_revno = trunc_revno[:9] + '...'
                
            yield util.Container(parity=parity, lineno=lineno, status=status,
                                 trunc_revno=trunc_revno, change=change, text=util.html_clean(text))
            lineno += 1
        
        log.debug('annotate: %r secs' % (time.time() - z,))
