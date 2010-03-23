loggerhead:  A web viewer for ``bzr`` branches
==============================================

Loggerhead is a web viewer for projects in bazaar. It can be used to navigate 
a branch history, annotate files, view patches, perform searches, etc.
It is heavily based on ``bazaar-webserve``, which is itself based on ``hgweb``
for Mercurial.

Getting Started
---------------

Loggerhead depends on the following Python libraries.:

- SimpleTAL for templating.

- simplejson for producing JSON data.

- Paste for the server. (You need version 1.2 or newer of Paste.)

- Paste Deploy  (optional, needed when proxying through Apache)

- flup (optional, needed to use FastCGI, SCGI or AJP)


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

To run loggerhead as a linux daemon:

1) Copy the ``loggerheadd`` scipt to ``/etc/init.d``

.. code-block:: sh

   $ sudo cp ./loggerheadd /etc/init.d

2) Edit the file to configure where your loggerhead is installed, and which
   serve-branches options you would like.

.. code-block:: sh

   $ sudo vim /etc/init.d/loggerheadd

3) Register the service

a) on upstart based systems like Ubuntu run: 

.. code-block:: sh

   $ sudo update-rc.d loggerheadd defaults

b) on Sysvinit based systems like Centos or SuSE run:

.. code-block:: sh

   $ sudo chkconfig --add loggerheadd


Using Loggerhead as a Bazaar Plugin
------------------------------------

This branch contains experimental support for using Loggerhead as a Bazaar
plugin.  To use it, place the top-level Loggerhead directory (the one
containing this file) at ``~/.bazaar/plugins/loggerhead``.  E.g.:

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


Serving Loggerhead from Behind Apache
-------------------------------------

If you want to view Bazaar branches from your existing Apache
installation, you'll need to configure Apache to proxy certain
requests to Loggerhead.  Adding lines like this to you Apache
configuration is one way to do this:

.. code-block:: apache

    <Location "/branches/">
        ProxyPass http://127.0.0.1:8080/branches/
        ProxyPassReverse http://127.0.0.1:8080/branches/
    </Location>

If Paste Deploy is installed, the :command:`serve-branches` script can be
run behind a proxy at the root of a site, but if you're running it at
some path into the site, you'll need to specify is using
``--prefix=/some_path``.


Search
------

Search is currently supported by using the bzr-search plugin (available
at: https://launchpad.net/bzr-search ).

You need to have the plugin installed and each branch indexed to allow
searching on branches.

Script Reference
----------------

.. toctree::
   :maxdepth: 2

   serve-branches
   start-loggerhead
   stop-loggerhead


Support
-------

Loggerhead is loosely based on `bazaar-webserve
<https://launchpad.net/bzr-webserve>`_, which was, in turn, loosely
based on `hgweb <http://mercurial.selenic.com/wiki/HgWebDirStepByStep>`_.

Discussion should take place on the bazaar-dev mailing list at
mailto:bazaar@lists.canonical.com.  You can join the list at
<https://lists.ubuntu.com/mailman/listinfo/bazaar>.  You don't need to
subscribe to post, but your first post will be held briefly for manual
moderation.

Bugs are tracked on Launchpad; start at:

    https://bugs.launchpad.net/loggerhead


Hacking
-------

To run loggerhead tests, you will need to install the package ``python-nose``,
and run its :command:`nosetests` script in the loggerhead directory:

.. code-block:: sh

    nosetests


License
-------

GNU GPLv2 or later.

See Also
--------

https://launchpad.net/loggerhead

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

