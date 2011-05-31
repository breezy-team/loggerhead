
import tarfile

from bzrlib.export import _export_iter_entries
from bzrlib import osutils
from bzrlib import errors

class TarExporterFileObject(object):
    
    def __init__(self):
        self._buffer = ''
    
    def write(self, str):
        self._buffer += str
    
    def get_buffer(self):
        buffer = self._buffer
        self._buffer = ''
        return buffer

        
def export_tarball(history, revid):
    """Export tree contents to a tarball.

    :param history: Instance of history to export
    :param revid: Revision to export
    """
    
    root = None
    subdir = None
    force_mtime = None
    
    tarfileobj = TarExporterFileObject()
    
    ball = tarfile.open(None, 'w:gz', tarfileobj)
    tree = history._branch.repository.revision_tree(revid)
    
    #TODO: remove unnecessary code
    
    for dp, ie in _export_iter_entries(tree, subdir):
        filename = osutils.pathjoin(root, dp).encode('utf8')
        item = tarfile.TarInfo(filename)
        if force_mtime is not None:
            item.mtime = force_mtime
        else:
            item.mtime = tree.get_file_mtime(ie.file_id, dp)
        if ie.kind == "file":
            item.type = tarfile.REGTYPE
            if tree.is_executable(ie.file_id):
                item.mode = 0755
            else:
                item.mode = 0644
            item.size = tree.get_file_size(ie.file_id)
            fileobj = tree.get_file(ie.file_id)
        elif ie.kind == "directory":
            item.type = tarfile.DIRTYPE
            item.name += '/'
            item.size = 0
            item.mode = 0755
            fileobj = None
        elif ie.kind == "symlink":
            item.type = tarfile.SYMTYPE
            item.size = 0
            item.mode = 0755
            item.linkname = tree.get_symlink_target(ie.file_id)
            fileobj = None
        else:
            raise errors.BzrError("don't know how to export {%s} of kind %r" %
                           (ie.file_id, ie.kind))
        ball.addfile(item, fileobj)
        yield tarfileobj.get_buffer()

        
        