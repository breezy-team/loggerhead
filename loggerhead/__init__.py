import os
import turbogears
import turbozpt
from turbozpt.template import zpt

_base = os.path.dirname(__file__)
def _pt(name):
    return zpt(os.path.join(_base, 'templates', name + '.pt'))


def file_change_summary(url, entry, modified_file_link):
    return _pt('revisionfilechanges')(
        url=url, entry=entry, modified_file_link=modified_file_link,
        **templatefunctions)

def revisioninfo(url, branch, entry, modified_file_link=None):
    from loggerhead import util
    return _pt('revisioninfo')(
        url=url, change=entry, branch=branch, util=util,
        modified_file_link=modified_file_link,
        **templatefunctions)

def collapse_button(group, name, normal='block'):
    return _pt('collapse-button')(
        group=group, name=name, normal=normal, tg=turbogears,
        **templatefunctions)

def collapse_all_button(group, normal='block'):
    return _pt('collapse-all-button')(
        group=group, normal=normal, tg=turbogears,
        **templatefunctions)

def revno_with_nick(entry):
    if entry.branch_nick:
        extra = ' ' + entry.branch_nick
    else:
        extra = ''
    return '(%s%s)'%(entry.revno, extra)

def modified_file_link_rev(url, entry, item):
    return _pt('modified-file-link-rev')(
        url=url, entry=entry, item=item,
        **templatefunctions)

def modified_file_link_log(url, entry, item):
    return _pt('modified-file-link-log')(
        url=url, entry=entry, item=item,
        **templatefunctions)

templatefunctions = {'file_change_summary': file_change_summary,
                     'revisioninfo': revisioninfo,
                     'collapse_button': collapse_button,
                     'collapse_all_button': collapse_all_button,
                     'revno_with_nick': revno_with_nick,
                     'modified_file_link_log': modified_file_link_log,
                     'modified_file_link_rev': modified_file_link_rev}
