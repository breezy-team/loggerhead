//! Revision history model, porting `loggerhead/history.py` +
//! `loggerhead/wholehistory.py`.
//!
//! All methods are synchronous because they go through breezyshim (PyO3 →
//! Python GIL). Call them from a blocking task.

use std::collections::HashMap;

use breezyshim::branch::Branch;
use breezyshim::graph::Graph;
use breezyshim::repository::Repository;
use breezyshim::revisionid::RevisionId;
use breezyshim::tsort::{merge_sort, MergeSortEntry};

use crate::util::errors::AppError;

/// Per-revision data produced by the whole-history walk.
#[derive(Debug, Clone)]
pub struct RevInfo {
    pub sequence: usize,
    pub revid: RevisionId,
    pub merge_depth: usize,
    pub revno: String,
    pub end_of_merge: bool,
    /// Parents of this revision, already filtered to exclude ghosts and
    /// `NULL_REVISION` (so every entry here is present in the history).
    pub parents: Vec<RevisionId>,
    /// Revisions that list this revision among their parents.
    pub children: Vec<RevisionId>,
}

/// The result of computing the whole-branch history graph.
///
/// `entries` is laid out in merge-sort order (tip first). `index` gives the
/// position of each revid in `entries` for O(1) lookup.
#[derive(Debug, Clone)]
pub struct WholeHistory {
    pub entries: Vec<RevInfo>,
    pub index: HashMap<RevisionId, usize>,
    /// Unix timestamp of the branch tip, for Last-Modified / 304
    /// responses. `None` for an empty branch.
    pub tip_timestamp: Option<f64>,
}

impl WholeHistory {
    /// Compute the whole-history graph for a branch, mirroring
    /// `wholehistory.compute_whole_history_data`.
    pub fn compute(branch: &dyn Branch) -> Result<Self, AppError> {
        let repo = branch.repository();
        let last_revid = branch.last_revision();
        let graph: Graph = repo.get_graph();

        // Build parent map from iter_ancestry, dropping ghost entries.
        let mut parent_map: HashMap<RevisionId, Vec<RevisionId>> = HashMap::new();
        for entry in graph.iter_ancestry(std::slice::from_ref(&last_revid))? {
            let (node, parents) = entry?;
            if let Some(ps) = parents {
                parent_map.insert(node, ps);
            }
        }
        // Drop NULL_REVISION and any references to nodes not present in the
        // map (_strip_NULL_ghosts).
        let null = RevisionId::null();
        parent_map.remove(&null);
        let present: std::collections::HashSet<RevisionId> = parent_map.keys().cloned().collect();
        for parents in parent_map.values_mut() {
            parents.retain(|p| present.contains(p));
        }

        let sorted: Vec<MergeSortEntry<RevisionId>> = if last_revid.is_null() {
            Vec::new()
        } else {
            merge_sort(&parent_map, &last_revid)?
        };

        let mut entries: Vec<RevInfo> = Vec::with_capacity(sorted.len());
        let mut index: HashMap<RevisionId, usize> = HashMap::with_capacity(sorted.len());
        for e in sorted {
            let parents = parent_map.get(&e.node).cloned().unwrap_or_default();
            let pos = entries.len();
            index.insert(e.node.clone(), pos);
            let revno_str = e.revno_str();
            entries.push(RevInfo {
                sequence: e.sequence,
                revid: e.node,
                merge_depth: e.merge_depth,
                revno: revno_str,
                end_of_merge: e.end_of_merge,
                parents,
                children: Vec::new(),
            });
        }

        // Second pass: compute children, skipping mainline entries (matches
        // wholehistory.py's `merge_depth == 0` skip).
        for i in 0..entries.len() {
            if entries[i].merge_depth == 0 {
                continue;
            }
            let revid = entries[i].revid.clone();
            let parents = entries[i].parents.clone();
            for parent in parents {
                if let Some(&pi) = index.get(&parent) {
                    if !entries[pi].children.contains(&revid) {
                        entries[pi].children.push(revid.clone());
                    }
                }
            }
        }

        // Tip timestamp for Last-Modified. Fetch the tip's Revision
        // once; cheap compared to the merge-sort we just did.
        let tip_timestamp = if last_revid.is_null() {
            None
        } else {
            repo.get_revision(&last_revid).ok().map(|r| r.timestamp)
        };

        Ok(WholeHistory {
            entries,
            index,
            tip_timestamp,
        })
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }

    pub fn is_empty(&self) -> bool {
        self.entries.is_empty()
    }

    /// Look up the dotted revno for a revision id; returns `"unknown"` for
    /// missing (ghost) revisions, matching `History.get_revno`.
    pub fn get_revno(&self, revid: &RevisionId) -> String {
        match self.index.get(revid) {
            Some(&i) => self.entries[i].revno.clone(),
            None => "unknown".to_string(),
        }
    }
}

