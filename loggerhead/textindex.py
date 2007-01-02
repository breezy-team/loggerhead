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
indexing of the comment text of revisions, for fast searching.

two separate 'shelve' files are created:

    - recorded: revid -> 1 (if the revid is indexed)
    - index: 3-letter substring -> list(revids)
"""

import logging
import os
import re
import shelve
import threading
import time

from loggerhead import util
from loggerhead.util import decorator
from loggerhead.lockfile import LockFile

# if any substring index reaches this many revids, replace the entry with
# an ALL marker -- it's not worth an explicit index.
ALL_THRESHOLD = 1000
ALL = 'ALL'


with_lock = util.with_lock('_lock')


def normalize_string(s):
    """
    remove any punctuation and normalize all whitespace to a single space.
    """
    s = util.to_utf8(s).lower()
    # remove apostrophes completely.
    s = re.sub(r"'", '', s)
    # convert other garbage into space
    s = re.sub(r'[^\w\d]', ' ', s)
    # compress multiple spaces into one.
    s = re.sub(r'\s{2,}', ' ', s)
    # and finally remove leading/trailing whitespace
    s = s.strip()
    return s


class TextIndex (object):
    def __init__(self, history, cache_path):
        self.history = history
        self.log = history.log
        
        if not os.path.exists(cache_path):
            os.mkdir(cache_path)
        
        self._recorded_filename = os.path.join(cache_path, 'textindex-recorded')
        self._index_filename = os.path.join(cache_path, 'textindex')
        
        # use a lockfile since the cache folder could be shared across different processes.
        self._lock = LockFile(os.path.join(cache_path, 'index-lock'))
        self._closed = False
        
        self.log.info('Using search index; %d entries.', len(self))
    
    def _is_indexed(self, revid, recorded):
        return recorded.get(util.to_utf8(revid), None) is not None
        
    @with_lock
    def is_indexed(self, revid):
        recorded = shelve.open(self._recorded_filename, 'c', protocol=2)
        try:
            return self._is_indexed(revid, recorded)
        finally:
            recorded.close()
    
    @with_lock
    def __len__(self):
        recorded = shelve.open(self._recorded_filename, 'c', protocol=2)
        try:
            return len(recorded)
        finally:
            recorded.close()

    @with_lock
    def close(self):
        self._closed = True
    
    @with_lock
    def closed(self):
        return self._closed
    
    @with_lock
    def flush(self):
        pass
    
    @with_lock
    def full(self):
        recorded = shelve.open(self._recorded_filename, 'c', protocol=2)
        try:
            return (len(recorded) >= len(self.history.get_revision_history())) and (util.to_utf8(self.history.last_revid) in recorded)
        finally:
            recorded.close()

    def _index_change(self, change, recorded, index):
        """
        currently, only indexes the 'comment' field.
        """
        comment = normalize_string(change.comment)
        if len(comment) < 3:
            return
        for i in xrange(len(comment) - 2):
            sub = comment[i:i + 3]
            revid_set = index.get(sub, None)
            if revid_set is None:
                revid_set = set()
            elif revid_set == ALL:
                # this entry got too big
                continue
            revid_set.add(change.revid)
            if len(revid_set) > ALL_THRESHOLD:
                revid_set = ALL
            index[sub] = revid_set
        
        recorded[util.to_utf8(change.revid)] = True

    @with_lock
    def index_changes(self, revid_list):
        recorded = shelve.open(self._recorded_filename, 'c', protocol=2)
        index = shelve.open(self._index_filename, 'c', protocol=2)
        try:
            revid_list = [r for r in revid_list if not self._is_indexed(r, recorded)]
            change_list = self.history.get_changes(revid_list)
            for change in change_list:
                self._index_change(change, recorded, index)
        finally:
            index.close()
            recorded.close()
    
    @with_lock
    def find(self, text, revid_list=None):
        index = shelve.open(self._index_filename, 'c', protocol=2)
        try:
            text = normalize_string(text)
            if len(text) < 3:
                return []
    
            total_set = None
            if revid_list is not None:
                total_set = set(revid_list)
            seen_all = False
            
            for i in xrange(len(text) - 2):
                sub = text[i:i + 3]
                revid_set = index.get(sub, None)
                if revid_set is None:
                    # zero matches, stop here.
                    return []
                if revid_set == ALL:
                    # skip
                    seen_all = True
                    continue
                if total_set is None:
                    total_set = revid_set
                else:
                    total_set.intersection_update(revid_set)
                if len(total_set) == 0:
                    return []
        finally:
            index.close()
        
        # tricky: if seen_all is True, one of the substring indices was ALL
        # (in other words, unindexed), so our results are actually a superset
        # of the exact answer.
        #
        # if we cared, we could do a direct match on the result set and cull
        # out any that aren't actually matches.  for now, i'm gonna say that
        # we DON'T care, and if one of the substrings hit ALL, there's a small
        # chance that we'll give a few false positives.
        return total_set
    
    def check_rebuild(self, max_time=3600):
        """
        check if there are any un-indexed revisions, and if so, index them.
        but don't spend longer than C{max_time} on it.
        """
        if self.closed() or self.full():
            # all done
            return

        self.log.info('Building search index...')
        work = list(self.history.get_revision_history())
        start_time = time.time()
        last_update = time.time()
        count = 0

        jump = 100
        for i in xrange(0, len(work), jump):
            r = work[i:i + jump]
            self.index_changes(r)
            if self.closed():
                return

            count += jump
            now = time.time()
            if now - start_time > 3600:
                # there's no point working for hours.  eventually we might even
                # hit the next re-index interval, which would suck mightily.
                self.log.info('Search indexing has worked for an hour; giving up for now.')
                return
            if now - last_update > 60:
                self.log.info('Search indexing continues: %d/%d' % (min(count, len(work)), len(work)))
                last_update = time.time()
            # give someone else a chance at the lock
            time.sleep(1)
        self.log.info('Search index completed.')
        self.flush()

