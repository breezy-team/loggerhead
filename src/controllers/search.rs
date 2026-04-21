use askama::Template;
use axum::extract::Query;
use axum::response::Html;
use serde::Deserialize;

use crate::util::errors::AppResult;

#[derive(Deserialize, Default)]
pub struct SearchQuery {
    #[serde(default)]
    pub q: Option<String>,
}

#[derive(Template)]
#[template(path = "search.html")]
struct SearchTemplate {
    query: String,
    /// Whether search is available at all (the `breezy.plugins.search` plugin
    /// is optional and we do not integrate with it yet).
    available: bool,
    results: Vec<ResultRow>,
}

struct ResultRow {
    revno: String,
    short_message: String,
}

/// GET /search?q=... — search across commit messages / file contents.
///
/// The Python loggerhead wires this up to the bzr-search plugin, which is
/// optional and rarely installed. For now the Rust port reports that search
/// is unavailable; returning an empty result set instead of 500-ing is the
/// same user-visible behaviour as a Python install without the plugin.
pub async fn show(Query(q): Query<SearchQuery>) -> AppResult<Html<String>> {
    let query = q.q.unwrap_or_default();
    let tmpl = SearchTemplate {
        query,
        available: false,
        results: Vec::new(),
    };
    Ok(Html(tmpl.render()?))
}
