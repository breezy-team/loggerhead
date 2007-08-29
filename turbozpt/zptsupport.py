"TurboGears support for Zope Page Templates"

import sys, os

from template import PageTemplate
import pkg_resources

import logging
log = logging.getLogger("turbogears.zptsupport")

def _recompile_template(package, basename, tfile, classname):
    log.debug("Recompiling template for %s" % classname)
    mod = PageTemplate(tfile)
    mtime = os.stat(tfile).st_mtime
    mod.__mtime__ = mtime
    return mod

class TurboZpt:
    extension = "pt"
    
    def __init__(self, extra_vars_func=None, options={}):
	self.options = options
	self.get_extra_vars = extra_vars_func
        self.compiledTemplates = {}
    
    def load_template(self, classname, loadingSite=False):
        """Searches for a template along the Python path.

        Template files must end in ".pt" and be in legitimate packages.
        U can set "zpt.cache_templates" option to cache a loaded template
	class and only check for updates. Templates are automatically
	checked for changes and reloaded as neccessary.
        """
        ct = self.compiledTemplates

        divider = classname.rfind(".")
        if divider > -1:
            package = classname[0:divider]
            basename = classname[divider+1:]
        else:
            raise ValueError, "All templates must be in a package"

        cache_templates = self.options.get("zpt.cache_templates", True)
        tfile = pkg_resources.resource_filename(package, 
                                                "%s.%s" % 
                                                (basename,
                                                self.extension))
						
        if cache_templates:
            if ct.has_key(classname):
                mtime = os.stat(tfile).st_mtime
		mod = ct[classname]
                if mod.__mtime__ != mtime:
		    # Recompile template
		    mod = _recompile_template(package, basename, tfile, classname)
                    ct[classname] = mod
                #else:
		    # use template from cache    
		    # pass 
            else:
		# First time compile template
		mod = PageTemplate(tfile)
                mod.__mtime__ = os.stat(tfile).st_mtime
		ct[classname] = mod
        else:
	    mod = PageTemplate(tfile)

        return mod

    def render(self, info, format="html", fragment=False, template=None):
	"""Renders data in the desired format.
	
	@param info: the data / context itself
	@type info: dict
	@para format: "html"
	@type format: "string"
	@para template: name of the template to use
	@type template: string
	"""
	#if isinstance(template, type):
	#    tclass = template
	#else:
	
	tinstance = self.load_template(template)
	log.debug("Applying template %s" % (tinstance.filename))
	data = dict()
	if self.get_extra_vars:
	    data.update(self.get_extra_vars())
	data.update(info)
        return tinstance(**data).encode('utf-8')

    def transform(self, info, template):
	"Render the output to Elements"
	pass
