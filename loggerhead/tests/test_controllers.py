from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.controllers.inventory_ui import InventoryUI
from loggerhead.history import History
from loggerhead.tests.test_simple import BasicTests


class TestInventoryUI(BasicTests):

    def test_get_filelist(self):

        self.tree = self.make_branch_and_tree('.')
        self.build_tree_contents(
            [('filename', '')])
        self.tree.add('filename')
        self.tree.commit('')
        self.tree.branch.lock_read()
        self.addCleanup(self.tree.branch.unlock)
        inv_ui = InventoryUI(
            BranchWSGIApp(self.tree.branch), lambda : History(self.tree.branch, {}))
        inv = self.tree.branch.repository.get_inventory(self.tree.branch.last_revision())
        self.assertEqual(1, len(inv_ui.get_filelist(inv, '')))

