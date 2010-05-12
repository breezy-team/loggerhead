# Copyright 2009, 2010 Canonical Ltd
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


# This file allows loggerhead to be treated as a plugin for bzr.
#
# XXX: Because loggerhead already contains a loggerhead directory, much of the
# code is going to appear loaded at bzrlib.plugins.loggerhead.loggerhead.
# This seems like the easiest thing, because bzrlib wants the top-level plugin
# directory to be the module, but when it's used as a library people expect
# the source directory to contain a directory called loggerhead.  -- mbp
# 20090123

"""Loggerhead web viewer for Bazaar branches.

This provides a new option "--http" to the "bzr serve" command, that
starts a web server to browse the contents of a branch.
"""

version_info = (1, 17, 0)

if __name__ == 'bzrlib.plugins.loggerhead':
    import bzrlib
    from bzrlib.api import require_any_api

    require_any_api(bzrlib, [
        (1, 13, 0), (1, 15, 0), (1, 16, 0), (1, 17, 0), (1, 18, 0),
        (2, 0, 0), (2, 1, 0), (2, 2, 0)])

    # NB: Normally plugins should lazily load almost everything, but this
    # seems reasonable to have in-line here: bzrlib.commands and options are
    # normally loaded, and the rest of loggerhead won't be loaded until serve
    # --http is run.

    # transport_server_registry was added in bzr 1.16. When we drop support for
    # older releases, we can remove the code to override cmd_serve.

    try:
        from bzrlib.transport import transport_server_registry
    except ImportError:
        transport_server_registry = None

    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 8080
    HELP = ('Loggerhead, a web-based code viewer and server. (default port: %d)' %
            (DEFAULT_PORT,))

    def setup_logging(config):
        import logging
        import sys

        logger = logging.getLogger('loggerhead')
        log_level = config.get_log_level()
        if log_level is not None:
            logger.setLevel(log_level)
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.DEBUG)
        logger.addHandler(handler)
        logging.getLogger('simpleTAL').addHandler(handler)
        logging.getLogger('simpleTALES').addHandler(handler)
        def _restrict_logging(logger_name):
            logger = logging.getLogger(logger_name)
            if logger.getEffectiveLevel() < logging.INFO:
                logger.setLevel(logging.INFO)
        # simpleTAL is *very* verbose in DEBUG mode, which is otherwise the
        # default. So quiet it up a bit.
        _restrict_logging('simpleTAL')
        _restrict_logging('simpleTALES')




    def _ensure_loggerhead_path():
        """Ensure that you can 'import loggerhead' and get the root."""
        # loggerhead internal code will try to 'import loggerhead', so
        # let's put it on the path if we can't find it in the existing path
        try:
            import loggerhead.apps.transport
        except ImportError:
            import os.path, sys
            sys.path.append(os.path.dirname(__file__))

    def serve_http(transport, host=None, port=None, inet=None):
        from paste.httpexceptions import HTTPExceptionHandler
        from paste.httpserver import serve

        _ensure_loggerhead_path()

        from loggerhead.apps.transport import BranchesFromTransportRoot
        from loggerhead.config import LoggerheadConfig

        if host is None:
            host = DEFAULT_HOST
        if port is None:
            port = DEFAULT_PORT
        argv = ['--host', host, '--port', str(port), '--', transport.base]
        if not transport.is_readonly():
            argv.insert(0, '--allow-writes')
        config = LoggerheadConfig(argv)
        setup_logging(config)
        app = BranchesFromTransportRoot(transport.base, config)
        app = HTTPExceptionHandler(app)
        serve(app, host=host, port=port)

    if transport_server_registry is not None:
        transport_server_registry.register('http', serve_http, help=HELP)
    else:
        import bzrlib.builtins
        from bzrlib.commands import get_cmd_object, register_command
        from bzrlib.option import Option

        _original_command = get_cmd_object('serve')

        class cmd_serve(bzrlib.builtins.cmd_serve):
            __doc__ = _original_command.__doc__

            takes_options = _original_command.takes_options + [
                Option('http', help=HELP)]

            def run(self, *args, **kw):
                if 'http' in kw:
                    from bzrlib.transport import get_transport
                    allow_writes = kw.get('allow_writes', False)
                    path = kw.get('directory', '.')
                    port = kw.get('port', DEFAULT_PORT)
                    # port might be an int already...
                    if isinstance(port, basestring) and ':' in port:
                        host, port = port.split(':')
                    else:
                        host = DEFAULT_HOST
                    if allow_writes:
                        transport = get_transport(path)
                    else:
                        transport = get_transport('readonly+' + path)
                    serve_http(transport, host, port)
                else:
                    super(cmd_serve, self).run(*args, **kw)

        register_command(cmd_serve)

    def load_tests(standard_tests, module, loader):
        _ensure_loggerhead_path()
        standard_tests.addTests(loader.loadTestsFromModuleNames(
            ['bzrlib.plugins.loggerhead.loggerhead.tests']))
        return standard_tests
