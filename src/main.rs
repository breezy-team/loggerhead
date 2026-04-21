use std::net::SocketAddr;
use std::sync::Arc;

use clap::Parser;
use tracing_subscriber::{EnvFilter, FmtSubscriber};

use loggerhead::app::{build_router, AppState};
use loggerhead::cache::RevInfoDiskCache;
use loggerhead::config::Args;

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
        // Default to the sibling Python loggerhead static dir so a checkout
        // "just works" without a separate install step.
        std::path::PathBuf::from(env!("CARGO_MANIFEST_DIR")).join("loggerhead/static")
    });
    if !static_dir.is_dir() {
        tracing::warn!(path = ?static_dir, "static asset directory not found; /static/* will 404");
    }

    let state = Arc::new(AppState::new(
        args.root.clone(),
        disk_cache,
        args.export_tarballs,
        static_dir,
        args.user_dirs,
        args.trunk_dir.clone(),
    ));

    let router = build_router(state);

    tracing::info!(%addr, root = %args.root, "loggerhead starting");
    let listener = tokio::net::TcpListener::bind(addr).await?;
    axum::serve(listener, router).await?;
    Ok(())
}
