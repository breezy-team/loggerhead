from turbosimpletal import TurboZpt
from turbogears import controllers
from turbogears import testutil
import turbogears
import cherrypy

RENDERED="<?xml version=\"1.0\" encoding=\"iso-8859-1\"?>\n<html>\n<head>\n<title>%s</title>\n</head>\n<body>\n<div>Hello, %s</div>\n</body>\n</html>"

def test_template_lookup():
    tc = TurboZpt()
    template = tc.load_template("turbosimpletal.tests.simple")
    assert template
    TITLE="test"
    NAME="World"
    info = dict(title=TITLE, name=NAME)
    s = template(**info)
    assert s.startswith(RENDERED % (TITLE, NAME))

class TestRoot(controllers.Root):
    def index(self, name, title="test"):
        return dict(name=name, title=title)
    index = turbogears.expose(html="zpt:turbosimpletal.tests.simple")(index)

def test_real_life_situation():
    cherrypy.root = TestRoot()
    TITLE="test dave"
    NAME="Dave"
    testutil.createRequest("/?name=%s" % NAME)
    print cherrypy.response.body
    assert cherrypy.response.body[0].startswith(RENDERED % ("test", NAME))
