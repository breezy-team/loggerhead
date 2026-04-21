//! On-disk cache for pre-computed branch history.
//!
//! Ported from `loggerhead/changecache.py::RevInfoDiskCache`. This is a
//! best-effort cache: missing or corrupted entries just fall through to
//! recomputation, and concurrent writers race optimistically.
//!
//! The on-disk format is **not** compatible with the Python cache (the Rust
//! implementation stores `WholeHistory` with a custom binary encoding rather
//! than pickle/marshal). The table layout is kept similar so an operator can
//! tell what's in the file.

pub mod disk;

pub use disk::RevInfoDiskCache;
