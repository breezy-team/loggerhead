# Copyright 2011 Canonical Ltd
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

from ..util import html_escape, html_format


class TestHTMLEscaping(tests.TestCase):

    def test_html_escape(self):
        self.assertEqual(
            "foo &quot;&#39;&lt;&gt;&amp;",
            html_escape("foo \"'<>&"))

    def test_html_format(self):
        self.assertEqual(
            '<foo bar="baz&quot;&#39;">&lt;baz&gt;&amp;</foo>',
            html_format(
                '<foo bar="%s">%s</foo>', "baz\"'", "<baz>&"))
