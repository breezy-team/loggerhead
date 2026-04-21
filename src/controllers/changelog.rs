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
    url_prefix: String,
    served_url: String,
    // page-specific
    last_revno: String,
    /// Revno at the end of the current page (for the "From Revision X to Y"
    /// header). Empty if the page is empty.
    end_revno: String,
    /// Does any row on this page have tags? If so, the template renders
    /// the extra "Tags" column.
    show_tag_col: bool,
    changes: Vec<ChangeView>,
    /// URL for the Newer (previous page) link, if there is one.
    prev_page_url: Option<String>,
    /// URL for the Older (next page) link, if there is one.
    next_page_url: Option<String>,
    /// The filter_path query echoed back so the header can say "Changes
    /// to <path>". Empty when there's no filter.
    filter_path: String,
    /// JSON map `{ "0": "<urlencoded-revid>", "1": ..., ... }` consumed
    /// by `static/javascript/changelog.js` to build `/+revlog/<revid>`
    /// URLs for the expand-a-row feature. The key is the row index
    /// (`log-N` element id suffix).
    revids_json: String,
}

struct ChangeView {
    revno: String,
    short_message: String,
    author: String,
    utc_iso: String,
    relative_date: String,
    /// Comma-separated list of tag names attached to this revision.
    tags: String,
    /// True iff the commit is a merge (has more than one parent). The
    /// template shows a small merge-from icon next to the summary.
    is_merge: bool,
    /// Merge depth (0 = mainline). The template renders an extra
    /// `padding-left` proportional to this so the log visualises the
    /// merge structure.
    merge_depth: usize,
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

/// Build the base query-string for pagination links: echoes `filter_path`
/// and the effective `start_revid` (as a revno, matching Python's format).
fn pagination_query(filter_path: &Option<String>, start_revno: Option<&str>) -> String {
    let mut parts: Vec<(&str, String)> = Vec::new();
    if let Some(fp) = filter_path.as_deref() {
        if !fp.is_empty() {
            parts.push(("filter_path", fp.to_string()));
        }
    }
    if let Some(sr) = start_revno {
        if !sr.is_empty() {
            parts.push(("start_revid", sr.to_string()));
        }
    }
    if parts.is_empty() {
        String::new()
    } else {
        let joined: Vec<String> = parts
            .into_iter()
            .map(|(k, v)| {
                format!(
                    "{k}={}",
                    percent_encoding::utf8_percent_encode(&v, percent_encoding::NON_ALPHANUMERIC)
                )
            })
            .collect();
        format!("?{}", joined.join("&"))
    }
}

struct PageData {
    nick: String,
    start_revno: String,
    end_revno: String,
    show_tag_col: bool,
    changes: Vec<ChangeView>,
    /// JSON blob: `{ "0": "<urlencoded-revid>", ... }` for changelog.js.
    revids_json: String,
    /// Revno of the revision one page older (larger offset) than the
    /// current view's start, if it exists.
    next_start_revno: Option<String>,
    /// Revno of the revision one page newer (smaller offset) than the
    /// current view's start, if it exists.
    prev_start_revno: Option<String>,
}

async fn render(
    state: Arc<AppState>,
    start_ref: Option<String>,
    q: ChangelogQuery,
) -> AppResult<Html<String>> {
    let filter_path_for_query = q.filter_path.clone();
    let filter_path = q.filter_path.clone();
    let state2 = state.clone();
    let data = tokio::task::spawn_blocking(move || -> AppResult<PageData> {
        let branch = open_branch(&state2.root)?;
        let _lock = branch.lock_read()?;
        let whole = state2.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;

        // Resolve starting point: explicit URL segment, query param, tip.
        let start_revid = match start_ref.as_deref().or(q.start_revid.as_deref()) {
            Some(r) => history
                .fix_revid(r)
                .ok_or_else(|| AppError::NotFound(format!("no revision {r}")))?,
            None => history.last_revid.clone(),
        };

        // Full merge-sorted list reachable from the branch tip. Unlike
        // the mainline-only view this includes merged revisions with
        // merge_depth > 0 so the template can render a graph indent.
        let full_entries = history.merge_sorted_from(&history.last_revid);
        let full_filtered: Vec<RevisionId> = if let Some(fp) = filter_path.as_deref() {
            if fp.is_empty() {
                full_entries.into_iter().map(|e| e.revid).collect()
            } else {
                let ids: Vec<_> = full_entries.into_iter().map(|e| e.revid).collect();
                filter_by_path(&branch, &ids, fp)?
            }
        } else {
            full_entries.into_iter().map(|e| e.revid).collect()
        };

        // Find the index of `start_revid` within the filtered mainline.
        let start_pos = full_filtered
            .iter()
            .position(|r| *r == start_revid)
            .unwrap_or(0);
        let end_exclusive = (start_pos + PAGE_SIZE).min(full_filtered.len());
        let page: Vec<RevisionId> = full_filtered[start_pos..end_exclusive].to_vec();

        let changes = history.get_changes(&branch, &page)?;

        // Is there a Next (Older) page?
        let next_start_revno = full_filtered
            .get(end_exclusive)
            .map(|r| history.whole.get_revno(r));
        // Is there a Previous (Newer) page?
        let prev_start_revno = if start_pos >= PAGE_SIZE {
            full_filtered
                .get(start_pos - PAGE_SIZE)
                .map(|r| history.whole.get_revno(r))
        } else if start_pos > 0 {
            // Prev page isn't a full PAGE_SIZE away — snap to the tip.
            Some(history.whole.get_revno(&full_filtered[0]))
        } else {
            None
        };

        let start_revno = history.whole.get_revno(&start_revid);
        let end_revno = changes.last().map(|c| c.revno.clone()).unwrap_or_default();

        let show_tag_col = changes.iter().any(|c| !c.tags.is_empty());
        // Build `revids_json` in parallel with the ChangeView list so
        // changelog.js can expand rows via /+revlog/<revid>. Key is
        // the row index as a string, value is the percent-encoded revid.
        let mut revid_map = serde_json::Map::new();
        let views: Vec<ChangeView> = changes
            .into_iter()
            .enumerate()
            .map(|(i, c)| {
                let revid_enc = percent_encoding::utf8_percent_encode(
                    &String::from_utf8_lossy(c.revid.as_bytes()),
                    percent_encoding::NON_ALPHANUMERIC,
                )
                .to_string();
                revid_map.insert(i.to_string(), serde_json::Value::String(revid_enc));
                let merge_depth = history
                    .whole
                    .index
                    .get(&c.revid)
                    .map(|&i| history.whole.entries[i].merge_depth)
                    .unwrap_or(0);
                let mut view = ChangeView::from(c);
                view.merge_depth = merge_depth;
                view
            })
            .collect();
        let revids_json = serde_json::Value::Object(revid_map).to_string();

        Ok::<_, AppError>(PageData {
            nick: history.nick,
            start_revno,
            end_revno,
            show_tag_col,
            changes: views,
            revids_json,
            next_start_revno,
            prev_start_revno,
        })
    })
    .await??;

    // Pagination link construction is URL-routing-shaped so we do it
    // out here where we already have the url_prefix.
    let url_prefix = &state.url_prefix;
    let next_page_url = data.next_start_revno.as_ref().map(|r| {
        format!(
            "{}/changes{}",
            url_prefix,
            pagination_query(&filter_path_for_query, Some(r))
        )
    });
    let prev_page_url = data.prev_start_revno.as_ref().map(|r| {
        format!(
            "{}/changes{}",
            url_prefix,
            pagination_query(&filter_path_for_query, Some(r))
        )
    });

    let tmpl = ChangelogTemplate {
        nick: data.nick,
        fileview_active: false,
        url_prefix: state.url_prefix.clone(),
        served_url: state.root.clone(),
        last_revno: data.start_revno,
        end_revno: data.end_revno,
        show_tag_col: data.show_tag_col,
        changes: data.changes,
        prev_page_url,
        next_page_url,
        filter_path: filter_path_for_query.unwrap_or_default(),
        revids_json: data.revids_json,
    };
    Ok(Html(tmpl.render()?))
}

impl From<Change> for ChangeView {
    fn from(c: Change) -> Self {
        let is_merge = c.parents.len() > 1;
        let tags = c.tags.join(", ");
        ChangeView {
            revno: c.revno,
            short_message: c.short_message,
            author: hide_email(&c.committer),
            utc_iso: utc_iso(c.timestamp, c.timezone),
            relative_date: approximate_date(c.timestamp),
            tags,
            is_merge,
            merge_depth: 0,
        }
    }
}

fn filter_by_path(
    branch: &dyn Branch,
    mainline: &[RevisionId],
    path: &str,
) -> Result<Vec<RevisionId>, AppError> {
    let repo = branch.repository();
    let p = PathBuf::from(path);
    let mut out = Vec::new();
    for rid in mainline {
        if rid.is_null() {
            continue;
        }
        let tree = repo.revision_tree(rid)?;
        if let Ok(file_rev) = tree.get_file_revision(&p) {
            if file_rev == *rid {
                out.push(rid.clone());
            }
        }
    }
    Ok(out)
}
