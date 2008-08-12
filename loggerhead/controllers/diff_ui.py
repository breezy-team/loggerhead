
from cStringIO import StringIO
import logging
import time
import sys

from paste import httpexceptions
from paste.request import path_info_pop

from loggerhead import history
from loggerhead import util
from loggerhead.templatefunctions import templatefunctions

import bzrlib
from bzrlib import branch
from bzrlib.diff import show_diff_trees


log = logging.getLogger("loggerhead.controllers")

class DiffUI(object):
    """

    Class to output a diff for a single file. This is mainly aimed at
    using it through AJAX, as it doesn't present it within the rest of the
    template.
    """
    
    def __init__(self, branch, history):
        self._branch = branch
        self._history = history
        self.log = history.log

    
    def __call__(self, environ, start_response):
        # /diff/<rev_id>?compare_to=<rev_id>
        """
        Default method called from /diff URL.
        """

        z = time.time()
        s = StringIO()
        
        args = []
        while 1:
            arg = path_info_pop(environ)
            if arg is None:
                break
            args.append(arg)
        
        revid_from = args[0]
        # Convert a revno to a revid if we get a revno
        revid_from = self._history.fix_revid(revid_from)
        change = self._history.get_changes([revid_from])[0]

        revid_to = args[1]

        if revid_to is None:
            revid_to = change.parents[0].revid 
        else:
            revid_to = self._history.fix_revid(revid_to)

        repo = self._branch.branch.repository
        revtree1 = repo.revision_tree(revid_from)
        revtree2 = repo.revision_tree(revid_to)
        
        show_diff_trees(revtree1, revtree2, s, 
                               specific_files=None,
                               external_diff_options=None,
                               old_label=old_label'', new_label='',
                               extra_trees=None, using=None)

        content = s.getvalue()

        self.log.info('/diff %r:%r in %r secs' % (revid_from, revid_to, 
                                                  time.time() - z))

        filename = 'revision.diff'
        headers = [
            ('Content-Type', 'application/octet-stream'),
            ('Content-Disposition', 'attachment; filename=%s'%(filename,)),
            ]
        start_response('200 OK', headers)
        return [content]

