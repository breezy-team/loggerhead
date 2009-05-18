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

def command_line_parser():
    parser = OptionParser("%prog [options] <path>")
    parser.set_defaults(
        user_dirs=False,
        show_version=False,
        log_folder=None,
        use_cdn=False,
        sql_dir=None,
        )
    parser.add_option("--user-dirs", action="store_true", dest="user_dirs",
                      help="Serve user directories as ~user.")
    parser.add_option("--trunk-dir", metavar="DIR",
                      help="The directory that contains the trunk branches.")
    parser.add_option("--port", dest="user_port",
                      help=("Port Loggerhead should listen on "
                            "(defaults to 8080)."))
    parser.add_option("--host", dest="user_host",
                      help="Host Loggerhead should listen on.")
    parser.add_option('--memory-profile', action='store_true',
                      dest='memory_profile',
                      help='Profile the memory usage using heapy.')
    parser.add_option("--prefix", dest="user_prefix",
                      help="Specify host prefix.")
    parser.add_option("--profile", action="store_true", dest="profile",
                      help="Generate callgrind profile data to "
                        "%d-stats.callgrind on each request.")
    parser.add_option("--reload", action="store_true", dest="reload",
                      help="Restarts the application when changing python"
                           " files. Only used for development purposes.")
    parser.add_option('--log-folder', dest="log_folder",
                      type=str, help="The directory to place log files in.")
    parser.add_option("--version", action="store_true", dest="show_version",
                      help="Print the software version and exit")
    parser.add_option('--use-cdn', action='store_true',
                      help="Serve YUI from Yahoo!'s CDN")
    parser.add_option('--cache-dir', dest='sql_dir',
                      help="The directory to place the SQL cache in")
    return parser


class LoggerheadConfig(object):
    '''A configuration object.'''

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

