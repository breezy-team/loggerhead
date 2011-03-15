# Copyright (C) 2007-2011 Canonical Ltd.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#

import cgi
import logging
import re

from bzrlib.tests import TestCaseWithTransport
try:
    from bzrlib.util.configobj.configobj import ConfigObj
except ImportError:
    from configobj import ConfigObj
from bzrlib import config

from loggerhead.apps.branch import BranchWSGIApp
from paste.fixture import TestApp
from paste.httpexceptions import HTTPExceptionHandler, HTTPMovedPermanently



class BasicTests(TestCaseWithTransport):

    def setUp(self):
        TestCaseWithTransport.setUp(self)
        logging.basicConfig(level=logging.ERROR)
        logging.getLogger('bzr').setLevel(logging.CRITICAL)

    def createBranch(self):
        self.tree = self.make_branch_and_tree('.')

    def setUpLoggerhead(self, **kw):
        branch_app = BranchWSGIApp(self.tree.branch, '', **kw).app
        return TestApp(HTTPExceptionHandler(branch_app))


class TestWithSimpleTree(BasicTests):

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()

        self.filecontents = ('some\nmultiline\ndata\n'
                             'with<htmlspecialchars\n')
        self.build_tree_contents(
            [('myfilename', self.filecontents)])
        self.tree.add('myfilename', 'myfile-id')
        self.fileid = self.tree.path2id('myfilename')
        self.msg = 'a very exciting commit message <'
        self.revid = self.tree.commit(message=self.msg)

    def test_changes(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain(cgi.escape(self.msg))

    def test_changes_for_file(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes?filter_file_id=myfile-id')
        res.mustcontain(cgi.escape(self.msg))

    def test_changes_branch_from(self):
        app = self.setUpLoggerhead(served_url="lp:loggerhead")
        res = app.get('/changes')
        self.failUnless("To get this branch, use:" in res)
        self.failUnless("lp:loggerhead" in res)
        app = self.setUpLoggerhead(served_url=None)
        res = app.get('/changes')
        self.failIf("To get this branch, use:" in res)

    def test_changes_search(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes', params={'q': 'foo'})
        res.mustcontain('Sorry, no results found for your search.')

    def test_annotate(self):
        app = self.setUpLoggerhead()
        res = app.get('/annotate', params={'file_id': self.fileid})
        # If pygments is installed, it inserts <span class="pyg" content into
        # the output, to trigger highlighting. And it specifically highlights
        # the &lt; that we are interested in seeing in the output.
        # Without pygments we have a simple: 'with&lt;htmlspecialchars'
        # With it, we have
        # '<span class='pyg-n'>with</span><span class='pyg-o'>&lt;</span>'
        # '<span class='pyg-n'>htmlspecialchars</span>
        # So we pre-filter the body, to make sure remove spans of that type.
        body_no_span = re.sub(r'<span class="pyg-.">', '', res.body)
        body_no_span = body_no_span.replace('</span>', '')
        for line in self.filecontents.splitlines():
            escaped = cgi.escape(line)
            self.assertTrue(escaped in body_no_span,
                            "did not find %r in %r" % (escaped, body_no_span))

    def test_inventory(self):
        app = self.setUpLoggerhead()
        res = app.get('/files')
        res.mustcontain('myfilename')
        res = app.get('/files/')
        res.mustcontain('myfilename')
        res = app.get('/files/1')
        res.mustcontain('myfilename')
        res = app.get('/files/1/')
        res.mustcontain('myfilename')
        res = app.get('/files/1/?file_id=' + self.tree.path2id(''))
        res.mustcontain('myfilename')

    def test_inventory_bad_rev_404(self):
        app = self.setUpLoggerhead()
        res = app.get('/files/200', status=404)
        res = app.get('/files/invalid-revid', status=404)

    def test_inventory_bad_path_404(self):
        app = self.setUpLoggerhead()
        res = app.get('/files/1/hooha', status=404)
        res = app.get('/files/1?file_id=dssadsada', status=404)

    def test_revision(self):
        app = self.setUpLoggerhead()
        res = app.get('/revision/1')
        res.mustcontain('myfilename')


class TestEmptyBranch(BasicTests):
    """Test that an empty branch doesn't break"""

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()

    def test_changes(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain('No revisions!')

    def test_inventory(self):
        app = self.setUpLoggerhead()
        res = app.get('/files')
        res.mustcontain('No revisions!')


class TestHiddenBranch(BasicTests):
    """
    Test that hidden branches aren't shown
    FIXME: not tested that it doesn't show up on listings
    """

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()
        locations = config.locations_config_filename()
        config.ensure_config_dir_exists()
        open(locations, 'wb').write('[%s]\nhttp_serve = False'
                                    % (self.tree.branch.base,))

    def test_no_access(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes', status=404)


class TestControllerRedirects(BasicTests):
    """
    Test that a file under /files redirects to /view,
    and a directory under /view redirects to /files.
    """

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()
        self.build_tree(('file', 'folder/', 'folder/file'))
        self.tree.smart_add([])
        self.tree.commit('')

    def test_view_folder(self):
        app = TestApp(BranchWSGIApp(self.tree.branch, '').app)

        self.assertRaises(HTTPMovedPermanently, app.get, '/view/head:/folder')

    def test_files_file(self):
        app = TestApp(BranchWSGIApp(self.tree.branch, '').app)

        self.assertRaises(HTTPMovedPermanently, app.get, '/files/head:/folder/file')
        self.assertRaises(HTTPMovedPermanently, app.get, '/files/head:/file')

#class TestGlobalConfig(BasicTests):
#    """
#    Test that global config settings are respected
#    """

#    def setUp(self):
#        BasicTests.setUp(self)
#        self.createBranch()
#        config.GlobalConfig().set_user_option('http_version', 'True')

#    def test_setting_respected(self):
        #FIXME: Figure out how to test this properly
#        app = self.setUpLoggerhead()
#        res = app.get('/changes', status=200)
