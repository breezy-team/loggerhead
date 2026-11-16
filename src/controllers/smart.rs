//! `POST /.bzr/smart` — Bazaar smart-protocol endpoint.
//!
//! Lets `bzr branch http://host/path` and friends work against a
//! loggerhead-served branch. Opens the branch's transport (wrapped
//! in `readonly+` since loggerhead is a viewer, not a push target),
//! hands the request body to [`crate::smart::run_exchange`], and
//! streams the response bytes back as `application/octet-stream`.

use std::sync::Arc;

use axum::body::Bytes;
use axum::extract::State;
use axum::http::{header, StatusCode};
use axum::response::{IntoResponse, Response};
use breezyshim::branch::Branch;
use breezyshim::transport::{get_transport, Transport};

use crate::app::AppState;
use crate::breezy::open_branch;
use crate::smart::run_exchange;
use crate::util::errors::{AppError, AppResult};

/// Wrap `transport` in a `readonly+` layer so the smart server
/// rejects any write attempts at the transport level.
fn readonly(transport: &Transport) -> AppResult<Transport> {
    let readonly_url = url::Url::parse(&format!("readonly+{}", transport.base()))?;
    Ok(get_transport(&readonly_url, None)?)
}

/// `POST /.bzr/smart` — serve a Bazaar smart-protocol request.
///
/// `root_client_path` is `"."` because the smart request paths are
/// relative to the served branch. The branch's `user_transport` is
/// used as the jail root so clients can't reach outside the branch.
pub async fn handle(State(state): State<Arc<AppState>>, body: Bytes) -> AppResult<Response> {
    let response_bytes = tokio::task::spawn_blocking(move || -> AppResult<Vec<u8>> {
        let branch = open_branch(&state.root)?;
        let jail = branch.user_transport();
        let backing = readonly(&jail)?;
        run_exchange(&backing, &jail, Some("."), &body).map_err(|e| AppError::Other(e.to_string()))
    })
    .await??;

    Ok((
        StatusCode::OK,
        [(header::CONTENT_TYPE, "application/octet-stream")],
        response_bytes,
    )
        .into_response())
}
