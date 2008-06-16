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

import logging
import os
import posixpath
import time

from paste.request import path_info_pop
from paste.httpexceptions import HTTPBadRequest

from loggerhead import util
from loggerhead.templatefunctions import templatefunctions


from turbosimpletal import TurboZpt

t = TurboZpt()
tt = t.load_template('loggerhead.templates.annotate')


log = logging.getLogger("loggerhead.controllers")

def dirname(path):
    while path.endswith('/'):
        path = path[:-1]
    path = posixpath.dirname(path)
    return path


class AnnotateUI (object):

    def __init__(self, branch):
        # BranchView object
        self._branch = branch
        self.log = branch.log

    def default(self, request, response):
        z = time.time()
        h = self._branch.history
        kw = request.GET
        util.set_context(kw)

        h._branch.lock_read()
        try:
            args = []
            while 1:
                arg = path_info_pop(request.environ)
                if arg is None:
                    break
                args.append(arg)

            if len(args) > 0:
                revid = h.fix_revid(args[0])
            else:
                revid = h.last_revid

            path = None
            if len(args) > 1:
                path = '/'.join(args[1:])
                if not path.startswith('/'):
                    path = '/' + path

            file_id = kw.get('file_id', None)
            if (file_id is None) and (path is None):
                raise HTTPBadRequest('No file_id or filename provided to annotate')

            if file_id is None:
                file_id = h.get_file_id(revid, path)

            # no navbar for revisions
            navigation = util.Container()

            if path is None:
                path = h.get_path(revid, file_id)
            filename = os.path.basename(path)

            vals = {
                'branch': self._branch,
                'util': util,
                'revid': revid,
                'file_id': file_id,
                'path': path,
                'filename': filename,
                'history': h,
                'navigation': navigation,
                'change': h.get_changes([ revid ])[0],
                'contents': list(h.annotate_file(file_id, revid)),
                'url': self._branch.context_url,
            }
            vals.update(templatefunctions)
            self.log.info('/annotate: %r secs' % (time.time() - z,))
            response.headers['Content-Type'] = 'text/html'
            tt.expand_(response, **vals)
        finally:
            h._branch.unlock()
