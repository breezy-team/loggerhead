#
# Copyright (C) 2006  Robey Pointer <robey@lag.net>
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
import re
import sha


def timespan(delta):
    if delta.days > 730:
        # good grief!
        return '%d years' % (int(delta.days // 365.25),)
    if delta.days >= 3:
        return '%d days' % delta.days
    seg = []
    if delta.days > 0:
        if delta.days == 1:
            seg.append('1 day')
        else:
            seg.append('%d days' % delta.days)
    hrs = delta.seconds // 3600
    mins = (delta.seconds % 3600) // 60
    if hrs > 0:
        if hrs == 1:
            seg.append('1 hour')
        else:
            seg.append('%d hours' % hrs)
    if delta.days == 0:
        if mins > 0:
            if mins == 1:
                seg.append('1 minute')
            else:
                seg.append('%d minutes' % mins)
        elif hrs == 0:
            seg.append('less than a minute')
    return ', '.join(seg)


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

    
def triple_factors():
    factors = (1, 3)
    index = 0
    n = 1
    while True:
        if n >= 10:
            yield n * factors[index]
        index += 1
        if index >= len(factors):
            index = 0
            n *= 10


def scan_range(pos, max):
    """
    given a position in a maximum range, return a list of negative and positive
    jump factors for an hgweb-style triple-factor geometric scan.
    
    for example, with pos=20 and max=500, the range would be:
    [ -10, -3, -1, 1, 3, 10, 30, 100, 300 ]
    
    i admit this is a very strange way of jumping through revisions.  i didn't
    invent it. :)
    """
    out = []
    for n in triple_factors():
        if n > max:
            return out
        if pos + n < max:
            out.append(n)
        if pos - n >= 0:
            out.insert(0, -n)


def html_clean(s):
    """
    clean up a string for html display.  expand any tabs, encode any html
    entities, and replace spaces with '&nbsp;'.  this is primarily for use
    in displaying monospace text.
    """
    s = cgi.escape(s.expandtabs()).replace(' ', '&nbsp;')
    return s


def fake_permissions(kind, executable):
    # fake up unix-style permissions given only a "kind" and executable bit
    if kind == 'directory':
        return 'drwxr-xr-x'
    if executable:
        return '-rwxr-xr-x'
    return '-rw-r--r--'

        
