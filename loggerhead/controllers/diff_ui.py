# Copyright (C) 2008-2011 Canonical Ltd.
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

import time
from io import BytesIO

from breezy.diff import show_diff_trees
from breezy.revision import NULL_REVISION
from paste.request import parse_querystring, path_info_pop

from ..controllers import TemplatedBranchView


class DiffUI(TemplatedBranchView):
    """Class to output a diff for a single file or revisions."""

    def __call__(self, environ, start_response):
        # End of URL is now /diff/<rev_id>?context=<context_lines>
        # or /diff/<rev_id>/<rev_id>?context=<context_lines>
        # This allows users to choose how much context they want to see.
        # Old format was /diff/<rev_id>/<rev_id> or /diff/<rev_id>
        """Default method called from /diff URL."""
        z = time.time()

        args = []
        while True:
            arg = path_info_pop(environ)
            if arg is None:
                break
            args.append(arg)

        numlines = 3  # This is the default.

        opts = parse_querystring(environ)
        for opt in opts:
            if opt[0] == "context":
                try:
                    numlines = int(opt[1])
                except ValueError:
                    pass

        revid_from = args[0]
        # Convert a revno to a revid if we get a revno.
        revid_from = self._history.fix_revid(revid_from)
        change = self._history.get_changes([revid_from])[0]

        if len(args) == 2:
            revid_to = self._history.fix_revid(args[1])
        elif len(change.parents) == 0:
            revid_to = NULL_REVISION
        else:
            revid_to = change.parents[0].revid

        repo = self._branch.branch.repository
        revtree1 = repo.revision_tree(revid_to)
        revtree2 = repo.revision_tree(revid_from)

        diff_content_stream = BytesIO()
        show_diff_trees(
            revtree1,
            revtree2,
            diff_content_stream,
            old_label="",
            new_label="",
            context=numlines,
        )

        content = diff_content_stream.getvalue()

        self.log.info(
            "/diff %r:%r in %r secs with %r context"
            % (revid_from, revid_to, time.time() - z, numlines)
        )

        revno1 = self._history.get_revno(revid_from)
        revno2 = self._history.get_revno(revid_to)
        filename = "%s_%s.diff" % (revno1, revno2)
        headers = [
            ("Content-Type", "application/octet-stream"),
            ("Content-Length", str(len(content))),
            ("Content-Disposition", "attachment; filename=%s" % (filename,)),
        ]
        start_response("200 OK", headers)
        return [content]
