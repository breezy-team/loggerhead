import os
import turbogears
import turbozpt
from turbozpt.template import PageTemplate

_base = os.path.dirname(__file__)
def _pt(name):
    return PageTemplate(os.path.join(_base, 'templates', name + '.pt'))


def file_change_summary(url, entry, links=True):
    return _pt('revisionfilechanges').render(
        dict(url=url, entry=entry, links=links))

def revisioninfo(url, branch, entry, includefilechanges=False):
    from loggerhead import util
    return _pt('revisioninfo').render(
        dict(url=url, change=entry, branch=branch, util=util,
             includefilechanges=includefilechanges,
             file_change_summary=file_change_summary))


def collapse_button(group, name, normal='block'):
    return _pt('collapse-button').render(
        dict(group=group, name=name, normal=normal, tg=turbogears))

def collapse_all_button(group, normal='block'):
    return _pt('collapse-all-button').render(
        dict(group=group, normal=normal, tg=turbogears))

templatefunctions = {'file_change_summary':file_change_summary,
                     'revisioninfo':revisioninfo,
                     'collapse_button':collapse_button,
                     'collapse_all_button':collapse_all_button}
