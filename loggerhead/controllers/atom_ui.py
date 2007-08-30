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

import cherrypy
import turbogears

from loggerhead import util, templatefunctions


class AtomUI (object):
    
    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    @turbogears.expose(template='zpt:loggerhead.templates.atom',
                       format="xml", content_type="application/atom+xml")
    def default(self, *args):
        h = self._branch.get_history()

        h._branch.lock_read()
        try:
            pagesize = int(self._branch.config.get('pagesize', '20'))

            revid_list = h.get_file_view(h.last_revid, None)
            entries = list(h.get_changes(list(revid_list)[:pagesize]))

            vals = {
                'branch': self._branch,
                'changes': entries,
                'util': util,
                'history': h,
                'updated': entries[0].date.isoformat() + 'Z',
            }
            vals.update(templatefunctions)
            h.flush_cache()
            return vals
        finally:
            h._branch.unlock()
