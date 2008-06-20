#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
# Copyright (C) 2006  Goffredo Baroncelli <kreijack@inwind.it>
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

try:
    from xml.etree import ElementTree as ET
except ImportError:
    from elementtree import ElementTree as ET

import base64
import cgi
import datetime
import logging
import re
import sha
import struct
import sys
import threading
import time
import traceback


log = logging.getLogger("loggerhead.controllers")

def fix_year(year):
    if year < 70:
        year += 2000
    if year < 100:
        year += 1900
    return year

# Display of times.

# date_day -- just the day
# date_time -- full date with time
#
# displaydate -- for use in sentences
# approximatedate -- for use in tables
#
# displaydate and approximatedate return an elementtree <span> Element
# with the full date in a tooltip.

def date_day(value):
    return value.strftime('%Y-%m-%d')


def date_time(value):
    return value.strftime('%Y-%m-%d %T')


def _displaydate(date):
    delta = abs(datetime.datetime.now() - date)
    if delta > datetime.timedelta(1, 0, 0):
        # far in the past or future, display the date
        return 'on ' + date_day(date)
    return _approximatedate(date)


def _approximatedate(date):
    delta = datetime.datetime.now() - date
    if abs(delta) > datetime.timedelta(1, 0, 0):
        # far in the past or future, display the date
        return date_day(date)
    future = delta < datetime.timedelta(0, 0, 0)
    delta = abs(delta)
    days = delta.days
    hours = delta.seconds / 3600
    minutes = (delta.seconds - (3600*hours)) / 60
    seconds = delta.seconds % 60
    result = ''
    if future:
        result += 'in '
    if days != 0:
        amount = days
        unit = 'day'
    elif hours != 0:
        amount = hours
        unit = 'hour'
    elif minutes != 0:
        amount = minutes
        unit = 'minute'
    else:
        amount = seconds
        unit = 'second'
    if amount != 1:
        unit += 's'
    result += '%s %s' % (amount, unit)
    if not future:
        result += ' ago'
        return result


def _wrap_with_date_time_title(date, formatted_date):
    elem = ET.Element("span")
    elem.text = formatted_date
    elem.set("title", date_time(date))
    return elem


def approximatedate(date):
    #FIXME: Returns an object instead of a string
    return _wrap_with_date_time_title(date, _approximatedate(date))


def displaydate(date):
    return _wrap_with_date_time_title(date, _displaydate(date))


class Container (object):
    """
    Convert a dict into an object with attributes.
    """
    def __init__(self, _dict=None, **kw):
        if _dict is not None:
            for key, value in _dict.iteritems():
                setattr(self, key, value)
        for key, value in kw.iteritems():
            setattr(self, key, value)

    def __repr__(self):
        out = '{ '
        for key, value in self.__dict__.iteritems():
            if key.startswith('_') or (getattr(self.__dict__[key], '__call__', None) is not None):
                continue
            out += '%r => %r, ' % (key, value)
        out += '}'
        return out


def clean_revid(revid):
    if revid == 'missing':
        return revid
    return sha.new(revid).hexdigest()


def obfuscate(text):
    return ''.join([ '&#%d;' % ord(c) for c in text ])


def trunc(text, limit=10):
    if len(text) <= limit:
        return text
    return text[:limit] + '...'


def to_utf8(s):
    if isinstance(s, unicode):
        return s.encode('utf-8')
    return s


STANDARD_PATTERN = re.compile(r'^(.*?)\s*<(.*?)>\s*$')
EMAIL_PATTERN = re.compile(r'[-\w\d\+_!%\.]+@[-\w\d\+_!%\.]+')

def hide_email(email):
    """
    try to obsure any email address in a bazaar committer's name.
    """
    m = STANDARD_PATTERN.search(email)
    if m is not None:
        name = m.group(1)
        email = m.group(2)
        return name
    m = EMAIL_PATTERN.search(email)
    if m is None:
        # can't find an email address in here
        return email
    username, domain = m.group(0).split('@')
    domains = domain.split('.')
    if len(domains) >= 2:
        return '%s at %s' % (username, domains[-2])
    return '%s at %s' % (username, domains[0])


def triple_factors(min_value=1):
    factors = (1, 3)
    index = 0
    n = 1
    while True:
        if n >= min_value:
            yield n * factors[index]
        index += 1
        if index >= len(factors):
            index = 0
            n *= 10


