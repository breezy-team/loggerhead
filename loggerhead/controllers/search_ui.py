# Copyright (C) 2008  Martin Albisetti <argentina@gmail.com>
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

import turbogears
from cherrypy import InternalError

from loggerhead import history
from loggerhead import util
from loggerhead.templatefunctions import templatefunctions
from loggerhead import search


class SearchUI(object):
    """
    
    Class to output progressive search result terms.
    """
    
    def __init__(self, branch):
        self._branch = branch
        self.log = branch.log

    @util.strip_whitespace
    @turbogears.expose(html='zpt:loggerhead.templates.search')
    
    def default(self, *args, **kwargs):
        """
        Default method called from the search box as /search URL

        Returns a list of suggested search terms parsed through the
        templating engine.
        """
        terms = []
        query = kwargs['query']
        if len(query) > 0:
            h = self._branch.get_history()
            terms = search.search_revisions(h._branch, query, True)

        vals = {'terms':terms}
        vals.update(templatefunctions)
        return vals

