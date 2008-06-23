LOGGERHEAD
==========

[ Version 1.6 for Bazaar 1.6 ]

Loggerhead is a web viewer for Bazaar branches.  It can be used to
navigate a branch history, annotate files, perform searches... all the
usual things.

GETTING STARTED
---------------

Loggerhead depends on SimpleTAL for templating and Paste for the
server.  So you need these installed -- on Ubuntu you want the
'python-simpletal' and 'python-paste' packages installed.  You need
version 1.2 or newer of Paste.

Then simply run the 'serve-branches.py' script of loggerhead from the
directory containing the branches you want to serve.

For example:

    XXX

USING A CONFIG FILE
-------------------

Previous versions of Loggerhead read their configuration from a config
file.  This mode of operation is still supported by the
'start-loggerhead.py' script.  A 'loggerhead.conf.example' file is
included in the source which has comments explaining the various
options.

Loggerhead can then be started by running::

    $ ./start-loggerhead.py

This will run loggerhead in the background.  It listens on port 8080
by default, so go to http://localhost:8080/ in your browser to see the
list of bublished branches.

To stop Loggerhead, run::

    $ ./stop-loggerhead.py

In the configuration file you can configure projects, and branches per
project.  The idea is that you could be publishing several (possibly
unrelated) projects through the same loggerhead instance, and several
branches for the same project.  See the "loggerhead.conf.example" file
included with the source.

A debug and access log are stored in the logs/ folder, relative to
the location of the start-loggerhead.py script.

You may update the Bazaar branch at any time (for example, from a cron).
Loggerhead will notice and refresh, and Bazaar uses its own branch
locking to prevent corruption.

SERVING LOGGERHEAD FROM BEHIND APACHE
-------------------------------------

If you want to view Bazaar branches from your existing Apache
installation, you'll need to configure Apache to proxy certain
requests to Loggerhead.  Adding lines like this to you Apache
configuration is one way to do this::

    <Location "/branches/">
        ProxyPass http://127.0.0.1:8080/
        ProxyPassReverse http://127.0.0.1:8080/
    </Location>



FILES CHANGED CACHE
-------------------

To speed up the display of the changelog view for large trees,
loggerhead can be configured to cache the files changes between
revisions.  Set the 'cachepath' value in the config file.


SUPPORT
-------

Loggerhead is loosely based on bazaar-webserve, which was loosely
based on hgweb.  Discussion should take place on the bazaar-dev
mailing list at bazaar@lists.canonical.com.  You can join the list at
<https://lists.ubuntu.com/mailman/listinfo/bazaar>.  You don't need to
subscribe to post, but your first post will be held briefly for manual
moderation.

Bugs are tracked on Launchpad; start at:

    https://bugs.launchpad.net/loggerhead
