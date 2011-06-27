import urllib

from loggerhead.controllers import TemplatedBranchView


class RevLogUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.revlog'

    def get_values(self, path, kwargs, headers):
        history = self._history

        revid = urllib.unquote(self.args[0])

        change = history.get_changes([revid])[0]
        file_changes = history.get_file_changes(change)
        history.add_branch_nicks(change)

        return {
            'entry': change,
            'file_changes': file_changes,
            'revid': revid,
        }

    def get_json_values(self, environ):
        core_values, headers = self.get_core_values(environ)
        return core_values, headers
