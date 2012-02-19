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
    scripts = [
        "serve-branches",
        "loggerhead.wsgi",
        ],
    packages = ["loggerhead",
                "loggerhead/apps",
                "loggerhead/controllers",
                "loggerhead/templates",
                "bzrlib.plugins.loggerhead"],
    package_dir={'bzrlib.plugins.loggerhead':'.'},
    package_data = {"loggerhead": ["templates/*.pt",
                                   "static/css/*.css",
                                   "static/javascript/*.js",
                                   "static/javascript/yui/build/anim/*",
                                   "static/javascript/yui/build/base/*",
                                   "static/javascript/yui/build/cssbase/*",
                                   "static/javascript/yui/build/cssgrids/*",
                                   "static/javascript/yui/build/dd/*",
                                   "static/javascript/yui/build/dump/*",
                                   "static/javascript/yui/build/get/*",
                                   "static/javascript/yui/build/json/*",
                                   "static/javascript/yui/build/node/*",
                                   "static/javascript/yui/build/queue/*",
                                   "static/javascript/yui/build/yui/*",
                                   "static/javascript/yui/build/attribute/*",
                                   "static/javascript/yui/build/cookie/*",
                                   "static/javascript/yui/build/cssfonts/*",
                                   "static/javascript/yui/build/cssreset/*",
                                   "static/javascript/yui/build/dom/*",
                                   "static/javascript/yui/build/event/*",
                                   "static/javascript/yui/build/io/*",
                                   "static/javascript/yui/build/loader/*",
                                   "static/javascript/yui/build/oop/*",
                                   "static/javascript/yui/build/substitute/*",
                                   "static/javascript/yui/build/yui-base/*",
                                   "static/images/*"]},
    data_files = [
        ('share/man/man1', ['serve-branches.1']),
        ('share/doc/loggerhead', ['apache-loggerhead.conf',
                                  'bazaar.conf']),
        ],
    )
