#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
# Copyright (C) 2006  Goffredo Baroncelli <kreijack@inwind.it>
# Copyright (C) 2005  Jake Edge <jake@edge2.net>
# Copyright (C) 2005  Matt Mackall <mpm@selenic.com>
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

#
# This file (and many of the web templates) contains work based on the
# "bazaar-webserve" project by Goffredo Baroncelli, which is in turn based
# on "hgweb" by Jake Edge and Matt Mackall.
#


import bisect
import cgi
import datetime
import logging
import os
import posixpath
import re
import shelve
import sys
import textwrap
import threading
import time
from StringIO import StringIO

from loggerhead import util
from loggerhead.util import decorator

import bzrlib
import bzrlib.annotate
import bzrlib.branch
import bzrlib.bundle.serializer
import bzrlib.diff
import bzrlib.errors
import bzrlib.progress
import bzrlib.textfile
import bzrlib.tsort
import bzrlib.ui


with_branch_lock = util.with_lock('_lock', 'branch')

@decorator
def with_bzrlib_read_lock(unbound):
    def bzrlib_read_locked(self, *args, **kw):
        #self.log.debug('-> %r bzr lock', id(threading.currentThread()))
        self._branch.repository.lock_read()
        try:
            return unbound(self, *args, **kw)
        finally:
            self._branch.repository.unlock()
            #self.log.debug('<- %r bzr lock', id(threading.currentThread()))
    return bzrlib_read_locked


# bzrlib's UIFactory is not thread-safe
uihack = threading.local()

class ThreadSafeUIFactory (bzrlib.ui.SilentUIFactory):
    def nested_progress_bar(self):
        if getattr(uihack, '_progress_bar_stack', None) is None:
            uihack._progress_bar_stack = bzrlib.progress.ProgressBarStack(klass=bzrlib.progress.DummyProgress)
        return uihack._progress_bar_stack.get_nested()

bzrlib.ui.ui_factory = ThreadSafeUIFactory()


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
        delete_list, insert_list = [], []
        for line in chunk.diff:
            if line.type == 'context':
                if len(delete_list) or len(insert_list):
                    _process_side_by_side_buffers(line_list, delete_list, insert_list)
                    delete_list, insert_list = [], []
                line_list.append(util.Container(old_lineno=line.old_lineno, new_lineno=line.new_lineno,
                                                old_line=line.line, new_line=line.line,
                                                old_type=line.type, new_type=line.type))
            elif line.type == 'delete':
                delete_list.append((line.old_lineno, line.line, line.type))
            elif line.type == 'insert':
                insert_list.append((line.new_lineno, line.line, line.type))
        if len(delete_list) or len(insert_list):
            _process_side_by_side_buffers(line_list, delete_list, insert_list)
        out_chunk_list.append(util.Container(diff=line_list))
    return out_chunk_list


def is_branch(folder):
    try:
        bzrlib.branch.Branch.open(folder)
        return True
    except:
        return False


# from bzrlib
class _RevListToTimestamps(object):
    """This takes a list of revisions, and allows you to bisect by date"""

    __slots__ = ['revid_list', 'repository']

    def __init__(self, revid_list, repository):
        self.revid_list = revid_list
        self.repository = repository

    def __getitem__(self, index):
        """Get the date of the index'd item"""
        return datetime.datetime.fromtimestamp(self.repository.get_revision(self.revid_list[index]).timestamp)

    def __len__(self):
        return len(self.revid_list)


