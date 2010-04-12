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
    lazy_import,
    option,
    registry,
    trace,
    )

lazy_import.lazy_import(globals(), """
from bzrlib.plugins.history_db import history_db as _mod_history_db
""")


class cmd_create_history_db(commands.Command):
    """Create and populate the history database for this branch.
    """

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     option.Option('expand-all', help='Expand all revnos'),
                     option.Option('incremental', short_name='i',
                        help='Consider this an incremental update.'),
                     option.Option('validate',
                        help='Do extra checks to ensure correctness.'),
                    ]

    def run(self, directory='.', db=None, expand_all=False, incremental=False,
            validate=False):
        import pprint
        from bzrlib import branch
        b = branch.Branch.open(directory)
        b.lock_read()
        try:
            importer = _mod_history_db.Importer(db, b, incremental=incremental,
                                                validate=validate)
            importer.do_import(expand_all=expand_all)
            importer.build_mainline_cache()
        finally:
            b.unlock()
        trace.note('Stats:\n%s' % (pprint.pformat(dict(importer._stats)),))


_dotted_revno_walk_types = registry.Registry()
_dotted_revno_walk_types.register('db-rev-id', None)
_dotted_revno_walk_types.register('db-db-id', None)
_dotted_revno_walk_types.register('db-range', None)
_dotted_revno_walk_types.register('db-range-multi', None)
_dotted_revno_walk_types.register('bzr', None)

class cmd_get_dotted_revno(commands.Command):
    """Query the db for a dotted revno.
    """

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     'revision',
                     option.RegistryOption('method',
                        help='How do you want to do the walking.',
                        converter=str, registry=_dotted_revno_walk_types)
                    ]

    def run(self, directory='.', db=None, revision=None,
            method=None):
        import pprint
        from bzrlib import branch
        b = branch.Branch.open(directory)
        if revision is None:
            raise errors.BzrCommandError('You must supply --revision')
        b.lock_read()
        try:
            rev_ids = [rspec.as_revision_id(b) for rspec in revision]
            t = time.time()
            if method == 'bzr':
                # Make sure to use a different branch, because the existing one
                # has already cached the mainline, etc in decoding the supplied
                # revision ids.
                b2 = b.bzrdir.open_branch()
                b2.lock_read()
                try:
                    revnos = [(b2.revision_id_to_dotted_revno(r), r)
                              for r in rev_ids]
                finally:
                    b2.unlock()
            else:
                query = _mod_history_db.Querier(db, b)
                if method == 'db-db-id':
                    revnos = [(query.get_dotted_revno_db_ids(rev_id), rev_id)
                              for rev_id in rev_ids]
                elif method == 'db-rev-id':
                    revnos = [(query.get_dotted_revno(rev_id), rev_id)
                              for rev_id in rev_ids]
                elif method == 'db-range':
                    revnos = [(query.get_dotted_revno_range(rev_id), rev_id)
                              for rev_id in rev_ids]
                else:
                    assert method == 'db-range-multi'
                    revno_map = query.get_dotted_revno_range_multi(rev_ids)
                    revnos = [(revno_map[rev_id], rev_id) for rev_id in rev_ids]
                trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
            tdelta = time.time() - t
            revno_strs = []
            max_len = 0
            for revno, rev_id in revnos:
                if revno is None:
                    s = '?'
                else:
                    s = '.'.join(map(str, revno))
                if len(s) > max_len:
                    max_len = len(s)
                revno_strs.append((s, rev_id))
            self.outf.write(''.join(['%*s %s\n' % (max_len, s, r)
                                     for s, r in revno_strs]))
        finally:
            b.unlock()
        trace.note('Time: %.3fs' % (tdelta,))


_dotted_to_rev_walk_types = registry.Registry()
_dotted_to_rev_walk_types.register('db-range', None)
_dotted_to_rev_walk_types.register('bzr', None)

class cmd_dotted_to_rev(commands.Command):
    """Query the db for a dotted revno => revision_id
    """

    takes_args = ['revno+']
    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     'revision',
                     option.RegistryOption('method',
                        help='How do you want to do the walking.',
                        converter=str, registry=_dotted_to_rev_walk_types)
                    ]

    def run(self, directory='.', db=None, revno_list=None,
            method=None):
        import pprint
        from bzrlib import branch
        b = branch.Branch.open(directory)
        b.lock_read()
        try:
            # Map back into integer dotted revnos
            revno_list = [tuple(map(int, r.split('.'))) for r in revno_list]
            t = time.time()
            if method == 'bzr':
                b2 = b.bzrdir.open_branch()
                b2.lock_read()
                try:
                    _orig_do_dotted_revno
                    revision_ids = [(r, _orig_do_dotted_revno(b2, r))
                                    for r in revno_list]
                finally:
                    b2.unlock()
            else:
                query = _mod_history_db.Querier(db, b)
                if method == 'db-range':
                    revno_map = query.get_revision_ids(revno_list)
                    revision_ids = [(r, revno_map.get(r, None))
                                    for r in revno_list]
                else:
                    assert method == 'db-range-multi'
                    revno_map = query.get_dotted_revno_range_multi(rev_ids)
                    revnos = [(revno_map[rev_id], rev_id) for rev_id in rev_ids]
                trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
            tdelta = time.time() - t
            revno_strs = []
            max_len = 0
            for revno, rev_id in revision_ids:
                if revno is None:
                    s = '?'
                else:
                    s = '.'.join(map(str, revno))
                if len(s) > max_len:
                    max_len = len(s)
                revno_strs.append((s, rev_id))
            self.outf.write(''.join(['%*s %s\n' % (max_len, s, r)
                                     for s, r in revno_strs]))
        finally:
            b.unlock()
        trace.note('Time: %.3fs' % (tdelta,))


