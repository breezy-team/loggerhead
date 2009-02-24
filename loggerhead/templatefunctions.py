#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
#
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
templatefunctions['breadcrumbs'] = _pt('breadcrumbs').macros


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
def branchinfo(branch):
    if branch.served_url is not None:
        return _pt('branchinfo').expand(branch=branch, **templatefunctions)
    else:
        return ''


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


@templatefunc
def search_box(branch, navigation):
    return _pt('search-box').expand(branch=branch, navigation=navigation,
        **templatefunctions)


@templatefunc
def feed_link(branch, url):
    return _pt('feed-link').expand(branch=branch, url=url, **templatefunctions)


@templatefunc
def menu(branch, url, fileview_active=False):
    return _pt('menu').expand(branch=branch, url=url,
        fileview_active=fileview_active, **templatefunctions)
