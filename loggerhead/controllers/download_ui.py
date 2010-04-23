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
import urllib

from paste import httpexceptions
from paste.request import path_info_pop

from loggerhead.controllers import TemplatedBranchView

log = logging.getLogger("loggerhead.controllers")


class DownloadUI (TemplatedBranchView):

    def __call__(self, environ, start_response):
        # /download/<rev_id>/<file_id>/[filename]

        h = self._history

        args = []
        while True:
            arg = path_info_pop(environ)
            if arg is None:
                break
            args.append(arg)

        if len(args) < 2:
            raise httpexceptions.HTTPMovedPermanently(self._branch.url(
                      '../changes'))

        revid = h.fix_revid(args[0])
        file_id = args[1]
        path, filename, content = h.get_file(file_id, revid)
        mime_type, encoding = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'

        self.log.info('/download %s @ %s (%d bytes)',
                      path,
                      h.get_revno(revid),
                      len(content))
        encoded_filename = urllib.quote(filename.encode('utf-8'))
        headers = [
            ('Content-Type', mime_type),
            ('Content-Length', str(len(content))),
            ('Content-Disposition',
             "attachment; filename*=utf-8''%s" % (encoded_filename,)),
            ]
        start_response('200 OK', headers)
        return [content]
