from configobj import ConfigObj

import cherrypy
from turbogears import testutil

from loggerhead.controllers import Root

def test_simple():
    config = ConfigObj()
    r = Root(config)
    cherrypy.root = r
    testutil.create_request('/')
    assert 'loggerhead branches' in cherrypy.response.body[0]
