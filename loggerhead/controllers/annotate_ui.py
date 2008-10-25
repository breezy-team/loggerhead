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

import os
import posixpath

from paste.httpexceptions import HTTPBadRequest, HTTPServerError

from loggerhead.controllers import TemplatedBranchView
from loggerhead import util


def dirname(path):
    while path.endswith('/'):
        path = path[:-1]
    path = posixpath.dirname(path)
    return path


class AnnotateUI (TemplatedBranchView):

    template_path = 'loggerhead.templates.annotate'

    def get_values(self, h, revid, path, kwargs, headers):

        revid = h.fix_revid(revid)
        file_id = kwargs.get('file_id', None)
        if (file_id is None) and (path is None):
            raise HTTPBadRequest('No file_id or filename '
                                 'provided to annotate')

        if file_id is None:
            file_id = h.get_file_id(revid, path)

        # no navbar for revisions
        navigation = util.Container()

        if path is None:
            path = h.get_path(revid, file_id)
        filename = os.path.basename(path)

        # Directory Breadcrumbs
        directory_breadcrumbs = (
            util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'files'))

        # Create breadcrumb trail for the path within the branch
        try:
            inv = h.get_inventory(revid)
        except:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')
        branch_breadcrumbs = util.branch_breadcrumbs(path, inv, 'files')

        return {
            'revid': revid,
            'file_id': file_id,
            'path': path,
            'filename': filename,
            'navigation': navigation,
            'change': h.get_changes([revid])[0],
            'contents': list(h.annotate_file(file_id, revid)),
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
        }
