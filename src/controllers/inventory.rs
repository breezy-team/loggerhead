use std::path::{Path as StdPath, PathBuf};
use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, Query, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tree::{Kind, Tree};
use serde::Deserialize;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{Change, History};
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::{approximate_date, hide_email, utc_iso};

#[derive(Debug, Deserialize, Default)]
pub struct FilesQuery {
    /// `filename` (default), `date`, or `size`. Matches Python loggerhead.
    pub sort: Option<String>,
}

#[derive(Copy, Clone, PartialEq, Eq)]
enum Sort {
    Filename,
    Date,
    Size,
}

impl Sort {
    fn from_str(s: Option<&str>) -> Self {
        match s {
            Some("date") => Sort::Date,
            Some("size") => Sort::Size,
            _ => Sort::Filename,
        }
    }
    fn as_str(&self) -> &'static str {
        match self {
            Sort::Filename => "filename",
            Sort::Date => "date",
            Sort::Size => "size",
        }
    }
}

#[derive(Template)]
#[template(path = "inventory.html")]
struct InventoryTemplate {
    // base
    nick: String,
    fileview_active: bool,
    url_prefix: String,
    // page
    revno: String,
    revid_hex: String,
    path: String,
    path_display: String,
    parent_path: Option<String>,
    tip_change: Option<ChangeView>,
    entries: Vec<Entry>,
    /// Current sort mode, as the query param string ("filename",
    /// "date", "size"). The template uses this to style the active
    /// column header.
    sort: String,
}

#[allow(dead_code)]
struct ChangeView {
    revno: String,
    committer: String,
    utc_iso: String,
    short_message: String,
    message: String,
}

impl From<Change> for ChangeView {
    fn from(c: Change) -> Self {
        ChangeView {
            revno: c.revno,
            committer: hide_email(&c.committer),
            utc_iso: utc_iso(c.timestamp, c.timezone),
            short_message: c.short_message,
            message: c.message,
        }
    }
}

struct Entry {
    name: String,
    href: String,
    #[allow(dead_code)]
    kind: &'static str,
    is_dir: bool,
    size: Option<u64>,
    last_revno: String,
    last_revid_hex: String,
    last_committer: String,
    last_relative: String,
    last_message: String,
    /// Unix timestamp of the last-changed revision, used for the
    /// ?sort=date mode. Zero when we couldn't resolve the change.
    last_timestamp: f64,
}

pub async fn show_root(
    State(state): State<Arc<AppState>>,
    Query(q): Query<FilesQuery>,
) -> AppResult<Html<String>> {
    render(state, None, String::new(), q).await
}

pub async fn show_rev(
    State(state): State<Arc<AppState>>,
    Path(revno): Path<String>,
    Query(q): Query<FilesQuery>,
) -> AppResult<Html<String>> {
    render(state, Some(revno), String::new(), q).await
}

pub async fn show_rev_path(
    State(state): State<Arc<AppState>>,
    Path((revno, path)): Path<(String, String)>,
    Query(q): Query<FilesQuery>,
) -> AppResult<Html<String>> {
    render(state, Some(revno), path, q).await
}