def scan_range(pos, max, pagesize=1):
    """
    given a position in a maximum range, return a list of negative and positive
    jump factors for an hgweb-style triple-factor geometric scan.

    for example, with pos=20 and max=500, the range would be:
    [ -10, -3, -1, 1, 3, 10, 30, 100, 300 ]

    i admit this is a very strange way of jumping through revisions.  i didn't
    invent it. :)
    """
    out = []
    for n in triple_factors(pagesize + 1):
        if n > max:
            return out
        if pos + n < max:
            out.append(n)
        if pos - n >= 0:
            out.insert(0, -n)


# only do this if unicode turns out to be a problem
#_BADCHARS_RE = re.compile(ur'[\u007f-\uffff]')

# FIXME: get rid of this method; use fixed_width() and avoid XML().
def html_clean(s):
    """
    clean up a string for html display.  expand any tabs, encode any html
    entities, and replace spaces with '&nbsp;'.  this is primarily for use
    in displaying monospace text.
    """
    s = cgi.escape(s.expandtabs())
    s = s.replace(' ', '&nbsp;')
    return s



NONBREAKING_SPACE = u'\N{NO-BREAK SPACE}'

def fixed_width(s):
    """
    expand tabs and turn spaces into "non-breaking spaces", so browsers won't
    chop up the string.
    """
    if not isinstance(s, unicode):
        # this kinda sucks.  file contents are just binary data, and no
        # encoding metadata is stored, so we need to guess.  this is probably
        # okay for most code, but for people using things like KOI-8, this
        # will display gibberish.  we have no way of detecting the correct
        # encoding to use.
        try:
            s = s.decode('utf-8')
        except UnicodeDecodeError:
            s = s.decode('iso-8859-15')
    return s.expandtabs().replace(' ', NONBREAKING_SPACE)


def fake_permissions(kind, executable):
    # fake up unix-style permissions given only a "kind" and executable bit
    if kind == 'directory':
        return 'drwxr-xr-x'
    if executable:
        return '-rwxr-xr-x'
    return '-rw-r--r--'


def if_present(format, value):
    """
    format a value using a format string, if the value exists and is not None.
    """
    if value is None:
        return ''
    return format % value


def b64(s):
    s = base64.encodestring(s).replace('\n', '')
    while (len(s) > 0) and (s[-1] == '='):
        s = s[:-1]
    return s


def uniq(uniqs, s):
    """
    turn a potentially long string into a unique smaller string.
    """
    if s in uniqs:
        return uniqs[s]
    uniqs[type(None)] = next = uniqs.get(type(None), 0) + 1
    x = struct.pack('>I', next)
    while (len(x) > 1) and (x[0] == '\x00'):
        x = x[1:]
    uniqs[s] = b64(x)
    return uniqs[s]


KILO = 1024
MEG = 1024 * KILO
GIG = 1024 * MEG
P95_MEG = int(0.9 * MEG)
P95_GIG = int(0.9 * GIG)

def human_size(size, min_divisor=0):
    size = int(size)
    if (size == 0) and (min_divisor == 0):
        return '0'
    if (size < 512) and (min_divisor == 0):
        return str(size)

    if (size >= P95_GIG) or (min_divisor >= GIG):
        divisor = GIG
    elif (size >= P95_MEG) or (min_divisor >= MEG):
        divisor = MEG
    else:
        divisor = KILO

    dot = size % divisor
    base = size - dot
    dot = dot * 10 // divisor
    base //= divisor
    if dot >= 10:
        base += 1
        dot -= 10

    out = str(base)
    if (base < 100) and (dot != 0):
        out += '.%d' % (dot,)
    if divisor == KILO:
        out += 'K'
    elif divisor == MEG:
        out += 'M'
    elif divisor == GIG:
        out += 'G'
    return out


def fill_in_navigation(navigation):
    """
    given a navigation block (used by the template for the page header), fill
    in useful calculated values.
    """
    if navigation.revid in navigation.revid_list: # XXX is this always true?
        navigation.position = navigation.revid_list.index(navigation.revid)
    else:
        navigation.position = 0
    navigation.count = len(navigation.revid_list)
    navigation.page_position = navigation.position // navigation.pagesize + 1
    navigation.page_count = (len(navigation.revid_list) + (navigation.pagesize - 1)) // navigation.pagesize

    def get_offset(offset):
        if (navigation.position + offset < 0) or (navigation.position + offset > navigation.count - 1):
            return None
        return navigation.revid_list[navigation.position + offset]

    navigation.prev_page_revid = get_offset(-1 * navigation.pagesize)
    navigation.next_page_revid = get_offset(1 * navigation.pagesize)
    prev_page_revno = navigation.branch.history.get_revno(
            navigation.prev_page_revid)
    next_page_revno = navigation.branch.history.get_revno(
            navigation.next_page_revid)
    start_revno = navigation.branch._history.get_revno(navigation.start_revid)

    params = { 'filter_file_id': navigation.filter_file_id }
    if getattr(navigation, 'query', None) is not None:
        params['q'] = navigation.query

    if getattr(navigation, 'start_revid', None) is not None:
        params['start_revid'] = start_revno

    if navigation.prev_page_revid:
        navigation.prev_page_url = navigation.branch.context_url(
            [navigation.scan_url, prev_page_revno], **params)
    if navigation.next_page_revid:
        navigation.next_page_url = navigation.branch.context_url(
            [navigation.scan_url, next_page_revno], **params)


