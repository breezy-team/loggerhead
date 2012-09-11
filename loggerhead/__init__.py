#
# Copyright (C) 2008, 2009 Canonical Ltd.
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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA

"""A simple container to turn this into a python package.

We also check the versions of some dependencies.
"""

import pkg_resources

__version__ = '1.18.2'  # Keep in sync with ../info.py.
__revision__ = None
required_bzrlib = (1, 17)

pkg_resources.get_distribution('Paste>=1.6')
try:
    pkg_resources.get_distribution('PasteDeploy>=1.3')
except pkg_resources.DistributionNotFound:
    # No paste.deploy is OK, but an old paste.deploy is bad.
    pass

try:
    from bzrlib.branch import Branch
    branch = Branch.open('./');

    __revision__ = branch.revno()
    
except:
    pass
