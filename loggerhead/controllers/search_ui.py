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

from loggerhead.controllers import TemplatedBranchView
from loggerhead import search


class SearchUI(TemplatedBranchView):
    """

    Class to output progressive search result terms.
    """

    template_path = 'loggerhead.templates.search'

    def get_values(self, path, kwargs, response):
        """
        Default method called from the search box as /search URL

        Returns a list of suggested search terms parsed through the
        templating engine.
        """
        terms = []
        query = kwargs['query']
        if len(query) > 0:
            terms = search.search_revisions(self._branch.branch, query, True)
            if terms is not None:
                terms = [term[0] for term in terms]
            else:
                # Should show a 'search is not available' etc box.
                terms = []

        return {'terms': terms}
