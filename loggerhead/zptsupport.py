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
