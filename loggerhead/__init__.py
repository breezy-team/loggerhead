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

"""A simple container to turn this into a python package."""

try:
    import importlib.metadata as importlib_metadata
except ImportError:
    import importlib_metadata

try:
    __version__ = importlib_metadata.version("loggerhead")
except importlib_metadata.PackageNotFoundError:
    # Support running tests from the build tree without installation.
    import os
    from setuptools.config import read_configuration
    cfg = read_configuration(os.path.join(os.path.dirname(__file__), '..', 'setup.cfg'))
    __version__ = cfg['metadata']['version']
__revision__ = None
required_breezy = (3, 1)
