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
    trace,
    ui,
    )

from bzrlib.plugins.history_db import schema


class Importer(object):
    """Import data from bzr into the history_db."""

    def __init__(self, db_path, a_branch):
        db_conn = dbapi2.connect(db_path)
        self._db_conn = db_conn
        self._ensure_schema()
        self._cursor = self._db_conn.cursor()
        self._branch = a_branch
        self._branch_tip_rev_id = a_branch.last_revision()
        self._branch_tip_key = (self._branch_tip_rev_id,)
        self._get_graph()
        self._rev_id_to_db_id = {}
        self._stats = defaultdict(lambda: 0)

    def _ensure_schema(self):
        if not schema.is_initialized(self._db_conn, dbapi2.OperationalError):
            schema.create_sqlite_db(self._db_conn)
            trace.note('Initialized database')

    def _ensure_revisions(self, revision_ids):
        schema.ensure_revisions(self._cursor, revision_ids,
                                self._rev_id_to_db_id, self._graph)

    def _get_graph(self):
        repo = self._branch.repository
        self._graph = repo.revisions.get_known_graph_ancestry(
            [self._branch_tip_key])

    def _insert_nodes(self, tip_rev_id, nodes):
        """Insert all of the nodes mentioned into the database."""
        self._stats['_insert_node_calls'] += 1
        self._ensure_revisions([n.key[0] for n in nodes])
        res = self._cursor.execute(
            "SELECT count(*) FROM dotted_revno JOIN revision"
            "    ON dotted_revno.tip_revision = revision.db_id"
            " WHERE revision_id = ?"
            "   AND tip_revision = merged_revision",
            (tip_rev_id,)).fetchone()
        if res[0] > 0:
            # Not importing anything because the data is already present
            return False
        self._stats['total_nodes_inserted'] += len(nodes)
        tip_db_id = self._rev_id_to_db_id[tip_rev_id]
        for node in nodes:
            schema.create_dotted_revno(self._cursor,
                tip_revision=tip_db_id,
                merged_revision=self._rev_id_to_db_id[node.key[0]],
                revno='.'.join(map(str, node.revno)),
                end_of_merge=node.end_of_merge,
                merge_depth=node.merge_depth)
        return True

    def _update_parents(self, nodes):
        """Update parent information for all these nodes."""
        # Get the keys and their parents
        parent_map = dict(
            (n.key[0], [p[0] for p in self._graph.get_parent_keys(n.key)])
            for n in nodes)
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

    def do_import(self):
        merge_sorted = self._graph.merge_sort(self._branch_tip_key)
        try:
            pb = ui.ui_factory.nested_progress_bar()
            last_mainline_rev_id = None
            new_nodes = []
            for idx, node in enumerate(merge_sorted):
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
            if new_nodes:
                assert last_mainline_rev_id is not None
                self._insert_nodes(last_mainline_rev_id, new_nodes)
                new_nodes = []
        except:
            self._db_conn.rollback()
            raise
        else:
            self._db_conn.commit()

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

    def _insert_range(self, range_db_ids):
        head_db_id = range_db_ids[0]
        tail_db_id = range_db_ids[-1]
        self._cursor.execute("INSERT INTO mainline_parent_range"
                             " (head, tail, count) VALUES (?, ?, ?)",
                             (head_db_id, tail_db_id, len(range_db_ids)))
        # Isn't there a dbapi to get back the row we just inserted?
        range_key = self._cursor.execute(
            "SELECT pkey FROM mainline_parent_range"
            " WHERE head = ? AND tail = ?",
            (head_db_id, tail_db_id)).fetchone()[0]
        self._stats['ranges_inserted'] += 1
        # Note that head and tail will get double values. The start range will
        # have head, then tail, the next range will have head == tail, etc.
        self._stats['revs_in_ranges'] += len(range_db_ids)
        # Note that inserting head and tail into mainline_parent is redundant,
        # since the data is available. But I'm sure it will make the *queries*
        # much easier.
        self._cursor.executemany(
            "INSERT INTO mainline_parent (range, revision)"
            " VALUES (?, ?)", [(range_key, d) for d in range_db_ids])

    def build_mainline_cache(self):
        """Given the current branch, cache mainline information."""
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
        #     potentially be done multiple times.)
        # The specific thresholds are arbitrary, but it should mean you would
        # average a larger 'minimum' size. And (c) helps avoid fragmentation.
        # (Where multiple imports turn a 100-revision range into 20 5-revision
        # ranges.)
        head_rev_id = self._branch_tip_rev_id
        self._ensure_revisions([head_rev_id])
        cur_db_id = self._rev_id_to_db_id[head_rev_id]
        range_db_ids = []
        try:
            while cur_db_id is not None:
                range_db_ids.append(cur_db_id)
                if self._check_range_exists_for(cur_db_id):
                    # This already exists as a valid 'head' in the range cache,
                    # so we can assume that all parents are already covered in
                    # reasonable ranges.
                    break
                if len(range_db_ids) > 100:
                    # We've stepped far enough, at 101 values, we cover 100
                    # revisions (rev 1000 to rev 1100, etc), because the range
                    # is inclusive
                    self._insert_range(range_db_ids[:75])
                    # We want to start a new range, with
                    #   new_range.head == last_range.tail
                    range_db_ids = range_db_ids[74:-1]
                    continue
                parent_db_id = self._get_lh_parent_db_id(cur_db_id)
                cur_db_id = parent_db_id
            if len(range_db_ids) > 1:
                self._insert_range(range_db_ids)
        except:
            self._db_conn.rollback()
            raise
        else:
            self._db_conn.commit()


