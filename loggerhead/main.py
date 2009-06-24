#!/usr/bin/env python
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

"""Search for branches underneath a directory and serve them all."""

import logging
import os
import sys

from bzrlib.plugin import load_plugins
from bzrlib.transport import get_transport

from paste import httpserver
from paste.httpexceptions import HTTPExceptionHandler, HTTPInternalServerError
from paste.translogger import TransLogger

from loggerhead import __version__
from loggerhead.apps.transport import (
    BranchesFromTransportRoot, UserBranchesFromTransportRoot)
from loggerhead.config import LoggerheadConfig
from loggerhead.util import Reloader
from loggerhead.apps.error import ErrorHandlerApp


def main(args):
    config = LoggerheadConfig()

    if config.get_option('show_version'):
        print "loggerhead %s" % __version__
        sys.exit(0)

    if config.arg_count > 1:
        config.print_help()
        sys.exit(1)
    elif config.arg_count == 1:
        path = config.get_arg(0)
    else:
        path = '.'

    load_plugins()

    if config.get_option('allow_writes'):
        transport = get_transport(path)
    else:
        transport = get_transport('readonly+' + path)

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
        app = UserBranchesFromTransportRoot(transport, config)
    else:
        app = BranchesFromTransportRoot(transport, config)

    # setup_logging()
    logging.basicConfig()
    logging.getLogger('').setLevel(logging.DEBUG)
    logger = getattr(app, 'log', logging.getLogger('loggerhead'))
    if config.get_option('log_folder'):
        logfile_path = os.path.join(
            config.get_option('log_folder'), 'serve-branches.log')
    else:
        logfile_path = 'serve-branches.log'
    logfile = logging.FileHandler(logfile_path, 'a')
    formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(name)s:'
                                  ' %(message)s')
    logfile.setFormatter(formatter)
    logfile.setLevel(logging.DEBUG)
    logger.addHandler(logfile)

    # setup_logging() #end

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
    app = TransLogger(app, logger=logger)

    if not config.get_option('user_port'):
        port = '8080'
    else:
        port = config.get_option('user_port')

    if not config.get_option('user_host'):
        host = '0.0.0.0'
    else:
        host = config.get_option('user_host')

    httpserver.serve(app, host=host, port=port)