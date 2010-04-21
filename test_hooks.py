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

"""Test the hook interfaces"""

from bzrlib import (
    errors,
    osutils,
    tests,
    )
from bzrlib.plugins import history_db


class TestHistoryDBHooks(tests.TestCaseWithMemoryTransport):

    def make_simple_history_branch(self):
        builder = self.make_branch_builder('test')
        builder.start_series()
        builder.build_snapshot('A', None, [
            ('add', ('', 'directory', 'TREE_ROOT', None))])
        builder.build_snapshot('B', ['A'], [])
        builder.finish_series()
        b = builder.get_branch()
        b.lock_write()
        self.addCleanup(b.unlock)
        merge_sorted = [('B', 0, (2,), False), ('A', 0, (1,), True)]
        return b, merge_sorted

    def test__get_history_db_path(self):
        b = self.make_branch('test')
        self.assertIs(None, history_db._get_history_db_path(b))
        cwd = osutils.getcwd()
        history_db_path = cwd + '/history.db'
        b.get_config().set_user_option('history_db_path', history_db_path)
        self.assertEqual(history_db_path, history_db._get_history_db_path(b))

    def test_iter_merge_sorted(self):
        b, merge_sorted = self.make_simple_history_branch()
        # With nothing configured, it should just fall back to the original
        # Branch.iter_merge_sorted_revisions()
        self.assertEqual(merge_sorted,
                list(history_db._history_db_iter_merge_sorted_revisions(b)))

    def test_iter_merge_sorted_not_cached(self):
        history_db_path = osutils.getcwd() + '/history.db'
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        # Without filling out the cache, it should still give correct results
        self.assertEqual(merge_sorted,
                list(history_db._history_db_iter_merge_sorted_revisions(b)))
        # TODO: It should populate the cache before running, so check that the
        #       cache is filled
        self.assertIsNot(None, b._history_db_querier)

    def test_iter_merge_sorted_cached(self):
        history_db_path = osutils.getcwd() + '/history.db'
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        importer = history_db._mod_history_db.Importer(history_db_path, b)
        importer.do_import()
        importer._db_conn.close()
        # Without filling out the cache, it should still give correct results
        self.assertEqual(merge_sorted,
                list(history_db._history_db_iter_merge_sorted_revisions(b)))
        self.assertIsNot(None, b._history_db_querier)
