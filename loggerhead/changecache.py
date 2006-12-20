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

import logging
import os
import shelve
import threading
import time

from loggerhead import util
from loggerhead.util import decorator


# cache lock binds tighter than branch lock
@decorator
def with_lock(unbound):
    def cache_locked(self, *args, **kw):
        self._lock.acquire()
        try:
            return unbound(self, *args, **kw)
        finally:
            self._lock.release()
    return cache_locked


class ChangeCache (object):
    
    def __init__(self, history, cache_path):
        self.history = history
        self.log = history.log
        
        if not os.path.exists(cache_path):
            os.mkdir(cache_path)

        # keep a separate cache for the diffs, because they're very time-consuming to fetch.
        changes_filename = os.path.join(cache_path, 'changes')
        changes_diffs_filename = os.path.join(cache_path, 'changes-diffs')
        
        self._cache = shelve.open(changes_filename, 'c', protocol=2)
        self._cache_diffs = shelve.open(changes_diffs_filename, 'c', protocol=2)
        
        self._lock = threading.RLock()
        self._closed = False
        
        # once we process a change (revision), it should be the same forever.
        self.log.info('Using change cache %s; %d/%d entries.' % (cache_path, len(self._cache), len(self._cache_diffs)))
    
    @with_lock
    def close(self):
        self._cache.close()
        self._cache_diffs.close()
        self._closed = True
    
    @with_lock
    def closed(self):
        return self._closed

    @with_lock
    def flush(self):
        self._cache.sync()
        self._cache_diffs.sync()
    
    @with_lock
    def get_changes(self, revid_list, get_diffs=False):
        """
        get a list of changes by their revision_ids.  any changes missing
        from the cache are fetched by calling L{History.get_change_uncached}
        and inserted into the cache before returning.
        """
        if get_diffs:
            cache = self._cache_diffs
        else:
            cache = self._cache

        out = []
        fetch_list = []
        sfetch_list = []
        for revid in revid_list:
            # if the revid is in unicode, use the utf-8 encoding as the key
            srevid = util.to_utf8(revid)
            
            if srevid in cache:
                out.append(cache[srevid])
            else:
                #self.log.debug('Entry cache miss: %r' % (revid,))
                out.append(None)
                fetch_list.append(revid)
                sfetch_list.append(srevid)
        
        if len(fetch_list) > 0:
            # some revisions weren't in the cache; fetch them
            changes = self.history.get_changes_uncached(fetch_list, get_diffs)
            if changes is None:
                return changes
            for i in xrange(len(revid_list)):
                if out[i] is None:
                    cache[sfetch_list.pop(0)] = out[i] = changes.pop(0)
        
        return out
    
    @with_lock
    def full(self, get_diffs=False):
        if get_diffs:
            cache = self._cache_diffs
        else:
            cache = self._cache
        return (len(cache) == len(self.history.get_revision_history())) and (util.to_utf8(self.history.last_revid) in cache)

    def check_rebuild(self, max_time=3600):
        """
        check if we need to fill in any missing pieces of the cache.  pull in
        any missing changes, but don't work any longer than C{max_time}
        seconds.
        """
        if self.full():
            return
        
        self.log.info('Building revision cache...')
        start_time = time.time()
        last_update = time.time()
        count = 0

        work = list(self.history.get_revision_history())
        jump = 100
        for i in xrange(0, len(work), jump):
            r = work[i:i + jump]
            self.get_changes(r)
            if self.closed():
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
        self.log.info('Revision cache rebuild completed.')
    


