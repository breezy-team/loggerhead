LOGGERHEAD
==========

[ Version 1.6 for Bazaar 1.6 ]

Loggerhead is a web viewer for Bazaar branches.  It can be used to
navigate a branch history, annotate files, perform searches... all the
usual things.


GETTING STARTED
---------------

Loggerhead depends on 
1) SimpleTAL for templating.
   on Ubuntu package `sudo apt-get install python-simpletal`
   or download from http://www.owlfish.com/software/simpleTAL/download.html
2) Paste for the server. (You need version 1.2 or newer of Paste.) 
   on Ubuntu package `sudo apt-get install python-paste`
   or use `easy_install Paste`
3) Paste Deploy  (optional, needed when proxying through Apache)
   on Ubuntu package `sudo apt-get install python-pastedeploy`
   or use `easy_install PasteDeploy`

Then simply run the 'serve-branches' with the branch you want to
serve on the command line:

    ./serve-branches ~/path/to/branch

The script listens on port 8080 so head to http://localhost:8080/ in
your browser to see the branch.  You can also pass a directory that
contains branches to the script, and it will serve a very simple
directory listing at other pages.

You may update the Bazaar branches being viewed at any time.
Loggerhead will notice and refresh, and Bazaar uses its own branch
locking to prevent corruption.

To run loggerhead as a linux daemon: 
1) Copy loggerheadd to /etc/init.d
2) Edit the file to configure where your loggerhead is installed, and which
   serve-branches options you would like.
3) Register the service
   cd /etc/init.d
   a) on upstart based systems like Ubuntu run: 
      update-rc.d loggerheadd defaults
   b) on Sysvinit based systems like Centos or SuSE run:
      chkconfig --add loggerheadd

USING A CONFIG FILE
-------------------

Previous versions of Loggerhead read their configuration from a config
file.  This mode of operation is still supported by the
'start-loggerhead' script.  A 'loggerhead.conf.example' file is
included in the source which has comments explaining the various
options.

Loggerhead can then be started by running::

    $ ./start-loggerhead

This will run loggerhead in the background, listening on port 8080 by
default.

To stop Loggerhead, run::

    $ ./stop-loggerhead

In the configuration file you can configure projects, and branches per
project.  The idea is that you could be publishing several (possibly
unrelated) projects through the same loggerhead instance, and several
branches for the same project.  See the "loggerhead.conf.example" file
included with the source.

A debug and access log are stored in the logs/ folder, relative to
the location of the start-loggerhead script.


SERVING LOGGERHEAD FROM BEHIND APACHE
-------------------------------------

If you want to view Bazaar branches from your existing Apache
installation, you'll need to configure Apache to proxy certain
requests to Loggerhead.  Adding lines like this to you Apache
configuration is one way to do this::

    <Location "/branches/">
        ProxyPass http://127.0.0.1:8080/branches/
        ProxyPassReverse http://127.0.0.1:8080/branches/
    </Location>

If Paste Deploy is installed, the 'serve-branches' script can be
run behind a proxy at the root of a site, but if you're running it at
some path into the site, you'll need to specify is using '--prefix=/some_path'.

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
