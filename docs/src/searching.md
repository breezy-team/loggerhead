# Searching

Loggerhead's `/search` page is backed by the [`bzr-search`] Breezy
plugin. You need to have the plugin installed in the Python environment
that Loggerhead is calling into, and each branch must be indexed before
its contents become searchable.

Indexing a branch is a Breezy-side operation:

```sh
brz index /path/to/branch
```

If the plugin isn't available or the branch hasn't been indexed, the
`/search` page renders a "search unavailable" notice rather than
erroring out.

[`bzr-search`]: https://launchpad.net/bzr-search
