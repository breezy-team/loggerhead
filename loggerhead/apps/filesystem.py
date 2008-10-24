"""Serve branches at urls that mimic the file system layout."""

import os
import tempfile

from bzrlib import branch, errors, lru_cache

from paste.request import path_info_pop
from paste import httpexceptions

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.apps import favicon_app, static_app
from loggerhead.controllers.directory_ui import DirectoryUI

sql_dir = tempfile.mkdtemp(prefix='loggerhead-cache-')


class BranchesFromFileSystemServer(object):

    def __init__(self, path, root, name=None):
        self.path = path
        self.root = root
        self.name = name

    def app_for_branch(self, branch):
        if not self.name:
            name = branch.nick
            is_root = True
        else:
            name = self.name
            is_root = False
        branch_app = BranchWSGIApp(
            branch, name, {'cachepath': sql_dir}, self.root.graph_cache,
            is_root=is_root)
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
                               self.path,
                               name)
        else:
            new_path = os.path.join(self.path, segment)
            if self.name:
                new_name = os.path.join(self.name, segment)
            else:
                new_name = '/' + segment
            return BranchesFromFileSystemServer(new_path, self.root, new_name)

    def __call__(self, environ, start_response):
        if not os.path.isdir(self.path):
            raise httpexceptions.HTTPNotFound()
        try:
            b = branch.Branch.open(self.path)
        except errors.NotBranchError:
            return self.app_for_non_branch(environ)(environ, start_response)
        else:
            return self.app_for_branch(b)(environ, start_response)


class BranchesFromFileSystemRoot(object):

    def __init__(self, folder):
        self.graph_cache = lru_cache.LRUCache()
        self.folder = folder

    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        if environ['PATH_INFO'].startswith('/static/'):
            segment = path_info_pop(environ)
            assert segment == 'static'
            return static_app(environ, start_response)
        elif environ['PATH_INFO'] == '/favicon.ico':
            return favicon_app(environ, start_response)
        else:
            return BranchesFromFileSystemServer(
                self.folder, self)(environ, start_response)


class UserBranchesFromFileSystemRoot(object):

    def __init__(self, folder, trunk_dir):
        self.graph_cache = lru_cache.LRUCache()
        self.folder = folder
        self.trunk_dir = trunk_dir

    def __call__(self, environ, start_response):
        environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        path_info= environ['PATH_INFO']
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
                new_path = os.path.join(self.folder, segment[1:])
                return BranchesFromFileSystemServer(
                    new_path, self, segment)(environ, start_response)
            else:
                new_path = os.path.join(self.folder, self.trunk_dir)
                return BranchesFromFileSystemServer(
                    new_path, self)(environ, start_response)
