# Copyright (C) 2008  Martin Albisetti <argentina@gmail.com>
# Copyright (C) 2008  Robert Collins
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
import sets
import os
from bzrlib.plugins.search import errors
from bzrlib.plugins.search import index as _mod_index
from bzrlib.plugins.search.index import FileTextHit, RevisionHit
from bzrlib.transport import get_transport
from bzrlib.plugin import load_plugins
load_plugins()

def search_revisions(branch, query_list=[], suggest=False):
    index = _mod_index.open_index_branch(branch)
    query = query_list.split(' ')
    query = [(term,) for term in query]
    revid_list = []
    index._branch.lock_read()
    if suggest:
        terms = index.suggest(query)
        terms = list(terms)
        terms.sort()
        return terms
    else:
        for result in index.search(query):
            if isinstance(result, FileTextHit):
                revid_list.append(result.text_key[1])
            elif isinstance(result, RevisionHit):
                revid_list.append(result.revision_key)

        return list(sets.Set(revid_list))
    index._branch.unlock()
