'''Profiling middleware for paste.'''
import cgi
import cProfile
from cStringIO import StringIO
import pstats
import sys

from paste.debug.profile import ProfileMiddleware
from paste import response

class CProfileMiddleware(ProfileMiddleware):
    '''Paste middleware for profiling with cProfile.'''

    def __call__(self, environ, start_response):

        catch_response = []
        body = []

        def capture_output(func, *args, **kwargs):
            out = StringIO()
            old_stdout = sys.stdout
            sys.stdout = out
            try:
                func(*args, **kwargs)
            finally:
                sys.stdout = old_stdout
            return out.getvalue()

        def replace_start_response(status, headers, exc_info=None):

            catch_response.extend([status, headers])
            start_response(status, headers, exc_info)
            return body.append

        def run_app():

            app_iter = self.app(environ, replace_start_response)
            try:
                body.extend(app_iter)
            finally:
                if hasattr(app_iter, 'close'):
                    app_iter.close()

        self.lock.acquire()
        try:
            cProfile.runctx("run_app()", globals(), locals(),
                filename='loggerhead.cprof')

            body = ''.join(body)
            headers = catch_response[1]
            content_type = response.header_value(headers, 'content-type')
            if content_type is None or \
                not content_type.startswith('text/html') :
                # We can't add info to non-HTML output
                return [body]
            stats = pstats.Stats('loggerhead.cprof')
            #stats.sort_stats('time', 'calls')
            stats.strip_dirs()
            output = capture_output(stats.print_stats, self.limit)
            output_callers = capture_output(
                stats.print_callers, self.limit)
            body += '<pre style="%s">%s\n%s</pre>' % (
                self.style, cgi.escape(output), cgi.escape(output_callers))
            return [body]
        finally:
            self.lock.release()

