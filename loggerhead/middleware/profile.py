'''Profiling middleware for paste.'''
import cgi
import logging
import sys
import threading

from bzrlib.lsprof import profile
from guppy import hpy

class LSProfMiddleware(object):
    '''Paste middleware for profiling with lsprof.'''

    def __init__(self, app, global_conf=None):
        self.app = app
        self.lock = threading.Lock()
        self.__count = 0

    def __run_app(self, environ, start_response):
        app_iter = self.app(environ, start_response)
        try:
            return list(app_iter)
        finally:
            if getattr(app_iter, 'close', None):
                app_iter.close()

    def __call__(self, environ, start_response):
        """Run a request."""
        self.lock.acquire()
        try:
            ret, stats = profile(self.__run_app, environ, start_response)
            self.__count += 1
            stats.save("%d-stats.callgrind" % self.__count, format="callgrind")
            return ret
        finally:
            self.lock.release()


class MemoryProfileMiddleware(object):
    '''Paste middleware for profiling memory with heapy.'''

    def __init__(self, app, limit=40):
        self.app = app
        self.lock = threading.Lock()

        self.type2count = {}
        self.type2all = {}
        self.limit = limit

    def update(self):
        obs = sys.getobjects(0)
        type2count = {}
        type2all = {}
        for o in obs:
            all = sys.getrefcount(o)

            if type(o) is str and o == '<dummy key>':
                # avoid dictionary madness
                continue
            t = type(o)
            if t in type2count:
                type2count[t] += 1
                type2all[t] += all
            else:
                type2count[t] = 1
                type2all[t] = all

        ct = [(type2count[t] - self.type2count.get(t, 0),
               type2all[t] - self.type2all.get(t, 0),
               t)
              for t in type2count.iterkeys()]
        ct.sort()
        ct.reverse()
        printed = False

        logging.debug("----------------------")
        logging.debug("Memory profiling")
        i = 0
        for delta1, delta2, t in ct:
            if delta1 or delta2:
                if not printed:
                    logging.debug("%-55s %8s %8s" % ('', 'insts', 'refs'))
                    printed = True

                logging.debug("%-55s %8d %8d" % (t, delta1, delta2))

                i += 1
                if i >= self.limit:
                    break 

        self.type2count = type2count
        self.type2all = type2all

    def __call__(self, environ, start_response):
        self.lock.acquire()
        try:
            # We don't want to be working with the static images
            # TODO: There needs to be a better way to do this.
            self.update()
            return self.app(environ, start_response)
        finally:
            self.lock.release()

