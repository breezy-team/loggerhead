from cStringIO import StringIO
import logging

from paste.httpexceptions import HTTPServerError

from bzrlib import errors

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.controllers.annotate_ui import AnnotateUI
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.controllers.revision_ui import RevisionUI
from loggerhead.tests.test_simple import BasicTests
from loggerhead import util


class TestInventoryUI(BasicTests):

    def make_bzrbranch_and_inventory_ui_for_tree_shape(self, shape):
        tree = self.make_branch_and_tree('.')
        self.build_tree(shape)
        tree.smart_add([])
        tree.commit('')
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = BranchWSGIApp(tree.branch, '')
        branch_app.log.setLevel(logging.CRITICAL)
        # These are usually set in BranchWSGIApp.app(), which is set from env
        # settings set by BranchesFromTransportRoot, so we fake it.
        branch_app._static_url_base = '/'
        branch_app._url_base = '/'
        return tree.branch, InventoryUI(branch_app, branch_app.get_history)

    def consume_app(self, app, extra_environ=None):
        env = {'SCRIPT_NAME': '/files', 'PATH_INFO': ''}
        if extra_environ is not None:
            env.update(extra_environ)
        body = StringIO()
        start = []
        def start_response(status, headers, exc_info=None):
            start.append((status, headers, exc_info))
            return body.write
        extra_content = list(app(env, start_response))
        body.writelines(extra_content)
        return start[0], body.getvalue()

    def test_get_filelist(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        inv = bzrbranch.repository.get_inventory(bzrbranch.last_revision())
        self.assertEqual(1, len(inv_ui.get_filelist(inv, '', 'filename')))

    def test_smoke(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        start, content = self.consume_app(inv_ui)
        self.assertEqual(('200 OK', [('Content-Type', 'text/html')], None),
                         start)
        self.assertContainsRe(content, 'filename')

    def test_no_content_for_HEAD(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        start, content = self.consume_app(inv_ui,
                            extra_environ={'REQUEST_METHOD': 'HEAD'})
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
        branch_app = BranchWSGIApp(tree.branch)
        branch_app._environ = {
            'wsgi.url_scheme':'',
            'SERVER_NAME':'',
            'SERVER_PORT':'80',
            }
        branch_app._url_base = ''
        branch_app.friendly_name = ''
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
        open('filename', 'w').write('')
        tree.add(['filename'], [file_id])
        for rev_id, text in rev_ids_texts:
            open('filename', 'w').write(text)
            tree.commit(rev_id=rev_id, message='.')
        tree.branch.lock_read()
        self.addCleanup(tree.branch.unlock)
        branch_app = BranchWSGIApp(tree.branch)
        return AnnotateUI(branch_app, branch_app.get_history)

    def test_annotate_file(self):
        history = [('rev1', 'old\nold\n'), ('rev2', 'new\nold\n')]
        ann_ui = self.make_annotate_ui_for_file_history('file_id', history)
        annotated = list(ann_ui.annotate_file('file_id', 'rev2'))
        self.assertEqual(2, len(annotated))
        self.assertEqual('2', annotated[0].change.revno)
        self.assertEqual('1', annotated[1].change.revno)
