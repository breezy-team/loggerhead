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

import turbogears
from cherrypy import HTTPRedirect, InternalError, response


class BundleUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    @turbogears.expose()
    def default(self, *args, **kw):
        # /bundle/<rev_id>/[<compare_rev_id>/]filename
        z = time.time()
        h = self._branch.get_history()

        h._branch.lock_read()
        try:
            if len(args) < 1:
                raise HTTPRedirect(self._branch.url('/changes'))
            revid = h.fix_revid(args[0])
            if len(args) >= 3:
                compare_revid = h.fix_revid(args[1])
            else:
                compare_revid = None

            try:
                bundle_data = h.get_bundle(revid, compare_revid)
            except:
                self.log.exception('Exception fetching bundle')
                raise InternalError('Could not fetch bundle')

            response.headers['Content-Type'] = 'application/octet-stream'
            response.headers['Content-Length'] = len(bundle_data)
            response.body = bundle_data
            self.log.info('/bundle: %r seconds' % (time.time() - z,))
            return response.body
        finally:
            h._branch.unlock()
