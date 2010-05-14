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

"""Test aspects of the importer code."""

import os
import tempfile
import threading
import time

from bzrlib import (
    graph,
    tests,
    branch,
    )
from loggerhead import history_db


class MockVF(object):

    def __init__(self, mock_branch):
        self._mock_branch = mock_branch

    def get_known_graph_ancestry(self, key):
        # Note that this ignores the 'key' parameter, but that should be ok for
        # our use case
        return self._mock_branch._get_keys_known_graph()


class MockRepository(object):
    
    def __init__(self, mock_branch):
        self._mock_branch = mock_branch

    @property
    def revisions(self):
        return MockVF(self._mock_branch)

    def get_parent_map(self, revision_ids):
        pmap = {}
        anc = self._mock_branch._ancestry
        for rev_id in revision_ids:
            if rev_id in anc:
                pmap[rev_id] = anc[rev_id]
        return pmap

        
class MockBranch(object):
    """Fake a Branch object, to provide the apis we need to have."""

    def __init__(self, ancestry, tip_revision):
        self._tip_revision = tip_revision
        self._ancestry = ancestry

    def _get_keys_known_graph(self):
        key_ancestry = dict(((r,), tuple([(p,) for p in ps]))
                            for r, ps in self._ancestry.iteritems())
        return graph.KnownGraph(key_ancestry)

    def last_revision(self):
        return self._tip_revision

    @property
    def repository(self):
        return MockRepository(self)

    def get_revision_id_to_revno_map(self):
        kg = self._get_keys_known_graph()
        merge_sorted = kg.merge_sort((self._tip_revision,))
        return dict((node.key[0], node.revno) for node in merge_sorted)


class TestCaseWithGraphs(tests.TestCase):

    def make_branch_with_simple_history(self):
        # Graph:
        #  A
        #  |
        #  B
        #  |\
        #  C D
        #  |/
        #  E
        ancestry = {'A': (), 'B': ('A',), 'C': ('B',), 'D': ('B',),
                    'E': ('C', 'D')}
        return MockBranch(ancestry, 'E')
        
    def make_interesting_branch(self):
        # Graph looks like:
        # A         1
        # |\        |\
        # | \       | \
        # |  \      |  \
        # |   B     |   1.1.1 ------.
        # |  /|\    |   |     \      \
        # | C E |   |   1.1.2   1.2.1 |
        # |/ / /    | /       /      /
        # D F H     2   1.2.2   1.3.1
        # |/ X      | /      \ /
        # G / J     3  .------' 1.2.3
        # |/ /|\    | /        /    \
        # I / K L   4        1.2.4    1.4.1
        # |/  |/    |         |     /
        # N   M     5        1.2.5
        # |  /
        # | /
        # |/
        # O
        ancestry = {'A': (),
                    'B': ('A',),
                    'C': ('B',),
                    'D': ('A', 'C'),
                    'E': ('B',),
                    'F': ('E',),
                    'G': ('D', 'F'),
                    'H': ('B',),
                    'I': ('G', 'H'),
                    'J': ('F',),
                    'K': ('J',),
                    'L': ('J',),
                    'M': ('K', 'L'),
                    'N': ('I', 'J'),
                    'O': ('N', 'M'),
                    }
        return MockBranch(ancestry, 'O')

    def make_branch_with_ghosts(self):
        # Simple ancestry:
        # A
        # |
        # B G?
        # |/|
        # C D
        # |/
        # E
        #
        # Both C and D refer to 'G' but that revision isn't actually present
        ancestry = {'A': (),
                    'B': ('A',),
                    'C': ('B', 'G'),
                    'D': ('G',),
                    'E': ('C', 'D'),
                   }
        return MockBranch(ancestry, 'E')

    def grab_interesting_ids(self, rev_id_to_db_id):
        for rev_id in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
            setattr(self, '%s_id' % (rev_id,), rev_id_to_db_id.get(rev_id))


