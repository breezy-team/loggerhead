//! `/+json/...` variants of the HTML-rendering controllers.
//!
//! Python loggerhead gates this behind `supports_json` on each
//! controller. Our approach is more explicit: each JSON endpoint is a
//! parallel thin handler that calls into the same underlying
//! data-gathering as the HTML counterpart, but serialises a purpose-
//! built serde struct instead of running an Askama template.

use std::path::{Path as StdPath, PathBuf};
use std::sync::Arc;

use axum::extract::{Path, Query, State};
use axum::Json;
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tree::{Kind, Tree};
use percent_encoding::percent_decode_str;
use serde::Serialize;
use similar::{ChangeTag, TextDiff};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::controllers::changelog::ChangelogQuery;
use crate::controllers::revision::RevisionQuery;
use crate::history::{FileChangeKind, History};
use crate::util::errors::{AppError, AppResult};

/// JSON body for `GET /+json/changes` (and its `/:revno` variant).
#[derive(Serialize)]
pub struct ChangesJson {
    pub nick: String,
    pub start_revno: String,
    pub page_size: usize,
    pub next_start_revno: Option<String>,
    pub prev_start_revno: Option<String>,
    pub changes: Vec<ChangeEntry>,
}

#[derive(Serialize)]
pub struct ChangeEntry {
    pub revno: String,
    pub revid: String,
    pub committer: String,
    pub timestamp: f64,
    pub message: String,
    pub tags: Vec<String>,
    pub parents: Vec<ParentEntry>,
    pub is_merge: bool,
}

#[derive(Serialize)]
pub struct ParentEntry {
    pub revno: String,
    pub revid: String,
}

#[derive(Serialize)]
pub struct FileChangeEntry {
    pub kind: &'static str,
    pub path: String,
    pub old_path: Option<String>,
}

/// `GET /+json/changes` — JSON log page.
pub async fn changes(
    State(state): State<Arc<AppState>>,
    Query(q): Query<ChangelogQuery>,
) -> AppResult<Json<ChangesJson>> {
    changes_render(state, None, q).await
}

/// `GET /+json/changes/:revno` — JSON log starting at `revno`.
pub async fn changes_from(
    State(state): State<Arc<AppState>>,
    Path(revno): Path<String>,
    Query(q): Query<ChangelogQuery>,
) -> AppResult<Json<ChangesJson>> {
    changes_render(state, Some(revno), q).await
}

const PAGE_SIZE: usize = 20;

async fn changes_render(
    state: Arc<AppState>,
    start_ref: Option<String>,
    q: ChangelogQuery,
) -> AppResult<Json<ChangesJson>> {
    let filter_path = q.filter_path.clone();
    let out = tokio::task::spawn_blocking(move || -> AppResult<ChangesJson> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let start_revid = match start_ref.as_deref().or(q.start_revid.as_deref()) {
            Some(r) => history
                .fix_revid(r)
                .ok_or_else(|| AppError::NotFound(format!("no revision {r}")))?,
            None => history.last_revid.clone(),
        };
        let mut mainline = history.mainline_from(&history.last_revid);
        if let Some(fp) = filter_path.as_deref() {
            if !fp.is_empty() {
                let repo = branch.repository();
                let p = PathBuf::from(fp);
                mainline.retain(|rid| {
                    if rid.is_null() {
                        return false;
                    }
                    match repo.revision_tree(rid) {
                        Ok(tree) => tree.get_file_revision(&p).ok().as_ref() == Some(rid),
                        Err(_) => false,
                    }
                });
            }
        }
        let start_pos = mainline.iter().position(|r| *r == start_revid).unwrap_or(0);
        let end_exclusive = (start_pos + PAGE_SIZE).min(mainline.len());
        let page: Vec<RevisionId> = mainline[start_pos..end_exclusive].to_vec();
        let next_start_revno = mainline
            .get(end_exclusive)
            .map(|r| history.whole.get_revno(r));
        let prev_start_revno = if start_pos >= PAGE_SIZE {
            mainline
                .get(start_pos - PAGE_SIZE)
                .map(|r| history.whole.get_revno(r))
        } else if start_pos > 0 {
            Some(history.whole.get_revno(&mainline[0]))
        } else {
            None
        };

        let changes = history.get_changes(&branch, &page)?;
        let entries: Vec<ChangeEntry> = changes
            .into_iter()
            .map(|c| {
                let is_merge = c.parents.len() > 1;
                ChangeEntry {
                    revno: c.revno,
                    revid: String::from_utf8_lossy(c.revid.as_bytes()).into_owned(),
                    committer: c.committer,
                    timestamp: c.timestamp,
                    message: c.message,
                    tags: c.tags,
                    parents: c
                        .parents
                        .into_iter()
                        .map(|(rid, revno)| ParentEntry {
                            revno,
                            revid: String::from_utf8_lossy(rid.as_bytes()).into_owned(),
                        })
                        .collect(),
                    is_merge,
                }
            })
            .collect();

        Ok(ChangesJson {
            nick: history.nick,
            start_revno: history.whole.get_revno(&start_revid),
            page_size: PAGE_SIZE,
            next_start_revno,
            prev_start_revno,
            changes: entries,
        })
    })
    .await??;
    Ok(Json(out))
}

