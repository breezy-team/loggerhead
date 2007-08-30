"""
By VladDrac@irc.freenode.net/#turbogears
+ Some small modifications
"""

from zope.pagetemplate import pagetemplatefile
import os.path
import sys

_zpt_cache = {}

def _compile_template(tfile):
    mod = PageTemplate(tfile)
    mtime = os.stat(tfile).st_mtime
    mod.__mtime__ = mtime
    return mod

def zpt(tfile):
    if tfile in _zpt_cache:
        mtime = os.stat(tfile).st_mtime
        mod = _zpt_cache[tfile]
        if mod.__mtime__ != mtime:
            mod = _compile_template(tfile)
            _zpt_cache[tfile] = mod
    else:
        mod = _zpt_cache[tfile] = _compile_template(tfile)
    return mod

class Here(object):
    def __init__(self, base, options):
        self.base = base
        self.options = options

    def __getitem__(self, name):
        tpl = zpt(os.path.join(self.base, name))
        return tpl(**self.options)

class PageTemplate(pagetemplatefile.PageTemplateFile):
    def __init__(self, name):
    	base = os.path.dirname(sys._getframe(1).f_globals["__file__"])
        self.name = name
        self.fullpath = os.path.join(base, self.name)
        self.base = os.path.dirname(self.fullpath)
        pagetemplatefile.PageTemplateFile.__init__(self, self.fullpath)

    def pt_getContext(self, args=(), options={}, **ignored):
        rval = pagetemplatefile.PageTemplateFile.pt_getContext(self, args, options, **ignored)
	rval.update(options)
        rval.update({'here':Here(self.base, options), 'template':self})
        return rval
