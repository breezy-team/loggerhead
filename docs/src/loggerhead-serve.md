# `loggerhead-serve`

`loggerhead-serve` runs a standalone Loggerhead HTTP server in the
foreground.

## Usage

```sh
loggerhead-serve [OPTIONS] <PATH_OR_URL>
```

`<PATH_OR_URL>` is either a single branch or a directory of branches
(see `--user-dirs` for the Launchpad-style layout).

## Options

### `--port <PORT>`

Port to listen on. Defaults to `8080`.

### `--host <HOST>`

Host address to bind to. Defaults to `0.0.0.0` (all interfaces).

### `--prefix <PREFIX>`

URL prefix, for use when Loggerhead is mounted under a sub-path behind
a reverse proxy. For example, if the proxy forwards
`https://example.com/bzr/` to Loggerhead, pass `--prefix=/bzr`.

### `--cache-dir <DIR>` (alias: `--cachepath`)

Directory to place the on-disk revision-info cache (SQLite). The cache
is optional — if it's not configured, Loggerhead recomputes history
from the branch on every cold request.

### `--export-tarballs`

Allow tarball downloads of revisions. Enabled by default. Pass
`--export-tarballs=false` to disable.

### `--log-folder <DIR>`

Directory to write log files to. Accepted for CLI compatibility with
the Python implementation; currently logs are still emitted to stderr.

### `--log-level <LEVEL>`

Log level. One of `trace`, `debug`, `info`, `warn`, `error`. You can
also set `RUST_LOG` in the environment.

### `--static-dir <DIR>`

Directory of static CSS/JS/image assets to serve under `/static`.
Defaults to the `static/` directory shipped with the source checkout;
Debian-packaged installs typically point this at
`/usr/share/loggerhead/static`.

### `--user-dirs`

Serve the root as a directory of user branches. Each
`<root>/<user>/<branch>` is exposed at `/~<user>/<branch>/`. Requires
`--trunk-dir`.

### `--trunk-dir <DIR>`

When `--user-dirs` is set, the subdirectory under `<root>` whose
branches are served under `/` without the `~user` prefix.

### `-h`, `--help`

Print help and exit.

### `--version`

Print the software version and exit.
