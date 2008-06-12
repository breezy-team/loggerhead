from loggerhead.history import History
from loggerhead.wsgiapp import BranchWSGIApp

h = History.from_folder('.')

app = BranchWSGIApp(h)


from paste import httpserver
from paste.evalexception import EvalException
from paste.httpexceptions import make_middleware
httpserver.serve(EvalException(make_middleware(app.app)), host='127.0.0.1', port='9876')

