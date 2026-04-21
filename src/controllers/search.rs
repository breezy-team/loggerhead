use std::sync::Arc;

use askama::Template;
use axum::extract::{Query, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use breezyshim::revisionid::RevisionId;
use breezyshim::search::{self, Hit, SearchError};
use serde::Deserialize;

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::History;
use crate::util::errors::{AppError, AppResult};

#[derive(Deserialize, Default)]
pub struct SearchQuery {
    #[serde(default)]
    pub q: Option<String>,
}

#[derive(Template)]
#[template(path = "search.html")]
struct SearchTemplate {
    // base
    nick: String,
    fileview_active: bool,
    url_prefix: String,
    // page
    query: String,
    /// True iff the `breezy.plugins.search` plugin is importable AND the
    /// branch has been indexed.
    available: bool,
    results: Vec<ResultRow>,
}

struct ResultRow {
    revno: String,
    short_message: String,
}

/// GET /search?q=… — search across commit messages / file contents
/// using the `bzr-search` plugin if it's installed and the branch is
/// indexed; otherwise render a "search unavailable" notice.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Query(q): Query<SearchQuery>,
) -> AppResult<Html<String>> {
    let query = q.q.unwrap_or_default();
    let query_for_task = query.clone();
    let state_for_task = state.clone();

    let (nick, available, results) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state_for_task.root)?;
        let _lock = branch.lock_read()?;
        let whole = state_for_task.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;

        if query_for_task.is_empty() {
            // Just render the form.
            return Ok::<_, AppError>((history.nick, search::is_available(), Vec::new()));
        }

        let hits = match search::search(&branch, &query_for_task) {
            Ok(h) => h,
            Err(SearchError::Unavailable) | Err(SearchError::NoIndex) => {
                return Ok((history.nick, false, Vec::new()));
            }
            Err(SearchError::Other(e)) => return Err(AppError::from(e)),
        };

        // De-duplicate to the set of revids; expand to rows with revno/msg.
        let mut seen = std::collections::HashSet::new();
        let revids: Vec<RevisionId> = hits
            .into_iter()
            .map(|h| match h {
                Hit::Revision(r) => r,
                Hit::FileText { revision, .. } => revision,
            })
            .filter(|r| seen.insert(r.clone()))
            .collect();

        let changes = history.get_changes(&branch, &revids)?;
        let results: Vec<ResultRow> = changes
            .into_iter()
            .map(|c| ResultRow {
                revno: c.revno,
                short_message: c.short_message,
            })
            .collect();
        Ok((history.nick, true, results))
    })
    .await??;

    let tmpl = SearchTemplate {
        nick,
        fileview_active: false,
        url_prefix: state.url_prefix.clone(),
        query,
        available,
        results,
    };
    Ok(Html(tmpl.render()?))
}
