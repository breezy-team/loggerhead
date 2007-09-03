from loggerhead.changecache import FileChangeCache

import random
import shutil
import tempfile


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

    # there are so i can run it with py.test and take advantage of the
    # error reporting...
    def setup_method(self, meth):
        self.setUp()

    def teardown_method(self, meth):
        self.tearDown()

    def setUp(self):
        self.cache_folder = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.cache_folder)

    def test_empty_cache(self):
        """An empty cache passes all the revids through to the history object.
        """

        history = MockHistory()
        cache = FileChangeCache(history, self.cache_folder)

        revids = ['a', 'b']
        entries = [MockEntry(revid) for revid in revids]

        result = cache.get_file_changes(entries)

        assert result == revids

        assert history.fetched_revids == set(revids)

    def test_full_cache(self):
        """A full cache passes none of the revids through to the history
        object.
        """

        history = MockHistory()
        cache = FileChangeCache(history, self.cache_folder)

        revids = ['a', 'b']
        entries = [MockEntry(revid) for revid in revids]

        # One call to fill the cache
        cache.get_file_changes(entries)
        history.fetched_revids.clear()

        result = cache.get_file_changes(entries)
        assert result == revids

        assert history.fetched_revids == set()

    def test_partial_cache(self):
        """A partially full cache passes some of the revids through to the
        history object, and preserves the ordering of the argument list.
        """

        history = MockHistory()
        cache = FileChangeCache(history, self.cache_folder)

        revids = [chr(ord('a') + i) for i in range(20)]
        entries = [MockEntry(revid) for revid in revids]

        some_entries = random.sample(entries, len(entries)/2)
        cache.get_file_changes(some_entries)
        history.fetched_revids.clear()

        result = cache.get_file_changes(entries)
        assert result == revids

        assert history.fetched_revids \
               == set(revids) - set([e.revid for e in some_entries])
