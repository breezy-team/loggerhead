#!/usr/bin/env python
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
