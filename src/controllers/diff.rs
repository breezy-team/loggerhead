use std::sync::Arc;

use axum::body::Body;
use axum::extract::{Path, Query, State};
use axum::http::{header, StatusCode};
use axum::response::{IntoResponse, Response};
use breezyshim::branch::Branch;
use breezyshim::diff::show_diff_trees_with;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use serde::Deserialize;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::History;
use crate::util::errors::{AppError, AppResult};

#[derive(Debug, Deserialize, Default)]
pub struct DiffQuery {
    /// Override the default 3 lines of unified-diff context. Matches
    /// Python loggerhead's `?context=N`.
    pub context: Option<usize>,
}

/// GET /diff/:new_revid — diff from new's first parent to new.
pub async fn show_one(
    State(state): State<Arc<AppState>>,
    Path(new_revid_enc): Path<String>,
    Query(q): Query<DiffQuery>,
) -> AppResult<Response> {
    render_diff(state, new_revid_enc, None, q.context).await
}

/// GET /diff/:new_revid/:old_revid — diff from old to new.
pub async fn show_two(
    State(state): State<Arc<AppState>>,
    Path((new_revid_enc, old_revid_enc)): Path<(String, String)>,
    Query(q): Query<DiffQuery>,
) -> AppResult<Response> {
    render_diff(state, new_revid_enc, Some(old_revid_enc), q.context).await
}

async fn render_diff(
    state: Arc<AppState>,
    new_revid_enc: String,
    old_revid_enc: Option<String>,
    context: Option<usize>,
) -> AppResult<Response> {
    let (diff_bytes, revno_new, revno_old) =
        tokio::task::spawn_blocking(move || -> AppResult<_> {
            let branch = open_branch(&state.root)?;
            let _lock = branch.lock_read()?;
            let whole = state.load_whole_history(&branch)?;
            let history = History::from_whole(&branch, (*whole).clone())?;

            let new_revid = history
                .fix_revid(&new_revid_enc)
                .ok_or_else(|| AppError::NotFound(format!("no revision {new_revid_enc}")))?;
            let old_revid = match old_revid_enc {
                Some(enc) => history
                    .fix_revid(&enc)
                    .ok_or_else(|| AppError::NotFound(format!("no revision {enc}")))?,
                None => {
                    // Default to new's first parent, or NULL_REVISION for root commits.
                    let entry_idx = history
                        .whole
                        .index
                        .get(&new_revid)
                        .copied()
                        .ok_or_else(|| AppError::NotFound("new revision not in branch".into()))?;
                    history.whole.entries[entry_idx]
                        .parents
                        .first()
                        .cloned()
                        .unwrap_or_else(RevisionId::null)
                }
            };

            let repo = branch.repository();
            let new_tree = repo.revision_tree(&new_revid)?;
            let old_tree = repo.revision_tree(&old_revid)?;

            let mut buf: Vec<u8> = Vec::new();
            show_diff_trees_with(&old_tree, &new_tree, &mut buf, Some(""), Some(""), context)?;

            let revno_new = history.whole.get_revno(&new_revid);
            let revno_old = history.whole.get_revno(&old_revid);
            Ok::<_, AppError>((buf, revno_new, revno_old))
        })
        .await??;

    let filename = format!("{revno_new}_{revno_old}.diff");
    Ok(Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "application/octet-stream")
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename={filename}"),
        )
        .body(Body::from(diff_bytes))
        .unwrap()
        .into_response())
}
