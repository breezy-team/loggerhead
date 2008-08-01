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

from loggerhead.controllers import TemplatedBranchView
import logging
import os

class DirectoryUI(TemplatedBranchView):
    """
    """

    template_path = 'loggerhead.templates.directory'

    def __init__(self, static_url_base, path):
        class branch(object):
            @staticmethod
            def static_url(path):
                return self._static_url_base + path
            context_url = 1
        self._branch = branch
        self._history = None
        self._path = path
        self._static_url_base = static_url_base
        self.log = logging.getLogger('')

    def get_values(self, h, args, kwargs, response):
        listing = [d for d in os.listdir(self._path)
                   if not d.startswith('.')
                   and os.path.isdir(os.path.join(self._path, d))]
        listing.sort(key=lambda x: x.lower())
        return {
            'dirs': listing,
            'path': self._path
            }
