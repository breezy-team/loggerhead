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
        # |   B     |   1.1.1
        # |  /|     |   |     \
        # | C E     |   1.1.2   1.2.1
        # |/ /|     | /       / |
        # D F H     2   1.2.2   1.3.1
        # |/ /      | /        /
        # G /       3  .------'
        # |/        | /
        # I         4
        ancestry = {'A': (),
                    'B': ('A',),
                    'C': ('B',),
                    'D': ('A', 'C'),
                    'E': ('B',),
                    'F': ('E',),
                    'G': ('D', 'F'),
                    'H': ('E',),
                    'I': ('G', 'H'),
                    }
        return MockBranch(ancestry, 'I')

    def test_build(self):
        b = self.make_interesting_branch()
        revno_map = b.get_revision_id_to_revno_map()
        self.assertEqual({'A': (1,), 'B': (1,1,1), 'C': (1,1,2),
                          'D': (2,), 'E': (1,2,1), 'F': (1,2,2),
                          'G': (3,), 'H': (1,3,1), 'I': (4,)},
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
                          'G': 5, 'H': 4, 'I': 6}, rev_gdfo)
        dotted_info = cur.execute(
            "SELECT tip_revision, merged_revision, revno"
            "  FROM dotted_revno").fetchall()
        A = rev_to_db_id['A']
        B = rev_to_db_id['B']
        C = rev_to_db_id['C']
        D = rev_to_db_id['D']
        E = rev_to_db_id['E']
        F = rev_to_db_id['F']
        G = rev_to_db_id['G']
        H = rev_to_db_id['H']
        I = rev_to_db_id['I']
        expected = {A: sorted([(A, '1')]),
                    D: sorted([(B, '1.1.1'), (C, '1.1.2'), (D, '2')]),
                    G: sorted([(E, '1.2.1'), (F, '1.2.2'), (G, '3')]),
                    I: sorted([(H, '1.3.1'), (I, '4')])}
        actual = {}
        for tip_rev, merge_rev, revno in dotted_info:
            val = actual.setdefault(tip_rev, [])
            val.append((merge_rev, revno))
            val.sort()
        self.assertEqual(expected, actual)
