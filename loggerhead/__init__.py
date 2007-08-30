import os
import turbogears
import turbozpt
from turbozpt.template import zpt

_base = os.path.dirname(__file__)
def _pt(name):
    return zpt(os.path.join(_base, 'templates', name + '.pt'))


def file_change_summary(url, entry, links=True):
    return _pt('revisionfilechanges')(url=url, entry=entry, links=links)

def revisioninfo(url, branch, entry, includefilechanges=False):
    from loggerhead import util
    return _pt('revisioninfo')(
        url=url, change=entry, branch=branch, util=util,
        includefilechanges=includefilechanges,
        file_change_summary=file_change_summary)


def collapse_button(group, name, normal='block'):
    return _pt('collapse-button')(
        group=group, name=name, normal=normal, tg=turbogears)

def collapse_all_button(group, normal='block'):
    return _pt('collapse-all-button')(
        group=group, normal=normal, tg=turbogears)

def revno_with_nick(entry):
    if entry.branch_nick:
        extra = ' ' + entry.branch_nick
    else:
        extra = ''
    return '(%s%s)'%(child.revno, extra)

templatefunctions = {'file_change_summary': file_change_summary,
                     'revisioninfo': revisioninfo,
                     'collapse_button': collapse_button,
                     'collapse_all_button': collapse_all_button,
                     'revno_with_nick': revno_with_nick}
