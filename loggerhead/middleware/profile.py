"""Profiling middleware for Paste."""

import threading

from breezy.lsprof import profile


class LSProfMiddleware(object):
    """Paste middleware for profiling with lsprof."""

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
            stats.save("%d-stats.callgrind" % (self.__count,), format="callgrind")
            return ret
        finally:
            self.lock.release()
