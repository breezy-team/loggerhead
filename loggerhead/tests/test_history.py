# Copyright (C) 2011 Canonical Ltd.
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

"""Direct tests of the loggerhead/history.py module"""

from bzrlib import tests

from loggerhead import history


class TestHistoryGetRevidsFrom(tests.TestCaseWithMemoryTransport):

    def make_linear_ancestry(self):
        # Time goes up
        # rev-3
        #  |
        # rev-2
        #  |
        # rev-1
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('rev-1', None, [
            ('add', ('', 'root-id', 'directory', None))])
        builder.build_snapshot('rev-2', ['rev-1'], [])
        builder.build_snapshot('rev-3', ['rev-2'], [])
        builder.finish_series()
        b = builder.get_branch()
        self.addCleanup(b.lock_read().unlock)
        return history.History(b, {})

    def make_merged_ancestry(self):
        # Time goes up
        # rev-3
        #  |  \
        #  |  rev-2
        #  |  /
        # rev-1
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('rev-1', None, [
            ('add', ('', 'root-id', 'directory', None))])
        builder.build_snapshot('rev-2', ['rev-1'], [])
        builder.build_snapshot('rev-3', ['rev-1', 'rev-2'], [])
        builder.finish_series()
        b = builder.get_branch()
        self.addCleanup(b.lock_read().unlock)
        return history.History(b, {})

    def make_deep_merged_ancestry(self):
        # Time goes up
        # F
        # |\
        # | E
        # | |\
        # | | D
        # | |/
        # B C
        # |/
        # A
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('A', None, [
            ('add', ('', 'root-id', 'directory', None))])
        builder.build_snapshot('B', ['A'], [])
        builder.build_snapshot('C', ['A'], [])
        builder.build_snapshot('D', ['C'], [])
        builder.build_snapshot('E', ['C', 'D'], [])
        builder.build_snapshot('F', ['B', 'E'], [])
        builder.finish_series()
        b = builder.get_branch()
        self.addCleanup(b.lock_read().unlock)
        return history.History(b, {})

    def assertRevidsFrom(self, expected, his, search_revs, tip_rev):
        self.assertEqual(expected,
                         list(his.get_revids_from(search_revs, tip_rev)))

    def test_get_revids_from_simple_mainline(self):
        his = self.make_linear_ancestry()
        self.assertRevidsFrom(['rev-3', 'rev-2', 'rev-1'],
                              his, None, 'rev-3')

    def test_get_revids_from_merged_mainline(self):
        his = self.make_merged_ancestry()
        self.assertRevidsFrom(['rev-3', 'rev-1'],
                              his, None, 'rev-3')

    def test_get_revids_given_one_rev(self):
        his = self.make_merged_ancestry()
        # rev-3 was the first mainline revision to see rev-2.
        self.assertRevidsFrom(['rev-3'], his, ['rev-2'], 'rev-3')

    def test_get_revids_deep_ancestry(self):
        his = self.make_deep_merged_ancestry()
        self.assertRevidsFrom(['F'], his, ['F'], 'F')
        self.assertRevidsFrom(['F'], his, ['E'], 'F')
        self.assertRevidsFrom(['F'], his, ['D'], 'F')
        self.assertRevidsFrom(['F'], his, ['C'], 'F')
        self.assertRevidsFrom(['B'], his, ['B'], 'F')
        self.assertRevidsFrom(['A'], his, ['A'], 'F')
