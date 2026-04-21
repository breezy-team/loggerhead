//! Thin ergonomics layer over breezyshim.
//!
//! All calls into breezyshim hold the Python GIL, so every public function
//! here is synchronous and intended to run on a blocking thread. Wrap calls
//! from async code in [`tokio::task::spawn_blocking`].

use std::path::Path;

use breezyshim::branch::{Branch, GenericBranch};
use url::Url;

use crate::util::errors::AppError;

/// True iff the branch's config permits being served over HTTP.
/// Mirrors Python loggerhead's
/// `branch.get_config().get_user_option_as_bool("http_serve",
/// default=True)` check. Errors reading the config fall back to
/// `true` (permissive) — matching Python's behaviour when the key
/// is missing.
pub fn is_http_serveable(branch: &dyn Branch) -> bool {
    branch
        .get_config()
        .get_user_option_as_bool("http_serve", true)
        .unwrap_or(true)
}

/// Open a Breezy branch from a filesystem path or URL.
pub fn open_branch(location: &str) -> Result<GenericBranch, AppError> {
    let url = match Url::parse(location) {
        Ok(u) => u,
        Err(_) => {
            let abs = Path::new(location)
                .canonicalize()
                .map_err(|e| AppError::Other(format!("canonicalize {location}: {e}")))?;
            Url::from_directory_path(&abs)
                .map_err(|()| AppError::Other(format!("cannot turn {abs:?} into file:// URL")))?
        }
    };
    let branch = breezyshim::branch::open_as_generic(&url)?;
    Ok(branch)
}

/// Information about a branch suitable for the landing page.
pub struct BranchInfo {
    pub nick: String,
    pub last_revision: String,
    pub revno: u32,
}

pub fn branch_info(location: &str) -> Result<BranchInfo, AppError> {
    let branch = open_branch(location)?;
    let (revno, last_rev) = branch.last_revision_info();
    let nick = branch.name().unwrap_or_else(|| "<unnamed>".to_string());
    Ok(BranchInfo {
        nick,
        last_revision: last_rev.as_str().to_string(),
        revno,
    })
}