class TestImporter(TestCaseWithGraphs):

    def test_build(self):
        b = self.make_interesting_branch()
        revno_map = b.get_revision_id_to_revno_map()
        self.assertEqual({'A': (1,), 'B': (1,1,1), 'C': (1,1,2),
                          'D': (2,), 'E': (1,2,1), 'F': (1,2,2),
                          'G': (3,), 'H': (1,3,1), 'I': (4,),
                          'J': (1,2,3,), 'K': (1,2,4), 'L': (1,4,1),
                          'M': (1,2,5,), 'N': (5,), 'O': (6,)},
                         revno_map)

    def test_import_non_incremental(self):
        b = self.make_interesting_branch()
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        cur = importer._db_conn.cursor()
        revs = cur.execute("SELECT revision_id, db_id, gdfo"
                           "  FROM revision").fetchall()
        # Track the db_ids that are assigned
        rev_to_db_id = dict((r[0], r[1]) for r in revs)
        db_to_rev_id = dict((r[1], r[0]) for r in revs)
        rev_gdfo = dict((r[0], r[2]) for r in revs)
        self.assertEqual({'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 3, 'F': 4,
                          'G': 5, 'H': 3, 'I': 6, 'J': 5, 'K': 6, 'L': 6,
                          'M': 7, 'N': 7, 'O': 8}, rev_gdfo)
        dotted_info = cur.execute(
            "SELECT tip_revision, merged_revision, revno"
            "  FROM dotted_revno").fetchall()
        self.grab_interesting_ids(rev_to_db_id)
        expected = {
            self.A_id: sorted([(self.A_id, '1')]),
            self.D_id: sorted([(self.B_id, '1.1.1'), (self.C_id, '1.1.2'),
                                (self.D_id, '2')]),
            self.G_id: sorted([(self.E_id, '1.2.1'), (self.F_id, '1.2.2'),
                               (self.G_id, '3')]),
            self.I_id: sorted([(self.H_id, '1.3.1'), (self.I_id, '4')]),
            self.N_id: sorted([(self.J_id, '1.2.3'), (self.N_id, '5')]),
            self.O_id: sorted([(self.K_id, '1.2.4'), (self.L_id, '1.4.1'),
                               (self.M_id, '1.2.5'), (self.O_id, '6')]),
        }
        actual = {}
        for tip_rev, merge_rev, revno in dotted_info:
            val = actual.setdefault(tip_rev, [])
            val.append((merge_rev, revno))
            val.sort()
        self.assertEqual(expected, actual)

    def test_import_records_ghosts(self):
        b = self.make_branch_with_ghosts()
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        cur = importer._db_conn.cursor()
        res = cur.execute("SELECT revision_id"
                          "  FROM ghost NATURAL JOIN revision")
        self.assertEqual(['G'], [r[0] for r in res])

    def test__update_ancestry_records_ghosts(self):
        b = self.make_branch_with_ghosts()
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer._update_ancestry('G')
        cur = importer._db_conn.cursor()
        res = cur.execute("SELECT revision_id"
                          "  FROM ghost NATURAL JOIN revision")
        self.assertEqual(['G'], [r[0] for r in res])

    def test__update_ancestry_from_scratch(self):
        b = self.make_interesting_branch()
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer._update_ancestry('O')
        cur = importer._db_conn.cursor()
        # revision and parent should be fully populated
        rev_gdfo = dict(cur.execute("SELECT revision_id, gdfo"
                                    "  FROM revision").fetchall())
        # Track the db_ids that are assigned
        self.assertEqual({'A': 1, 'B': 2, 'C': 3, 'D': 4, 'E': 3, 'F': 4,
                          'G': 5, 'H': 3, 'I': 6, 'J': 5, 'K': 6, 'L': 6,
                          'M': 7, 'N': 7, 'O': 8}, rev_gdfo)
        parent_map = dict(((c_id, p_idx), p_id) for c_id, p_id, p_idx in
            cur.execute("SELECT c.revision_id, p.revision_id, parent_idx"
                        "  FROM parent, revision c, revision p"
                        " WHERE parent.parent = p.db_id"
                        "   AND parent.child = c.db_id").fetchall())
        self.assertEqual({('B', 0): 'A', ('C', 0): 'B', ('D', 0): 'A',
                          ('D', 1): 'C', ('E', 0): 'B', ('F', 0): 'E',
                          ('G', 0): 'D', ('G', 1): 'F', ('H', 0): 'B',
                          ('I', 0): 'G', ('I', 1): 'H', ('J', 0): 'F',
                          ('K', 0): 'J', ('L', 0): 'J', ('M', 0): 'K',
                          ('M', 1): 'L', ('N', 0): 'I', ('N', 1): 'J',
                          ('O', 0): 'N', ('O', 1): 'M',
                         }, parent_map)

    def test__update_ancestry_partial(self):
        b = self.make_interesting_branch()
        importer = history_db.Importer(':memory:', b, incremental=False)
        # We intentionally seed the data with some wrong values, to see if the
        # result uses them.
        cur = importer._db_conn.cursor()
        cur.executemany("INSERT INTO revision (revision_id, gdfo)"
                        " VALUES (?, ?)", [('A', 11)])
        importer._graph = None
        importer._update_ancestry('O')
        cur = importer._db_conn.cursor()
        # revision and parent should be fully populated
        rev_gdfo = dict(cur.execute("SELECT revision_id, gdfo"
                                    "  FROM revision").fetchall())
        # Track the db_ids that are assigned
        self.assertEqual({'A': 11, 'B': 12, 'C': 13, 'D': 14, 'E': 13,
                          'F': 14, 'G': 15, 'H': 13, 'I': 16, 'J': 15,
                          'K': 16, 'L': 16, 'M': 17, 'N': 17, 'O': 18},
                         rev_gdfo)
        parent_map = dict(((c_id, p_idx), p_id) for c_id, p_id, p_idx in
            cur.execute("SELECT c.revision_id, p.revision_id, parent_idx"
                        "  FROM parent, revision c, revision p"
                        " WHERE parent.parent = p.db_id"
                        "   AND parent.child = c.db_id").fetchall())
        self.assertEqual({('B', 0): 'A', ('C', 0): 'B', ('D', 0): 'A',
                          ('D', 1): 'C', ('E', 0): 'B', ('F', 0): 'E',
                          ('G', 0): 'D', ('G', 1): 'F', ('H', 0): 'B',
                          ('I', 0): 'G', ('I', 1): 'H', ('J', 0): 'F',
                          ('K', 0): 'J', ('L', 0): 'J', ('M', 0): 'K',
                          ('M', 1): 'L', ('N', 0): 'I', ('N', 1): 'J',
                          ('O', 0): 'N', ('O', 1): 'M',
                         }, parent_map)


