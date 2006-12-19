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

from loggerhead import util
from loggerhead.util import decorator

log = logging.getLogger("loggerhead.controllers")

# if any substring index reaches this many revids, replace the entry with
# an ALL marker -- it's not worth an explicit index.
ALL_THRESHOLD = 1000
ALL = 'ALL'


@decorator
def with_lock(unbound):
    def locked(self, *args, **kw):
        self._lock.acquire()
        try:
            return unbound(self, *args, **kw)
        finally:
            self._lock.release()
    return locked


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
        
        if not os.path.exists(cache_path):
            os.mkdir(cache_path)
        
        recorded_filename = os.path.join(cache_path, 'textindex-recorded')
        index_filename = os.path.join(cache_path, 'textindex')
        
        self._recorded = shelve.open(recorded_filename, 'c', protocol=2)
        self._index = shelve.open(index_filename, 'c', protocol=2)
        
        self._lock = threading.RLock()
        
        log.info('Using search index; %d entries.', len(self._recorded))
    
    @with_lock
    def is_indexed(self, revid):
        return self._recorded.get(util.to_utf8(revid), None) is not None
    
    @with_lock
    def __len__(self):
        return len(self._recorded)

    @with_lock
    def flush(self):
        self._recorded.sync()
        self._index.sync()
    
    @with_lock
    def index_change(self, change):
        """
        currently, only indexes the 'comment' field.
        """
        comment = normalize_string(change.comment)
        if len(comment) < 3:
            return
        for i in xrange(len(comment) - 2):
            sub = comment[i:i + 3]
            revid_set = self._index.get(sub, None)
            if revid_set is None:
                revid_set = set()
            elif revid_set == ALL:
                # this entry got too big
                continue
            revid_set.add(change.revid)
            if len(revid_set) > ALL_THRESHOLD:
                revid_set = ALL
            self._index[sub] = revid_set
        
        self._recorded[util.to_utf8(change.revid)] = True
        return
    
    @with_lock
    def find(self, text, revid_list=None):
        text = normalize_string(text)
        if len(text) < 3:
            return []

        total_set = None
        if revid_list is not None:
            total_set = set(revid_list)
        seen_all = False
        
        for i in xrange(len(text) - 2):
            sub = text[i:i + 3]
            revid_set = self._index.get(sub, None)
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
        
        # tricky: if seen_all is True, one of the substring indices was ALL
        # (in other words, unindexed), so our results are actually a superset
        # of the exact answer.
        #
        # if we cared, we could do a direct match on the result set and cull
        # out any that aren't actually matches.  for now, i'm gonna say that
        # we DON'T care, and if one of the substrings hit ALL, there's a small
        # chance that we'll give a few false positives, and we don't care.
        return total_set
        
