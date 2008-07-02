import cgi
import unittest
import os
import tempfile
import shutil
import logging

import bzrlib.bzrdir
import bzrlib.osutils
from configobj import ConfigObj

from loggerhead.history import History
from loggerhead.apps.branch import BranchWSGIApp
from paste.fixture import TestApp


def test_config_root():
    from loggerhead.apps.config import Root
    config = ConfigObj()
    app = TestApp(Root(config))
    res = app.get('/')
    res.mustcontain('loggerhead branches')


class BasicTests(object):

    # setup_method and teardown_method are so i can run the tests with
    # py.test and take advantage of the error reporting.
    def setup_method(self, meth):
        self.setUp()

    def teardown_method(self, meth):
        self.tearDown()

    def setUp(self):
        logging.basicConfig(level=logging.DEBUG)
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
        app = TestApp(BranchWSGIApp(self.branch).app)
        return app

    def tearDown(self):
        if self.bzrbranch is not None:
            shutil.rmtree(self.bzrbranch)
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


    def test_changes(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain(cgi.escape(self.msg))

    def test_changes_search(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes', params={'q': 'foo'})
        res.mustcontain('Sorry, no results found for your search.')

    def test_annotate(self):
        app = self.setUpLoggerhead()
        res = app.get('/annotate', params={'file_id':self.fileid})
        for line in self.filecontents.splitlines():
            res.mustcontain(cgi.escape(line))

    def test_inventory(self):
        app = self.setUpLoggerhead()
        res = app.get('/files')
        res.mustcontain('myfilename')

    def test_revision(self):
        app = self.setUpLoggerhead()
        res = app.get('/revision/1')
        res.mustcontain('myfilename')


class TestEmptyBranch(BasicTests):

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()

    def test_changes(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain('No revisions!')

