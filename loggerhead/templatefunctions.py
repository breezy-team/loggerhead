import os
from loggerhead.zptsupport import zpt

templatefunctions = {}
def templatefunc(func):
    templatefunctions[func.__name__] = func
    return func


_base = os.path.dirname(__file__)
def _pt(name):
    return zpt(os.path.join(_base, 'templates', name + '.pt'))


templatefunctions['macros'] = _pt('macros').macros

@templatefunc
def file_change_summary(url, entry, modified_file_link):
    return _pt('revisionfilechanges').expand(
        url=url, entry=entry, modified_file_link=modified_file_link,
        **templatefunctions)

@templatefunc
def revisioninfo(url, branch, entry, modified_file_link=None):
    from loggerhead import util
    return _pt('revisioninfo').expand(
        url=url, change=entry, branch=branch, util=util,
        modified_file_link=modified_file_link,
        **templatefunctions)

@templatefunc
def collapse_button(group, name, branch, normal='block'):
    return _pt('collapse-button').expand(
        group=group, name=name, normal=normal, branch=branch,
        **templatefunctions)

@templatefunc
def collapse_all_button(group, branch, normal='block'):
    return _pt('collapse-all-button').expand(
        group=group, normal=normal, branch=branch,
        **templatefunctions)

@templatefunc
def revno_with_nick(entry):
    if entry.branch_nick:
        extra = ' ' + entry.branch_nick
    else:
        extra = ''
    return '(%s%s)'%(entry.revno, extra)

@templatefunc
def modified_file_link_rev(url, entry, item):
    return _pt('modified-file-link-rev').expand(
        url=url, entry=entry, item=item,
        **templatefunctions)

@templatefunc
def modified_file_link_log(url, entry, item):
    return _pt('modified-file-link-log').expand(
        url=url, entry=entry, item=item,
        **templatefunctions)

class tg:
    @staticmethod
    def url(what):
        return what

templatefunctions['tg'] =  tg
