"""Exports an archive from a bazaar branch"""

from bzrlib.export import get_export_generator

class ExporterFileObject(object):
    
    def __init__(self):
        self._buffer = []
        
    def write(self, str):
        self._buffer.append(str)
        
    def get_buffer(self):
        try:
            return ''.join(self._buffer)
        finally:
            self._buffer = []
        
def export_archive(history, revid, format=".tar.gz"):
    """Export tree contents to an archive

    :param history: Instance of history to export
    :param revid: Revision to export
    :param format: Format of the archive
    """
    
    fileobj = ExporterFileObject()
    
    tree = history._branch.repository.revision_tree(revid)
    
    for _ in get_export_generator(tree=tree, fileobj=fileobj, format=format):
        
        yield fileobj.get_buffer()

    
        