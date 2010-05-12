#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

"""
a cache for chewed-up 'file change' data structures, which are basically just
a different way of storing a revision delta.  the cache improves lookup times
10x over bazaar's xml revision structure, though, so currently still worth
doing.

once a revision is committed in bazaar, it never changes, so once we have
cached a change, it's good forever.
"""

import cPickle
import marshal
import os
import tempfile
import zlib

try:
    from sqlite3 import dbapi2
except ImportError:
    from pysqlite2 import dbapi2

# We take an optimistic approach to concurrency here: we might do work twice
# in the case of races, but not crash or corrupt data.

def safe_init_db(filename, init_sql):
    # To avoid races around creating the database, we create the db in
    # a temporary file and rename it into the ultimate location.
    fd, temp_path = tempfile.mkstemp(dir=os.path.dirname(filename))
    os.close(fd)
    con = dbapi2.connect(temp_path)
    cur = con.cursor()
    cur.execute(init_sql)
    con.commit()
    con.close()
    os.rename(temp_path, filename)

class FakeShelf(object):

    def __init__(self, filename):
        create_table = not os.path.exists(filename)
        if create_table:
            safe_init_db(
                filename, "create table RevisionData "
                "(revid binary primary key, data binary)")
        self.connection = dbapi2.connect(filename)
        self.cursor = self.connection.cursor()

    def _create_table(self, filename):
        con = dbapi2.connect(filename)
        cur = con.cursor()
        cur.execute(
            "create table RevisionData "
            "(revid binary primary key, data binary)")
        con.commit()
        con.close()

    def _serialize(self, obj):
        return dbapi2.Binary(cPickle.dumps(obj, protocol=2))

    def _unserialize(self, data):
        return cPickle.loads(str(data))

    def get(self, revid):
        self.cursor.execute(
            "select data from revisiondata where revid = ?", (revid, ))
        filechange = self.cursor.fetchone()
        if filechange is None:
            return None
        else:
            return self._unserialize(filechange[0])

    def add(self, revid, object):
        try:
            self.cursor.execute(
                "insert into revisiondata (revid, data) values (?, ?)",
                (revid, self._serialize(object)))
            self.connection.commit()
        except dbapi2.IntegrityError:
            # If another thread or process attempted to set the same key, we
            # assume it set it to the same value and carry on with our day.
            pass


class FileChangeCache(object):

    def __init__(self, cache_path):

        if not os.path.exists(cache_path):
            os.mkdir(cache_path)

        self._changes_filename = os.path.join(cache_path, 'filechanges.sql')

    def get_file_changes(self, entry):
        cache = FakeShelf(self._changes_filename)
        changes = cache.get(entry.revid)
        if changes is None:
            changes = self.history.get_file_changes_uncached(entry)
            cache.add(entry.revid, changes)
        return changes
