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
#
"""Support for Zope Page Templates using the Chameleon library."""

import os
import pkg_resources
import re

from chameleon import PageTemplate

_zpt_cache = {}


def zpt(tfile):
    tinstance = _zpt_cache.get(tfile)
    stat = os.stat(tfile)
    if tinstance is None or tinstance.stat != stat:
        with open(tfile) as tf:
            text = tf.read()
        text = re.sub(r'\s*\n\s*', '\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        tinstance = _zpt_cache[tfile] = TemplateWrapper(
            PageTemplate(text), tfile, stat)
    return tinstance


class TemplateWrapper(object):

    def __init__(self, template, filename, stat):
        self.template = template
        self.filename = filename
        self.stat = stat

    def expand(self, **info):
        return self.template(**info)

    def expand_into(self, f, **info):
        f.write(self.template(**info).encode('UTF-8'))

    @property
    def macros(self):
        return self.template.macros


def load_template(classname):
    """Searches for a template along the Python path.

    Template files must end in ".pt" and be in legitimate packages.
    Templates are automatically checked for changes and reloaded as
    neccessary.
    """
    divider = classname.rfind(".")
    if divider > -1:
        package = classname[0:divider]
        basename = classname[divider+1:]
    else:
        raise ValueError("All templates must be in a package")

    tfile = pkg_resources.resource_filename(
        package, "%s.%s" % (basename, "pt"))
    return zpt(tfile)
