use std::path::{Path, PathBuf};
use std::sync::Mutex;

use breezyshim::revisionid::RevisionId;
use rusqlite::{params, Connection, OptionalExtension};

use crate::history::{RevInfo, WholeHistory};
use crate::util::errors::AppError;

/// SQLite-backed cache of expensive per-branch computations.
///
/// Storage layout:
///
/// ```sql
/// CREATE TABLE data (
///     key   BLOB PRIMARY KEY,  -- logical key (e.g. "whole_history")
///     revid BLOB,              -- branch tip this entry was computed for
///     data  BLOB               -- encoded payload
/// );
/// ```
///
/// Entries become stale once the branch tip moves; the caller decides what
/// to do by passing the current tip to [`get_whole_history`] — a mismatch
/// produces `None`.
pub struct RevInfoDiskCache {
    conn: Mutex<Connection>,
    #[allow(dead_code)]
    path: PathBuf,
}

impl RevInfoDiskCache {
    /// Open (creating if necessary) a cache under `cache_path`.
    ///
    /// The directory is created on demand. The DB file is named `revinfo.sql`
    /// inside that directory, matching the Python layout.
    pub fn open(cache_path: &Path) -> Result<Self, AppError> {
        std::fs::create_dir_all(cache_path)
            .map_err(|e| AppError::Other(format!("mkdir {cache_path:?}: {e}")))?;
        let path = cache_path.join("revinfo.sql");
        let conn =
            Connection::open(&path).map_err(|e| AppError::Other(format!("open {path:?}: {e}")))?;
        conn.execute_batch(
            "CREATE TABLE IF NOT EXISTS data (
                 key   BLOB PRIMARY KEY,
                 revid BLOB,
                 data  BLOB
             );
             PRAGMA journal_mode = WAL;",
        )
        .map_err(|e| AppError::Other(format!("init schema: {e}")))?;
        Ok(Self {
            conn: Mutex::new(conn),
            path,
        })
    }

    /// Look up a cached [`WholeHistory`]. Returns `None` if absent, if the
    /// stored tip doesn't match `current_tip`, or if the payload can't be
    /// decoded (which is treated as a miss — the cache will be overwritten
    /// on the next `set`).
    pub fn get_whole_history(&self, current_tip: &RevisionId) -> Option<WholeHistory> {
        let conn = self.conn.lock().ok()?;
        let row: (Vec<u8>, Vec<u8>) = conn
            .query_row(
                "SELECT revid, data FROM data WHERE key = ?",
                params![WHOLE_HISTORY_KEY],
                |r| Ok((r.get::<_, Vec<u8>>(0)?, r.get::<_, Vec<u8>>(1)?)),
            )
            .optional()
            .ok()
            .flatten()?;
        if row.0.as_slice() != current_tip.as_bytes() {
            return None;
        }
        decode_whole_history(&row.1).ok()
    }

    /// Store `wh` under the logical `WHOLE_HISTORY_KEY`, stamped with `tip`.
    /// Errors are logged but not propagated — a cache-write failure is
    /// never fatal for a read.
    pub fn set_whole_history(&self, tip: &RevisionId, wh: &WholeHistory) {
        let blob = encode_whole_history(wh);
        let Ok(conn) = self.conn.lock() else { return };
        if let Err(e) = conn.execute(
            "INSERT INTO data (key, revid, data) VALUES (?, ?, ?)
             ON CONFLICT(key) DO UPDATE SET revid = excluded.revid, data = excluded.data",
            params![WHOLE_HISTORY_KEY, tip.as_bytes(), blob],
        ) {
            tracing::warn!(error = %e, "disk cache write failed");
        }
    }
}

const WHOLE_HISTORY_KEY: &[u8] = b"whole_history";

/// Magic+version header so we can change the encoding later and reject
/// stale entries rather than misinterpret them.
const MAGIC: &[u8; 4] = b"LHWH";
const VERSION: u8 = 1;

fn encode_whole_history(wh: &WholeHistory) -> Vec<u8> {
    let mut out = Vec::with_capacity(256 + wh.entries.len() * 64);
    out.extend_from_slice(MAGIC);
    out.push(VERSION);
    put_u64(&mut out, wh.entries.len() as u64);
    for e in &wh.entries {
        put_u64(&mut out, e.sequence as u64);
        put_bytes(&mut out, e.revid.as_bytes());
        put_u64(&mut out, e.merge_depth as u64);
        put_bytes(&mut out, e.revno.as_bytes());
        out.push(u8::from(e.end_of_merge));
        put_u64(&mut out, e.parents.len() as u64);
        for p in &e.parents {
            put_bytes(&mut out, p.as_bytes());
        }
        put_u64(&mut out, e.children.len() as u64);
        for c in &e.children {
            put_bytes(&mut out, c.as_bytes());
        }
    }
    out
}

