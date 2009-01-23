# Copyright 2009 Canonical Ltd

# This file allows loggerhead to be treated as a plugin for bzr.
#
# XXX: Because loggerhead already contains a loggerhead directory, much of the code
# is going to live in bzrlib.plugins.loggerhead.loggerhead.  But moving it can
# wait. -- mbp 20090123

"""Loggerhead web viewer for Bazaar branches."""

import bzrlib
from bzrlib.api import require_api

require_api(bzrlib, (1, 11, 0))
