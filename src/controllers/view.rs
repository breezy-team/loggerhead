use std::path::PathBuf;
use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, State};
use axum::response::{Html, IntoResponse, Redirect, Response};
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use breezyshim::tree::{Kind, Tree};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::highlight::highlight;
use crate::history::History;
use crate::util::errors::{AppError, AppResult};

#[derive(Template)]
#[template(path = "view.html")]
struct ViewTemplate {
    // shared base
    nick: String,
    fileview_active: bool,
    url_prefix: String,
    // page-specific
    revno: String,
    path: String,
    lines: Vec<Line>,
    #[allow(dead_code)]
    background: Option<String>,
    is_binary: bool,
}

struct Line {
    n: usize,
    html: String,
}

/// One of two outcomes when looking up a /view target.
enum Lookup {
    File {
        nick: String,
        content: Vec<u8>,
        revno: String,
    },
    /// Target is a directory; redirect to `/files/<revno>/<path>`.
    Directory { revno: String },
}

/// `GET /view/:revno/*path` — view file at a specific revision.
/// Use `/view/head:/path` for the branch tip.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Path((revno, path)): Path<(String, String)>,
) -> AppResult<Response> {
    render(state, Some(revno), path).await
}

async fn render(
    state: Arc<AppState>,
    revno_req: Option<String>,
    path: String,
) -> AppResult<Response> {
    let path_norm = path.trim_matches('/').to_string();
    if path_norm.is_empty() {
        return Err(AppError::Other("no filename provided".into()));
    }
    let path_for_task = path_norm.clone();
    let url_prefix = state.url_prefix.clone();
    let state_for_redirect = state.clone();

    let outcome = tokio::task::spawn_blocking(move || -> AppResult<Lookup> {
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
        let p = PathBuf::from(&path_for_task);
        if !tree.has_filename(&p) {
            return Err(AppError::NotFound(format!("{path_for_task} not found")));
        }
        match tree.kind(&p) {
            Ok(Kind::File) => {}
            Ok(Kind::Directory) => return Ok(Lookup::Directory { revno }),
            Ok(_) => {
                return Err(AppError::Other(format!(
                    "{path_for_task} is not a regular file"
                )))
            }
            Err(e) => return Err(AppError::from(e)),
        }
        let bytes = tree.get_file_text(&p)?;
        Ok(Lookup::File {
            nick: history.nick,
            content: bytes,
            revno,
        })
    })
    .await??;

    let (nick, content, revno) = match outcome {
        Lookup::File {
            nick,
            content,
            revno,
        } => (nick, content, revno),
        Lookup::Directory { revno } => {
            let target = state_for_redirect.url(&format!("/files/{revno}/{path_norm}"));
            return Ok(Redirect::permanent(&target).into_response());
        }
    };

    let (lines, background, is_binary) = match std::str::from_utf8(&content) {
        Ok(text) => {
            let hl = highlight(&path_norm, text);
            let ls: Vec<Line> = hl
                .lines
                .into_iter()
                .enumerate()
                .map(|(i, html)| Line { n: i + 1, html })
                .collect();
            (ls, hl.background, false)
        }
        Err(_) => (Vec::new(), None, true),
    };

    let tmpl = ViewTemplate {
        nick,
        fileview_active: true,
        url_prefix,
        revno,
        path: path_norm,
        lines,
        background,
        is_binary,
    };
    Ok(Html(tmpl.render()?).into_response())
}
