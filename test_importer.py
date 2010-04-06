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

from bzrlib import (
    graph,
    tests,
    branch,
    )
from bzrlib.plugins.history_db import history_db


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


class TestImporter(tests.TestCaseWithTransport):
    """Test aspects of importing."""

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

    def grab_interesting_ids(self, rev_id_to_db_id):
        for rev_id in 'ABCDEFGHIJKLMNO':
            setattr(self, '%s_id' % (rev_id,), rev_id_to_db_id.get(rev_id))

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
        db_conn = importer._db_conn
        cur = db_conn.cursor()
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

    def test__incremental_importer_step_by_step(self):
        b = self.make_interesting_branch()
        b._tip_revision = 'D' # Something older
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        D_id = importer._rev_id_to_db_id['D']
        self.assertEqual(1, importer._cursor.execute(
            "SELECT count(*) FROM dotted_revno, revision"
            " WHERE tip_revision = merged_revision"
            "   AND tip_revision = db_id"
            "   AND revision_id = ?", ('D',)).fetchone()[0])
        # Now work on just importing G
        importer._update_ancestry('G')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        G_id = importer._rev_id_to_db_id['G']
        inc_importer = history_db._IncrementalImporter(importer, self.G_id)
        inc_importer._find_needed_mainline()
        self.assertEqual([self.G_id], inc_importer._mainline_db_ids)
        self.assertEqual(self.D_id, inc_importer._imported_mainline_id)
        self.assertEqual(set([self.G_id]), inc_importer._interesting_ancestor_ids)
        # This should populate ._search_tips, as well as gdfo information
        inc_importer._get_initial_search_tips()
        self.assertEqual(set([self.F_id]), inc_importer._search_tips)
        self.assertEqual(4, inc_importer._imported_gdfo)
        self.assertEqual(self.D_id, inc_importer._imported_mainline_id)
        self.assertEqual({self.F_id: 4, self.D_id: 4}, inc_importer._known_gdfo)
        # D_id has gdfo >= F_id, so we know it isn't merged. So
        # _split_search_tips_by_gdfo should return nothing, and update
        # _interesting_ancestor_ids
        self.assertEqual([], inc_importer._split_search_tips_by_gdfo([self.F_id]))
        self.assertEqual(set([self.G_id, self.F_id]),
                         inc_importer._interesting_ancestor_ids)
        # Since we know that all search tips are interesting, we walk them
        inc_importer._step_search_tips()
        self.assertEqual(set([self.E_id]), inc_importer._search_tips)
        # Now when we go to _split_search_tips_by_gdfo, we aren't positive that
        # E wasn't merged, it should tell us so.
        self.assertEqual([self.E_id],
                         inc_importer._split_search_tips_by_gdfo([self.E_id]))
        # And it should not have updatde search tips or ancestor_ids
        self.assertEqual(set([self.G_id, self.F_id]),
                         inc_importer._interesting_ancestor_ids)
        self.assertEqual(set([self.E_id]), inc_importer._search_tips)
        # Checking children should notice that no children have gdfo < F, so E
        # is auto-marked as interesting.
        self.assertEqual([],
                         inc_importer._split_interesting_using_children([self.E_id]))
        self.assertEqual(set([self.E_id, self.G_id, self.F_id]),
                         inc_importer._interesting_ancestor_ids)
        # Since we know all search tips are interesting, step again.
        inc_importer._step_search_tips()
        self.assertEqual(set([self.B_id]), inc_importer._search_tips)
        self.assertEqual(set([self.E_id, self.G_id, self.F_id]),
                         inc_importer._interesting_ancestor_ids)
        # B is merged, so these two steps should not filter it out
        self.assertEqual([self.B_id],
                         inc_importer._split_search_tips_by_gdfo([self.B_id]))
        self.assertEqual([self.B_id],
                         inc_importer._split_interesting_using_children([self.B_id]))
        # At this point, we have to step the mainline, to find out if we can
        # filter out this search tip. After stepping, _imported_dotted_revno
        # should be filled with the next mainline step
        inc_importer._step_mainline()
        self.assertEqual(self.A_id, inc_importer._imported_mainline_id)
        self.assertEqual(1, inc_importer._imported_gdfo)
        self.C_id = importer._rev_id_to_db_id['C']
        self.assertEqual({self.D_id: ((2,), 0, 0), self.C_id: ((1,1,2), 0, 1),
                          self.B_id: ((1,1,1), 1, 1),
                         }, inc_importer._imported_dotted_revno)
        # Search tips is not yet changed
        self.assertEqual(set([self.B_id]), inc_importer._search_tips)
        # And now when we check gdfo again, it should remove B_id from the
        # search_tips, because it sees it in _imported_dotted_revno
        self.assertEqual([], inc_importer._split_search_tips_by_gdfo([self.B_id]))
        self.assertEqual(set([]), inc_importer._search_tips)
        inc_importer._update_info_from_dotted_revno()
        self.assertEqual({1: 1}, inc_importer._revno_to_branch_count)
        self.assertEqual({(1, 1): 2}, inc_importer._branch_to_child_count)

    def test__incremental_find_interesting_ancestry(self):
        b = self.make_interesting_branch()
        b._tip_revision = 'D' # Something older
        importer = history_db.Importer(':memory:', b, incremental=False)
        importer.do_import()
        importer._update_ancestry('O')
        self.grab_interesting_ids(importer._rev_id_to_db_id)
        inc_importer = history_db._IncrementalImporter(importer, self.O_id)
        # This should step through the ancestry, and load in the necessary
        # data. Check the final state
        inc_importer._find_interesting_ancestry()
        self.assertEqual([self.O_id, self.N_id, self.I_id, self.G_id],
                         inc_importer._mainline_db_ids)
        # We should stop loading A, I need to figure out why it gets loaded
        self.assertEqual(self.A_id, inc_importer._imported_mainline_id)
        self.assertEqual(1, inc_importer._imported_gdfo)
        self.assertEqual(set([self.E_id, self.F_id, self.G_id, self.H_id,
                              self.I_id, self.J_id, self.K_id, self.L_id,
                              self.M_id, self.N_id, self.O_id]),
                         inc_importer._interesting_ancestor_ids)
        self.assertEqual(set([]), inc_importer._search_tips)
        self.assertEqual({self.D_id: ((2,), 0, 0), self.C_id: ((1,1,2), 0, 1),
                          self.B_id: ((1,1,1), 1, 1),
                         }, inc_importer._imported_dotted_revno)
