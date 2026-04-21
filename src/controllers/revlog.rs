use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use percent_encoding::percent_decode_str;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{FileChangeKind, History};
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::hide_email;

#[derive(Template)]
#[template(path = "revlog.html")]
struct RevLogTemplate {
    url_prefix: String,
    author: String,
    parents: Vec<ParentView>,
    bugs: Vec<String>,
    file_changes: Vec<FileChangeEntry>,
}

struct ParentView {
    revno: String,
}

struct FileChangeEntry {
    kind: &'static str,
    path: String,
}

/// GET /+revlog/:revid — HTML fragment for the "expand a row"
/// interaction on the changelog page. The rendered fragment is
/// consumed by `static/javascript/custom.js::Collapsible._load_finished`,
/// which discards the first line (using `data.split('\n').splice(0, 1)`)
/// and inserts the rest as HTML — so the template starts with a
/// leading blank line deliberately. Matches the shape of Python
/// loggerhead's `revlog.pt`.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Path(revid_enc): Path<String>,
) -> AppResult<Html<String>> {
    let idref = percent_decode_str(&revid_enc)
        .decode_utf8_lossy()
        .into_owned();
    let url_prefix = state.url_prefix.clone();
    let tmpl = tokio::task::spawn_blocking(move || -> AppResult<RevLogTemplate> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let revid = history
            .fix_revid(&idref)
            .ok_or_else(|| AppError::NotFound(format!("no revision {idref}")))?;
        if !history.whole.index.contains_key(&revid) {
            return Err(AppError::NotFound(format!(
                "revision {idref} not in branch"
            )));
        }
        let change = history
            .get_changes(&branch, std::slice::from_ref(&revid))?
            .into_iter()
            .next()
            .ok_or_else(|| AppError::NotFound("revision data missing".into()))?;
        let file_changes = history.get_file_changes(&branch, &revid)?;
        Ok(RevLogTemplate {
            url_prefix: url_prefix.clone(),
            author: hide_email(&change.committer),
            parents: change
                .parents
                .into_iter()
                .map(|(_, revno)| ParentView { revno })
                .collect(),
            bugs: change.bugs,
            file_changes: file_changes
                .into_iter()
                .map(|f| FileChangeEntry {
                    kind: match f.kind {
                        FileChangeKind::Added => "added",
                        FileChangeKind::Removed => "removed",
                        FileChangeKind::Modified => "modified",
                        FileChangeKind::Renamed => "renamed",
                        FileChangeKind::Copied => "copied",
                        FileChangeKind::KindChanged => "kind-changed",
                    },
                    path: f.path,
                })
                .collect(),
        })
    })
    .await??;

    Ok(Html(tmpl.render()?))
}
