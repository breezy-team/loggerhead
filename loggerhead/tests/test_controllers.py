# Copyright (C) 2008-2011 Canonical Ltd.
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

from __future__ import absolute_import

import json
import tarfile
import tempfile

from paste.fixture import (
    AppError,
    )
from paste.httpexceptions import HTTPNotFound

from testtools.matchers import (
    Matcher,
    Mismatch,
    )

from ..apps.branch import BranchWSGIApp
from ..controllers.annotate_ui import AnnotateUI
from .test_simple import (
    BasicTests,
    consume_app,
    TestWithSimpleTree,
    )


class TestInventoryUI(BasicTests):

    def make_bzrbranch_for_tree_shape(self, shape):
        tree = self.make_branch_and_tree('.')
        self.build_tree(shape)
        tree.smart_add([])
        tree.commit('')
        self.addCleanup(tree.branch.lock_read().unlock)
        return tree.branch

    def make_bzrbranch_and_inventory_ui_for_tree_shape(self, shape, env):
        branch = self.make_bzrbranch_for_tree_shape(shape)
        branch_app = self.make_branch_app(branch)
        return branch, branch_app.lookup_app(env)

    def test_get_filelist(self):
        env = {
            'SCRIPT_NAME': '',
            'PATH_INFO': '/files',
            'wsgi.url_scheme': 'http',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            }
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'], env)
        revtree = bzrbranch.repository.revision_tree(bzrbranch.last_revision())
        self.assertEqual(1, len(inv_ui.get_filelist(revtree, '', 'filename', 'head')))

    def test_smoke(self):
        env = {
            'SCRIPT_NAME': '',
            'PATH_INFO': '/files',
            'wsgi.url_scheme': 'http',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            }
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'], env)
        start, content = consume_app(inv_ui, env)
        self.assertEqual(('200 OK', [('Content-Type', 'text/html')], None),
                         start)
        self.assertContainsRe(content, b'filename')

    def test_no_content_for_HEAD(self):
        env = {
            'SCRIPT_NAME': '',
            'PATH_INFO': '/files',
            'REQUEST_METHOD': 'HEAD',
            'wsgi.url_scheme': 'http',
            'SERVER_NAME': 'localhost',
            'SERVER_PORT': '80',
            }
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'], env)
        start, content = consume_app(inv_ui, env)
        self.assertEqual(('200 OK', [('Content-Type', 'text/html')], None),
                         start)
        self.assertEqual(b'', content)

    def test_get_values_smoke(self):
        branch = self.make_bzrbranch_for_tree_shape(['a-file'])
        branch_app = self.make_branch_app(branch)
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/files',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        inv_ui = branch_app.lookup_app(env)
        inv_ui.parse_args(env)
        values = inv_ui.get_values('', {}, {})
        self.assertEqual('a-file', values['filelist'][0].filename)

    def test_json_render_smoke(self):
        branch = self.make_bzrbranch_for_tree_shape(['a-file'])
        branch_app = self.make_branch_app(branch)
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/+json/files',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        inv_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(inv_ui, env)


