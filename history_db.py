# Copyright (C) 2010 Canonical Ltd
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
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA

"""Store history information in a database."""

try:
    from sqlite3 import dbapi2
except ImportError:
    from pysqlite2 import dbapi2

from collections import defaultdict, deque
import time

from bzrlib import (
    revision,
    trace,
    ui,
    )

from bzrlib.plugins.history_db import schema


NULL_PARENTS = (revision.NULL_REVISION,)


def _n_params(n):
    """Create a query string representing N parameters.

    n=1 => ?
    n=2 => ?, ?
    etc.
    """
    return ', '.join('?'*n)


def _add_n_params(query, n):
    """Add n parameters to the query string.

    the query should have a single '%s' in it to be expanded.
    """
    return query % (_n_params(n),)


class Importer(object):
    """Import data from bzr into the history_db."""

    def __init__(self, db_path, a_branch, incremental=False):
        db_conn = dbapi2.connect(db_path)
        self._incremental = incremental
        self._db_conn = db_conn
        self._ensure_schema()
        self._cursor = self._db_conn.cursor()
        self._branch = a_branch
        self._branch_tip_rev_id = a_branch.last_revision()
        self._branch_tip_key = (self._branch_tip_rev_id,)
        self._graph = None
        self._ensure_graph()
        self._rev_id_to_db_id = {}
        self._stats = defaultdict(lambda: 0)

    def _ensure_schema(self):
        if not schema.is_initialized(self._db_conn, dbapi2.OperationalError):
            schema.create_sqlite_db(self._db_conn)
            trace.note('Initialized database')
            # We know we can't do this incrementally, because nothing has
            # existed before...
            #self._incremental = False

    def _ensure_revisions(self, revision_ids):
        schema.ensure_revisions(self._cursor, revision_ids,
                                self._rev_id_to_db_id, self._graph)

    def _ensure_graph(self):
        if self._graph is not None:
            return
        repo = self._branch.repository
        self._graph = repo.revisions.get_known_graph_ancestry(
            [self._branch_tip_key])

    def _is_imported(self, tip_rev_id):
        res = self._cursor.execute(
            "SELECT count(*) FROM dotted_revno JOIN revision"
            "    ON dotted_revno.tip_revision = revision.db_id"
            " WHERE revision_id = ?"
            "   AND tip_revision = merged_revision",
            (tip_rev_id,)).fetchone()
        return res[0] > 0

    def _insert_nodes(self, tip_rev_id, nodes):
        """Insert all of the nodes mentioned into the database."""
        self._stats['_insert_node_calls'] += 1
        self._ensure_revisions([n.key[0] for n in nodes])
        if self._is_imported(tip_rev_id):
            # Not importing anything because the data is already present
            return False
        self._stats['total_nodes_inserted'] += len(nodes)
        tip_db_id = self._rev_id_to_db_id[tip_rev_id]
        revno_entries = []
        for node in nodes:
            # TODO: Do we need to track the 'end_of_merge' and 'merge_depth'
            #       fields?
            revno_entries.append((tip_db_id,
                                  self._rev_id_to_db_id[node.key[0]],
                                  '.'.join(map(str, node.revno)),
                                  node.end_of_merge,
                                  node.merge_depth))
        schema.create_dotted_revnos(self._cursor, revno_entries)
        return True

    def _update_parents(self, nodes):
        """Update parent information for all these nodes."""
        # Get the keys and their parents
        # TODO: handle ghosts somehow, the current table structure won't
        #       distinguish between valid roots and roots that are ghosts.
        #       Note, though, that merge_sort also prunes ghosts, so you have
        #       to find them some other way.
        parent_map = dict(
            (n.key[0], [p[0] for p in self._graph.get_parent_keys(n.key)])
            for n in nodes)
        self._insert_parent_map(parent_map)

    def _insert_parent_map(self, parent_map):
        """Insert all the entries in this parent map into the parent table."""
        rev_ids = set(parent_map)
        map(rev_ids.update, parent_map.itervalues())
        self._ensure_revisions(rev_ids)
        data = []
        r_to_d = self._rev_id_to_db_id
        for rev_id, parent_ids in parent_map.iteritems():
            for idx, parent_id in enumerate(parent_ids):
                data.append((r_to_d[rev_id], r_to_d[parent_id], idx))
        self._cursor.executemany("INSERT OR IGNORE INTO parent"
                                 "  (child, parent, parent_idx)"
                                 "VALUES (?, ?, ?)", data)

    def do_import(self, expand_all=False):
        if self._incremental:
            self._update_ancestry(self._branch_tip_rev_id)
            tip_db_id = self._rev_id_to_db_id[self._branch_tip_rev_id]
            inc_importer = _IncrementalImporter(self, tip_db_id)
        merge_sorted = self._import_tip(self._branch_tip_rev_id)
        if not expand_all:
            return
        # We know all the other imports are going to be incremental
        self._incremental = True
        self._stats['nodes_expanded'] += 0 # create an entry
        # We want to expand every possible mainline into a dotted_revno cache.
        # We don't really want to have to compute all the ones we have already
        # cached. And we want to compute as much as possible per pass. So we
        # start again at the tip, and just skip all the ones that already have
        # db entries.
        pb = ui.ui_factory.nested_progress_bar()
        for idx, node in enumerate(merge_sorted):
            pb.update('expanding', idx, len(merge_sorted))
            # this progress is very non-linear, it is expected the first few
            # will be slow, and the last few very fast.
            tip_rev_id = node.key[0]
            if self._is_imported(tip_rev_id):
                # This node its info is already imported
                continue
            self._stats['nodes_expanded'] += 1
            # Note: Suppressing the commit until we are finished saves a fair
            #       amount of time. expanding all of bzr.dev goes from 4m37s
            #       down to 3m21s.
            self._import_tip(tip_rev_id, suppress_progress_and_commit=True)
        self._db_conn.commit()
        pb.finished()

    def _import_tip(self, tip_revision_id, suppress_progress_and_commit=False):
        merge_sorted = self._graph.merge_sort((tip_revision_id,))
        try:
            if suppress_progress_and_commit:
                pb = None
            else:
                pb = ui.ui_factory.nested_progress_bar()
            last_mainline_rev_id = None
            new_nodes = []
            for idx, node in enumerate(merge_sorted):
                if pb is not None:
                    pb.update('importing', idx, len(merge_sorted))
                if last_mainline_rev_id is None:
                    assert not new_nodes
                    assert node.merge_depth == 0, \
                        "We did not start at a mainline?"
                    last_mainline_rev_id = node.key[0]
                    new_nodes.append(node)
                    continue
                if node.merge_depth == 0:
                    # We've seen all the nodes that were introduced by this
                    # revision into mainline, check to see if we've already
                    # inserted this data into the db. If we have, then we can
                    # assume that all parents are *also* inserted into the
                    # database and stop This is only safe if we either import
                    # in 'forward' order, or we wait to commit until all the
                    # data is imported. However, if we import in 'reverse'
                    # order, it is obvious when we can stop...

                    self._update_parents(new_nodes)
                    if not self._insert_nodes(last_mainline_rev_id, new_nodes):
                        # This data has already been imported.
                        new_nodes = []
                        break
                    last_mainline_rev_id = node.key[0]
                    new_nodes = []
                new_nodes.append(node)
            if pb is not None:
                pb.finished()
            if new_nodes:
                assert last_mainline_rev_id is not None
                self._insert_nodes(last_mainline_rev_id, new_nodes)
                new_nodes = []
        except:
            self._db_conn.rollback()
            raise
        else:
            if not suppress_progress_and_commit:
                self._db_conn.commit()
        return merge_sorted

    def _update_ancestry(self, new_tip_rev_id):
        """Walk the parents of this tip, updating 'revision' and 'parent'

        self._rev_id_to_db_id will be updated.
        """
        (known, parent_map,
         children) = self._find_known_ancestors(new_tip_rev_id)
        self._compute_gdfo_and_insert(known, children, parent_map)
        self._insert_parent_map(parent_map)
        self._db_conn.commit()

    def _find_known_ancestors(self, new_tip_rev_id):
        """Starting at tip, find ancestors we already have"""
        needed = [new_tip_rev_id]
        all_needed = set(new_tip_rev_id)
        children = {}
        parent_map = {}
        known = {}
        while needed:
            rev_id = needed.pop()
            if rev_id in known:
                # We may add particular parents multiple times, just ignore
                # them once they've been found
                continue
            res = self._cursor.execute("SELECT gdfo"
                                       "  FROM revision WHERE revision_id = ?",
                                       (rev_id,)).fetchone()
            if res is not None:
                known[rev_id] = res[0]
                continue
            # We don't have this entry recorded yet, add the parents to the
            # search
            pmap = self._branch.repository.get_parent_map([rev_id])
            parent_map.update(pmap)
            parent_ids = pmap.get(rev_id, ())
            if not parent_ids or parent_ids == NULL_PARENTS:
                # XXX: We should handle 'not parent_ids' differently, because
                #      that means they are a ghost. Currently the table cannot
                #      distinguish between a ghost and a root revision.
                # We can insert this rev directly, because we know its gdfo,
                # as it has no parents.
                parent_map[rev_id] = ()
                self._cursor.execute("INSERT INTO revision (revision_id, gdfo)"
                                     " VALUES (?, ?)", (rev_id, 1))
                # Wrap around to populate known quickly
                needed.append(rev_id)
                continue
            for parent_id in pmap[rev_id]:
                if parent_id not in known:
                    if parent_id not in all_needed:
                        needed.append(parent_id)
                        all_needed.add(parent_id)
                children.setdefault(parent_id, []).append(rev_id)
        return known, parent_map, children

    def _compute_gdfo_and_insert(self, known, children, parent_map):
        # At this point, we should have walked to all known parents, and should
        # be able to build up the gdfo and parent info for all keys.
        pending = [(gdfo, rev_id) for rev_id, gdfo in known.iteritems()]
        while pending:
            gdfo, rev_id = pending.pop()
            for child_id in children.get(rev_id, []):
                if child_id in known:
                    # XXX: Already numbered?
                    assert known[child_id] > gdfo
                    continue
                parent_ids = parent_map[child_id]
                max_gdfo = -1
                for parent_id in parent_ids:
                    try:
                        this_gdfo = known[parent_id]
                    except KeyError:
                        # One parent hasn't been computed yet
                        break
                    if this_gdfo > max_gdfo:
                        max_gdfo = this_gdfo
                else:
                    # All parents have their gdfo known
                    # assert gdfo == max_gdfo
                    child_gdfo = max_gdfo + 1
                    known[child_id] = child_gdfo
                    self._cursor.execute(
                        "INSERT INTO revision (revision_id, gdfo)"
                        " VALUES (?, ?)",
                        (child_id, child_gdfo))
                    # Put this into the pending queue so that *its* children
                    # also get updated
                    pending.append((child_gdfo, child_id))
        if self._graph is not None:
            for rev_id, gdfo in known.iteritems():
                assert gdfo == self._graph._nodes[(rev_id,)].gdfo

    def _get_db_id(self, revision_id):
        return self._cursor.execute('SELECT db_id FROM revision'
                                    ' WHERE revision_id = ?',
                                    (revision_id,)).fetchone()[0]

    def _update_dotted(self, new_tip_rev_id):
        """We have a new 'tip' revision, Update the dotted_revno table."""
        # Just make sure the db has valid info for all the existing entries
        self._update_ancestry(new_tip_rev_id)

    def _check_range_exists_for(self, head_db_id):
        """Does the given head_db_id already have a range defined using it."""
        return self._cursor.execute("SELECT count(*) FROM mainline_parent_range"
                                    " WHERE head = ?",
                                    (head_db_id,)).fetchone()[0] > 0

    def _get_lh_parent_db_id(self, revision_db_id):
        parent_res = self._cursor.execute("""
            SELECT parent.parent
              FROM parent
             WHERE parent.child = ?
               AND parent_idx = 0
            LIMIT 1 -- hint to the db, should always be only 1
            """, (revision_db_id,)).fetchone()
        # self._stats['lh_parent_step'] += 1
        if parent_res is None:
            return None
        return parent_res[0]

    def _insert_range(self, range_db_ids, tail_db_id):
        head_db_id = range_db_ids[0]
        self._cursor.execute("INSERT INTO mainline_parent_range"
                             " (head, tail, count) VALUES (?, ?, ?)",
                             (head_db_id, tail_db_id, len(range_db_ids)))
        # Note: This works for sqlite, does it work for pgsql?
        range_key = self._cursor.lastrowid
        self._stats['ranges_inserted'] += 1
        # Note that 'tail' is explicitly not included in the range
        self._stats['revs_in_ranges'] += len(range_db_ids)
        self._cursor.executemany(
            "INSERT INTO mainline_parent (range, revision, dist)"
            " VALUES (?, ?, ?)",
            [(range_key, d, idx) for idx, d in enumerate(range_db_ids)])

    def build_mainline_cache(self):
        """Given the current branch, cache mainline information."""
        self._build_one_mainline(self._branch_tip_rev_id)
        # TODO: expand_all?

    def _build_one_mainline(self, head_rev_id):
        # I'm not sure if this is optimal, but for now, I just walk backwards
        # through the mainline, and see if there is already a cached version,
        # or if I've stepped 100 revisions. If I've gone 100, I checkpoint, and
        # start again.
        # TODO: To avoid getting trivial ranges after large ranges, we could
        #       use another technique:
        #  a) Walk up to X revisions
        #  b) If we still haven't found a tip, then we stop, and split out a
        #     Y-revision range. Starting a new range with the remaining X-Y
        #     nodes.
        #  c) If we do find a tip, see how many revisions it points to (Z). If
        #     X + Z < threshold, then collapse the ranges (this could
        #     potentially be done multiple times.) However, I *think* that if
        #     the policy is to collapse at 1, then you should avoid chained
        #     collapses. (Any given revision should have only 1 partial jump
        #     before it gets into large-range areas.)
        # The specific thresholds are arbitrary, but it should mean you would
        # average a larger 'minimum' size. And (c) helps avoid fragmentation.
        # (Where multiple imports turn a 100-revision range into 20 5-revision
        # ranges.)
        self._ensure_revisions([head_rev_id])
        cur_db_id = self._rev_id_to_db_id[head_rev_id]
        range_db_ids = []
        try:
            while cur_db_id is not None:
                if self._check_range_exists_for(cur_db_id):
                    # This already exists as a valid 'head' in the range cache,
                    # so we can assume that all parents are already covered in
                    # reasonable ranges.
                    break
                if len(range_db_ids) >= 100:
                    # We have a 100 node range
                    self._insert_range(range_db_ids, cur_db_id)
                    # We want to start a new range, with
                    #   new_range.head == last_range.tail
                    range_db_ids = []
                range_db_ids.append(cur_db_id)
                parent_db_id = self._get_lh_parent_db_id(cur_db_id)
                cur_db_id = parent_db_id
            if len(range_db_ids) > 1:
                self._insert_range(range_db_ids, cur_db_id)
        except:
            self._db_conn.rollback()
            raise
        else:
            self._db_conn.commit()


