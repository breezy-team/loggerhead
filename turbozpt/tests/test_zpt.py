from turbozpt import TurboZpt
from turbogears import controllers
from turbogears import testutil
import turbogears
import cherrypy

RENDERED="<html>\n<head>\n<title>%s</title>\n</head>\n<body>\n<div>Hello, %s</div>\n</body>\n</html>\n"

def test_template_lookup():
    tc = TurboZpt()
    template = tc.load_template("turbozpt.tests.simple")
    assert template
    TITLE="test"
    NAME="World"
    info = dict(title=TITLE, name=NAME)
    t = template(**info)
    assert str(t).startswith(RENDERED % (TITLE, NAME))

class TestRoot(controllers.Root):
    def index(self, name, title="test"):
        return dict(name=name, title=title)
    index = turbogears.expose(html="zpt:turbozpt.tests.simple")(index)

def test_real_life_situation():
    cherrypy.root = TestRoot()
    TITLE="test dave"
    NAME="Dave"
    testutil.createRequest("/?name=%s" % NAME)
    print cherrypy.response.body
    assert cherrypy.response.body[0].startswith(RENDERED % ("test", NAME))
