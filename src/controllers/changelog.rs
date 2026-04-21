use std::path::PathBuf;
use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, Query, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tree::Tree;
use serde::Deserialize;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{Change, History};
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::{approximate_date, hide_email, utc_iso};

/// Query parameters accepted by the `/changes` page.
#[derive(Debug, Deserialize, Default)]
pub struct ChangelogQuery {
    pub start_revid: Option<String>,
    /// Restrict the log to revisions that touched this path.
    pub filter_path: Option<String>,
}

const PAGE_SIZE: usize = 20;

#[derive(Template)]
#[template(path = "changelog.html")]
struct ChangelogTemplate {
    // shared base-template fields
    nick: String,
    fileview_active: bool,
    served_url: String,
    // page-specific
    last_revno: String,
    changes: Vec<ChangeView>,
}

struct ChangeView {
    revno: String,
    short_message: String,
    author: String,
    utc_iso: String,
    relative_date: String,
}

impl From<Change> for ChangeView {
    fn from(c: Change) -> Self {
        ChangeView {
            revno: c.revno,
            short_message: c.short_message,
            author: hide_email(&c.committer),
            utc_iso: utc_iso(c.timestamp, c.timezone),
            relative_date: approximate_date(c.timestamp),
        }
    }
}

/// `GET /changes` — full mainline from the branch tip.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Query(q): Query<ChangelogQuery>,
) -> AppResult<Html<String>> {
    render(state, None, q).await
}

/// `GET /changes/:revno` — log starting from `revno` (Python loggerhead's
/// "view history from revision N" link).
pub async fn show_from(
    State(state): State<Arc<AppState>>,
    Path(revno): Path<String>,
    Query(q): Query<ChangelogQuery>,
) -> AppResult<Html<String>> {
    render(state, Some(revno), q).await
}

async fn render(
    state: Arc<AppState>,
    start_ref: Option<String>,
    q: ChangelogQuery,
) -> AppResult<Html<String>> {
    let filter_path = q.filter_path.clone();
    let state2 = state.clone();
    let (nick, last_revno, changes) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state2.root)?;
        let _lock = branch.lock_read()?;
        let whole = state2.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        // Resolve starting point: explicit URL segment, query param, then tip.
        let start_revid = match start_ref.as_deref().or(q.start_revid.as_deref()) {
            Some(r) => history
                .fix_revid(r)
                .ok_or_else(|| AppError::NotFound(format!("no revision {r}")))?,
            None => history.last_revid.clone(),
        };
        let mainline = history.mainline_from(&start_revid);

        // Optional file filter — keep only revisions that touched the
        // path. A revision R touched `path` iff its tree's recorded
        // "last revision for this file" (`get_file_revision`) points
        // at R itself.
        let filtered: Vec<RevisionId> = if let Some(fp) = filter_path.as_deref() {
            let repo = branch.repository();
            let path = PathBuf::from(fp);
            let mut out = Vec::new();
            for rid in &mainline {
                if rid.is_null() {
                    continue;
                }
                let tree = repo.revision_tree(rid)?;
                if let Ok(file_rev) = tree.get_file_revision(&path) {
                    if file_rev == *rid {
                        out.push(rid.clone());
                    }
                }
            }
            out
        } else {
            mainline
        };

        let page: Vec<_> = filtered.into_iter().take(PAGE_SIZE).collect();
        let changes = history.get_changes(&branch, &page)?;
        let last_revno = history.whole.get_revno(&start_revid);
        Ok::<_, AppError>((history.nick, last_revno, changes))
    })
    .await??;

    let tmpl = ChangelogTemplate {
        nick,
        fileview_active: false,
        served_url: state.root.clone(),
        last_revno,
        changes: changes.into_iter().map(Into::into).collect(),
    };
    Ok(Html(tmpl.render()?))
}
