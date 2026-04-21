use std::sync::Arc;

use axum::body::Body;
use axum::extract::State;
use axum::http::{header, StatusCode};
use axum::response::{IntoResponse, Response};
use breezyshim::branch::Branch;
use chrono::{DateTime, Utc};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::{Change, History};
use crate::util::errors::{AppError, AppResult};

const PAGE_SIZE: usize = 20;

/// GET /atom — an Atom feed of the last PAGE_SIZE mainline revisions.
pub async fn show(State(state): State<Arc<AppState>>) -> AppResult<Response> {
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

    let body = render_atom(&nick, &entries);
    Ok(Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "application/atom+xml; charset=utf-8")
        .body(Body::from(body))
        .unwrap()
        .into_response())
}

fn render_atom(nick: &str, entries: &[Change]) -> String {
    let updated = entries
        .first()
        .and_then(|c| DateTime::<Utc>::from_timestamp(c.timestamp as i64, 0))
        .unwrap_or_else(Utc::now)
        .to_rfc3339();
    let mut out = String::with_capacity(1024 + entries.len() * 512);
    out.push_str(
        r#"<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>"#,
    );
    out.push_str(&format!("bazaar changes for {}", xml_escape(nick)));
    out.push_str("</title>\n  <updated>");
    out.push_str(&updated);
    out.push_str("</updated>\n  <id>urn:loggerhead:");
    out.push_str(&xml_escape(nick));
    out.push_str("</id>\n  <link rel=\"alternate\" type=\"text/html\" href=\"/changes\"/>\n");
    for entry in entries {
        let date = DateTime::<Utc>::from_timestamp(entry.timestamp as i64, 0)
            .map(|d| d.to_rfc3339())
            .unwrap_or_default();
        let revid_hex = String::from_utf8_lossy(entry.revid.as_bytes());
        out.push_str("  <entry>\n    <title>");
        out.push_str(&xml_escape(&format!(
            "{}: {}",
            entry.revno, entry.short_message
        )));
        out.push_str("</title>\n    <updated>");
        out.push_str(&date);
        out.push_str("</updated>\n    <id>urn:revid:");
        out.push_str(&xml_escape(&revid_hex));
        out.push_str("</id>\n    <author><name>");
        out.push_str(&xml_escape(&entry.committer));
        out.push_str("</name></author>\n    <content type=\"text\">");
        out.push_str(&xml_escape(&entry.message));
        out.push_str(
            "</content>\n    <link rel=\"alternate\" type=\"text/html\" href=\"/revision/",
        );
        // Percent-encode revids for the URL safely.
        let enc =
            percent_encoding::utf8_percent_encode(&revid_hex, percent_encoding::NON_ALPHANUMERIC);
        out.push_str(&enc.to_string());
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
