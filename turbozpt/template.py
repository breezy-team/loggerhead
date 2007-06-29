"""
By VladDrac@irc.freenode.net/#turbogears
+ Some small modifications
"""

from zope.pagetemplate import pagetemplatefile
import os.path
import sys

class Here(object):
    def __init__(self, base):
        self.base = base

    def __getattr__(self, name):
        # import pdb; pdb.set_trace()
        tpl = PageTemplate(os.path.join(self.base, name))
        return tpl

class PageTemplate(pagetemplatefile.PageTemplateFile):
    def __init__(self, name):
    	base = os.path.dirname(sys._getframe(1).f_globals["__file__"])
	self.extra_context = {}
        self.name = name
        self.fullpath = os.path.join(base, self.name)
        self.base = os.path.dirname(self.fullpath)
        pagetemplatefile.PageTemplateFile.__init__(self, self.fullpath)
    
    def render(self, extra_dict=None):
	if extra_dict:
    	    context = self.pt_getContext()
	    context.update(extra_dict)
	return self.pt_render(context)
    
    def add_context(self, d):
	self.extra_context.update(d)
	
    def pt_getContext(self, args=(), options={}, **ignored):
        rval = pagetemplatefile.PageTemplateFile.pt_getContext(self, args, options, **ignored)
	rval.update(options)
	rval.update(self.extra_context)
        rval.update({'here':Here(self.base), 'template':self})
        return rval
