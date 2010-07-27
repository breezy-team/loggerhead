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

from distutils.core import setup

import loggerhead


setup(
    name = "loggerhead",
    version = loggerhead.__version__,
    description = "Loggerhead is a web viewer for projects in bazaar",
    license = "GNU GPL v2 or later",
    maintainer = "Michael Hudson",
    maintainer_email = "michael.hudson@canonical.com",
    scripts = ["serve-branches"],
    packages = ["loggerhead",
                "loggerhead/apps",
                "loggerhead/controllers",
                "loggerhead/templates",
                "loggerhead/tests",
                "bzrlib.plugins.loggerhead"],
    package_dir={'bzrlib.plugins.loggerhead':'.'},
    package_data = {"loggerhead": ["templates/*.pt",
                                   "static/css/*.css",
                                   "static/javascript/*.js",
                                   "static/images/*"]},
    data_files = [
        ('share/man/man1', ['serve-branches.1']),
        ('share/doc/loggerhead', ['loggerhead.conf.example']),
        ],
    )
