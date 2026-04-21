use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, Query, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use chrono::{FixedOffset, TimeZone};
use percent_encoding::percent_decode_str;
use serde::Deserialize;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{Change, FileChange, FileChangeKind, History};
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::{hide_email, utc_iso};

/// Query parameters accepted by `/revision/:revid` (and /:revid/*path).
#[derive(Debug, Default, Deserialize)]
pub struct RevisionQuery {
    /// Log-context anchor: "we're viewing this revision inside a log
    /// that starts at start_revid". Preserved through all navigation
    /// links on the page so the user can return to /changes with the
    /// same window.
    pub start_revid: Option<String>,
    /// "Compare with another revision" mode: the user clicked the
    /// compare link on this revno, so we should render every other
    /// revision link with `compare_revid=<remember>` attached.
    pub remember: Option<String>,
    /// Active diff-against base. When set, file_changes and per-file
    /// diff links are computed against this revision rather than the
    /// first-parent of the displayed revision.
    pub compare_revid: Option<String>,
}

#[derive(Template)]
#[template(path = "revision.html")]
struct RevisionTemplate {
    // shared base fields
    nick: String,
    fileview_active: bool,
    url_prefix: String,
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
    /// Bug URLs attached to this revision (from the `bugs` revision
    /// property). Rendered as clickable links above the message.
    bugs: Vec<String>,
    /// Foreign-VCS metadata shown alongside the bzr revid (e.g. the
    /// git SHA-1 for a git-backed branch).
    foreign: Option<ForeignView>,
    parents: Vec<ParentView>,
    added: Vec<FileChangeView>,
    removed: Vec<FileChangeView>,
    modified: Vec<FileChangeView>,
    renamed: Vec<FileChangeView>,
    /// JSON map `{ "diff-N": "<new_revid>/<old_revid>/<path>" }` consumed
    /// by `static/javascript/diff.js` to build `/+filediff/...` URLs.
    link_data: String,
    /// JSON map `{ "<path>": "diff-N" }` for anchor → diff-box lookup.
    path_to_id: String,
    /// Revno we're currently comparing against (if any), for the
    /// "viewing diff vs revision X" banner.
    compare_revno: Option<String>,
    /// Revno stashed for the "remember" mechanism — displayed in the
    /// "Click another revision to compare with N" banner.
    remember_revno: Option<String>,
    /// Query-string suffix to append to revision-navigation links so
    /// start_revid / remember / compare_revid are preserved.
    nav_qs: String,
}

struct ParentView {
    revno: String,
    #[allow(dead_code)]
    revid_hex: String,
}

struct ForeignView {
    abbreviation: String,
    foreign_revid: String,
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
    Query(q): Query<RevisionQuery>,
) -> AppResult<Html<String>> {
    render(state, idref, q).await
}

/// `GET /revision/:revid/*path` — same page; the path is used by the
/// anchor in the URL, which Python loggerhead links to from the file
/// list inside each revision view. Our template already assigns
/// `id="<path>"` to each diff box.
pub async fn show_with_path(
    State(state): State<Arc<AppState>>,
    Path((idref, _path)): Path<(String, String)>,
    Query(q): Query<RevisionQuery>,
) -> AppResult<Html<String>> {
    render(state, idref, q).await
}

