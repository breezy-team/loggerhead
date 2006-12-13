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
import logging
import os
import posixpath
import time

import turbogears
from cherrypy import HTTPRedirect, session

from loggerhead.history import History
from loggerhead import util

log = logging.getLogger("loggerhead.controllers")


class ChangeLogUI (object):

    @turbogears.expose(html='loggerhead.templates.changelog')
    def default(self, *args, **kw):
        h = History.from_folder(turbogears.config.get('loggerhead.folder'))
        if len(args) > 0:
            revid = args[0]
        else:
            revid = None

        path = kw.get('path', None)
        pagesize = int(turbogears.config.get('loggerhead.pagesize', '20'))
        
        try:
            revlist, revid = h.get_navigation(revid, path)
            entry_list = list(h.get_revids_from(revlist, revid))[:pagesize]
            entries = h.get_changelist(entry_list)
        except Exception, x:
            log.error('Exception fetching changes: %r, %s' % (x, x))
            raise HTTPRedirect(turbogears.url('/changes'))

        buttons = [
            ('top', turbogears.url('/changes')),
            ('inventory', turbogears.url([ '/inventory', revid ])),
            ('feed', turbogears.url('/atom')),
        ]

        navigation = util.Container(pagesize=pagesize, revid=revid, revlist=revlist, path=path,
                                    buttons=buttons, scan_url='/changes')
        vals = {
            'branch_name': turbogears.config.get('loggerhead.branch_name'),
            'changes': entries,
            'util': util,
            'history': h,
            'revid': revid,
            'navigation': navigation,
            'path': path,
        }
        if kw.get('style', None) == 'rss':
            vals['tg_template'] = 'loggerhead.templates.changelog-rss'
            vals['tg_format'] = 'xml'
            vals['tg_content_type'] = 'application/rss+xml'
        return vals
