import os

from loggerhead.tests.test_simple import BasicTests


class TestCornerCases(BasicTests):
    """Tests that excercise various corner cases."""

    def addFileAndCommit(self, filename, commit_msg):
        """Make a trivial commit that has 'msg' as its commit message.

        The commit adds a file called 'myfilename' containing the string
        'foo'.
        """
        self.build_tree_contents([(filename, 'foo')])
        self.tree.add(filename)
        self.tree.commit(message=commit_msg)

    def test_revision_only_changing_execute_bit(self):
        """Check that a commit that only changes the execute bit of a file
        does not break the rendering."""
        self.createBranch()

        # Just a commit to have a file to change the execute bit of.
        msg = 'a very exciting commit message'
        self.addFileAndCommit('myfilename', msg)

        # Make a commit that changes the execute bit of 'myfilename'.
        os.chmod('myfilename', 0755)
        newrevid = self.tree.commit(message='make something executable')

        # Check that it didn't break things.
        app = self.setUpLoggerhead()
        res = app.get('/revision/'+newrevid)
        res.mustcontain('executable')

    def test_empty_commit_message(self):
        """Check that an empty commit message does not break the rendering."""
        self.createBranch()

        # Make a commit that has an empty message.
        self.addFileAndCommit('myfilename', '')

        # Check that it didn't break things.
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        # It's not much of an assertion, but we only really care about
        # "assert not crashed".
        res.mustcontain('myfilename')

    def test_whitespace_only_commit_message(self):
        """Check that a whitespace-only commit message does not break the
        rendering."""
        self.createBranch()

        # Make a commit that has a whitespace only message.
        self.addFileAndCommit('myfilename', '   ')

        # Check that it didn't break things.
        app = self.setUpLoggerhead()
        res = app.get('/changes')
        # It's not much of an assertion, but we only really care about
        # "assert not crashed".
        res.mustcontain('myfilename')
