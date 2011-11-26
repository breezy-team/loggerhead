# Copyright (C) 2011 Canonical Ltd
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
"""Exports an archive from a bazaar branch"""

from bzrlib.export import get_export_generator


class ExporterFileObject(object):
    """Shim that accumulates temporarily written out data.

    There are python tarfile classes that want to write to a file like object.
    We want to stream data.  But wsgi assumes it can pull data from the
    handler, rather than having bytes pushed.

    So this class holds the data temporarily, until it is pulled.  It 
    should never buffer everything because as soon as a chunk is produced, 
    wsgi will be given the chance to take it.
    """

    def __init__(self):
        self._buffer = []

    def write(self, s):
        self._buffer.append(s)

    def get_buffer(self):
        try:
            return ''.join(self._buffer)
        finally:
            self._buffer = []

    def close(self):
        pass


def export_archive(history, root, revid, archive_format):
    """Export tree contents to an archive

    :param history: Instance of history to export
    :param root: Root location inside the archive.
    :param revid: Revision to export
    :param archive_format: Format of the archive, eg 'tar.gz'.
    """
    fileobj = ExporterFileObject()
    tree = history._branch.repository.revision_tree(revid)
    for _ in get_export_generator(tree=tree, root=root, fileobj=fileobj,
        format=archive_format):
        yield fileobj.get_buffer()
    # Might have additonal contents written
    yield fileobj.get_buffer()
