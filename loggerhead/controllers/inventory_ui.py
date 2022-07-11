#
# Copyright (C) 2008  Canonical Ltd.
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

import logging
import posixpath
import urllib

from paste.httpexceptions import HTTPNotFound, HTTPMovedPermanently

from breezy import (
    errors,
    osutils,
    urlutils,
    )
from breezy.revision import is_null as is_null_rev

from .. import util
from ..controllers import TemplatedBranchView



def dirname(path):
    if path is not None:
        path = path.rstrip('/')
        path = urlutils.escape(posixpath.dirname(path))
    return path


class InventoryUI(TemplatedBranchView):

    template_name = 'inventory'
    supports_json = True

    def get_filelist(self, tree, path, sort_type, revno_url):
        """
        return the list of all files (and their attributes) within a given
        path subtree.

        @param tree: The tree
        @param path: The path of a directory within the tree.
        @param sort_type: How to sort the results... XXX.
        """
        file_list = []

        if tree.kind(path) != 'directory':
            raise HTTPMovedPermanently(self._branch.context_url(['/view', revno_url, path]))

        revid_set = set()

        child_entries = []

        for entry in tree.iter_child_entries(path):
            child_path = osutils.pathjoin(path, entry.name)
            child_revision = tree.get_file_revision(child_path)
            revid_set.add(child_revision)
            child_entries.append((child_path, entry, child_revision))

        change_dict = {}
        for change in self._history.get_changes(list(revid_set)):
            change_dict[change.revid] = change

        for child_path, entry, child_revision in child_entries:
            pathname = entry.name
            contents_changed_rev = None
            if entry.kind == 'directory':
                pathname += '/'
                size = None
            else:
                size = entry.text_size

            file_timestamp = change_dict[child_revision].timestamp

            # TODO: For the JSON rendering, this inlines the "change" aka
            # revision information attached to each file. Consider either
            # pulling this out as a separate changes dict, or possibly just
            # including the revision id and having a separate request to get
            # back the revision info.
            file = util.Container(
                filename=entry.name, executable=entry.executable,
                kind=entry.kind, absolutepath=child_path,
                size=size, revid=child_revision,
                change=change_dict[child_revision], contents_changed_rev=contents_changed_rev)
            file_list.append(file)

        if sort_type == 'filename':
            file_list.sort(key=lambda x: x.filename.lower()) # case-insensitive
        elif sort_type == 'size':
            def size_key(x):
                if x.size is None:
                    return -1
                return x.size
            file_list.sort(key=size_key)
        elif sort_type == 'date':
            file_list.sort(key=lambda x: x.change.date, reverse=True)

        if sort_type != 'date':
        # Don't always sort directories first.
            file_list.sort(key=lambda x: x.kind != 'directory')

        return file_list

    def get_values(self, path, kwargs, headers):
        history = self._history
        branch = history._branch
        try:
            revid = self.get_revid()
            rev_tree = branch.repository.revision_tree(revid)
        except errors.NoSuchRevision:
            raise HTTPNotFound()

        start_revid = kwargs.get('start_revid', None)
        sort_type = kwargs.get('sort', 'filename')

        if path is None:
            path = "/"

        path = path.rstrip('/')
        if not rev_tree.has_filename(path) and not is_null_rev(revid):
            raise HTTPNotFound()

        # Are we at the top of the tree
        if path in ['/', '']:
            updir = None
        else:
            updir = dirname(path)

        if not is_null_rev(revid):
            change = history.get_changes([revid])[0]
            # If we're looking at the tip, use head: in the URL instead
            if revid == branch.last_revision():
                revno_url = 'head:'
            else:
                revno_url = history.get_revno(revid)
            history.add_branch_nicks(change)
            filelist = self.get_filelist(rev_tree, path, sort_type, revno_url)

        else:
            start_revid = None
            change = None
            path = "/"
            updir = None
            revno_url = 'head:'
            filelist = []

        return {
            'revid': revid,
            'revno_url': revno_url,
            'change': change,
            'path': path,
            'updir': updir,
            'filelist': filelist,
            'start_revid': start_revid,
        }

    def add_template_values(self, values):
        super(InventoryUI, self).add_template_values(values)
        # Directory Breadcrumbs
        directory_breadcrumbs = util.directory_breadcrumbs(
                self._branch.friendly_name,
                self._branch.is_root,
                'files')

        path = values['path']
        revid = values['revid']
        # no navbar for revisions
        navigation = util.Container()

        if is_null_rev(revid):
            branch_breadcrumbs = []
        else:
            # Create breadcrumb trail for the path within the branch
            branch = self._history._branch
            rev_tree = branch.repository.revision_tree(revid)
            branch_breadcrumbs = util.branch_breadcrumbs(path, rev_tree, 'files')
        values.update({
            'fileview_active': True,
            'directory_breadcrumbs': directory_breadcrumbs,
            'branch_breadcrumbs': branch_breadcrumbs,
            'navigation': navigation,
        })
