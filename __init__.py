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

"""Store history information in a database."""

import time

from bzrlib import (
    branch,
    commands,
    debug,
    lazy_import,
    option,
    registry,
    trace,
    )

lazy_import.lazy_import(globals(), """
from bzrlib.plugins.history_db import history_db as _mod_history_db
""")


def _ensure_db_for_command(db, b):
    if db is not None:
        return db
    db = _get_history_db_path(b)
    if db is None:
        raise BzrCommandError('No --db supplied and no default'
            ' db configured as "history_db_path"')
    return db


class cmd_history_db_create(commands.Command):
    """Create and populate the history database for this branch.
    """

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     option.Option('incremental', short_name='i',
                        help='Consider this an incremental update.'),
                     option.Option('validate',
                        help='Do extra checks to ensure correctness.'),
                    ]
    hidden = True

    def run(self, directory='.', db=None, incremental=False,
            validate=False):
        import pprint
        from bzrlib import branch
        b = branch.Branch.open(directory)
        b.lock_read()
        try:
            db = _ensure_db_for_command(db, b)
            importer = _mod_history_db.Importer(db, b, incremental=incremental,
                                                validate=validate)
            importer.do_import()
        finally:
            b.unlock()
        trace.note('Stats:\n%s' % (pprint.pformat(dict(importer._stats)),))


_orig_do_dotted_revno = getattr(branch.Branch,
    '_do_dotted_revno_to_revision_id', None)
_orig_do_rev_id_to_dotted = getattr(branch.Branch,
    '_do_revision_id_to_dotted_revno', None)
_orig_iter_merge_sorted = getattr(branch.Branch,
    'iter_merge_sorted_revisions', None)
_orig_clear_cached_state = getattr(branch.Branch,
    '_clear_cached_state', None)


def _get_history_db_path(a_branch):
    """Return the path to the history DB cache or None."""
    # TODO: Consider allowing a relative path to the branch root
    #       Or to the repository, or ?
    #       For now, the user could just configure an absolute path on the
    #       Repository in locations.conf and have that inherited to the
    #       branches.
    # TODO: Consider not making this a Branch configuration. For remote
    #       branches, it adds at least 1 round-trip to read the remote
    #       branch.conf. Which is a shame.
    path = a_branch.get_config().get_user_option('history_db_path')
    return path


_singleton = object()
def _get_querier(a_branch):
    """Get a Querier instance if history_db is enabled."""
    query = getattr(a_branch, '_history_db_querier', _singleton)
    if query is not _singleton:
        # query may be None, all we know is that we've already set something
        return query
    history_db_path = _get_history_db_path(a_branch)
    if history_db_path is None:
        if 'history_db' in debug.debug_flags:
            trace.note('"history_db_path" not set for %s' % (a_branch,))
        query = None
    else:
        try:
            query = _mod_history_db.Querier(history_db_path, a_branch)
        except _mod_history_db.dbapi2.OperationalError,e:
            trace.note('history_db failed: %s' % (e,))
            query = None
    a_branch._history_db_querier = query
    return query


def _history_db_clear_cached_state(a_branch):
    query = getattr(a_branch, '_history_db_querier', _singleton)
    if query is not _singleton:
        if query is not None:
            query.close()
        del a_branch._history_db_querier
    return _orig_clear_cached_state(a_branch)


