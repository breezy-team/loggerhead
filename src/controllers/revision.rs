use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use chrono::{FixedOffset, TimeZone};
use percent_encoding::percent_decode_str;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{Change, FileChange, FileChangeKind, History};
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::{hide_email, utc_iso};

#[derive(Template)]
#[template(path = "revision.html")]
struct RevisionTemplate {
    // shared base fields
    nick: String,
    fileview_active: bool,
    // page-specific
    revno: String,
    revid_hex: String,
    author: String,
    #[allow(dead_code)]
    committer: String,
    utc_iso: String,
    #[allow(dead_code)]
    date: String,
    message: String,
    parents: Vec<ParentView>,
    added: Vec<FileChangeView>,
    removed: Vec<FileChangeView>,
    modified: Vec<FileChangeView>,
    renamed: Vec<FileChangeView>,
}

struct ParentView {
    revno: String,
    #[allow(dead_code)]
    revid_hex: String,
}

struct FileChangeView {
    path: String,
    old_path: Option<String>,
}

impl From<FileChange> for FileChangeView {
    fn from(c: FileChange) -> Self {
        FileChangeView {
            path: c.path,
            old_path: c.old_path,
        }
    }
}

/// `GET /revision/:revid` — render the revision page.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Path(idref): Path<String>,
) -> AppResult<Html<String>> {
    render(state, idref).await
}

/// `GET /revision/:revid/*path` — same page; the path is used by the
/// anchor in the URL, which Python loggerhead links to from the file
/// list inside each revision view. Our template already assigns
/// `id="<path>"` to each diff box.
pub async fn show_with_path(
    State(state): State<Arc<AppState>>,
    Path((idref, _path)): Path<(String, String)>,
) -> AppResult<Html<String>> {
    render(state, idref).await
}

async fn render(state: Arc<AppState>, idref: String) -> AppResult<Html<String>> {
    let idref = percent_decode_str(&idref).decode_utf8_lossy().into_owned();

    let state2 = state.clone();
    let (nick, change, file_changes): (String, Change, Vec<FileChange>) =
        tokio::task::spawn_blocking(move || -> AppResult<_> {
            let branch = open_branch(&state2.root)?;
            let _lock = branch.lock_read()?;
            let whole = state2.load_whole_history(&branch)?;
            let history = History::from_whole(&branch, (*whole).clone())?;
            let revid = history
                .fix_revid(&idref)
                .ok_or_else(|| AppError::NotFound(format!("no revision {idref}")))?;
            if !history.whole.index.contains_key(&revid) {
                return Err(AppError::NotFound(format!(
                    "revision {idref} not in branch"
                )));
            }
            let changes = history.get_changes(&branch, std::slice::from_ref(&revid))?;
            let change = changes
                .into_iter()
                .next()
                .ok_or_else(|| AppError::NotFound("revision data missing".into()))?;
            let file_changes = history.get_file_changes(&branch, &revid)?;
            Ok::<_, AppError>((history.nick, change, file_changes))
        })
        .await??;

    let tz = FixedOffset::east_opt(change.timezone).unwrap_or(FixedOffset::east_opt(0).unwrap());
    let date = tz
        .timestamp_opt(change.timestamp as i64, 0)
        .single()
        .map(|d| d.format("%Y-%m-%d %H:%M:%S %z").to_string())
        .unwrap_or_default();

    let mut added = Vec::new();
    let mut removed = Vec::new();
    let mut modified = Vec::new();
    let mut renamed = Vec::new();
    for f in file_changes {
        let view = FileChangeView::from(f.clone());
        match f.kind {
            FileChangeKind::Added => added.push(view),
            FileChangeKind::Removed => removed.push(view),
            FileChangeKind::Modified => modified.push(view),
            FileChangeKind::Renamed | FileChangeKind::Copied => renamed.push(view),
            FileChangeKind::KindChanged => modified.push(view),
        }
    }

    let tmpl = RevisionTemplate {
        nick,
        fileview_active: false,
        revno: change.revno,
        revid_hex: String::from_utf8_lossy(change.revid.as_bytes()).into_owned(),
        author: hide_email(&change.committer),
        utc_iso: utc_iso(change.timestamp, change.timezone),
        committer: change.committer,
        date,
        message: change.message,
        parents: change
            .parents
            .into_iter()
            .map(|(p, revno)| ParentView {
                revno,
                revid_hex: String::from_utf8_lossy(p.as_bytes()).into_owned(),
            })
            .collect(),
        added,
        removed,
        modified,
        renamed,
    };
    Ok(Html(tmpl.render()?))
}
