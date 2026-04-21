# Getting started

## Building

Loggerhead is a Rust crate. You need a recent stable Rust toolchain and
a working Python environment (Breezy is invoked through PyO3 via
[breezyshim]).

```sh
cargo build --release
```

The resulting binary is `target/release/loggerhead-serve`.

## Running

Point `loggerhead-serve` at a branch or a directory of branches:

```sh
./target/release/loggerhead-serve ~/path/to/branch
```

By default the server listens on port 8080, so browse to
<http://localhost:8080/> to see the branch.

If you pass a directory that contains several branches, Loggerhead
presents a simple directory listing at `/`, with each branch mounted
under `/<name>/`.

Loggerhead re-reads the branch data on every request, so you can update
your branches while the server is running and see the changes the next
time you reload.

See [`loggerhead-serve`](./loggerhead-serve.md) for every command-line
option.

## Hiding branches

To hide a branch from Loggerhead, add the following to
`~/.config/breezy/locations.conf` under the branch's section:

```ini
[/path/to/branch]
http_serve = False
```

[breezyshim]: https://github.com/breezy-team/breezyshim
