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

import time

from paste import httpexceptions
from paste.request import path_info_pop


class BundleUI (object):

    def __init__(self, branch, history):
        # BranchView object
        self._branch = branch
        self._history = history
        self.log = branch.log

    def __call__(self, environ, start_response):
        # /bundle/<rev_id>/[<compare_rev_id>/]filename
        z = time.time()
        h = self._history

        args = []
        while 1:
            arg = path_info_pop(environ)
            if arg is None:
                break
            args.append(arg)
        if len(args) < 1:
            raise httpexceptions.HTTPMovedPermanently('../changes')
        revid = h.fix_revid(args[0])
        if len(args) >= 3:
            compare_revid = h.fix_revid(args[1])
        else:
            compare_revid = None

        try:
            bundle_data = h.get_bundle(revid, compare_revid)
        except:
            self.log.exception('Exception fetching bundle')
            raise httpexceptions.HTTPServerError('Could not fetch bundle')
        self.log.info('/bundle: %r seconds' % (time.time() - z,))
        headers = [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Length', len(bundle_data)),
            ('Content-Disposition', 'attachment; filename=bundle.txt'),
                  ]
        start_response('200 OK', headers)
        return [bundle_data]
        #response.headers['Content-Type'] = 'application/octet-stream'
        #response.headers['Content-Length'] = len(bundle_data)
        #response.write(bundle_data)
