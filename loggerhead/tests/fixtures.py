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

from __future__ import absolute_import

from fixtures import Fixture


class SampleBranch(Fixture):

    def __init__(self, testcase):
        # Must be a bzr TestCase to hook into branch creation, unfortunately.
        self.testcase = testcase

    def setUp(self):
        Fixture.setUp(self)

        self.tree = self.testcase.make_branch_and_tree('.')

        self.filecontents = (
            'some\nmultiline\ndata\n'
            'with<htmlspecialchars\n')
        filenames = ['myfilename', 'anotherfile<', 'folder/', 'folder/myfilename']
        self.testcase.build_tree_contents(
            (filename, self.filecontents) for filename in filenames)
        self.tree.add(filenames)
        self.path = 'myfilename'
        self.msg = 'a very exciting commit message <'
        self.revid = self.tree.commit(message=self.msg, rev_id=b'rev-1')
