from StringIO import StringIO
import urllib

from bzrlib import diff
from bzrlib import errors

from loggerhead import util
from loggerhead.controllers import TemplatedBranchView

def _process_diff(difftext):
    # doesn't really need to be a method; could be static.
    chunks = []
    chunk = None
    for line in difftext.splitlines():
        if len(line) == 0:
            continue
        if line.startswith('+++ ') or line.startswith('--- '):
            continue
        if line.startswith('@@ '):
            # new chunk
            if chunk is not None:
                chunks.append(chunk)
            chunk = util.Container()
            chunk.diff = []
            split_lines = line.split(' ')[1:3]
            lines = [int(x.split(',')[0][1:]) for x in split_lines]
            old_lineno = lines[0]
            new_lineno = lines[1]
        elif line.startswith(' '):
            chunk.diff.append(util.Container(old_lineno=old_lineno,
                                             new_lineno=new_lineno,
                                             type='context',
                                             line=line[1:]))
            old_lineno += 1
            new_lineno += 1
        elif line.startswith('+'):
            chunk.diff.append(util.Container(old_lineno=None,
                                             new_lineno=new_lineno,
                                             type='insert', line=line[1:]))
            new_lineno += 1
        elif line.startswith('-'):
            chunk.diff.append(util.Container(old_lineno=old_lineno,
                                             new_lineno=None,
                                             type='delete', line=line[1:]))
            old_lineno += 1
        else:
            chunk.diff.append(util.Container(old_lineno=None,
                                             new_lineno=None,
                                             type='unknown',
                                             line=repr(line)))
    if chunk is not None:
        chunks.append(chunk)
    return chunks


def diff_chunks_for_file(repository, file_id, new_revid, old_revid):
    print old_revid == new_revid
    old_tree, new_tree = repository.revision_trees([old_revid, new_revid])
    try:
        old_lines = old_tree.get_file_lines(file_id)
    except errors.NoSuchId:
        old_lines = []
    try:
        new_lines = new_tree.get_file_lines(file_id)
    except errors.NoSuchId:
        new_lines = []
    buffer = StringIO()
    if old_lines != new_lines:
        try:
            diff.internal_diff('', old_lines, '', new_lines, buffer)
        except errors.BinaryFile:
            difftext = ''
        else:
            difftext = buffer.getvalue()
    else:
        difftext = ''

    print repr(difftext)

    return _process_diff(difftext)


class FileDiffUI(TemplatedBranchView):

    template_path = 'loggerhead.templates.filediff'

    def get_values(self, path, kwargs, headers):
        history = self._history

        revid = urllib.unquote(self.args[0])
        compare_revid = urllib.unquote(self.args[1])
        file_id = urllib.unquote(self.args[2])

        chunks = diff_chunks_for_file(
            self._history._branch.repository, file_id, revid, compare_revid)

        return {
            'util': util,
            'chunks': chunks,
        }
