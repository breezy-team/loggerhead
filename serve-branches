#!/usr/bin/env python
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

"""Search for branches underneath a directory and serve them all."""

import logging
import sys

from paste import httpserver
from paste.httpexceptions import HTTPExceptionHandler
from paste.translogger import TransLogger

from loggerhead.apps.filesystem import BranchesFromFileSystemRoot


logging.basicConfig()
logging.getLogger().setLevel(logging.DEBUG)

if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    path = '.'

app = BranchesFromFileSystemRoot(path)

app = HTTPExceptionHandler(app)
app = TransLogger(app)

try:
    from paste.deploy.config import PrefixMiddleware
except ImportError:
    pass
else:
    app = PrefixMiddleware(app)

#from paste.evalexception import EvalException
#app = EvalException(app)

httpserver.serve(app, host='0.0.0.0', port='8080')