class _IncrementalImporter(object):
    """Context for importing partial history."""
    # Note: all of the ids in this object are database ids. the revision_ids
    #       should have already been imported before we get to this step.

    def __init__(self, importer, tip_db_id):
        self._importer = importer
        self._tip_db_id = tip_db_id
        self._mainline_db_ids = None
        self._imported_mainline_id = None
        self._cursor = importer._cursor

        # db_id => gdfo
        self._known_gdfo = {}
        # db_ids that we know are ancestors of mainline_db_ids that are not
        # ancestors of pre_mainline_id
        self._interesting_ancestor_ids = set()

        # Information from the dotted_revno table for revisions that are in the
        # already-imported mainline.
        self._imported_dotted_revno = {}
        # Map from (dotted,revno,) => db_id
        self._dotted_to_db_id = {}
        # This is the gdfo of the current mainline revision search tip. This is
        # the threshold such that 
        self._imported_gdfo = None

        # Revisions that we are walking, to see if they are interesting, or
        # already imported.
        self._search_tips = None
        # mainline revno => number of child branches
        self._revno_to_branch_count = {}
        # (revno, branch_num) => oldest seen child
        self._branch_to_child_count = {}

        self._depth_first_stack = None
        self._scheduled_stack = None
        self._seen_parents = None
        # Map from db_id => parent_ids
        self._parent_map = {}

    def _find_needed_mainline(self):
        """Find mainline revisions that need to be filled out.
        
        :return: ([mainline_not_imported], most_recent_imported)
        """
        db_id = self._tip_db_id
        needed = []
        while db_id is not None and not self._is_imported_db_id(db_id):
            needed.append(db_id)
            db_id = self._importer._get_lh_parent_db_id(db_id)
        self._mainline_db_ids = needed
        self._interesting_ancestor_ids.update(self._mainline_db_ids)
        self._imported_mainline_id = db_id

    def _get_initial_search_tips(self):
        """Grab the right-hand parents of all the interesting mainline.

        We know we already searched all of the left-hand parents, so just grab
        the right-hand parents.
        """
        # TODO: Split this into a loop, since sqlite has a maximum number of
        #       parameters.
        res = self._cursor.execute(_add_n_params(
            "SELECT parent, gdfo FROM parent, revision"
            " WHERE parent.parent = revision.db_id"
            "   AND parent_idx != 0"
            "   AND child IN (%s)", len(self._mainline_db_ids)),
            self._mainline_db_ids).fetchall()
        self._search_tips = set([r[0] for r in res])
        known_gdfo = self._known_gdfo
        known_gdfo.update(res)
        res = self._cursor.execute(
            "SELECT gdfo FROM revision WHERE db_id = ?",
            [self._imported_mainline_id]).fetchone()
        imported_gdfo = res[0]
        self._imported_gdfo = imported_gdfo
        known_gdfo[self._imported_mainline_id] = imported_gdfo

    def _is_imported_db_id(self, tip_db_id):
        res = self._cursor.execute(
            "SELECT count(*) FROM dotted_revno"
            " WHERE tip_revision = ?"
            "   AND tip_revision = merged_revision",
            (tip_db_id,)).fetchone()
        return res[0] > 0

    def _split_search_tips_by_gdfo(self, unknown):
        """For these search tips, mark ones 'interesting' based on gdfo.
        
        All search tips are ancestors of _mainline_db_ids. So if their gdfo
        indicates that they could not be merged into already imported
        revisions, then we know automatically that they are
        new-and-interesting. Further, if they are present in
        _imported_dotted_revno, then we know they are not interesting, and
        we will stop searching them.

        Otherwise, we don't know for sure which category they fall into, so
        we return them for further processing.

        :return: still_unknown - search tips that aren't known to be
            interesting, and aren't known to be in the ancestry of already
            imported revisions.
        """
        still_unknown = []
        min_gdfo = None
        for db_id in unknown:
            if db_id in self._imported_dotted_revno:
                # This should be removed as a search tip, we know it isn't
                # interesting, it is an ancestor of an imported revision
                self._search_tips.remove(db_id)
                continue
            gdfo = self._known_gdfo[db_id]
            if gdfo >= self._imported_gdfo:
                self._interesting_ancestor_ids.add(db_id)
            else:
                still_unknown.append(db_id)
        return still_unknown

    def _split_interesting_using_children(self, unknown_search_tips):
        """Find children of these search tips.

        For each search tip, we find all of its known children. We then filter
        the children by:
            a) child is ignored if child in _interesting_ancestor_ids
            b) child is ignored if gdfo(child) > _imported_gdfo
                or (gdfo(child) == _imported_gdfo and child !=
                _imported_mainline_id)
               The reason for the extra check is because for the ancestry
               left-to-be-searched, with tip at _imported_mainline_id, *only*
               _imported_mainline_id is allowed to have gdfo = _imported_gdfo.
        for each search tip, if there are no interesting children, then this
        search tip is definitely interesting (there is no path for it to be
        merged into a previous mainline entry.)

        :return: still_unknown
            still_unknown are the search tips that are still have children that
            could be possibly merged.
        """
        interesting = self._interesting_ancestor_ids
        parent_child_res = self._cursor.execute(_add_n_params(
            "SELECT parent, child FROM parent"
            " WHERE parent IN (%s)",
            len(unknown_search_tips)), unknown_search_tips).fetchall()
        parent_to_children = {}
        already_imported = set()
        for parent, child in parent_child_res:
            if (child in self._imported_dotted_revno
                or child == self._imported_mainline_id):
                # This child is already imported, so obviously the parent is,
                # too.
                already_imported.add(parent)
                already_imported.add(child)
            parent_to_children.setdefault(parent, []).append(child)
        self._search_tips.difference_update(already_imported)
        possibly_merged_children = set(
            [c for p, c in parent_child_res
                if c not in interesting and p not in already_imported])
        known_gdfo = self._known_gdfo
        unknown_gdfos = [c for c in possibly_merged_children
                            if c not in known_gdfo]
        # TODO: Is it more wasteful to join this table early, or is it better
        #       because we avoid having to pass N parameters back in?
        # TODO: Would sorting the db ids help? They are the primary key for the
        #       table, so we could potentially fetch in a better order.
        if unknown_gdfos:
            res = self._cursor.execute(_add_n_params(
                "SELECT db_id, gdfo FROM revision WHERE db_id IN (%s)",
                len(unknown_gdfos)), unknown_gdfos)
            known_gdfo.update(res)
        min_gdfo = self._imported_gdfo
        # Remove all of the children who have gdfo >= min. We already handled
        # the == min case in the first loop.
        possibly_merged_children.difference_update(
            [c for c in possibly_merged_children if known_gdfo[c] >= min_gdfo])
        still_unknown = []
        for parent in unknown_search_tips:
            if parent in already_imported:
                continue
            for c in parent_to_children[parent]:
                if c in possibly_merged_children:
                    still_unknown.append(parent)
                    break
            else: # All children could not be possibly merged
                interesting.add(parent)
        return still_unknown

    def _step_mainline(self):
        """Move the mainline pointer by one, updating the data."""
        res = self._cursor.execute(
            "SELECT merged_revision, revno, end_of_merge, merge_depth"
            "  FROM dotted_revno WHERE tip_revision = ?",
            [self._imported_mainline_id]).fetchall()
        dotted_info = [(r[0], (tuple(map(int, r[1].split('.'))), r[2], r[3]))
                       for r in res]
        self._imported_dotted_revno.update(dotted_info)
        self._dotted_to_db_id.update([(i[1][0], i[0]) for i in dotted_info])
        # TODO: We could remove search tips that show up as newly merged
        #       though that can wait until the next
        #       _split_search_tips_by_gdfo
        # new_merged_ids = [r[0] for r in res]
        res = self._cursor.execute("SELECT parent, gdfo"
                                   "  FROM parent, revision"
                                   " WHERE parent = db_id"
                                   "   AND parent_idx = 0"
                                   "   AND child = ?",
                                   [self._imported_mainline_id]).fetchone()
        if res is None:
            # Walked off the mainline...
            # TODO: Make sure this stuff is tested
            self._imported_mainline_id = None
            self._imported_gdfo = 0
        else:
            self._imported_mainline_id, self._imported_gdfo = res
            self._known_gdfo[self._imported_mainline_id] = self._imported_gdfo

    def _step_search_tips(self):
        """Move the search tips to their parents."""
        res = self._cursor.execute(_add_n_params(
            "SELECT parent, gdfo FROM parent, revision"
            " WHERE parent=db_id AND child IN (%s)",
            len(self._search_tips)), list(self._search_tips)).fetchall()
        # Filter out search tips that we've already searched via a different
        # path. By construction, if we are stepping the search tips, we know
        # that all previous search tips are either in
        # self._imported_dotted_revno or in self._interesting_ancestor_ids.
        # _imported_dotted_revno will be filtered in the first
        # _split_search_tips_by_gdfo call, so we just filter out already
        # interesting ones.
        interesting = self._interesting_ancestor_ids
        self._search_tips = set([r[0] for r in res if r[0] not in interesting])
        # TODO: For search tips we will be removing, we don't need to join
        #       against revision since we should already have them. There may
        #       be other ways that we already know gdfo. It may be cheaper to
        #       check first.
        self._known_gdfo.update(res)

    def _find_interesting_ancestry(self):
        self._find_needed_mainline()
        self._get_initial_search_tips()
        while self._search_tips:
            # We don't know whether these search tips are known interesting, or
            # known uninteresting
            unknown = list(self._search_tips)
            while unknown:
                unknown = self._split_search_tips_by_gdfo(unknown)
                if not unknown:
                    break
                unknown = self._split_interesting_using_children(unknown)
                if not unknown:
                    break
                # The current search tips are the 'newest' possible tips right
                # now. If we can't classify them as definitely being
                # interesting, then we need to step the mainline until we can.
                # This means that the current search tips have children that
                # could be merged into an earlier mainline, walk the mainline
                # to see if we can resolve that.
                # Note that relying strictly on gdfo is a bit of a waste here,
                # because you may have a rev with 10 children before it lands
                # in mainline, but all 11 revs will be in the dotted_revno
                # cache for that mainline.
                self._step_mainline()
            # All search_tips are known to either be interesting or
            # uninteresting. Walk any search tips that remain.
            self._step_search_tips()
        # Once we get to here, we should have loaded enough of
        # _imported_dotted_revno to be able to create the merge_sort graph.
        # Also all of the new pending revisions should be in
        # self._interesting_ancestor_ids

    def _update_info_from_dotted_revno(self):
        """Update info like 'child_seen' from the dotted_revno info."""
        # TODO: We can move this iterator into a parameter, and have it
        #       continuously updated from _step_mainline()
        iterator = self._imported_dotted_revno.iteritems()
        for db_id, (revno, eom, depth) in iterator:
            if len(revno) > 1: # dotted revno, make sure branch count is right
                base_revno = revno[0]
                if (base_revno not in self._revno_to_branch_count
                    or revno[1] > self._revno_to_branch_count[base_revno]):
                    self._revno_to_branch_count[base_revno] = revno[1]
                branch_key = revno[:2]
                mini_revno = revno[2]
            else:
                # *mainline* branch
                branch_key = 0
                mini_revno = revno[0]
            if (branch_key not in self._branch_to_child_count
                or mini_revno > self._branch_to_child_count[branch_key]):
                self._branch_to_child_count[branch_key] = mini_revno

    def _is_first_child(self, parent_id):
        """Is this the first child seen for the given parent?"""
        if parent_id in self._seen_parents:
            return False
        # We haven't seen this while walking, but perhaps the already merged
        # stuff has.
        self._seen_parents.add(parent_id)
        if parent_id not in self._imported_dotted_revno:
            # Haven't seen this parent merged before, so we can't have seen
            # children of it
            return True
        revno = self._imported_dotted_revno[parent_id][0]
        if len(revno) > 1:
            branch_key = revno[:2]
            mini_revno = revno[2]
        else:
            branch_key = 0
            mini_revno = revno[0]
        if self._branch_to_child_count.get(branch_key, 0) > mini_revno:
            # This revision shows up in the graph, but another revision in this
            # branch shows up later, so this revision must have already been
            # seen
            return False
        # If we got this far, it doesn't appear to have been seen.
        return True

    # XXX: For now, we just re-implement some of the merge_sort logic locally
    def _push_node(self, db_id, merge_depth):
        # TODO: Check if db_id is a ghost (not allowed on the stack)
        parent_res = self._cursor.execute(
                    "SELECT parent FROM parent WHERE child = ?"
                    " ORDER BY parent_idx", (db_id,)).fetchall()
        parent_ids = tuple([r[0] for r in parent_res])
        self._parent_map[db_id] = parent_ids
        if len(parent_ids) <= 0:
            left_parent = None
            # We are dealing with a 'new root' possibly because of a ghost,
            # possibly because of merging a new ancestry.
            # KnownGraph.merge_sort just always says True here, so stick with
            # that
            is_first = True
        else:
            left_parent = parent_ids[0]
            is_first = self._is_first_child(left_parent)
        pending_parents = parent_ids[1:]
        # v- logically probably better as a tuple or object. We currently
        # modify it in place, so we use a list
        self._depth_first_stack.append([db_id, merge_depth, left_parent,
                                        left_parent, pending_parents,
                                        is_first])

    def _pop_node(self):
        """Move the last node from the _depth_first_stack to _scheduled_stack.

        This is the most left-hand node that we are able to find.
        """
        (db_id, merge_depth, left_parent_id, _, _,
         is_first) = self._depth_first_stack.pop()
        if left_parent_id is not None:
            parent_revno = self._imported_dotted_revno[left_parent_id][0]
            if is_first: # We simply number as parent + 1
                if len(parent_revno) == 1:
                    mini_revno = parent_revno[0] + 1
                    revno = (mini_revno,)
                    # TODO: Do we need to increment
                    #       self._branch_to_child_count[0]
                    #       I think we do, but it is currently only used by
                    #       _is_first_child, which should already be setting
                    #       the 'seen' counters...
                    # self._branch_to_child_count[0] = revno / max(revno, ...)
                else:
                    revno = parent_revno[:2] + (parent_revno[2] + 1,)
            else:
                # we need a new branch number. To get this correct, we have to
                # make sure that the beginning of this branch has been loaded
                ## branch_root = parent_revno[:2] + (1,)
                ## while branch_root not in self._dotted_to_db_id:
                ##     self._step_mainline()
                base_revno = parent_revno[0]
                branch_count = (
                    self._revno_to_branch_count.get(base_revno, 0) + 1)
                self._revno_to_branch_count[base_revno] = branch_count
                revno = (base_revno, branch_count, 1)
        else:
            # New Root. To get the numbering correct, we have to walk the
            # mainline back to the beginning... :(
            ## while self._imported_mainline_id is not None:
            ##     self._step_mainline()
            branch_count = self._revno_to_branch_count.get(0, -1) + 1
            self._revno_to_branch_count[0] = branch_count
            if branch_count == 0: # This is the mainline
                revno = (1,)
            else:
                revno = (0, branch_count, 1)
        # XXX: This isn't correct any more, we need to look at the parent,
        #      what *would* have been scheduled if we weren't doing partial
        #      scheduling. Then again, maybe it is correct for all but the
        #      mainline (first entry on the stack). Because we always break
        #      apart the dotted_revno cache based on what has gotten merged...
        if not self._scheduled_stack:
            end_of_merge = True
        else:
            prev_db_id, prev_revno, _, prev_depth = self._scheduled_stack[-1]
            if prev_depth < merge_depth:
                end_of_merge = True
            elif (prev_depth == merge_depth
                  and prev_db_id not in self._parent_map[db_id]):
                # Next node is not a direct parent
                end_of_merge = True
            else:
                end_of_merge = False
        self._imported_dotted_revno[db_id] = (revno, end_of_merge, merge_depth)
        self._scheduled_stack.append((db_id, revno, end_of_merge, merge_depth))

    def _compute_merge_sort(self):
        self._depth_first_stack = []
        self._scheduled_stack = []
        self._seen_parents = set()
        self._push_node(self._mainline_db_ids[0], 0)

        while self._depth_first_stack:
            last = self._depth_first_stack[-1]
            if last[3] is None and not last[4]:
                # The parents have been processed, pop the node
                self._pop_node()
                continue
            while last[3] is not None or last[4]:
                if last[3] is not None:
                    # Push on the left-hand-parent
                    next_db_id = last[3]
                    last[3] = None
                else:
                    pending_parents = last[4]
                    next_db_id = pending_parents[-1]
                    last[4] = pending_parents[:-1]
                if next_db_id in self._imported_dotted_revno:
                    continue
                if next_db_id == last[2]: #Is the left-parent?
                    next_merge_depth = last[1]
                else:
                    next_merge_depth = last[1] + 1
                self._push_node(next_db_id, next_merge_depth)
                # And switch to the outer loop
                break

    def do_import(self):
        self._find_interesting_ancestry()


