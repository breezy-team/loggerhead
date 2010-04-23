:command:`start-loggerhead`
===========================

The :command:`start-loggerhead` command starts a new standalone Loggerhead
server.  By default, the server runs in the background (daemonized).

.. program:: start-loggerhead

Usage
-----

.. code-block:: sh

    start-loggerhead [OPTIONS]

Options
-------

.. cmdoption:: --version

    Print the software version and exit.

.. cmdoption:: -h, --help

    Show this help message and exit.

.. cmdoption:: --foreground

    Run in the foreground;  don't daemonize.

.. cmdoption:: -C, --check

    Only start if not already running (useful for cron jobs).

.. cmdoption:: -p, --pidfile=PIDFILE

    Override pid file location.

.. cmdoption:: -c, --config-file=CONFIGFILE

    Override configuration file location (the default is
    :file:`/etc/loggerhead.conf`).

.. cmdoption:: --log-folder=LOG_FOLDER

    The directory in which to place log files.