class Querier(object):
    """Perform queries on an existing history db."""

    def __init__(self, db_path, a_branch):
        db_conn = dbapi2.connect(db_path)
        self._db_conn = db_conn
        self._cursor = self._db_conn.cursor()
        self._branch = a_branch
        self._branch_tip_rev_id = a_branch.last_revision()
        self._stats = defaultdict(lambda: 0)

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

    def walk_mainline(self):
        """Walk the db, and grab all the mainline identifiers."""
        t = time.time()
        cur_id = self._branch_tip_rev_id
        all_ids = []
        while cur_id is not None:
            all_ids.append(cur_id)
            cur_id = self._get_lh_parent_rev_id(cur_id)
        self._stats['query_time'] += (time.time() - t)
        return

    def walk_mainline_db_ids(self):
        """Walk the db, and grab all the mainline identifiers."""
        t = time.time()
        db_id = self._cursor.execute('SELECT db_id FROM revision'
                                     ' WHERE revision_id = ?',
                                     (self._branch_tip_rev_id,)).fetchone()[0]
        all_ids = []
        while db_id is not None:
            all_ids.append(db_id)
            db_id = self._get_lh_parent_db_id(db_id)
        self._stats['query_time'] += (time.time() - t)
        return

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
        return len(all)

    def walk_ancestry_db_ids(self):
        _exec = self._cursor.execute
        all_ancestors = set()
        db_id = _exec("SELECT db_id FROM revision WHERE revision_id = ?",
                      (self._branch_tip_rev_id,)).fetchone()[0]
        all_ancestors.add(db_id)
        remaining = [db_id]
        while remaining:
            self._stats['num_steps'] += 1
            next = remaining[:1000]
            remaining = remaining[len(next):]
            res = _exec("SELECT parent FROM parent WHERE child in (%s)"
                        % (', '.join('?'*len(next))), tuple(next))
            next_p = [p[0] for p in res if p[0] not in all_ancestors]
            all_ancestors.update(next_p)
            remaining.extend(next_p)
        return len(all_ancestors)

    def heads(self, revision_ids):
        """Compute Graph.heads() on the given data."""
        raise NotImplementedError(self.heads)
