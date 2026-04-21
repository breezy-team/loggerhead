use std::net::IpAddr;
use std::path::PathBuf;

use clap::Parser;

#[derive(Parser, Debug, Clone)]
#[command(
    name = "loggerhead-serve",
    about = "Web viewer for Bazaar/Breezy branches"
)]
pub struct Args {
    /// Path or URL of the branch (or root directory of branches) to serve.
    #[arg(value_name = "PATH_OR_URL")]
    pub root: String,

    /// Port to listen on.
    #[arg(long, default_value_t = 8080)]
    pub port: u16,

    /// Host address to bind to.
    #[arg(long, default_value = "0.0.0.0")]
    pub host: IpAddr,

    /// URL prefix, for deployment behind a reverse proxy.
    #[arg(long, default_value = "")]
    pub prefix: String,

    /// Path to the on-disk revision-info cache (SQLite).
    #[arg(long, value_name = "DIR")]
    pub cachepath: Option<PathBuf>,

    /// Allow tarball downloads of revisions.
    #[arg(long, default_value_t = true)]
    pub export_tarballs: bool,

    /// Directory to write log files to (currently logs are still emitted to
    /// stderr; this flag is accepted for CLI-compat with the Python
    /// implementation and reserved for future file-logging support).
    #[arg(long, value_name = "DIR")]
    pub log_folder: Option<PathBuf>,

    /// Log level (matches Python loggerhead's `--log-level`). One of
    /// `trace`, `debug`, `info`, `warn`, `error`.
    #[arg(long, value_name = "LEVEL")]
    pub log_level: Option<String>,

    /// Directory of static CSS/JS/image assets to serve under `/static`.
    /// Defaults to the Python loggerhead static dir shipped with this
    /// checkout; override for a Debian install (e.g. `/usr/share/loggerhead/static`).
    #[arg(long, value_name = "DIR")]
    pub static_dir: Option<PathBuf>,

    /// Serve the root as a directory of user branches. Each
    /// `<root>/<user>/<branch>` is exposed at `/~<user>/<branch>/`.
    /// Useful for Launchpad-style layouts.
    #[arg(long)]
    pub user_dirs: bool,

    /// When `--user-dirs` is set, the subdirectory under `<root>`
    /// that contains "trunk" branches to serve under `/` without
    /// the `~user` prefix. No-op otherwise.
    #[arg(long, value_name = "DIR")]
    pub trunk_dir: Option<String>,
}