async fn render(
    state: Arc<AppState>,
    revno_req: Option<String>,
    path: String,
    q: FilesQuery,
) -> AppResult<Html<String>> {
    let state_for_tmpl = state.clone();
    let sort_for_tmpl = Sort::from_str(q.sort.as_deref()).as_str().to_string();
    let (nick, revno, revid_hex, tip_change, entries, path_display, parent_path, normalized) =
        tokio::task::spawn_blocking(move || -> AppResult<_> {
            let branch = open_branch(&state.root)?;
            let _lock = branch.lock_read()?;
            let whole = state.load_whole_history(&branch)?;
            let history = History::from_whole(&branch, (*whole).clone())?;
            let revid = match revno_req.as_deref() {
                Some(r) => history
                    .fix_revid(r)
                    .ok_or_else(|| AppError::NotFound(format!("no revision {r}")))?,
                None => history.last_revid.clone(),
            };
            let revno = history.whole.get_revno(&revid);
            let repo = branch.repository();
            let tree = repo.revision_tree(&revid)?;

            let normalized = path.trim_matches('/').to_string();
            let list_path = if normalized.is_empty() {
                PathBuf::from("")
            } else {
                PathBuf::from(&normalized)
            };
            if !normalized.is_empty() {
                if !tree.has_filename(&list_path) {
                    return Err(AppError::NotFound(format!("{normalized} not found")));
                }
                if !matches!(tree.kind(&list_path)?, Kind::Directory) {
                    return Err(AppError::Other(format!("{normalized} is not a directory")));
                }
            }

            // Fetch revision information for tip, to show in the info box.
            let tip_change_rec = history
                .get_changes(&branch, std::slice::from_ref(&revid))?
                .pop();

            // Walk children, gathering per-entry last-changed revids.
            let from_dir = if normalized.is_empty() {
                None
            } else {
                Some(list_path.as_path())
            };
            let iter = tree.list_files(Some(false), from_dir, Some(false), Some(false))?;
            let mut raw: Vec<(String, Kind, Option<u64>, RevisionId)> = Vec::new();
            for item in iter {
                let (rel, _v, kind, entry) = item?;
                let size = match &entry {
                    breezyshim::tree::TreeEntry::File { size, .. } => Some(*size),
                    _ => None,
                };
                let name = rel
                    .file_name()
                    .map(|n| n.to_string_lossy().into_owned())
                    .unwrap_or_else(|| rel.to_string_lossy().into_owned());
                let full = if normalized.is_empty() {
                    name.clone()
                } else {
                    format!("{normalized}/{name}")
                };
                let child_revid = tree
                    .get_file_revision(StdPath::new(&full))
                    .unwrap_or_else(|_| revid.clone());
                raw.push((name, kind, size, child_revid));
            }

            // Batch-fetch the changes for all the unique revids involved.
            let unique: std::collections::HashSet<RevisionId> =
                raw.iter().map(|(_, _, _, r)| r.clone()).collect();
            let unique_vec: Vec<_> = unique.into_iter().collect();
            let changes = history.get_changes(&branch, &unique_vec)?;
            let mut change_by_id: std::collections::HashMap<RevisionId, Change> =
                std::collections::HashMap::new();
            for c in changes {
                change_by_id.insert(c.revid.clone(), c);
            }

            let mut entries: Vec<Entry> = raw
                .into_iter()
                .map(|(name, kind, size, child_revid)| {
                    let is_dir = matches!(kind, Kind::Directory);
                    let kind_str = match kind {
                        Kind::File => "file",
                        Kind::Directory => "directory",
                        Kind::Symlink => "symlink",
                        Kind::TreeReference => "tree-reference",
                    };
                    let full = if normalized.is_empty() {
                        name.clone()
                    } else {
                        format!("{normalized}/{name}")
                    };
                    let href = if is_dir {
                        format!("{}/files/{}/{}", state.url_prefix, revno, full)
                    } else {
                        format!("{}/view/{}/{}", state.url_prefix, revno, full)
                    };
                    let ch = change_by_id.get(&child_revid);
                    Entry {
                        name,
                        href,
                        kind: kind_str,
                        is_dir,
                        size,
                        last_revno: ch
                            .map(|c| c.revno.clone())
                            .unwrap_or_else(|| "?".to_string()),
                        last_revid_hex: String::from_utf8_lossy(child_revid.as_bytes())
                            .into_owned(),
                        last_committer: ch.map(|c| hide_email(&c.committer)).unwrap_or_default(),
                        last_relative: ch
                            .map(|c| approximate_date(c.timestamp))
                            .unwrap_or_default(),
                        last_message: ch.map(|c| c.short_message.clone()).unwrap_or_default(),
                        last_timestamp: ch.map(|c| c.timestamp).unwrap_or(0.0),
                    }
                })
                .collect();
            // Apply the requested sort. For date: newest first. For
            // size: largest first, ignoring directories (size None).
            // For filename (default): alphabetical, dirs first.
            let sort = Sort::from_str(q.sort.as_deref());
            match sort {
                Sort::Date => entries.sort_by(|a, b| {
                    b.last_timestamp
                        .partial_cmp(&a.last_timestamp)
                        .unwrap_or(std::cmp::Ordering::Equal)
                        .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
                }),
                Sort::Size => entries.sort_by(|a, b| {
                    // Put directories at the bottom of size sort; among
                    // files, largest first.
                    b.is_dir
                        .cmp(&a.is_dir)
                        .reverse()
                        .then(b.size.unwrap_or(0).cmp(&a.size.unwrap_or(0)))
                        .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
                }),
                Sort::Filename => entries.sort_by(|a, b| {
                    b.is_dir
                        .cmp(&a.is_dir)
                        .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
                }),
            }

            let path_display = if normalized.is_empty() {
                "/".to_string()
            } else {
                format!("/{normalized}")
            };
            let parent_path = if normalized.is_empty() {
                None
            } else {
                Some(
                    StdPath::new(&normalized)
                        .parent()
                        .map(|p| p.to_string_lossy().into_owned())
                        .unwrap_or_default(),
                )
            };
            let revid_hex = String::from_utf8_lossy(revid.as_bytes()).into_owned();
            Ok::<_, AppError>((
                history.nick,
                revno,
                revid_hex,
                tip_change_rec.map(ChangeView::from),
                entries,
                path_display,
                parent_path,
                normalized,
            ))
        })
        .await??;

    let tmpl = InventoryTemplate {
        nick,
        fileview_active: true,
        url_prefix: state_for_tmpl.url_prefix.clone(),
        revno,
        revid_hex,
        path: normalized,
        path_display,
        parent_path,
        tip_change,
        entries,
        sort: sort_for_tmpl,
    };
    Ok(Html(tmpl.render()?))
}
