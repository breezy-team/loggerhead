# Copyright (C) 2006-2010 Canonical Ltd.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

#
# This file (and many of the web templates) contains work based on the
# "bazaar-webserve" project by Goffredo Baroncelli, which is in turn based
# on "hgweb" by Jake Edge and Matt Mackall.
#


import datetime
import logging
import os
import re
import textwrap
import threading

from bzrlib import lru_cache
import bzrlib.branch
import bzrlib.delta
import bzrlib.errors
import bzrlib.foreign
import bzrlib.revision

from loggerhead import search
from loggerhead import util

from bzrlib.plugins.history_db import (
    history_db,
    _get_querier,
    )


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
                filename=rich_filename(paths[1], kind),
                file_id=file_id, kind=kind[1]))
        elif versioned == 'removed':
            self.removed.append(util.Container(
                filename=rich_filename(paths[0], kind),
                file_id=file_id, kind=kind[0]))
        elif renamed:
            self.renamed.append(util.Container(
                old_filename=rich_filename(paths[0], kind[0]),
                new_filename=rich_filename(paths[1], kind[1]),
                file_id=file_id,
                text_modified=modified == 'modified'))
        else:
            self.modified.append(util.Container(
                filename=rich_filename(paths[1], kind),
                file_id=file_id))

# The lru_cache is not thread-safe, so we need a lock around it for
# all threads.
rev_info_memory_cache_lock = threading.RLock()

_raw_revno_revid_cache = lru_cache.LRUCache(10000)
_revno_revid_lock = threading.RLock()


class RevnoRevidMemoryCache(object):
    """A store that maps revnos to revids based on the branch it is in.
    """

    def __init__(self, cache, lock, branch_tip):
        # Note: what we'd really like is something that knew how long it takes
        # to produce a revno * how often it is accessed. Since some revnos
        # take 100x longer to produce than others. Could we cheat and just loop
        # on __getitem__ ?
        # There are also other possible layouts. A per-branch cache, with an
        # LRU around the whole thing, etc. I chose this for simplicity.
        self._branch_tip = branch_tip
        self._cache = cache
        # lru_cache is not thread-safe, so we need to lock all accesses.
        # It is even modified when doing a get() on it.
        self._lock = lock

    def get(self, key):
        """Return the data associated with `key`. Otherwise return None.

        :param key: Can be a revno_str or a revid.
        """
        self._lock.acquire()
        try:
            cached = self._cache.get((self._branch_tip, key))
        finally:
            self._lock.release()
        return cached

    def set(self, revid, revno_str):
        """Record that in this branch `revid` has revno `revno_str`."""
        self._lock.acquire()
        try:
            # Could use StaticTuples here, but probably only useful if we
            # cache more than 10k of them. 100k/1M is probably useful.
            self._cache[(self._branch_tip, revid)] = revno_str
            self._cache[(self._branch_tip, revno_str)] = revid
        finally:
            self._lock.release()

history_db_importer_lock = threading.Lock()


