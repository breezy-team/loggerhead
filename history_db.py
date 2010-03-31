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

try:
    from sqlite3 import dbapi2
except ImportError:
    from pysqlite2 import dbapi2

from bzrlib import trace

from bzrlib.plugin.history_db import schema


def import_from_branch(a_branch, db=None):
    """Import the history data from a_branch into the database."""
    db_conn = dbapi2.connect(db)
    if not schema.is_initialized(db_conn):
        trace.note('Initialized database: %s' % (db,))
        schema.create_sqlite_db(db_conn)
