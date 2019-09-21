# Copyright (C) 2011 Canonical Ltd.
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
#

from __future__ import absolute_import

from .test_simple import BasicTests


class TestRevisionUI(BasicTests):

    def test_authors_vs_committer(self):
        self.createBranch()
        self.tree.commit('First', committer="Joe Example <joe@example.com>",
            revprops={'authors': u'A Author <aauthor@example.com>\n'
                                 u'B Author <bauthor@example.com>'})
        app = self.setUpLoggerhead()
        res = app.get('/revision/1')
        # We would like to assert that Joe Example is connected to Committer,
        # and the Authors are connected. However, that requires asserting the
        # exact HTML connections, which I wanted to avoid.
        res.mustcontain('Committer', 'Joe Example',
                        'Author(s)', 'A Author, B Author')

    def test_author_is_committer(self):
        self.createBranch()
        self.tree.commit('First', committer="Joe Example <joe@example.com>")
        app = self.setUpLoggerhead()
        res = app.get('/revision/1')
        # We would like to assert that Joe Example is connected to Committer,
        # and the Authors are connected. However, that requires asserting the
        # exact HTML connections, which I wanted to avoid.
        res.mustcontain('Committer', 'Joe Example')
        self.assertFalse(b'Author(s)' in res.body)
