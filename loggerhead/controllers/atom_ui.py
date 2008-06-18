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

from loggerhead.controllers import TemplatedBranchView


class AtomUI (TemplatedBranchView):

    def get_values(self, h, args, kw, response):
        h = self._branch.history

        pagesize = int(20)#self._branch.config.get('pagesize', '20'))

        revid_list = h.get_file_view(h.last_revid, None)
        entries = list(h.get_changes(list(revid_list)[:pagesize]))

        response.headers['Content-Type'] = 'application/atom+xml'
        return {
            'changes': entries,
            'updated': entries[0].date.isoformat() + 'Z',
        }
