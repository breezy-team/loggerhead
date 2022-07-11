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

from __future__ import absolute_import

from html import escape
import json
import logging
import re
from io import BytesIO

from breezy.tests import TestCaseWithTransport
from configobj import ConfigObj
from breezy import config

from ..apps.branch import BranchWSGIApp
from ..apps.http_head import HeadMiddleware
from paste.fixture import TestApp
from paste.httpexceptions import HTTPExceptionHandler, HTTPMovedPermanently

from .fixtures import (
    SampleBranch,
    )


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
        json.loads(content.decode('UTF-8'))

    def make_branch_app(self, branch, **kw):
        branch_app = BranchWSGIApp(branch, friendly_name='friendly-name', **kw)
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
        self.sample_branch_fixture = SampleBranch(self)

        # XXX: This could be cleaned up more... -- mbp 2011-11-25
        self.useFixture(self.sample_branch_fixture)
        self.tree = self.sample_branch_fixture.tree
        self.path = self.sample_branch_fixture.path
        self.filecontents = self.sample_branch_fixture.filecontents
        self.msg = self.sample_branch_fixture.msg

    def test_public_private(self):
        app = self.make_branch_app(self.tree.branch, private=True)
        self.assertEqual(app.public_private_css(), 'private')
        app = self.make_branch_app(self.tree.branch)
        self.assertEqual(app.public_private_css(), 'public')

    def test_changes(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        res.mustcontain(escape(self.msg))

    def test_changes_for_file(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes?filter_path=%s' % self.path)
        res.mustcontain(escape(self.msg))

    def test_changes_branch_from(self):
        app = self.setUpLoggerhead(served_url="lp:loggerhead")
        res = app.get('/changes')
        self.failUnless("To get this branch, use:" in res)
        self.failUnless("lp:loggerhead" in res)

    def test_changes_search(self):
        app = self.setUpLoggerhead()
        res = app.get('/changes', params={'q': 'foo'})
        res.mustcontain('Sorry, no results found for your search.')

    def test_annotate(self):
        app = self.setUpLoggerhead()
        res = app.get('/annotate/1/%s' % self.path, params={})
        # If pygments is installed, it inserts <span class="pyg" content into
        # the output, to trigger highlighting. And it specifically highlights
        # the &lt; that we are interested in seeing in the output.
        # Without pygments we have a simple: 'with&lt;htmlspecialchars'
        # With it, we have
        # '<span class='pyg-n'>with</span><span class='pyg-o'>&lt;</span>'
        # '<span class='pyg-n'>htmlspecialchars</span>
        # So we pre-filter the body, to make sure remove spans of that type.
        body_no_span = re.sub(b'<span class="pyg-.">', b'', res.body)
        body_no_span = body_no_span.replace(b'</span>', b'')
        for line in self.filecontents.splitlines():
            escaped = escape(line).encode('utf-8')
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

    def test_inventory_bad_rev_404(self):
        app = self.setUpLoggerhead()
        res = app.get('/files/200', status=404)
        res = app.get('/files/invalid-revid', status=404)

    def test_inventory_bad_path_404(self):
        app = self.setUpLoggerhead()
        res = app.get('/files/1/hooha', status=404)

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
        try:
            locations = config.locations_config_filename()
        except AttributeError:
            from breezy import bedding
            locations = bedding.locations_config_path()
            ensure_config_dir_exists = bedding.ensure_config_dir_exists
        else:
            ensure_config_dir_exists = config.ensure_config_dir_exists
        ensure_config_dir_exists()
        with open(locations, 'w') as f:
            f.write('[%s]\nhttp_serve = False' % (
                self.tree.branch.base,))

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
        self.assertEqualDiff(b'', res.body)


def consume_app(app, env):
    body = BytesIO()
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
