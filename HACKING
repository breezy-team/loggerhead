Loggerhead
==========

Overview
--------

This document attempts to give some hints for people that are wanting to work
on Loggerhead.


Testing
-------

You can run the loggerhead test suite as a bzr plugin. To run just the
loggerhead tests::

  bzr selftest -s bp.loggerhead


Load Testing
------------

As a web service, Loggerhead will often be hit by multiple requests. We want
to make sure that loggerhead can scale with many requests, without performing
poorly or crashing under the load.

There is a command ``bzr load-test-loggerhead`` that can be run to stress
loggerhead. A script is given, describing what requests to make, against what
URLs, and for what level of parallel activity.


Load Testing Multiple Instances
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

One way that Launchpad provides both high availability and performance scaling
is by running multiple instances of loggerhead, serving the same content. A
proxy is then used to load balance the requests. This also allows us to shut
down one instance for upgrading, without interupting service (requests are
just routed to the other instance).

However, multiple processes poses an even greater risk that caches will
conflict. As such, it is useful to test that changes don't introduce coherency
issues at load. ``bzr load-test-loggerhead`` can be configured with a script
that will make requests against multiple loggerhead instances concurrently.

To run multiple instances, it is often sufficient to just spawn multiple
servers on different ports. For example::

  $ bzr serve --http --port=8080 &
  $ bzr serve --http --port=8081 &

There is a simple example script already in the source tree::

  $ bzr load-test-loggerhead load_test_scripts/multiple_instances.script



.. vim: ft=rst tw=78

