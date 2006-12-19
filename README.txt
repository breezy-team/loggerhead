LOGGERHEAD
==========

Loggerhead is a web viewer for bazaar branches.  It can be used to navigate
a branch history, annotate files, perform searches... all the usual things.

This is a TurboGears (http://www.turbogears.org) project.  It can be
started by running the 'start-loggerhead.py' script.

If you're not familiar with turbogears, the easiest way to get this script
started is to run it via::

    $ nohup ./start-loggerhead.py &
    
and add the following lines to your apache configuration::

    <Location "/bzr.dev/">
        ProxyPass http://127.0.0.1:8080/
        ProxyPassReverse http://127.0.0.1:8080/
    </Location>
    
The port configuration is in "dev.cfg".

The config file is "loggerhead.conf".  Currently it can only serve one
branch at a time, but in the future I plan to add support for serving
multiple branches at once.


CACHES
------

To speed up most operations, loggerhead will start creating two caches
when it first launches:

    - a revision data cache
    - a text searching cache

You can put the cache folder anywhere, but I find that a folder under
the branch's .bzr/ folder is the simplest place.

The caches for a branch with 10,000 revisions take about 15 minutes each
on my machine, but YMMV.  Once they are built, they update every six hours
or so but usually finish quickly (or instantly).  Until the revision cache
is built, all operations will be slow.

You may update the bazaar branch at any time (for example, from a cron).
Loggerhead will notice and refresh, and bazaar uses its own branch locking
to prevent corruption.


SUPPORT
-------

This is loosely based on bazaar-webserve, which was loosely based on hgweb.
Discussion should take place on the bazaar-dev mailing list.

