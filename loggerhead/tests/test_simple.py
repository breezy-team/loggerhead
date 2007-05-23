from configobj import ConfigObj
import unittest
import os
import tempfile
import shutil

import cherrypy
from turbogears import testutil

from bzrlib.bzrdir import BzrDir

from loggerhead.controllers import Root

def test_simple():
    config = ConfigObj()
    r = Root(config)
    cherrypy.root = r
    testutil.create_request('/')
    assert 'loggerhead branches' in cherrypy.response.body[0]

config_template = """
[project]
    [[branch]]
        folder = '%s'
"""


class TestWithSimpleTree(object):
    def setUp(self):
        self.old_bzrhome = os.environ.get('BZR_HOME')
        os.environ['BZR_HOME'] = ''
        self.bzrbranch = tempfile.mkdtemp()
        branch = BzrDir.create_branch_convenience(
            self.bzrbranch, force_new_tree=True)
        tree = branch.bzrdir.open_workingtree()
        f = open(os.path.join(self.bzrbranch, 'file'), 'w')
        f.write('data')
        f.close()
        tree.add('file')
        tree.commit(message='.')

        config = ConfigObj(config_template%self.bzrbranch)
        cherrypy.root = Root(config)

    def tearDown(self):
        shutil.rmtree(self.bzrbranch)
        if self.old_bzrhome is None:
            del os.environ['BZR_HOME']
        else:
            os.environ['BZR_HOME'] = self.old_bzrhome

    def test_index(self):
        testutil.create_request('/')
        assert 'loggerhead branches' in cherrypy.response.body[0]