class Test_IncrementalMergeSort(TestCaseWithGraphs):

    def make_inc_merger(self, branch, imported_tip, new_tip):
        branch._tip_revision = imported_tip
        importer = history_db.Importer(':memory:', branch, incremental=False)
        importer.do_import()
        importer._update_ancestry(new_tip)
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer,
            importer._rev_id_to_db_id[new_tip])
        return inc_merger

    def assertScheduledStack(self, inc_merger, expected):
        """Check that the merge_sort result is as expected."""
        actual = [(node.key, node.revno, node.end_of_merge, node.merge_depth)
                  for node in inc_merger._scheduled_stack]
        self.assertEqual(expected, actual)

    def test_step_by_step(self):
        b = self.make_interesting_branch()
        inc_merger = self.make_inc_merger(b, 'G', 'N')
        inc_merger._find_needed_mainline()
        self.assertEqual([self.N_id, self.I_id], inc_merger._mainline_db_ids)
        self.assertEqual(self.G_id, inc_merger._imported_mainline_id)
        self.assertEqual(set([self.N_id, self.I_id]),
                         inc_merger._interesting_ancestor_ids)
        # This should populate ._search_tips, as well as gdfo information
        inc_merger._get_initial_search_tips()
        self.assertEqual(set([self.J_id, self.H_id]), inc_merger._search_tips)
        # We should have taken a single step on the mainline
        self.assertEqual(self.D_id, inc_merger._imported_mainline_id)
        self.assertEqual(4, inc_merger._imported_gdfo)
        self.assertEqual({self.D_id: 4, self.J_id: 5, self.H_id: 3},
                         inc_merger._known_gdfo)
        # Both J has gdfo > D so it is quickly removed. H does not, so it is
        # left behind.
        self.assertEqual([self.H_id],
             inc_merger._split_search_tips_by_gdfo([self.J_id, self.H_id]))
        self.assertEqual(set([self.N_id, self.I_id, self.J_id]),
                         inc_merger._interesting_ancestor_ids)
        # Checking children should notice that all known children are fine, so
        # H now gets marked interesting
        self.assertEqual([],
                 inc_merger._split_interesting_using_children([self.H_id]))
        self.assertEqual(set([self.N_id, self.I_id, self.J_id, self.H_id]),
                         inc_merger._interesting_ancestor_ids)
        # Since we know all search tips are interesting, step again.
        inc_merger._step_search_tips()
        self.assertEqual(set([self.B_id, self.F_id]), inc_merger._search_tips)
        self.assertEqual(set([self.N_id, self.I_id, self.J_id, self.H_id]),
                         inc_merger._interesting_ancestor_ids)
        # F is known-merged, so the first step should filter it from unknowns,
        # and remove it from the search tips
        # However B is not known yet, and has GDFO < D (since it was merged
        # in).
        # However E is a child of B, and that is already known to be merged. So
        # B gets filtered out in the child step, and removed as a search tip
        self.assertEqual([self.B_id],
             inc_merger._split_search_tips_by_gdfo([self.B_id, self.F_id]))
        self.assertEqual(set([self.B_id]), inc_merger._search_tips)
        self.assertEqual([],
                     inc_merger._split_interesting_using_children([self.B_id]))
        self.assertEqual(set([]), inc_merger._search_tips)
        # At this point, we will stop searching. XXX: B's info has not been
        # loaded yet...
        self.assertEqual(self.D_id, inc_merger._imported_mainline_id)
        self.assertEqual(4, inc_merger._imported_gdfo)
        self.assertEqual({self.E_id: ((1,2,1), 1, 1),
                          self.F_id: ((1,2,2), 0, 1),
                          self.G_id: ((3,), 0, 0),
                         }, inc_merger._imported_dotted_revno)
        self.assertEqual(set([(1,2,1), (1,2,2), (3,)]),
                         inc_merger._known_dotted)
        # At this point, B_id isn't in _imported_dotted_revno, so we loop to
        # ensure we have enough dotted_revno data
        inc_merger._ensure_lh_parent_info()
        self.assertEqual(self.A_id, inc_merger._imported_mainline_id)
        self.assertEqual(1, inc_merger._imported_gdfo)
        self.assertEqual({self.B_id: ((1,1,1), 1, 1),
                          self.C_id: ((1,1,2), 0, 1),
                          self.D_id: ((2,), 0, 0),
                          self.E_id: ((1,2,1), 1, 1),
                          self.F_id: ((1,2,2), 0, 1),
                          self.G_id: ((3,), 0, 0),
                         }, inc_merger._imported_dotted_revno)
        self.assertEqual({0: 0, 1: 2}, inc_merger._revno_to_branch_count)
        self.assertEqual({0: 3, (1, 1): 2, (1, 2): 2},
                         inc_merger._branch_to_child_count)
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger,
                         [(self.H_id, (1, 3, 1), True, 1),
                          (self.I_id, (4,), False, 0),
                          (self.J_id, (1, 2, 3), True, 1),
                          (self.N_id, (5,), False, 0),
                         ])

    def test__find_interesting_ancestry(self):
        b = self.make_interesting_branch()
        b._tip_revision = 'G' # Something older
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('O')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.O_id)
        # This should step through the ancestry, and load in the necessary
        # data. Check the final state
        inc_merger._find_interesting_ancestry()
        self.assertEqual([self.O_id, self.N_id, self.I_id],
                         inc_merger._mainline_db_ids)
        # We should stop loading A, I need to figure out why it gets loaded
        self.assertEqual(self.A_id, inc_merger._imported_mainline_id)
        self.assertEqual(1, inc_merger._imported_gdfo)
        self.assertEqual(set([self.H_id, self.I_id, self.J_id, self.K_id,
                              self.L_id, self.M_id, self.N_id, self.O_id]),
                         inc_merger._interesting_ancestor_ids)
        self.assertEqual(set([]), inc_merger._search_tips)
        self.assertEqual({self.B_id: ((1,1,1), 1, 1),
                          self.C_id: ((1,1,2), 0, 1),
                          self.D_id: ((2,), 0, 0),
                          self.E_id: ((1,2,1), 1, 1),
                          self.F_id: ((1,2,2), 0, 1),
                          self.G_id: ((3,), 0, 0),
                         }, inc_merger._imported_dotted_revno)
        self.assertEqual(set([(1,1,1), (1,1,2), (2,), (1,2,1), (1,2,2), (3,)]),
                         inc_merger._known_dotted)

    def test__split_gdfo_handles_mainline_tip(self):
        b = self.make_branch_with_simple_history()
        inc_merger = self.make_inc_merger(b, 'C', 'E')
        inc_merger._find_needed_mainline()
        inc_merger._get_initial_search_tips()
        self.assertEqual(set([self.D_id]), inc_merger._search_tips)
        self.assertEqual(self.B_id, inc_merger._imported_mainline_id)
        # First step knows right away that D is too new
        self.assertEqual([],
            inc_merger._split_search_tips_by_gdfo([self.D_id]))
        inc_merger._step_search_tips()
        self.assertEqual(set([self.B_id]), inc_merger._search_tips)
        # B_id can't be merged into B_id, but *because* it is B_id :)
        self.assertEqual([],
            inc_merger._split_search_tips_by_gdfo([self.B_id]))
        self.assertEqual(set([]), inc_merger._search_tips)
        self.assertEqual(set([self.D_id, self.E_id]),
                         inc_merger._interesting_ancestor_ids)

    def test__step_search_tips_skips_already_seen(self):
        # Simpler graph:
        # A
        # |
        # B
        # |\
        # | C
        # | |\
        # | D E
        # |/|/
        # F G
        # |/
        # H
        # In this case, first step should go to G & D, when stepping from
        # there, G => D should not continue on D, since it has already been
        # seen, but we should include E.
        ancestry = {'A': (),
                    'B': ('A',),
                    'C': ('B',),
                    'D': ('C',),
                    'E': ('C',),
                    'F': ('B', 'D'),
                    'G': ('D', 'E'),
                    'H': ('F', 'G'),
                    }
        b = MockBranch(ancestry, 'B')
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('H')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.H_id)
        inc_merger._find_needed_mainline()
        self.assertEqual([self.H_id, self.F_id], inc_merger._mainline_db_ids)
        self.assertEqual(self.B_id, inc_merger._imported_mainline_id)
        inc_merger._get_initial_search_tips()
        self.assertEqual(set([self.D_id, self.G_id]), inc_merger._search_tips)
        # Both have higher-than-mainline gdfos
        self.assertEqual([],
                 inc_merger._split_search_tips_by_gdfo([self.D_id, self.G_id]))
        inc_merger._step_search_tips()
        # It should want to include D_id, but it should know that we've already
        # been there
        self.assertEqual(set([self.C_id, self.E_id]), inc_merger._search_tips)

    def test_maintain_branch_counter_correct(self):
        # The trick is that if we have already imported to N, then we will be
        # hiding the correct branch counter for revno 1. We will see it as 2
        # from the revisions we've loaded, but really it is 3 because of the H
        # branch.
        b = self.make_interesting_branch()
        b._tip_revision = 'N'
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('O')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.O_id)
        inc_merger._find_interesting_ancestry()
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger,
                         [(self.K_id, (1, 2, 4), True, 1),
                          (self.L_id, (1, 4, 1), True, 2),
                          (self.M_id, (1, 2, 5), False, 1),
                          (self.O_id, (6,), False, 0),
                         ])
        # We have to load I to get H, but at that point we've seen a (1,X,1)
        # revision, so we know we've seen the newest merged branch.
        self.assertEqual(self.G_id, inc_merger._imported_mainline_id)

    def test_handles_simple_child(self):
        ancestry = {'A': (), 'B': ('A',), 'C': ('B',), 'D': ('C',)}
        b = MockBranch(ancestry, 'C')
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('D')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.D_id)
        inc_merger._find_interesting_ancestry()
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger, [(self.D_id, (4,), False, 0)])

    def test_assigns_first_branch_without_loading_history(self):
        # Importing E + D should not have to load anything before B
        b = self.make_branch_with_simple_history()
        inc_merger = self.make_inc_merger(b, 'C', 'E')
        inc_merger._find_interesting_ancestry()
        self.assertEqual(self.A_id, inc_merger._imported_mainline_id)
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger, [
            (self.D_id, (2,1,1), True, 1),
            (self.E_id, (4,), False, 0),
            ])
        self.assertEqual(self.A_id, inc_merger._imported_mainline_id)

    def test_handles_empty_branch(self):
        ancestry = {}
        b = MockBranch(ancestry, 'null:')
        importer = history_db.Importer(':memory:', b, incremental=True)
        importer.do_import()

    def test_handles_multi_roots(self):
        # Graph:
        #  A B
        #  |/
        #  C 
        #  |
        #  D E
        #  |/
        #  F
        # Since D is already imported, the incremental importer will only see
        # E. However, we have to load everything, so that we can get the
        # numbering for a 0-based rev correct.
        ancestry = {'A': (), 'B': (), 'C': ('A', 'B'), 'D': ('C',), 'E': (),
                    'F': ('D', 'E')}
        b = MockBranch(ancestry, 'D')
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('F')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.F_id)
        inc_merger._find_interesting_ancestry()
        self.assertEqual(self.C_id, inc_merger._imported_mainline_id)
        self.assertEqual(set([self.E_id, self.F_id]),
                         inc_merger._interesting_ancestor_ids)
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger,
                         [(self.E_id, (0, 2, 1), True, 1),
                          (self.F_id, (4,), False, 0),
                         ])

    def test_handles_partial_complex_multi_roots(self):
        # Graph:
        #  A B
        #  |/ \
        #  C E |
        #  | | |
        #  D F |
        #  |/ /
        #  G H
        #  |/
        #  I J
        #  |/
        #  K
        
        # Ideas:
        # 1) (0,1,2) gets merged after (0,2,2). Which means we certainly have
        #    to find (0,2,2) to get (0, 3, 1) correct. Even though we've found
        #    a possible extra root.
        # 2) We don't have to go all the way back to find (0,1,1) as soon as we
        #    find (0,2,1).
        ancestry = {'A': (), 'B': (), 'C': ('A', 'B'), 'D': ('C',), 'E': (),
                    'F': ('E',), 'G': ('D', 'F'), 'H': ('B',), 'I': ('G', 'H'),
                    'J': (), 'K': ('I', 'J')}
        b = MockBranch(ancestry, 'I')
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('K')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.K_id)
        inc_merger._find_interesting_ancestry()
        self.assertEqual(self.G_id, inc_merger._imported_mainline_id)
        self.assertEqual(set([self.K_id, self.J_id]),
                         inc_merger._interesting_ancestor_ids)
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger,
                         [(self.J_id, (0, 3, 1), True, 1),
                          (self.K_id, (6,), False, 0),
                         ])
        # We only have to walk back and stop at D because we have found (0,2,1)
        # which must be the latest branch.
        self.assertEqual(self.D_id, inc_merger._imported_mainline_id)

    def test_one_rev(self):
        # Trivial ancestry:
        #  A
        ancestry = {'A': ()}
        b = MockBranch(ancestry, 'A')
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer._update_ancestry('A')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.A_id)
        inc_merger._find_interesting_ancestry()
        inc_merger._compute_merge_sort()
        self.assertScheduledStack(inc_merger,
                         [(self.A_id, (1,), True, 0),
                         ])

    def test_skips_ghosts(self):
        b = self.make_branch_with_ghosts()
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer._update_ancestry('E')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.E_id)
        inc_merger._find_interesting_ancestry()
        inc_merger._compute_merge_sort()
        # G is not mentioned in merge_sorted, neither as a left-hand parent,
        # nor as a right-hand parent
        self.assertScheduledStack(inc_merger,
                         [(self.A_id, (1,), True, 0),
                          (self.B_id, (2,), False, 0),
                          (self.C_id, (3,), False, 0),
                          (self.D_id, (0, 1, 1), True, 1),
                          (self.E_id, (4,), False, 0),
                         ])

    def test_handle_partial_ghosts(self):
        b = self.make_branch_with_ghosts()
        b._tip_revision = 'C'
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('E')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_merger = history_db._IncrementalMergeSort(importer, self.E_id)
        inc_merger.topo_order()
        # G is not mentioned in merge_sorted, neither as a left-hand parent,
        # nor as a right-hand parent
        self.assertScheduledStack(inc_merger,
                         [(self.D_id, (0, 1, 1), True, 1),
                          (self.E_id, (4,), False, 0),
                         ])

    def test_ignore_uninteresting_ancestors(self):
        # Graph:
        # A
        # |\
        # B C
        # |X|
        # D E
        # |\| 
        # | F
        # |/
        # G
        #
        # Some did work C, while trunk evolved to B. C was landed, while
        # concurrently someone tried to update C for the trunk changes.
        # After trying to cleanup, they had to do it again.
        # If D is imported, we should only number E and F, we shouldn't try to
        # include B or C
        # Note: This ancestry was taken from bzr.dev@5114.1.1, which
        # demonstrated the race condition.
        ancestry = {'A': (), 'B': ('A',), 'C': ('A',), 'D': ('B', 'C'),
                    'E': ('C', 'B'), 'F': ('E', 'D'), 'G': ('D', 'F')}
        b = MockBranch(ancestry, 'G')
        inc_merger = self.make_inc_merger(b, 'D', 'G')
        inc_merger.topo_order()
        self.assertScheduledStack(inc_merger,
                         [(self.E_id, (1, 1, 2), True, 1),
                          (self.F_id, (1, 1, 3), False, 1),
                          (self.G_id, (4,), False, 0),
                         ])
        self.assertTrue(self.E_id in inc_merger._imported_dotted_revno)
        self.assertTrue((1,1,2) in inc_merger._known_dotted)

    def test_handles_already_imported(self):
        b = self.make_interesting_branch()
        inc_merger = self.make_inc_merger(b, 'O', 'O')
        inc_merger.topo_order()
        self.assertScheduledStack(inc_merger, [])


