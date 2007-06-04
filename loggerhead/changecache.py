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
from loggerhead.lockfile import LockFile


with_lock = util.with_lock('_lock', 'ChangeCache')
        

class ChangeCache (object):
    
    def __init__(self, history, cache_path):
        self.history = history
        self.log = history.log
        
        if not os.path.exists(cache_path):
            os.mkdir(cache_path)

        # keep a separate cache for the diffs, because they're very time-consuming to fetch.
        self._changes_filename = os.path.join(cache_path, 'changes')
        self._changes_diffs_filename = os.path.join(cache_path, 'changes-diffs')
        
        # use a lockfile since the cache folder could be shared across different processes.
        self._lock = LockFile(os.path.join(cache_path, 'lock'))
        self._closed = False
        
        # this is fluff; don't slow down startup time with it.
        def log_sizes():
            s1, s2 = self.sizes()
            self.log.info('Using change cache %s; %d/%d entries.' % (cache_path, s1, s2))
        threading.Thread(target=log_sizes).start()
    
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
    def get_changes(self, revid_list, get_diffs=False):
        """
        get a list of changes by their revision_ids.  any changes missing
        from the cache are fetched by calling L{History.get_change_uncached}
        and inserted into the cache before returning.
        """
        if get_diffs:
            cache = shelve.open(self._changes_diffs_filename, 'c', protocol=2)
        else:
            cache = shelve.open(self._changes_filename, 'c', protocol=2)

        try:
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
        finally:
            cache.close()
    
    @with_lock
    def full(self, get_diffs=False):
        if get_diffs:
            cache = shelve.open(self._changes_diffs_filename, 'c', protocol=2)
        else:
            cache = shelve.open(self._changes_filename, 'c', protocol=2)
        try:
            return (len(cache) >= len(self.history.get_revision_history())) and (util.to_utf8(self.history.last_revid) in cache)
        finally:
            cache.close()

    @with_lock
    def sizes(self):
        cache = shelve.open(self._changes_filename, 'c', protocol=2)
        s1 = len(cache)
        cache.close()
        cache = shelve.open(self._changes_diffs_filename, 'c', protocol=2)
        s2 = len(cache)
        cache.close()
        return s1, s2
        
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


