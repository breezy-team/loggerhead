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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

import os

from bzrlib.errors import (
    BinaryFile,
    NoSuchId,
    NoSuchRevision,
    )
import bzrlib.textfile
import bzrlib.osutils

from paste.httpexceptions import (
    HTTPBadRequest,
    HTTPMovedPermanently,
    HTTPNotFound,
    HTTPServerError,
    )

from loggerhead.controllers import TemplatedBranchView
try:
    from loggerhead.highlight import highlight
except ImportError:
    highlight = None
from loggerhead import util


class ViewUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.view'
    
    def tree_for(self, file_id, revid):
        file_revid = self._history.get_inventory(revid)[file_id].revision
        return self._history._branch.repository.revision_tree(file_revid)

    def text_lines(self, file_id, revid):
        file_name = os.path.basename(self._history.get_path(revid, file_id))
        
        tree = self.tree_for(file_id, revid)
        file_text = tree.get_file_text(file_id)
        encoding = 'utf-8'
        try:
            file_text = file_text.decode(encoding)
        except UnicodeDecodeError:
            encoding = 'iso-8859-15'
            file_text = file_text.decode(encoding)

        file_lines = bzrlib.osutils.split_lines(file_text)
        # This can throw bzrlib.errors.BinaryFile (which our caller catches).
        bzrlib.textfile.check_text_lines(file_lines)
        
        if highlight is not None:
            hl_lines = highlight(file_name, file_text, encoding)
            # highlight strips off extra newlines at the end of the file.
            extra_lines = len(file_lines) - len(hl_lines)
            hl_lines.extend([u''] * extra_lines)
        else:
            hl_lines = map(util.html_escape, file_lines)
        
        return hl_lines;

    def file_contents(self, file_id, revid):
        try:
            file_lines = self.text_lines(file_id, revid)
        except BinaryFile:
            # bail out; this isn't displayable text
            return ['(This is a binary file.)']

        return file_lines

    def get_values(self, path, kwargs, headers):
        history = self._history
        branch = history._branch
        revid = self.get_revid()
        revid = history.fix_revid(revid)
        file_id = kwargs.get('file_id', None)
        if (file_id is None) and (path is None):
            raise HTTPBadRequest('No file_id or filename '
                                 'provided to view')

        try:
            if file_id is None:
                file_id = history.get_file_id(revid, path)
            if path is None:
                path = history.get_path(revid, file_id)
        except (NoSuchId, NoSuchRevision):
            raise HTTPNotFound()

        filename = os.path.basename(path)

        change = history.get_changes([revid])[0]
        # If we're looking at the tip, use head: in the URL instead
        if revid == branch.last_revision():
            revno_url = 'head:'
        else:
            revno_url = history.get_revno(revid)

        # Directory Breadcrumbs
        directory_breadcrumbs = (
            util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'files'))

        # Create breadcrumb trail for the path within the branch
        try:
            inv = history.get_inventory(revid)
        except:
            self.log.exception('Exception fetching changes')
            raise HTTPServerError('Could not fetch changes')
        branch_breadcrumbs = util.branch_breadcrumbs(path, inv, 'files')

        try:
            file = inv[file_id]
        except NoSuchId:
            raise HTTPNotFound()

        if file.kind == "directory":
            raise HTTPMovedPermanently(self._branch.context_url(['/files', revno_url, path]))

        # no navbar for revisions
        navigation = util.Container()

        return {
            # In AnnotateUI, "annotated" is a dictionary mapping lines to changes.
            # We exploit the fact that bool({}) is False when checking whether
            # we're in "annotated" mode.
            'annotated': {},
            'revno_url': revno_url,
            'file_id': file_id,
            'file_path': path,
            'filename': filename,
            'navigation': navigation,
            'change': change,
            'contents':  self.file_contents(file_id, revid),
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
        }
