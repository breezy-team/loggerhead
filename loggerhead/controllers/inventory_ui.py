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
import posixpath

from paste.httpexceptions import HTTPNotFound, HTTPServerError

from bzrlib.revision import is_null as is_null_rev

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView


log = logging.getLogger("loggerhead.controllers")

def dirname(path):
    while path.endswith('/'):
        path = path[:-1]
    path = posixpath.dirname(path)
    return path


class InventoryUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.inventory'

    def get_values(self, h, args, kw, headers):
        if len(args) > 0:
            revid = h.fix_revid(args[0])
        else:
            revid = h.last_revid

        # no navbar for revisions
        navigation = util.Container()
        # Directory Breadcrumbs
        directory_breadcrumbs = util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'files')

        if not is_null_rev(revid):
            try:
                inv = h.get_inventory(revid)
            except:
                self.log.exception('Exception fetching changes')
                raise HTTPServerError('Could not fetch changes')

            file_id = kw.get('file_id', inv.root.file_id)
            start_revid = kw.get('start_revid', None)
            sort_type = kw.get('sort', None)

            change = h.get_changes([ revid ])[0]
            # add parent & merge-point branch-nick info, in case it's useful
            h.get_branch_nicks([ change ])

            path = inv.id2path(file_id)
            if not path.startswith('/'):
                path = '/' + path
            idpath = inv.get_idpath(file_id)
            if len(idpath) > 1:
                updir = dirname(path)
                updir_file_id = idpath[-2]
            else:
                updir = None
                updir_file_id = None
            if updir == '/':
                updir_file_id = None

            # Create breadcrumb trail for the path within the branch
            branch_breadcrumbs = util.branch_breadcrumbs(path, inv, 'files')
            filelist = h.get_filelist(inv, file_id, sort_type)
        else:
            inv = None
            file_id = None
            start_revid = None
            sort_type = None
            change = None
            path = "/"
            idpath = None
            updir = None
            updir_file_id = None
            branch_breadcrumbs = []
            filelist = []

        return {
            'branch': self._branch,
            'util': util,
            'revid': revid,
            'change': change,
            'file_id': file_id,
            'path': path,
            'updir': updir,
            'updir_file_id': updir_file_id,
            'filelist': filelist,
            'history': h,
            'posixpath': posixpath,
            'navigation': navigation,
            'url': self._branch.context_url,
            'start_revid': start_revid,
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
        }
