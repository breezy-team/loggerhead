use std::sync::Arc;

use askama::Template;
use axum::extract::{Path, State};
use axum::response::Html;
use breezyshim::branch::Branch;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tree::Tree;
use percent_encoding::percent_decode_str;
use similar::{ChangeTag, TextDiff};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::util::errors::{AppError, AppResult};

#[derive(Template)]
#[template(path = "filediff.html")]
struct FileDiffTemplate {
    chunks: Vec<Chunk>,
}

struct Chunk {
    #[allow(dead_code)]
    header: String,
    lines: Vec<DiffLine>,
}

struct DiffLine {
    old_lineno: Option<usize>,
    new_lineno: Option<usize>,
    kind: &'static str,
    /// HTML-ready fragment: characters are escaped and tabs/spaces
    /// are rewritten to `&nbsp;` so the `<div>` container preserves
    /// leading indentation the way Python's `util.html_clean` does.
    /// Rendered through Askama's `|safe` filter.
    text: String,
}

/// GET /+filediff/:new_revid/:old_revid/*path — render a unified diff for a
/// single file between two revisions.
pub async fn show(
    State(state): State<Arc<AppState>>,
    Path((new_revid_enc, old_revid_enc, path_enc)): Path<(String, String, String)>,
) -> AppResult<Html<String>> {
    let new_revid = revid_from_enc(&new_revid_enc);
    let old_revid = revid_from_enc(&old_revid_enc);
    let path = percent_decode_str(&path_enc)
        .decode_utf8_lossy()
        .into_owned();

    let (old_lines, new_lines) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let repo = branch.repository();
        let new_tree = repo.revision_tree(&new_revid)?;
        let old_tree = repo.revision_tree(&old_revid)?;
        let p = std::path::Path::new(&path);
        let new_lines = read_file_lines(&new_tree, p);
        let old_lines = read_file_lines(&old_tree, p);
        Ok::<_, AppError>((old_lines, new_lines))
    })
    .await??;

    let chunks = render_chunks(&old_lines, &new_lines);
    let tmpl = FileDiffTemplate { chunks };
    Ok(Html(tmpl.render()?))
}

fn revid_from_enc(s: &str) -> RevisionId {
    let decoded = percent_decode_str(s).decode_utf8_lossy().into_owned();
    RevisionId::from(decoded.into_bytes())
}

/// Read a file from a tree as UTF-8 text split into lines (empty on missing
/// file or binary content).
fn read_file_lines(tree: &dyn Tree, path: &std::path::Path) -> String {
    match tree.get_file_text(path) {
        Ok(bytes) => String::from_utf8_lossy(&bytes).into_owned(),
        Err(_) => String::new(),
    }
}

/// HTML-escape a diff line and rewrite whitespace so a non-`<pre>`
/// container preserves leading indentation. Tabs are expanded to
/// 8 spaces (matching Python's `str.expandtabs`) and every space
/// becomes `&nbsp;`. Matches `loggerhead.util.html_clean`.
fn html_clean(s: &str) -> String {
    // Escape HTML first, then substitute whitespace.
    let mut escaped = String::with_capacity(s.len());
    for c in s.chars() {
        match c {
            '&' => escaped.push_str("&amp;"),
            '<' => escaped.push_str("&lt;"),
            '>' => escaped.push_str("&gt;"),
            '"' => escaped.push_str("&quot;"),
            '\'' => escaped.push_str("&#39;"),
            _ => escaped.push(c),
        }
    }
    // expandtabs: replace each `\t` with enough spaces to reach the
    // next 8-column tab stop. We do a simple uniform expansion to
    // 8 spaces — precise column tracking isn't needed for diff
    // rendering.
    let expanded = escaped.replace('\t', "        ");
    expanded.replace(' ', "&nbsp;")
}

fn render_chunks(old: &str, new: &str) -> Vec<Chunk> {
    let diff = TextDiff::from_lines(old, new);
    let mut chunks = Vec::new();
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
                let raw = change.value();
                let trimmed = raw.trim_end_matches('\n');
                lines.push(DiffLine {
                    old_lineno: change.old_index().map(|i| i + 1),
                    new_lineno: change.new_index().map(|i| i + 1),
                    kind,
                    text: html_clean(trimmed),
                });
            }
        }
        chunks.push(Chunk { header, lines });
    }
    chunks
}
