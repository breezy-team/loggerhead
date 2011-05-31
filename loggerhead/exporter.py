
import tarfile
import StringIO

from bzrlib.export import _export_iter_entries
from bzrlib import osutils
from bzrlib import errors
from bzrlib.filters import ContentFilterContext
from bzrlib.filters import filtered_output_bytes



class TarExporterFileObject(object):
    
    def __init__(self):
        ""
        
class TarExporter(object):
    """Iterator that exports a tarball"""
    
    def __init__(self, revid, history):
        self.fileobj = TarExporterFileObject()
        self.ball = tarfile.open(None, 'w:gz', self.fileobj)
        rev_tree = self.history._branch.repository.revision_tree(revid)
        
        
    def __iter__(self):
        return self
    
    def next(self):
        ""

def export_tarball(history, revid):
    """Export tree contents to a tarball.

    :param history: Instance of history to export
    :param revid: Revision to export
    """
    
    root = None
    subdir = None
    filtered = False
    force_mtime = None
    
    fileobj = TarExporterFileObject()
    
    ball = tarfile.open(None, 'w:gz', fileobj)
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
            if filtered:
                chunks = tree.get_file_lines(ie.file_id)
                filters = tree._content_filter_stack(dp)
                context = ContentFilterContext(dp, tree, ie)
                contents = filtered_output_bytes(chunks, filters, context)
                content = ''.join(contents)
                item.size = len(content)
                fileobj = StringIO.StringIO(content)
            else:
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

        
        