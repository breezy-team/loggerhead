use axum::http::StatusCode;
use axum::response::{IntoResponse, Response};

/// Error type surfaced by controllers and returned to axum.
#[derive(Debug, thiserror::Error)]
pub enum AppError {
    #[error("branch not found: {0}")]
    NotFound(String),

    #[error("breezy error: {0}")]
    Breezy(Box<breezyshim::error::Error>),

    #[error("template render: {0}")]
    Template(#[from] askama::Error),

    #[error("join error: {0}")]
    Join(#[from] tokio::task::JoinError),

    #[error("url parse: {0}")]
    Url(#[from] url::ParseError),

    #[error("{0}")]
    Other(String),
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let (status, msg) = match &self {
            AppError::NotFound(_) => (StatusCode::NOT_FOUND, self.to_string()),
            _ => (StatusCode::INTERNAL_SERVER_ERROR, self.to_string()),
        };
        tracing::error!(error = %self, "request failed");
        (status, msg).into_response()
    }
}

pub type AppResult<T> = Result<T, AppError>;

impl From<breezyshim::error::Error> for AppError {
    fn from(e: breezyshim::error::Error) -> Self {
        AppError::Breezy(Box::new(e))
    }
}
