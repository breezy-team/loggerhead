#!/usr/bin/env python3
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

from setuptools import setup

import loggerhead


with open("README.rst") as readme:
    long_description = readme.read()


setup(
    name="loggerhead",
    version=loggerhead.__version__,
    description="Loggerhead is a web viewer for projects in bazaar",
    long_description=long_description,
    long_description_content_type="text/x-rst",
    license="GNU GPL v2 or later",
    maintainer="Michael Hudson",
    maintainer_email="michael.hudson@canonical.com",
    scripts=[
        "loggerhead-serve",
        ],
    packages=["loggerhead",
              "loggerhead/apps",
              "loggerhead/controllers",
              "loggerhead/middleware",
              "loggerhead/templates",
              "breezy.plugins.loggerhead"],
    package_dir={'breezy.plugins.loggerhead': '.'},
    package_data={"loggerhead": ["templates/*.pt",
                                 "static/css/*.css",
                                 "static/javascript/*.js",
                                 "static/images/*"]},
    data_files=[
        ('share/man/man1', ['loggerhead-serve.1']),
        ('share/doc/loggerhead', ['apache-loggerhead.conf',
                                  'loggerheadd',
                                  'breezy.conf']),
        ],
    install_requires=[
        'paste',
        'bleach',
        'breezy>=3.1',
    ],
    testsuite='loggerhead.tests.test_suite',
    )
