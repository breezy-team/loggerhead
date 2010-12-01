#
# Copyright (C) 2010 Canonical Ltd.
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

from loggerhead.controllers.view_ui import ViewUI
from loggerhead import util

class AnnotateUI(ViewUI):

    def annotate_file(self, info):
        file_id = info['file_id']
        revid = info['change'].revid
        
        tree = self.tree_for(file_id, revid)
        
        change_cache = {}
        last_line_revid = None
        parity = 1
        for line_revid, text in tree.annotate_iter(file_id):
            if line_revid == last_line_revid:
                # remember which lines have a new revno and which don't
                new_rev = False
            else:
                new_rev = True
                parity ^= 1
                last_line_revid = line_revid
                if line_revid in change_cache:
                    change = change_cache[line_revid]
                else:
                    change = self._history.get_changes([line_revid])[0]
                    change_cache[line_revid] = change

            yield util.Container(
                parity=parity, new_rev=new_rev, change=change)
            
    def get_values(self, path, kwargs, headers):
        values = super(AnnotateUI, self).get_values(path, kwargs, headers)
        values['annotated'] = self.annotate_file(values)
        
        return values
