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
"""Configuration tools for Loggerhead."""

from optparse import OptionParser
import sys
import tempfile

from bzrlib import config

_temporary_sql_dir = None

def _get_temporary_sql_dir():
    global _temporary_sql_dir
    if _temporary_sql_dir is None:
        _temporary_sql_dir = tempfile.mkdtemp(prefix='loggerhead-cache-')
    return _temporary_sql_dir

def command_line_parser():
    parser = OptionParser("%prog [options] <path>")
    parser.set_defaults(
        user_dirs=False,
        show_version=False,
        log_folder=None,
        use_cdn=False,
        sql_dir=None,
        allow_writes=False,
        export_tarballs=True,
        )
    parser.add_option("--user-dirs", action="store_true",
                      help="Serve user directories as ~user.")
    parser.add_option("--trunk-dir", metavar="DIR",
                      help="The directory that contains the trunk branches.")
    parser.add_option("--port", dest="user_port",
                      help=("Port Loggerhead should listen on "
                            "(defaults to 8080)."))
    parser.add_option("--host", dest="user_host",
                      help="Host Loggerhead should listen on.")
    parser.add_option("--protocol", dest="protocol",
                      help=("Protocol to use: http, scgi, fcgi, ajp"
                           "(defaults to http)."))
    parser.add_option("--log-level", default=None, action='callback',
                      callback=_optparse_level_to_int_level,
                      type="string",
                      help="Set the verbosity of logging. Can either"
                           " be set to a numeric or string"
                           " (eg, 10=debug, 30=warning)")
    parser.add_option("--memory-profile", action="store_true",
                      help="Profile the memory usage using Dozer.")
    parser.add_option("--prefix", dest="user_prefix",
                      help="Specify host prefix.")
    parser.add_option("--profile", action="store_true",
                      help="Generate callgrind profile data to "
                        "%d-stats.callgrind on each request.")
    parser.add_option("--reload", action="store_true",
                      help="Restarts the application when changing python"
                           " files. Only used for development purposes.")
    parser.add_option("--log-folder",
                      help="The directory to place log files in.")
    parser.add_option("--version", action="store_true", dest="show_version",
                      help="Print the software version and exit")
    parser.add_option("--use-cdn", action="store_true", dest="use_cdn",
                      help="Serve YUI from Yahoo!'s CDN")
    parser.add_option("--cache-dir", dest="sql_dir",
                      help="The directory to place the SQL cache in")
    parser.add_option("--allow-writes", action="store_true",
                      help="Allow writing to the Bazaar server.")
    parser.add_option("--export-tarballs", action="store_true",
                      help="Allow exporting revisions to tarballs.")
    return parser


_log_levels = {
    'debug': 10,
    'info': 20,
    'warning': 30,
    'error': 40,
    'critical': 50,
}

def _optparse_level_to_int_level(option, opt_str, value, parser):
    parser.values.log_level = _level_to_int_level(value)


def _level_to_int_level(value):
    """Convert a string level to an integer value."""
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        pass
    return _log_levels[value.lower()]


class LoggerheadConfig(object):
    """A configuration object."""

    def __init__(self, argv=None):
        if argv is None:
            argv = sys.argv[1:]
        self._parser = command_line_parser()
        self._options, self._args = self._parser.parse_args(argv)

        sql_dir = self.get_option('sql_dir')
        if sql_dir is None:
            sql_dir = _get_temporary_sql_dir()
        self.SQL_DIR = sql_dir

    def get_option(self, option):
        """Get the value for the config option, either
        from ~/.bazaar/bazaar.conf or from the command line.
        All loggerhead-specific settings start with 'http_'
        """
        global_config = config.GlobalConfig().get_user_option('http_'+option)
        cmd_config = getattr(self._options, option)
        if global_config is not None and (
            cmd_config is None or cmd_config is False):
            return global_config
        else:
            return cmd_config

    def get_log_level(self):
        opt = self.get_option('log_level')
        return _level_to_int_level(opt)

    def get_arg(self, index):
        """Get an arg from the arg list."""
        return self._args[index]

    def print_help(self):
        """Wrapper around OptionParser.print_help."""
        return self._parser.print_help()

    @property
    def arg_count(self):
        """Return the number of args from the option parser."""
        return len(self._args)
