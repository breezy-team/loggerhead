import os
from bzrlib import branch, errors
from loggerhead.history import History
from loggerhead.wsgiapp import BranchWSGIApp, static_app
from paste.request import path_info_pop
from paste import httpexceptions
from paste import httpserver
from paste.httpexceptions import make_middleware
from paste.translogger import make_filter
from loggerhead.changecache import FileChangeCache



class BranchesFromFileSystemServer(object):
    def __init__(self, folder, root):
        self.folder = folder
        self.root = root

    def __call__(self, environ, start_response):
        segment = path_info_pop(environ)
        if segment is None:
            raise httpexceptions.HTTPNotFound()
        relpath = os.path.join(self.folder, segment)
        f = os.path.join(self.root.folder, relpath)
        if not os.path.isdir(f):
            raise httpexceptions.HTTPNotFound()
        if f in self.root.cache:
            return self.root.cache[f](environ, start_response)
        try:
            b = branch.Branch.open(f)
        except errors.NotBranchError:
            return BranchesFromFileSystemServer(relpath, self.root)(environ, start_response)
        else:
            b.lock_read()
            try:
                _history = History.from_branch(b)
                _history.use_file_cache(FileChangeCache(_history, 'sql'))
                h = BranchWSGIApp(_history, relpath).app
                self.root.cache[f] = h
                return h(environ, start_response)
            finally:
                b.unlock()

class BranchesFromFileSystemRoot(object):
    def __init__(self, folder):
        self.cache = {}
        self.folder = folder
    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        segment = path_info_pop(environ)
        if segment == 'static':
            return static_app(environ, start_response)
        else:
            return BranchesFromFileSystemServer(
                segment, self)(environ, start_response)

app = BranchesFromFileSystemRoot('../..')

app = app
app = make_middleware(app)
app = make_filter(app, None)

from paste.evalexception.middleware import EvalException

httpserver.serve(EvalException(app), host='127.0.0.1', port='9876')

