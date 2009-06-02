# Copyright 2009 Canonical Ltd
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

version_info = (1, 11, 0)

if __name__ == 'bzrlib.plugins.loggerhead':
    import bzrlib
    from bzrlib.api import require_any_api

    require_any_api(bzrlib, [(1, 11, 0), (1, 13, 0), (1, 15, 0)])

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
    HELP = ('Loggerhead web-based code viewer and server. (default port: %d)' %
            (DEFAULT_PORT,))

    def serve_http(transport, host=None, port=None, inet=None):
        # loggerhead internal code will try to 'import loggerhead', so
        # let's put it on the path if we can't find it in the existing path
        try:
            import loggerhead
        except ImportError:
            import os.path, sys
            sys.path.append(os.path.dirname(__file__))

        from loggerhead.apps.transport import BranchesFromTransportRoot
        from loggerhead.config import LoggerheadConfig
        from paste.httpexceptions import HTTPExceptionHandler
        from paste.httpserver import serve
        if host is None:
            host = DEFAULT_HOST
        if port is None:
            port = DEFAULT_PORT
        argv = ['--host', host, '--port', str(port), transport.base]
        config = LoggerheadConfig(argv)
        app = BranchesFromTransportRoot(transport, config)
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
                    path = kw.get('directory', '.')
                    port = kw.get('port', DEFAULT_PORT)
                    # port might be an int already...
                    if isinstance(port, basestring) and ':' in port:
                        host, port = port.split(':')
                    else:
                        host = DEFAULT_HOST
                    transport = get_transport(path)
                    serve_http(transport, host, port)
                else:
                    super(cmd_serve, self).run(*args, **kw)

        register_command(cmd_serve)
