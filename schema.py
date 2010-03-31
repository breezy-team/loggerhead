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

# TODO: Consider using an ORM for all of this. For now, though, I like knowing
#       what SQL exactly is being executed
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
    parent_idx INTEGER NOT NULL, -- 0 == left-hand parent
    CONSTRAINT parent_is_unique UNIQUE (child, parent, parent_idx)
);
"""
_create_statements.append(parent_t)

parent_child_index = """
CREATE INDEX parent_child_index ON parent (child);
"""
_create_statements.append(parent_child_index)
# So we can find a parent for a given node

parent_parent_index = """
CREATE INDEX parent_parent_index ON parent (parent);
"""
_create_statements.append(parent_parent_index)
# So we can find the *children* of a given node

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

mainline_parent_range_index = """
CREATE INDEX mainline_parent_range_index
    ON mainline_parent (range);
"""
_create_statements.append(mainline_parent_range_index)


def create_sqlite_db(conn):
    """Given a connection to an sqlite database, create the fields."""
    cursor = conn.cursor()
    for statement in _create_statements:
        cursor.execute(statement)
    conn.commit()


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


def ensure_revision(cursor, revision_id):
    """Ensure a revision exists, and return its database id."""
    x = cursor.execute('SELECT db_id FROM revision WHERE revision_id = ?',
                       (revision_id,))
    val = x.fetchone()
    if val is None:
        cursor.execute('INSERT INTO revision (revision_id) VALUES (?)',
                       (revision_id,))
        return ensure_revision(cursor, revision_id)
    return val[0]


_BATCH_SIZE = 100
def ensure_revisions(cursor, revision_ids, rev_id_to_db_id):
    """Do a bulk check to make sure we have db ids for all revisions.
    
    Update the revision_id => db_id mapping
    """
    # TODO: I wish I knew a more efficient way to do this
    #   a) You could select all revisions that are in the db. But potentially
    #      you have lots of unrelated projects, and this would give unwanted
    #      overlap.
    #   b) SQLITE defaults to limiting you to 999 parameters
    #   c) IIRC the postgres code uses a tradeoff of 10%. If it thinks it needs
    #      more than 10% of the data in the table, it is faster to do an I/O
    #      friendly sequential scan, than to do a random order scan.
    remaining = [r for r in revision_ids if r not in rev_id_to_db_id]
    cur = 0
    missing = set()
    # res = cursor.execute('SELECT revision_id, db_id FROM revision')
    # for rev_id, db_id in res.fetchall():
    #     if rev_id in missing:
    #         result[rev_id] = db_id
    #         missing.discard(rev_id)
    while cur < len(remaining):
        next = remaining[cur:cur+_BATCH_SIZE]
        cur += _BATCH_SIZE
        res = cursor.execute('SELECT revision_id, db_id FROM revision'
                             ' WHERE revision_id in (%s)'
                             % (', '.join('?'*len(next))),
                             tuple(next))
        local_missing = set(next)
        for rev_id, db_id in res.fetchall():
            rev_id_to_db_id[rev_id] = db_id
            local_missing.discard(rev_id)
        missing.update(local_missing)
    if missing:
        cursor.executemany('INSERT INTO revision (revision_id) VALUES (?)',
                           [(m,) for m in missing])
        ensure_revisions(cursor, missing, rev_id_to_db_id)


def create_dotted_revno(cursor, tip_revision, merged_revision, revno,
                        end_of_merge, merge_depth):
    """Create a dotted revno entry for this info."""
    # TODO: Consider changing this to a bulk SELECT a bunch which may be
    #       missing, .executemany() the ones that aren't present
    existing = cursor.execute('SELECT revno, end_of_merge, merge_depth'
                              '  FROM dotted_revno'
                              ' WHERE tip_revision = ?'
                              '   AND merged_revision = ?',
                              (tip_revision, merged_revision)).fetchone()
    if existing is not None:
        new_value = (revno, end_of_merge, merge_depth)
        if existing != new_value:
            raise ValueError('Disagreement in the graph. Wanted to add'
                ' node %s, but %s already exists'
                % (new_value, existing))
        return
    cursor.execute(
        'INSERT INTO dotted_revno (tip_revision, merged_revision,'
        '                          revno, end_of_merge, merge_depth)'
        ' VALUES (?, ?, ?, ?, ?)',
        (tip_revision, merged_revision, revno, end_of_merge, merge_depth))
