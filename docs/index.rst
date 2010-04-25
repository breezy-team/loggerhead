Loggerhead:  A web viewer for ``bzr`` branches
==============================================

Loggerhead is a web viewer for projects in Bazaar. It can be used to navigate 
a branch history, annotate files, view patches, perform searches, etc.
Loggerhead is heavily based on `bazaar-webserve
<https://launchpad.net/bzr-webserve>`_, which was, in turn, loosely
based on `hgweb <http://mercurial.selenic.com/wiki/HgWebDirStepByStep>`_.


Getting Started
---------------

Loggerhead depends on the following Python libraries.:

- SimpleTAL for templating.

- simplejson for producing JSON data.

- Paste for the server. (You need version 1.2 or newer of Paste).

- Paste Deploy  (optional, needed when proxying through Apache).

- flup (optional, needed to use FastCGI, SCGI or AJP).


Installing Dependencies Using Ubuntu Packages
#############################################

.. code-block:: sh

   $ sudo apt-get install python-simpletal
   $ sudo apt-get install python-simplejson
   $ sudo apt-get install python-paste
   $ sudo apt-get install python-pastedeploy
   $ sudo apt-get install python-flup

Installing Dependencies Using :command:`easy_install`
#####################################################

.. code-block:: sh

   $ easy_install \
     -f http://www.owlfish.com/software/simpleTAL/py2compatible/download.html \
     SimpleTAL
   $ easy_install simplejson
   $ easy_install Paste
   $ easy_install PasteDeploy
   $ easy_install flup


Running the Standalone Loggerhead Server
----------------------------------------

After installing all the dependencies, you should be able to run
:command:`serve-branches` with the branch you want to serve on the
command line:

.. code-block:: sh

    ./serve-branches ~/path/to/branch

By default, the script listens on port 8080, so head to
http://localhost:8080/ in your browser to see the branch.

You can also pass a directory that contains branches to the script,
and it will serve a very simple directory listing at other pages.

You may update the Bazaar branches being viewed at any time.
Loggerhead will notice and refresh, and Bazaar uses its own branch
locking to prevent corruption.

See :doc:`serve-branches` for all command line options.

Running Loggerhead as a Daemon
------------------------------

To run Loggerhead as a linux daemon:

1) Copy the ``loggerheadd`` scipt to ``/etc/init.d``

.. code-block:: sh

   $ sudo cp ./loggerheadd /etc/init.d

2) Edit the file to configure where your Loggerhead is installed, and which
   serve-branches options you would like.

.. code-block:: sh

   $ sudo vim /etc/init.d/loggerheadd

3) Register the service

.. code-block:: sh

   # on upstart based systems like Ubuntu run: 
   $ sudo update-rc.d loggerheadd defaults

   # on Sysvinit based systems like Centos or SuSE run:
   $ sudo chkconfig --add loggerheadd


Using Loggerhead as a Bazaar Plugin
------------------------------------

This branch contains experimental support for using Loggerhead as a Bazaar
plugin.  To use it, place the top-level Loggerhead directory (the one
containing COPYING.txt) at ``~/.bazaar/plugins/loggerhead``.  E.g.:

.. code-block:: sh

   $ bzr branch lp:loggerhead ~/.bazaar/plugins/loggerhead
   $ cd ~/myproject
   $ bzr serve --http


Using a Config File
-------------------

To hide branches from being displayed, add to ``~/.bazaar/locations.conf``,
under the branch's section:

.. code-block:: ini

    [/path/to/branch]
    http_serve = False

More configuration options to come soon.


Serving Loggerhead behind Apache
--------------------------------

If you want to view Bazaar branches from your existing Apache
installation, you'll need to configure Apache to proxy certain
requests to Loggerhead.  Adding lines like this to your Apache
configuration is one way to do this:

.. code-block:: apache

    <Location "/branches/">
        ProxyPass http://127.0.0.1:8080/branches/
        ProxyPassReverse http://127.0.0.1:8080/branches/
    </Location>

If Paste Deploy is installed, the :command:`serve-branches` script can be
run behind a proxy at the root of a site, but if you're running it at
some path into the site, you'll need to specify it using
``--prefix=/some_path``.

Serving Loggerhead with mod_wsgi
--------------------------------

A second method for using Loggerhead with apache is to have apache itself
execute Loggerhead via mod_wsgi.  You need to add configuration for apache and
for bazaar to make this work.  Example config files are in the Loggerhead doc
directory as apache-loggerhead.conf and bazaar.conf.  You can copy them into
place and use them as a starting point following these directions:

1) Install mod_wsgi.  On Ubuntu and other Debian derived distros::

    sudo apt-get install libapache2-mod-wsgi

   On Fedora-derived distros::

    su -c yum install mod_wsgi

2) Copy the bazaar.conf file where apache will find it (May be done for you if
   you installed Loggerhead from a distribution package)::

    # install -d -o apache -g apache -m 0755 /etc/loggerhead
    # cp -p /usr/share/doc/loggerhead*/bazaar.conf /etc/loggerhead/
    # ln -s /etc/loggerhead /var/www/.bazaar

3) Create the cache directory (May be done for you if you installed Loggerhead
   from a distribution package)::

    # install -d -o apache -g apache -m 0700 /var/cache/loggerhead/

4) Edit /etc/loggerhead/bazaar.conf.  You need to set http_root_dir to the filesystem
   path that you will find your bzr branches under.  Note that normal
   directories under that path will also be visible in Loggerhead.

5) Install the apache conf file::

     # cp -p /usr/share/doc/loggerhead*/apache-loggerhead.conf /etc/httpd/conf.d/loggerhead.conf

6) Edit /etc/httpd/conf.d/loggerhead.conf to point to the url you desire to
   serve Loggerhead on.  This should match with the setting for
   http_user_prefix in bazaar.conf

7) Restart apache and you should be able to start browsing

.. note:: If you have SELinux enabled on your system you may need to allow
   apache to execute files in temporary directories.  You will get a
   MemoryError traceback from python if this is the case.  This is because of
   the way that python ctypes interacts with libffi.  To rectify this, you may
   have to do several things, such as mounting tmpdirs so programs can be
   executed on them and setting this SELinux boolean::

       setsebool httpd_tmp_exec on

   This bug has information about how python and/or Linux distros might solve
   this issue permanently and links to bugs which diagnose the root cause.
   https://bugzilla.redhat.com/show_bug.cgi?id=582009

Search
------

Search is currently supported by using the bzr-search plugin (available
at: https://launchpad.net/bzr-search ).

You need to have the plugin installed and each branch indexed to allow
searching on branches.

Command-Line Reference
----------------------

.. toctree::
   :maxdepth: 2

   serve-branches
   start-loggerhead
   stop-loggerhead


Support
-------

Discussion should take place on the bazaar-dev mailing list at
mailto:bazaar@lists.canonical.com.  You can join the list at
<https://lists.ubuntu.com/mailman/listinfo/bazaar>.  You don't need to
subscribe to post, but your first post will be held briefly for manual
moderation.

Bugs, support questions and merge proposals are tracked on Launchpad, e.g:

    https://bugs.launchpad.net/loggerhead


Hacking
-------

To run Loggerhead tests, you will need to install the package ``python-nose``,
and run its :command:`nosetests` script in the Loggerhead directory:

.. code-block:: sh

    nosetests


License
-------

GNU GPLv2 or later.

See Also
--------

https://launchpad.net/loggerhead

Index
=====

- :ref:`genindex`
