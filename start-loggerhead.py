#!/usr/bin/env python2.4

import pkg_resources
pkg_resources.require("TurboGears")

import logging
import os

import turbogears
import cherrypy
cherrypy.lowercase_api = True

import sys


def setup_logging(home, foreground):
    # i hate that stupid logging config format, so just set up logging here.

    log_folder = os.path.join(home, 'logs')
    if not os.path.exists(log_folder):
        os.mkdir(log_folder)
    
    f = logging.Formatter('%(levelname)-.3s [%(asctime)s.%(msecs)03d] %(name)s: %(message)s',
                          '%Y%m%d-%H:%M:%S')
    debug_log = logging.FileHandler(os.path.join(log_folder, 'debug.log'))
    debug_log.setLevel(logging.DEBUG)
    debug_log.setFormatter(f)
    if foreground:
        stdout_log = logging.StreamHandler(sys.stdout)
        stdout_log.setLevel(logging.DEBUG)
        stdout_log.setFormatter(f)
    f = logging.Formatter('[%(asctime)s.%(msecs)03d] %(message)s',
                          '%Y%m%d-%H:%M:%S')
    access_log = logging.FileHandler(os.path.join(log_folder, 'access.log'))
    access_log.setLevel(logging.INFO)
    access_log.setFormatter(f)
    
    logging.getLogger('').addHandler(debug_log)
    logging.getLogger('turbogears.access').addHandler(access_log)
    logging.getLogger('turbogears.controllers').setLevel(logging.INFO)
    
    if foreground:
        logging.getLogger('').addHandler(stdout_log)
    


foreground = False
if len(sys.argv) > 1:
    if sys.argv[1] == '-f':
        foreground = True

home = os.path.realpath(os.path.dirname(__file__))
pidfile = os.path.join(home, 'loggerhead.pid')

# read loggerhead config

from configobj import ConfigObj
config = ConfigObj(os.path.join(home, 'loggerhead.conf'), encoding='utf-8')
extra_path = config.get('bzrpath', None)
if extra_path:
    sys.path.insert(0, extra_path)

turbogears.update_config(configfile="dev.cfg", modulename="loggerhead.config")

potential_overrides = [ ('server.socket_port', int), ('server.webpath', str), ('server.thread_pool', int) ]
for key, keytype in potential_overrides:
    value = config.get(key, None)
    if value is not None:
        value = keytype(value)
        turbogears.config.update({ key: value })

if not foreground:
    sys.stderr.write('\n')
    sys.stderr.write('Launching loggerhead into the background.\n')
    sys.stderr.write('PID file: %s\n' % (pidfile,))
    sys.stderr.write('\n')

    from loggerhead.daemon import daemonize
    daemonize(pidfile, home)

setup_logging(home, foreground=foreground)
    
log = logging.getLogger('loggerhead')
log.info('Starting up...')

from loggerhead.controllers import Root

Root = Root(config)

# re-index every 6 hours

index_freq = config.get('cache_rebuild_frequency', 6 * 3600)
turbogears.scheduler.add_interval_task(initialdelay=1, interval=index_freq, action=Root._check_rebuild)

try:
    turbogears.start_server(Root)
finally:
    log.info('Shutdown.')
    try:
        os.remove(pidfile)
    except OSError:
        pass