class TestRevisionUI(BasicTests):

    def make_branch_app_for_revision_ui(self, shape1, shape2):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents(shape1)
        tree.smart_add([])
        tree.commit('msg 1', rev_id=b'rev-1')
        self.build_tree_contents(shape2)
        tree.smart_add([])
        tree.commit('msg 2', rev_id=b'rev-2')
        branch = tree.branch
        self.addCleanup(branch.lock_read().unlock)
        return self.make_branch_app(branch)

    def test_get_values(self):
        branch_app = self.make_branch_app_for_revision_ui([], [])
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/revision/2',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        rev_ui = branch_app.lookup_app(env)
        rev_ui.parse_args(env)
        self.assertIsInstance(rev_ui.get_values('', {}, []), dict)

    def test_add_template_values(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', b'content\n')], [('file', b'new content\n')])
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/revision/1/non-existent-file',
               'QUERY_STRING':'start_revid=1',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        revision_ui = branch_app.lookup_app(env)
        path = revision_ui.parse_args(env)
        values = revision_ui.get_values(path, revision_ui.kwargs, {})
        revision_ui.add_template_values(values)
        self.assertIs(values['diff_chunks'], None)

    def test_add_template_values_with_changes(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', b'content\n')], [('file', b'new content\n')])
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/revision/1/file',
               'QUERY_STRING':'start_revid=1',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        revision_ui = branch_app.lookup_app(env)
        path = revision_ui.parse_args(env)
        values = revision_ui.get_values(path, revision_ui.kwargs, {})
        revision_ui.add_template_values(values)
        self.assertEqual(len(values['diff_chunks']), 1)

    def test_add_template_values_with_non_ascii(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [(u'skr\xe1', b'content\n')], [(u'skr\xe1', b'new content\n')])
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/revision/1',
               'QUERY_STRING': 'start_revid=1',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        revision_ui = branch_app.lookup_app(env)
        path = revision_ui.parse_args(env)
        values = revision_ui.get_values(path, revision_ui.kwargs, {})
        revision_ui.add_template_values(values)
        self.assertEqual(
            json.loads(values['link_data']),
            {'diff-0': 'rev-1/null%253A/%252F',
             'diff-1': 'rev-1/null%253A/skr%25C3%25A1'})
        self.assertEqual(
            json.loads(values['path_to_id']),
            {'/': 'diff-0', u'skr\xe1': 'diff-1'})

    def test_get_values_smoke(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', b'content\n'), ('other-file', b'other\n')],
                [('file', b'new content\n')])
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/revision/head:',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        revision_ui = branch_app.lookup_app(env)
        revision_ui.parse_args(env)
        values = revision_ui.get_values('', {}, {})

        self.assertEqual(values['revid'], 'rev-2')
        self.assertEqual(values['change'].comment, 'msg 2')
        self.assertEqual(values['file_changes'].modified[0].filename, 'file')
        self.assertEqual(values['merged_in'], None)

    def test_json_render_smoke(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', b'content\n'), ('other-file', b'other\n')],
                [('file', b'new content\n')])
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/+json/revision/head:',
                'REQUEST_METHOD': 'GET',
                'wsgi.url_scheme': 'http',
                'SERVER_NAME': 'localhost',
                'SERVER_PORT': '80'}
        revision_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(revision_ui, env)


class TestAnnotateUI(BasicTests):

    def make_annotate_ui_for_file_history(self, filename, rev_ids_texts):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents([(filename, '')])
        tree.add([filename])
        for rev_id, text, message in rev_ids_texts:
            self.build_tree_contents([(filename, text)])
            tree.commit(rev_id=rev_id, message=message)
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = BranchWSGIApp(tree.branch, friendly_name='test_name')
        return AnnotateUI(branch_app, branch_app.get_history)

    def test_annotate_file(self):
        history = [(b'rev1', b'old\nold\n', '.'), (b'rev2', b'new\nold\n', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('filename', history)
        # A lot of this state is set up by __call__, but we'll do it directly
        # here.
        ann_ui.args = ['rev2']
        annotate_info = ann_ui.get_values(u'filename', kwargs={}, headers={})
        annotated = annotate_info['annotated']
        self.assertEqual(2, len(annotated))
        self.assertEqual('2', annotated[1].change.revno)
        self.assertEqual('1', annotated[2].change.revno)

    def test_annotate_empty_comment(self):
        # Testing empty comment handling without breaking
        history = [(b'rev1', b'old\nold\n', '.'), (b'rev2', b'new\nold\n', '')]
        ann_ui = self.make_annotate_ui_for_file_history('filename', history)
        ann_ui.args = ['rev2']
        ann_ui.get_values(u'filename', kwargs={}, headers={})

    def test_annotate_file_zero_sized(self):
        # Test against a zero-sized file without breaking. No annotation
        # must be present.
        history = [(b'rev1', b'', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('filename', history)
        ann_ui.args = ['rev1']
        annotate_info = ann_ui.get_values(u'filename', kwargs={}, headers={})
        annotated = annotate_info['annotated']
        self.assertEqual(0, len(annotated))

    def test_annotate_nonexistent_file(self):
        history = [(b'rev1', b'', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('filename', history)
        ann_ui.args = ['rev1']
        self.assertRaises(
            HTTPNotFound, ann_ui.get_values, u'not-filename', {}, {})

    def test_annotate_nonexistent_rev(self):
        history = [(b'rev1', b'', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('filename', history)
        ann_ui.args = ['norev']
        self.assertRaises(
            HTTPNotFound, ann_ui.get_values, u'not-filename', {}, {})


class TestFileDiffUI(BasicTests):

    def make_branch_app_for_filediff_ui(self):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        rev1 = builder.build_snapshot(None, [
            ('add', ('', None, 'directory', '')),
            ('add', ('filename', None, 'file', b'content\n'))],
            message="First commit.")
        rev2 = builder.build_snapshot(None, [
             ('modify', ('filename', b'new content\n'))])
        builder.finish_series()
        branch = builder.get_branch()
        self.addCleanup(branch.lock_read().unlock)
        return self.make_branch_app(branch), (rev1, rev2)

    def test_get_values_smoke(self):
        branch_app, (rev1, rev2) = self.make_branch_app_for_filediff_ui()
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/+filediff/%s/%s/filename' % (rev2.decode('utf-8'), rev1.decode('utf-8')),
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        filediff_ui = branch_app.lookup_app(env)
        filediff_ui.parse_args(env)
        values = filediff_ui.get_values('', {}, {})
        chunks = values['chunks']
        self.assertEqual('insert', chunks[0].diff[1].type)
        self.assertEqual('new content', chunks[0].diff[1].line)

    def test_json_render_smoke(self):
        branch_app, (rev1, rev2) = self.make_branch_app_for_filediff_ui()
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/+json/+filediff/%s/%s/filename' % (rev2.decode('utf-8'), rev1.decode('utf-8')),
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        filediff_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(filediff_ui, env)


class TestRevLogUI(BasicTests):

    def make_branch_app_for_revlog_ui(self):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        revid = builder.build_snapshot(None, [
            ('add', ('', None, 'directory', '')),
            ('add', ('filename', None, 'file', b'content\n'))],
            message="First commit.")
        builder.finish_series()
        branch = builder.get_branch()
        self.addCleanup(branch.lock_read().unlock)
        return self.make_branch_app(branch), revid

    def test_get_values_smoke(self):
        branch_app, revid = self.make_branch_app_for_revlog_ui()
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/+revlog/%s' % revid.decode('utf-8'),
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        revlog_ui = branch_app.lookup_app(env)
        revlog_ui.parse_args(env)
        values = revlog_ui.get_values('', {}, {})
        self.assertEqual(values['file_changes'].added[1].filename, 'filename')
        self.assertEqual(values['entry'].comment, "First commit.")

    def test_json_render_smoke(self):
        branch_app, revid = self.make_branch_app_for_revlog_ui()
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/+json/+revlog/%s' % revid.decode('utf-8'),
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        revlog_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(revlog_ui, env)


class TestControllerHooks(BasicTests):

    def test_dummy_hook(self):
        return
        # A hook that returns None doesn't influence the searching for
        # a controller.
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/custom',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        myhook = lambda app, environ: None
        branch = self.make_branch('.')
        self.addCleanup(branch.lock_read().unlock)
        app = self.make_branch_app(branch)
        self.addCleanup(BranchWSGIApp.hooks.uninstall_named_hook, 'controller',
            'captain hook')
        BranchWSGIApp.hooks.install_named_hook('controller', myhook, "captain hook")
        self.assertRaises(KeyError, app.lookup_app, env)

    def test_working_hook(self):
        # A hook can provide an app to use for a particular request.
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/custom',
               'REQUEST_METHOD': 'GET',
               'wsgi.url_scheme': 'http',
               'SERVER_NAME': 'localhost',
               'SERVER_PORT': '80'}
        myhook = lambda app, environ: "I am hooked"
        branch = self.make_branch('.')
        self.addCleanup(branch.lock_read().unlock)
        app = self.make_branch_app(branch)
        self.addCleanup(BranchWSGIApp.hooks.uninstall_named_hook, 'controller',
            'captain hook')
        BranchWSGIApp.hooks.install_named_hook('controller', myhook, "captain hook")
        self.assertEquals("I am hooked", app.lookup_app(env))


class MatchesDownloadHeaders(Matcher):

    def __init__(self, expect_filename, expect_mimetype):
        self.expect_filename = expect_filename
        self.expect_mimetype = expect_mimetype

    def match(self, response):
        # Maybe the c-t should be more specific, but this is probably good for
        # making sure it gets saved without the client trying to decompress it
        # or anything.
        if (response.header('Content-Type') == self.expect_mimetype
            and response.header('Content-Disposition') ==
            "attachment; filename*=utf-8''" + self.expect_filename):
            pass
        else:
            return Mismatch("wrong response headers: %r"
                % response.headers)

    def __str__(self):
        return 'MatchesDownloadHeaders(%r, %r)' % (
            self.expect_filename, self.expect_mimetype)


class TestDownloadUI(TestWithSimpleTree):

    def test_download(self):
        app = self.setUpLoggerhead()
        response = app.get('/download/1/myfilename')
        self.assertEqual(
            b'some\nmultiline\ndata\nwith<htmlspecialchars\n', response.body)
        self.assertThat(
            response,
            MatchesDownloadHeaders('myfilename', 'application/octet-stream'))

    def test_download_bad_revision(self):
        app = self.setUpLoggerhead()
        e = self.assertRaises(
            AppError,
            app.get, '/download/norev/myfilename')
        self.assertContainsRe(str(e), '404 Not Found')

    def test_download_bad_filename(self):
        app = self.setUpLoggerhead()
        e = self.assertRaises(
            AppError,
            app.get, '/download/1/notmyfilename')
        self.assertContainsRe(str(e), '404 Not Found')

    def test_download_from_subdirectory(self):
        app = self.setUpLoggerhead()
        response = app.get('/download/1/folder/myfilename')
        self.assertEqual(
            b'some\nmultiline\ndata\nwith<htmlspecialchars\n', response.body)
        self.assertThat(
            response,
            MatchesDownloadHeaders('myfilename', 'application/octet-stream'))


class IsTarfile(Matcher):

    def __init__(self, compression):
        self.compression = compression

    def match(self, content_bytes):
        f = tempfile.NamedTemporaryFile()
        try:
            f.write(content_bytes)
            f.flush()
            tarfile.open(f.name, mode='r|' + self.compression)
        finally:
            f.close()


class TestDownloadTarballUI(TestWithSimpleTree):

    def test_download_tarball(self):
        # Tarball downloads are enabled by default.
        app = self.setUpLoggerhead()
        response = app.get('/tarball')
        self.assertThat(
            response.body,
            IsTarfile('gz'))
        self.assertThat(
            response,
            MatchesDownloadHeaders('branch.tgz', 'application/octet-stream'))

    def test_download_tarball_of_version(self):
        app = self.setUpLoggerhead()
        response = app.get('/tarball/1')
        self.assertThat(
            response.body,
            IsTarfile('gz'))
        self.assertThat(
            response,
            MatchesDownloadHeaders(
                'branch-r1.tgz', 'application/octet-stream'))

    def test_download_tarball_forbidden(self):
        app = self.setUpLoggerhead(export_tarballs=False)
        e = self.assertRaises(
            AppError,
            app.get,
            '/tarball')
        self.assertContainsRe(
            str(e),
            '(?s).*403 Forbidden'
            '.*Tarball downloads are not allowed')
