import urllib

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView


class RevLogUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.revlog'

    def get_values(self, path, kwargs, headers):
        history = self._history

        revid = urllib.unquote(self.args[0])

        changes = list(history.get_changes([revid]))
        history.add_changes(changes[0])
        history.get_branch_nicks(changes)

        return {
            'branch': self._branch,
            'entry': changes[0],
            'util': util,
            'revid': revid,
            'url': self._branch.context_url,
        }
