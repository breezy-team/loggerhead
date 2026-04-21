use std::sync::Arc;

use axum::extract::{Path, State};
use axum::Json;
use breezyshim::branch::Branch;
use breezyshim::revisionid::RevisionId;
use percent_encoding::percent_decode_str;
use serde::Serialize;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::History;
use crate::util::errors::{AppError, AppResult};

#[derive(Serialize)]
pub struct RevLogResponse {
    revid: String,
    revno: String,
    committer: String,
    timestamp: f64,
    message: String,
    short_message: String,
    parents: Vec<ParentEntry>,
    tags: Vec<String>,
    file_changes: Vec<FileChangeEntry>,
}

#[derive(Serialize)]
struct ParentEntry {
    revid: String,
    revno: String,
}

#[derive(Serialize)]
struct FileChangeEntry {
    kind: &'static str,
    path: String,
    old_path: Option<String>,
}

/// GET /+revlog/:revid — machine-readable JSON for a single revision.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Path(revid_enc): Path<String>,
) -> AppResult<Json<RevLogResponse>> {
    let revid = RevisionId::from(
        percent_decode_str(&revid_enc)
            .decode_utf8_lossy()
            .into_owned()
            .into_bytes(),
    );
    let response = tokio::task::spawn_blocking(move || -> AppResult<RevLogResponse> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        if !history.whole.index.contains_key(&revid) {
            return Err(AppError::NotFound(format!(
                "revision {} not in branch",
                String::from_utf8_lossy(revid.as_bytes())
            )));
        }
        let change = history
            .get_changes(&branch, std::slice::from_ref(&revid))?
            .into_iter()
            .next()
            .ok_or_else(|| AppError::NotFound("revision data missing".into()))?;
        let file_changes = history.get_file_changes(&branch, &revid)?;
        Ok(RevLogResponse {
            revid: String::from_utf8_lossy(change.revid.as_bytes()).into_owned(),
            revno: change.revno,
            committer: change.committer,
            timestamp: change.timestamp,
            message: change.message,
            short_message: change.short_message,
            parents: change
                .parents
                .into_iter()
                .map(|(rid, revno)| ParentEntry {
                    revid: String::from_utf8_lossy(rid.as_bytes()).into_owned(),
                    revno,
                })
                .collect(),
            tags: change.tags,
            file_changes: file_changes
                .into_iter()
                .map(|f| FileChangeEntry {
                    kind: match f.kind {
                        crate::history::FileChangeKind::Added => "added",
                        crate::history::FileChangeKind::Removed => "removed",
                        crate::history::FileChangeKind::Modified => "modified",
                        crate::history::FileChangeKind::Renamed => "renamed",
                        crate::history::FileChangeKind::Copied => "copied",
                        crate::history::FileChangeKind::KindChanged => "kind-changed",
                    },
                    path: f.path,
                    old_path: f.old_path,
                })
                .collect(),
        })
    })
    .await??;
    Ok(Json(response))
}
