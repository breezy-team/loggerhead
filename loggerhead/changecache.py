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
import logging
import os
import threading
import time

from loggerhead import util
from loggerhead.util import decorator
from loggerhead.lockfile import LockFile


with_lock = util.with_lock('_lock', 'ChangeCache')

SQLITE_INTERFACE = os.environ.get('SQLITE_INTERFACE', 'sqlite')

if SQLITE_INTERFACE == 'pysqlite2':
    from pysqlite2 import dbapi2
    _param_marker = '?'
elif SQLITE_INTERFACE == 'sqlite':
    import sqlite as dbapi2
    _param_marker = '%s'
else:
    raise AssertionError("bad sqlite interface %r!?"%SQLITE_INTERFACE)

_select_stmt = ("select data from revisiondata where revid = ?"
                ).replace('?', _param_marker)
_insert_stmt = ("insert into revisiondata (revid, data) "
                "values (?, ?)").replace('?', _param_marker)
_update_stmt = ("update revisiondata set data = ? where revid = ?"
                ).replace('?', _param_marker)




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
    def add(self, revid_obj_pairs, commit=True):
        for  (r, d) in revid_obj_pairs:
            self.cursor.execute(_insert_stmt, (r, self._serialize(d)))
        if commit:
            self.connection.commit()
    def update(self, revid_obj_pairs, commit=True):
        for  (r, d) in revid_obj_pairs:
            self.cursor.execute(_update_stmt, (self._serialize(d), r))
        if commit:
            self.connection.commit()
    def count(self):
        self.cursor.execute(
            "select count(*) from revisiondata")
        return self.cursor.fetchone()[0]
    def close(self, commit=False):
        if commit:
            self.connection.commit()
        self.connection.close()

class ChangeCache (object):

    def __init__(self, history, cache_path):
        self.history = history
        self.log = history.log
        
        if not os.path.exists(cache_path):
            os.mkdir(cache_path)

        self._changes_filename = os.path.join(cache_path, 'changes.sql')

        # use a lockfile since the cache folder could be shared across different processes.
        self._lock = LockFile(os.path.join(cache_path, 'lock'))
        self._closed = False

##         # this is fluff; don't slow down startup time with it.
##         # but it is racy in tests :(
##         def log_sizes():
##             self.log.info('Using change cache %s; %d entries.' % (cache_path, self.size()))
##         threading.Thread(target=log_sizes).start()

    def _cache(self):
        return FakeShelf(self._changes_filename)

    @with_lock
    def close(self):
        self.log.debug('Closing cache file.')
        self._closed = True
    
    @with_lock
    def closed(self):
        return self._closed

    @with_lock
    def flush(self):
        pass
    
    @with_lock
    def get_changes(self, revid_list):
        """
        get a list of changes by their revision_ids.  any changes missing
        from the cache are fetched by calling L{History.get_change_uncached}
        and inserted into the cache before returning.
        """
        out = []
        missing_revids = []
        missing_revid_indices = []
        cache = self._cache()
        for revid in revid_list:
            entry = cache.get(revid)
            if entry is not None:
                out.append(entry)
            else:
                missing_revids.append(revid)
                missing_revid_indices.append(len(out))
                out.append(None)
        if missing_revids:
            missing_entries = self.history.get_changes_uncached(missing_revids)
            missing_entry_dict = {}
            for entry in missing_entries:
                missing_entry_dict[entry.revid] = entry
            revid_entry_pairs = []
            for i, revid in zip(missing_revid_indices, missing_revids):
                out[i] = entry = missing_entry_dict.get(revid)
                if entry is not None:
                    revid_entry_pairs.append((revid, entry))
            cache.add(revid_entry_pairs)
        return filter(None, out)

    @with_lock
    def full(self):
        cache = self._cache()
        last_revid = util.to_utf8(self.history.last_revid)
        revision_history = self.history.get_revision_history()
        return (cache.count() >= len(revision_history)
                and cache.get(last_revid) is not None)

    @with_lock
    def size(self):
        return self._cache().count()

    def check_rebuild(self, max_time=3600):
        """
        check if we need to fill in any missing pieces of the cache.  pull in
        any missing changes, but don't work any longer than C{max_time}
        seconds.
        """
        if self.closed() or self.full():
            return
        
        self.log.info('Building revision cache...')
        start_time = time.time()
        last_update = time.time()
        count = 0

        work = list(self.history.get_revision_history())
        jump = 100
        for i in xrange(0, len(work), jump):
            r = work[i:i + jump]
            # must call into history so we grab the branch lock (otherwise, lock inversion)
            self.history.get_changes(r)
            if self.closed():
                self.flush()
                return
            count += jump
            now = time.time()
            if now - start_time > max_time:
                self.log.info('Cache rebuilding will pause for now.')
                self.flush()
                return
            if now - last_update > 60:
                self.log.info('Revision cache rebuilding continues: %d/%d' % (min(count, len(work)), len(work)))
                last_update = time.time()
                self.flush()
            # give someone else a chance at the lock
            time.sleep(1)
        self.log.info('Revision cache rebuild completed.')
        self.flush()

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