/// JSON body for `GET /+json/revision/:revid`.
#[derive(Serialize)]
pub struct RevisionJson {
    pub revid: String,
    pub revno: String,
    pub committer: String,
    pub timestamp: f64,
    pub message: String,
    pub parents: Vec<ParentEntry>,
    pub tags: Vec<String>,
    pub file_changes: Vec<FileChangeEntry>,
    /// If the request included `compare_revid`, this is the revno of
    /// the comparison base; otherwise null.
    pub compare_revno: Option<String>,
}

pub async fn revision(
    State(state): State<Arc<AppState>>,
    Path(idref): Path<String>,
    Query(q): Query<RevisionQuery>,
) -> AppResult<Json<RevisionJson>> {
    let idref = percent_decode_str(&idref).decode_utf8_lossy().into_owned();
    let out = tokio::task::spawn_blocking(move || -> AppResult<RevisionJson> {
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
        let (file_changes, compare_revno) = match q.compare_revid.as_deref() {
            Some(cr) => {
                let base = history
                    .fix_revid(cr)
                    .ok_or_else(|| AppError::NotFound(format!("no revision {cr}")))?;
                let diffs = history.file_changes_between(&branch, &base, &revid)?;
                (diffs, Some(history.whole.get_revno(&base)))
            }
            None => (history.get_file_changes(&branch, &revid)?, None),
        };
        Ok(RevisionJson {
            revid: String::from_utf8_lossy(change.revid.as_bytes()).into_owned(),
            revno: change.revno,
            committer: change.committer,
            timestamp: change.timestamp,
            message: change.message,
            parents: change
                .parents
                .into_iter()
                .map(|(rid, revno)| ParentEntry {
                    revno,
                    revid: String::from_utf8_lossy(rid.as_bytes()).into_owned(),
                })
                .collect(),
            tags: change.tags,
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
                    old_path: f.old_path,
                })
                .collect(),
            compare_revno,
        })
    })
    .await??;
    Ok(Json(out))
}

/// JSON body for `GET /+json/files[/:revno[/*path]]`.
#[derive(Serialize)]
pub struct FilesJson {
    pub revno: String,
    pub revid: String,
    pub path: String,
    pub entries: Vec<FileEntry>,
}

#[derive(Serialize)]
pub struct FileEntry {
    pub name: String,
    pub kind: String,
    pub size: Option<u64>,
    pub last_revno: String,
    pub last_revid: String,
}

pub async fn files_root(State(state): State<Arc<AppState>>) -> AppResult<Json<FilesJson>> {
    files_render(state, None, String::new()).await
}

pub async fn files_rev(
    State(state): State<Arc<AppState>>,
    Path(revno): Path<String>,
) -> AppResult<Json<FilesJson>> {
    files_render(state, Some(revno), String::new()).await
}

pub async fn files_rev_path(
    State(state): State<Arc<AppState>>,
    Path((revno, path)): Path<(String, String)>,
) -> AppResult<Json<FilesJson>> {
    files_render(state, Some(revno), path).await
}

