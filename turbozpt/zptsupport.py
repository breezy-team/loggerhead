"TurboGears support for Zope Page Templates"

from template import zpt
import pkg_resources

import logging
log = logging.getLogger("turbogears.zptsupport")

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
        return tinstance(**data).encode('utf-8')

