from configobj import ConfigObj
import cgi
import unittest
import os
import tempfile
import shutil
import logging

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


class BasicTests(object):


    # there are so i can run it with py.test and take advantage of the
    # error reporting...
    def setup_method(self, meth):
        self.setUp()

    def teardown_method(self, meth):
        self.tearDown()

    def setUp(self):
        #logging.basicConfig(level=logging.DEBUG)
        self.bzrbranch = None
        self.old_bzrhome = None

    def createBranch(self):
        self.old_bzrhome = bzrlib.osutils.set_or_unset_env('BZR_HOME', '')
        self.bzrbranch = tempfile.mkdtemp()
        self.branch = bzrlib.bzrdir.BzrDir.create_branch_convenience(
            self.bzrbranch, force_new_tree=True)
        self.tree = self.branch.bzrdir.open_workingtree()

    config_template = """
    [project]
        [[branch]]
            branch_name = 'branch'
            folder = '%(branch)s'
    """

    def setUpLoggerhead(self):
        ini = self.config_template%dict(branch=self.bzrbranch)

        config = ConfigObj(ini.splitlines())
        cherrypy.root = Root(config)

    def tearDown(self):
        #if self.bzrbranch is not None:
        #    shutil.rmtree(self.bzrbranch)
        bzrlib.osutils.set_or_unset_env('BZR_HOME', self.old_bzrhome)

class TestWithSimpleTree(BasicTests):

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()

        f = open(os.path.join(self.bzrbranch, 'myfilename'), 'w')
        self.filecontents = ('some\nmultiline\ndata\n'
                             'with<htmlspecialchars\n')
        try:
            f.write(self.filecontents)
        finally:
            f.close()
        self.tree.add('myfilename')
        self.fileid = self.tree.path2id('myfilename')
        self.msg = 'a very exciting commit message <'
        self.revid = self.tree.commit(message=self.msg)

        self.setUpLoggerhead()

    def test_index(self):
        testutil.create_request('/')
        link = '<a href="/project/branch">branch</a>'
        assert link in cherrypy.response.body[0]

    def test_changes(self):
        testutil.create_request('/project/branch/changes')
        assert cgi.escape(self.msg) in cherrypy.response.body[0]

    def test_changes_search(self):
        testutil.create_request('/project/branch/changes?q=foo')
        assert 'Sorry, no results found for your search.' in cherrypy.response.body[0]

    def test_annotate(self):
        testutil.create_request('/project/branch/annotate?'
                                + 'file_id='+self.fileid)
        for line in self.filecontents.splitlines():
            assert cgi.escape(line) in cherrypy.response.body[0]

    def test_inventory(self):
        testutil.create_request('/project/branch/files')
        assert 'myfilename' in cherrypy.response.body[0]

    def test_revision(self):
        testutil.create_request('/project/branch/revision/' + self.revid)
        assert 'myfilename' in cherrypy.response.body[0]

class TestWithSimpleTreeAndCache(TestWithSimpleTree):
    config_template = """
    testing = True
    [project]
        [[branch]]
            branch_name = 'branch'
            folder = '%(branch)s'
            cachepath = '%(branch)s/cache'
    """

class TestEmptyBranch(BasicTests):

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()
        self.setUpLoggerhead()

    def test_index(self):
        testutil.create_request('/')
        link = '<a href="/project/branch">branch</a>'
        assert link in cherrypy.response.body[0]

    def test_changes(self):
        testutil.create_request('/project/branch/changes')
        assert 'No revisions!' in cherrypy.response.body[0]

class TestEmptyBranchWithCache(TestEmptyBranch):
    config_template = """
    testing = True
    [project]
        [[branch]]
            branch_name = 'branch'
            folder = '%(branch)s'
            cachepath = '%(branch)s/cache'
    """