/// One entry in a revision's file-change list.
#[derive(Debug, Clone)]
pub struct FileChange {
    pub kind: FileChangeKind,
    /// Canonical path for display: new path for add/modify/rename-target,
    /// old path for remove.
    pub path: String,
    /// When the change is a rename (or copy), this is the prior path.
    pub old_path: Option<String>,
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum FileChangeKind {
    Added,
    Removed,
    Modified,
    Renamed,
    Copied,
    KindChanged,
}

/// A revision plus the rendered fields needed by the changelog template.
#[derive(Debug, Clone)]
pub struct Change {
    pub revid: RevisionId,
    pub revno: String,
    pub committer: String,
    pub timestamp: f64,
    pub timezone: i32,
    pub message: String,
    pub short_message: String,
    pub parents: Vec<(RevisionId, String)>, // (revid, revno)
    pub tags: Vec<String>,
    /// Bug URLs from the `bugs` revision property. Each entry is a
    /// URL (first whitespace-delimited token of a line). Rendered as
    /// clickable links on the revision page.
    pub bugs: Vec<String>,
}

/// Branch-scoped history object, analogous to `loggerhead.history.History`.
pub struct History {
    pub last_revid: RevisionId,
    pub nick: String,
    pub whole: WholeHistory,
    pub branch_tags: HashMap<RevisionId, Vec<String>>,
}

impl History {
    /// Resolve a URL identifier (either a dotted revno like `"3"` or
    /// `"1.2.3"`, the literal `"head:"`, or a raw revid) to a concrete
    /// `RevisionId`. Mirrors Python `History.fix_revid`.
    pub fn fix_revid(&self, raw: &str) -> Option<RevisionId> {
        if raw == "head:" {
            return Some(self.last_revid.clone());
        }
        // A dotted revno consists of digits and dots only.
        if !raw.is_empty() && raw.chars().all(|c| c.is_ascii_digit() || c == '.') {
            // Find the revid with this revno by scanning the whole-history
            // entries. For small-to-medium branches this is fine; for very
            // large ones we could build a revno→revid index at graph time.
            for e in &self.whole.entries {
                if e.revno == raw {
                    return Some(e.revid.clone());
                }
            }
            return None;
        }
        // Otherwise treat as a raw revid.
        Some(RevisionId::from(raw.as_bytes().to_vec()))
    }

    /// Build a History. Caller must hold a read lock on the branch.
    pub fn new(branch: &dyn Branch) -> Result<Self, AppError> {
        let whole = WholeHistory::compute(branch)?;
        Self::from_whole(branch, whole)
    }

    /// Build a History reusing a pre-computed `WholeHistory`.
    pub fn from_whole(branch: &dyn Branch, whole: WholeHistory) -> Result<Self, AppError> {
        let last_revid = branch.last_revision();
        let nick = branch
            .get_config()
            .get_nickname()
            .unwrap_or_else(|_| "<unnamed>".to_string());
        let reverse_tags = branch
            .tags()
            .ok()
            .and_then(|t| t.get_reverse_tag_dict().ok())
            .unwrap_or_default();
        let branch_tags: HashMap<RevisionId, Vec<String>> = reverse_tags
            .into_iter()
            .map(|(rid, tags)| {
                let mut v: Vec<String> = tags.into_iter().collect();
                v.sort();
                (rid, v)
            })
            .collect();
        Ok(History {
            last_revid,
            nick,
            whole,
            branch_tags,
        })
    }

    pub fn has_revisions(&self) -> bool {
        !self.last_revid.is_null()
    }

    /// Return the full merge-sorted list of revisions reachable from
    /// `start`, in the same order as `whole.entries` (topological from
    /// the branch tip down) but restricted to the ancestors of `start`.
    /// Each entry carries `merge_depth`, so a consumer that wants to
    /// render a merge-graph indentation can read it off.
    pub fn merge_sorted_from(&self, start: &RevisionId) -> Vec<RevInfo> {
        let Some(&start_idx) = self.whole.index.get(start) else {
            return Vec::new();
        };

        // Walk the DAG from `start`, collecting all ancestors (not
        // just the mainline). We iterate by BFS over whole.index so
        // each revision is visited once.
        let mut reachable = std::collections::HashSet::new();
        let mut queue = std::collections::VecDeque::new();
        queue.push_back(start.clone());
        while let Some(rid) = queue.pop_front() {
            if !reachable.insert(rid.clone()) {
                continue;
            }
            if let Some(&i) = self.whole.index.get(&rid) {
                for p in &self.whole.entries[i].parents {
                    if !reachable.contains(p) {
                        queue.push_back(p.clone());
                    }
                }
            }
        }

        // Emit entries in whole.entries order (which is merge-sort
        // order from the branch tip), starting at start_idx — anything
        // before `start_idx` is a descendant of `start` and should be
        // skipped.
        self.whole.entries[start_idx..]
            .iter()
            .filter(|e| reachable.contains(&e.revid))
            .cloned()
            .collect()
    }

    /// Yield revisions along the mainline starting at `start`, walking
    /// first-parent pointers. Matches `get_revids_from(None, start)`.
    pub fn mainline_from(&self, start: &RevisionId) -> Vec<RevisionId> {
        let mut out = Vec::new();
        let mut cur = start.clone();
        while !cur.is_null() {
            out.push(cur.clone());
            let idx = match self.whole.index.get(&cur) {
                Some(&i) => i,
                None => break,
            };
            let parents = &self.whole.entries[idx].parents;
            if parents.is_empty() {
                break;
            }
            cur = parents[0].clone();
        }
        out
    }

