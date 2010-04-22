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

import os

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

    def get_history_db_path(self):
        p = osutils.getcwd() + '/history.db'
        def remove():
            if os.path.isfile(p):
                os.remove(p)
        self.addCleanup(remove)
        return p

    def test__get_history_db_path(self):
        b = self.make_branch('test')
        self.assertIs(None, history_db._get_history_db_path(b))
        history_db_path = self.get_history_db_path()
        b.get_config().set_user_option('history_db_path', history_db_path)
        self.assertEqual(history_db_path, history_db._get_history_db_path(b))

    def test_iter_merge_sorted(self):
        b, merge_sorted = self.make_simple_history_branch()
        # With nothing configured, it should just fall back to the original
        # Branch.iter_merge_sorted_revisions()
        self.assertEqual(merge_sorted,
                list(history_db._history_db_iter_merge_sorted_revisions(b)))

    def test_iter_merge_sorted_no_init(self):
        history_db_path = self.get_history_db_path()
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        # Without filling out the cache, it should still give correct results
        self.assertEqual(merge_sorted,
                list(history_db._history_db_iter_merge_sorted_revisions(b)))
        self.assertIsNot(None, b._history_db_querier)
        self.assertIsNot(None, b._history_db_querier._branch_tip_db_id)
        self.assertEqual({'B': (2,)},
                    b._history_db_querier.get_dotted_revno_range_multi(['B']))

    def test_iter_merge_sorted_no_parents(self):
        history_db_path = self.get_history_db_path()
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        # Without filling out the cache, it should still give correct results
        val = history_db._history_db_iter_merge_sorted_revisions(b,
                        start_revision_id='B', stop_revision_id='A',
                        stop_rule='with-merges')
        self.assertEqual(merge_sorted, list(val))
        val = history_db._history_db_iter_merge_sorted_revisions(b,
                        start_revision_id='B', stop_revision_id=None,
                        stop_rule='with-merges')
        self.assertEqual(merge_sorted, list(val))
        val = history_db._history_db_iter_merge_sorted_revisions(b,
                        start_revision_id='B', stop_revision_id=None,
                        stop_rule='exclude')
        self.assertEqual(merge_sorted, list(val))

    def test_iter_merge_sorted_ghost(self):
        history_db_path = self.get_history_db_path()
        builder = self.make_branch_builder('test')
        builder.start_series()
        builder.build_snapshot('A', None, [
            ('add', ('', 'directory', 'TREE_ROOT', None))])
        builder.build_snapshot('B', ['A', 'ghost'], [])
        builder.finish_series()
        b = builder.get_branch()
        b.lock_write()
        self.addCleanup(b.unlock)
        b.get_config().set_user_option('history_db_path', history_db_path)
        # Without filling out the cache, it should still give correct results
        val = history_db._history_db_iter_merge_sorted_revisions(b,
                        start_revision_id='B', stop_revision_id='ghost',
                        stop_rule='with-merges')
        self.assertEqual([('B', 0, (2,), False), ('A', 0, (1,), True)],
                         list(val))


    def test_iter_merge_sorted_cached(self):
        history_db_path = self.get_history_db_path()
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        importer = history_db._mod_history_db.Importer(history_db_path, b)
        importer.do_import()
        importer._db_conn.close()
        # Without filling out the cache, it should still give correct results
        self.assertEqual(merge_sorted,
                list(history_db._history_db_iter_merge_sorted_revisions(b)))
        self.assertIsNot(None, b._history_db_querier)

    def test_rev_to_dotted_not_imported(self):
        history_db_path = self.get_history_db_path()
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        self.assertEqual((2,),
                history_db._history_db_revision_id_to_dotted_revno(b, 'B'))

    def test_dotted_to_rev_not_imported(self):
        history_db_path = self.get_history_db_path()
        b, merge_sorted = self.make_simple_history_branch()
        b.get_config().set_user_option('history_db_path', history_db_path)
        self.assertEqual('B',
                history_db._history_db_dotted_revno_to_revision_id(b, (2,)))
