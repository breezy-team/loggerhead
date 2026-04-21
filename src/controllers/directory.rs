use std::sync::Arc;

use askama::Template;
use axum::extract::State;
use axum::response::Html;
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use chrono::{DateTime, Utc};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::hide_email;

#[derive(Template)]
#[template(path = "directory.html")]
struct DirectoryTemplate {
    // base-template fields — `nick` is the root name here
    nick: String,
    #[allow(dead_code)]
    fileview_active: bool,
    url_prefix: String,
    entries: Vec<Entry>,
}

struct Entry {
    name: String,
    /// Href relative to the root — either a sub-branch view or a
    /// drill-down into a deeper listing.
    href: String,
    /// True if this entry is itself a branch (so the row gets the
    /// revision info).
    is_branch: bool,
    /// Last revision committer + ISO date, shown only for branches.
    last_committer: String,
    last_date: String,
}

/// `GET /` when the configured root is a directory rather than a branch.
///
/// Currently this only renders the listing; drill-down into sub-branches
/// (the old Python `BranchesFromTransportServer`) is not yet implemented
/// because axum's Router is built at startup and re-dispatching per
/// request requires either dynamic routing or per-controller support
/// for a branch sub-path. For single-branch installs, point
/// `loggerhead-serve` directly at the branch directory.
pub async fn show(State(state): State<Arc<AppState>>) -> AppResult<Html<String>> {
    let root_path = std::path::PathBuf::from(&state.root);
    let root_name = root_path
        .file_name()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_else(|| state.root.clone());

    let state2 = state.clone();
    let entries = tokio::task::spawn_blocking(move || -> AppResult<Vec<Entry>> {
        let mut out: Vec<Entry> = Vec::new();
        let read = std::fs::read_dir(&state2.root)
            .map_err(|e| AppError::Other(format!("read_dir {}: {e}", state2.root)))?;
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

        for name in names {
            let child_path = format!("{}/{}", state2.root.trim_end_matches('/'), name);
            let (is_branch, last_committer, last_date) = match open_branch(&child_path) {
                Ok(branch) => {
                    let (committer, date) = branch
                        .lock_read()
                        .ok()
                        .map(|_| {
                            let rid = branch.last_revision();
                            if rid.is_null() {
                                return (String::new(), String::new());
                            }
                            let repo = branch.repository();
                            match repo.get_revision(&rid) {
                                Ok(rev) => {
                                    let committer = hide_email(&rev.committer);
                                    let date =
                                        DateTime::<Utc>::from_timestamp(rev.timestamp as i64, 0)
                                            .map(|d| d.format("%Y-%m-%d %H:%M UTC").to_string())
                                            .unwrap_or_default();
                                    (committer, date)
                                }
                                Err(_) => (String::new(), String::new()),
                            }
                        })
                        .unwrap_or_default();
                    (true, committer, date)
                }
                Err(_) => (false, String::new(), String::new()),
            };
            out.push(Entry {
                href: format!("/{name}/"),
                name,
                is_branch,
                last_committer,
                last_date,
            });
        }
        Ok(out)
    })
    .await??;

    let tmpl = DirectoryTemplate {
        nick: root_name,
        fileview_active: false,
        url_prefix: state.url_prefix.clone(),
        entries,
    };
    Ok(Html(tmpl.render()?))
}
