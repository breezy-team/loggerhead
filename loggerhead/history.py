# Copyright (C) 2006-2011 Canonical Ltd.
#                     (Authored by Martin Albisetti <argentina@gmail.com>)
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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

#
# This file (and many of the web templates) contains work based on the
# "bazaar-webserve" project by Goffredo Baroncelli, which is in turn based
# on "hgweb" by Jake Edge and Matt Mackall.
#


import bisect
import datetime
import logging
import re
import textwrap
import threading
import tarfile

from bzrlib import tag
import bzrlib.branch
import bzrlib.delta
import bzrlib.errors
import bzrlib.foreign
import bzrlib.revision

from loggerhead import search
from loggerhead import util
from loggerhead.wholehistory import compute_whole_history_data


def is_branch(folder):
    try:
        bzrlib.branch.Branch.open(folder)
        return True
    except:
        return False


def clean_message(message):
    """Clean up a commit message and return it and a short (1-line) version.

    Commit messages that are long single lines are reflowed using the textwrap
    module (Robey, the original author of this code, apparently favored this
    style of message).
    """
    message = message.lstrip().splitlines()

    if len(message) == 1:
        message = textwrap.wrap(message[0])

    if len(message) == 0:
        # We can end up where when (a) the commit message was empty or (b)
        # when the message consisted entirely of whitespace, in which case
        # textwrap.wrap() returns an empty list.
        return [''], ''

    # Make short form of commit message.
    short_message = message[0]
    if len(short_message) > 60:
        short_message = short_message[:60] + '...'

    return message, short_message


def rich_filename(path, kind):
    if kind == 'directory':
        path += '/'
    if kind == 'symlink':
        path += '@'
    return path


class _RevListToTimestamps(object):
    """This takes a list of revisions, and allows you to bisect by date"""

    __slots__ = ['revid_list', 'repository']

    def __init__(self, revid_list, repository):
        self.revid_list = revid_list
        self.repository = repository

    def __getitem__(self, index):
        """Get the date of the index'd item"""
        return datetime.datetime.fromtimestamp(self.repository.get_revision(
                   self.revid_list[index]).timestamp)

    def __len__(self):
        return len(self.revid_list)

class FileChangeReporter(object):

    def __init__(self, old_inv, new_inv):
        self.added = []
        self.modified = []
        self.renamed = []
        self.removed = []
        self.text_changes = []
        self.old_inv = old_inv
        self.new_inv = new_inv

    def revid(self, inv, file_id):
        try:
            return inv[file_id].revision
        except bzrlib.errors.NoSuchId:
            return 'null:'

    def report(self, file_id, paths, versioned, renamed, modified,
               exe_change, kind):
        if modified not in ('unchanged', 'kind changed'):
            if versioned == 'removed':
                filename = rich_filename(paths[0], kind[0])
            else:
                filename = rich_filename(paths[1], kind[1])
            self.text_changes.append(util.Container(
                filename=filename, file_id=file_id,
                old_revision=self.revid(self.old_inv, file_id),
                new_revision=self.revid(self.new_inv, file_id)))
        if versioned == 'added':
            self.added.append(util.Container(
                filename=rich_filename(paths[1], kind), kind=kind[1]))
        elif versioned == 'removed':
            self.removed.append(util.Container(
                filename=rich_filename(paths[0], kind), kind=kind[0]))
        elif renamed:
            self.renamed.append(util.Container(
                old_filename=rich_filename(paths[0], kind[0]),
                new_filename=rich_filename(paths[1], kind[1]),
                text_modified=modified == 'modified', exe_change=exe_change))
        else:
            self.modified.append(util.Container(
                filename=rich_filename(paths[1], kind),
                text_modified=modified == 'modified', exe_change=exe_change))

# The lru_cache is not thread-safe, so we need a lock around it for
# all threads.
rev_info_memory_cache_lock = threading.RLock()