async fn files_render(
    state: Arc<AppState>,
    revno_req: Option<String>,
    path: String,
) -> AppResult<Json<FilesJson>> {
    let out = tokio::task::spawn_blocking(move || -> AppResult<FilesJson> {
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
        let unique_revids: std::collections::HashSet<RevisionId> =
            raw.iter().map(|(_, _, _, r)| r.clone()).collect();
        let unique_vec: Vec<_> = unique_revids.into_iter().collect();
        let change_by_id: std::collections::HashMap<RevisionId, String> = history
            .get_changes(&branch, &unique_vec)?
            .into_iter()
            .map(|c| (c.revid.clone(), c.revno))
            .collect();

        let mut entries: Vec<FileEntry> = raw
            .into_iter()
            .map(|(name, kind, size, child_revid)| FileEntry {
                name,
                kind: match kind {
                    Kind::File => "file".into(),
                    Kind::Directory => "directory".into(),
                    Kind::Symlink => "symlink".into(),
                    Kind::TreeReference => "tree-reference".into(),
                },
                size,
                last_revno: change_by_id
                    .get(&child_revid)
                    .cloned()
                    .unwrap_or_else(|| "?".into()),
                last_revid: String::from_utf8_lossy(child_revid.as_bytes()).into_owned(),
            })
            .collect();
        entries.sort_by(|a, b| {
            (b.kind == "directory")
                .cmp(&(a.kind == "directory"))
                .then(a.name.to_lowercase().cmp(&b.name.to_lowercase()))
        });

        Ok(FilesJson {
            revno,
            revid: String::from_utf8_lossy(revid.as_bytes()).into_owned(),
            path: normalized,
            entries,
        })
    })
    .await??;
    Ok(Json(out))
}

/// JSON body for `GET /+json/+filediff/:new_revid/:old_revid/*path`.
#[derive(Serialize)]
pub struct FileDiffJson {
    pub chunks: Vec<DiffChunk>,
}

#[derive(Serialize)]
pub struct DiffChunk {
    pub header: String,
    pub lines: Vec<DiffLine>,
}

#[derive(Serialize)]
pub struct DiffLine {
    pub old_lineno: Option<usize>,
    pub new_lineno: Option<usize>,
    pub kind: &'static str,
    pub text: String,
}

pub async fn filediff(
    State(state): State<Arc<AppState>>,
    Path((new_revid_enc, old_revid_enc, path_enc)): Path<(String, String, String)>,
) -> AppResult<Json<FileDiffJson>> {
    let new_revid = RevisionId::from(
        percent_decode_str(&new_revid_enc)
            .decode_utf8_lossy()
            .into_owned()
            .into_bytes(),
    );
    let old_revid = RevisionId::from(
        percent_decode_str(&old_revid_enc)
            .decode_utf8_lossy()
            .into_owned()
            .into_bytes(),
    );
    let path = percent_decode_str(&path_enc)
        .decode_utf8_lossy()
        .into_owned();
    let out = tokio::task::spawn_blocking(move || -> AppResult<FileDiffJson> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let repo = branch.repository();
        let new_tree = repo.revision_tree(&new_revid)?;
        let old_tree = repo.revision_tree(&old_revid)?;
        let p = StdPath::new(&path);
        let new_text = new_tree
            .get_file_text(p)
            .map(|b| String::from_utf8_lossy(&b).into_owned())
            .unwrap_or_default();
        let old_text = old_tree
            .get_file_text(p)
            .map(|b| String::from_utf8_lossy(&b).into_owned())
            .unwrap_or_default();

        let diff = TextDiff::from_lines(&old_text, &new_text);
        let mut chunks: Vec<DiffChunk> = Vec::new();
        for group in diff.grouped_ops(3) {
            if group.is_empty() {
                continue;
            }
            let first = &group[0];
            let last = &group[group.len() - 1];
            let old_start = first.as_tag_tuple().1.start + 1;
            let new_start = first.as_tag_tuple().2.start + 1;
            let old_len = last.as_tag_tuple().1.end - first.as_tag_tuple().1.start;
            let new_len = last.as_tag_tuple().2.end - first.as_tag_tuple().2.start;
            let header = format!("@@ -{old_start},{old_len} +{new_start},{new_len} @@");
            let mut lines = Vec::new();
            for op in group {
                for change in diff.iter_changes(&op) {
                    let kind = match change.tag() {
                        ChangeTag::Equal => "context",
                        ChangeTag::Delete => "delete",
                        ChangeTag::Insert => "insert",
                    };
                    let text = change
                        .value()
                        .to_string()
                        .trim_end_matches('\n')
                        .to_string();
                    lines.push(DiffLine {
                        old_lineno: change.old_index().map(|i| i + 1),
                        new_lineno: change.new_index().map(|i| i + 1),
                        kind,
                        text,
                    });
                }
            }
            chunks.push(DiffChunk { header, lines });
        }
        Ok(FileDiffJson { chunks })
    })
    .await??;
    Ok(Json(out))
}
