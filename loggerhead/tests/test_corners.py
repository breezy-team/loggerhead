from __future__ import absolute_import

import os

from .test_simple import BasicTests


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
        os.chmod('myfilename', 0o755)
        newrevid = self.tree.commit(message='make something executable')

        # Check that it didn't break things.
        app = self.setUpLoggerhead()
        res = app.get('/revision/'+newrevid.decode('utf-8'))
        res.mustcontain(b'executable')

    def test_revision_escapes_commit_message(self):
        """XXX."""
        self.createBranch()

        msg = b'<b>hi</b>'
        self.addFileAndCommit('myfilename', msg)
        app = self.setUpLoggerhead()
        res = app.get('/revision/1')
        self.assertFalse(msg in res.body)

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
        res.mustcontain('1')

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
        res.mustcontain('1')