class Querier(object):
    """Perform queries on an existing history db."""

    def __init__(self, db_path, a_branch):
        db_conn = dbapi2.connect(db_path)
        self._db_conn = db_conn
        self._cursor = self._db_conn.cursor()
        self._branch = a_branch
        self._branch_tip_rev_id = a_branch.last_revision()
        self._stats = defaultdict(lambda: 0)

    def _get_db_id(self, revision_id):
        return self._cursor.execute('SELECT db_id FROM revision'
                                    ' WHERE revision_id = ?',
                                    (revision_id,)).fetchone()[0]

    def _get_lh_parent_rev_id(self, revision_id):
        parent_res = self._cursor.execute("""
            SELECT p.revision_id
              FROM parent, revision as c, revision as p
             WHERE parent.child = c.db_id
               AND parent.parent = p.db_id
               AND c.revision_id = ?
               AND parent_idx = 0
            """, (revision_id,)).fetchone()
        self._stats['lh_parent_step'] += 1
        if parent_res is None:
            return None
        return parent_res[0]

    def _get_lh_parent_db_id(self, revision_db_id):
        parent_res = self._cursor.execute("""
            SELECT parent.parent
              FROM parent
             WHERE parent.child = ?
               AND parent_idx = 0
            """, (revision_db_id,)).fetchone()
        self._stats['lh_parent_step'] += 1
        if parent_res is None:
            return None
        return parent_res[0]

    def _get_possible_dotted_revno(self, tip_revision_id, merged_revision_id):
        """Given a possible tip revision, try to determine the dotted revno."""
        revno = self._cursor.execute("""
            SELECT revno FROM dotted_revno, revision t, revision m
             WHERE t.revision_id = ?
               AND t.db_id = dotted_revno.tip_revision
               AND m.revision_id = ?
               AND m.db_id = dotted_revno.merged_revision
            LIMIT 1 -- should always <= 1, but hint to the db?
            """, (tip_revision_id, merged_revision_id)).fetchone()
        self._stats['dotted_revno_query'] += 1
        if revno is None:
            return None
        return revno[0]

    def _get_possible_dotted_revno_db_id(self, tip_db_id, merged_db_id):
        """Get a dotted revno if we have it."""
        revno = self._cursor.execute("""
            SELECT revno FROM dotted_revno
             WHERE tip_revision = ?
               AND merged_revision = ?
            LIMIT 1 -- should always <= 1, but hint to the db?
            """, (tip_db_id, merged_db_id)).fetchone()
        self._stats['dotted_revno_query'] += 1
        if revno is None:
            return None
        return revno[0]

    def get_dotted_revno(self, revision_id):
        """Get the dotted revno for a specific revision id."""
        t = time.time()
        cur_tip_revision_id = self._branch_tip_rev_id
        while cur_tip_revision_id is not None:
            possible_revno = self._get_possible_dotted_revno(
                cur_tip_revision_id, revision_id)
            if possible_revno is not None:
                self._stats['query_time'] += (time.time() - t)
                return tuple(map(int, possible_revno.split('.')))
            cur_tip_revision_id = self._get_lh_parent_rev_id(
                cur_tip_revision_id)
        # If we got here, we just don't have an answer
        self._stats['query_time'] += (time.time() - t)
        return None

    def get_dotted_revno_db_ids(self, revision_id):
        """Get the dotted revno, but in-memory use db ids."""
        t = time.time()
        rev_id_to_db_id = {}
        schema.ensure_revisions(self._cursor,
                                [revision_id, self._branch_tip_rev_id],
                                rev_id_to_db_id, graph=None)
        tip_db_id = rev_id_to_db_id[self._branch_tip_rev_id]
        rev_db_id = rev_id_to_db_id[revision_id]
        while tip_db_id is not None:
            possible_revno = self._get_possible_dotted_revno_db_id(
                tip_db_id, rev_db_id)
            if possible_revno is not None:
                self._stats['query_time'] += (time.time() - t)
                return tuple(map(int, possible_revno.split('.')))
            tip_db_id = self._get_lh_parent_db_id(tip_db_id)
        self._stats['query_time'] += (time.time() - t)
        return None

    def get_dotted_revno_range(self, revision_id):
        """Determine the dotted revno, using the range info, etc."""
        t = time.time()
        tip_db_id = self._get_db_id(self._branch_tip_rev_id)
        rev_db_id = self._get_db_id(revision_id)
        revno = None
        while tip_db_id is not None:
            self._stats['num_steps'] += 1
            range_res = self._cursor.execute(
                "SELECT pkey, tail"
                "  FROM mainline_parent_range"
                " WHERE head = ?"
                " ORDER BY count DESC LIMIT 1",
                (tip_db_id,)).fetchone()
            if range_res is None:
                revno_res = self._cursor.execute(
                    "SELECT revno FROM dotted_revno"
                    " WHERE tip_revision = ? AND merged_revision = ?",
                    (tip_db_id, rev_db_id)).fetchone()
                next_db_id = self._get_lh_parent_db_id(tip_db_id)
            else:
                pkey, next_db_id = range_res
                revno_res = self._cursor.execute(
                    "SELECT revno FROM dotted_revno, mainline_parent"
                    " WHERE tip_revision = mainline_parent.revision"
                    "   AND mainline_parent.range = ?"
                    "   AND merged_revision = ?",
                    (pkey, rev_db_id)).fetchone()
            tip_db_id = next_db_id
            if revno_res is not None:
                revno = tuple(map(int, revno_res[0].split('.')))
                break
        self._stats['query_time'] += (time.time() - t)
        return revno

    def get_dotted_revno_range_multi(self, revision_ids):
        """Determine the dotted revno, using the range info, etc."""
        t = time.time()
        rev_id_to_db_id = {}
        need_ids = [self._branch_tip_rev_id]
        need_ids.extend(revision_ids)
        schema.ensure_revisions(self._cursor, need_ids,
                                rev_id_to_db_id, graph=None)
        tip_db_id = rev_id_to_db_id[self._branch_tip_rev_id]
        db_id_to_rev_id = dict((d, r) for r, d in rev_id_to_db_id.iteritems())
        db_ids = set([rev_id_to_db_id[r] for r in revision_ids])
        revnos = {}
        while tip_db_id is not None and db_ids:
            self._stats['num_steps'] += 1
            range_res = self._cursor.execute(
                "SELECT pkey, tail"
                "  FROM mainline_parent_range"
                " WHERE head = ?"
                " ORDER BY count DESC LIMIT 1",
                (tip_db_id,)).fetchone()
            if range_res is None:
                revno_res = self._cursor.execute(_add_n_params(
                    "SELECT merged_revision, revno FROM dotted_revno"
                    " WHERE tip_revision = ?"
                    "   AND merged_revision IN (%s)",
                    len(db_ids)), 
                    [tip_db_id] + list(db_ids)).fetchall()
                next_db_id = self._get_lh_parent_db_id(tip_db_id)
            else:
                pkey, next_db_id = range_res
                revno_res = self._cursor.execute(_add_n_params(
                    "SELECT merged_revision, revno"
                    "  FROM dotted_revno, mainline_parent"
                    " WHERE tip_revision = mainline_parent.revision"
                    "   AND mainline_parent.range = ?"
                    "   AND merged_revision IN (%s)",
                    len(db_ids)), 
                    [pkey] + list(db_ids)).fetchall()
            tip_db_id = next_db_id
            for db_id, revno in revno_res:
                db_ids.discard(db_id)
                revnos[db_id_to_rev_id[db_id]] = tuple(map(int,
                    revno.split('.')))
        self._stats['query_time'] += (time.time() - t)
        return revnos

    def walk_mainline(self):
        """Walk the db, and grab all the mainline identifiers."""
        t = time.time()
        cur_id = self._branch_tip_rev_id
        all_ids = []
        while cur_id is not None:
            all_ids.append(cur_id)
            cur_id = self._get_lh_parent_rev_id(cur_id)
        self._stats['query_time'] += (time.time() - t)
        return all_ids

    def walk_mainline_db_ids(self):
        """Walk the db, and grab all the mainline identifiers."""
        t = time.time()
        db_id = self._get_db_id(self._branch_tip_rev_id)
        all_ids = []
        while db_id is not None:
            all_ids.append(db_id)
            db_id = self._get_lh_parent_db_id(db_id)
        self._stats['query_time'] += (time.time() - t)
        return all_ids

    def _get_mainline_range_starting_at(self, head_db_id):
        """Try to find a range at this tip.

        If a range cannot be found, just find the next parent.
        :return: (range_or_None, next_db_id)
        """
        range_res = self._cursor.execute(
            "SELECT pkey, tail"
            "  FROM mainline_parent_range"
            " WHERE head = ?"
            " ORDER BY count DESC LIMIT 1",
            (head_db_id,)).fetchone()
        if range_res is None:
            parent_db_id = self._get_lh_parent_db_id(head_db_id)
            return None, parent_db_id
        range_key, tail_db_id = range_res
        # TODO: Is ORDER BY dist ASC expensive? We know a priori that the list
        #       is probably already in sorted order, but does sqlite know that?
        range_db_ids = self._cursor.execute(
            "SELECT revision FROM mainline_parent"
            " WHERE range = ? ORDER BY dist ASC",
            (range_key,)).fetchall()
        db_ids = [r[0] for r in range_db_ids]
        return db_ids, tail_db_id

    def walk_mainline_using_ranges(self):
        t = time.time()
        db_id = self._get_db_id(self._branch_tip_rev_id)
        all_ids = []
        while db_id is not None:
            self._stats['num_steps'] += 1
            next_range, next_db_id = self._get_mainline_range_starting_at(db_id)
            if next_range is None:
                # No range, so switch to using by-parent search
                all_ids.append(db_id)
            else:
                assert next_range[0] == db_id
                all_ids.extend(next_range)
            db_id = next_db_id
        self._stats['query_time'] += (time.time() - t)
        return all_ids

    def walk_ancestry(self):
        """Walk all parents of the given revision."""
        remaining = deque([self._branch_tip_rev_id])
        all = set(remaining)
        while remaining:
            next = remaining.popleft()
            parents = self._cursor.execute("""
                SELECT p.revision_id
                  FROM parent, revision p, revision c
                 WHERE parent.child = c.db_id
                   AND parent.parent = p.db_id
                   AND c.revision_id = ?
                   """, (next,)).fetchall()
            self._stats['num_steps'] += 1
            next_parents = [p[0] for p in parents if p[0] not in all]
            all.update(next_parents)
            remaining.extend(next_parents)
        return all

    def walk_ancestry_db_ids(self):
        _exec = self._cursor.execute
        all_ancestors = set()
        db_id = self._get_db_id(self._branch_tip_rev_id)
        all_ancestors.add(db_id)
        remaining = [db_id]
        while remaining:
            self._stats['num_steps'] += 1
            next = remaining[:100]
            remaining = remaining[len(next):]
            res = _exec(_add_n_params(
                "SELECT parent FROM parent WHERE child in (%s)",
                len(db_ids)), next)
            next_p = [p[0] for p in res if p[0] not in all_ancestors]
            all_ancestors.update(next_p)
            remaining.extend(next_p)
        return all_ancestors

    def walk_ancestry_range(self):
        """Walk the whole ancestry.
        
        Use the mainline_parent_range/mainline_parent table to speed things up.
        """
        _exec = self._cursor.execute
        # All we are doing is pre-seeding the search with all the mainline
        # revisions, we could probably do more with interleaving calls to
        # mainline with calls to parents but this is easier to write :)
        all_mainline = self.walk_mainline_using_ranges()
        t = time.time()
        all_ancestors = set(all_mainline)
        remaining = list(all_mainline)
        while remaining:
            self._stats['num_steps'] += 1
            next = remaining[:100]
            remaining = remaining[len(next):]
            res = _exec(_add_n_params(
                "SELECT parent FROM parent WHERE child in (%s)",
                len(next)), next)
            next_p = [p[0] for p in res if p[0] not in all_ancestors]
            all_ancestors.update(next_p)
            remaining.extend(next_p)
        self._stats['query_time'] += (time.time() - t)
        # Using this shortcut to grab the mainline first helps, but not a lot.
        # Probably because the limiting factor is the 'child in (...)' step,
        # which is 100 entries or so. (note that setting the range to :1000
        # shows a failure, which indicates the old code path was definitely
        # capped at a maximum range.)
        # 1.719s walk_ancestry       
        # 0.198s walk_ancestry_db_ids
        # 0.164s walk_ancestry_range
        return all_ancestors

    def walk_ancestry_range_and_dotted(self):
        """Walk the whole ancestry.

        Use the information from the dotted_revno table and the mainline_parent
        table to speed things up.
        """
        db_id = self._get_db_id(self._branch_tip_rev_id)
        all_ancestors = set()
        t = time.time()
        while db_id is not None:
            self._stats['num_steps'] += 1
            range_res = self._cursor.execute(
                "SELECT pkey, tail"
                "  FROM mainline_parent_range"
                " WHERE head = ?"
                " ORDER BY count DESC LIMIT 1",
                (db_id,)).fetchone()
            if range_res is None:
                next_db_id = self._get_lh_parent_db_id(db_id)
                merged_revs = self._cursor.execute(
                    "SELECT merged_revision FROM dotted_revno"
                    " WHERE tip_revision = ?",
                    (db_id,)).fetchall()
                all_ancestors.update([r[0] for r in merged_revs])
            else:
                pkey, next_db_id = range_res
                merged_revs = self._cursor.execute(
                    "SELECT merged_revision FROM dotted_revno, mainline_parent"
                    " WHERE tip_revision = mainline_parent.revision"
                    "   AND mainline_parent.range = ?",
                    (pkey,)).fetchall()
                all_ancestors.update([r[0] for r in merged_revs])
            db_id = next_db_id
        self._stats['query_time'] += (time.time() - t)
        return all_ancestors

    def heads(self, revision_ids):
        """Compute Graph.heads() on the given data."""
        raise NotImplementedError(self.heads)
