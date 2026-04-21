//! Small formatters used by templates: author-display scrubbing, relative
//! dates, etc. Keep this dumb/stateless so templates can call through.

use chrono::{DateTime, FixedOffset, TimeZone, Utc};

/// Strip the `<email>` part from a `"Name <email@host>"` committer string,
/// matching Python loggerhead's `util.hide_email`.
pub fn hide_email(author: &str) -> String {
    match author.find('<') {
        Some(i) => author[..i].trim().to_string(),
        None => author.trim().to_string(),
    }
}

/// Render a Breezy timestamp+timezone as the "2026-04-21 17:09:44 UTC" form
/// Python loggerhead uses as the `<span title>` tooltip.
pub fn utc_iso(timestamp: f64, timezone: i32) -> String {
    let tz = FixedOffset::east_opt(timezone).unwrap_or(FixedOffset::east_opt(0).unwrap());
    match tz.timestamp_opt(timestamp as i64, 0).single() {
        Some(dt) => dt
            .with_timezone(&Utc)
            .format("%Y-%m-%d %H:%M:%S UTC")
            .to_string(),
        None => String::new(),
    }
}

/// Render a Breezy timestamp as a human-readable relative-time string,
/// mirroring Python loggerhead's `util.approximate_date`:
///   "just now", "N minutes ago", "N hours ago", "yesterday at ...",
///   "N days ago", "YYYY-MM-DD".
pub fn approximate_date(timestamp: f64) -> String {
    let Some(dt) = DateTime::<Utc>::from_timestamp(timestamp as i64, 0) else {
        return String::new();
    };
    let now = Utc::now();
    let delta = now - dt;
    let secs = delta.num_seconds();
    if secs < 60 {
        "just now".to_string()
    } else if secs < 3600 {
        let m = secs / 60;
        format!("{m} minute{} ago", if m == 1 { "" } else { "s" })
    } else if secs < 86_400 {
        let h = secs / 3600;
        format!("{h} hour{} ago", if h == 1 { "" } else { "s" })
    } else if secs < 7 * 86_400 {
        let d = secs / 86_400;
        format!("{d} day{} ago", if d == 1 { "" } else { "s" })
    } else {
        dt.format("%Y-%m-%d").to_string()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn hide_email_strips_angle_block() {
        assert_eq!(
            hide_email("Jelmer Vernooij <jelmer@jelmer.uk>"),
            "Jelmer Vernooij"
        );
    }

    #[test]
    fn hide_email_passthrough_when_no_angle() {
        assert_eq!(hide_email("Anonymous"), "Anonymous");
    }

    #[test]
    fn approximate_date_just_now() {
        let now = Utc::now().timestamp() as f64;
        assert_eq!(approximate_date(now), "just now");
    }

    #[test]
    fn approximate_date_hours_ago() {
        let t = (Utc::now() - chrono::Duration::hours(3)).timestamp() as f64;
        assert_eq!(approximate_date(t), "3 hours ago");
    }
}
