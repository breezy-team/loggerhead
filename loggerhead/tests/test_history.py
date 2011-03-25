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

from datetime import datetime
from bzrlib import tag, tests

from loggerhead import history as _mod_history


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
        return _mod_history.History(b, {})

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
        return _mod_history.History(b, {})

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
        return _mod_history.History(b, {})

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
        return _mod_history.History(b, {})

    def assertRevidsFrom(self, expected, history, search_revs, tip_rev):
        self.assertEqual(expected,
                         list(history.get_revids_from(search_revs, tip_rev)))


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

    def test_get_revids_from_simple_mainline(self):
        history = self.make_linear_ancestry()
        self.assertRevidsFrom(['rev-3', 'rev-2', 'rev-1'],
                              history, None, 'rev-3')

    def test_get_revids_from_merged_mainline(self):
        history = self.make_merged_ancestry()
        self.assertRevidsFrom(['rev-3', 'rev-1'],
                              history, None, 'rev-3')

    def test_get_revids_given_one_rev(self):
        history = self.make_merged_ancestry()
        # rev-3 was the first mainline revision to see rev-2.
        self.assertRevidsFrom(['rev-3'], history, ['rev-2'], 'rev-3')

    def test_get_revids_deep_ancestry(self):
        history = self.make_deep_merged_ancestry()
        self.assertRevidsFrom(['F'], history, ['F'], 'F')
        self.assertRevidsFrom(['F'], history, ['E'], 'F')
        self.assertRevidsFrom(['F'], history, ['D'], 'F')
        self.assertRevidsFrom(['F'], history, ['C'], 'F')
        self.assertRevidsFrom(['B'], history, ['B'], 'F')
        self.assertRevidsFrom(['A'], history, ['A'], 'F')

    def test_get_revids_doesnt_over_produce_simple_mainline(self):
        # get_revids_from shouldn't walk the whole ancestry just to get the
        # answers for the first few revisions.
        history = self.make_long_linear_ancestry()
        accessed = track_rev_info_accesses(history)
        result = history.get_revids_from(None, 'Z')
        self.assertEqual(set(), accessed)
        self.assertEqual('Z', result.next())
        # We already know 'Z' because we passed it in.
        self.assertEqual(set(), accessed)
        self.assertEqual('Y', result.next())
        self.assertEqual(set([history._rev_indices['Z']]), accessed)

    def test_get_revids_doesnt_over_produce_for_merges(self):
        # get_revids_from shouldn't walk the whole ancestry just to get the
        # answers for the first few revisions.
        history = self.make_long_linear_ancestry()
        accessed = track_rev_info_accesses(history)
        result = history.get_revids_from(['X', 'V'], 'Z')
        self.assertEqual(set(), accessed)
        self.assertEqual('X', result.next())
        # We access 'W' because we are checking that W wasn't merged into X.
        # The important bit is that we aren't getting the whole ancestry.
        self.assertEqual(set([history._rev_indices[x] for x in 'ZYXW']),
                         accessed)
        self.assertEqual('V', result.next())
        self.assertEqual(set([history._rev_indices[x] for x in 'ZYXWVU']),
                         accessed)
        self.assertRaises(StopIteration, result.next)
        self.assertEqual(set([history._rev_indices[x] for x in 'ZYXWVU']),
                         accessed)



class TestHistoryChangeFromRevision(tests.TestCaseWithTransport):

    def make_single_commit(self):
        tree = self.make_branch_and_tree('test')
        rev_id = tree.commit('Commit Message', timestamp=1299838474.317,
            timezone=3600, committer='Joe Example <joe@example.com>',
            revprops={})
        self.addCleanup(tree.branch.lock_write().unlock)
        rev = tree.branch.repository.get_revision(rev_id)
        history = _mod_history.History(tree.branch, {})
        return history, rev

    def test_simple(self):
        history, rev = self.make_single_commit()
        change = history._change_from_revision(rev)
        self.assertEqual(rev.revision_id, change.revid)
        self.assertEqual(datetime.fromtimestamp(1299838474.317),
                         change.date)
        self.assertEqual(datetime.utcfromtimestamp(1299838474.317),
                         change.utc_date)
        self.assertEqual(['Joe Example <joe@example.com>'],
                         change.authors)
        self.assertEqual('test', change.branch_nick)
        self.assertEqual('Commit Message', change.short_comment)
        self.assertEqual('Commit Message', change.comment)
        self.assertEqual(['Commit&nbsp;Message'], change.comment_clean)
        self.assertEqual([], change.parents)
        self.assertEqual([], change.bugs)
        self.assertEqual(None, change.tags)

    def test_tags(self):
        history, rev = self.make_single_commit()
        b = history._branch
        b.tags.set_tag('tag-1', rev.revision_id)
        b.tags.set_tag('tag-2', rev.revision_id)
        b.tags.set_tag('Tag-10', rev.revision_id)
        change = history._change_from_revision(rev)
        # If available, tags are 'naturally' sorted. (sorting numbers in order,
        # and ignoring case, etc.)
        if getattr(tag, 'sort_natural', None) is not None:
            self.assertEqual('tag-1, tag-2, Tag-10', change.tags)
        else:
            self.assertEqual('Tag-10, tag-1, tag-2', change.tags)

    def test_committer_vs_authors(self):
        tree = self.make_branch_and_tree('test')
        rev_id = tree.commit('Commit Message', timestamp=1299838474.317,
            timezone=3600, committer='Joe Example <joe@example.com>',
            revprops={'authors': u'A Author <aauthor@example.com>\n'
                                 u'B Author <bauthor@example.com>'})
        self.addCleanup(tree.branch.lock_write().unlock)
        rev = tree.branch.repository.get_revision(rev_id)
        history = _mod_history.History(tree.branch, {})
        change = history._change_from_revision(rev)
        self.assertEqual(u'Joe Example <joe@example.com>',
                         change.committer)
        self.assertEqual([u'A Author <aauthor@example.com>',
                          u'B Author <bauthor@example.com>'],
                         change.authors)


class TestHistory_IterateSufficiently(tests.TestCase):

    def assertIterate(self, expected, iterable, stop_at, extra_rev_count):
        self.assertEqual(expected, _mod_history.History._iterate_sufficiently(
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



class TestHistoryGetView(TestCaseWithExamples):

    def test_get_view_limited_history(self):
        # get_view should only load enough history to serve the result, not all
        # history.
        history = self.make_long_linear_ancestry()
        accessed = track_rev_info_accesses(history)
        revid, start_revid, revid_list = history.get_view('Z', 'Z', None,
                                                      extra_rev_count=5)
        self.assertEqual(['Z', 'Y', 'X', 'W', 'V', 'U'], revid_list)
        self.assertEqual('Z', revid)
        self.assertEqual('Z', start_revid)
        self.assertEqual(set([history._rev_indices[x] for x in 'ZYXWVU']),
                         accessed)