async fn render(state: Arc<AppState>, idref: String, q: RevisionQuery) -> AppResult<Html<String>> {
    let idref = percent_decode_str(&idref).decode_utf8_lossy().into_owned();

    let state2 = state.clone();
    let compare_ref = q.compare_revid.clone();
    let (nick, change, file_changes, compare_revno): (
        String,
        Change,
        Vec<FileChange>,
        Option<String>,
    ) = tokio::task::spawn_blocking(move || -> AppResult<_> {
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

        let (file_changes, compare_revno) = match compare_ref.as_deref() {
            Some(cr) => {
                let base = history
                    .fix_revid(cr)
                    .ok_or_else(|| AppError::NotFound(format!("no revision {cr}")))?;
                let diffs = history.file_changes_between(&branch, &base, &revid)?;
                (diffs, Some(history.whole.get_revno(&base)))
            }
            None => (history.get_file_changes(&branch, &revid)?, None),
        };
        Ok::<_, AppError>((history.nick, change, file_changes, compare_revno))
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

    // Build the JSON maps consumed by static/javascript/diff.js.
    // `link_data["diff-N"]` is the `<new>/<old>/<path>` fragment that
    // diff.js uses to build /+filediff URLs; `path_to_id` is the
    // inverse anchor lookup. Each element is percent-encoded the same
    // way Python's util.dq wraps it.
    let new_revid_enc = percent_encoding::utf8_percent_encode(
        &String::from_utf8_lossy(change.revid.as_bytes()),
        percent_encoding::NON_ALPHANUMERIC,
    )
    .to_string();
    // Diff base for per-file diff URLs: the compare_revid if we were
    // asked to compare, otherwise the first parent.
    let old_revid_enc = match q.compare_revid.as_deref() {
        Some(cr) => percent_encoding::utf8_percent_encode(cr, percent_encoding::NON_ALPHANUMERIC)
            .to_string(),
        None => change
            .parents
            .first()
            .map(|(p, _)| {
                percent_encoding::utf8_percent_encode(
                    &String::from_utf8_lossy(p.as_bytes()),
                    percent_encoding::NON_ALPHANUMERIC,
                )
                .to_string()
            })
            .unwrap_or_default(),
    };
    let mut link_obj = serde_json::Map::new();
    let mut path_obj = serde_json::Map::new();
    for (i, f) in modified.iter().enumerate() {
        let id = format!("diff-{i}");
        link_obj.insert(
            id.clone(),
            serde_json::Value::String(format!("{}/{}/{}", new_revid_enc, old_revid_enc, f.path)),
        );
        path_obj.insert(f.path.clone(), serde_json::Value::String(id));
    }
    let link_data = serde_json::Value::Object(link_obj).to_string();
    let path_to_id = serde_json::Value::Object(path_obj).to_string();

    // Build the query string to preserve on navigation links. We
    // preserve start_revid always; remember/compare only when they
    // apply to where we're heading (the template conditionalises
    // which of the two to emit at each link site).
    let mut nav_params: Vec<(&str, String)> = Vec::new();
    if let Some(s) = q.start_revid.as_deref().filter(|s| !s.is_empty()) {
        nav_params.push(("start_revid", s.to_string()));
    }
    let nav_qs = if nav_params.is_empty() {
        String::new()
    } else {
        let parts: Vec<String> = nav_params
            .iter()
            .map(|(k, v)| {
                format!(
                    "{k}={}",
                    percent_encoding::utf8_percent_encode(v, percent_encoding::NON_ALPHANUMERIC)
                )
            })
            .collect();
        format!("?{}", parts.join("&"))
    };

    // Resolve remember/compare to their display revnos if set.
    let remember_revno = q.remember.as_deref().map(|r| r.to_string());

    let tmpl = RevisionTemplate {
        nick,
        fileview_active: false,
        url_prefix: state.url_prefix.clone(),
        revno: change.revno,
        revid_hex: String::from_utf8_lossy(change.revid.as_bytes()).into_owned(),
        author: hide_email(&change.committer),
        utc_iso: utc_iso(change.timestamp, change.timezone),
        committer: change.committer,
        date,
        message: change.message,
        bugs: change.bugs,
        foreign: change.foreign.map(|f| ForeignView {
            abbreviation: f.abbreviation,
            foreign_revid: f.foreign_revid,
        }),
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
        link_data,
        path_to_id,
        compare_revno,
        remember_revno,
        nav_qs,
    };
    Ok(Html(tmpl.render()?))
}
