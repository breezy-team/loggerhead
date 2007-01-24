LOGGERHEAD
==========

[ version 1.1.1 for bazaar 0.13 ]

Loggerhead is a web viewer for bazaar branches.  It can be used to navigate
a branch history, annotate files, perform searches... all the usual things.

This is a TurboGears (http://www.turbogears.org) project.  It can be
started by running::

    $ ./start-loggerhead.py
    
This will run loggerhead in the background.  To stop it, run::

    $ ./stop-loggerhead.py

If you're not familiar with TurboGears, the simplest way to get running is
to add the following lines to your apache configuration::

    <Location "/branches/">
        ProxyPass http://127.0.0.1:8080/
        ProxyPassReverse http://127.0.0.1:8080/
    </Location>
    
The config file is "loggerhead.conf".  In there, you can configure projects,
and branches per project.  The idea is that you could be publishing several
(possibly unrelated) projects through the same loggerhead instance, and 
several branches for the same project.

Don't bother with "dev.cfg" or any of the other TurboGears config files.
Loggerhead overrides those values with its own.

A debug and access log are stored in the logs/ folder.


CACHES
------

To speed up most operations, loggerhead will start creating two caches per
branch when it first launches:

    - a revision data cache
    - a text searching cache

You can put the cache folder anywhere, but I find that a folder under
the branch's .bzr/ folder is the simplest place.

The caches for a branch with 10,000 revisions take about 15 minutes each
on my machine, but YMMV.  Once they are built, they update every six hours
or so but usually finish quickly (or instantly) after the initial creation.
Until the revision cache is built, all operations will be slow.

You may update the bazaar branch at any time (for example, from a cron).
Loggerhead will notice and refresh, and bazaar uses its own branch locking
to prevent corruption.


SUPPORT
-------

This is loosely based on bazaar-webserve, which was loosely based on hgweb.
Discussion should take place on the bazaar-dev mailing list.

