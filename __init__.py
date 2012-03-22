# Copyright 2009, 2010, 2011 Canonical Ltd
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

import sys

from info import (
    bzr_plugin_version as version_info,
    bzr_compatible_versions,
    )

if __name__ == 'bzrlib.plugins.loggerhead':
    import bzrlib
    from bzrlib.api import require_any_api
    from bzrlib import commands

    require_any_api(bzrlib, bzr_compatible_versions)

    from bzrlib.transport import transport_server_registry

    DEFAULT_HOST = '0.0.0.0'
    DEFAULT_PORT = 8080
    HELP = ('Loggerhead, a web-based code viewer and server. (default port: %d)' %
            (DEFAULT_PORT,))

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
        # TODO: if we supported inet to pass requests in and respond to them,
        #       then it would be easier to test the full stack, but it probably
        #       means routing around paste.httpserver.serve which probably
        #       isn't testing the full stack
        from paste.httpexceptions import HTTPExceptionHandler
        from paste.httpserver import serve

        _ensure_loggerhead_path()

        from loggerhead.apps.http_head import HeadMiddleware
        from loggerhead.apps.transport import BranchesFromTransportRoot
        from loggerhead.config import LoggerheadConfig
        from loggerhead.main import setup_logging

        if host is None:
            host = DEFAULT_HOST
        if port is None:
            port = DEFAULT_PORT
        argv = ['--host', host, '--port', str(port), '--', transport.base]
        if not transport.is_readonly():
            argv.insert(0, '--allow-writes')
        config = LoggerheadConfig(argv)
        setup_logging(config, init_logging=False, log_file=sys.stderr)
        app = BranchesFromTransportRoot(transport.base, config)
        # Bug #758618, HeadMiddleware seems to break HTTPExceptionHandler from
        # actually sending appropriate return codes to the client. Since nobody
        # desperately needs HeadMiddleware right now, just ignoring it.
        # app = HeadMiddleware(app)
        app = HTTPExceptionHandler(app)
        serve(app, host=host, port=port)

    transport_server_registry.register('http', serve_http, help=HELP)

    class cmd_load_test_loggerhead(commands.Command):
        """Run a load test against a live loggerhead instance.

        Pass in the name of a script file to run. See loggerhead/load_test.py
        for a description of the file format.
        """

        takes_args = ["filename"]

        def run(self, filename):
            from bzrlib.plugins.loggerhead.loggerhead import load_test
            script = load_test.run_script(filename)
            for thread_id in sorted(script._threads):
                worker = script._threads[thread_id][0]
                for url, success, time in worker.stats:
                    self.outf.write(' %5.3fs %s %s\n'
                                    % (time, str(success)[0], url))

    commands.register_command(cmd_load_test_loggerhead)

    def load_tests(standard_tests, module, loader):
        _ensure_loggerhead_path()
        standard_tests.addTests(loader.loadTestsFromModuleNames(
            ['bzrlib.plugins.loggerhead.loggerhead.tests']))
        return standard_tests
