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

"""The current SQL schema definition."""

_create_statements = []

revision_t = """
CREATE TABLE revision (
    db_id INTEGER PRIMARY KEY AUTOINCREMENT,
    revision_id TEXT NOT NULL
);
"""
_create_statements.append(revision_t)

revision_index = """
CREATE INDEX revision_revision_id_index ON revision (revision_id);
"""
_create_statements.append(revision_index)

parent_t = """
CREATE TABLE parent (
    child INTEGER REFERENCES revision NOT NULL,
    parent INTEGER REFERENCES revision NOT NULL,
    parent_idx INTEGER NOT NULL -- 0 == left-hand parent
);
"""
_create_statements.append(parent_t)

parent_child_index = """
CREATE INDEX parent_child_index ON parent (child);
"""
_create_statements.append(parent_child_index)

dotted_revno_t = """
CREATE TABLE dotted_revno (
    tip_revision INTEGER REFERENCES revision NOT NULL,
    merged_revision INTEGER REFERENCES revision NOT NULL,
    revno TEXT NOT NULL,
    end_of_merge BOOL NOT NULL,
    merge_depth INTEGER NOT NULL,
    CONSTRAINT dotted_revno_key UNIQUE (tip_revision, merged_revision)
);
"""
_create_statements.append(dotted_revno_t)

dotted_revno_index = """
CREATE INDEX dotted_revno_index ON dotted_revno(tip_revision);
"""
_create_statements.append(dotted_revno_index)

mainline_parent_range_t = """
CREATE TABLE mainline_parent_range (
    pkey INTEGER PRIMARY KEY AUTOINCREMENT,
    head INTEGER REFERENCES revision NOT NULL,
    tail INTEGER REFERENCES revision NOT NULL
);
"""
_create_statements.append(mainline_parent_range_t)

mainline_parent_range_head_index = """
CREATE INDEX mainline_parent_range_head_index
    ON mainline_parent_range (head);
"""
_create_statements.append(mainline_parent_range_head_index)

mainline_parent_t = """
CREATE TABLE mainline_parent (
    pkey INTEGER PRIMARY KEY AUTOINCREMENT,
    range INTEGER REFERENCES mainline_parent_range NOT NULL,
    revision INTEGER REFERENCES revision NOT NULL
);
"""
_create_statements.append(mainline_parent_t)

mainline_parents_range_index = """
CREATE INDEX mainline_parents_range_index
    ON mainline_parents (range);
"""
_create_statements.append(mainline_parents_range_index)


def create_sqlite_db(conn):
    """Given a connection to an sqlite database, create the fields."""
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    for statement in _create_statements:
        cursor.execute(statement)
    cursor.execute("COMMIT")


def create_pgsql_db(conn):
    """Populate a Postgres database.

    Slightly different syntax from sqlite.
    """
    cursor = conn.cursor()
    cursor.execute("BEGIN")
    for statement in _create_statements:
        statement = statement.replace('INTEGER PRIMARY KEY AUTOINCREMENT',
                                      'SERIAL PRIMARY KEY')
        cursor.execute(statement)
    cursor.execute("COMMIT")


def is_initialized(conn, err_type):
    # Both pgsql and sqlite have ways to tell if a table exists, but they
    # aren't the *same*, so just punt and ask for content of a table.
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT count(*) FROM revision').fetchall()
    except err_type: # ???
        return False
    return True
