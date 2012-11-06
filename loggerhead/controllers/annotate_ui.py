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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA
#

import itertools

from loggerhead.controllers.view_ui import ViewUI
from loggerhead import util

class AnnotateUI(ViewUI):

    def annotate_file(self, info):
        file_id = info['file_id']
        revid = info['change'].revid
        
        tree = self.tree_for(file_id, revid)
        
        change_cache = {}
        last_line_revid = None
        last_lineno = None
        message = ""

        revisions = {}

        lineno = 0
        for (line_revid, text), lineno in zip(tree.annotate_iter(file_id), itertools.count(1)):
            if line_revid != last_line_revid:
                last_line_revid = line_revid

                change = change_cache.get(line_revid, None)
                if change is None:
                    change = self._history.get_changes([line_revid])[0]
                    change_cache[line_revid] = change

                try:
                    message = change.comment.splitlines()[0]
                except IndexError:
                    # Comment not present for this revision
                    message = ""

                if last_lineno:
                    # The revspan is of lines between the last revision and this one.
                    # We set the one for the previous revision when we're creating the current revision.
                    revisions[last_lineno].revspan = lineno - last_lineno

                revisions[lineno] = util.Container(change=change, message=message)

                last_lineno = lineno
                last_line_revid = line_revid

        # Zero-size file. Return empty revisions.
        if last_lineno is None:
            return revisions

        # We never set a revspan for the last revision during the loop above, so set it here.
        revisions[last_lineno].revspan = lineno - last_lineno + 1

        return revisions
            
    def get_values(self, path, kwargs, headers):
        values = super(AnnotateUI, self).get_values(path, kwargs, headers)
        values['annotated'] = self.annotate_file(values)
        
        return values
