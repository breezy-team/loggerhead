import urllib

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView


class RevLogUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.revlog'

    def get_values(self, path, kwargs, headers):
        history = self._history

        revid = urllib.unquote(self.args[0])

        change = history.get_changes([revid])[0]
        file_changes = history.get_file_changes(change)
        history.get_branch_nicks([change])

        return {
            'branch': self._branch,
            'entry': change,
            'file_changes': file_changes,
            'util': util,
            'revid': revid,
            'url': self._branch.context_url,
        }
