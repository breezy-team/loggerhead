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


class TestCaseWithExamples(tests.TestCaseWithMemoryTransport):


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

    def make_long_linear_ancestry(self):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('A', None, [
            ('add', ('', 'root-id', 'directory', None))])
        for r in "BCDEFGHIJKLMNOPQRSTUVWXYZ":
            builder.build_snapshot(r, None, [])
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


class TestHistory(TestCaseWithExamples):

    def test_get_file_view_iterable(self):
        # We want to make sure that get_file_view returns an iterator, rather
        # than pre-loading all history.
        pass


class _DictProxy(object):

    def __init__(self, d):
        self._d = d
        self._accessed = set()
        self.__setitem__ = d.__setitem__

    def __getitem__(self, name):
        self._accessed.add(name)
        return self._d[name]

    def __len__(self):
        return len(self._d)


def track_rev_info_accesses(h):
    """Track __getitem__ access to History._rev_info,

    :return: set of items accessed
    """
    h._rev_info = _DictProxy(h._rev_info)
    return h._rev_info._accessed


class TestHistoryGetRevidsFrom(TestCaseWithExamples):

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

    def test_get_revids_doesnt_over_produce_simple_mainline(self):
        # get_revids_from shouldn't walk the whole ancestry just to get the
        # answers for the first few revisions.
        his = self.make_long_linear_ancestry()
        accessed = track_rev_info_accesses(his)
        result = his.get_revids_from(None, 'Z')
        self.assertEqual(set(), accessed)
        self.assertEqual('Z', result.next())
        # We already know 'Z' because we passed it in.
        self.assertEqual(set(), accessed)
        self.assertEqual('Y', result.next())
        self.assertEqual(set([his._rev_indices['Z']]), accessed)

    def test_get_revids_doesnt_over_produce_for_merges(self):
        # get_revids_from shouldn't walk the whole ancestry just to get the
        # answers for the first few revisions.
        his = self.make_long_linear_ancestry()
        accessed = track_rev_info_accesses(his)
        result = his.get_revids_from(['X', 'V'], 'Z')
        self.assertEqual(set(), accessed)
        self.assertEqual('X', result.next())
        # We access 'W' because we are checking that W wasn't merged into X.
        # The important bit is that we aren't getting the whole ancestry.
        self.assertEqual(set([his._rev_indices[x] for x in 'ZYXW']), accessed)
        self.assertEqual('V', result.next())
        self.assertEqual(set([his._rev_indices[x] for x in 'ZYXWVU']), accessed)
        self.assertRaises(StopIteration, result.next)
        self.assertEqual(set([his._rev_indices[x] for x in 'ZYXWVU']), accessed)



class TestHistory_IterateSufficiently(tests.TestCase):

    def assertIterate(self, expected, iterable, stop_at, extra_rev_count):
        self.assertEqual(expected, history.History._iterate_sufficiently(
            iterable, stop_at, extra_rev_count))

    def test_iter_no_extra(self):
        lst = list('abcdefghijklmnopqrstuvwxyz')
        self.assertIterate(['a', 'b', 'c'], iter(lst), 'c', 0)
        self.assertIterate(['a', 'b', 'c', 'd'], iter(lst), 'd', 0)

    def test_iter_not_found(self):
        # If the key in question isn't found, we just exhaust the list
        lst = list('abcdefghijklmnopqrstuvwxyz')
        self.assertIterate(lst, iter(lst), 'not-there', 0)

    def test_iter_with_extra(self):
        lst = list('abcdefghijklmnopqrstuvwxyz')
        self.assertIterate(['a', 'b', 'c'], iter(lst), 'b', 1)
        self.assertIterate(['a', 'b', 'c', 'd', 'e'], iter(lst), 'c', 2)

    def test_iter_with_too_many_extra(self):
        lst = list('abcdefghijklmnopqrstuvwxyz')
        self.assertIterate(lst, iter(lst), 'y', 10)
        self.assertIterate(lst, iter(lst), 'z', 10)

    def test_iter_with_extra_None(self):
        lst = list('abcdefghijklmnopqrstuvwxyz')
        self.assertIterate(lst, iter(lst), 'z', None)
