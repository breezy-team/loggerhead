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
    def __init__(self, folder, root):
        self.folder = folder
        self.root = root

    def app_for_branch(self, branch):
        if not self.folder:
            name = os.path.basename(os.path.abspath(self.root.folder))
        else:
            name = self.folder
        branch_app = BranchWSGIApp(
            branch, name, {'cachepath': sql_dir}, self.root.graph_cache)
        return branch_app.app

    def app_for_non_branch(self, environ):
        segment = path_info_pop(environ)
        if segment is None:
            raise httpexceptions.HTTPMovedPermanently(
                environ['SCRIPT_NAME'] + '/')
        elif segment == '':
            return DirectoryUI(environ['loggerhead.static.url'], os.path.join(self.root.folder, self.folder))
        else:
            relpath = os.path.join(self.folder, segment)
            return BranchesFromFileSystemServer(relpath, self.root)

    def __call__(self, environ, start_response):
        path = os.path.join(self.root.folder, self.folder)
        if not os.path.isdir(path):
            raise httpexceptions.HTTPNotFound()
        try:
            b = branch.Branch.open(path)
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
                '', self)(environ, start_response)
