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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

from loggerhead.controllers import TemplatedBranchView

class ErrorUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.error'

    def __init__(self, branch, exc_info, environ=None):
        super(ErrorUI, self).__init__(branch, None)
        self.exc_info = exc_info
        self.environ = environ

    def get_values(self, h, args, kw, headers):
        exc_type, exc_object, exc_tb = self.exc_info
        import traceback
        from StringIO import StringIO
        description = StringIO()
        traceback.print_exception(exc_type, exc_object, None, file=description)
        return {
            'branch': self._branch,
            'error_title': 'An unexpected error occurred while proccesing the request',
            'error_description': description.getvalue(),
        }
        
