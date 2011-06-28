from cStringIO import StringIO
import logging
import simplejson

from paste.httpexceptions import HTTPServerError

from bzrlib import errors

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.controllers.revlog_ui import RevLogUI
from loggerhead.tests.test_simple import BasicTests
from loggerhead import util


def consume_app(app, env):
    body = StringIO()
    start = []
    def start_response(status, headers, exc_info=None):
        start.append((status, headers, exc_info))
        return body.write
    extra_content = list(app(env, start_response))
    body.writelines(extra_content)
    return start[0], body.getvalue()


class TestInventoryUI(BasicTests):

    def make_bzrbranch_and_inventory_ui_for_tree_shape(self, shape):
        tree = self.make_branch_and_tree('.')
        self.build_tree(shape)
        tree.smart_add([])
        tree.commit('')
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = self.make_branch_app(tree.branch)
        return tree.branch, InventoryUI(branch_app, branch_app.get_history)

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


class TestRevisionUI(BasicTests):

    def make_bzrbranch_and_revision_ui_for_tree_shapes(self, shape1, shape2):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents(shape1)
        tree.smart_add([])
        tree.commit('')
        self.build_tree_contents(shape2)
        tree.smart_add([])
        tree.commit('')
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = self.make_branch_app(tree.branch)
        return tree.branch, RevisionUI(branch_app, branch_app.get_history)

    def test_get_values(self):
        branch, rev_ui = self.make_bzrbranch_and_revision_ui_for_tree_shapes(
            [], [])
        rev_ui.args = ['2']
        util.set_context({})
        self.assertIsInstance(
            rev_ui.get_values('', {}, []),
            dict)


class TestAnnotateUI(BasicTests):

    def make_annotate_ui_for_file_history(self, file_id, rev_ids_texts):
        tree = self.make_branch_and_tree('.')
        self.build_tree_contents([('filename', '')])
        tree.add(['filename'], [file_id])
        for rev_id, text in rev_ids_texts:
            self.build_tree_contents([('filename', text)])
            tree.commit(rev_id=rev_id, message='.')
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = BranchWSGIApp(tree.branch, friendly_name='test_name')
        return AnnotateUI(branch_app, branch_app.get_history)

    def test_annotate_file(self):
        history = [('rev1', 'old\nold\n'), ('rev2', 'new\nold\n')]
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
        start, content = consume_app(revlog_ui, env)
        self.assertEqual('200 OK', start[0])
        self.assertEqual('application/json', dict(start[1])['Content-Type'])
        self.assertEqual(None, start[2])
        simplejson.loads(content)

