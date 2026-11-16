//! Bazaar smart-protocol HTTP helper.
//!
//! Loggerhead speaks plain HTTP for its browser views, but the Bazaar
//! command line (`bzr branch http://host/path`, `bzr pull`, ...) uses
//! the smart protocol over HTTP POST to `.bzr/smart`. This module
//! wraps [`breezyshim::bazaar::smart`] into a single call that
//! takes a request body and returns the response bytes a caller
//! should send back with `Content-Type: application/octet-stream`.
//!
//! The helper is deliberately minimal: it owns the
//! `detect_protocol_factory` -> `ResponseBuffer` -> `build` ->
//! `accept_bytes` -> `next_read_size` sequence and nothing else.
//! Routing, authentication, read-only wrapping, and per-request
//! transport resolution stay with the caller.
//!
//! All breezyshim calls are synchronous (PyO3 -> Python), so from an
//! async context callers should run [`run_exchange`] inside
//! [`tokio::task::spawn_blocking`].
//!
//! # Example
//!
//! ```no_run
//! use breezyshim::transport::get_transport;
//! use loggerhead::smart;
//!
//! # fn demo(body: &[u8]) -> Result<Vec<u8>, smart::SmartError> {
//! let url = url::Url::parse("file:///srv/bzr/foo").unwrap();
//! let transport = get_transport(&url, None)?;
//! smart::run_exchange(&transport, &transport, Some("."), body)
//! # }
//! ```

use breezyshim::bazaar::smart::{detect_protocol_factory, ResponseBuffer};
use breezyshim::transport::Transport;

/// Canonical response body Bazaar expects when the request bytes are
/// truncated or the client's protocol version is newer than this
/// server understands. Matches what Python's `breezy.transport.http.wsgi`
/// writes.
pub const INCOMPLETE_REQUEST_ERROR: &[u8] = b"error\x01incomplete request\n";

/// Error returned by [`run_exchange`].
#[derive(Debug, thiserror::Error)]
pub enum SmartError {
    /// A breezyshim call (protocol detection, transport, buffer,
    /// `build`, `accept_bytes`, or `next_read_size`) failed.
    #[error("breezy error: {0}")]
    Breezy(Box<breezyshim::error::Error>),
}

impl From<breezyshim::error::Error> for SmartError {
    fn from(e: breezyshim::error::Error) -> Self {
        SmartError::Breezy(Box::new(e))
    }
}

/// Run one smart-protocol exchange and return the response bytes.
///
/// `backing` is the transport the protocol serves from. `jail` bounds
/// which paths the client may reach — typically the top-level branch
/// transport. `root_client_path` is the path prefix the client's
/// request URIs are relative to (pass `Some(".")` for the common case
/// of serving a single branch at the request root, or `None` to use
/// the client's paths as-is).
///
/// Returns [`INCOMPLETE_REQUEST_ERROR`] as the response body when the
/// protocol reports an incomplete request after `accept_bytes` —
/// callers should still send this as a `200 OK` with
/// `Content-Type: application/octet-stream`; the error is a protocol
/// response, not a transport error.
pub fn run_exchange(
    backing: &Transport,
    jail: &Transport,
    root_client_path: Option<&str>,
    body: &[u8],
) -> Result<Vec<u8>, SmartError> {
    let buffer = ResponseBuffer::new()?;
    let write_func = buffer.write_func()?;

    let (factory, unused) = detect_protocol_factory(body)?;
    let proto = factory.build(backing, write_func, root_client_path, jail)?;
    proto.accept_bytes(&unused)?;

    if proto.next_read_size()? != 0 {
        return Ok(INCOMPLETE_REQUEST_ERROR.to_vec());
    }

    Ok(buffer.into_bytes()?)
}

#[cfg(test)]
mod tests {
    use super::*;

    fn init() {
        // breezyshim's shared init; needed for any test that touches Python.
        breezyshim::init();
    }

    fn file_transport(path: &std::path::Path) -> Transport {
        let url = url::Url::from_file_path(path).unwrap();
        breezyshim::transport::get_transport(&url, None).unwrap()
    }

    /// A well-formed v3 request against an empty on-disk transport
    /// round-trips: the exchange returns a non-empty response body
    /// (whatever breezy answers for the verb — we don't care about
    /// the payload here, only that the glue works).
    #[test]
    fn round_trips_v3_request() {
        init();
        let tmp = tempfile::tempdir().unwrap();
        let transport = file_transport(tmp.path());

        // Minimal v3 "hello"-style request: verb 'hello' on path '.'.
        // Build the same way breezyshim's own test does.
        let verb = "hello";
        let path = ".";
        let args = format!("l{}:{}{}:{}e", verb.len(), verb, path.len(), path);
        let mut request = b"bzr message 3 (bzr 1.6)\n".to_vec();
        request.extend(2u32.to_be_bytes());
        request.extend(b"des");
        request.extend((args.len() as u32).to_be_bytes());
        request.extend(b"s");
        request.extend(args.as_bytes());
        request.extend(b"e");

        let response = run_exchange(&transport, &transport, Some("/"), &request).unwrap();
        assert!(!response.is_empty());
        assert_ne!(response.as_slice(), INCOMPLETE_REQUEST_ERROR);
    }

    /// A truncated request body makes `next_read_size` non-zero after
    /// `accept_bytes`; the helper swaps that for the canonical
    /// incomplete-request body so HTTP callers have a single
    /// well-defined thing to send back.
    #[test]
    fn truncated_request_returns_incomplete_error() {
        init();
        let tmp = tempfile::tempdir().unwrap();
        let transport = file_transport(tmp.path());

        // v3 marker alone — the protocol will want more bytes.
        let body: &[u8] = b"bzr message 3 (bzr 1.6)\n";
        let response = run_exchange(&transport, &transport, Some("/"), body).unwrap();
        assert_eq!(response.as_slice(), INCOMPLETE_REQUEST_ERROR);
    }
}
