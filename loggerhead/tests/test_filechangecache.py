"""Tests for the FileChangeCache in loggerhead.changecache."""

import shutil
import tempfile

from loggerhead.changecache import FileChangeCache

class MockEntry:
    def __init__(self, revid):
        self.revid = revid


class MockHistory:
    def __init__(self):
        self.fetched_revids = set()
    def get_file_changes_uncached(self, entries):
        output = []
        for entry in entries:
            self.fetched_revids.add(entry.revid)
            output.append(entry.revid)
        return output


class TestFileChangeCache(object):

    # setup_method and teardown_method are so i can run the tests with
    # py.test and take advantage of the error reporting.
    def setup_method(self, meth):
        self.setUp()

    def teardown_method(self, meth):
        self.tearDown()

    def setUp(self):
        self.cache_folders = []

    def tearDown(self):
        for folder in self.cache_folders:
            shutil.rmtree(folder)


    def makeHistoryAndEntriesForRevids(self, revids, fill_cache_with=[]):
        cache_folder = tempfile.mkdtemp()
        self.cache_folders.append(cache_folder)
        self.history = MockHistory()
        self.cache = FileChangeCache(self.history, cache_folder)

        self.entries = [MockEntry(revid) for revid in revids]

        self.cache.get_file_changes([entry for entry in self.entries
                                     if entry.revid in fill_cache_with])
        self.history.fetched_revids.clear()


    def test_empty_cache(self):
        """An empty cache passes all the revids through to the history object.
        """
        revids = ['a', 'b']
        self.makeHistoryAndEntriesForRevids(revids)

        result = self.cache.get_file_changes(self.entries)

        assert result == revids
        assert self.history.fetched_revids == set(revids)

    def test_full_cache(self):
        """A full cache passes none of the revids through to the history
        object.
        """
        revids = ['a', 'b']
        self.makeHistoryAndEntriesForRevids(revids, fill_cache_with=revids)

        result = self.cache.get_file_changes(self.entries)

        assert result == revids
        assert self.history.fetched_revids == set()

    def test_partial_cache(self):
        """A partially full cache passes some of the revids through to the
        history object, and preserves the ordering of the argument list.
        """
        # To test the preservation of argument order code, we put the uncached
        # revid at the beginning, middle and then end of the list of revids
        # being asked for.
        for i in range(3):
            cached_revids = ['a', 'b']
            revids = cached_revids[:]
            revids.insert(i, 'uncached')
            self.makeHistoryAndEntriesForRevids(
                revids, fill_cache_with=cached_revids)

            result = self.cache.get_file_changes(self.entries)
            assert result == revids

            assert self.history.fetched_revids == set(['uncached'])
