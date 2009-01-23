# Copyright 2009 Canonical Ltd

# This file allows loggerhead to be treated as a plugin for bzr.
#
# XXX: Because loggerhead already contains a loggerhead directory, much of the code
# is going to live in bzrlib.plugins.loggerhead.loggerhead.  But moving it can
# wait.  When we do move it, we may need to guard the plugin code by __name__
# so it can be used as a library from other places.  -- mbp 20090123

"""Loggerhead web viewer for Bazaar branches."""

import bzrlib
from bzrlib.api import require_api

version_info = (1, 11, 0)

require_api(bzrlib, (1, 11, 0))


# TODO: All the following should be in a lazily-loaded module.
#
# TODO: This should provide a new type of server that can be used by bzr
# serve, maybe through a registry, rather than overriding the command.  Though
# maybe we should keep the wrapper to work with older bzr releases, at least
# for a bit.
#
# TODO: If a --port option is given, use that.

import bzrlib.builtins
from bzrlib.commands import get_cmd_object, register_command
from bzrlib.option import Option

_original_command = get_cmd_object('serve')

class cmd_serve(bzrlib.builtins.cmd_serve):
    __doc__ = _original_command.__doc__

    takes_options = _original_command.takes_options + [
        Option('http',
            help='Run an http (Loggerhead) server to browse code.')]

    def run(self, *args, **kw):
        if 'http' in kw:
            # hack around loggerhead expecting to be loaded from the module
            # "loggerhead"
            import os.path, sys
            sys.path.append(os.path.dirname(__file__))
            from loggerhead.apps.filesystem import BranchesFromFileSystemRoot
            from paste.httpexceptions import HTTPExceptionHandler
            from paste.httpserver import serve
            a = HTTPExceptionHandler(BranchesFromFileSystemRoot('.'))
            serve(a, host='0.0.0.0', port='9876')
        else:
            super(cmd_serve, self).run(*args, **kw)

register_command(cmd_serve)
