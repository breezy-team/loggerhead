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

from bzrlib import (
    trace,
    ui,
    )

from bzrlib.plugins.history_db import schema


def _insert_nodes(cursor, tip_rev_id, nodes, rev_id_to_db_id):
    """Insert all of the nodes mentioned into the database."""
    # rev_ids we don't know the db id for
    schema.ensure_revisions(cursor, [n.key[0] for n in nodes], rev_id_to_db_id)
    res = cursor.execute("SELECT count(*) FROM dotted_revno JOIN revision"
                         "    ON dotted_revno.tip_revision = revision.db_id"
                         " WHERE revision_id = ?"
                         "   AND tip_revision = merged_revision",
                         (tip_rev_id,)).fetchone()
    if res[0] > 0:
        # Not importing anything because the data is already present
        return False

    tip_db_id = rev_id_to_db_id[tip_rev_id]
    for node in nodes:
        schema.create_dotted_revno(cursor,
            tip_revision=tip_db_id,
            merged_revision=rev_id_to_db_id[node.key[0]],
            revno='.'.join(map(str, node.revno)),
            end_of_merge=node.end_of_merge,
            merge_depth=node.merge_depth)
    return True


def _update_parents(cursor, nodes, graph, rev_id_to_db_id):
    """Update parent information for all these nodes."""
    # Get the keys and their parents
    parent_map = dict((n.key[0], [p[0] for p in graph.get_parent_keys(n.key)])
                      for n in nodes)
    rev_ids = set(parent_map)
    map(rev_ids.update, parent_map.itervalues())
    schema.ensure_revisions(cursor, rev_ids, rev_id_to_db_id)
    data = []
    r_to_d = rev_id_to_db_id
    for rev_id, parent_ids in parent_map.iteritems():
        for idx, parent_id in enumerate(parent_ids):
            data.append((r_to_d[rev_id], r_to_d[parent_id], idx))
    cursor.executemany("INSERT OR IGNORE INTO parent"
                       "  (child, parent, parent_idx)"
                       "VALUES (?, ?, ?)", data)


def import_from_branch(a_branch, db=None):
    """Import the history data from a_branch into the database."""
    db_conn = dbapi2.connect(db)
    if not schema.is_initialized(db_conn, dbapi2.OperationalError):
        trace.note('Initialized database: %s' % (db,))
        schema.create_sqlite_db(db_conn)
    tip_key = (a_branch.last_revision(),)
    kg = a_branch.repository.revisions.get_known_graph_ancestry([tip_key])
    merge_sorted = kg.merge_sort(tip_key)
    new_nodes = []
    cursor = db_conn.cursor()
    try:
        pb = ui.ui_factory.nested_progress_bar()
        last_tip_rev_id = None
        new_nodes = []
        rev_id_to_db_id = {}
        imported_count = 0
        for idx, node in enumerate(merge_sorted):
            pb.update('importing', idx, len(merge_sorted))
            if last_tip_rev_id is None:
                assert not new_nodes
                assert node.merge_depth == 0, "We did not start at a mainline?"
                last_tip_rev_id = node.key[0]
                new_nodes.append(node)
                continue
            if node.merge_depth == 0:
                # We've seen all the nodes that were introduced by this
                # revision into mainline, check to see if we've already
                # inserted this data into the db. If we have, then we can
                # assume that all parents are *also* inserted into the database
                # and stop
                # This is only safe if we either import in 'forward' order, or
                # we wait to commit until all the data is imported. However, if
                # we import in 'reverse' order, it is obvious when we can
                # stop...

                _update_parents(cursor, new_nodes, kg, rev_id_to_db_id)
                if not _insert_nodes(cursor, last_tip_rev_id, new_nodes,
                                     rev_id_to_db_id):
                    # This data has already been imported.
                    new_nodes = []
                    break
                imported_count += len(new_nodes)
                last_tip_rev_id = node.key[0]
                new_nodes = []
            new_nodes.append(node)
        if new_nodes:
            assert last_tip_rev_id is not None
            _insert_nodes(cursor, last_tip_rev_id, new_nodes, rev_id_to_db_id)
            imported_count += len(new_nodes)
            new_nodes = []
        print "Imported %d revisions" % (imported_count,)
    except:
        db_conn.rollback()
        raise
    else:
        db_conn.commit()
