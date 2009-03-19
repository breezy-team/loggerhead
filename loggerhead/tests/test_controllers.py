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
        branch_app = BranchWSGIApp(tree.branch)
        return tree.branch, InventoryUI(branch_app, branch_app.get_history)

    def test_get_filelist(self):
        bzrbranch, inv_ui = self.make_bzrbranch_and_inventory_ui_for_tree_shape(
            ['filename'])
        inv = bzrbranch.repository.get_inventory(bzrbranch.last_revision())
        self.assertEqual(1, len(inv_ui.get_filelist(inv, '', 'filename')))


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

    def test_get_changes_with_diff(self):
        branch, rev_ui = self.make_bzrbranch_and_revision_ui_for_tree_shapes(
            [('file', 'oldcontents'), ('file2', 'oldcontents')],
            [('file', 'newcontents'), ('file2', 'oldcontents')])
        change = rev_ui._history.get_changes([branch.last_revision()])[0]
        changes, diffs = rev_ui.get_changes_with_diff(change, None, None)
        self.assertEqual(1, len(diffs))

    def test_get_changes_with_diff_specific_path(self):
        branch, rev_ui = self.make_bzrbranch_and_revision_ui_for_tree_shapes(
            [('file', 'oldcontents'), ('file2', 'oldcontents')],
            [('file', 'newcontents'), ('file2', 'newcontents')])
        change = rev_ui._history.get_changes([branch.last_revision()])[0]
        changes, diffs = rev_ui.get_changes_with_diff(change, None, 'file')
        self.assertEqual(1, len(diffs))

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
