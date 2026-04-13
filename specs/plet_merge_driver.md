# plet_merge_driver.py (MGD)

> Status: complete (mini-spec)

Custom git merge driver for append-only files. Resolves merge conflicts on plet runtime artifacts and trace NDJSON during merge-squash by appending new content from both sides.

## 1. Purpose (MGD_PUR)

| ID | Requirement | Priority |
|----|-------------|----------|
| MGD_PUR_1 | Resolve merge conflicts on append-only files during `git merge --squash`. Both workstream (orchestrator/gate entries) and iteration branch (subagent entries) append to the same files — default merge may conflict. | P0 |
| MGD_PUR_2 | Handles runtime artifacts (`progress.md`, `learnings.md`, `emergent.md`) and trace NDJSON (`trace/*.ndjson`). Same logic for all — append-only invariant. | P0 |
| MGD_PUR_3 | Callable standalone for debugging/testing, AND as a git merge driver (called automatically by git during merge operations). | P0 |

**Why this exists:** Worktree isolation (SF_26) means the subagent writes to `worktree_plet_dir` while the orchestrator writes to `global_plet_dir`. Both append to the same logical files on different branches. Without this driver, `merge-squash` may produce conflict markers in runtime artifacts — a bad place to fail mid-orchestrator-loop.

## 2. Configuration

**`.gitattributes` (in target project, created by session setup):**
```
plet/progress.md merge=plet-append
plet/learnings.md merge=plet-append
plet/emergent.md merge=plet-append
plet/trace/*.ndjson merge=plet-append
```

**`git config` (set by preflight or start-session):**
```
git config merge.plet-append.driver "python3 /path/to/plet_merge_driver.py %O %A %B"
git config merge.plet-append.name "plet append-only merge"
```

If the driver is not configured, git falls back to default three-way merge — which may auto-resolve (git handles append-to-end well) or conflict. The driver makes resolution deterministic.

## 3. Behavior (MGD_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| MGD_BHV_1 | **Append-only invariant check:** Verify theirs (%B) starts with base (%O) line-for-line. If theirs modified or removed base content, exit 1 (conflict — not append-only, fall back to manual resolution). | P0 |
| MGD_BHV_2 | **Extract new content:** New lines = theirs lines after the base prefix. These are the subagent's appended entries. | P0 |
| MGD_BHV_3 | **Merge:** Append new lines from theirs to ours (%A). Ours already has the workstream's appended entries. Result: base + ours-added + theirs-added. | P0 |
| MGD_BHV_4 | **Write result to %A.** Git reads %A after the driver exits. Exit 0 = success. | P0 |
| MGD_BHV_5 | **Entry ordering:** Ours entries appear before theirs entries. Within each side, entries preserve their original order. Cross-side chronological ordering is a future consideration (MGD_FUT_1). | P0 |
| MGD_BHV_6 | **Empty base:** If base is empty, all of theirs is "new." Append to ours. Handles new files that both sides created. | P0 |
| MGD_BHV_7 | **No new content from theirs:** If theirs == base (nothing appended), ours is already correct. Exit 0, no changes. | P0 |

## 4. Inputs / Outputs

**Inputs:** Three file paths (positional args):
- `%O` (base) — common ancestor
- `%A` (ours) — current branch (workstream)
- `%B` (theirs) — other branch (iteration)

**Outputs:**
- Merged result written to `%A` (in-place)
- Exit 0: merge succeeded
- Exit 1: not append-only (conflict — git shows conflict markers)

## 5. Edge Cases (MGD_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| MGD_EDG_1 | Theirs modified base content → exit 1 (conflict) | P0 |
| MGD_EDG_2 | Theirs shorter than base (content removed) → exit 1 | P0 |
| MGD_EDG_3 | All three empty → exit 0, result empty | P0 |
| MGD_EDG_4 | Large files (20+ entries each side) → works, preserves all | P0 |
| MGD_EDG_5 | Wrong number of CLI args → exit 1 with usage message | P0 |
| MGD_EDG_6 | Driver not configured in git → git falls back to default merge (may auto-resolve or conflict) | P0 |

## 6. Files Covered

| Pattern | File type | Both sides append? |
|---------|-----------|-------------------|
| `plet/progress.md` | Markdown, `###` fenced entries | Yes — orchestrator (gate results, session events) + subagent (implementation/verification progress) |
| `plet/learnings.md` | Markdown, `###` fenced entries | Yes — orchestrator (rarely) + subagent (patterns, gotchas) |
| `plet/emergent.md` | Markdown, `###` fenced entries | Mostly subagent — orchestrator rarely writes. Included for safety. |
| `plet/trace/*.ndjson` | NDJSON, one JSON object per line | Yes — `invoke.py` writes invocation event to workstream, subagent writes activity/decision events to worktree |

## 7. Testing (MGD_TST)

- File: `skills/plet/tests/test_plet_merge_driver.py`
- 53 tests: unit (direct invocation with temp files) + git integration (real `merge --squash`)
- Realistic entries for all 4 artifact types
- Conflict detection for non-append-only modifications
- Edge cases: empty files, large merges, wrong args

## 8. Future Considerations (MGD_FUT)

| ID | Area | Description |
|----|------|-------------|
| MGD_FUT_1 | **Chronological resorting.** Current merge puts ours entries before theirs. This means orchestrator entries (e.g., 10:00:05) appear before subagent entries (e.g., 10:01:30) — which happens to be chronological for most cases. But if the subagent ran for a long time and the orchestrator wrote entries after the subagent started, the merged timeline would be out of order. A future version could parse `### [timestamp]` headers (markdown) or `"timestamp"` fields (NDJSON) and re-sort all entries chronologically after merging. |
| MGD_FUT_2 | **Entry deduplication.** If the orchestrator relay approach (Option C/H from design discussion) is ever implemented — where the orchestrator extracts entries from the worktree and appends them to the workstream before merge — the driver would see duplicates. A future version could deduplicate by entry header or pletId. |
| MGD_FUT_3 | **Configurable conflict behavior.** Currently exits 1 on non-append-only files. Could accept a flag or env var to force-merge (take ours + all of theirs) even when the invariant is violated. Useful for crash recovery where files may be partially written. |

## 9. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Which files need the driver? | Runtime artifacts + trace NDJSON. Per-iteration state files don't need it — SF_28 moved lifecycle to state.json, and subagent is sole writer to per-iteration files (no conflict). |
| 2 | What about traces? | Yes — `invoke.py` writes invocation event to workstream trace, subagent writes to worktree trace. Same filename, different branches. Same append-only merge. |
| 3 | Line-based or entry-based comparison? | Line-based. Simpler, works for both markdown (multi-line entries) and NDJSON (one object per line). Entry-based parsing would be more robust but adds complexity for no current benefit. |
| 4 | What if git auto-resolves without the driver? | Often works (append-to-end). The driver makes it deterministic. If driver isn't configured, git's default merge is an acceptable fallback. |
