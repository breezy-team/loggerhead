from loggerhead.apps.filesystem import BranchesFromFileSystemRoot
from paste import httpserver
from paste.httpexceptions import make_middleware
from paste.translogger import make_filter

app = BranchesFromFileSystemRoot('.')

app = app
app = make_middleware(app)
app = make_filter(app, None)


httpserver.serve(app, host='127.0.0.1', port='9876')
