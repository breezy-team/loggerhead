use askama::Template;
use axum::http::{header, StatusCode};
use axum::response::{Html, IntoResponse, Response};

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

#[derive(Template)]
#[template(path = "error.html")]
struct ErrorTemplate {
    // base-template fields
    nick: String,
    #[allow(dead_code)]
    fileview_active: bool,
    url_prefix: String,
    // page
    error_title: String,
    error_description: String,
}

impl IntoResponse for AppError {
    fn into_response(self) -> Response {
        let status = match &self {
            AppError::NotFound(_) => StatusCode::NOT_FOUND,
            _ => StatusCode::INTERNAL_SERVER_ERROR,
        };
        let title = match &self {
            AppError::NotFound(_) => "Not Found".to_string(),
            AppError::Breezy(_) => "Breezy error".to_string(),
            AppError::Template(_) => "Template rendering error".to_string(),
            AppError::Join(_) => "Task join error".to_string(),
            AppError::Url(_) => "Invalid URL".to_string(),
            AppError::Other(_) => "Error".to_string(),
        };
        let description = self.to_string();
        tracing::error!(error = %self, "request failed");

        let tmpl = ErrorTemplate {
            nick: String::new(),
            fileview_active: false,
            url_prefix: String::new(),
            error_title: title,
            error_description: description.clone(),
        };
        match tmpl.render() {
            Ok(body) => (
                status,
                [(header::CONTENT_TYPE, "text/html; charset=utf-8")],
                Html(body),
            )
                .into_response(),
            // If rendering the error template itself fails, fall back to
            // plain text so at least something lands on the wire.
            Err(_) => (status, description).into_response(),
        }
    }
}

pub type AppResult<T> = Result<T, AppError>;

impl From<breezyshim::error::Error> for AppError {
    fn from(e: breezyshim::error::Error) -> Self {
        AppError::Breezy(Box::new(e))
    }
}
