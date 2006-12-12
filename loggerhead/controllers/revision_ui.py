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

import datetime
import os
import textwrap

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead.history import History
from loggerhead import util


class RevisionUI (object):

    @turbogears.expose(html='loggerhead.templates.revision')
    def default(self, *args, **kw):
        h = History.from_folder(turbogears.config.get('loggerhead.folder'))
        if len(args) > 0:
            revid = args[0]
        else:
            revid = h.last_revid

        buttons = [
            ('top', turbogears.url('/changes')),
            ('inventory', turbogears.url([ '/inventory', revid ])),
            ('history', turbogears.url([ '/changes', revid ])),
        ]
        
        vals = {
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'revid': revid,
            'change': h.get_change(revid, get_diffs=True),
            'buttons': buttons,
            'util': util,
            'history': h,
            'scan_url': '/revision',
            'pagesize': 1,
        }
        return vals
 