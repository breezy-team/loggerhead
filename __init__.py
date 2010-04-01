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
    )


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
        from bzrlib import branch, trace
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
        from bzrlib import branch, trace
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

commands.register_command(cmd_create_history_db)
commands.register_command(cmd_get_dotted_revno)
