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

from breezy.errors import (
    BinaryFile,
    NoSuchId,
    NoSuchRevision,
    )
try:
    from breezy.transport import NoSuchFile
except ImportError:
    from breezy.errors import NoSuchFile
from breezy import (
    osutils,
    urlutils,
    )
import breezy.textfile

from paste.httpexceptions import (
    HTTPBadRequest,
    HTTPMovedPermanently,
    HTTPNotFound,
    )

from ..controllers import TemplatedBranchView
try:
    from ..highlight import highlight
except ImportError:
    highlight = None
from .. import util


class ViewUI(TemplatedBranchView):

    template_name = 'view'

    def tree_for(self, path, revid):
        if not isinstance(path, str):
            raise TypeError(path)
        if not isinstance(revid, bytes):
            raise TypeError(revid)
        return self._history._branch.repository.revision_tree(revid)

    def text_lines(self, path, revid):
        file_name = os.path.basename(path)

        tree = self.tree_for(path, revid)
        file_text = tree.get_file_text(path)

        encoding = 'utf-8'
        try:
            file_text.decode(encoding)
        except UnicodeDecodeError:
            encoding = 'iso-8859-15'
            file_text.decode(encoding)

        file_lines = osutils.split_lines(file_text)
        # This can throw breezy.errors.BinaryFile (which our caller catches).
        breezy.textfile.check_text_lines(file_lines)

        file_text = file_text.decode(encoding)
        file_lines = osutils.split_lines(file_text)

        if highlight is not None:
            hl_lines = highlight(file_name, file_text, encoding)
            # highlight strips off extra newlines at the end of the file.
            extra_lines = len(file_lines) - len(hl_lines)
            hl_lines.extend([u''] * extra_lines)
        else:
            hl_lines = [util.html_escape(line) for line in file_lines]

        return hl_lines

    def file_contents(self, path, revid):
        try:
            file_lines = self.text_lines(path, revid)
        except BinaryFile:
            # bail out; this isn't displayable text
            return ['(This is a binary file.)']

        return file_lines

    def get_values(self, path, kwargs, headers):
        history = self._history
        branch = history._branch
        revid = self.get_revid()
        if path is None:
            raise HTTPBadRequest('No filename provided to view')

        if not history.file_exists(revid, path):
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

        tree = history.revision_tree(revid)

        # Create breadcrumb trail for the path within the branch
        branch_breadcrumbs = util.branch_breadcrumbs(path, tree, 'files')

        try:
            if tree.kind(path) == "directory":
                raise HTTPMovedPermanently(
                    self._branch.context_url(['/files', revno_url, path]))
        except NoSuchFile:
            raise HTTPNotFound()

        # no navbar for revisions
        navigation = util.Container()

        return {
            # In AnnotateUI, "annotated" is a dictionary mapping lines to
            # changes.  We exploit the fact that bool({}) is False when
            # checking whether we're in "annotated" mode.
            'annotated': {},
            'revno_url': revno_url,
            'file_path': path,
            'filename': filename,
            'navigation': navigation,
            'change': change,
            'contents':  self.file_contents(path, revid),
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
        }
