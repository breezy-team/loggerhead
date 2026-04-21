use std::sync::Arc;

use axum::extract::{Request, State};
use axum::http::{header, HeaderValue, StatusCode};
use axum::middleware::Next;
use axum::response::{IntoResponse, Redirect, Response};
use axum::{routing::get, Router};
use chrono::{DateTime, Utc};
use moka::sync::Cache;
use tower_http::services::ServeDir;
use tower_http::trace::TraceLayer;

use breezyshim::branch::Branch;
use breezyshim::revisionid::RevisionId;

use crate::cache::RevInfoDiskCache;
use crate::history::WholeHistory;
use crate::util::errors::AppError;

/// Shared application state handed to every handler.
pub struct AppState {
    /// Location (filesystem path or URL) of the branch served by this
    /// router instance. In directory mode each sub-branch gets its own
    /// nested `AppState`, so every handler can just read this without
    /// knowing whether we're in single- or multi-branch mode.
    pub root: String,
    /// URL prefix under which this branch is served. Empty (`""`) in
    /// single-branch mode; `"/<name>"` in directory mode. Every
    /// template-facing link computed by a controller is prefixed with
    /// this so that output works behind an additional mount point.
    pub url_prefix: String,
    /// Whether `root` is a single branch or a directory of branches.
    /// Only meaningful on the top-level AppState; the per-branch
    /// AppState created for each nested directory mount is always
    /// `ServeMode::Branch`.
    pub serve_mode: ServeMode,
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
        user_dirs: bool,
        trunk_dir: Option<String>,
    ) -> Self {
        let serve_mode = detect_serve_mode(&root, user_dirs, trunk_dir);
        Self {
            root,
            url_prefix: String::new(),
            serve_mode,
            whole_history_cache: Cache::new(10),
            disk_cache,
            export_tarballs,
            static_dir,
        }
    }

    /// Build a per-branch `AppState` for a sub-branch inside a
    /// directory-mode deployment. Shares the disk cache and static-dir
    /// with the parent; gets its own in-memory history cache.
    pub fn nested(parent: &AppState, root: String, name: &str) -> Self {
        Self {
            root,
            url_prefix: format!("/{name}"),
            serve_mode: ServeMode::Branch,
            whole_history_cache: Cache::new(10),
            disk_cache: parent.disk_cache.clone(),
            export_tarballs: parent.export_tarballs,
            static_dir: parent.static_dir.clone(),
        }
    }

    /// Produce an absolute URL for `path` under this branch's prefix.
    pub fn url(&self, path: &str) -> String {
        if self.url_prefix.is_empty() {
            path.to_string()
        } else {
            format!("{}{}", self.url_prefix, path)
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
async fn root_redirect(
    axum::extract::State(state): axum::extract::State<Arc<AppState>>,
) -> Redirect {
    Redirect::permanent(&state.url("/changes"))
}

/// Returns the most recent tip-timestamp known for this branch, if any.
/// We consult the in-memory LRU by picking the maximum timestamp across
/// currently-cached `WholeHistory` entries. Usually there's just one.
fn cached_last_modified(state: &AppState) -> Option<f64> {
    let mut best: Option<f64> = None;
    for (_, wh) in state.whole_history_cache.iter() {
        if let Some(t) = wh.tip_timestamp {
            best = Some(best.map_or(t, |b| b.max(t)));
        }
    }
    best
}

/// Axum middleware that adds `Last-Modified` to successful responses
/// and short-circuits to 304 Not Modified when the client's
/// `If-Modified-Since` is at least as new as the branch tip. Only
/// attached to per-branch HTML routers.
async fn last_modified_layer(
    State(state): State<Arc<AppState>>,
    req: Request,
    next: Next,
) -> Response {
    let ims = req
        .headers()
        .get(header::IF_MODIFIED_SINCE)
        .and_then(|v| v.to_str().ok())
        .and_then(|s| httpdate::parse_http_date(s).ok());
    let last_ts = cached_last_modified(&state);

    if let (Some(ims), Some(ts)) = (ims, last_ts) {
        let tip_secs = ts as i64;
        let ims_secs = ims
            .duration_since(std::time::UNIX_EPOCH)
            .map(|d| d.as_secs() as i64)
            .unwrap_or(0);
        if ims_secs >= tip_secs {
            return StatusCode::NOT_MODIFIED.into_response();
        }
    }

    let mut resp = next.run(req).await;
    if resp.status().is_success() {
        if let Some(ts) = last_ts {
            if let Some(dt) = DateTime::<Utc>::from_timestamp(ts as i64, 0) {
                let rfc = dt.format("%a, %d %b %Y %H:%M:%S GMT").to_string();
                if let Ok(v) = HeaderValue::from_str(&rfc) {
                    resp.headers_mut().insert(header::LAST_MODIFIED, v);
                }
            }
        }
    }
    resp
}

/// Serve mode determined at startup.
#[derive(Clone, Debug)]
pub enum ServeMode {
    /// `root` points directly at a single branch.
    Branch,
    /// `root` is a directory containing branches at `<root>/<name>`.
    /// `/` shows a listing; `/<name>/…` drills into the branch.
    Directory,
    /// `root` is a directory structured as `<root>/<user>/<branch>`.
    /// Each user branch is exposed at `/~<user>/<branch>/…`.
    /// Optionally a `trunk_dir` subdir under `<root>` hosts
    /// "common" branches served at `/<branch>/…` without a
    /// `~user` prefix.
    UserDirs {
        /// Subdirectory under `<root>` whose children are branches
        /// served at `/<name>/`. `None` means no trunk section.
        trunk_dir: Option<String>,
    },
}

/// Detect at startup whether `root` is itself a branch or a directory
/// containing branches. The `user_dirs_config` option forces UserDirs
/// mode regardless of whether `root` itself is openable as a branch.
/// Errors fall back to Branch mode — the per-branch handlers will
/// produce a sensible error on the first request.
pub fn detect_serve_mode(root: &str, user_dirs: bool, trunk_dir: Option<String>) -> ServeMode {
    if user_dirs {
        return ServeMode::UserDirs { trunk_dir };
    }
    if crate::breezy::open_branch(root).is_ok() {
        ServeMode::Branch
    } else if std::path::Path::new(root).is_dir() {
        ServeMode::Directory
    } else {
        ServeMode::Branch
    }
}

pub fn build_router(state: Arc<AppState>) -> Router {
    match &state.serve_mode {
        ServeMode::Directory => build_directory_router(state),
        ServeMode::Branch => build_branch_router(state),
        ServeMode::UserDirs { trunk_dir } => {
            let trunk = trunk_dir.clone();
            build_user_dirs_router(state, trunk)
        }
    }
}

fn build_directory_router(state: Arc<AppState>) -> Router {
    use crate::controllers::directory;
    let static_dir = state.static_dir.clone();
    let subdirs = list_subdirs(&state.root);
    let top = Router::new()
        .route("/", get(directory::show))
        .with_state(state.clone());
    let mut router: Router<()> = top.nest_service("/static", ServeDir::new(&static_dir));
    // Discover branches once at startup and mount each under /<name>.
    // New branches added to the directory after startup will 404 until
    // the server restarts — acceptable for a loggerhead deployment.
    for name in subdirs {
        let child_root = format!("{}/{}", state.root.trim_end_matches('/'), name);
        if crate::breezy::open_branch(&child_root).is_err() {
            continue;
        }
        let child_state = Arc::new(AppState::nested(&state, child_root, &name));
        let branch_router = build_branch_router_inner(child_state);
        router = router.nest(&format!("/{name}"), branch_router);
    }
    router.layer(TraceLayer::new_for_http())
}

fn build_user_dirs_router(state: Arc<AppState>, trunk_dir: Option<String>) -> Router {
    use crate::controllers::directory;
    let static_dir = state.static_dir.clone();
    let top = Router::new()
        .route("/", get(directory::show))
        .with_state(state.clone());
    let mut router: Router<()> = top.nest_service("/static", ServeDir::new(&static_dir));

    // ~user/branch branches. Each user directory under <root> holds
    // branches; each branch is mounted at /~<user>/<branch>/.
    let root_trimmed = state.root.trim_end_matches('/');
    for user in list_subdirs(&state.root) {
        // Users whose name starts with `.` are skipped by list_subdirs,
        // but also skip the trunk_dir here to avoid double-mounting.
        if Some(&user) == trunk_dir.as_ref() {
            continue;
        }
        let user_root = format!("{root_trimmed}/{user}");
        for branch_name in list_subdirs(&user_root) {
            let child_root = format!("{user_root}/{branch_name}");
            if crate::breezy::open_branch(&child_root).is_err() {
                continue;
            }
            let prefix = format!("/~{user}/{branch_name}");
            let child_state = Arc::new(AppState {
                root: child_root,
                url_prefix: prefix.clone(),
                serve_mode: ServeMode::Branch,
                whole_history_cache: Cache::new(10),
                disk_cache: state.disk_cache.clone(),
                export_tarballs: state.export_tarballs,
                static_dir: state.static_dir.clone(),
            });
            let branch_router = build_branch_router_inner(child_state);
            router = router.nest(&prefix, branch_router);
        }
    }

    // Optional trunk area: <root>/<trunk_dir>/<branch> at /<branch>/.
    if let Some(trunk) = trunk_dir.as_deref() {
        let trunk_root = format!("{root_trimmed}/{trunk}");
        for branch_name in list_subdirs(&trunk_root) {
            let child_root = format!("{trunk_root}/{branch_name}");
            if crate::breezy::open_branch(&child_root).is_err() {
                continue;
            }
            let child_state = Arc::new(AppState::nested(&state, child_root, &branch_name));
            let branch_router = build_branch_router_inner(child_state);
            router = router.nest(&format!("/{branch_name}"), branch_router);
        }
    }

    router.layer(TraceLayer::new_for_http())
}

fn list_subdirs(root: &str) -> Vec<String> {
    let Ok(read) = std::fs::read_dir(root) else {
        return Vec::new();
    };
    let mut names: Vec<String> = read
        .filter_map(|e| e.ok())
        .filter_map(|e| {
            let n = e.file_name().to_string_lossy().into_owned();
            if n.starts_with('.') {
                None
            } else if e.file_type().ok().is_some_and(|t| t.is_dir()) {
                Some(n)
            } else {
                None
            }
        })
        .collect();
    names.sort_by_key(|s| s.to_lowercase());
    names
}

fn build_branch_router(state: Arc<AppState>) -> Router {
    let static_dir = state.static_dir.clone();
    build_branch_router_inner(state)
        .nest_service("/static", ServeDir::new(&static_dir))
        .layer(TraceLayer::new_for_http())
}

/// Per-branch routes, without the top-level `/static` mount or tracing
/// layer. Used both directly in single-branch mode and from
/// `build_directory_router` at each `/<branch>` nesting point.
fn build_branch_router_inner(state: Arc<AppState>) -> Router {
    use crate::controllers::{
        annotate, atom, changelog, diff, download, filediff, inventory, json, revision, revlog,
        search, view,
    };
    Router::new()
        .route("/", get(root_redirect))
        .route("/changes", get(changelog::show))
        .route("/changes/:revno", get(changelog::show_from))
        .route("/revision/:revid", get(revision::show))
        .route("/revision/:revid/*path", get(revision::show_with_path))
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
        // +json variants: machine-readable versions of the HTML views.
        .route("/+json/changes", get(json::changes))
        .route("/+json/changes/:revno", get(json::changes_from))
        .route("/+json/revision/:revid", get(json::revision))
        .route("/+json/files", get(json::files_root))
        .route("/+json/files/:revno", get(json::files_rev))
        .route("/+json/files/:revno/*path", get(json::files_rev_path))
        .route(
            "/+json/+filediff/:new_revid/:old_revid/*path",
            get(json::filediff),
        )
        .layer(axum::middleware::from_fn_with_state(
            state.clone(),
            last_modified_layer,
        ))
        .with_state(state)
}
