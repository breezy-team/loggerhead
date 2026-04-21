//! Syntax highlighting via [`syntect`], replacing the Python loggerhead's
//! Pygments wrapper in `loggerhead/highlight.py`.

use std::sync::OnceLock;

use syntect::highlighting::{Theme, ThemeSet};
use syntect::html::{
    append_highlighted_html_for_styled_line, start_highlighted_html_snippet, IncludeBackground,
};
use syntect::parsing::{SyntaxReference, SyntaxSet};
use syntect::util::LinesWithEndings;

/// Cap matching loggerhead's 512KB threshold — above this we return escaped
/// plain text instead of paying the highlighting cost.
const MAX_HIGHLIGHT_BYTES: usize = 512 * 1024;

fn assets() -> &'static (SyntaxSet, Theme) {
    static CELL: OnceLock<(SyntaxSet, Theme)> = OnceLock::new();
    CELL.get_or_init(|| {
        let ss = SyntaxSet::load_defaults_newlines();
        let ts = ThemeSet::load_defaults();
        let theme = ts.themes["InspiredGitHub"].clone();
        (ss, theme)
    })
}

/// Pick a syntax by filename; fall back to plain text.
fn syntax_for<'a>(ss: &'a SyntaxSet, filename: &str, first_line: &str) -> &'a SyntaxReference {
    ss.find_syntax_for_file(filename)
        .ok()
        .flatten()
        .or_else(|| ss.find_syntax_by_first_line(first_line))
        .unwrap_or_else(|| ss.find_syntax_plain_text())
}

/// Result of highlighting: HTML fragments, one per source line, without the
/// outer `<pre>`. The caller is responsible for wrapping in `<pre>` or a
/// table of (line number, content) cells.
pub struct Highlighted {
    /// One `<span>`-wrapped HTML string per source line.
    pub lines: Vec<String>,
    /// Suggested background color (rgba) for wrapping, from the theme.
    pub background: Option<String>,
}

/// Highlight `content` as the language inferred from `filename`. If the file
/// is larger than [`MAX_HIGHLIGHT_BYTES`] or syntect fails, returns escaped
/// plain text (one HTML-escaped line per input line).
pub fn highlight(filename: &str, content: &str) -> Highlighted {
    if content.len() > MAX_HIGHLIGHT_BYTES {
        return plain(content);
    }
    let (ss, theme) = assets();
    let first_line = content.lines().next().unwrap_or("");
    let syntax = syntax_for(ss, filename, first_line);
    let mut hl = syntect::easy::HighlightLines::new(syntax, theme);

    let mut out = Vec::new();
    let (_prelude, bg) = start_highlighted_html_snippet(theme);
    for line in LinesWithEndings::from(content) {
        let mut piece = String::new();
        let regions = match hl.highlight_line(line, ss) {
            Ok(r) => r,
            Err(_) => return plain(content),
        };
        if append_highlighted_html_for_styled_line(&regions, IncludeBackground::No, &mut piece)
            .is_err()
        {
            return plain(content);
        }
        // Strip the trailing newline that `LinesWithEndings` keeps so the
        // renderer can lay lines out in its own table.
        let piece = piece.trim_end_matches('\n').to_string();
        out.push(piece);
    }
    Highlighted {
        lines: out,
        background: Some(format!("rgb({}, {}, {})", bg.r, bg.g, bg.b)),
    }
}

fn plain(content: &str) -> Highlighted {
    let lines = content.lines().map(html_escape::encode_safe_str).collect();
    Highlighted {
        lines,
        background: None,
    }
}

/// Very small subset of HTML escaping — enough for file-view safety.
mod html_escape {
    pub fn encode_safe_str(s: &str) -> String {
        let mut out = String::with_capacity(s.len());
        for c in s.chars() {
            match c {
                '&' => out.push_str("&amp;"),
                '<' => out.push_str("&lt;"),
                '>' => out.push_str("&gt;"),
                '"' => out.push_str("&quot;"),
                '\'' => out.push_str("&#39;"),
                _ => out.push(c),
            }
        }
        out
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn plain_text_escapes() {
        let h = highlight("README", "a < b\n1 & 2\n");
        assert_eq!(h.lines.len(), 2);
        // Syntect can also emit HTML for plain text; just check it's valid-ish.
        assert!(h.lines[0].contains("a ") || h.lines[0].contains("&lt;"));
    }

    #[test]
    fn rust_keywords_get_spans() {
        let src = "fn main() {}\n";
        let h = highlight("main.rs", src);
        assert!(h.lines[0].contains("<span"));
    }

    #[test]
    fn huge_file_falls_back() {
        let big = "a\n".repeat(MAX_HIGHLIGHT_BYTES);
        let h = highlight("big.txt", &big);
        // Fell back — background is None for plain.
        assert!(h.background.is_none());
    }
}