class RevInfoMemoryCache(object):
    """A store that validates values against the revids they were stored with.

    We use a unique key for each branch.

    The reason for not just using the revid as the key is so that when a new
    value is provided for a branch, we replace the old value used for the
    branch.

    There is another implementation of the same interface in
    loggerhead.changecache.RevInfoDiskCache.
    """

    def __init__(self, cache):
        self._cache = cache

    def get(self, key, revid):
        """Return the data associated with `key`, subject to a revid check.

        If a value was stored under `key`, with the same revid, return it.
        Otherwise return None.
        """
        rev_info_memory_cache_lock.acquire()
        try:
            cached = self._cache.get(key)
        finally:
            rev_info_memory_cache_lock.release()
        if cached is None:
            return None
        stored_revid, data = cached
        if revid == stored_revid:
            return data
        else:
            return None

    def set(self, key, revid, data):
        """Store `data` under `key`, to be checked against `revid` on get().
        """
        rev_info_memory_cache_lock.acquire()
        try:
            self._cache[key] = (revid, data)
        finally:
            rev_info_memory_cache_lock.release()

# Used to store locks that prevent multiple threads from building a 
# revision graph for the same branch at the same time, because that can
# cause severe performance issues that are so bad that the system seems
# to hang.
revision_graph_locks = {}
revision_graph_check_lock = threading.Lock()

