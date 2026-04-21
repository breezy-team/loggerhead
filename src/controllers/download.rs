use std::path::Path as StdPath;
use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Body;
use axum::extract::{Path, State};
use axum::http::{header, StatusCode};
use axum::response::{IntoResponse, Redirect, Response};
use breezyshim::branch::Branch;
use breezyshim::export::{archive, ArchiveFormat};
use breezyshim::repository::Repository;
use breezyshim::tree::Tree;
use percent_encoding::{percent_decode_str, utf8_percent_encode, NON_ALPHANUMERIC};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::history::History;
use crate::util::errors::{AppError, AppResult};
use crate::util::fmt::http_date;

/// GET /download (no args) — permanent redirect to `/changes`. Matches
/// Python's DownloadUI, which redirects when fewer than two args are given.
pub async fn show_bare(State(state): State<Arc<AppState>>) -> Redirect {
    Redirect::permanent(&state.url("/changes"))
}

/// GET /download/:revid/*path — stream a single file at `path` from
/// `revid` (a dotted revno, `head:`, or a raw revid).
pub async fn show_file(
    State(state): State<Arc<AppState>>,
    Path((revid_enc, path_enc)): Path<(String, String)>,
) -> AppResult<Response> {
    let idref = percent_decode_str(&revid_enc)
        .decode_utf8_lossy()
        .into_owned();
    let path = percent_decode_str(&path_enc)
        .decode_utf8_lossy()
        .into_owned();
    let filename = StdPath::new(&path)
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_else(|| path.clone());

    let path_for_task = path.clone();
    let (content, timestamp) = tokio::task::spawn_blocking(move || -> AppResult<(Vec<u8>, f64)> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let revid = history
            .fix_revid(&idref)
            .ok_or_else(|| AppError::NotFound(format!("no revision {idref}")))?;
        let repo = branch.repository();
        let tree = repo.revision_tree(&revid)?;
        let p = PathBuf::from(&path_for_task);
        let bytes = tree.get_file_text(&p)?;
        // `Last-Modified` for the download: timestamp of the revision
        // being served, not the branch tip. See Launchpad bug #503144.
        let timestamp = repo.get_revision(&revid)?.timestamp;
        Ok((bytes, timestamp))
    })
    .await??;

    let mime = mime_guess::from_path(&filename)
        .first_or_octet_stream()
        .to_string();
    let encoded = utf8_percent_encode(&filename, NON_ALPHANUMERIC).to_string();
    let mut builder = Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, mime)
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename*=utf-8''{encoded}"),
        );
    if let Some(d) = http_date(timestamp) {
        builder = builder.header(header::LAST_MODIFIED, d);
    }
    Ok(builder.body(Body::from(content)).unwrap().into_response())
}

/// GET /tarball/:revid — stream a tgz of the tree at the given
/// revision reference (dotted revno, `head:`, or raw revid).
pub async fn tarball(
    State(state): State<Arc<AppState>>,
    Path(revid_enc): Path<String>,
) -> AppResult<Response> {
    if !state.export_tarballs {
        return Err(AppError::Other("tarball export is disabled".into()));
    }
    let idref = percent_decode_str(&revid_enc)
        .decode_utf8_lossy()
        .into_owned();

    // Gather the archive into memory inside spawn_blocking. Streaming the
    // iterator across the async boundary while still holding the GIL is
    // awkward; for the sizes most loggerhead deployments see this is a fair
    // tradeoff, and we can revisit with a bounded mpsc channel if needed.
    let (bytes, filename, timestamp) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let whole = state.load_whole_history(&branch)?;
        let history = History::from_whole(&branch, (*whole).clone())?;
        let revid = history
            .fix_revid(&idref)
            .ok_or_else(|| AppError::NotFound(format!("no revision {idref}")))?;
        let nick = branch
            .get_config()
            .get_nickname()
            .unwrap_or_else(|_| "branch".into());
        let repo = branch.repository();
        let tree = repo.revision_tree(&revid)?;
        // Python names the file `<nick>-r<ref>.tgz` when a rev is
        // specified; we use the revno form since `idref` may already
        // be a dotted revno.
        let revno_part = history.whole.get_revno(&revid);
        let filename = format!("{nick}-r{revno_part}.tgz");
        let timestamp = repo.get_revision(&revid)?.timestamp;
        let mut out = Vec::new();
        for chunk in archive(&tree, ArchiveFormat::Tgz, &filename, None, Some(&nick))? {
            out.extend_from_slice(&chunk?);
        }
        Ok::<_, AppError>((out, filename, timestamp))
    })
    .await??;

    let encoded = utf8_percent_encode(&filename, NON_ALPHANUMERIC).to_string();
    let mut builder = Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "application/octet-stream")
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename*=utf-8''{encoded}"),
        );
    if let Some(d) = http_date(timestamp) {
        builder = builder.header(header::LAST_MODIFIED, d);
    }
    Ok(builder.body(Body::from(bytes)).unwrap().into_response())
}
