#!/usr/bin/python -tt

import sys
import os
import pwd
sys.path.insert(0, os.path.dirname(__file__))

from paste.httpexceptions import HTTPExceptionHandler
from loggerhead.apps.transport import BranchesFromTransportRoot
from loggerhead.apps.error import ErrorHandlerApp
from loggerhead.config import LoggerheadConfig
from bzrlib import config as bzrconfig
from paste.deploy.config import PrefixMiddleware
from bzrlib.plugin import load_plugins

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
