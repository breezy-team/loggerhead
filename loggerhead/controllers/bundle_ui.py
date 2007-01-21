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
import time

import turbogears
from cherrypy import HTTPRedirect, response

from loggerhead import util


class BundleUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    @turbogears.expose()
    def default(self, *args, **kw):
        # /bundle/<rev_id>/filename
        z = time.time()
        h = self._branch.get_history()
        compare_revid = kw.get('compare_revid', None)

        if len(args) < 1:
            raise HTTPRedirect(self._branch.url('/changes'))
        revid = h.fix_revid(args[0])
        compare_revid = None
        if len(args) >= 3:
            compare_revid = h.fix_revid(args[1])

        try:
            bundle_data = h.get_bundle(revid, compare_revid)
        except Exception, x:
            self.log.error('Exception fetching bundle: %s' % (x,))
            util.log_exception(self.log)
            raise HTTPRedirect(self._branch.url('/changes'))
            
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Length'] = len(bundle_data)
        response.body = bundle_data
        self.log.info('/bundle: %r seconds' % (time.time() - z,))
        return response.body
