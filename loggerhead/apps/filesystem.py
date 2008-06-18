import cgi, os, tempfile
from bzrlib import branch, errors
from loggerhead.history import History
from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.apps import favicon_app, static_app
from paste.request import path_info_pop
from paste.wsgiwrappers import WSGIRequest, WSGIResponse
from paste import httpexceptions
from loggerhead.changecache import FileChangeCache


sql_dir = tempfile.mkdtemp()

class BranchesFromFileSystemServer(object):
    def __init__(self, folder, root):
        self.folder = folder
        self.root = root

    def directory_listing(self, path, environ, start_response):
        request = WSGIRequest(environ)
        response = WSGIResponse()
        listing = [d for d in os.listdir(path) if not d.startswith('.')]
        response.headers['Content-Type'] = 'text/html'
        print >> response, '<html><body>'
        for d in sorted(listing):
            if os.path.isdir(os.path.join(path, d)):
                d = cgi.escape(d)
                print >> response, '<li><a href="%s/">%s</a></li>' % (d, d)
        print >> response, '</body></html>'
        return response(environ, start_response)

    def app_for_branch(self, b, path):
        b.lock_read()
        try:
            _history = History.from_branch(b)
        finally:
            b.unlock()
        _history.use_file_cache(FileChangeCache(_history, sql_dir))
        if not self.folder:
            name = os.path.basename(os.path.abspath(path))
        else:
            name = self.folder
        h = BranchWSGIApp(_history, name)
        self.root.cache[path] = h
        return h.app

    def __call__(self, environ, start_response):
        path = os.path.join(self.root.folder, self.folder)
        if not os.path.isdir(path):
            raise httpexceptions.HTTPNotFound()
        cached = self.root.cache.get(path)
        if cached and not cached.history.out_of_date():
            return cached.app(environ, start_response)
        try:
            b = branch.Branch.open(path)
        except errors.NotBranchError:
            segment = path_info_pop(environ)
            if segment is None:
                raise httpexceptions.HTTPMovedPermanently(
                    environ['SCRIPT_NAME'] + '/')
            elif segment == '':
                return self.directory_listing(path, environ, start_response)
            else:
                relpath = os.path.join(self.folder, segment)
                return BranchesFromFileSystemServer(relpath, self.root)(
                    environ, start_response)
        else:
            return self.app_for_branch(b, path)(environ, start_response)


class BranchesFromFileSystemRoot(object):
    def __init__(self, folder):
        self.cache = {}
        self.folder = folder
    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        if environ['PATH_INFO'].startswith('/static/'):
            segment = path_info_pop(environ)
            assert segment == 'static'
            return static_app(environ, start_response)
        elif environ['PATH_INFO'] == '/favicon.ico':
            return favicon_app(environ, start_response)
        else:
            return BranchesFromFileSystemServer(
                '', self)(environ, start_response)