class History(object):
    """Decorate a branch to provide information for rendering.

    History objects are expected to be short lived -- when serving a request
    for a particular branch, open it, read-lock it, wrap a History object
    around it, serve the request, throw the History object away, unlock the
    branch and throw it away.

    :ivar _rev_info: A list of information about revisions.  This is by far
        the most cryptic data structure in loggerhead.  At the top level, it
        is a list of 3-tuples [(merge-info, where-merged, parents)].
        `merge-info` is (seq, revid, merge_depth, revno_str, end_of_merge) --
        like a merged sorted list, but the revno is stringified.
        `where-merged` is a tuple of revisions that have this revision as a
        non-lefthand parent.  Finally, `parents` is just the usual list of
        parents of this revision.
    :ivar _rev_indices: A dictionary mapping each revision id to the index of
        the information about it in _rev_info.
    :ivar _revno_revid: A dictionary mapping stringified revnos to revision
        ids.
    """

    def _load_whole_history_data(self, caches, cache_key):
        """Set the attributes relating to the whole history of the branch.

        :param caches: a list of caches with interfaces like
            `RevInfoMemoryCache` and be ordered from fastest to slowest.
        :param cache_key: the key to use with the caches.
        """
        self._rev_indices = None
        self._rev_info = None

        missed_caches = []
        def update_missed_caches():
            for cache in missed_caches:
                cache.set(cache_key, self.last_revid, self._rev_info)

        # Theoretically, it's possible for two threads to race in creating
        # the Lock() object for their branch, so we put a lock around
        # creating the per-branch Lock().
        revision_graph_check_lock.acquire()
        try:
            if cache_key not in revision_graph_locks:
                revision_graph_locks[cache_key] = threading.Lock()
        finally:
            revision_graph_check_lock.release()

        revision_graph_locks[cache_key].acquire()
        try:
            for cache in caches:
                data = cache.get(cache_key, self.last_revid)
                if data is not None:
                    self._rev_info = data
                    update_missed_caches()
                    break
                else:
                    missed_caches.append(cache)
            else:
                whole_history_data = compute_whole_history_data(self._branch)
                self._rev_info, self._rev_indices = whole_history_data
                update_missed_caches()
        finally:
            revision_graph_locks[cache_key].release()

        if self._rev_indices is not None:
            self._revno_revid = {}
            for ((_, revid, _, revno_str, _), _, _) in self._rev_info:
                self._revno_revid[revno_str] = revid
        else:
            self._revno_revid = {}
            self._rev_indices = {}
            for ((seq, revid, _, revno_str, _), _, _) in self._rev_info:
                self._rev_indices[revid] = seq
                self._revno_revid[revno_str] = revid

    def __init__(self, branch, whole_history_data_cache,
                 revinfo_disk_cache=None, cache_key=None):
        assert branch.is_locked(), (
            "Can only construct a History object with a read-locked branch.")
        self._branch = branch
        self._branch_tags = None
        self._inventory_cache = {}
        self._branch_nick = self._branch.get_config().get_nickname()
        self.log = logging.getLogger('loggerhead.%s' % (self._branch_nick,))

        self.last_revid = branch.last_revision()

        caches = [RevInfoMemoryCache(whole_history_data_cache)]
        if revinfo_disk_cache:
            caches.append(revinfo_disk_cache)
        self._load_whole_history_data(caches, cache_key)

    @property
    def has_revisions(self):
        return not bzrlib.revision.is_null(self.last_revid)

    def get_config(self):
        return self._branch.get_config()

    def get_revno(self, revid):
        if revid not in self._rev_indices:
            # ghost parent?
            return 'unknown'
        seq = self._rev_indices[revid]
        revno = self._rev_info[seq][0][3]
        return revno

    def get_revids_from(self, revid_list, start_revid):
        """
        Yield the mainline (wrt start_revid) revisions that merged each
        revid in revid_list.
        """
        if revid_list is None:
            # Just yield the mainline, starting at start_revid
            revid = start_revid
            is_null = bzrlib.revision.is_null
            while not is_null(revid):
                yield revid
                parents = self._rev_info[self._rev_indices[revid]][2]
                if not parents:
                    return
                revid = parents[0]
            return
        revid_set = set(revid_list)
        revid = start_revid

        def introduced_revisions(revid):
            r = set([revid])
            seq = self._rev_indices[revid]
            md = self._rev_info[seq][0][2]
            i = seq + 1
            while i < len(self._rev_info) and self._rev_info[i][0][2] > md:
                r.add(self._rev_info[i][0][1])
                i += 1
            return r
        while revid_set:
            if bzrlib.revision.is_null(revid):
                return
            rev_introduced = introduced_revisions(revid)
            matching = rev_introduced.intersection(revid_set)
            if matching:
                # We don't need to look for these anymore.
                revid_set.difference_update(matching)
                yield revid
            parents = self._rev_info[self._rev_indices[revid]][2]
            if len(parents) == 0:
                return
            revid = parents[0]

    def get_short_revision_history_by_fileid(self, file_id):
        # FIXME: would be awesome if we could get, for a folder, the list of
        # revisions where items within that folder changed.i
        possible_keys = [(file_id, revid) for revid in self._rev_indices]
        get_parent_map = self._branch.repository.texts.get_parent_map
        # We chunk the requests as this works better with GraphIndex.
        # See _filter_revisions_touching_file_id in bzrlib/log.py
        # for more information.
        revids = []
        chunk_size = 1000
        for start in xrange(0, len(possible_keys), chunk_size):
            next_keys = possible_keys[start:start + chunk_size]
            revids += [k[1] for k in get_parent_map(next_keys)]
        del possible_keys, next_keys
        return revids

    def get_revision_history_since(self, revid_list, date):
        # if a user asks for revisions starting at 01-sep, they mean inclusive,
        # so start at midnight on 02-sep.
        date = date + datetime.timedelta(days=1)
        # our revid list is sorted in REVERSE date order,
        # so go thru some hoops here...
        revid_list.reverse()
        index = bisect.bisect(_RevListToTimestamps(revid_list,
                                                   self._branch.repository),
                              date)
        if index == 0:
            return []
        revid_list.reverse()
        index = -index
        return revid_list[index:]

    def get_search_revid_list(self, query, revid_list):
        """
        given a "quick-search" query, try a few obvious possible meanings:

            - revision id or # ("128.1.3")
            - date (US style "mm/dd/yy", earth style "dd-mm-yy", or \
iso style "yyyy-mm-dd")
            - comment text as a fallback

        and return a revid list that matches.
        """
        # FIXME: there is some silliness in this action.  we have to look up
        # all the relevant changes (time-consuming) only to return a list of
        # revids which will be used to fetch a set of changes again.

        # if they entered a revid, just jump straight there;
        # ignore the passed-in revid_list
        revid = self.fix_revid(query)
        if revid is not None:
            if isinstance(revid, unicode):
                revid = revid.encode('utf-8')
            changes = self.get_changes([revid])
            if (changes is not None) and (len(changes) > 0):
                return [revid]

        date = None
        m = self.us_date_re.match(query)
        if m is not None:
            date = datetime.datetime(util.fix_year(int(m.group(3))),
                                     int(m.group(1)),
                                     int(m.group(2)))
        else:
            m = self.earth_date_re.match(query)
            if m is not None:
                date = datetime.datetime(util.fix_year(int(m.group(3))),
                                         int(m.group(2)),
                                         int(m.group(1)))
            else:
                m = self.iso_date_re.match(query)
                if m is not None:
                    date = datetime.datetime(util.fix_year(int(m.group(1))),
                                             int(m.group(2)),
                                             int(m.group(3)))
        if date is not None:
            if revid_list is None:
                # if no limit to the query was given,
                # search only the direct-parent path.
                revid_list = list(self.get_revids_from(None, self.last_revid))
            return self.get_revision_history_since(revid_list, date)

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
        if revid == 'head:':
            return self.last_revid
        try:
            if self.revno_re.match(revid):
                revid = self._revno_revid[revid]
        except KeyError:
            raise bzrlib.errors.NoSuchRevision(self._branch_nick, revid)
        return revid

    def get_file_view(self, revid, file_id):
        """
        Given a revid and optional path, return a (revlist, revid) for
        navigation through the current scope: from the revid (or the latest
        revision) back to the original revision.

        If file_id is None, the entire revision history is the list scope.
        """
        if revid is None:
            revid = self.last_revid
        if file_id is not None:
            revlist = list(
                self.get_short_revision_history_by_fileid(file_id))
            revlist = self.get_revids_from(revlist, revid)
        else:
            revlist = self.get_revids_from(None, revid)
        return revlist

    @staticmethod
    def _iterate_sufficiently(iterable, stop_at, extra_rev_count):
        """Return a list of iterable.

        If extra_rev_count is None, fully consume iterable.
        Otherwise, stop at 'stop_at' + extra_rev_count.

        Example:
          iterate until you find stop_at, then iterate 10 more times.
        """
        if extra_rev_count is None:
            return list(iterable)
        result = []
        found = False
        for n in iterable:
            result.append(n)
            if n == stop_at:
                found = True
                break
        if found:
            for count, n in enumerate(iterable):
                if count >= extra_rev_count:
                    break
                result.append(n)
        return result

    def get_view(self, revid, start_revid, file_id, query=None,
                 extra_rev_count=None):
        """
        use the URL parameters (revid, start_revid, file_id, and query) to
        determine the revision list we're viewing (start_revid, file_id, query)
        and where we are in it (revid).

            - if a query is given, we're viewing query results.
            - if a file_id is given, we're viewing revisions for a specific
              file.
            - if a start_revid is given, we're viewing the branch from a
              specific revision up the tree.
            - if extra_rev_count is given, find the view from start_revid =>
              revid, and continue an additional 'extra_rev_count'. If not
              given, then revid_list will contain the full history of
              start_revid

        these may be combined to view revisions for a specific file, from
        a specific revision, with a specific search query.

        returns a new (revid, start_revid, revid_list) where:

            - revid: current position within the view
            - start_revid: starting revision of this view
            - revid_list: list of revision ids for this view

        file_id and query are never changed so aren't returned, but they may
        contain vital context for future url navigation.
        """
        if start_revid is None:
            start_revid = self.last_revid

        if query is None:
            revid_list = self.get_file_view(start_revid, file_id)
            revid_list = self._iterate_sufficiently(revid_list, revid,
                                                    extra_rev_count)
            if revid is None:
                revid = start_revid
            if revid not in revid_list:
                # if the given revid is not in the revlist, use a revlist that
                # starts at the given revid.
                revid_list = self.get_file_view(revid, file_id)
                revid_list = self._iterate_sufficiently(revid_list, revid,
                                                        extra_rev_count)
                start_revid = revid
            return revid, start_revid, revid_list

        # potentially limit the search
        if file_id is not None:
            revid_list = self.get_file_view(start_revid, file_id)
        else:
            revid_list = None
        revid_list = search.search_revisions(self._branch, query)
        if revid_list and len(revid_list) > 0:
            if revid not in revid_list:
                revid = revid_list[0]
            return revid, start_revid, revid_list
        else:
            # XXX: This should return a message saying that the search could
            # not be completed due to either missing the plugin or missing a
            # search index.
            return None, None, []

    def get_inventory(self, revid):
        if revid not in self._inventory_cache:
            self._inventory_cache[revid] = (
                self._branch.repository.get_inventory(revid))
        return self._inventory_cache[revid]

    def get_path(self, revid, file_id):
        if (file_id is None) or (file_id == ''):
            return ''
        path = self.get_inventory(revid).id2path(file_id)
        if (len(path) > 0) and not path.startswith('/'):
            path = '/' + path
        return path

    def get_file_id(self, revid, path):
        if (len(path) > 0) and not path.startswith('/'):
            path = '/' + path
        return self.get_inventory(revid).path2id(path)

    def get_merge_point_list(self, revid):
        """
        Return the list of revids that have merged this node.
        """
        if '.' not in self.get_revno(revid):
            return []

        merge_point = []
        while True:
            children = self._rev_info[self._rev_indices[revid]][1]
            nexts = []
            for child in children:
                child_parents = self._rev_info[self._rev_indices[child]][2]
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
            if revnos in d:
                m = d[revnos][0]
                if revnolast < m:
                    d[revnos] = (revnolast, revid)
            else:
                d[revnos] = (revnolast, revid)

        return [revid for (_, revid) in d.itervalues()]

    def add_branch_nicks(self, change):
        """
        given a 'change', fill in the branch nicks on all parents and merge
        points.
        """
        fetch_set = set()
        for p in change.parents:
            fetch_set.add(p.revid)
        for p in change.merge_points:
            fetch_set.add(p.revid)
        p_changes = self.get_changes(list(fetch_set))
        p_change_dict = dict([(c.revid, c) for c in p_changes])
        for p in change.parents:
            if p.revid in p_change_dict:
                p.branch_nick = p_change_dict[p.revid].branch_nick
            else:
                p.branch_nick = '(missing)'
        for p in change.merge_points:
            if p.revid in p_change_dict:
                p.branch_nick = p_change_dict[p.revid].branch_nick
            else:
                p.branch_nick = '(missing)'

    def get_changes(self, revid_list):
        """Return a list of changes objects for the given revids.

        Revisions not present and NULL_REVISION will be ignored.
        """
        changes = self.get_changes_uncached(revid_list)
        if len(changes) == 0:
            return changes

        # some data needs to be recalculated each time, because it may
        # change as new revisions are added.
        for change in changes:
            merge_revids = self.simplify_merge_point_list(
                               self.get_merge_point_list(change.revid))
            change.merge_points = [
                util.Container(revid=r,
                revno=self.get_revno(r)) for r in merge_revids]
            if len(change.parents) > 0:
                change.parents = [util.Container(revid=r,
                    revno=self.get_revno(r)) for r in change.parents]
            change.revno = self.get_revno(change.revid)

        parity = 0
        for change in changes:
            change.parity = parity
            parity ^= 1

        return changes

    def get_changes_uncached(self, revid_list):
        # FIXME: deprecated method in getting a null revision
        revid_list = filter(lambda revid: not bzrlib.revision.is_null(revid),
                            revid_list)
        parent_map = self._branch.repository.get_graph().get_parent_map(
                         revid_list)
        # We need to return the answer in the same order as the input,
        # less any ghosts.
        present_revids = [revid for revid in revid_list
                          if revid in parent_map]
        rev_list = self._branch.repository.get_revisions(present_revids)

        return [self._change_from_revision(rev) for rev in rev_list]

    def _change_from_revision(self, revision):
        """
        Given a bzrlib Revision, return a processed "change" for use in
        templates.
        """
        message, short_message = clean_message(revision.message)

        if self._branch_tags is None:
            self._branch_tags = self._branch.tags.get_reverse_tag_dict()

        revtags = None
        if revision.revision_id in self._branch_tags:
          # tag.sort_* functions expect (tag, data) pairs, so we generate them,
          # and then strip them
          tags = [(t, None) for t in self._branch_tags[revision.revision_id]]
          sort_func = getattr(tag, 'sort_natural', None)
          if sort_func is None:
              tags.sort()
          else:
              sort_func(self._branch, tags)
          revtags = u', '.join([t[0] for t in tags])

        entry = {
            'revid': revision.revision_id,
            'date': datetime.datetime.fromtimestamp(revision.timestamp),
            'utc_date': datetime.datetime.utcfromtimestamp(revision.timestamp),
            'committer': revision.committer,
            'authors': revision.get_apparent_authors(),
            'branch_nick': revision.properties.get('branch-nick', None),
            'short_comment': short_message,
            'comment': revision.message,
            'comment_clean': [util.html_clean(s) for s in message],
            'parents': revision.parent_ids,
            'bugs': [bug.split()[0] for bug in revision.properties.get('bugs', '').splitlines()],
            'tags': revtags,
        }
        if isinstance(revision, bzrlib.foreign.ForeignRevision):
            foreign_revid, mapping = (
                revision.foreign_revid, revision.mapping)
        elif ":" in revision.revision_id:
            try:
                foreign_revid, mapping = \
                    bzrlib.foreign.foreign_vcs_registry.parse_revision_id(
                        revision.revision_id)
            except bzrlib.errors.InvalidRevisionId:
                foreign_revid = None
                mapping = None
        else:
            foreign_revid = None
        if foreign_revid is not None:
            entry["foreign_vcs"] = mapping.vcs.abbreviation
            entry["foreign_revid"] = mapping.vcs.show_foreign_revid(foreign_revid)
        return util.Container(entry)

    def get_file_changes(self, entry):
        if entry.parents:
            old_revid = entry.parents[0].revid
        else:
            old_revid = bzrlib.revision.NULL_REVISION
        return self.file_changes_for_revision_ids(old_revid, entry.revid)

    def add_changes(self, entry):
        changes = self.get_file_changes(entry)
        entry.changes = changes

    def get_file(self, file_id, revid):
        """Returns (path, filename, file contents)"""
        inv = self.get_inventory(revid)
        inv_entry = inv[file_id]
        rev_tree = self._branch.repository.revision_tree(inv_entry.revision)
        path = inv.id2path(file_id)
        if not path.startswith('/'):
            path = '/' + path
        return path, inv_entry.name, rev_tree.get_file_text(file_id)

    def file_changes_for_revision_ids(self, old_revid, new_revid):
        """
        Return a nested data structure containing the changes in a delta::

            added: list((filename, file_id)),
            renamed: list((old_filename, new_filename, file_id)),
            deleted: list((filename, file_id)),
            modified: list(
                filename: str,
                file_id: str,
            ),
            text_changes: list((filename, file_id)),
        """
        repo = self._branch.repository
        if (bzrlib.revision.is_null(old_revid) or
            bzrlib.revision.is_null(new_revid) or
            old_revid == new_revid):
            old_tree, new_tree = map(
                repo.revision_tree, [old_revid, new_revid])
        else:
            old_tree, new_tree = repo.revision_trees([old_revid, new_revid])

        reporter = FileChangeReporter(old_tree.inventory, new_tree.inventory)

        bzrlib.delta.report_changes(new_tree.iter_changes(old_tree), reporter)

        return util.Container(
            added=sorted(reporter.added, key=lambda x: x.filename),
            renamed=sorted(reporter.renamed, key=lambda x: x.new_filename),
            removed=sorted(reporter.removed, key=lambda x: x.filename),
            modified=sorted(reporter.modified, key=lambda x: x.filename),
            text_changes=sorted(reporter.text_changes,
                                key=lambda x: x.filename))

