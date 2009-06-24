# Copyright (C) 2008, 2009 Canonical Ltd.
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
"""Serve branches at urls that mimic a transport's file system layout."""

import threading

from bzrlib import branch, errors, lru_cache, urlutils
from bzrlib.bzrdir import BzrDir
from bzrlib.transport import get_transport
from bzrlib.transport.http import wsgi

from paste.request import path_info_pop
from paste import httpexceptions
from paste import urlparser

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.apps import favicon_app, static_app
from loggerhead.config import LoggerheadConfig
from loggerhead.controllers.directory_ui import DirectoryUI


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
            branch, name,
            {'cachepath': self._config.SQL_DIR},
            self.root.graph_cache, is_root=is_root,
            use_cdn=self._config.get_option('use_cdn'))
        return branch_app.app

    def app_for_non_branch(self, environ):
        segment = path_info_pop(environ)
        if segment is None:
            raise httpexceptions.HTTPMovedPermanently(
                environ['SCRIPT_NAME'] + '/')
        elif segment == '':
            if self.name:
                name = self.name
            else:
                name = '/'
            return DirectoryUI(environ['loggerhead.static.url'],
                               self.transport,
                               name)
        else:
            new_transport = self.transport.clone(segment)
            if self.name:
                new_name = urlutils.join(self.name, segment)
            else:
                new_name = '/' + segment
            return BranchesFromTransportServer(new_transport, self.root, new_name)

    def __call__(self, environ, start_response):
        try:
            b = branch.Branch.open_from_transport(self.transport)
        except errors.NotBranchError:
            if not self.transport.listable() or not self.transport.has('.'):
                raise httpexceptions.HTTPNotFound()
            return self.app_for_non_branch(environ)(environ, start_response)
        else:
            if b.get_config().get_user_option('http_serve') == 'False':
                raise httpexceptions.HTTPNotFound()
            else:
                return self.app_for_branch(b)(environ, start_response)


_transport_store = threading.local()

def get_transport_for_thread(base):
    """ """
    thread_transports = getattr(_transport_store, 'transports', None)
    if thread_transports is None:
        thread_transports = _transport_store.transports = {}
    if base in thread_transports:
        return thread_transports[base]
    transport = get_transport(base)
    return transport


class BranchesFromTransportRoot(object):

    def __init__(self, base, config):
        self.graph_cache = lru_cache.LRUCache(10)
        self.base = base
        self._config = config

    def get_local_path(self):
        """Raise exception if it's not a local path, otherwise return it"""

        # TODO: Use something here that uses the transport API 
        # rather than relying on the local filesystem API.
        try:
            path = urlutils.local_path_from_url(get_transport(self.base).base)
        except errors.InvalidURL, e:
            print e
            raise httpexceptions.HTTPNotFound()
        else:
            return path

    def check_is_a_branch(self, transport, path_info):
        """Check if it's a branch, and that it's allowed to be shown"""
        try:
            bzrdir = BzrDir.open_containing_from_transport(
                       transport.clone(path_info))[0]
            branch = bzrdir.open_branch()
            if branch.get_config().get_user_option('http_serve') == 'False':
                raise httpexceptions.HTTPNotFound()
        except errors.NotBranchError:
            return

    def __call__(self, environ, start_response):
        transport = get_transport_for_thread(self.base)
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        if environ['PATH_INFO'].startswith('/static/'):
            segment = path_info_pop(environ)
            assert segment == 'static'
            return static_app(environ, start_response)
        elif environ['PATH_INFO'] == '/favicon.ico':
            return favicon_app(environ, start_response)
        elif environ['PATH_INFO'].endswith("/.bzr/smart"):
            self.check_is_a_branch(transport, environ['PATH_INFO'])
            # smart_server_app = ...
            return smart_server_app(environ, start_response)
        elif '/.bzr/' in environ['PATH_INFO']:
            self.check_is_a_branch(transport, environ['PATH_INFO'])
            path = self.get_local_path()
            app = urlparser.make_static(None, path)
            return app(environ, start_response)
        else:
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
        path_info = environ['PATH_INFO']
        if path_info.startswith('/static/'):
            segment = path_info_pop(environ)
            assert segment == 'static'
            return static_app(environ, start_response)
        elif path_info == '/favicon.ico':
            return favicon_app(environ, start_response)
        else:
            # segments starting with ~ are user branches
            if path_info.startswith('/~'):
                segment = path_info_pop(environ)
                new_transport = self.transport.clone(segment[1:])
                return BranchesFromTransportServer(
                    new_transport, self, segment)(environ, start_response)
            else:
                new_transport = self.transport.clone(self.trunk_dir)
                return BranchesFromTransportServer(
                    new_transport, self)(environ, start_response)
