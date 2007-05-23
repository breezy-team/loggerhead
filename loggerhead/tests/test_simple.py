from configobj import ConfigObj
import unittest
import os
import tempfile
import shutil

import cherrypy
from turbogears import testutil

import bzrlib

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
        branch_name = 'branch'
        folder = '%s'
"""


class TestWithSimpleTree(object):
    def setUp(self):
        self.old_bzrhome = bzrlib.osutils.set_or_unset_env('BZR_HOME', '')
        self.bzrbranch = tempfile.mkdtemp()
        branch = bzrlib.bzrdir.BzrDir.create_branch_convenience(
            self.bzrbranch, force_new_tree=True)
        tree = branch.bzrdir.open_workingtree()
        f = open(os.path.join(self.bzrbranch, 'file'), 'w')
        try:
            f.write('data')
        finally:
            f.close()
        tree.add('file')
        self.msg = 'a very exciting commit message'
        tree.commit(message=self.msg)

        ini = config_template%self.bzrbranch

        config = ConfigObj(ini.splitlines())
        cherrypy.root = Root(config)

    def tearDown(self):
        shutil.rmtree(self.bzrbranch)
        bzrlib.osutils.set_or_unset_env('BZR_HOME', self.old_bzrhome)

    # there are so i can run it with py.test and take advantage of the
    # error reporting...
    def setup_method(self, meth):
        self.setUp()

    def teardown_method(self, meth):
        self.tearDown()

    def test_index(self):
        testutil.create_request('/')
        link = '<a href="/project/branch">branch</a>'
        assert link in cherrypy.response.body[0]

    def test_changes(self):
        testutil.create_request('/project/branch/changes')
        assert self.msg in cherrypy.response.body[0]
