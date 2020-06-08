:command:`loggerhead-serve`
=========================

The :command:`loggerhead-serve` script runs a standalone Loggerhead server in
the foreground.

.. program:: loggerhead-serve

Usage
-----

.. code-block:: sh

   loggerhead-serve [OPTIONS] <target directory>

Options
-------

.. cmdoption:: --user-dirs

    Serve user directories as ``~user`` (requires ``--trunk-dir``).

    If both options are set, then for requests where the CGI ``PATH_INFO``
    starts with "/~<name>", serve branches under the <name> directory.

.. cmdoption:: --trunk-dir=DIR

    The directory that contains the trunk branches (requires ``--user-dirs``).

    If both options are set, then for requests where the CGI ``PATH_INFO``
    does not start with "/~<name>", serve branches under DIR.

.. cmdoption:: --port

    Listen on the given port.
    
    Defaults to 8080.

.. cmdoption:: --host

    Listen on the interface corresponding to the given IP. 
    
    Defaults to listening on all interfaces, i.e., "0.0.0.0".

.. cmdoption:: --protocol

    Serve the application using the specified protocol.
    
    Can be one of: "http", "scgi", "fcgi", "ajp" (defaults to "http").

.. cmdoption:: --prefix

    Set the supplied value as the CGI ``SCRIPT_NAME`` for the application.

    This option is intended for use when serving Loggerhead behind a
    reverse proxy, with Loggerhead being "mounted" at a directory below
    the root.  E.g., if the reverse proxy translates requests for
    ``http://example.com/loggerhead`` onto the standalone Loggerhead process,
    that process should be run with ``--prefix=/loggerhead``.

.. cmdoption:: --log-folder=LOG_FOLDER

    The directory in which to place Loggerhead's log files.
    
    Defaults to the current directory.

.. cmdoption:: --cache-dir=SQL_CACHE_DIR

    The directory in which to place the SQL cache.

    Defaults to the current directory.

.. cmdoption:: --use-cdn
   
    Serve jQuery javascript libraries from Googles CDN.

.. cmdoption:: --allow-writes
   
    Allow writing to the Breezy server.
    
    Setting this option keeps Loggerhead from adding a 'readonly+' prefix
    to the base URL of the branch.  The only effect of suppressing this prefix
    is to make visible the display of instructions for checking out the
    'public_branch' URL for the branch being browsed.

.. cmdoption:: -h, --help

    Print the help message and exit

.. cmdoption:: --version

    Print the software version and exit.

Debugging Options
-----------------

The following options are only useful when developing / debugging Loggerhead
itself.

.. cmdoption:: --profile
   
    Generate per-request callgrind profile data.
    
    Data for each request is written to a file ``%d-stats.callgrind``,
    where ``%d`` is replaced by the sequence number of the request.

.. cmdoption:: --memory-profile

    Profile the memory usage using the `Dozer
    <http://pypi.python.org/pypi/Dozer>`_ middleware.

.. cmdoption:: --reload

    Restart the application when any of its python file change.
    
    This option should only used for development purposes.
