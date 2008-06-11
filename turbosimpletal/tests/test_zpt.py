from turbosimpletal import TurboZpt
from turbogears import controllers, expose, testutil
import cherrypy

RENDERED = u"<html>\n<head>\n<title>%s</title>\n</head>\n<body>\n<div>Hello, %s</div>\n</body>\n</html>"

def test_template_lookup():
    tc = TurboZpt()
    template = tc.load_template("turbosimpletal.tests.simple")
    assert template
    TITLE="test"
    NAME="World"
    info = dict(title=TITLE, name=NAME)
    s = template.expand(**info)
    assert s.startswith(RENDERED % (TITLE, NAME))

class TestRoot(controllers.Root):
    @expose(html="zpt:turbosimpletal.tests.simple")
    def index(self, name, title="test"):
        return dict(name=name, title=title)

def test_real_life_situation():
    cherrypy.root = TestRoot()
    NAME="Dave"
    testutil.createRequest("/?name=%s" % NAME)
    assert cherrypy.response.body[0].startswith(RENDERED % ("test", NAME))
