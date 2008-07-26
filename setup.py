#!/usr/bin/env python
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

from setuptools import setup, find_packages
from turbogears.finddata import find_package_data

import os
execfile(os.path.join("loggerhead", "release.py"))


setup(
    name="loggerhead",
    version=version,
    
    description=description,
    author=author,
    author_email=email,
    url=url,
    download_url=download_url,
    license=license,
    maintainer="Michael Hudson",
    maintainer_email="michael.hudson@canonical.com",
    
    install_requires = [
        "TurboGears >= 1.0b1",
# for some reason, distutils can't find bzr.
#        "bzr >= 0.13",
    ],
    scripts = ["start-loggerhead", "stop-loggerhead"],
    zip_safe=False,
    packages=find_packages(),
    package_data = find_package_data(where='loggerhead',
                                     package='loggerhead'),
#    data_files = find_package_data(where='loggerhead', package='loggerhead'),
    keywords = [
        'turbogears.app',
    ],
    classifiers = [
        'Development Status :: 3 - Alpha',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Framework :: TurboGears',
        'Framework :: TurboGears :: Applications',
    ],
    test_suite = 'nose.collector',
    )
    
