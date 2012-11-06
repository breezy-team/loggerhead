#
# Copyright (C) 2008, 2009 Canonical Ltd
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

"""Search for branches underneath a directory and serve them all."""

import logging
import os
import sys

from bzrlib.plugin import load_plugins

from paste import httpserver
from paste.httpexceptions import HTTPExceptionHandler, HTTPInternalServerError
from paste.translogger import TransLogger

from loggerhead import __version__
from loggerhead.apps.transport import (
    BranchesFromTransportRoot, UserBranchesFromTransportRoot)
from loggerhead.config import LoggerheadConfig
from loggerhead.util import Reloader
from loggerhead.apps.error import ErrorHandlerApp


def get_config_and_path(args):
    config = LoggerheadConfig(args)

    if config.get_option('show_version'):
        print "loggerhead %s" % (__version__,)
        sys.exit(0)

    if config.arg_count > 1:
        config.print_help()
        sys.exit(1)
    elif config.arg_count == 1:
        base = config.get_arg(0)
    else:
        base = '.'

    if not config.get_option('allow_writes'):
        base = 'readonly+' + base

    return config, base


def setup_logging(config, init_logging=True, log_file=None):
    log_level = config.get_log_level()
    if init_logging:
        logging.basicConfig()
        if log_level is not None:
            logging.getLogger('').setLevel(log_level)
    logger = logging.getLogger('loggerhead')
    if log_level is not None:
        logger.setLevel(log_level)
    if log_file is not None:
        handler = logging.StreamHandler(log_file)
    else:
        if config.get_option('log_folder'):
            logfile_path = os.path.join(
                config.get_option('log_folder'), 'serve-branches.log')
        else:
            logfile_path = 'serve-branches.log'
        handler = logging.FileHandler(logfile_path, 'a')
        formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)s:'
                                      ' %(message)s')
        handler.setFormatter(formatter)
    # We set the handler to accept all messages, the *logger* won't emit them
    # if it is configured to suppress it
    handler.setLevel(logging.DEBUG)
    logger.addHandler(handler)
    def _restrict_logging(logger_name):
        logger = logging.getLogger(logger_name)
        if logger.getEffectiveLevel() < logging.INFO:
            logger.setLevel(logging.INFO)
    # simpleTAL is *very* verbose in DEBUG mode, which is otherwise the
    # default. So quiet it up a bit.
    _restrict_logging('simpleTAL')
    _restrict_logging('simpleTALES')
    return logger


def make_app_for_config_and_path(config, base):
    if config.get_option('trunk_dir') and not config.get_option('user_dirs'):
        print "--trunk-dir is only valid with --user-dirs"
        sys.exit(1)

    if config.get_option('reload'):
        if Reloader.is_installed():
            Reloader.install()
        else:
            return Reloader.restart_with_reloader()

    if config.get_option('user_dirs'):
        if not config.get_option('trunk_dir'):
            print "You didn't specify a directory for the trunk directories."
            sys.exit(1)
        app = UserBranchesFromTransportRoot(base, config)
    else:
        app = BranchesFromTransportRoot(base, config)

    setup_logging(config)

    if config.get_option('profile'):
        from loggerhead.middleware.profile import LSProfMiddleware
        app = LSProfMiddleware(app)
    if config.get_option('memory_profile'):
        from dozer import Dozer
        app = Dozer(app)

    if not config.get_option('user_prefix'):
        prefix = '/'
    else:
        prefix = config.get_option('user_prefix')
        if not prefix.startswith('/'):
            prefix = '/' + prefix

    try:
        from paste.deploy.config import PrefixMiddleware
    except ImportError:
        cant_proxy_correctly_message = (
            'Unsupported configuration: PasteDeploy not available, but '
            'loggerhead appears to be behind a proxy.')
        def check_not_proxied(app):
            def wrapped(environ, start_response):
                if 'HTTP_X_FORWARDED_SERVER' in environ:
                    exc = HTTPInternalServerError()
                    exc.explanation = cant_proxy_correctly_message
                    raise exc
                return app(environ, start_response)
            return wrapped
        app = check_not_proxied(app)
    else:
        app = PrefixMiddleware(app, prefix=prefix)

    app = HTTPExceptionHandler(app)
    app = ErrorHandlerApp(app)
    app = TransLogger(app, logger=logging.getLogger('loggerhead'))

    return app


def main(args):
    load_plugins()

    config, path = get_config_and_path(args)

    app = make_app_for_config_and_path(config, path)

    if not config.get_option('user_port'):
        port = '8080'
    else:
        port = config.get_option('user_port')

    if not config.get_option('user_host'):
        host = '0.0.0.0'
    else:
        host = config.get_option('user_host')

    if not config.get_option('protocol'):
        protocol = 'http'
    else:
        protocol = config.get_option('protocol')

    if protocol == 'http':
        httpserver.serve(app, host=host, port=port)
    else:
        if protocol == 'fcgi':
            from flup.server.fcgi import WSGIServer
        elif protocol == 'scgi':
            from flup.server.scgi import WSGIServer
        elif protocol == 'ajp':
            from flup.server.ajp import WSGIServer
        else:
            print 'Unknown protocol: %s.' % (protocol)
            sys.exit(1)
        WSGIServer(app, bindAddress=(host, int(port))).run()
