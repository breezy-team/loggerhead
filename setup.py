#!/usr/bin/env python
#
# Copyright (C) 2008  Canonical Ltd.
#                     (Authored by Martin Albisetti <argentina@gmail.com>)
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
"""Loggerhead is a web viewer for projects in bazaar"""

from distutils.core import setup, Command
from distutils.command.install_data import install_data
from distutils.dep_util import newer
from distutils.log import info
import glob
import os
import sys
import loggerhead
import bzrlib


# Make sure you have all required dependencies
if sys.version_info < (2, 4):
    sys.stderr.write("[ERROR] Not a supported Python version. Need 2.4+\n")
    sys.exit(1)

bzrlib_version = bzrlib.version_info[:2]
try:
    from bzrlib.trace import warning
except ImportError:
    from warnings import warn as warning
if bzrlib_version < loggerhead.required_bzrlib:
    from bzrlib.errors import BzrError
    warning('Installed Bazaar version %s is too old to be used with loggerhead'
            ' %s.' % (bzrlib.__version__, __version__))
    raise BzrError('Version mismatch: %r, %r' % (version_info, 
                                                 bzrlib.version_info) )

try:
    import paste
except ImportError:
    raise errors.BzrCommandError("python-paste not installed.")
try:
    import simpletal
except ImportError:
    raise errors.BzrCommandError("python-simpletal not installed.")



class InstallData(install_data):
    def run(self):
        install_data.run(self)

setup(
    name = "loggerhead",
    version = loggerhead.__version__,
    description = "Loggerhead is a web viewer for projects in bazaar",
    license = "GNU GPL v2 or later",
    maintainer = "Michael Hudson",
    maintainer_email = "michael.hudson@canonical.com",
    scripts = ["start-loggerhead", "stop-loggerhead", "serve-branches"],
    packages = ["loggerhead",
               ],
    package_data = {"loggerhead":["templates/*"]},
    data_files=[
                ('share/man/man1',['start-loggerhead.1', 'stop-loggerhead.1']),
                ('share/doc/loggerhead', ['loggerhead.conf.example'])
               ],
    cmdclass={'install_data':InstallData}
    )
    
