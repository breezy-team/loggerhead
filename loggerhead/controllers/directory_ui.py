# Copyright (C) 2008  Canonical Ltd.
#                     (Authored by Martin Albisetti <argentina@gmail.com>)
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

import datetime
import logging
import stat

from bzrlib import branch, errors

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView


class DirEntry(object):

    def __init__(self, dirname, parity, branch):
        self.dirname = dirname
        self.parity = parity
        self.branch = branch
        if branch is not None:
            # If a branch is empty, bzr raises an exception when trying this
            try:
                self.last_change = datetime.datetime.utcfromtimestamp(
                    branch.repository.get_revision(
                        branch.last_revision()).timestamp)
            except:
                self.last_change = None


class DirectoryUI(TemplatedBranchView):
    """
    """

    template_path = 'loggerhead.templates.directory'

    def __init__(self, static_url_base, transport, name):

        class _branch(object):
            context_url = 1

            @staticmethod
            def static_url(path):
                return self._static_url_base + path
        self._branch = _branch
        self._history_callable = lambda: None
        self._name = name
        self._static_url_base = static_url_base
        self.transport = transport
        self.log = logging.getLogger('')

    def get_values(self, path, kwargs, response):
        listing = [d for d in self.transport.list_dir('.')
                   if not d.startswith('.')]
        listing.sort(key=lambda x: x.lower())
        dirs = []
        parity = 0
        for d in listing:
            try:
                b = branch.Branch.open_from_transport(self.transport.clone(d))
                if b.get_config().get_user_option('http_serve') == 'False':
                    continue
            except:
                try:
                    if not stat.S_ISDIR(self.transport.stat(d).st_mode):
                        continue
                except errors.NoSuchFile:
                    continue
                b = None
            dirs.append(DirEntry(d, parity, b))
            parity = 1 - parity
        # Create breadcrumb trail
        directory_breadcrumbs = util.directory_breadcrumbs(
                self._name,
                False,
                'directory')
        return {
            'dirs': dirs,
            'name': self._name,
            'directory_breadcrumbs': directory_breadcrumbs,
            }
