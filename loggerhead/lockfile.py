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

import os
import threading
import time

from loggerhead import util


with_lock = util.with_lock('_tlock', 'LockFile')

MAX_STALE_TIME = 5 * 60


class LockFile (object):
    """
    simple lockfile implementation that mimics the API of threading.Lock, so
    it can be used interchangably.  it's actually a reentrant lock, so the
    lock may be acquired multiple times by the same thread, as long as it's
    released an equal number of times.  unlike threading.Lock, this lock can
    be used across processes.

    this uses os.open(O_CREAT|O_EXCL), which apparently works even on windows,
    but will not work over NFS, if anyone still uses that.  so don't put the
    cache folder on an NFS server...
    """

    def __init__(self, filename):
        self._filename = filename
        # thread lock to maintain internal consistency
        self._tlock = threading.Lock()
        self._count = 0
        if os.path.exists(filename):
            # remove stale locks left over from a previous run
            if time.time() - os.stat(filename).st_mtime > MAX_STALE_TIME:
                os.remove(filename)

    @with_lock
    def _try_acquire(self):
        if self._count > 0:
            self._count += 1
            return True
        try:
            fd = os.open(self._filename,
                         os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0600)
            os.close(fd)
            self._count += 1
            return True
        except OSError:
            return False

    def acquire(self):
        # try over and over, sleeping on exponential backoff with
        # an upper limit of about 5 seconds
        pause = 0.1
        #max_pause = 5.0
        max_pause = 0.1
        while True:
            if self._try_acquire():
                return
            time.sleep(pause)
            pause = min(pause * 2.0, max_pause)

    @with_lock
    def release(self):
        self._count -= 1
        if self._count == 0:
            os.remove(self._filename)
