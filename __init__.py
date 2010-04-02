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

from bzrlib import (
    commands,
    option,
    registry,
    trace,
    )
import time


class cmd_create_history_db(commands.Command):
    """Create and populate the history database for this branch.
    """

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                    ]

    def run(self, directory='.', db=None):
        import pprint
        from bzrlib.plugins.history_db import history_db
        from bzrlib import branch
        b = branch.Branch.open(directory)
        b.lock_read()
        try:
            importer = history_db.Importer(db, b)
            importer.do_import()
            importer.build_mainline_cache()
        finally:
            b.unlock()
        trace.note('Stats:\n%s' % (pprint.pformat(dict(importer._stats)),))


class cmd_get_dotted_revno(commands.Command):
    """Query the db for a dotted revno.
    """

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     'revision',
                     option.Option('use-db-ids',
                        help='Do the queries using database ids'),
                    ]

    def run(self, directory='.', db=None, revision=None, use_db_ids=False):
        import pprint
        from bzrlib.plugins.history_db import history_db
        from bzrlib import branch
        b = branch.Branch.open(directory)
        if revision is None:
            raise errors.BzrCommandError('You must supply --revision')
        b.lock_read()
        try:
            rev_ids = [rspec.as_revision_id(b) for rspec in revision]
            query = history_db.Querier(db, b)
            if use_db_ids:
                revnos = [(query.get_dotted_revno_db_ids(rev_id), rev_id)
                          for rev_id in rev_ids]
            else:
                revnos = [(query.get_dotted_revno(rev_id), rev_id)
                          for rev_id in rev_ids]
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
        trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))


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
        from bzrlib.plugins.history_db import history_db
        from bzrlib import branch
        import pprint
        import time
        b = branch.Branch.open(directory)
        b.lock_read()
        self.add_cleanup(b.unlock)
        t = time.time()
        if method.startswith('db'):
            query = history_db.Querier(db, b)
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
        from bzrlib.plugins.history_db import history_db
        from bzrlib import branch
        import pprint
        b = branch.Branch.open(directory)
        b.lock_read()
        self.add_cleanup(b.unlock)
        t = time.time()
        if method.startswith('db'):
            query = history_db.Querier(db, b)
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
            ancestors = len(kg._nodes)
        self.outf.write('Found %d ancestors\n' % (len(ancestors),))
        trace.note('Time: %.3fs' % (time.time() - t,))

commands.register_command(cmd_create_history_db)
commands.register_command(cmd_get_dotted_revno)
commands.register_command(cmd_walk_mainline)
commands.register_command(cmd_walk_ancestry)
