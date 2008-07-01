# A server that recreates (modulo cherrypy bugs :) the url parsing
# from the old, loggerhead.conf approach.

# It's all a bit horrible really.

import logging
import os
import posixpath

import bzrlib.lru_cache

from configobj import ConfigObj

from paste.request import path_info_pop
from paste import httpexceptions
from paste.wsgiwrappers import WSGIResponse

from loggerhead.apps.branch import BranchWSGIApp
from loggerhead.apps import favicon_app, static_app
from loggerhead.templatefunctions import templatefunctions
from loggerhead.zptsupport import load_template
from loggerhead import util

log = logging.getLogger("loggerhead.controllers")

from loggerhead.history import is_branch

class Project(object):
    def __init__(self, name, config, root_config, graph_cache):
        self.name = name
        self.friendly_name = config.get('name', name)
        self.description = config.get('description', '')
        self.long_description = config.get('long_description', '')
        self._config = config
        self._root_config = root_config
        self.graph_cache = graph_cache

        self.view_names = []
        self.view_data_by_name = {}
        for view_name in config.sections:
            log.debug('Configuring (project %s) branch %s...', name, view_name)
            self._add_view(
                view_name, config[view_name], config[view_name].get('folder'))

        self._auto_folder = config.get('auto_publish_folder', None)
        self._auto_list = []
        if self._auto_folder is not None:
            self._recheck_auto_folders()

    def _recheck_auto_folders(self):
        if self._auto_folder is None:
            return
        auto_list = []
        # scan a folder for bazaar branches, and add them automatically
        for path, folders, filenames in os.walk(self._auto_folder):
            for folder in folders:
                folder = os.path.join(path, folder)
                if is_branch(folder):
                    auto_list.append(folder)
        auto_list.sort()
        if auto_list == self._auto_list:
            # nothing has changed; do nothing.
            return

        # rebuild views:
        self.view_names = []
        log.debug('Rescanning auto-folder for project %s ...', self.name)
        for folder in auto_list:
            view_name = os.path.basename(folder)
            log.debug('Auto-configuring (project %s) branch %s...', self.name, view_name)
            self._add_view(view_name, ConfigObj(), folder)
        self._auto_list = auto_list

    def _get_branch_url(self, view, view_config, folder):
        url = view_config.get('url', None)
        if url is not None:
            return url
        url = self._config.get('url_prefix', None)
        if url is not None:
            return posixpath.join(url, folder) + '/'
        return None

    def _get_description(self, view, view_config, history):
        description = view_config.get('description', None)
        if description is not None:
            return description
        description = history._branch.get_config().get_user_option('description')
        return description

    def _add_view(self, view_name, view_config, folder):
        b = bzrlib.branch.Branch.open(folder)
        view = BranchWSGIApp(b, view_name, view_config, self.graph_cache)
        b.lock_read()
        try:
            history = view.get_history()
            friendly_name = view_config.get('branch_name', None)
            if friendly_name is None:
                friendly_name = history.get_config().get_nickname()
                if friendly_name is None:
                    friendly_name = view_name
            self.view_data_by_name[view_name] = {
                'branch_path': folder,
                'args': (view_name, view_config, self.graph_cache),
                'description': self._get_description(view, view_config, history),
                '_src_folder': folder,
                '_view_config': view_config,
                'friendly_name': friendly_name,
                'name': view_name,
                }
            branch_url = self._get_branch_url(view, view_config, view_name)
            if branch_url is not None:
                self.view_data_by_name[view_name]['branch_url'] = branch_url
            self.view_names.append(view_name)
        finally:
            b.unlock()

    def view_named(self, name):
        view_data = self.view_data_by_name.get(name)
        if view_data is None:
            return None
        view_data = view_data.copy()
        branch_path = view_data.pop('branch_path')
        args = view_data.pop('args')
        b = bzrlib.branch.Branch.open(branch_path)
        b.lock_read()
        view = BranchWSGIApp(b, *args)
        for k in view_data:
            setattr(view, k, view_data[k])
        return view

    def call(self, environ, start_response):
        segment = path_info_pop(environ)
        if not segment:
            raise httpexceptions.HTTPNotFound()
        else:
            view = self.view_named(segment)
            if view is None:
                raise httpexceptions.HTTPNotFound()
            try:
                return view.app(environ, start_response)
            finally:
                view.branch.unlock()


class Root(object):

    def __init__(self, config):
        self.projects = []
        self.config = config
        self.projects_by_name = {}
        graph_cache = bzrlib.lru_cache.LRUCache()
        for project_name in self.config.sections:
            project = Project(
                project_name, self.config[project_name], self.config, graph_cache)
            self.projects.append(project)
            self.projects_by_name[project_name] = project

    def browse(self, response):
        for p in self.projects:
            p._recheck_auto_folders()
        class branch(object):
            @staticmethod
            def static_url(path):
                return self._static_url_base + path
        views_by_project = {}
        all_views = []
        try:
            for p in self.projects:
                views_by_project[p] = []
                for vn in p.view_names:
                    v = p.view_named(vn)
                    all_views.append(v)
                    views_by_project[p].append(v)
            vals = {
                'projects': self.projects,
                'util': util,
                'title': self.config.get('title', None),
                'branch': branch,
                'views_by_project': views_by_project,
            }
            vals.update(templatefunctions)
            response.headers['Content-Type'] = 'text/html'
            template = load_template('loggerhead.templates.browse')
            template.expand_into(response, **vals)
        finally:
            for v in all_views:
                v.branch.unlock()

    def __call__(self, environ, start_response):
        self._static_url_base = environ['loggerhead.static.url'] = environ['SCRIPT_NAME']
        segment = path_info_pop(environ)
        if segment is None:
            raise httpexceptions.HTTPMovedPermanently(
                environ['SCRIPT_NAME'] + '/')
        elif segment == '':
            response = WSGIResponse()
            self.browse(response)
            return response(environ, start_response)
        elif segment == 'static':
            return static_app(environ, start_response)
        elif segment == 'favicon.ico':
            return favicon_app(environ, start_response)
        else:
            project = self.projects_by_name.get(segment)
            if project is None:
                raise httpexceptions.HTTPNotFound()
            return project.call(environ, start_response)
