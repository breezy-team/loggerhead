# Copyright (C) 2008-2011 Canonical Ltd.
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
#
"""Serve branches at urls that mimic a transport's file system layout."""

import threading

from bzrlib import branch, errors, lru_cache, urlutils
from bzrlib.config import LocationConfig
from bzrlib.smart import request
from bzrlib.transport import get_transport
from bzrlib.transport.http import wsgi

from paste.request import path_info_pop
from paste import httpexceptions
from paste import urlparser

from loggerhead import util
from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.apps import favicon_app, robots_app, static_app
from loggerhead.controllers.directory_ui import DirectoryUI

# TODO: Use bzrlib.ui.bool_from_string(), added in bzr 1.18
_bools = {
    'yes': True, 'no': False,
    'on': True, 'off': False,
    '1': True, '0': False,
    'true': True, 'false': False,
    }

class BranchesFromTransportServer(object):

    def __init__(self, transport, root, name=None):
        self.transport = transport
        self.root = root
        self.name = name
        self._config = root._config

    def app_for_branch(self, branch):
        if not self.name:
            name = branch._get_nick(local=True)
            is_root = True
        else:
            name = self.name
            is_root = False
        branch_app = BranchWSGIApp(
            branch,
            name,
            {'cachepath': self._config.SQL_DIR},
            self.root.graph_cache,
            is_root=is_root,
            use_cdn=self._config.get_option('use_cdn'),
            )
        return branch_app.app

    def app_for_non_branch(self, environ):
        segment = path_info_pop(environ)
        if segment is None:
            raise httpexceptions.HTTPMovedPermanently.relative_redirect(
                environ['SCRIPT_NAME'] + '/', environ)
        elif segment == '':
            if self.name:
                name = self.name
            else:
                name = '/'
            return DirectoryUI(
                environ['loggerhead.static.url'], self.transport, name)
        else:
            new_transport = self.transport.clone(segment)
            if self.name:
                new_name = urlutils.join(self.name, segment)
            else:
                new_name = '/' + segment
            return BranchesFromTransportServer(new_transport, self.root, new_name)

    def app_for_bazaar_data(self, relpath):
        if relpath == '/.bzr/smart':
            root_transport = get_transport_for_thread(self.root.base)
            wsgi_app = wsgi.SmartWSGIApp(root_transport)
            return wsgi.RelpathSetter(wsgi_app, '', 'loggerhead.path_info')
        else:
            # TODO: Use something here that uses the transport API
            # rather than relying on the local filesystem API.
            base = self.transport.base
            try:
                path = util.local_path_from_url(base)
            except errors.InvalidURL:
                raise httpexceptions.HTTPNotFound()
            else:
                return urlparser.make_static(None, path)

    def check_serveable(self, config):
        value = config.get_user_option('http_serve')
        if value is None:
            return
        elif not _bools.get(value.lower(), True):
            raise httpexceptions.HTTPNotFound()

    def __call__(self, environ, start_response):
        path = environ['PATH_INFO']
        try:
            b = branch.Branch.open_from_transport(self.transport)
        except errors.NotBranchError:
            if path.startswith('/.bzr'):
                self.check_serveable(LocationConfig(self.transport.base))
                return self.app_for_bazaar_data(path)(environ, start_response)
            if not self.transport.listable() or not self.transport.has('.'):
                raise httpexceptions.HTTPNotFound()
            return self.app_for_non_branch(environ)(environ, start_response)
        else:
            self.check_serveable(b.get_config())
            if path.startswith('/.bzr'):
                return self.app_for_bazaar_data(path)(environ, start_response)
            else:
                return self.app_for_branch(b)(environ, start_response)


_transport_store = threading.local()

def get_transport_for_thread(base):
    thread_transports = getattr(_transport_store, 'transports', None)
    if thread_transports is None:
        thread_transports = _transport_store.transports = {}
    if base in thread_transports:
        return thread_transports[base]
    transport = get_transport(base)
    thread_transports[base] = transport
    return transport


class BranchesFromTransportRoot(object):

    def __init__(self, base, config):
        self.graph_cache = lru_cache.LRUCache(10)
        self.base = base
        self._config = config

    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        environ['loggerhead.path_info'] = environ['PATH_INFO']
        if environ['PATH_INFO'].startswith('/static/'):
            segment = path_info_pop(environ)
            assert segment == 'static'
            return static_app(environ, start_response)
        elif environ['PATH_INFO'] == '/favicon.ico':
            return favicon_app(environ, start_response)
        elif environ['PATH_INFO'] == '/robots.txt':
            return robots_app(environ, start_response)
        else:
            transport = get_transport_for_thread(self.base)
            return BranchesFromTransportServer(
                transport, self)(environ, start_response)


class UserBranchesFromTransportRoot(object):

    def __init__(self, base, config):
        self.graph_cache = lru_cache.LRUCache(10)
        self.base = base
        self._config = config
        self.trunk_dir = config.get_option('trunk_dir')

    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        environ['loggerhead.path_info'] = environ['PATH_INFO']
        path_info = environ['PATH_INFO']
        if path_info.startswith('/static/'):
            segment = path_info_pop(environ)
            assert segment == 'static'
            return static_app(environ, start_response)
        elif path_info == '/favicon.ico':
            return favicon_app(environ, start_response)
        elif environ['PATH_INFO'] == '/robots.txt':
            return robots_app(environ, start_response)
        else:
            transport = get_transport_for_thread(self.base)
            # segments starting with ~ are user branches
            if path_info.startswith('/~'):
                segment = path_info_pop(environ)
                return BranchesFromTransportServer(
                    transport.clone(segment[1:]), self, segment)(
                    environ, start_response)
            else:
                return BranchesFromTransportServer(
                    transport.clone(self.trunk_dir), self)(
                    environ, start_response)
