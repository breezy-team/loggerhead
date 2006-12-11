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

import base64
import os
import posixpath
import time

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead.history import History
from loggerhead import util


class ChangeLogUI (object):

    @turbogears.expose(html='loggerhead.templates.changelog')
    def default(self, *args, **kw):
        h = History.from_folder(turbogears.config.get('loggerhead.folder'))
        if len(args) > 0:
            revid = args[0]
        else:
            revid = h.last_revid
        revlist = h.get_short_revision_history_from(revid)
        entries = h.get_changelist(list(revlist)[:20])
        
        buttons = [
            ('main', turbogears.url('/changes')),
            ('inventory', turbogears.url([ '/inventory', revid ])),
            ('feed', turbogears.url('/atom')),
        ]

        merge_revids = h.simplify_merge_point_list(h.get_merge_point_list(revid))
        merge_points = [{
            'revid': m_revid,
            'revno': h.get_revno(m_revid),
        } for m_revid in merge_revids]

        vals = {
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'changes': entries,
            'util': util,
            'history': h,
            'scan_url': '/changes',
            'pagesize': 20,
            'revid': revid,
            'buttons': buttons,
            'merge_points': [util.Container(m) for m in merge_points],
        }
        if kw.get('style', None) == 'rss':
            vals['tg_template'] = 'loggerhead.templates.changelog-rss'
            vals['tg_format'] = 'xml'
            vals['tg_content_type'] = 'application/rss+xml'
        return vals
