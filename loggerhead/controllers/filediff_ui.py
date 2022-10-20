from io import BytesIO

from breezy import (
    diff,
    errors,
    urlutils,
    )
try:
    from breezy.transport import NoSuchFile
except ImportError:
    from breezy.errors import NoSuchFile
from breezy.tree import find_previous_path

from .. import util
from ..controllers import TemplatedBranchView


def _process_diff(difftext):
    chunks = []
    chunk = None

    def decode_line(line):
        return line.decode('utf-8', 'replace')
    for line in difftext.splitlines():
        if len(line) == 0:
            continue
        if line.startswith(b'+++ ') or line.startswith(b'--- '):
            continue
        if line.startswith(b'@@ '):
            # new chunk
            if chunk is not None:
                chunks.append(chunk)
            chunk = util.Container()
            chunk.diff = []
            split_lines = line.split(b' ')[1:3]
            lines = [int(x.split(b',')[0][1:]) for x in split_lines]
            old_lineno = lines[0]
            new_lineno = lines[1]
        elif line.startswith(b' '):
            chunk.diff.append(util.Container(old_lineno=old_lineno,
                                             new_lineno=new_lineno,
                                             type='context',
                                             line=decode_line(line[1:])))
            old_lineno += 1
            new_lineno += 1
        elif line.startswith(b'+'):
            chunk.diff.append(util.Container(
                old_lineno=None,
                new_lineno=new_lineno,
                type='insert', line=decode_line(line[1:])))
            new_lineno += 1
        elif line.startswith(b'-'):
            chunk.diff.append(util.Container(
                old_lineno=old_lineno,
                new_lineno=None,
                type='delete', line=decode_line(line[1:])))
            old_lineno += 1
        else:
            chunk.diff.append(util.Container(
                old_lineno=None,
                new_lineno=None,
                type='unknown',
                line=repr(line)))
    if chunk is not None:
        chunks.append(chunk)
    return chunks


def diff_chunks_for_file(repository, filename, compare_revid, revid,
                         context_lines=None):
    if context_lines is None:
        context_lines = 3
    lines = {}
    compare_tree = repository.revision_tree(compare_revid)
    tree = repository.revision_tree(revid)
    try:
        lines[revid] = tree.get_file_lines(filename)
    except NoSuchFile:
        lines[revid] = []
        lines[compare_revid] = compare_tree.get_file_lines(filename)
    else:
        compare_filename = find_previous_path(tree, compare_tree, filename)
        if compare_filename is not None:
            lines[compare_revid] = compare_tree.get_file_lines(compare_filename)
        else:
            lines[compare_revid] = []

    buffer = BytesIO()
    try:
        diff.internal_diff(
            '', lines[compare_revid], '', lines[revid], buffer,
            context_lines=context_lines)
    except errors.BinaryFile:
        difftext = b''
    else:
        difftext = buffer.getvalue()

    return _process_diff(difftext)


class FileDiffUI(TemplatedBranchView):

    template_name = 'filediff'
    supports_json = True

    def get_values(self, path, kwargs, headers):
        revid = urlutils.unquote_to_bytes(self.args[0])
        compare_revid = urlutils.unquote_to_bytes(self.args[1])
        filename = urlutils.unquote(self.args[2])

        try:
            context_lines = int(kwargs['context'])
        except (KeyError, ValueError):
            context_lines = None

        chunks = diff_chunks_for_file(
            self._history._branch.repository, filename, compare_revid, revid,
            context_lines=context_lines)

        return {
            'chunks': chunks,
        }
