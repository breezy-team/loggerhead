# Cache the whole history data needed by loggerhead about a branch.
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

import logging
import time

from bzrlib.revision import is_null, NULL_REVISION
from bzrlib.tsort import merge_sort


def _strip_NULL_ghosts(revision_graph):
    """
    Copied over from bzrlib meant as a temporary workaround for
    deprecated methods.
    """
    # Filter ghosts, and null:
    if NULL_REVISION in revision_graph:
        del revision_graph[NULL_REVISION]
    for key, parents in revision_graph.items():
        revision_graph[key] = tuple(parent for parent in parents if parent
            in revision_graph)
    return revision_graph


def compute_whole_history_data(branch):
    z = time.time()

    last_revid = branch.last_revision()

    log = logging.getLogger('loggerhead.%s' % (branch.nick,))

    graph = branch.repository.get_graph()
    parent_map = dict(((key, value) for key, value in
         graph.iter_ancestry([last_revid]) if value is not None))

    _revision_graph = _strip_NULL_ghosts(parent_map)
    _full_history = []
    _revision_info = {}
    _revno_revid = {}
    if is_null(last_revid):
        _merge_sort = []
    else:
        _merge_sort = merge_sort(
            _revision_graph, last_revid, generate_revno=True)

    for (seq, revid, merge_depth, revno, end_of_merge) in _merge_sort:
        _full_history.append(revid)
        revno_str = '.'.join(str(n) for n in revno)
        _revno_revid[revno_str] = revid
        _revision_info[revid] = (
            seq, revid, merge_depth, revno_str, end_of_merge)

    _where_merged = {}

    for revid in _revision_graph.keys():
        if _revision_info[revid][2] == 0:
            continue
        for parent in _revision_graph[revid]:
            _where_merged.setdefault(parent, set()).add(revid)

    log.info('built revision graph cache: %r secs' % (time.time() - z,))

    return (_revision_graph, _full_history, _revision_info,
            _revno_revid, _merge_sort, _where_merged)
