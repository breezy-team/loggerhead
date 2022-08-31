# Copyright (C) 2022 Canonical Ltd.
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

from .test_simple import TestWithSimpleTree


class TestInventoryUI(TestWithSimpleTree):

    def test_authors_vs_committer(self):
        app = self.setUpLoggerhead()
        res = app.get('/files')
        # download url in top directory is composed correctly
        res.mustcontain('/download/rev-1/myfilename')

        res2 = app.get('/files/head:/folder')
        # download url in subdirectory is composed correctly
        res2.mustcontain('/download/rev-1/folder/myfilename')