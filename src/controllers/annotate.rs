use std::path::PathBuf;
use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tree::{Kind, Tree};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::History;
use crate::util::errors::{AppError, AppResult};

#[derive(Template)]
#[template(path = "annotate.html")]
struct AnnotateTemplate {
    // base
    nick: String,
    fileview_active: bool,
    // page
    revno: String,
    path: String,
    lines: Vec<Line>,
}

struct Line {
    n: usize,
    revno: String,
    revid_short: String,
    text: String,
}

/// GET /annotate/:revno/*path — blame-style view of a file at the given
/// revision (use `head:` for the tip).
pub async fn show(
    State(state): State<Arc<AppState>>,
    Path((revno_req, path)): Path<(String, String)>,
) -> AppResult<Html<String>> {
    let path_norm = path.trim_matches('/').to_string();
    if path_norm.is_empty() {
        return Err(AppError::Other("no filename provided".into()));
    }
    let path_for_task = path_norm.clone();

    let (nick, annotated, revno) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let revid = history
            .fix_revid(&revno_req)
            .ok_or_else(|| AppError::NotFound(format!("no revision {revno_req}")))?;
        let revno = history.whole.get_revno(&revid);

        let repo = branch.repository();
        let tree = repo.revision_tree(&revid)?;
        let p = PathBuf::from(&path_for_task);
        if !tree.has_filename(&p) {
            return Err(AppError::NotFound(format!("{path_for_task} not found")));
        }
        if !matches!(tree.kind(&p)?, Kind::File) {
            return Err(AppError::Other(format!(
                "{path_for_task} is not a regular file"
            )));
        }

        let mut annotated: Vec<(RevisionId, Vec<u8>)> = Vec::new();
        for item in tree.annotate_iter(&p, None)? {
            annotated.push(item?);
        }

        let lines: Vec<Line> = annotated
            .into_iter()
            .enumerate()
            .map(|(i, (rid, bytes))| {
                let revno = history.whole.get_revno(&rid);
                let full = String::from_utf8_lossy(rid.as_bytes()).into_owned();
                let short = full.split('-').next_back().unwrap_or("").to_string();
                Line {
                    n: i + 1,
                    revno,
                    revid_short: short,
                    text: String::from_utf8_lossy(&bytes)
                        .trim_end_matches('\n')
                        .to_string(),
                }
            })
            .collect();
        Ok::<_, AppError>((history.nick, lines, revno))
    })
    .await??;

    let tmpl = AnnotateTemplate {
        nick,
        fileview_active: true,
        revno,
        path: path_norm,
        lines: annotated,
    };
    Ok(Html(tmpl.render()?))
}
