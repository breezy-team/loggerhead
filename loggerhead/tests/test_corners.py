from loggerhead.tests.test_simple import BasicTests

import os
from turbogears import testutil
import cherrypy

class TestCornerCases(BasicTests):

    def test_survive_over_upgrade(self):
        self.createBranch()

        f = open(os.path.join(self.bzrbranch, 'myfilename'), 'w')
        try:
            f.write("foo")
        finally:
            f.close()
        self.tree.add('myfilename')
        msg = 'a very exciting commit message'
        self.tree.commit(message=msg)

        self.setUpLoggerhead()

        testutil.create_request('/project/branch/changes')
        assert msg in cherrypy.response.body[0]

        from bzrlib.upgrade import upgrade
        from bzrlib.bzrdir import format_registry
        upgrade(self.bzrbranch, format_registry.make_bzrdir('dirstate-tags'))

        testutil.create_request('/project/branch/changes')
        assert msg in cherrypy.response.body[0]

    def test_revision_only_changing_execute_bit(self):
        self.createBranch()

        f = open(os.path.join(self.bzrbranch, 'myfilename'), 'w')
        try:
            f.write("foo")
        finally:
            f.close()
        self.tree.add('myfilename')
        msg = 'a very exciting commit message'
        self.tree.commit(message=msg)

        os.chmod(os.path.join(self.bzrbranch, 'myfilename'), 0755)

        newrevid = self.tree.commit(message='make something executable')

        self.setUpLoggerhead()


        testutil.create_request('/project/branch/revision/'+newrevid)
        assert 'executable' in cherrypy.response.body[0]
