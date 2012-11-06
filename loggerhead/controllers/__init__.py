#
# Copyright (C) 2008  Canonical Ltd.
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
# Foundation, Inc., 51 Franklin Street, Suite 500, Boston, MA 02110-1335  USA

import bzrlib.errors
import simplejson
import time

from paste.httpexceptions import HTTPNotFound, HTTPSeeOther
from paste.request import path_info_pop, parse_querystring

from loggerhead import util
from loggerhead.templatefunctions import templatefunctions
from loggerhead.zptsupport import load_template


class BufferingWriter(object):

    def __init__(self, writefunc, buf_limit):
        self.bytes = 0
        self.buf = []
        self.buflen = 0
        self.writefunc = writefunc
        self.buf_limit = buf_limit

    def flush(self):
        self.writefunc(''.join(self.buf))
        self.buf = []
        self.buflen = 0

    def write(self, data):
        self.buf.append(data)
        self.buflen += len(data)
        self.bytes += len(data)
        if self.buflen > self.buf_limit:
            self.flush()


class TemplatedBranchView(object):

    template_path = None
    supports_json = False

    def __init__(self, branch, history_callable):
        self._branch = branch
        self._history_callable = history_callable
        self.__history = None
        self.log = branch.log

    @property
    def _history(self):
        if self.__history is not None:
            return self.__history
        self.__history = self._history_callable()
        return self.__history

    def parse_args(self, environ):
        kwargs = dict(parse_querystring(environ))
        util.set_context(kwargs)
        args = []
        while True:
            arg = path_info_pop(environ)
            if arg is None:
                break
            args.append(arg)

        path = None
        if len(args) > 1:
            path = unicode('/'.join(args[1:]), 'utf-8')
        self.args = args
        self.kwargs = kwargs
        return path

    def add_template_values(self, values):
        values.update({
            'static_url': self._branch.static_url,
            'branch': self._branch,
            'util': util,
            'url': self._branch.context_url,
        })
        values.update(templatefunctions)

    def __call__(self, environ, start_response):
        z = time.time()
        if environ.get('loggerhead.as_json') and not self.supports_json:
            raise HTTPNotFound
        path = self.parse_args(environ)
        headers = {}
        values = self.get_values(path, self.kwargs, headers)

        self.log.info('Getting information for %s: %.3f secs' % (
            self.__class__.__name__, time.time() - z))
        if environ.get('loggerhead.as_json'):
            headers['Content-Type'] = 'application/json'
        elif 'Content-Type' not in headers:
            headers['Content-Type'] = 'text/html'
        writer = start_response("200 OK", headers.items())
        if environ.get('REQUEST_METHOD') == 'HEAD':
            # No content for a HEAD request
            return []
        z = time.time()
        w = BufferingWriter(writer, 8192)
        if environ.get('loggerhead.as_json'):
            w.write(simplejson.dumps(values,
                default=util.convert_to_json_ready))
        else:
            self.add_template_values(values)
            template = load_template(self.template_path)
            template.expand_into(w, **values)
        w.flush()
        self.log.info(
            'Rendering %s: %.3f secs, %s bytes' % (
                self.__class__.__name__, time.time() - z, w.bytes))
        return []

    def get_revid(self):
        h = self._history
        if h is None:
            return None
        if len(self.args) > 0 and self.args != ['']:
            try:
                revid = h.fix_revid(self.args[0])
            except bzrlib.errors.NoSuchRevision:
                raise HTTPNotFound;
        else:
            revid = h.last_revid
        return revid