class History (object):
    
    def __init__(self):
        self._change_cache = None
        self._index = None
        self._lock = threading.RLock()
    
    @classmethod
    def from_branch(cls, branch, name=None):
        z = time.time()
        self = cls()
        self._branch = branch
        self._history = branch.revision_history()
        self._last_revid = self._history[-1]
        self._revision_graph = branch.repository.get_revision_graph(self._last_revid)
        
        if name is None:
            name = self._branch.nick
        self._name = name
        self.log = logging.getLogger('loggerhead.%s' % (name,))
        
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

        self.log.info('built revision graph cache: %r secs' % (time.time() - z,))
        return self
    
    @classmethod
    def from_folder(cls, path, name=None):
        b = bzrlib.branch.Branch.open(path)
        return cls.from_branch(b, name)

    @with_branch_lock
    def out_of_date(self):
        if self._branch.revision_history()[-1] != self._last_revid:
            return True
        return False

    def use_cache(self, cache):
        self._change_cache = cache
    
    def use_search_index(self, index):
        self._index = index

    @with_branch_lock
    def detach(self):
        # called when a new history object needs to be created, because the
        # branch history has changed.  we need to immediately close and stop
        # using our caches, because a new history object will be created to
        # replace us, using the same cache files.
        # (may also be called during server shutdown.)
        if self._change_cache is not None:
            self._change_cache.close()
            self._change_cache = None
        if self._index is not None:
            self._index.close()
            self._index = None

    def flush_cache(self):
        if self._change_cache is None:
            return
        self._change_cache.flush()
    
    def check_rebuild(self):
        if self._change_cache is not None:
            self._change_cache.check_rebuild()
        if self._index is not None:
            self._index.check_rebuild()
    
    last_revid = property(lambda self: self._last_revid, None, None)
    
    count = property(lambda self: self._count, None, None)

    @with_branch_lock
    def get_config(self):
        return self._branch.get_config()
    
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
    def get_revision_history_since(self, revid_list, date):
        # if a user asks for revisions starting at 01-sep, they mean inclusive,
        # so start at midnight on 02-sep.
        date = date + datetime.timedelta(days=1)
        # our revid list is sorted in REVERSE date order, so go thru some hoops here...
        revid_list.reverse()
        index = bisect.bisect(_RevListToTimestamps(revid_list, self._branch.repository), date)
        if index == 0:
            return []
        revid_list.reverse()
        index = -index
        return revid_list[index:]
    
    @with_branch_lock
    def get_revision_history_matching(self, revid_list, text):
        self.log.debug('searching %d revisions for %r', len(revid_list), text)
        z = time.time()
        # this is going to be painfully slow. :(
        out = []
        text = text.lower()
        for revid in revid_list:
            change = self.get_changes([ revid ])[0]
            if text in change.comment.lower():
                out.append(revid)
        self.log.debug('searched %d revisions for %r in %r secs', len(revid_list), text, time.time() - z)
        return out

    def get_revision_history_matching_indexed(self, revid_list, text):
        self.log.debug('searching %d revisions for %r', len(revid_list), text)
        z = time.time()
        if self._index is None:
            return self.get_revision_history_matching(revid_list, text)
        out = self._index.find(text, revid_list)
        self.log.debug('searched %d revisions for %r in %r secs: %d results', len(revid_list), text, time.time() - z, len(out))
        # put them in some coherent order :)
        out = [r for r in self._full_history if r in out]
        return out
    
    @with_branch_lock
    def get_search_revid_list(self, query, revid_list):
        """
        given a "quick-search" query, try a few obvious possible meanings:
        
            - revision id or # ("128.1.3")
            - date (US style "mm/dd/yy", earth style "dd-mm-yy", or iso style "yyyy-mm-dd")
            - comment text as a fallback

        and return a revid list that matches.
        """
        # FIXME: there is some silliness in this action.  we have to look up
        # all the relevant changes (time-consuming) only to return a list of
        # revids which will be used to fetch a set of changes again.
        
        # if they entered a revid, just jump straight there; ignore the passed-in revid_list
        revid = self.fix_revid(query)
        if revid is not None:
            changes = self.get_changes([ revid ])
            if (changes is not None) and (len(changes) > 0):
                return [ revid ]
        
        date = None
        m = self.us_date_re.match(query)
        if m is not None:
            date = datetime.datetime(util.fix_year(int(m.group(3))), int(m.group(1)), int(m.group(2)))
        else:
            m = self.earth_date_re.match(query)
            if m is not None:
                date = datetime.datetime(util.fix_year(int(m.group(3))), int(m.group(2)), int(m.group(1)))
            else:
                m = self.iso_date_re.match(query)
                if m is not None:
                    date = datetime.datetime(util.fix_year(int(m.group(1))), int(m.group(2)), int(m.group(3)))
        if date is not None:
            if revid_list is None:
                # if no limit to the query was given, search only the direct-parent path.
                revid_list = list(self.get_revids_from(None, self._last_revid))
            return self.get_revision_history_since(revid_list, date)
        
        # check comment fields.
        if revid_list is None:
            revid_list = self._full_history
        return self.get_revision_history_matching_indexed(revid_list, query)
    
    revno_re = re.compile(r'^[\d\.]+$')
    # the date regex are without a final '$' so that queries like
    # "2006-11-30 12:15" still mostly work.  (i think it's better to give
    # them 90% of what they want instead of nothing at all.)
    us_date_re = re.compile(r'^(\d{1,2})/(\d{1,2})/(\d\d(\d\d?))')
    earth_date_re = re.compile(r'^(\d{1,2})-(\d{1,2})-(\d\d(\d\d?))')
    iso_date_re = re.compile(r'^(\d\d\d\d)-(\d\d)-(\d\d)')

    def fix_revid(self, revid):
        # if a "revid" is actually a dotted revno, convert it to a revid
        if revid is None:
            return revid
        if self.revno_re.match(revid):
            revid = self._revno_revid[revid]
        return revid
    
    @with_branch_lock
    def get_file_view(self, revid, file_id):
        """
        Given an optional revid and optional path, return a (revlist, revid)
        for navigation through the current scope: from the revid (or the
        latest revision) back to the original revision.
        
        If file_id is None, the entire revision history is the list scope.
        If revid is None, the latest revision is used.
        """
        if revid is None:
            revid = self._last_revid
        if file_id is not None:
            # since revid is 'start_revid', possibly should start the path tracing from revid... FIXME
            inv = self._branch.repository.get_revision_inventory(revid)
            revlist = list(self.get_short_revision_history_by_fileid(file_id))
            revlist = list(self.get_revids_from(revlist, revid))
        else:
            revlist = list(self.get_revids_from(None, revid))
        if revid is None:
            revid = revlist[0]
        return revlist, revid
    
    @with_branch_lock
    def get_view(self, revid, start_revid, file_id, query=None):
        """
        use the URL parameters (revid, start_revid, file_id, and query) to
        determine the revision list we're viewing (start_revid, file_id, query)
        and where we are in it (revid).
        
        if a query is given, we're viewing query results.
        if a file_id is given, we're viewing revisions for a specific file.
        if a start_revid is given, we're viewing the branch from a
            specific revision up the tree.
        (these may be combined to view revisions for a specific file, from
            a specific revision, with a specific search query.)
            
        returns a new (revid, start_revid, revid_list, scan_list) where:
        
            - revid: current position within the view
            - start_revid: starting revision of this view
            - revid_list: list of revision ids for this view
        
        file_id and query are never changed so aren't returned, but they may
        contain vital context for future url navigation.
        """
        if query is None:
            revid_list, start_revid = self.get_file_view(start_revid, file_id)
            if revid is None:
                revid = start_revid
            if revid not in revid_list:
                # if the given revid is not in the revlist, use a revlist that
                # starts at the given revid.
                revid_list, start_revid = self.get_file_view(revid, file_id)
            return revid, start_revid, revid_list
        
        # potentially limit the search
        if (start_revid is not None) or (file_id is not None):
            revid_list, start_revid = self.get_file_view(start_revid, file_id)
        else:
            revid_list = None

        revid_list = self.get_search_revid_list(query, revid_list)
        if len(revid_list) > 0:
            if revid not in revid_list:
                revid = revid_list[0]
            return revid, start_revid, revid_list
        else:
            # no results
            return None, None, []

    @with_branch_lock
    def get_inventory(self, revid):
        return self._branch.repository.get_revision_inventory(revid)

    @with_branch_lock
    def get_path(self, revid, file_id):
        if (file_id is None) or (file_id == ''):
            return ''
        path = self._branch.repository.get_revision_inventory(revid).id2path(file_id)
        if (len(path) > 0) and not path.startswith('/'):
            path = '/' + path
        return path
    
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

    def get_branch_nicks(self, changes):
        """
        given a list of changes from L{get_changes}, fill in the branch nicks
        on all parents and merge points.
        """
        fetch_set = set()
        for change in changes:
            for p in change.parents:
                fetch_set.add(p.revid)
            for p in change.merge_points:
                fetch_set.add(p.revid)
        p_changes = self.get_changes(list(fetch_set))
        p_change_dict = dict([(c.revid, c) for c in p_changes])
        for change in changes:
            for p in change.parents:
                p.branch_nick = p_change_dict[p.revid].branch_nick
            for p in change.merge_points:
                p.branch_nick = p_change_dict[p.revid].branch_nick
    
    @with_branch_lock
    def get_changes(self, revid_list, get_diffs=False):
        if self._change_cache is None:
            changes = self.get_changes_uncached(revid_list, get_diffs)
        else:
            changes = self._change_cache.get_changes(revid_list, get_diffs)
        if changes is None:
            return changes
        
        # some data needs to be recalculated each time, because it may
        # change as new revisions are added.
        for i in xrange(len(revid_list)):
            revid = revid_list[i]
            change = changes[i]
            merge_revids = self.simplify_merge_point_list(self.get_merge_point_list(revid))
            change.merge_points = [util.Container(revid=r, revno=self.get_revno(r)) for r in merge_revids]
        
        return changes

    # alright, let's profile this sucka.
    def _get_changes_profiled(self, revid_list, get_diffs=False):
        from loggerhead.lsprof import profile
        import cPickle
        ret, stats = profile(self.get_changes_uncached, revid_list, get_diffs)
        stats.sort()
        stats.freeze()
        cPickle.dump(stats, open('lsprof.stats', 'w'), 2)
        return ret

    @with_branch_lock
    @with_bzrlib_read_lock
    def get_changes_uncached(self, revid_list, get_diffs=False):
        try:
            rev_list = self._branch.repository.get_revisions(revid_list)
        except (KeyError, bzrlib.errors.NoSuchRevision):
            return None
        
        delta_list = self._branch.repository.get_deltas_for_revisions(rev_list)
        combined_list = zip(rev_list, delta_list)
        
        tree_map = {}
        if get_diffs:
            # lookup the trees for each revision, so we can calculate diffs
            lookup_set = set()
            for rev in rev_list:
                lookup_set.add(rev.revision_id)
                if len(rev.parent_ids) > 0:
                    lookup_set.add(rev.parent_ids[0])
            tree_map = dict((t.get_revision_id(), t) for t in self._branch.repository.revision_trees(lookup_set))
            # also the root tree, in case we hit the origin:
            tree_map[None] = self._branch.repository.revision_tree(None)
        
        entries = []
        for rev, delta in combined_list:
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
    
            old_tree, new_tree = None, None
            if get_diffs:
                new_tree = tree_map[rev.revision_id]
                old_tree = tree_map[left_parent]

            entry = {
                'revid': rev.revision_id,
                'revno': self.get_revno(rev.revision_id),
                'date': commit_time,
                'author': rev.committer,
                'branch_nick': rev.properties.get('branch-nick', None),
                'short_comment': short_message,
                'comment': rev.message,
                'comment_clean': [util.html_clean(s) for s in message],
                'parents': parents,
                'changes': self.parse_delta(delta, get_diffs, old_tree, new_tree),
            }
            entries.append(util.Container(entry))
        
        return entries

    @with_branch_lock
    def get_file(self, file_id, revid):
        "returns (filename, data)"
        inv_entry = self.get_inventory(revid)[file_id]
        rev_tree = self._branch.repository.revision_tree(inv_entry.revision)
        return inv_entry.name, rev_tree.get_file_text(file_id)
    
    @with_branch_lock
    def parse_delta(self, delta, get_diffs=True, old_tree=None, new_tree=None):
        """
        Return a nested data structure containing the changes in a delta::
        
            added: list((filename, file_id)),
            renamed: list((old_filename, new_filename, file_id)),
            deleted: list((filename, file_id)),
            modified: list(
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
        
        if C{get_diffs} is false, the C{chunks} will be omitted.
        """
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
                modified.append(util.Container(filename=rich_filename(new_path, kind), file_id=fid))
                return
            old_lines = old_tree.get_file_lines(fid)
            new_lines = new_tree.get_file_lines(fid)
            buffer = StringIO()
            bzrlib.diff.internal_diff(old_path, old_lines, new_path, new_lines, buffer)
            diff = buffer.getvalue()
            modified.append(util.Container(filename=rich_filename(new_path, kind), file_id=fid, chunks=process_diff(diff), raw_diff=diff))

        for path, fid, kind in delta.added:
            added.append((rich_filename(path, kind), fid))
        
        for path, fid, kind, text_modified, meta_modified in delta.modified:
            handle_modify(path, path, fid, kind)
        
        for oldpath, newpath, fid, kind, text_modified, meta_modified in delta.renamed:
            renamed.append((rich_filename(oldpath, kind), rich_filename(newpath, kind), fid))
            if meta_modified or text_modified:
                handle_modify(oldpath, newpath, fid, kind)
        
        for path, fid, kind in delta.removed:
            removed.append((rich_filename(path, kind), fid))
        
        return util.Container(added=added, renamed=renamed, removed=removed, modified=modified)

    @staticmethod
    def add_side_by_side(changes):
        # FIXME: this is a rotten API.
        for change in changes:
            for m in change.changes.modified:
                m.sbs_chunks = _make_side_by_side(m.chunks)
    
    @with_branch_lock
    def get_filelist(self, inv, path, sort_type=None):
        """
        return the list of all files (and their attributes) within a given
        path subtree.
        """
        while path.endswith('/'):
            path = path[:-1]
        if path.startswith('/'):
            path = path[1:]
        
        entries = inv.entries()
        
        fetch_set = set()
        for filepath, entry in entries:
            fetch_set.add(entry.revision)
        change_dict = dict([(c.revid, c) for c in self.get_changes(list(fetch_set))])
        
        file_list = []
        for filepath, entry in entries:
            if posixpath.dirname(filepath) != path:
                continue
            filename = posixpath.basename(filepath)
            rich_filename = filename
            pathname = filename
            if entry.kind == 'directory':
                pathname += '/'
            
            # last change:
            revid = entry.revision
            change = change_dict[revid]
            
            file = util.Container(filename=filename, rich_filename=rich_filename, executable=entry.executable, kind=entry.kind,
                                  pathname=pathname, file_id=entry.file_id, size=entry.text_size, revid=revid, change=change)
            file_list.append(file)
        
        if sort_type == 'filename':
            file_list.sort(key=lambda x: x.filename)
        elif sort_type == 'size':
            file_list.sort(key=lambda x: x.size)
        elif sort_type == 'date':
            file_list.sort(key=lambda x: x.change.date)
        
        parity = 0
        for file in file_list:
            file.parity = parity
            parity ^= 1

        return file_list


    _BADCHARS_RE = re.compile(ur'[\x00-\x08\x0b-\x0c\x0e-\x1f]')

    @with_branch_lock
    def annotate_file(self, file_id, revid):
        z = time.time()
        lineno = 1
        parity = 0
        
        file_revid = self.get_inventory(revid)[file_id].revision
        oldvalues = None
        
        # because we cache revision metadata ourselves, it's actually much
        # faster to call 'annotate_iter' on the weave directly than it is to
        # ask bzrlib to annotate for us.
        w = self._branch.repository.weave_store.get_weave(file_id, self._branch.repository.get_transaction())
        
        revid_set = set()
        for line_revid, text in w.annotate_iter(file_revid):
            revid_set.add(line_revid)
            if self._BADCHARS_RE.match(text):
                # bail out; this isn't displayable text
                yield util.Container(parity=0, lineno=1, status='same',
                                     text='<i>' + util.html_clean('(This is a binary file.)') + '</i>',
                                     change=util.Container())
                return
        change_cache = dict([(c.revid, c) for c in self.get_changes(list(revid_set))])
        
        last_line_revid = None
        for line_revid, text in w.annotate_iter(file_revid):
            if line_revid == last_line_revid:
                # remember which lines have a new revno and which don't
                status = 'same'
            else:
                status = 'changed'
                parity ^= 1
                last_line_revid = line_revid
                change = change_cache[line_revid]
                trunc_revno = change.revno
                if len(trunc_revno) > 10:
                    trunc_revno = trunc_revno[:9] + '...'
                
            yield util.Container(parity=parity, lineno=lineno, status=status,
                                 change=change, text=util.html_clean(text))
            lineno += 1
        
        self.log.debug('annotate: %r secs' % (time.time() - z,))

    @with_branch_lock
    @with_bzrlib_read_lock
    def get_bundle(self, revid):
        parents = self._revision_graph[revid]
        if len(parents) > 0:
            parent_revid = parents[0]
        else:
            parent_revid = None
        s = StringIO()
        bzrlib.bundle.serializer.write_bundle(self._branch.repository, revid, parent_revid, s)
        return s.getvalue()

