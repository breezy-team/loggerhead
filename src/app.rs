use std::sync::Arc;

use axum::response::Redirect;
use axum::{routing::get, Router};
use moka::sync::Cache;
use tower_http::services::ServeDir;
use tower_http::trace::TraceLayer;

use breezyshim::branch::Branch;
use breezyshim::revisionid::RevisionId;

use crate::cache::RevInfoDiskCache;
use crate::controllers::{changelog, revision};
use crate::history::WholeHistory;
use crate::util::errors::AppError;

/// Shared application state handed to every handler.
pub struct AppState {
    /// Location (filesystem path or URL) of the branch being served.
    pub root: String,
    /// Cached whole-branch graph, invalidated when the branch tip changes.
    pub whole_history_cache: Cache<RevisionId, Arc<WholeHistory>>,
    /// Optional SQLite-backed persistent cache.
    pub disk_cache: Option<Arc<RevInfoDiskCache>>,
    /// Whether tarball exports are permitted.
    pub export_tarballs: bool,
    /// Filesystem directory containing CSS/JS/image assets (served under
    /// `/static`).
    pub static_dir: std::path::PathBuf,
}

impl AppState {
    pub fn new(
        root: String,
        disk_cache: Option<Arc<RevInfoDiskCache>>,
        export_tarballs: bool,
        static_dir: std::path::PathBuf,
    ) -> Self {
        Self {
            root,
            whole_history_cache: Cache::new(10),
            disk_cache,
            export_tarballs,
            static_dir,
        }
    }

    /// Fetch the whole-history for `branch`'s current tip, consulting the
    /// in-memory LRU and optional disk cache, computing + storing on miss.
    /// Must be called from a blocking context (holds the GIL).
    pub fn load_whole_history(&self, branch: &dyn Branch) -> Result<Arc<WholeHistory>, AppError> {
        let tip = branch.last_revision();
        if let Some(w) = self.whole_history_cache.get(&tip) {
            return Ok(w);
        }
        if let Some(from_disk) = self
            .disk_cache
            .as_ref()
            .and_then(|d| d.get_whole_history(&tip))
        {
            tracing::debug!("whole_history: disk cache hit");
            let w = Arc::new(from_disk);
            self.whole_history_cache.insert(tip, w.clone());
            return Ok(w);
        }
        tracing::debug!("whole_history: computing (miss on memory & disk)");
        let computed = WholeHistory::compute(branch)?;
        if let Some(d) = self.disk_cache.as_ref() {
            d.set_whole_history(&tip, &computed);
        }
        let w = Arc::new(computed);
        self.whole_history_cache.insert(tip, w.clone());
        Ok(w)
    }
}

/// Permanent redirect to `/changes`, matching Python loggerhead's root
/// behaviour (see `apps/branch.py::lookup_app`).
async fn root_redirect() -> Redirect {
    Redirect::permanent("/changes")
}

pub fn build_router(state: Arc<AppState>) -> Router {
    use crate::controllers::{
        annotate, atom, diff, download, filediff, inventory, revlog, search, view,
    };
    Router::new()
        .route("/", get(root_redirect))
        .route("/changes", get(changelog::show))
        .route("/revision/:revid", get(revision::show))
        .route("/diff/:new_revid", get(diff::show_one))
        .route("/diff/:new_revid/:old_revid", get(diff::show_two))
        .route(
            "/+filediff/:new_revid/:old_revid/*path",
            get(filediff::show),
        )
        .route("/files", get(inventory::show_root))
        .route("/files/:revno", get(inventory::show_rev))
        .route("/files/:revno/*path", get(inventory::show_rev_path))
        .route("/view/:revno/*path", get(view::show))
        .route("/annotate/:revno/*path", get(annotate::show))
        .route("/download/:revid/*path", get(download::show_file))
        .route("/tarball/:revid", get(download::tarball))
        .route("/atom", get(atom::show))
        .route("/+revlog/:revid", get(revlog::show))
        .route("/search", get(search::show))
        .nest_service("/static", ServeDir::new(&state.static_dir))
        .layer(TraceLayer::new_for_http())
        .with_state(state)
}
