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
        from bzrlib.plugins.history_db import history_db
        from bzrlib import branch
        b = branch.Branch.open(directory)
        b.lock_read()
        try:
            imported_count = history_db.Importer.import_from_branch(b, db=db)
        finally:
            b.unlock()
        trace.note('Imported %d revisions' % (imported_count,))


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
        import pprint
        trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))


class cmd_walk_mainline(commands.Command):
    """Walk the mainline of the branch."""

    takes_options = [option.Option('db', type=unicode,
                        help='Use this as the database for storage'),
                     option.Option('directory', type=unicode, short_name='d',
                        help='Import this location instead of "."'),
                     option.Option('use-db-ids',
                        help='Do the queries using database ids'),
                     option.Option('in-bzr', help="Use the bzr graph."),
                    ]

    def run(self, directory='.', db=None, in_bzr=False, use_db_ids=False):
        from bzrlib.plugins.history_db import history_db
        from bzrlib import branch
        b = branch.Branch.open(directory)
        b.lock_read()
        try:
            if in_bzr:
                import time
                t = time.time()
                b.revision_history()
                trace.note('Time: %.3fs' % (time.time() - t,))
            else:
                query = history_db.Querier(db, b)
                if use_db_ids:
                    query.walk_mainline_db_ids()
                else:
                    query.walk_mainline()
                import pprint
                trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
        finally:
            b.unlock()
        # Time to walk bzr mainline
        #  bzr 31packs  683ms
        #  bzr 1pack    320ms
        #  db rev_ids   295ms
        #  db db_ids    236ms


_ancestry_walk_types = registry.Registry()
_ancestry_walk_types.register('db-rev-id', None)
_ancestry_walk_types.register('db-db-id', None)
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
                query.walk_ancestry_db_ids()
            elif method == 'db-rev-id':
                query.walk_ancestry()
            trace.note('Stats:\n%s' % (pprint.pformat(dict(query._stats)),))
        elif method == 'bzr-iter-anc':
            g = b.repository.get_graph()
            anc = list(g.iter_ancestry([b.last_revision()]))
        elif method == 'bzr-kg':
            kg = b.repository.revisions.get_known_graph_ancestry(
                [(b.last_revision(),)])
        trace.note('Time: %.3fs' % (time.time() - t,))

commands.register_command(cmd_create_history_db)
commands.register_command(cmd_get_dotted_revno)
commands.register_command(cmd_walk_mainline)
commands.register_command(cmd_walk_ancestry)
