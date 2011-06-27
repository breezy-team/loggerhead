import datetime
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

    def get_json_values(self, environ):
        core_values, headers = self.get_core_values(environ)
        del core_values['branch'], core_values['util'], core_values['url']
        return core_values, headers