def log_exception(log):
    for line in ''.join(traceback.format_exception(*sys.exc_info())).split('\n'):
        log.debug(line)


def decorator(unbound):
    def new_decorator(f):
        g = unbound(f)
        g.__name__ = f.__name__
        g.__doc__ = f.__doc__
        g.__dict__.update(f.__dict__)
        return g
    new_decorator.__name__ = unbound.__name__
    new_decorator.__doc__ = unbound.__doc__
    new_decorator.__dict__.update(unbound.__dict__)
    return new_decorator


# common threading-lock decorator
def with_lock(lockname, debug_name=None):
    if debug_name is None:
        debug_name = lockname
    @decorator
    def _decorator(unbound):
        def locked(self, *args, **kw):
            getattr(self, lockname).acquire()
            try:
                return unbound(self, *args, **kw)
            finally:
                getattr(self, lockname).release()
        return locked
    return _decorator


@decorator
def strip_whitespace(f):
    def _f(*a, **kw):
        out = f(*a, **kw)
        orig_len = len(out)
        out = re.sub(r'\n\s+', '\n', out)
        out = re.sub(r'[ \t]+', ' ', out)
        out = re.sub(r'\s+\n', '\n', out)
        new_len = len(out)
        log.debug('Saved %sB (%d%%) by stripping whitespace.',
                  human_size(orig_len - new_len),
                  round(100.0 - float(new_len) * 100.0 / float(orig_len)))
        return out
    return _f


@decorator
def lsprof(f):
    def _f(*a, **kw):
        from loggerhead.lsprof import profile
        import cPickle
        z = time.time()
        ret, stats = profile(f, *a, **kw)
        log.debug('Finished profiled %s in %d msec.' % (f.__name__, int((time.time() - z) * 1000)))
        stats.sort()
        stats.freeze()
        now = time.time()
        msec = int(now * 1000) % 1000
        timestr = time.strftime('%Y%m%d%H%M%S', time.localtime(now)) + ('%03d' % msec)
        filename = f.__name__ + '-' + timestr + '.lsprof'
        cPickle.dump(stats, open(filename, 'w'), 2)
        return ret
    return _f


# just thinking out loud here...
#
# so, when browsing around, there are 5 pieces of context, most optional:
#     - current revid
#         current location along the navigation path (while browsing)
#     - starting revid (start_revid)
#         the current beginning of navigation (navigation continues back to
#         the original revision) -- this defines an 'alternate mainline'
#         when the user navigates into a branch.
#     - file_id
#         the file being looked at
#     - filter_file_id
#         if navigating the revisions that touched a file
#     - q (query)
#         if navigating the revisions that matched a search query
#     - remember
#         a previous revision to remember for future comparisons
#
# current revid is given on the url path.  the rest are optional components
# in the url params.
#
# other transient things can be set:
#     - compare_revid
#         to compare one revision to another, on /revision only
#     - sort
#         for re-ordering an existing page by different sort

t_context = threading.local()
_valid = ('start_revid', 'file_id', 'filter_file_id', 'q', 'remember',
          'compare_revid', 'sort')


def set_context(map):
    t_context.map = dict((k, v) for (k, v) in map.iteritems() if k in _valid)


def get_context(**overrides):
    """
    Soon to be deprecated.


    return a context map that may be overriden by specific values passed in,
    but only contains keys from the list of valid context keys.

    if 'clear' is set, only the 'remember' context value will be added, and
    all other context will be omitted.
    """
    map = dict()
    if overrides.get('clear', False):
        map['remember'] = t_context.map.get('remember', None)
    else:
        map.update(t_context.map)
    overrides = dict((k, v) for (k, v) in overrides.iteritems() if k in _valid)
    map.update(overrides)
    return map