class _InterLocker(object):
    """Wrapper around thread locks to help with testing.

    The idea is that one thread will be wanting to acquire a lock. When it does
    so, we block it, and signal the testing thread that the acquisition was
    attempted, so now would be a good time to check that things are proceeding
    properly.
    """

    def __init__(self):
        self._monitored_lock = threading.Lock()
        # We start the lock in blocked mode, so that we have to call
        # self.wait_for_acquire before we will let the other thread through.
        self._monitored_lock.acquire()
        self._acquire_called = False
        self._release_called = False
        self._acquireCondition = threading.Condition()
        self._releaseCondition = threading.Condition()
        self._max_wait_time = 1.0

    def acquire(self):
        """Same as threading.Lock.acquire.
        
        This is meant to be called by the thread you are testing / monitoring.
        """
        self._acquireCondition.acquire()
        self._acquire_called = True
        self._acquireCondition.notify()
        self._acquireCondition.release()
        # Acquire the actual lock that this is substituting for
        t_wait_start = time.time()
        while not self._monitored_lock.acquire(False):
            t_waited = time.time() - t_wait_start
            if t_waited > self._max_wait_time:
                raise RuntimeError('Acquire timed out after %.1fs'
                                   % (t_waited,))
            time.sleep(0.1)

    def release(self):
        """See threading.Lock.release."""
        self._monitored_lock.release()
        self._releaseCondition.acquire()
        self._release_called = True
        self._releaseCondition.notify()
        self._releaseCondition.release()

    def _wait_for_condition(self, condition, evaluator, name, timeout):
        """Wait for the given condition to trigger.

        :param condition: A Condition variable
        :param evaluator: A callback to indicate if the condition has actually
            been fulfilled. Should return True if the condition is ready to go.
        :param name: An associated name for the condition (used for error
            messages)
        :param timeout: If the condition hasn't triggered after timeout
            seconds, raise an error.
        :return: When this function returns, the condition lock will be held.
            Callers are responsible for calling .release()
        """
        t_wait_start = time.time()
        condition.acquire()
        while not evaluator():
            t_waited = time.time() - t_wait_start
            if t_waited > timeout:
                raise RuntimeError('%s not triggered after %.1f seconds'
                                   % (name, t_waited))
            condition.wait(0.1)

    def wait_for_acquire(self):
        """Called by the test thread.

        This will wait on a Condition until another thread calls 'acquire'.
        Once that happens, that thread will be blocked, and this call will
        return. Follow this up with 'wait_for_release' to let the other
        thread continue, and block until release is called.
        """
        self._wait_for_condition(self._acquireCondition, 
            lambda: self._acquire_called, 'acquire', self._max_wait_time)
        # Let the other thread start processing from the acquire.
        self._monitored_lock.release()
        self._acquireCondition.release()

    def wait_for_release(self):
        """Block this thread until self.release() is called."""
        self._wait_for_condition(self._releaseCondition,
            lambda: self._release_called, 'release', self._max_wait_time)
        self._releaseCondition.release()


