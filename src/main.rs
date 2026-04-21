use std::net::SocketAddr;
use std::sync::Arc;

use axum::Router;
use clap::Parser;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

use loggerhead::app::{build_router, AppState};
use loggerhead::cache::RevInfoDiskCache;
use loggerhead::config::Args;

/// Normalize a `--prefix` value: empty stays empty; otherwise a leading `/`
/// is ensured and any trailing `/` stripped, so it composes cleanly into
/// URLs as `{prefix}{path}`.
fn normalize_prefix(raw: &str) -> String {
    let trimmed = raw.trim_end_matches('/');
    if trimmed.is_empty() {
        return String::new();
    }
    if trimmed.starts_with('/') {
        trimmed.to_string()
    } else {
        format!("/{trimmed}")
    }
}

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let args = Args::parse();

    // Precedence: RUST_LOG env var → --log-level flag → info.
    let filter = EnvFilter::try_from_default_env().unwrap_or_else(|_| {
        args.log_level
            .as_deref()
            .unwrap_or("info")
            .parse::<EnvFilter>()
            .unwrap_or_else(|_| EnvFilter::new("info"))
    });
    FmtSubscriber::builder().with_env_filter(filter).init();

    if let Some(dir) = &args.log_folder {
        tracing::info!(path = ?dir, "--log-folder accepted but file logging is not yet implemented; logging to stderr");
    }

    // Matches Python's "--trunk-dir is only valid with --user-dirs"
    // and "--user-dirs requires --trunk-dir" validations.
    if args.trunk_dir.is_some() && !args.user_dirs {
        anyhow::bail!("--trunk-dir is only valid with --user-dirs");
    }
    if args.user_dirs && args.trunk_dir.is_none() {
        anyhow::bail!("--user-dirs requires --trunk-dir");
    }

    // Initialize breezy/Python once on the main thread.
    breezyshim::init();

    let disk_cache = match &args.cachepath {
        Some(p) => match RevInfoDiskCache::open(p) {
            Ok(c) => Some(Arc::new(c)),
            Err(e) => {
                tracing::warn!(path = ?p, error = %e, "disabling disk cache");
                None
            }
        },
        None => None,
    };

    let addr = SocketAddr::new(args.host, args.port);
    let static_dir = args.static_dir.clone().unwrap_or_else(|| {
        // Default to the in-tree `static/` dir so a checkout "just works"
        // without a separate install step.
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("static")
    });
    if !static_dir.is_dir() {
        tracing::warn!(path = ?static_dir, "static asset directory not found; /static/* will 404");
    }

    let prefix = normalize_prefix(&args.prefix);

    let state = Arc::new(AppState::new(
        args.root.clone(),
        disk_cache,
        args.export_tarballs,
        static_dir,
        args.user_dirs,
        args.trunk_dir.clone(),
        prefix.clone(),
    ));

    let inner = build_router(state);
    let router = if prefix.is_empty() {
        inner
    } else {
        // Serve the same app under `<prefix>/…` when deployed behind a
        // reverse proxy that forwards the original path.
        Router::new().nest(&prefix, inner)
    };

    tracing::info!(%addr, root = %args.root, prefix = %args.prefix, "loggerhead starting");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, router).await?;
    Ok(())
}
