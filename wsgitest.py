from loggerhead.history import History
from loggerhead.wsgiapp import BranchWSGIApp

h = History.from_folder('.')

app = BranchWSGIApp(h)


from paste import httpserver
from paste.evalexception import EvalException
from paste.httpexceptions import make_middleware
from paste.translogger import make_filter

app = app.app
for w in EvalException, make_middleware:
    app = w(app)

app = make_filter(app, None)

httpserver.serve(app, host='127.0.0.1', port='9876')

