# Loggerhead

Loggerhead is a web viewer for [Bazaar] / [Breezy] branches. It can be
used to navigate a branch's history, annotate files, view patches,
download tarballs, and search commit messages.

Loggerhead is distantly based on [bazaar-webserve], which was itself
loosely based on [hgweb] for Mercurial.

This branch of Loggerhead is written in Rust and uses [breezyshim] to
talk to Breezy.

[Bazaar]: https://bazaar.canonical.com/
[Breezy]: https://www.breezy-vcs.org/
[bazaar-webserve]: https://launchpad.net/bzr-webserve
[hgweb]: https://www.mercurial-scm.org/wiki/HgWebDirStepByStep
[breezyshim]: https://github.com/breezy-team/breezyshim
