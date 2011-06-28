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

    def __init__(self):
        self._buffer = []

    def write(self, s):
        self._buffer.append(s)

    def get_buffer(self):
        try:
            return ''.join(self._buffer)
        finally:
            self._buffer = []


def export_archive(history, root, revid, format=".tar.gz"):
    """Export tree contents to an archive

    :param history: Instance of history to export
    :param root: Root location inside the archive.
    :param revid: Revision to export
    :param format: Format of the archive
    """
    fileobj = ExporterFileObject()
    tree = history._branch.repository.revision_tree(revid)
    for _ in get_export_generator(tree=tree, root=root, fileobj=fileobj, format=format):
        yield fileobj.get_buffer()
    # Might have additonal contents written
    yield fileobj.get_buffer()
