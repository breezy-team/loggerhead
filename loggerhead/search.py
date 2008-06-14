import sets
import os
from bzrlib.plugins.search import errors
from bzrlib.plugins.search import index as _mod_index
from bzrlib.plugins.search.index import FileTextHit, RevisionHit
from bzrlib.transport import get_transport
from bzrlib.plugin import load_plugins
load_plugins()

def search_revisions(query_list=[]):
    #This is terribly stupid, you should pass on the location of the branch
    absfolder = '/home/beuno/bzr_devel/bzr.garbage'
    trans = get_transport(absfolder)
    index = _mod_index.open_index_url(trans.base)
    query = [(query_item,) for query_item in query_list]
    revid_list = []
    for result in index.search(query):
        if isinstance(result, FileTextHit):
            revid_list.append(result.text_key[1])
        elif isinstance(result, RevisionHit):
            revid_list.append(result.revision_key)

    if len(revid_list) == 0:
        raise errors.NoMatch(query_listo)

    return list(sets.Set(revid_list))
