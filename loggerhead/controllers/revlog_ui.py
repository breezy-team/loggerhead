import datetime
import simplejson
import time
import urllib

from loggerhead import util
from loggerhead.controllers import BufferingWriter, TemplatedBranchView


class RevLogUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.revlog'

    def get_values(self, path, kwargs, headers):
        history = self._history

        revid = urllib.unquote(self.args[0])

        change = history.get_changes([revid])[0]
        file_changes = history.get_file_changes(change)
        history.add_branch_nicks(change)

        return {
            'branch': self._branch,
            'entry': change,
            'file_changes': file_changes,
            'util': util,
            'revid': revid,
            'url': self._branch.context_url,
        }


class RevLogJSONUI(RevLogUI):

    def get_json_values(self, environ):
        core_values, headers = self.get_core_values(environ)
        del core_values['branch'], core_values['util'], core_values['url']
#        print core_values
#        core_values['entry'] = core_values['entry']._properties
#        core_values['file_changes'] = core_values['file_changes']._properties

        return core_values, headers

    def __call__(self, environ, start_response):
        z = time.time()
        json_values, headers = self.get_json_values(environ)

        # XXX de-dupe this code.
        self.log.info('Getting information for %s: %.3f secs' % (
            self.__class__.__name__, time.time() - z))
        #headers['Content-Type'] = 'application/json'
        headers['Content-Type'] = 'text/plain'
        writer = start_response("200 OK", headers.items())
        if environ.get('REQUEST_METHOD') == 'HEAD':
            # No content for a HEAD request
            return []
        z = time.time()
        w = BufferingWriter(writer, 8192)
        def encode_stuff(obj):
            if isinstance(obj, util.Container):
                d = obj.__dict__.copy()
                del d['_properties']
                return d
            elif isinstance(obj, datetime.datetime):
                return tuple(obj.utctimetuple())
            raise TypeError(repr(obj) + " is not JSON serializable")

        w.write(simplejson.dumps(json_values, default=encode_stuff))
        w.flush()
        self.log.info(
            'Rendering %s: %.3f secs, %s bytes' % (
                self.__class__.__name__, time.time() - z, w.bytes))
        return []
