# Copyright (C) 2007, 2008, 2009, 2011 Canonical Ltd.
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
import simplejson
from cStringIO import StringIO

from bzrlib.tests import TestCaseWithTransport
try:
    from bzrlib.util.configobj.configobj import ConfigObj
except ImportError:
    from configobj import ConfigObj
from bzrlib import config

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.apps.http_head import HeadMiddleware
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

    def assertOkJsonResponse(self, app, env):
        start, content = consume_app(app, env)
        self.assertEqual('200 OK', start[0])
        self.assertEqual('application/json', dict(start[1])['Content-Type'])
        self.assertEqual(None, start[2])
        simplejson.loads(content)

    def make_branch_app(self, branch):
        branch_app = BranchWSGIApp(branch, friendly_name='friendly-name')
        branch_app._environ = {
            'wsgi.url_scheme':'',
            'SERVER_NAME':'',
            'SERVER_PORT':'80',
            }
        branch_app._url_base = ''
        return branch_app


class TestWithSimpleTree(BasicTests):

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()

        self.filecontents = ('some\nmultiline\ndata\n'
                             'with<htmlspecialchars\n')
        filenames = ['myfilename', 'anotherfile<']
        self.build_tree_contents(
            (filename, self.filecontents) for filename in filenames)
        for filename in filenames:
            self.tree.add(filename, '%s-id' % filename)
        self.fileid = self.tree.path2id('myfilename')
        self.msg = 'a very exciting commit message <'
        self.revid = self.tree.commit(message=self.msg)

    def test_changes(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain(cgi.escape(self.msg))

    def test_changes_for_file(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes?filter_file_id=myfilename-id')
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
        res.mustcontain(no=['anotherfile<'])
        res.mustcontain('anotherfile&lt;')
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

        e = self.assertRaises(HTTPMovedPermanently, app.get, '/view/head:/folder')
        self.assertEqual(e.location(), '/files/head:/folder')

    def test_files_file(self):
        app = TestApp(BranchWSGIApp(self.tree.branch, '').app)

        e = self.assertRaises(HTTPMovedPermanently, app.get, '/files/head:/folder/file')
        self.assertEqual(e.location(), '/view/head:/folder/file')
        e = self.assertRaises(HTTPMovedPermanently, app.get, '/files/head:/file')
        self.assertEqual(e.location(), '/view/head:/file')


class TestHeadMiddleware(BasicTests):

    def setUp(self):
        BasicTests.setUp(self)
        self.createBranch()
        self.msg = 'trivial commit message'
        self.revid = self.tree.commit(message=self.msg)

    def setUpLoggerhead(self, **kw):
        branch_app = BranchWSGIApp(self.tree.branch, '', **kw).app
        return TestApp(HTTPExceptionHandler(HeadMiddleware(branch_app)))

    def test_get(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain(self.msg)
        self.assertEqual('text/html', res.header('Content-Type'))

    def test_head(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes', extra_environ={'REQUEST_METHOD': 'HEAD'})
        self.assertEqual('text/html', res.header('Content-Type'))
        self.assertEqualDiff('', res.body)


def consume_app(app, env):
    body = StringIO()
    start = []
    def start_response(status, headers, exc_info=None):
        start.append((status, headers, exc_info))
        return body.write
    extra_content = list(app(env, start_response))
    body.writelines(extra_content)
    return start[0], body.getvalue()



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
