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
#
"""Support for Zope Page Templates using the simpletal library."""

import logging
import os
import pkg_resources
import StringIO

from simpletal import simpleTAL, simpleTALES

logging.getLogger("simpleTAL").setLevel(logging.INFO)
logging.getLogger("simpleTALES").setLevel(logging.INFO)


_zpt_cache = {}
def zpt(tfile):
    tinstance = _zpt_cache.get(tfile)
    stat = os.stat(tfile)
    if tinstance is None or tinstance.stat != stat:
        tinstance = _zpt_cache[tfile] = TemplateWrapper(
            simpleTAL.compileXMLTemplate(open(tfile)), tfile, stat)
    return tinstance


class TemplateWrapper(object):

    def __init__(self, template, filename, stat):
        self.template = template
        self.filename = filename
        self.stat = stat

    def expand(self, **info):
        context = simpleTALES.Context(allowPythonPath=1)
        for k, v in info.iteritems():
            context.addGlobal(k, v)
        s = StringIO.StringIO()
        self.template.expandInline(context, s)
        return s.getvalue()

    def expand_into(self, f, **info):
        context = simpleTALES.Context(allowPythonPath=1)
        for k, v in info.iteritems():
            context.addGlobal(k, v)
        self.template.expand(context, f, 'utf-8')

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
        raise ValueError, "All templates must be in a package"

    tfile = pkg_resources.resource_filename(
        package, "%s.%s" % (basename, "pt"))
    return zpt(tfile)
