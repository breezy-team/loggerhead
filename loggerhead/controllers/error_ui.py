#
# Copyright (C) 2008  Guillermo Gonzalez <guillo.gonzo@gmail.com>
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

import traceback
from io import StringIO

from .. import util
from ..controllers import TemplatedBranchView


class ErrorUI(TemplatedBranchView):
    template_name = "error"

    def __init__(self, branch, exc_info):
        super(ErrorUI, self).__init__(branch, lambda: None)
        self.exc_info = exc_info

    def get_values(self, path, kwargs, response):
        exc_type, exc_object, exc_tb = self.exc_info
        description = StringIO()
        traceback.print_exception(exc_type, exc_object, None, file=description)
        directory_breadcrumbs = util.directory_breadcrumbs(
            self._branch.friendly_name, self._branch.is_root, "changes"
        )
        return {
            "branch": self._branch,
            "error_title": (
                "An unexpected error occurred whileprocessing the request:"
            ),
            "error_description": description.getvalue(),
            "directory_breadcrumbs": directory_breadcrumbs,
        }
