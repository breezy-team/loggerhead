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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import datetime
import logging
import os

from bzrlib import branch

from loggerhead.controllers import TemplatedBranchView

class DirEntry(object):
    def __init__(self, dirname, parity, branch):
        self.dirname = dirname
        self.parity = parity
        self.branch = branch
        if branch is not None:
            self.last_change =  datetime.datetime.fromtimestamp(
                branch.repository.get_revision(branch.last_revision()).timestamp)

class DirectoryUI(TemplatedBranchView):
    """
    """

    template_path = 'loggerhead.templates.directory'

    def __init__(self, static_url_base, path, name):
        class _branch(object):
            context_url = 1
        self._branch = _branch
        self._history = None
        self._path = path
        self._name = name
        self._static_url_base = static_url_base
        self.log = logging.getLogger('')

    def get_values(self, h, args, kwargs, response):
        listing = [d for d in os.listdir(self._path)
                   if not d.startswith('.')
                   and os.path.isdir(os.path.join(self._path, d))]
        listing.sort(key=lambda x: x.lower())
        dirs = []
        parity = 0
        def static_url(path):
            return self._static_url_base + path
        for d in listing:
            p = os.path.join(self._path, d)
            try:
                b = branch.Branch.open(p)
            except:
                b = None
            dirs.append(DirEntry(d, parity, b))
            parity = 1 - parity
        # Create breadcrumb trail
        dir_parts = self._name.strip('/').split('/')
        breadcrumbs = []
        for index, dir_name in enumerate(dir_parts):
            breadcrumbs.append({
                'dir_name': dir_name,
                'path': '/'.join(dir_parts[:index + 1]),
            })
        return {
            'dirs': dirs,
            'name': self._name,
            'static_url': static_url,
            'breadcrumbs': breadcrumbs,
            }
