use std::sync::Arc;

use askama::Template;
use axum::extract::{Query, State};
use axum::response::Html;
use breezyshim::branch::Branch;
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

pub async fn show(
    State(state): State<Arc<AppState>>,
    Query(_q): Query<ChangelogQuery>,
) -> AppResult<Html<String>> {
    let state2 = state.clone();
    let (nick, last_revno, changes) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state2.root)?;
        let _lock = branch.lock_read()?;
        let whole = state2.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let mainline = history.mainline_from(&history.last_revid);
        let page: Vec<_> = mainline.into_iter().take(PAGE_SIZE).collect();
        let changes = history.get_changes(&branch, &page)?;
        let last_revno = history.whole.get_revno(&history.last_revid);
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
