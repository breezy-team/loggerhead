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

from loggerhead import util
from loggerhead.lockfile import LockFile

with_lock = util.with_lock('_lock', 'ChangeCache')

SQLITE_INTERFACE = os.environ.get('SQLITE_INTERFACE', 'sqlite')

if SQLITE_INTERFACE == 'pysqlite2':
    from pysqlite2 import dbapi2
    _param_marker = '?'
elif SQLITE_INTERFACE == 'sqlite':
    import sqlite as dbapi2
    _param_marker = '%s'


_select_stmt = ("select data from revisiondata where revid = ?"
                ).replace('?', _param_marker)
_insert_stmt = ("insert into revisiondata (revid, data) "
                "values (?, ?)").replace('?', _param_marker)




class FakeShelf(object):
    def __init__(self, filename):
        create_table = not os.path.exists(filename)
        self.connection = dbapi2.connect(filename)
        self.cursor = self.connection.cursor()
        if create_table:
            self._create_table()
    def _create_table(self):
        self.cursor.execute(
            "create table RevisionData "
            "(revid binary primary key, data binary)")
        self.connection.commit()
    def _serialize(self, obj):
        r = dbapi2.Binary(cPickle.dumps(obj, protocol=2))
        return r
    def _unserialize(self, data):
        return cPickle.loads(str(data))
    def get(self, revid):
        self.cursor.execute(_select_stmt, (revid,))
        filechange = self.cursor.fetchone()
        if filechange is None:
            return None
        else:
            return self._unserialize(filechange[0])
    def add(self, revid_obj_pairs):
        for  (r, d) in revid_obj_pairs:
            self.cursor.execute(_insert_stmt, (r, self._serialize(d)))
        self.connection.commit()


class FileChangeCache(object):
    def __init__(self, history, cache_path):
        self.history = history

        if not os.path.exists(cache_path):
            os.mkdir(cache_path)

        self._changes_filename = os.path.join(cache_path, 'filechanges.sql')

        # use a lockfile since the cache folder could be shared across
        # different processes.
        self._lock = LockFile(os.path.join(cache_path, 'filechange-lock'))

    @with_lock
    def get_file_changes(self, entries):
        out = []
        missing_entries = []
        missing_entry_indices = []
        cache = FakeShelf(self._changes_filename)
        for entry in entries:
            changes = cache.get(entry.revid)
            if changes is not None:
                out.append(changes)
            else:
                missing_entries.append(entry)
                missing_entry_indices.append(len(out))
                out.append(None)
        if missing_entries:
            missing_changes = self.history.get_file_changes_uncached(missing_entries)
            revid_changes_pairs = []
            for i, entry, changes in zip(
                missing_entry_indices, missing_entries, missing_changes):
                revid_changes_pairs.append((entry.revid, changes))
                out[i] = changes
            cache.add(revid_changes_pairs)
        return out
