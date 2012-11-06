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

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.tests.test_simple import (
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

    def make_bzrbranch_and_inventory_ui_for_tree_shape(self, shape):
        branch = self.make_bzrbranch_for_tree_shape(shape)
        branch_app = self.make_branch_app(branch)
        return branch, InventoryUI(branch_app, branch_app.get_history)

    def test_get_filelist(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        inv = bzrbranch.repository.get_inventory(bzrbranch.last_revision())
        self.assertEqual(1, len(inv_ui.get_filelist(inv, '', 'filename', 'head')))

    def test_smoke(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        start, content = consume_app(inv_ui,
            {'SCRIPT_NAME': '/files', 'PATH_INFO': ''})
        self.assertEqual(('200 OK', [('Content-Type', 'text/html')], None),
                         start)
        self.assertContainsRe(content, 'filename')

    def test_no_content_for_HEAD(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        start, content = consume_app(inv_ui,
            {'SCRIPT_NAME': '/files', 'PATH_INFO': '',
             'REQUEST_METHOD': 'HEAD'})
        self.assertEqual(('200 OK', [('Content-Type', 'text/html')], None),
                         start)
        self.assertEqual('', content)

    def test_get_values_smoke(self):
        branch = self.make_bzrbranch_for_tree_shape(['a-file'])
        branch_app = self.make_branch_app(branch)
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/files'}
        inv_ui = branch_app.lookup_app(env)
        inv_ui.parse_args(env)
        values = inv_ui.get_values('', {}, {})
        self.assertEqual('a-file', values['filelist'][0].filename)

    def test_json_render_smoke(self):
        branch = self.make_bzrbranch_for_tree_shape(['a-file'])
        branch_app = self.make_branch_app(branch)
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/+json/files'}
        inv_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(inv_ui, env)


class TestRevisionUI(BasicTests):

    def make_branch_app_for_revision_ui(self, shape1, shape2):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents(shape1)
        tree.smart_add([])
        tree.commit('msg 1', rev_id='rev-1')
        self.build_tree_contents(shape2)
        tree.smart_add([])
        tree.commit('msg 2', rev_id='rev-2')
        branch = tree.branch
        self.addCleanup(branch.lock_read().unlock)
        return self.make_branch_app(branch)

    def test_get_values(self):
        branch_app = self.make_branch_app_for_revision_ui([], [])
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/revision/2'}
        rev_ui = branch_app.lookup_app(env)
        rev_ui.parse_args(env)
        self.assertIsInstance(rev_ui.get_values('', {}, []), dict)

    def test_add_template_values(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', 'content\n')], [('file', 'new content\n')])
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/revision/1/non-existent-file',
               'QUERY_STRING':'start_revid=1' }
        revision_ui = branch_app.lookup_app(env)
        path = revision_ui.parse_args(env)
        values = revision_ui.get_values(path, revision_ui.kwargs, {})
        revision_ui.add_template_values(values)
        self.assertIs(values['diff_chunks'], None)

    def test_get_values_smoke(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', 'content\n'), ('other-file', 'other\n')],
                [('file', 'new content\n')])
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/revision/head:'}
        revision_ui = branch_app.lookup_app(env)
        revision_ui.parse_args(env)
        values = revision_ui.get_values('', {}, {})

        self.assertEqual(values['revid'], 'rev-2')
        self.assertEqual(values['change'].comment, 'msg 2')
        self.assertEqual(values['file_changes'].modified[0].filename, 'file')
        self.assertEqual(values['merged_in'], None)

    def test_json_render_smoke(self):
        branch_app = self.make_branch_app_for_revision_ui(
                [('file', 'content\n'), ('other-file', 'other\n')],
                [('file', 'new content\n')])
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/+json/revision/head:'}
        revision_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(revision_ui, env)


class TestAnnotateUI(BasicTests):

    def make_annotate_ui_for_file_history(self, file_id, rev_ids_texts):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents([('filename', '')])
        tree.add(['filename'], [file_id])
        for rev_id, text, message in rev_ids_texts:
            self.build_tree_contents([('filename', text)])
            tree.commit(rev_id=rev_id, message=message)
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = BranchWSGIApp(tree.branch, friendly_name='test_name')
        return AnnotateUI(branch_app, branch_app.get_history)

    def test_annotate_file(self):
        history = [('rev1', 'old\nold\n', '.'), ('rev2', 'new\nold\n', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('file_id', history)
        # A lot of this state is set up by __call__, but we'll do it directly
        # here.
        ann_ui.args = ['rev2']
        annotate_info = ann_ui.get_values('filename',
            kwargs={'file_id': 'file_id'}, headers={})
        annotated = annotate_info['annotated']
        self.assertEqual(2, len(annotated))
        self.assertEqual('2', annotated[1].change.revno)
        self.assertEqual('1', annotated[2].change.revno)

    def test_annotate_empty_comment(self):
        # Testing empty comment handling without breaking
        history = [('rev1', 'old\nold\n', '.'), ('rev2', 'new\nold\n', '')]
        ann_ui = self.make_annotate_ui_for_file_history('file_id', history)
        ann_ui.args = ['rev2']
        ann_ui.get_values(
            'filename', kwargs={'file_id': 'file_id'}, headers={})

    def test_annotate_file_zero_sized(self):
        # Test against a zero-sized file without breaking. No annotation
        # must be present.
        history = [('rev1', '', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('file_id', history)
        ann_ui.args = ['rev1']
        annotate_info = ann_ui.get_values('filename',
            kwargs={'file_id': 'file_id'}, headers={})
        annotated = annotate_info['annotated']
        self.assertEqual(0, len(annotated))

    def test_annotate_nonexistent_file(self):
        history = [('rev1', '', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('file_id', history)
        ann_ui.args = ['rev1']
        self.assertRaises(
            HTTPNotFound, ann_ui.get_values, 'not-filename', {}, {})

    def test_annotate_nonexistent_rev(self):
        history = [('rev1', '', '.')]
        ann_ui = self.make_annotate_ui_for_file_history('file_id', history)
        ann_ui.args = ['norev']
        self.assertRaises(
            HTTPNotFound, ann_ui.get_values, 'not-filename', {}, {})


class TestFileDiffUI(BasicTests):

    def make_branch_app_for_filediff_ui(self):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('rev-1-id', None, [
            ('add', ('', 'root-id', 'directory', '')),
            ('add', ('filename', 'f-id', 'file', 'content\n'))],
            message="First commit.")
        builder.build_snapshot('rev-2-id', None, [
            ('modify', ('f-id', 'new content\n'))])
        builder.finish_series()
        branch = builder.get_branch()
        self.addCleanup(branch.lock_read().unlock)
        return self.make_branch_app(branch)

    def test_get_values_smoke(self):
        branch_app = self.make_branch_app_for_filediff_ui()
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/+filediff/rev-2-id/rev-1-id/f-id'}
        filediff_ui = branch_app.lookup_app(env)
        filediff_ui.parse_args(env)
        values = filediff_ui.get_values('', {}, {})
        chunks = values['chunks']
        self.assertEqual('insert', chunks[0].diff[1].type)
        self.assertEqual('new content', chunks[0].diff[1].line)

    def test_json_render_smoke(self):
        branch_app = self.make_branch_app_for_filediff_ui()
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/+json/+filediff/rev-2-id/rev-1-id/f-id'}
        filediff_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(filediff_ui, env)


class TestRevLogUI(BasicTests):

    def make_branch_app_for_revlog_ui(self):
        builder = self.make_branch_builder('branch')
        builder.start_series()
        builder.build_snapshot('rev-id', None, [
            ('add', ('', 'root-id', 'directory', '')),
            ('add', ('filename', 'f-id', 'file', 'content\n'))],
            message="First commit.")
        builder.finish_series()
        branch = builder.get_branch()
        self.addCleanup(branch.lock_read().unlock)
        return self.make_branch_app(branch)

    def test_get_values_smoke(self):
        branch_app = self.make_branch_app_for_revlog_ui()
        env = {'SCRIPT_NAME': '/',
               'PATH_INFO': '/+revlog/rev-id'}
        revlog_ui = branch_app.lookup_app(env)
        revlog_ui.parse_args(env)
        values = revlog_ui.get_values('', {}, {})
        self.assertEqual(values['file_changes'].added[1].filename, 'filename')
        self.assertEqual(values['entry'].comment, "First commit.")

    def test_json_render_smoke(self):
        branch_app = self.make_branch_app_for_revlog_ui()
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/+json/+revlog/rev-id'}
        revlog_ui = branch_app.lookup_app(env)
        self.assertOkJsonResponse(revlog_ui, env)


class TestControllerHooks(BasicTests):

    def test_dummy_hook(self):
        return
        # A hook that returns None doesn't influence the searching for
        # a controller.
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/custom'}
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
        env = {'SCRIPT_NAME': '', 'PATH_INFO': '/custom'}
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
        response = app.get('/download/1/myfilename-id/myfilename')
        self.assertEqual(
            'some\nmultiline\ndata\nwith<htmlspecialchars\n', response.body)
        self.assertThat(
            response,
            MatchesDownloadHeaders('myfilename', 'application/octet-stream'))

    def test_download_bad_revision(self):
        app = self.setUpLoggerhead()
        e = self.assertRaises(
            AppError,
            app.get, '/download/norev/myfilename-id/myfilename')
        self.assertContainsRe(str(e), '404 Not Found')

    def test_download_bad_fileid(self):
        app = self.setUpLoggerhead()
        e = self.assertRaises(
            AppError,
            app.get, '/download/1/myfilename-notid/myfilename')
        self.assertContainsRe(str(e), '404 Not Found')


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
