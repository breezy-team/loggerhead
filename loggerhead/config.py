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

'''Configuration tools for Loggerhead.'''
from optparse import OptionParser
import sys
import tempfile


_temporary_sql_dir = None

def _get_temporary_sql_dir():
    global _temporary_sql_dir
    if _temporary_sql_dir is None:
        _temporary_sql_dir = tempfile.mkdtemp(prefix='loggerhead-cache-')
    return _temporary_sql_dir


class LoggerheadConfig(object):
    '''A configuration object.'''

    def __init__(self, argv=None):
        if argv is None:
            argv = sys.argv[1:]
        self._parser = self.command_line_parser()
        self._options, self._args = self._parser.parse_args(argv)

        sql_dir = self.get_option('sql_dir')
        if sql_dir is None:
            sql_dir = _get_temporary_sql_dir()
        self.SQL_DIR = sql_dir

    def command_line_parser(self):
        parser = OptionParser("%prog [options] <path>")
        parser.set_defaults(
            user_dirs=False,
            show_version=False,
            log_folder=None,
            use_cdn=False,
            sql_dir=None,
            )
        self.add_option(parser=parser,
                        name="user-dirs", 
                        action="store_true", 
                        dest="user_dirs",
                        help="Serve user directories as ~user.")
        self.add_option(parser=parser,
                        name="trunk-dir", 
                        metavar="DIR",
                        help="The directory that contains the trunk branches.")
        self.add_option(parser=parser,
                        name="port", 
                        dest="user_port",
                        help="Port Loggerhead should listen on "
                             "(defaults to 8080).")
        self.add_option(parser=parser,
                        name="host",
                        dest="user_host",
                        help="Host Loggerhead should listen on.")
        self.add_option(parser=parser,
                        name="memory-profile",
                        action="store_true",
                        dest="memory_profile",
                        help="Profile the memory usage using heapy.")
        self.add_option(parser=parser,
                        name="prefix",
                        dest="user_prefix",
                        help="Specify host prefix.")
        self.add_option(parser=parser,
                        name="profile",
                        action="store_true",
                        dest="profile",
                        help="Generate callgrind profile data to "
                             "%d-stats.callgrind on each request.")
        self.add_option(parser=parser,
                        name="reload", 
                        help="Restarts the application when changing python "
                             "files. Only used for development purposes.",
                        action="store_true",
                        dest="reload")
        self.add_option(parser=parser,
                        name="log-folder",
                        dest="log_folder",
                        type=str,
                        help="The directory to place log files in.")
        self.add_option(parser=parser,
                        name="version",
                        action="store_true",
                        dest="show_version",
                        help="Print the software version and exit")
        self.add_option(parser=parser,
                        name="use-cdn",
                        action="store_true",
                        help="Serve YUI from Yahoo!'s CDN")
        self.add_option(parser=parser,
                        name="cache-dir",
                        dest="sql_dir",
                        help="The directory to place the SQL cache in")
        return parser

    def add_option(self, parser, name, help, 
                   action=None, dest=None, type=None, metavar=None):
        parser.add_option('--' + name, help=help, action=action, dest=dest,
                          type=type, metavar=metavar)

    def get_option(self, option):
        '''Get an option from the options dict.'''
        return getattr(self._options, option)

    def get_arg(self, index):
        '''Get an arg from the arg list.'''
        return self._args[index]

    def print_help(self):
        '''Wrapper around OptionParser.print_help.'''
        return self._parser.print_help()

    @property
    def arg_count(self):
        '''Return the number of args from the option parser.'''
        return len(self._args)