class History(object):
    """Decorate a branch to provide information for rendering.

    History objects are expected to be short lived -- when serving a request
    for a particular branch, open it, read-lock it, wrap a History object
    around it, serve the request, throw the History object away, unlock the
    branch and throw it away.

    :ivar _file_change_cache: An object that caches information about the
        files that changed between two revisions.
    :ivar _querier: A HistoryDB.Querier instance, allowing us to query for
        information in the ancestry of the branch.
    :ivar _revno_revid: A dictionary mapping stringified revnos to revision
        ids.
    """

    def __init__(self, branch, file_cache=None, cache_key=None, cache_path=None):
        assert branch.is_locked(), (
            "Can only construct a History object with a read-locked branch.")
        if file_cache is not None:
            self._file_change_cache = file_cache
            file_cache.history = self
        else:
            self._file_change_cache = None
        self._branch = branch
        self._branch_tags = None
        self._inventory_cache = {}
        self._querier = _get_querier(branch)
        if self._querier is None:
            # History-db is not configured for this branch, do it ourselves
            assert cache_path is not None
            self._querier = history_db.Querier(
                os.path.join(cache_path, 'historydb.sql'), branch)
        # sqlite is single-writer, so block concurrent updates.
        self._querier.set_importer_lock(history_db_importer_lock)
        # TODO: Is this being premature? It makes the rest of the code
        #       simpler...
        self._querier.ensure_branch_tip()
        self._branch_nick = self._branch.get_config().get_nickname()
        self.log = logging.getLogger('loggerhead.%s' % (self._branch_nick,))

        self.last_revid = branch.last_revision()
        self._revno_revid_cache = RevnoRevidMemoryCache(_raw_revno_revid_cache,
            _revno_revid_lock, self._branch.last_revision())

    @property
    def has_revisions(self):
        return not bzrlib.revision.is_null(self.last_revid)

    def get_config(self):
        return self._branch.get_config()

    def get_revno(self, revid):
        if revid is None:
            return 'unknown'
        revno_str = self._revno_revid_cache.get(revid)
        if revno_str is not None:
            return revno_str
        revnos = self._querier.get_dotted_revno_range_multi([revid])
        # TODO: Should probably handle KeyError?
        dotted_revno = revnos[revid]
        revno_str = '.'.join(map(str, dotted_revno))
        self._revno_revid_cache.set(revid, revno_str)
        return revno_str

    def get_revnos(self, revids):
        """Get a map of revid => revno for all revisions."""
        revno_map = {}
        unknown = []
        for revid in revids:
            if revid is None:
                revno_map[revid] = 'unknown'
                continue
            revno_str = self._revno_revid_cache.get(revid)
            if revno_str is not None:
                revno_map[revid] = revno_str
                continue
            unknown.append(revid)
        if not unknown:
            return revno_map
        # querier returns dotted revno tuples
        query_revno_map = self._querier.get_dotted_revno_range_multi(
                            unknown)
        ghosts = set(unknown)
        for revid, dotted_revno in query_revno_map.iteritems():
            revno_str = '.'.join(map(str, dotted_revno))
            self._revno_revid_cache.set(revid, revno_str)
            revno_map[revid] = revno_str
            ghosts.discard(revid)
        if ghosts:
            revno_map.update([(n, 'unknown') for n in ghosts])
        return revno_map

    def get_revid_for_revno(self, revno_str):
        revid = self._revno_revid_cache.get(revno_str)
        if revid is not None:
            return revid
        dotted_revno = tuple(map(int, revno_str.split('.')))
        revnos = self._querier.get_revision_ids([dotted_revno])
        revnos = dict([('.'.join(map(str, drn)), ri)
                       for drn, ri in revnos.iteritems()])
        for revno_str, revid in revnos.iteritems():
            self._revno_revid_cache.set(revid, revno_str)
        return revnos[revno_str]

    def _get_lh_parent(self, revid):
        """Get the left-hand parent of a given revision id."""
        # TODO: Move this into a public method on Querier
        # TODO: Possibly look into caching some of this info in memory, and
        #       between HTTP requests.
        self._querier.ensure_branch_tip()
        return self._querier._get_lh_parent_rev_id(revid)

    def _get_children(self, revid):
        """Get the children of the given revision id."""
        # XXX: We should be filtering this based on self._branch's ancestry...
        # TODO: We also should be using a method on Querier, instead of doing
        #       it ourselves
        c = self._querier._get_cursor()
        res = c.execute("SELECT c.revision_id"
                        "  FROM revision p, parent, revision c"
                        " WHERE child = c.db_id"
                        "   AND parent = p.db_id"
                        "   AND p.revision_id = ?",
                        (revid,)).fetchall()
        return [r[0] for r in res]

    def get_revids_from(self, revid_list, start_revid):
        """
        Yield the mainline (wrt start_revid) revisions that merged each
        revid in revid_list.
        """
        tip_revid = start_revid
        if revid_list is None:
            # This returns the mainline of start_revid
            # TODO: We could use Querier for this
            # Note: Don't use self._branch.revision_history, as that always
            #       grabs the full history, and we now support stopping early.
            history = self._branch.repository.iter_reverse_revision_history(
                            start_revid)
            is_null = bzrlib.revision.is_null
            for revid in history:
                yield revid
            return
        revid_set = set(revid_list)

        while tip_revid is not None and revid_set:
            parent_revid = self._get_lh_parent(tip_revid)
            # TODO: Consider caching this, especially between HTTP requests
            introduced = self._querier.iter_merge_sorted_revisions(
                start_revision_id=tip_revid, stop_revision_id=parent_revid)
            introduced_revs = set([i[0] for i in introduced
                                   if i in revid_set])
            if introduced_revs:
                revid_set.difference_update(introduced_revs)
                yield tip_revid
            tip_revid = parent_revid

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

    revno_re = re.compile(r'^[\d\.]+$')

    def fix_revid(self, revid):
        # if a "revid" is actually a dotted revno, convert it to a revid
        if revid is None:
            return revid
        if revid == 'head:':
            return self.last_revid
        try:
            if self.revno_re.match(revid):
                val = self.get_revid_for_revno(revid)
                # XXX: Do this more cleanly
                if val is None:
                    raise KeyError
                revid = val
        except KeyError:
            import pdb; pdb.set_trace()
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

    def _iterate_sufficiently(self, iterable, stop_at, extra_rev_count):
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
                result.append(n)
                if count >= extra_rev_count:
                    break
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
            # TODO: This cache is unbounded, though only used for a single http
            #       request. Consider what we might do to limit this.
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
            children = self._get_children(revid)
            nexts = []
            for child in children:
                child_lh_parent = self._get_lh_parent(child)
                if child_lh_parent == revid:
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

        needed_revnos = set()
        for change in changes:
            needed_revnos.add(change.revid)
            needed_revnos.update([p_id for p_id in change.parents])
        revno_map = self.get_revnos(needed_revnos)

        def merge_points_callback(a_change, attr):
            merge_revids = self.simplify_merge_point_list(
                               self.get_merge_point_list(a_change.revid))
            if not merge_revids:
                return []
            revno_map = self.get_revnos(merge_revids)
            return [util.Container(revid=r, revno=revno_map[r])
                    for r in merge_revids]
        parity = 0
        for change in changes:
            change._set_property('merge_points', merge_points_callback)
            if len(change.parents) > 0:
                change.parents = [util.Container(revid=r, revno=revno_map[r])
                                  for r in change.parents]
            change.revno = revno_map[change.revid]
            change.parity = parity
            parity ^= 1

        return changes

    def get_changes_uncached(self, revid_list):
        # FIXME: deprecated method in getting a null revision
        revid_list = filter(lambda revid: not bzrlib.revision.is_null(revid),
                            revid_list)
        parent_map = self._branch.repository.get_parent_map(
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
          revtags = ', '.join(self._branch_tags[revision.revision_id])

        entry = {
            'revid': revision.revision_id,
            'date': datetime.datetime.fromtimestamp(revision.timestamp),
            'utc_date': datetime.datetime.utcfromtimestamp(revision.timestamp),
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
            foreign_revid, mapping = (revision.foreign_revid, revision.mapping)
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

    def get_file_changes_uncached(self, entry):
        if entry.parents:
            old_revid = entry.parents[0].revid
        else:
            old_revid = bzrlib.revision.NULL_REVISION
        return self.file_changes_for_revision_ids(old_revid, entry.revid)

    def get_file_changes(self, entry):
        if self._file_change_cache is None:
            return self.get_file_changes_uncached(entry)
        else:
            return self._file_change_cache.get_file_changes(entry)

    def get_merged_in(self, entry):
        """Get the point where this entry was merged into the mainline.
        
        :param entry: A Container having .revno and .revid.
        :return: The revno string of the mainline revision.
        """
        if '.' not in entry.revno:
            return None
        rev_id_to_mainline = self._querier.get_mainline_where_merged(
            [entry.revid])
        revid = rev_id_to_mainline.get(entry.revid, None)
        if revid is None:
            return None
        return self.get_revno(revid)

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
            bzrlib.revision.is_null(new_revid)):
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
            text_changes=sorted(reporter.text_changes, key=lambda x: x.filename))
