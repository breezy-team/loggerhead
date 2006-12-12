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

        rev = h.get_revision(revid)
        if len(rev.parent_ids) > 0:
            previous = rev.parent_ids[0]
        else:
            previous = None
        
        show_diff = kw.get('show_diff', False)
        
        parents = [util.Container(revid=r, revno=h.get_revno(r)) for r in rev.parent_ids]
        children = [util.Container(revid=r, revno=h.get_revno(r)) for r in h.get_where_merged(revid)]
        
        comment = rev.message.splitlines()
        if len(comment) == 1:
            # robey-style 1-line long message
            comment = textwrap.wrap(comment[0])
        
        changes = h.diff_revisions(revid, previous)
        
        buttons = [
            ('main', turbogears.url('/changes')),
            ('inventory', turbogears.url([ '/inventory', revid ])),
            ('log', turbogears.url([ '/changes', revid ])),
        ]
        
        vals = {
            'revid': revid,
            'buttons': buttons,
            'revno': h.get_revno(revid),
            'parents': parents,
            'children': children,
            'author': rev.committer,
            'comment': comment,
            'comment_clean': [util.html_clean(s) for s in comment],
            'date': datetime.datetime.fromtimestamp(rev.timestamp),
            'changes': changes,
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'util': util,
            'history': h,
            'scan_url': '/revision',
            'pagesize': 1,
        }
        return vals
 
        