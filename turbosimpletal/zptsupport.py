"TurboGears support for Zope Page Templates"

import StringIO
import logging
import os
import pkg_resources

from simpletal import simpleTAL, simpleTALES

log = logging.getLogger("turbogears.zptsupport")


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

    @property
    def macros(self):
        return self.template.macros


class TurboZpt(object):
    extension = "pt"

    def __init__(self, extra_vars_func=None):
        self.get_extra_vars = extra_vars_func

    def load_template(self, classname, loadingSite=False):
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
            package, "%s.%s" % (basename, self.extension))
        return zpt(tfile)

    def render(self, info, format="html", fragment=False, template=None):
        """Renders data in the desired format.

        @param info: the data / context itself
        @type info: dict
        @para format: "html"
        @type format: "string"
        @para template: name of the template to use
        @type template: string
        """
        tinstance = self.load_template(template)
        log.debug("Applying template %s" % (tinstance.filename))
        data = dict()
        if self.get_extra_vars:
            data.update(self.get_extra_vars())
        data.update(info)
        return tinstance.expand(**data).encode('utf-8')
