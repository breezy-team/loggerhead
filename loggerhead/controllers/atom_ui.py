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

import turbogears

from loggerhead.history import History
from loggerhead import util


FOLDER = '/Users/robey/code/paramiko/paramiko'
BRANCH_NAME = 'paramiko-dev'
EXTERNAL_URL = 'http://localhost:8080'

class AtomUI (object):

    @turbogears.expose(template='loggerhead.templates.atom', format="xml", content_type="application/atom+xml")
    def default(self, *args):
        h = History.from_folder(FOLDER)
        if len(args) > 0:
            revid = args[0]
        else:
            revid = h.last_revid
        revlist = h.get_short_revision_history_from(revid)
        entries = list(h.get_changelist(list(revlist)[:20]))

        vals = {
            'external_url': EXTERNAL_URL,
            'branch_name': BRANCH_NAME,
            'changes': entries,
            'util': util,
            'history': h,
            'scan_url': '/changes',
            'updated': entries[0].date.isoformat() + 'Z',
        }
        return vals
