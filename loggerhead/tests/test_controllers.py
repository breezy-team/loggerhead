from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.tests.test_simple import BasicTests


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
        self.assertEqual(1, len(inv_ui.get_filelist(inv, '')))

