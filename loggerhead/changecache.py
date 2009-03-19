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
a cache for chewed-up "change" data structures, which are basically just a
different way of storing a revision.  the cache improves lookup times 10x
over bazaar's xml revision structure, though, so currently still worth doing.

once a revision is committed in bazaar, it never changes, so once we have
cached a change, it's good forever.
"""

import cPickle
import os
import tempfile

from loggerhead import util

with_lock = util.with_lock('_lock', 'ChangeCache')

try:
    from sqlite3 import dbapi2
except ImportError:
    from pysqlite2 import dbapi2


class FakeShelf(object):

    def __init__(self, filename):
        create_table = not os.path.exists(filename)
        if create_table:
            fd, path = tempfile.mkstemp(dir=os.path.dirname(filename))
            self._create_table(path)
            os.rename(path, filename)
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
        r = dbapi2.Binary(cPickle.dumps(obj, protocol=2))
        return r

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
            # oh well!
            pass


class FileChangeCache(object):

    def __init__(self, history, cache_path):
        self.history = history

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
