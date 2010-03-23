:command:`serve-branches`:  Run a loggerhead server [XXX in the foreground]
===========================================================================

The :command:`serve-branches` command runs a standalone loggerhead server in
the foreground.

.. program:: serve-branches

Usage
-----

.. code-block:: sh

   serve-branches [OPTIONS] <target directory>

.. cmdoption:: -h, --help

    Show this help message and exit

.. cmdoption:: --user-dirs

    Serve user directories as ``~user``. XXX (Requires ``--trunk-dir``).

.. cmdoption:: --trunk-dir=DIR

    The directory that contains the trunk branches.

.. cmdoption:: --port

    Port Loggerhead should listen on (defaults to 8080).

.. cmdoption:: --host

    Host Loggerhead should listen on. XXX (defaults to 0.0.0.0).

.. cmdoption:: --prefix

    Specify host prefix. XXX this is wildly unclear.

.. cmdoption:: --reload

    Restarts the application when changing python files. Only used for
    development purposes.

.. cmdoption:: --log-folder=LOG_FOLDER

    The directory [XXX in which] to place log files

.. cmdoption:: --version

    Print the software version and exit.
