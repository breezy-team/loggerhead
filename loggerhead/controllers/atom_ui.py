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

from loggerhead.controllers import TemplatedBranchView


class AtomUI (TemplatedBranchView):

    template_path = 'loggerhead.templates.atom'

    def get_values(self, path, kwargs, headers):
        history = self._history
        pagesize = int(20)#self._branch.config.get('pagesize', '20'))

        revid_list = history.get_file_view(history.last_revid, None)
        entries = list(history.get_changes(list(revid_list)[:pagesize]))

        headers['Content-Type'] = 'application/atom+xml'
        return {
            'changes': entries,
            'updated': entries[0].utc_date.isoformat(),
            'history': self._history,
        }