    /// Compute the per-file change list between `revid` and its first
    /// parent, using breezy's `InterTree.compare()`. For root commits the
    /// source tree is the null tree, so everything shows up as added.
    pub fn get_file_changes(
        &self,
        branch: &dyn Branch,
        revid: &RevisionId,
    ) -> Result<Vec<FileChange>, AppError> {
        let parents = self
            .whole
            .index
            .get(revid)
            .map(|&i| self.whole.entries[i].parents.clone())
            .unwrap_or_default();
        let base = parents.first().cloned().unwrap_or_else(RevisionId::null);
        self.file_changes_between(branch, &base, revid)
    }

    /// Compute the per-file change list between two arbitrary revisions.
    /// Used for the `?compare_revid=…` mode on the revision page.
    pub fn file_changes_between(
        &self,
        branch: &dyn Branch,
        base: &RevisionId,
        new: &RevisionId,
    ) -> Result<Vec<FileChange>, AppError> {
        use breezyshim::intertree;
        let repo = branch.repository();
        let old_tree = repo.revision_tree(base)?;
        let new_tree = repo.revision_tree(new)?;
        let inter = intertree::get(&old_tree, &new_tree);
        let delta = inter.compare();

        let mut out = Vec::new();
        let path_of = |c: &breezyshim::tree::TreeChange, prefer_new: bool| -> String {
            let (old, new) = (&c.path.0, &c.path.1);
            let chosen = if prefer_new {
                new.as_ref().or(old.as_ref())
            } else {
                old.as_ref().or(new.as_ref())
            };
            chosen
                .map(|p| p.to_string_lossy().into_owned())
                .unwrap_or_default()
        };

        for c in &delta.added {
            out.push(FileChange {
                kind: FileChangeKind::Added,
                path: path_of(c, true),
                old_path: None,
            });
        }
        for c in &delta.removed {
            out.push(FileChange {
                kind: FileChangeKind::Removed,
                path: path_of(c, false),
                old_path: None,
            });
        }
        for c in &delta.modified {
            out.push(FileChange {
                kind: FileChangeKind::Modified,
                path: path_of(c, true),
                old_path: None,
            });
        }
        for c in &delta.renamed {
            out.push(FileChange {
                kind: FileChangeKind::Renamed,
                path: path_of(c, true),
                old_path: Some(path_of(c, false)),
            });
        }
        for c in &delta.copied {
            out.push(FileChange {
                kind: FileChangeKind::Copied,
                path: path_of(c, true),
                old_path: Some(path_of(c, false)),
            });
        }
        for c in &delta.kind_changed {
            out.push(FileChange {
                kind: FileChangeKind::KindChanged,
                path: path_of(c, true),
                old_path: None,
            });
        }
        Ok(out)
    }

    /// Fetch revision objects for the given revids and produce display
    /// `Change` records. Ghost / null entries are skipped.
    pub fn get_changes(
        &self,
        branch: &dyn Branch,
        revids: &[RevisionId],
    ) -> Result<Vec<Change>, AppError> {
        let repo = branch.repository();
        let non_null: Vec<RevisionId> = revids.iter().filter(|r| !r.is_null()).cloned().collect();
        let mut out = Vec::with_capacity(non_null.len());
        for revid in non_null {
            let rev = repo.get_revision(&revid)?;
            let (message, short_message) = clean_message(&rev.message);
            let parents: Vec<(RevisionId, String)> = rev
                .parent_ids
                .iter()
                .map(|p| (p.clone(), self.whole.get_revno(p)))
                .collect();
            let tags = self.branch_tags.get(&revid).cloned().unwrap_or_default();
            // Extract bug URLs from the `bugs` revision property.
            // Each line is `<url> <status>`; we take the URL and
            // drop anything empty.
            let bugs: Vec<String> = rev
                .properties
                .get("bugs")
                .map(|raw| {
                    raw.lines()
                        .filter_map(|line| line.split_whitespace().next().map(String::from))
                        .filter(|s| !s.is_empty())
                        .collect()
                })
                .unwrap_or_default();
            out.push(Change {
                revid: rev.revision_id,
                revno: self.whole.get_revno(&revid),
                committer: rev.committer,
                timestamp: rev.timestamp,
                timezone: rev.timezone,
                message,
                short_message,
                parents,
                tags,
                bugs,
            });
        }
        Ok(out)
    }
}

/// Lightly reflow / normalize a commit message and produce a short form,
/// mirroring `history.clean_message`.
fn clean_message(message: &str) -> (String, String) {
    let trimmed = message.trim_start();
    let lines: Vec<&str> = trimmed.lines().collect();
    if lines.is_empty() {
        return (String::new(), String::new());
    }
    let first = lines[0];
    let short = if first.chars().count() > 60 {
        let mut s: String = first.chars().take(60).collect();
        s.push_str("...");
        s
    } else {
        first.to_string()
    };
    (trimmed.to_string(), short)
}
