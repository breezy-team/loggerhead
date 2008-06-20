#!/usr/bin/env python

import pkg_resources
pkg_resources.require("TurboGears")

import os
import sys

home = os.path.realpath(os.path.dirname(__file__))
pidfile = os.path.join(home, 'loggerhead.pid')

try:
    f = open(pidfile, 'r')
except IOError, e:
    print 'No pid file found.'
    sys.exit(1)

pid = int(f.readline())

try:
    os.kill(pid, 0)
except OSError, e:
    print 'Stale pid file; server is not running.'
    sys.exit(1)

print
print 'Shutting down previous server @ pid %d.' % (pid,)
print

import signal
os.kill(pid, signal.SIGINT)
