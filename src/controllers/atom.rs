use std::sync::Arc;

use axum::body::Body;
use axum::extract::{Host, State};
use axum::http::{header, HeaderMap, StatusCode};
use axum::response::{IntoResponse, Response};
use breezyshim::branch::Branch;
use chrono::{DateTime, Utc};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{Change, History};
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::hide_email;

const PAGE_SIZE: usize = 20;

/// GET /atom — Atom feed of the last PAGE_SIZE mainline revisions.
///
/// Byte-structurally matches Python loggerhead's `atom.pt` output:
/// id, rel=self, rel=alternate, and per-entry ids all resolve to
/// absolute `http(s)://host/<path>` URLs. The Host header gives
/// us the scheme+host.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Host(host): Host,
    headers: HeaderMap,
) -> AppResult<Response> {
    // axum 0.7 `Host` extractor doesn't give us the scheme; we infer
    // "https" if the X-Forwarded-Proto header says so, else "http".
    let scheme = headers
        .get("x-forwarded-proto")
        .and_then(|v| v.to_str().ok())
        .map(|s| s.to_string())
        .unwrap_or_else(|| "http".into());
    let prefix = state.url_prefix.clone();
    let base = format!("{scheme}://{host}{prefix}");

    let (nick, entries) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let mainline = history.mainline_from(&history.last_revid);
        let page: Vec<_> = mainline.into_iter().take(PAGE_SIZE).collect();
        let changes = history.get_changes(&branch, &page)?;
        Ok::<_, AppError>((history.nick, changes))
    })
    .await??;

    let body = render_atom(&base, &nick, &entries);
    Ok(Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "application/atom+xml; charset=utf-8")
        .body(Body::from(body))
        .unwrap()
        .into_response())
}

fn render_atom(base: &str, nick: &str, entries: &[Change]) -> String {
    let updated = entries
        .first()
        .and_then(|c| DateTime::<Utc>::from_timestamp(c.timestamp as i64, 0))
        .unwrap_or_else(Utc::now)
        .to_rfc3339();
    let atom_self = format!("{base}/atom");
    let changes_url = format!("{base}/changes");
    let mut out = String::with_capacity(1024 + entries.len() * 512);
    out.push_str(
        r#"<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>"#,
    );
    out.push_str(&format!("bazaar changes for {}", xml_escape(nick)));
    out.push_str("</title>\n  <updated>");
    out.push_str(&updated);
    out.push_str("</updated>\n  <id>");
    out.push_str(&xml_escape(&atom_self));
    out.push_str("</id>\n  <link rel=\"self\" type=\"application/atom+xml\" href=\"");
    out.push_str(&xml_escape(&atom_self));
    out.push_str("\"/>\n  <link rel=\"alternate\" type=\"text/html\" href=\"");
    out.push_str(&xml_escape(&changes_url));
    out.push_str("\"/>\n");
    for entry in entries {
        let date = DateTime::<Utc>::from_timestamp(entry.timestamp as i64, 0)
            .map(|d| d.to_rfc3339())
            .unwrap_or_default();
        let rev_url = format!("{base}/revision/{}", entry.revno);
        let author_name = hide_email(&entry.committer);
        out.push_str("  <entry>\n    <title>");
        out.push_str(&xml_escape(&format!(
            "{}: {}",
            entry.revno, entry.short_message
        )));
        out.push_str("</title>\n    <updated>");
        out.push_str(&date);
        out.push_str("</updated>\n    <id>");
        out.push_str(&xml_escape(&rev_url));
        out.push_str("</id>\n    <author><name>");
        out.push_str(&xml_escape(&author_name));
        out.push_str("</name></author>\n    <content type=\"text\">");
        out.push_str(&xml_escape(&entry.message));
        out.push_str("</content>\n    <link rel=\"alternate\" type=\"text/html\" href=\"");
        out.push_str(&xml_escape(&rev_url));
        out.push_str("\"/>\n  </entry>\n");
    }
    out.push_str("</feed>\n");
    out
}

fn xml_escape(s: &str) -> String {
    let mut out = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => out.push_str("&amp;"),
            '<' => out.push_str("&lt;"),
            '>' => out.push_str("&gt;"),
            '"' => out.push_str("&quot;"),
            '\'' => out.push_str("&apos;"),
            _ => out.push(c),
        }
    }
    out
}
