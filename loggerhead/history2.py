"""Extract data suitable for web presentation from Bazaar branches.

The module is the interface between Loggerhead and bzrlib.  Other code in
Loggerhead should not use bzrlib APIs, and functions and methods in this
module should not return bzrlib data types.

The core method is `History.getRevisionInfo`.  This method is meant to be
cheap, so you should not worry about calling it multiple times with the same
argument or calling it just to retreive a subset of the information it
returns.

Revisions are described using good old bzrlib revision ids.

Revision ids, file ids, file names and file paths are always utf-8 encoded 8
bit strings.
"""

class FileDelta(object):
    """Information about how an inventory entry changed in a revision.

    All attribute names are fairly self explanatory.  The ``*_parent`` fields
    are the file id of the parent or ``None`` for the root.

    :ivar file_id:
    :ivar old_path:
    :ivar new_path:
    :ivar old_name:
    :ivar new_name:
    :ivar old_parent:
    :ivar new_parent:
    :ivar old_kind:
    :ivar new_kind:
    :ivar content_change:
    :type content_change: ``bool``
    :ivar execute_change: A boolean reflecting the new state if it changed, or
                          ``None`` if it did not.
    :type execute_change: ``bool`` or ``None``
    """


class FileChanges(object):
    """Contains information about which files changed in a revision.

    Note that the 'files changed' information is relative to left-most parent
    by default, as in 'bzr log -v'.

    :ivar deltas: A list of `FileDelta` objects.
    :ivar fileset: ``set(d.file_id for d in self.deltas)``, but cached.
    """

class RevisionInfo(object):
    """Contains all the immutable information Loggerhead needs about a
    particular revision.

    :ivar revid: Obvious.
    :ivar date: The date and time this revision was committed.
    :type date: ``datetime.datetime``
    :ivar committer: The committer.
    :type committer: utf-8 encoded ``str``
    :ivar revprops: The branch properties.
    :type revprops: A dictionary mapping ``str``\ s to ``str``\ s (both utf-8
                    encoded).
    :ivar message: The commit message of this revision.
    :type message: utf-8 encoded ``str``
    :ivar parents: The list of the revids of the revision's parents.
    """

class BranchRevisionInfo(object):
    """Contains all the mutable information Loggerhead needs about a
    particular revision, and points to the immutable data.

    :ivar revno: The dotted revno of this revision in this branch.
    :type revno: ``str``
    :ivar where_merged: The list of revids that have this revision as a
                        parent.
    :ivar info: The corresponding `RevisionInfo`.
    """

class FileEntry(object):
    """An entry in the list returned by `getFileList`.

    :ivar path: The path of the object in the revision passed to
                `getFileList`.
    :ivar fileid: Obvious.
    :ivar kind: one of ``'file'``, ``'executable'``, ``'link'`` or
                ``'directory'``.
    :type kind: ``str``
    :ivar last_changed_revid: The revid of the revision in which this path
                              last changed.  Not that this is recursive,
                              i.e. the last_changed_revid for a directory is
                              the revid in which the directory or anything
                              contained in in changed.x
    :ivar size: The size of this object in this revision in bytes.
    :type size: ``int``
    """

class History(object):
    """Provide the information loggerhead needs about a bzrlib Branch.

    An instance of this class is effectively a wrapper around a
    `bzrlib.branch.Branch` that translates the information provided by bzrlib
    into a form convenient for use in loggerhead.

    :ivar last_revision: The revid of the tip of the branch.
    """

    @classmethod
    def fromBranch(cls, branch):
        """Create and initialize a `History` object from a
        `bzrlib.branch.Branch`.
        """

    def outOfDate(self):
        """Decide whether this History object is still current.

        At least to start with, an out of date History object should be thrown
        away and a fresh one created.
        """

    def getRevisionInfo(self, revid):
        """Find the `BranchRevisionInfo` object for a given revision id.

        This operation is to be thought of as 'cheap', which is to say that
        you should not worry about calling it repeatedly with the same
        argument or about calling it just to retrieve a subset of the
        information it includes.

        :param revid: a revision id.
        :returns: a `BranchRevisionInfo` object or ``None`` if the given
                  revision id does not exist in the branch.
        """

    def getChanges(self, revid, other_revid=None):
        """Find the `FileChanges` object between two revision.

        :param revid: A revision id.
        :param other_revid: The revision id to compare against.  If ``None``
                            or not given, compare against the leftmost parent
                            of ``revid``.
        :returns: The corresponding `FileChanges` object.
        """

    # There will need to be some more methods here to allow searching for
    # revisions by date, committer, commit message, etc...

    def getDiff(self, revidA, revidB):
        """Compute the diff between two revisions.

        Not sure what this will return yet, probably something similar to but
        more structured than the 'chunks' loggerhead already works with.
        """

    def getDirList(self, fileid, revid):
        """List the files in the given directory as of the given revision.

        :return: a list of `FileEntry` objects.
        """

    def getFileAnnotation(self, fileid, revid):
        """Annotate the given file.

        Not sure what this should return, mostly likely a list of
        (revid-or-None, line contents) (and ``None`` for a binary file).
        """

    def getFileText(self, fileid, revid):
        """Fetch the contents of a file at a particular revision.

        :returns: (filename, data)
        :rtype: ``(str, str)``
        """

    def getBundle(self, revid, compare_revid=None):
        """Return a bundle for this revision.

        Relative to compare_revid, or left-most parent if this is not supplied
        or None.

        :return: A bundle (in a string).
        """

    def normalizeRevivionSpec(self, revspec):
        """Convert a revid or revno or 'head' to a revid.

        :returns: a revision id.
        """

    def normalizeFileArguments(self, revid, fileid, filepath):
        """Handle various ways of specifying a file in the branch.

        One of ``fileid`` and ``filepath`` should be None.

        :returns: (fileid, filepath)
        """
