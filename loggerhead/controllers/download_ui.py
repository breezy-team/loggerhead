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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

import logging
import mimetypes
import urllib

from breezy.errors import (
    NoSuchId,
    NoSuchRevision,
    )
try:
    from breezy.transport import NoSuchFile
except ImportError:
    from breezy.errors import NoSuchFile
from breezy import osutils, urlutils
from paste import httpexceptions
from paste.request import path_info_pop

from ..controllers import TemplatedBranchView

log = logging.getLogger("loggerhead.controllers")


class DownloadUI (TemplatedBranchView):

    def encode_filename(self, filename):

        return urlutils.escape(filename)

    def get_args(self, environ):
        args = []
        while True:
            arg = path_info_pop(environ)
            if arg is None:
                break
            args.append(arg)
        return args

    def __call__(self, environ, start_response):
        # /download/<rev_id>/<filename>
        h = self._history
        args = self.get_args(environ)
        if len(args) < 2:
            raise httpexceptions.HTTPMovedPermanently(
                self._branch.absolute_url('/changes'))
        revid = h.fix_revid(args[0])
        try:
            path, filename, content = h.get_file("/".join(args[1:]), revid)
        except (NoSuchFile, NoSuchRevision):
            raise httpexceptions.HTTPNotFound()
        mime_type, encoding = mimetypes.guess_type(filename)
        if mime_type is None:
            mime_type = 'application/octet-stream'
        self.log.info('/download %s @ %s (%d bytes)',
                      path,
                      h.get_revno(revid),
                      len(content))
        encoded_filename = self.encode_filename(filename)
        headers = [
            ('Content-Type', mime_type),
            ('Content-Length', str(len(content))),
            ('Content-Disposition',
             "attachment; filename*=utf-8''%s" % (encoded_filename,)),
            ]
        start_response('200 OK', headers)
        return [content]


class DownloadTarballUI(DownloadUI):

    def __call__(self, environ, start_response):
        """Stream a tarball from a bazaar branch."""
        # Tried to re-use code from downloadui, not very successful
        if not self._branch.export_tarballs:
            raise httpexceptions.HTTPForbidden(
                "Tarball downloads are not allowed")
        archive_format = "tgz"
        history = self._history
        self.args = self.get_args(environ)
        if len(self.args):
            revid = history.fix_revid(self.args[0])
            version_part = '-r' + self.args[0]
        else:
            revid = self.get_revid()
            version_part = ''
        # XXX: Perhaps some better suggestion based on the URL or path?
        #
        # TODO: Perhaps set the tarball suggested mtime to the revision
        # mtime.
        root = self._branch.friendly_name or 'branch'
        filename = root + version_part + '.' + archive_format
        encoded_filename = self.encode_filename(filename)
        headers = [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Disposition',
                "attachment; filename*=utf-8''%s" % (encoded_filename,)),
            ]
        start_response('200 OK', headers)
        tree = history._branch.repository.revision_tree(revid)
        return tree.archive(root=root, format=archive_format, name=filename)