class TestQuerier(TestCaseWithGraphs):

    def get_db_path(self):
        fn, temp = tempfile.mkstemp(prefix='test-bzr-history-db-', suffix='.db')
        os.close(fn)
        self.addCleanup(os.remove, temp)
        return temp
        
    def test_importer_lock(self):
        temp = self.get_db_path()
        b = self.make_interesting_branch()
        b._tip_revision = 'I'
        importer = history_db.Importer(temp, b, incremental=False)
        importer.do_import()
        del importer
        b._tip_revision = 'O'
        lock = _InterLocker()
        query = history_db.Querier(temp, b)
        query.set_importer_lock(lock)
        query.close() # We will be doing the rest in another thread, and
                      # sqlite connections can't be shared between threads
        t = threading.Thread(target=query.ensure_branch_tip)
        t.start()
        # TODO: The only bit we don't handle is that we'd really like the test
        #       to fail if the other thread didn't exit cleanly. However, this
        #       is good enough for now.
        self.addCleanup(t.join)
        lock.wait_for_acquire()
        # At this point, the database should not have been updated yet.
        conn = history_db.dbapi2.connect(temp)
        res = conn.cursor().execute("SELECT db_id FROM revision"
                                    " WHERE revision_id = ?",
                                    ('O',)).fetchone()
        self.assertIs(None, res)
        lock.wait_for_release()
        # Now that it has gotten the lock and finished, we should have the tip
        # imported properly.
        res = conn.cursor().execute("SELECT tip_revision"
                                    "  FROM revision, dotted_revno"
                                    " WHERE tip_revision = merged_revision"
                                    "   AND revision_id = ?",
                                    ('O',)).fetchone()
        self.assertIsNot(None, res)

    def test_get_merged_into(self):
        db_path = self.get_db_path()
        b = self.make_interesting_branch()
        importer = history_db.Importer(db_path, b, incremental=False)
        importer.do_import()
        del importer
        query = history_db.Querier(db_path, b)
        rev_to_mainline_map = query.get_mainline_where_merged(
            ['E', 'F', 'H', 'L'])
        self.assertEqual({'E': 'G', 'F': 'G', 'H': 'I', 'L': 'O'},
                         rev_to_mainline_map)

    def test_empty_branche(self):
        db_path = self.get_db_path()
        b = MockBranch({}, 'null:')
        query = history_db.Querier(db_path, b)
        query.ensure_branch_tip()
        query.close()
