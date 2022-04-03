# Copyright 2022 Canonical Ltd
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

from breezy import tests

from ..highlight import highlight


class TestHighLight(tests.TestCase):
    def test_no_highlighting_for_big_texts(self):
        rv = highlight(
            path="",
            text="text\n" * 102401,  # bigger than MAX_HIGHLIGHT_SIZE
            encoding="utf-8",
        )
        self.assertIsInstance(rv, list)
        self.assertLength(102401, rv)
        # no highlighting applied
        for item in rv:
            self.assertEqual("text\n", item)
