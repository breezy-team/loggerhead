#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
# Copyright (C) 2006  Goffredo Baroncelli <kreijack@inwind.it>
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

import logging
import mimetypes
import time

from paste import httpexceptions
from paste.request import path_info_pop

log = logging.getLogger("loggerhead.controllers")


class DownloadUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    def default(self, request, response):
        # /download/<rev_id>/<file_id>/[filename]
        z = time.time()
        h = self._branch.history

        h._branch.lock_read()
        try:
            args = []
            while 1:
                arg = path_info_pop(request.environ)
                if arg is None:
                    break
                args.append(arg)

            if len(args) < 2:
                raise httpexceptions.HTTPMovedPermanently(self._branch.url('../changes'))

            revid = h.fix_revid(args[0])
            file_id = args[1]
            path, filename, content = h.get_file(file_id, revid)
            mime_type, encoding = mimetypes.guess_type(filename)
            if mime_type is None:
                mime_type = 'application/octet-stream'

            self.log.info('/download %s @ %s (%d bytes)', path, h.get_revno(revid), len(content))
            response.headers['Content-Type'] = mime_type
            response.headers['Content-Length'] = len(content)
            response.headers['Content-Disposition'] = 'attachment; filename=%s'%(filename,)
            response.write(content)
        finally:
            h._branch.unlock()