fn decode_whole_history(blob: &[u8]) -> Result<WholeHistory, DecodeError> {
    let mut cur = Cursor::new(blob);
    let magic = cur.take(4)?;
    if magic != MAGIC {
        return Err(DecodeError::BadMagic);
    }
    let version = cur.take_u8()?;
    if version != VERSION {
        return Err(DecodeError::BadVersion(version));
    }
    let n = cur.take_u64()? as usize;
    let mut entries = Vec::with_capacity(n);
    let mut index = std::collections::HashMap::with_capacity(n);
    for _ in 0..n {
        let sequence = cur.take_u64()? as usize;
        let revid = RevisionId::from(cur.take_bytes()?);
        let merge_depth = cur.take_u64()? as usize;
        let revno_bytes = cur.take_bytes()?;
        let revno =
            String::from_utf8(revno_bytes).map_err(|_| DecodeError::InvalidUtf8("revno"))?;
        let end_of_merge = cur.take_u8()? != 0;
        let pcount = cur.take_u64()? as usize;
        let mut parents = Vec::with_capacity(pcount);
        for _ in 0..pcount {
            parents.push(RevisionId::from(cur.take_bytes()?));
        }
        let ccount = cur.take_u64()? as usize;
        let mut children = Vec::with_capacity(ccount);
        for _ in 0..ccount {
            children.push(RevisionId::from(cur.take_bytes()?));
        }
        index.insert(revid.clone(), entries.len());
        entries.push(RevInfo {
            sequence,
            revid,
            merge_depth,
            revno,
            end_of_merge,
            parents,
            children,
        });
    }
    Ok(WholeHistory { entries, index })
}

fn put_u64(out: &mut Vec<u8>, v: u64) {
    out.extend_from_slice(&v.to_le_bytes());
}

fn put_bytes(out: &mut Vec<u8>, b: &[u8]) {
    put_u64(out, b.len() as u64);
    out.extend_from_slice(b);
}

struct Cursor<'a> {
    buf: &'a [u8],
    pos: usize,
}

impl<'a> Cursor<'a> {
    fn new(buf: &'a [u8]) -> Self {
        Self { buf, pos: 0 }
    }

    fn take(&mut self, n: usize) -> Result<&'a [u8], DecodeError> {
        let end = self.pos.checked_add(n).ok_or(DecodeError::Truncated)?;
        if end > self.buf.len() {
            return Err(DecodeError::Truncated);
        }
        let out = &self.buf[self.pos..end];
        self.pos = end;
        Ok(out)
    }

    fn take_u8(&mut self) -> Result<u8, DecodeError> {
        Ok(self.take(1)?[0])
    }

    fn take_u64(&mut self) -> Result<u64, DecodeError> {
        let bytes = self.take(8)?;
        let mut arr = [0u8; 8];
        arr.copy_from_slice(bytes);
        Ok(u64::from_le_bytes(arr))
    }

    fn take_bytes(&mut self) -> Result<Vec<u8>, DecodeError> {
        let n = self.take_u64()? as usize;
        Ok(self.take(n)?.to_vec())
    }
}

#[derive(Debug, thiserror::Error)]
enum DecodeError {
    #[error("truncated cache entry")]
    Truncated,
    #[error("bad magic")]
    BadMagic,
    #[error("unsupported cache version {0}")]
    BadVersion(u8),
    #[error("invalid utf-8 in {0}")]
    InvalidUtf8(&'static str),
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::collections::HashMap;
    use tempfile::TempDir;

    fn sample_whole_history() -> WholeHistory {
        let r1 = RevisionId::from(b"rev-1".to_vec());
        let r2 = RevisionId::from(b"rev-2".to_vec());
        let entries = vec![
            RevInfo {
                sequence: 0,
                revid: r2.clone(),
                merge_depth: 0,
                revno: "2".to_string(),
                end_of_merge: true,
                parents: vec![r1.clone()],
                children: Vec::new(),
            },
            RevInfo {
                sequence: 1,
                revid: r1.clone(),
                merge_depth: 0,
                revno: "1".to_string(),
                end_of_merge: true,
                parents: Vec::new(),
                children: Vec::new(),
            },
        ];
        let mut index = HashMap::new();
        index.insert(r2, 0);
        index.insert(r1, 1);
        WholeHistory { entries, index }
    }

    #[test]
    fn round_trip_encoding() {
        let wh = sample_whole_history();
        let encoded = encode_whole_history(&wh);
        let decoded = decode_whole_history(&encoded).unwrap();
        assert_eq!(decoded.entries.len(), wh.entries.len());
        for (a, b) in decoded.entries.iter().zip(wh.entries.iter()) {
            assert_eq!(a.sequence, b.sequence);
            assert_eq!(a.revid.as_bytes(), b.revid.as_bytes());
            assert_eq!(a.revno, b.revno);
            assert_eq!(a.parents.len(), b.parents.len());
        }
    }

    #[test]
    fn disk_cache_get_set() {
        let tmp = TempDir::new().unwrap();
        let cache = RevInfoDiskCache::open(tmp.path()).unwrap();
        let tip = RevisionId::from(b"rev-2".to_vec());
        assert!(cache.get_whole_history(&tip).is_none());

        let wh = sample_whole_history();
        cache.set_whole_history(&tip, &wh);
        let fetched = cache.get_whole_history(&tip).unwrap();
        assert_eq!(fetched.entries.len(), 2);

        // Different tip → treated as miss.
        let other = RevisionId::from(b"other".to_vec());
        assert!(cache.get_whole_history(&other).is_none());
    }

    #[test]
    fn rejects_bad_magic() {
        assert!(matches!(
            decode_whole_history(b"ZZZZ\x01\x00\x00\x00\x00\x00\x00\x00\x00"),
            Err(DecodeError::BadMagic)
        ));
    }

    #[test]
    fn rejects_bad_version() {
        let mut blob = MAGIC.to_vec();
        blob.push(99);
        blob.extend_from_slice(&0u64.to_le_bytes());
        assert!(matches!(
            decode_whole_history(&blob),
            Err(DecodeError::BadVersion(99))
        ));
    }
}