_mainline_walk_types = registry.Registry()
_mainline_walk_types.register('db-rev-id', None)
_mainline_walk_types.register('db-db-id', None)
_mainline_walk_types.register('db-range', None)
_mainline_walk_types.register('bzr', None)

class cmd_walk_mainline(commands.Command):
    """Walk the mainline of the branch."""

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     option.RegistryOption('method',
                        help='How do you want to do the walking.',
                        converter=str, registry=_mainline_walk_types)
                    ]

    def run(self, directory='.', db=None, method=None):
        from bzrlib import branch
        import pprint
        import time
        b = branch.Branch.open(directory)
        b.lock_read()
        self.add_cleanup(b.unlock)
        t = time.time()
        if method.startswith('db'):
            query = _mod_history_db.Querier(db, b)
            if method == 'db-db-id':
                mainline = query.walk_mainline_db_ids()
            elif method == 'db-rev-id':
                mainline = query.walk_mainline()
            else:
                assert method == 'db-range'
                mainline = query.walk_mainline_using_ranges()
            tdelta = time.time() - t
            trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
        else:
            assert method == 'bzr'
            mainline = b.revision_history()
            tdelta = time.time() - t
        self.outf.write('Found %d revs\n' % (len(mainline),))
        trace.note('Time: %.3fs' % (tdelta,))
        # Time to walk bzr mainline
        # Outer includes the branch.open time, Query is just the time we spend
        # walking the database, etc.
        #               Outer Query
        #  bzr 13packs  646ms
        #  bzr 1pack    406ms
        #  db rev_ids   381ms 296ms
        #  db db_ids    331ms 243ms
        #  db range     118ms  18ms


_ancestry_walk_types = registry.Registry()
_ancestry_walk_types.register('db-rev-id', None)
_ancestry_walk_types.register('db-db-id', None)
_ancestry_walk_types.register('db-range', None)
_ancestry_walk_types.register('db-dotted', None)
_ancestry_walk_types.register('bzr-iter-anc', None)
_ancestry_walk_types.register('bzr-kg', None)

class cmd_walk_ancestry(commands.Command):
    """Walk the whole ancestry of a branch tip."""

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     option.RegistryOption('method',
                        help='How do you want to do the walking.',
                        converter=str, registry=_ancestry_walk_types)
                    ]

    def run(self, directory='.', db=None, method=None):
        from bzrlib import branch
        import pprint
        b = branch.Branch.open(directory)
        b.lock_read()
        self.add_cleanup(b.unlock)
        t = time.time()
        if method.startswith('db'):
            query = _mod_history_db.Querier(db, b)
            if method == 'db-db-id':
                ancestors = query.walk_ancestry_db_ids()
            elif method == 'db-rev-id':
                ancestors = query.walk_ancestry()
            elif method == 'db-dotted':
                ancestors = query.walk_ancestry_range_and_dotted()
            else:
                assert method == 'db-range'
                ancestors = query.walk_ancestry_range()
            trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
        elif method == 'bzr-iter-anc':
            g = b.repository.get_graph()
            ancestors = list(g.iter_ancestry([b.last_revision()]))
        elif method == 'bzr-kg':
            kg = b.repository.revisions.get_known_graph_ancestry(
                [(b.last_revision(),)])
            ancestors = kg._nodes
        self.outf.write('Found %d ancestors\n' % (len(ancestors),))
        trace.note('Time: %.3fs' % (time.time() - t,))

commands.register_command(cmd_create_history_db)
commands.register_command(cmd_get_dotted_revno)
commands.register_command(cmd_dotted_to_rev)
commands.register_command(cmd_walk_mainline)
commands.register_command(cmd_walk_ancestry)


_orig_do_dotted_revno = getattr(branch.Branch,
    '_do_dotted_revno_to_revision_id', None)
_orig_do_rev_id_to_dotted = getattr(branch.Branch,
    '_do_revision_id_to_dotted_revno', None)
