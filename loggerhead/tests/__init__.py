# Copyright 2006, 2010, 2011 Canonical Ltd
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


def test_suite():
    import unittest

    loader = unittest.TestLoader()
    return loader.loadTestsFromNames(
        [
            (__name__ + "." + x)
            for x in [
                "test_controllers",
                "test_corners",
                "test_history",
                "test_http_head",
                "test_load_test",
                "test_simple",
                "test_revision_ui",
                "test_templating",
                "test_util",
                "test_highlight",
            ]
        ]
    )
