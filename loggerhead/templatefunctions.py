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
import cgi
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
def file_change_summary(url, entry, style='normal', currently_showing=None):
    if style == 'fragment':
        def file_link(filename):
            if currently_showing and filename == currently_showing:
                return '<b><a href="#%s">%s</a></b>' % (
                    cgi.escape(filename), cgi.escape(filename))
            else:
                return revision_link(
                    url, entry.revno, filename, '#' + filename)
    else:
        def file_link(filename):
            return '<a href="%s%s" title="View changes to %s in revision %s">%s</a>'%(
                url(['/revision', entry.revno]), '#' + filename, cgi.escape(filename),
                cgi.escape(entry.revno), cgi.escape(filename))
    return _pt('revisionfilechanges').expand(
        file_changes=entry.changes, file_link=file_link, **templatefunctions)


@templatefunc
def revisioninfo(url, branch, entry, include_file_list=False, currently_showing=None):
    from loggerhead import util
    return _pt('revisioninfo').expand(
        url=url, change=entry, branch=branch, util=util,
        include_file_list=include_file_list, currently_showing=currently_showing,
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


@templatefunc
def annotate_link(url, revno, path):
    return '<a href="%s" title="Annotate %s">%s</a>'%(
        url(['/annotate', revno, path]), cgi.escape(path), cgi.escape(path))

@templatefunc
def revision_link(url, revno, path, frag=''):
    return '<a href="%s%s" title="View changes to %s in revision %s">%s</a>'%(
        url(['/revision', revno, path]), frag, cgi.escape(path),
        cgi.escape(revno), cgi.escape(path))
