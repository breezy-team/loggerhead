#!/usr/bin/python -tt
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


import sys
import os
import pwd
sys.path.insert(0, os.path.dirname(__file__))

from paste.httpexceptions import HTTPExceptionHandler
from loggerhead.apps.transport import BranchesFromTransportRoot
from loggerhead.apps.error import ErrorHandlerApp
from loggerhead.config import LoggerheadConfig
from breezy import config as bzrconfig
from paste.deploy.config import PrefixMiddleware
from breezy.plugin import load_plugins

class NotConfiguredError(Exception):
    pass


load_plugins()
config = LoggerheadConfig()
prefix = config.get_option('user_prefix') or ''
# Note we could use LoggerheadConfig here if it didn't fail when a
# config option is not also a commandline option
root_dir = bzrconfig.GlobalConfig().get_user_option('http_root_dir')
if not root_dir:
    raise NotConfiguredError('You must have a ~/.bazaar/bazaar.conf file for'
            ' %(user)s with http_root_dir set to the base directory you want'
            ' to serve bazaar repositories from' %
            {'user': pwd.getpwuid(os.geteuid()).pw_name})
prefix = prefix.encode('utf-8', 'ignore')
root_dir = root_dir.encode('utf-8', 'ignore')
app = BranchesFromTransportRoot(root_dir, config)
app = PrefixMiddleware(app, prefix=prefix)
app = HTTPExceptionHandler(app)
application = ErrorHandlerApp(app)
