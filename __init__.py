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

commands.register_command(cmd_create_history_db)
