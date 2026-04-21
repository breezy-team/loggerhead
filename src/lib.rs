//! Loggerhead: a web viewer for Bazaar/Breezy branches.
//!
//! This crate provides the HTTP server, routing, templates, and VCS glue.
//! VCS access is via [`breezyshim`], a PyO3 wrapper around the Python
//! `breezy` library — all VCS calls are synchronous and must run on the
//! blocking thread pool.

pub mod app;
pub mod breezy;
pub mod cache;
pub mod config;
pub mod controllers;
pub mod highlight;
pub mod history;
pub mod util;