def _history_db_iter_merge_sorted_revisions(self, start_revision_id=None,
    stop_revision_id=None, stop_rule='exclude', direction='reverse'):
    """See Branch.iter_merge_sorted_revisions()

    This is a monkeypatch that overrides the default behavior, extracting data
    from the history db if it is enabled.
    """
    t0 = time.clock()
    query = _get_querier(self)
    fallback = False
    if stop_rule not in ('exclude', 'with-merges'):
        trace.mutter('history_db falling back to original'
                     'iter_merge_sorted_revisions, we don\'t support: %s'
                     % (stop_rule,))
        fallback = True
    if query is None:
        fallback = True
    if fallback:
        # TODO: Consider other cases where we may want to fall back, like
        #       special arguments, etc that we don't handle well yet.
        trace.mutter('history_db falling back to original'
                     'iter_merge_sorted_revisions')
        return _orig_iter_merge_sorted(self,
            start_revision_id=start_revision_id,
            stop_revision_id=stop_revision_id, stop_rule=stop_rule,
            direction=direction)
    if stop_rule == 'exclude':
        real_stop_revision_id = stop_revision_id
    else:
        assert stop_rule == 'with-merges'
        # 'with-merges' is just exclude vs the previous parent, so walk-by-one.
        if stop_revision_id is None:
            real_stop_revision_id = stop_revision_id
        else:
            pm = self.repository.get_parent_map([stop_revision_id])
            parents = pm.get(stop_revision_id, None)
            if parents is None or not parents:
                trace.note('stop revision is a ghost, excluding.')
                real_stop_revision_id = stop_revision_id
            else:
                real_stop_revision_id = parents[0]
    merge_sorted = query.iter_merge_sorted_revisions(
                    start_revision_id=start_revision_id,
                    stop_revision_id=real_stop_revision_id)
    t1 = time.clock()
    func = getattr(self, '_filter_start_non_ancestors', None)
    if func is None:
        func = getattr(self, '_filter_non_ancestors', None)
    if func is not None:
        merge_sorted = func(iter(merge_sorted))
    t2 = time.clock()
    if 'history_db' in debug.debug_flags:
        import pprint
        trace.note('history_db iter_merge took %.3fs (%.3fs query)'
                   % (t2-t0, t1-t0))
        trace.mutter('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
    if direction == 'reverse':
        return merge_sorted
    elif direction == 'forward':
        return reversed(list(filtered))
    else:
        raise ValueError('invalid direction %r' % direction)


def _history_db_revision_id_to_dotted_revno(self, revision_id):
    """See Branch._do_revision_id_to_dotted_revno"""
    revno = self._partial_revision_id_to_revno_cache.get(revision_id, None)
    if revno is not None:
        if 'history_db' in debug.debug_flags:
            trace.note('history_db rev=>dotted cached %s' % (revno,))
        return revno
    t0 = time.clock()
    query = _get_querier(self)
    if query is None:
        if 'history_db' in debug.debug_flags:
            trace.mutter('history_db falling back to original'
                         'revision_id => dotted_revno')
        return _orig_do_rev_id_to_dotted(self, revision_id)
    t1 = time.clock()
    revision_id_map = query.get_dotted_revnos([revision_id])
    t2 = time.clock()
    if 'history_db' in debug.debug_flags:
        trace.note('history_db rev=>dotted %s took %.3fs, %.3fs to init,'
                   ' %.3fs to query' % (revision_id_map.values(),
                                        t2-t0, t1-t0, t2-t1))
    self._partial_revision_id_to_revno_cache.update(revision_id_map)

    if revision_id not in revision_id_map:
        trace.mutter('history_db failed to find a mapping for {%s},'
                     'falling back' % (revision_id,))
        return _orig_do_rev_id_to_dotted(self, revision_id)
    return revision_id_map[revision_id]


def _history_db_dotted_revno_to_revision_id(self, revno):
    """See Branch._do_dotted_revno_to_revision_id."""
    # revno should be a dotted revno, aka either 1-part or 3-part tuple
    t0 = time.clock()
    query = _get_querier(self)
    if query is None:
        if 'history_db' in debug.debug_flags:
            trace.mutter('history_db falling back to original'
                     'dotted_revno => revision_id, "history_db_path" not set')
        return _orig_do_dotted_revno(self, revno)
    t1 = time.clock()
    revno_map = query.get_revision_ids([revno])
    t2 = time.clock()
    if 'history_db' in debug.debug_flags:
        trace.note('history_db dotted=>rev took %.3fs, %.3fs to init,'
                   ' %.3fs to query' % (t2-t0, t1-t0, t2-t1))
    self._partial_revision_id_to_revno_cache.update(
        [(r_id, r_no) for r_no, r_id in revno_map.iteritems()])
               
    if revno not in revno_map:
        trace.mutter('history_db failed to find a mapping for %s,'
                     'falling back' % (revno,))
        return _orig_do_dotted_revno(self, revno)
    return revno_map[revno]


def _history_db_post_change_branch_tip_hook(params):
    """Run when the tip of a branch changes revision_id."""
    t0 = time.clock()
    import pprint
    # TODO: This requires a round-trip to the remote server to find out whether
    #       or not something is configured (even if we have it set it
    #       locations.conf), we should be able to do better...
    history_db_path = _get_history_db_path(params.branch)
    t1 = time.clock()
    if history_db_path is None:
        if 'history_db' in debug.debug_flags:
            trace.mutter('Note updating history-db, "history_db_path"'
                         ' not configured')
        return
    importer = _mod_history_db.Importer(history_db_path, params.branch,
                                        tip_revision_id=params.new_revid,
                                        incremental=True)
    t2 = time.clock()
    importer.do_import()
    t3 = time.clock()
    if 'history_db' in debug.debug_flags:
        info = trace.note
    else:
        info = trace.mutter
    info('history_db post-change-hook took %.3fs'
         ' (%.3fs to get_config, %.3fs to init, %.3fs to import)'
         % (t3-t0, t1-t0, t2-t1, t3-t2))
    trace.mutter('Stats:\n%s'
                 % (pprint.pformat(dict(importer._stats)),))


def _register_history_db_hooks():
    if _orig_do_dotted_revno is None:
        trace.mutter('Unable to enable history-db, needs bzr 1.12 or later')
        return
    branch.Branch._do_dotted_revno_to_revision_id = \
        _history_db_dotted_revno_to_revision_id
    branch.Branch._do_revision_id_to_dotted_revno = \
        _history_db_revision_id_to_dotted_revno
    branch.Branch.iter_merge_sorted_revisions = \
        _history_db_iter_merge_sorted_revisions
    branch.Branch._clear_cached_state = \
        _history_db_clear_cached_state
    branch.Branch.hooks.install_named_hook('post_change_branch_tip',
        _history_db_post_change_branch_tip_hook, 'history_db')


_register_history_db_hooks()

def load_tests(standard_tests, module, loader):
    standard_tests.addTests(loader.loadTestsFromModuleNames([
        (__name__ + '.' + x) for x in [
            'test_hooks',
            'test_importer',
        ]]))
    return standard_tests