_orig_iter_merge_sorted = getattr(branch.Branch,
    'iter_merge_sorted_revisions', None)


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


def _history_db_iter_merge_sorted_revisions(self, start_revision_id=None,
    stop_revision_id=None, stop_rule='exclude', direction='reverse'):
    """See Branch.iter_merge_sorted_revisions()

    This is a monkeypatch that overrides the default behavior, extracting data
    from the history db if it is enabled.
    """
    history_db_path = _get_history_db_path(self)
    if history_db_path is None:
        # TODO: Consider other cases where we may want to fall back, like
        #       special arguments, etc that we don't handle well yet.
        trace.mutter('history_db falling back to original'
                     'iter_merge_sorted_revisions, "history_db_path" not set')
        return _orig_iter_merge_sorted(self,
            start_revision_id=start_revision_id,
            stop_revision_id=stop_revision_id, stop_rule=stop_rule,
            direction=direction)
    import pdb; pdb.set_trace()
    # TODO: Consider what to do if the branch has not been imported yet. My gut
    #       feeling is that we really want to do the import at this time. Since
    #       the user would want the data, and it is possible to update a cache
    #       with new values and return them *faster* than you could get them
    #       out from scratch.
    return _orig_iter_merge_sorted(self,
        start_revision_id=start_revision_id, stop_revision_id=stop_revision_id,
        stop_rule=stop_rule, direction=direction)


def _history_db_revision_id_to_dotted_revno(self, revision_id):
    """See Branch._do_revision_id_to_dotted_revno"""
    # TODO: Fill it self._partial_revision_id_to_revno_cache and use it
    t0 = time.clock()
    history_db_path = _get_history_db_path(self)
    if history_db_path is None:
        trace.mutter('history_db falling back to original'
                     'revision_id => dotted_revno, "history_db_path" not set')
        return _orig_do_rev_id_to_dotted(self, revno)
    try:
        query = _mod_history_db.Querier(history_db_path, self)
    except _mod_history_db.dbapi2.OperationalError,e:
        trace.note('history_db failed: %s' % (e,))
        return _orig_do_rev_id_to_dotted(self, revno)
    t1 = time.clock()
    revision_id_map = query.get_dotted_revno_range_multi([revision_id])
    t2 = time.clock()
    trace.note('history_db rev=>dotted took %.3fs, %.3fs to init,'
               ' %.3fs to query' % (t2-t0, t1-t0, t2-t1))
               
    if revision_id not in revision_id_map:
        trace.mutter('history_db failed to find a mapping for {%s},'
                     'falling back' % (revision_id,))
        return _orig_do_rev_id_to_dotted(self, revno)
    return revision_id_map[revision_id]


def _history_db_dotted_revno_to_revision_id(self, revno):
    """See Branch._do_dotted_revno_to_revision_id."""
    # TODO: Fill it self._partial_revision_id_to_revno_cache and use it
    # revno should be a dotted revno, aka either 1-part or 3-part tuple
    t0 = time.clock()
    history_db_path = _get_history_db_path(self)
    if history_db_path is None:
        trace.mutter('history_db falling back to original'
                     'dotted_revno => revision_id, "history_db_path" not set')
        return _orig_do_dotted_revno(self, revno)
    try:
        query = _mod_history_db.Querier(history_db_path, self)
    except _mod_history_db.dbapi2.OperationalError,e:
        trace.note('history_db failed: %s' % (e,))
        return _orig_do_dotted_revno(self, revno)
    t1 = time.clock()
    revno_map = query.get_revision_ids([revno])
    t2 = time.clock()
    trace.note('history_db dotted=>rev took %.3fs, %.3fs to init,'
               ' %.3fs to query' % (t2-t0, t1-t0, t2-t1))
               
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
        trace.mutter('Note updating history-db, "history_db_path"'
                     ' not configured')
        return
    importer = _mod_history_db.Importer(history_db_path, params.branch,
                                        tip_revision_id=params.new_revid,
                                        incremental=True)
    t2 = time.clock()
    importer.do_import()
    t3 = time.clock()
    importer.build_mainline_cache()
    t4 = time.clock()
    trace.note('history_db post-change-hook took %.3fs'
               ' (%.3fs to get_config, %.3fs to init, %.3fs to import)'
               % (t4-t0, t1-t0, t2-t1, t3-t2))
    trace.mutter('Stats:\n%s' % (pprint.pformat(dict(importer._stats)),))



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
    branch.Branch.hooks.install_named_hook('post_change_branch_tip',
        _history_db_post_change_branch_tip_hook, 'history_db')


_register_history_db_hooks()

def load_tests(standard_tests, module, loader):
    standard_tests.addTests(loader.loadTestsFromModuleNames([
        (__name__ + '.' + x) for x in [
            'test_importer',
        ]]))
    return standard_tests
