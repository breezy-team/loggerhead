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

from paste.httpexceptions import HTTPServerError

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView


log = logging.getLogger("loggerhead.controllers")

def dirname(path):
    if path is not None:
        while path.endswith('/'):
            path = path[:-1]
        path = posixpath.dirname(path)
    return path


class InventoryUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.inventory'

    def get_values(self, h, revid, path, kwargs, headers):

        try:
            inv = h.get_inventory(revid)
        except:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')

        file_id = kwargs.get('file_id', None)
        start_revid = kwargs.get('start_revid', None)
        sort_type = kwargs.get('sort', None)

        # no navbar for revisions
        navigation = util.Container()

        change = h.get_changes([ revid ])[0]
        # add parent & merge-point branch-nick info, in case it's useful
        h.get_branch_nicks([ change ])

        if path is not None:
            if not path.startswith('/'):
                path = '/' + path
            file_id = h.get_file_id(revid, path)
        else:
            path = inv.id2path(file_id)
        
        if file_id is None:
            file_id = inv.root.file_id


        idpath = inv.get_idpath(file_id)
        if len(idpath) > 1:
            updir = dirname(path)
            updir_file_id = idpath[-2]
        else:
            updir = None
            updir_file_id = None
        if updir == '/':
            updir_file_id = None

        # Directory Breadcrumbs
        directory_breadcrumbs = util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'files')

        # Create breadcrumb trail for the path within the branch
        branch_breadcrumbs = util.branch_breadcrumbs(path, inv, 'files')
        
        return {
            'branch': self._branch,
            'util': util,
            'revid': revid,
            'change': change,
            'file_id': file_id,
            'path': path,
            'updir': updir,
            'updir_file_id': updir_file_id,
            'filelist': h.get_filelist(inv, file_id, sort_type),
            'history': h,
            'posixpath': posixpath,
            'navigation': navigation,
            'url': self._branch.context_url,
            'start_revid': start_revid,
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
        }
