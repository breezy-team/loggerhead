use std::path::PathBuf;
use std::sync::Arc;

use axum::body::Body;
use axum::extract::{Path, State};
use axum::http::{header, StatusCode};
use axum::response::{IntoResponse, Response};
use breezyshim::branch::Branch;
use breezyshim::export::{archive, ArchiveFormat};
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tree::Tree;
use percent_encoding::{percent_decode_str, utf8_percent_encode, NON_ALPHANUMERIC};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::util::errors::{AppError, AppResult};

/// GET /download/:revid/*path — stream a single file at `path` from `revid`.
pub async fn show_file(
    State(state): State<Arc<AppState>>,
    Path((revid_enc, path_enc)): Path<(String, String)>,
) -> AppResult<Response> {
    let revid = RevisionId::from(
        percent_decode_str(&revid_enc)
            .decode_utf8_lossy()
            .into_owned()
            .into_bytes(),
    );
    let path = percent_decode_str(&path_enc)
        .decode_utf8_lossy()
        .into_owned();
    let filename = StdPath::new(&path)
        .file_name()
        .map(|n| n.to_string_lossy().into_owned())
        .unwrap_or_else(|| path.clone());

    let path_for_task = path.clone();
    let content = tokio::task::spawn_blocking(move || -> AppResult<Vec<u8>> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let repo = branch.repository();
        let tree = repo.revision_tree(&revid)?;
        let p = PathBuf::from(&path_for_task);
        Ok(tree.get_file_text(&p)?)
    })
    .await??;

    let mime = mime_guess::from_path(&filename)
        .first_or_octet_stream()
        .to_string();
    let encoded = utf8_percent_encode(&filename, NON_ALPHANUMERIC).to_string();
    Ok(Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, mime)
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename*=utf-8''{encoded}"),
        )
        .body(Body::from(content))
        .unwrap()
        .into_response())
}

/// GET /tarball/:revid — stream a tgz of the tree at `revid`.
pub async fn tarball(
    State(state): State<Arc<AppState>>,
    Path(revid_enc): Path<String>,
) -> AppResult<Response> {
    if !state.export_tarballs {
        return Err(AppError::Other("tarball export is disabled".into()));
    }
    let revid = RevisionId::from(
        percent_decode_str(&revid_enc)
            .decode_utf8_lossy()
            .into_owned()
            .into_bytes(),
    );

    // Gather the archive into memory inside spawn_blocking. Streaming the
    // iterator across the async boundary while still holding the GIL is
    // awkward; for the sizes most loggerhead deployments see this is a fair
    // tradeoff, and we can revisit with a bounded mpsc channel if needed.
    let (bytes, filename) = tokio::task::spawn_blocking(move || -> AppResult<_> {
        let branch = open_branch(&state.root)?;
        let _lock = branch.lock_read()?;
        let nick = branch
            .get_config()
            .get_nickname()
            .unwrap_or_else(|_| "branch".into());
        let repo = branch.repository();
        let tree = repo.revision_tree(&revid)?;
        let filename = format!("{nick}.tgz");
        let mut out = Vec::new();
        for chunk in archive(&tree, ArchiveFormat::Tgz, &filename, None, Some(&nick))? {
            out.extend_from_slice(&chunk?);
        }
        Ok::<_, AppError>((out, filename))
    })
    .await??;

    let encoded = utf8_percent_encode(&filename, NON_ALPHANUMERIC).to_string();
    Ok(Response::builder()
        .status(StatusCode::OK)
        .header(header::CONTENT_TYPE, "application/octet-stream")
        .header(
            header::CONTENT_DISPOSITION,
            format!("attachment; filename*=utf-8''{encoded}"),
        )
        .body(Body::from(bytes))
        .unwrap()
        .into_response())
}

use std::path::Path as StdPath;
