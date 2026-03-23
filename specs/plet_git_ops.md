# plet_git_ops.py (GTO)

> Status: draft

## 1. Purpose (GTO_PUR)

Each phase of an iteration produces incremental commits for crash recovery (IMP_17). At phase end, these must be squashed into a single clean commit, with the pre-squash history preserved via an audit tag. Agents doing this by hand produced inconsistent commit messages, forgot audit tags, misidentified branch points, and failed to log tag/commit metadata to progress.md. This script makes the tag→squash workflow deterministic.

These commands are called by the orchestrator during phase transitions — they need orchestrator context (branch points, tag naming, session state) and are not called directly by subagents.

**Phase-end workflow (where GTO fits):**

```
Subagent finishes phase
  │
  ▼
audit-tag ── preserves incremental history as tag
  │
  ▼
squash ── git reset --soft to merge-base, single plet-convention commit
  │
  ▼
rebase ── replay onto workstream tip (orchestrator, not GTO)
  │
  ▼
fast-forward merge ── linear history on workstream (orchestrator, not GTO)
  │
  ▼
worktree-remove ── clean up working directory (GTI)
```

GTO owns the audit-tag and squash steps. Rebase, merge, and worktree cleanup are orchestrator and GTI responsibilities. If verify made no commits, the orchestrator skips the entire audit-tag → squash sequence.

**Responsibility boundary:** GTO is a pure git tool — it does git operations and returns results (tag names, commit hashes, squashed counts). It does NOT write to progress.md or trace files. The **orchestrator** is responsible for logging GTO results: calling `plet_entries.py add-progress` with the tag/squash metadata and `plet_trace.py append-event` for the lifecycle record. GTO returns the data; the orchestrator logs it.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_PUR_1 | **Git history is never lost.** Audit tags preserve the full incremental commit history before squash. Even after squash, the pre-squash commits are recoverable via the audit tag (or via reflog if tags are cleaned up). | P0 |
| GTO_PUR_2 | Deterministic squash workflow. Agents computing merge-base, constructing commit messages, and creating tags freehand drift on format and sequencing. This script makes every step canonical. | P0 |
| GTO_PUR_3 | Audit tag lifecycle management. Tags are always created before squash. Optionally deleted after squash if `cleanupTagsAutomatically` is true (commit hash logged for recovery). | P0 |

## 2. Agent Personas (GTO_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GTO_AGT_1 | orchestrator | after implement phase completes | `audit-tag`, then `squash` |
| GTO_AGT_2 | orchestrator | after verify phase completes | `audit-tag`, then `squash` (skipped if no commits during verify) |
| GTO_AGT_3 | orchestrator | after post-rebase re-squash (rebase conflict resolution produced new commits) | `audit-tag`, then `squash` |
| GTO_AGT_4 | human | manual cleanup / debugging | both commands |

## 3. Commands

Command abbreviations: `ATG` (audit-tag), `SQH` (squash).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |
| `--dry-run` | both commands | Preview what would be done without modifying git state. |

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 audit-tag (ATG)

#### Justification (GTO_ATG_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_JUS_1 | Why: preserves the full incremental commit history before squash. Without the tag, the pre-squash commits become unreachable after `git reset --soft` and are eventually garbage-collected. The tag is the safety net for GTO_PUR_1. | P0 |
| GTO_ATG_JUS_2 | When: called by the orchestrator immediately before `squash`. Always — even if `cleanupTagsAutomatically` is true (the tag is created, then squash runs, then the tag is deleted with the commit hash logged). | P0 |
| GTO_ATG_JUS_3 | Deprecation signal: only if git's reflog is deemed sufficient and audit tags add no value. Unlikely — reflogs expire, tags persist. | P1 |

#### Definition (GTO_ATG_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_CMD_1 | Usage: `plet_git_ops.py audit-tag <global_state_json> <iter_state_json> --phase implement|verify [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (creates git tag), idempotent (re-tagging same commit with same name succeeds or can use `--force`)

**Concurrency:** safe — tags are repo-global, no branch-level conflict

#### Inputs (GTO_ATG_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_INP_1 | `global_state_json` — path to `plet/state.json`. Loaded via `util_state.load_and_validate_global_state()`. Provides `projectId`, `loopSessionCount`. | P0 |
| GTO_ATG_INP_2 | `iter_state_json` — path to per-iteration state file (e.g., `plet/state/ID_001.json`). Loaded via `util_state.load_and_validate_iter_state_json()`. Provides `iterationId`, `attempts`. | P0 |
| GTO_ATG_INP_3 | `--phase` — `implement` or `verify`. Required because lifecycle may be mid-transition when this is called. Attempt number derived from `iter_state_json.attempts[phase]`. | P0 |

#### Outputs (GTO_ATG_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_OUT_1 | Text mode: `OK — created audit tag {tag_name} at {commit_hash}` to stdout, exit 0 | P0 |
| GTO_ATG_OUT_2 | JSON mode: `{"status":"ok", "command":"audit-tag", "tagName":"...", "commitHash":"...", "iterationId":"...", "phase":"...", "attempt":N, ...}` | P0 |
| GTO_ATG_OUT_3 | Dry-run: `DRY RUN — would create audit tag {tag_name} at {commit_hash}`, exit 0 | P0 |
| GTO_ATG_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (GTO_ATG_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_PRE_1 | All required args present: `global_state_json`, `iter_state_json`, `--phase` | P0 |
| GTO_ATG_PRE_2 | `global_state_json` passes `util_state.load_and_validate_global_state()` | P0 |
| GTO_ATG_PRE_3 | `iter_state_json` passes `util_state.load_and_validate_iter_state_json()` | P0 |
| GTO_ATG_PRE_4 | `--phase` is `implement` or `verify` | P0 |
| GTO_ATG_PRE_5 | `iter_state_json.attempts[phase]` is a positive integer (> 0 — phase has been attempted) | P0 |
| GTO_ATG_PRE_6 | Current directory is inside a git repository | P0 |
| GTO_ATG_PRE_7 | HEAD points to a valid commit (something to tag) | P0 |

#### Postconditions (GTO_ATG_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_PST_1 | Tag `plet/{projectId}/loop{N}/audit/{iter_id}/{phase}-{attempt}` exists pointing to HEAD | P0 |
| GTO_ATG_PST_2 | Tag points to the same commit as HEAD at time of creation | P0 |

#### Behaviors (GTO_ATG_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_BHV_1 | Reads `projectId` and `loopSessionCount` from state.json, `iterationId` and `attempts` from iter_state_json to derive tag name and attempt number | P0 |
| GTO_ATG_BHV_2 | Tag name convention: `plet/{projectId}/loop{N}/audit/{iter_id}/{phase}-{attempt}`. The `/` separators allow GUI tools to filter hierarchically. | P0 |
| GTO_ATG_BHV_3 | Creates tag at HEAD: `git tag {tag_name}`. If tag already exists (re-run), uses `git tag -f {tag_name}` to update it. Logs a warning to stderr: `Warning: tag {name} already existed at {old_hash}, updated to {new_hash}`. If old and new hashes differ, something unexpected happened — the orchestrator should log this to progress and trace. | P0 |
| GTO_ATG_BHV_4 | Captures the commit hash (short, 7 chars) from HEAD for output and logging. | P0 |

---

### 3.2 squash (SQH)

#### Justification (GTO_SQH_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_JUS_1 | Why: squashes all incremental commits on an iteration branch into a single clean commit per phase. Keeps the loop workstream history readable — one commit per phase per iteration. Without this, the workstream accumulates dozens of "WIP", "fix test", "red step" commits per iteration. | P0 |
| GTO_SQH_JUS_2 | When: called by the orchestrator after `audit-tag`, at the end of each implement or verify phase. If no commits were made during the phase (e.g., verify with no fix-in-place), squash is skipped by the orchestrator (not by this script — this script errors if there's nothing to squash). | P0 |
| GTO_SQH_JUS_3 | Deprecation signal: only if plet moves to a non-squash workflow (e.g., keeping all incremental commits). | P1 |

#### Definition (GTO_SQH_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_CMD_1 | Usage: `plet_git_ops.py squash <global_state_json> <iter_state_json> --phase implement|verify [--cleanup-tag] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (rewrites git history on the branch), not idempotent (running twice on an already-squashed branch errors — merge-base equals HEAD)

**Concurrency:** not safe — must not run while a subagent is committing to the same branch

#### Inputs (GTO_SQH_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_INP_1 | `global_state_json` — path to `plet/state.json`. Loaded via `util_state.load_and_validate_global_state()`. Provides `projectId`, `loopSessionCount`. | P0 |
| GTO_SQH_INP_2 | `iter_state_json` — path to per-iteration state file (e.g., `plet/state/ID_001.json`). Loaded via `util_state.load_and_validate_iter_state_json()`. Provides `iterationId`, `title`, `attempts`, `cleanupTagsAutomatically`. | P0 |
| GTO_SQH_INP_3 | `--phase` — `implement` or `verify`. Attempt number derived from `iter_state_json.attempts[phase]`. | P0 |
| GTO_SQH_INP_4 | `--cleanup-tag` — (optional flag) override: force-delete the audit tag after squash regardless of `cleanupTagsAutomatically`. If absent, reads `cleanupTagsAutomatically` from `iter_state_json`. | P1 |

#### Outputs (GTO_SQH_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_OUT_1 | Text mode: `OK — squashed to: plet: [{iter_id}] {phase}-{attempt} - {title} ({commit_hash})` to stdout, exit 0 | P0 |
| GTO_SQH_OUT_2 | JSON mode: `{"status":"ok", "command":"squash", "commitMessage":"...", "commitHash":"...", "squashedCount":N, "tagCleaned":bool, "tagName":"...", "preSquashHash":"...", ...}` | P0 |
| GTO_SQH_OUT_3 | Dry-run: `DRY RUN — would squash N commits to: plet: [{iter_id}] ...`, exit 0 | P0 |
| GTO_SQH_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (GTO_SQH_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_PRE_1 | All required args present: `global_state_json`, `iter_state_json`, `--phase` | P0 |
| GTO_SQH_PRE_2 | `global_state_json` passes `util_state.load_and_validate_global_state()` | P0 |
| GTO_SQH_PRE_3 | `iter_state_json` passes `util_state.load_and_validate_iter_state_json()` | P0 |
| GTO_SQH_PRE_4 | `--phase` is `implement` or `verify` | P0 |
| GTO_SQH_PRE_5 | `iter_state_json.attempts[phase]` is a positive integer (> 0) | P0 |
| GTO_SQH_PRE_6 | Current directory is inside a git repository | P0 |
| GTO_SQH_PRE_7 | HEAD is ahead of the merge-base with the workstream (there are commits to squash). Error if HEAD equals merge-base (nothing to squash). | P0 |
| GTO_SQH_PRE_8 | Working tree is clean (no uncommitted changes). Squashing with dirty state risks losing work. | P0 |

#### Postconditions (GTO_SQH_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_PST_1 | Branch has exactly one commit ahead of the workstream merge-base | P0 |
| GTO_SQH_PST_2 | Commit message matches convention: `plet: [{iter_id}] {phase}-{attempt} - {title}` | P0 |
| GTO_SQH_PST_3 | All file changes from the squashed commits are preserved in the single commit | P0 |
| GTO_SQH_PST_4 | If `--cleanup-tag`, the audit tag for this phase/attempt is deleted and the pre-squash commit hash is included in output for logging | P0 |

#### Behaviors (GTO_SQH_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_SQH_BHV_1 | Derives the workstream branch name from state.json: `plet/{projectId}/loop{N}/workstream`. | P0 |
| GTO_SQH_BHV_2 | Computes merge-base: `git merge-base HEAD {workstream}`. This is the correct squash target regardless of attempt number — finds where the iteration branch diverged from the workstream. | P0 |
| GTO_SQH_BHV_3 | Counts commits to squash: `git rev-list --count {merge_base}..HEAD`. Reports in output. | P0 |
| GTO_SQH_BHV_4 | Squash: `git reset --soft {merge_base}` then `git commit -m "plet: [{iter_id}] {phase}-{attempt} - {title}"`. All staged changes from the incremental commits become one commit. | P0 |
| GTO_SQH_BHV_5 | Commit message convention: `plet: [{iter_id}] {phase}-{attempt} - {title}`. No body — the commit is a squash; the incremental history is in the audit tag. | P0 |
| GTO_SQH_BHV_6 | Tag cleanup: if `--cleanup-tag` is passed OR `iter_state_json.cleanupTagsAutomatically` is true, derives audit tag name, deletes it with `git tag -d {tag}`, includes the pre-squash commit hash in output. The orchestrator logs this to progress.md for recovery. `--cleanup-tag` is a force-override; without it, the script reads the per-iteration state. | P0 |
| GTO_SQH_BHV_8 | Reads `title` from `iter_state_json.title` for the commit message. No `--title` flag needed — single source of truth. | P0 |
| GTO_SQH_BHV_7 | All git operations via `subprocess.run()` with explicit args per UNV_NFR_9 (no shell=True). | P0 |

---

## 4. Edge Cases (GTO_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_EDG_1 | Nothing to squash (HEAD equals merge-base) — error. Orchestrator should skip squash when verify made no commits. | P0 |
| GTO_EDG_2 | Dirty working tree on squash — error. Uncommitted changes would be silently included in the squash commit. | P0 |
| GTO_EDG_3 | Audit tag already exists — `audit-tag` uses `git tag -f` to update (idempotent). Handles re-runs after crash. | P0 |
| GTO_EDG_4 | `--cleanup-tag` but tag doesn't exist — warning, not error. Tag may have been cleaned up in a previous run. | P0 |
| GTO_EDG_5 | Workstream branch doesn't exist — error from merge-base. Pass through git error with context. | P0 |
| GTO_EDG_6 | Not inside a git repo — error before any git operations. | P0 |
| GTO_EDG_7 | state.json fails `util_state.load_and_validate_global_state()` — error with specific field/issue. | P0 |
| GTO_EDG_8 | `--pretty` without `--output json` — error. | P0 |
| GTO_EDG_9 | `--fields` without `--output json` — error. | P0 |
| GTO_EDG_10 | Duplicate flags — error via `parse_kwargs`. | P0 |
| GTO_EDG_11 | Multiple squashes on same branch (re-run after successful squash) — HEAD equals merge-base, caught by EDG_1. | P0 |

## 5. Error Handling (GTO_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| GTO_ERR_2 | Invalid `--iter-id` → `Error: --iter-id '{value}' does not match expected pattern ID_N+` | P0 |
| GTO_ERR_3 | Invalid `--phase` → `Error: invalid --phase '{value}' (valid: implement, verify)` | P0 |
| GTO_ERR_4 | Invalid `--attempt` → `Error: --attempt must be a positive integer, got '{value}'` | P0 |
| GTO_ERR_5 | state.json validation failure → error from `util_state` or `util_state` | P0 |
| GTO_ERR_6 | Not a git repo → `Error: not inside a git repository` | P0 |
| GTO_ERR_7 | Nothing to squash → `Error: nothing to squash — HEAD equals merge-base with {workstream}. Orchestrator should skip squash when no commits were made.` | P0 |
| GTO_ERR_8 | Dirty working tree → `Error: working tree is dirty — commit or stash changes before squashing` | P0 |
| GTO_ERR_9 | Git command failed → `Error: git command failed: {stderr}` | P0 |
| GTO_ERR_10 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| GTO_ERR_11 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| GTO_ERR_12 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| GTO_ERR_13 | `global_state_json` is a directory → `Error: expected a file, got directory: {path}` (UNV_ERR_5) | P0 |

## 6. Formats (GTO_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_FMT_1 | Reads `plet/state.json` via `util_state` for `projectId`, `loopSessionCount`. Reads `plet/state/{id}.json` via `util_state` for `iterationId`, `title`, `attempts`, `cleanupTagsAutomatically`. | P0 |
| GTO_FMT_2 | Audit tag convention: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` | P0 |
| GTO_FMT_3 | Squash commit message convention: `plet: [{iteration_id}] {phase}-{attempt} - {title}` | P0 |

## 7. Agent Flows (GTO_AFL)

### GTO_AFL_1: End of implement phase (normal completion)

1. Impl subagent finishes, sets lifecycle to `verifying`
2. Orchestrator runs: `plet_git_ops.py audit-tag plet/state.json plet/state/ID_001.json --phase implement`
3. Tag created: `plet/LOGA/loop1/audit/ID_001/implement-1` at current HEAD
4. Orchestrator runs: `plet_git_ops.py squash plet/state.json plet/state/ID_001.json --phase implement`
5. Branch now has one squashed commit: `plet: [ID_001] implement-1 - Project scaffolding`
6. If `cleanupTagsAutomatically`: add `--cleanup-tag` to squash, tag deleted, hash logged

### GTO_AFL_2: End of verify phase (passed, no commits)

1. Verify subagent passes all criteria, no fix-in-place work
2. Orchestrator detects no new commits since last squash (HEAD unchanged)
3. Orchestrator **skips** both audit-tag and squash (nothing to tag/squash)
4. Proceeds directly to rebase + fast-forward merge

### GTO_AFL_3: End of verify phase (fix-in-place commits)

1. Verify subagent fixed minor issues, made commits
2. Orchestrator runs audit-tag then squash (same as AFL_1 but phase=verify)
3. Branch now has two squashed commits: `implement-1` + `verify-1`

### GTO_AFL_4: Post-rebase re-squash

1. After squash, orchestrator rebases onto workstream
2. Rebase produces conflicts, agent resolves them and commits fixes
3. These post-rebase commits need squashing: orchestrator runs audit-tag + squash again
4. Result is still one commit per phase (the re-squash absorbs the conflict resolution)

## 8. Examples (GTO_EXM)

### GTO_EXM_1: Audit tag + squash cycle

```bash
# 1. Create audit tag (preserves pre-squash history)
plet_git_ops.py audit-tag plet/state.json plet/state/ID_001.json \
    --phase implement
# OK — created audit tag plet/LOGA/loop1/audit/ID_001/implement-1 at abc1234

# 2. Squash incremental commits
plet_git_ops.py squash plet/state.json plet/state/ID_001.json \
    --phase implement
# OK — squashed to: plet: [ID_001] implement-1 - Project scaffolding (def5678)
```

### GTO_EXM_2: Squash with tag cleanup

```bash
plet_git_ops.py audit-tag plet/state.json plet/state/ID_001.json \
    --phase implement
# OK — created audit tag plet/LOGA/loop1/audit/ID_001/implement-1 at abc1234

plet_git_ops.py squash plet/state.json plet/state/ID_001.json \
    --phase implement --cleanup-tag
# OK — squashed to: plet: [ID_001] implement-1 - Project scaffolding (def5678)
#   Tag plet/LOGA/loop1/audit/ID_001/implement-1 deleted (was at abc1234)
```

### GTO_EXM_3: Dry-run

```bash
plet_git_ops.py squash plet/state.json plet/state/ID_001.json \
    --phase implement --dry-run
# DRY RUN — would squash 5 commits to: plet: [ID_001] implement-1 - Project scaffolding
```

### GTO_EXM_4: JSON output

```bash
plet_git_ops.py squash plet/state.json plet/state/ID_001.json \
    --phase implement --output json --pretty
# {
#   "status": "ok",
#   "command": "squash",
#   "commitMessage": "plet: [ID_001] implement-1 - Project scaffolding",
#   "commitHash": "def5678",
#   "squashedCount": 5,
#   "tagCleaned": false,
#   "preSquashHash": "abc1234",
#   ...
# }
```

## 9. Dependencies on Other Scripts (GTO_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GTO_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields` |
| GTO_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state_json` |
| GTO_DEP_3 | called by | `plet_orchestrator.py` | phase-end squash workflow |

No outgoing calls to other `plet_*.py` scripts — `plet_git_ops.py` is a leaf CLI tool. Calls `git` directly via `subprocess`.

## 10. Non-Functional Requirements (GTO_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_NFR_1 | Git operations via `subprocess.run()` with explicit args per UNV_NFR_9 (no shell=True) | P0 |
| GTO_NFR_2 | All git stderr captured and included in error messages | P0 |
| GTO_NFR_3 | Squash is fast (< 2s typical) — single reset + commit regardless of commit count | P1 |

## 11. Developer Experience (GTO_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| GTO_DXP_2 | Help text for both commands strongly recommends `--dry-run` in IMPORTANT section | P0 |
| GTO_DXP_3 | PITFALLS: squash on wrong branch, forgetting audit-tag before squash, dirty working tree | P0 |
| GTO_DXP_4 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json` | P0 |
| GTO_DXP_5 | Error messages include git's stderr when a git command fails | P0 |
| GTO_DXP_6 | Output includes commit hashes (short, 7 chars) for cross-referencing with progress.md | P0 |

## 12. Critical Test Areas (GTO_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GTO_CRT_1 | Audit tag creation | Tag not created or wrong name | Create tag, verify it exists with correct name pointing to HEAD |
| GTO_CRT_2 | Squash correctness | Wrong commits squashed or changes lost | Create 3 commits, squash, verify single commit with all changes preserved |
| GTO_CRT_3 | Commit message format | Wrong convention | Squash, verify commit message matches `plet: [ID_xxx] phase-N - title` |
| GTO_CRT_4 | Merge-base detection | Wrong squash target | Create commits after branching from workstream, verify merge-base is the branch point |
| GTO_CRT_5 | Nothing to squash | Silent no-op instead of error | Call squash when HEAD equals merge-base, verify error |
| GTO_CRT_6 | Dirty working tree | Uncommitted changes included in squash | Create uncommitted changes, verify squash errors |
| GTO_CRT_7 | --cleanup-tag | Tag not deleted or wrong tag | Squash with --cleanup-tag, verify tag gone and hash in output |
| GTO_CRT_8 | --dry-run | Dry-run modifies git state | Verify no tags created, no commits changed after dry-run |
| GTO_CRT_9 | Audit tag idempotency | Re-run fails on existing tag | Create tag twice, verify second succeeds (--force) |
| GTO_CRT_10 | Squashed count | Reports wrong number of squashed commits | Create known number of commits, verify squashedCount in JSON output |

## 13. Testing & Verification (GTO_TST)

**What to test:** See §12 Critical Test Areas (GTO_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_git_ops.py`
- Run: `python3 skills/plet/tests/test_plet_git_ops.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- **Git fixtures:** tests create temporary git repos with mock state.json, workstream branches, and incremental commits. Tests must clean up all git state after completion.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | cleanup-stashes command? | Dropped — worktrees (GTI) eliminate stashing. YAGNI. Monitor during PLAN_9. |
| 2 | Should squash handle rebase too? | No — rebase is a separate orchestrator step between squash and merge. Squash rewrites the iteration branch; rebase replays onto workstream; merge fast-forwards. Separate concerns. |
| 3 | Should audit-tag error on existing tag? | No — use `git tag -f` for idempotency. Handles re-runs after crash gracefully. |
| 4 | Who decides to skip squash when verify has no commits? | The orchestrator — it checks if HEAD moved since the last squash. This script errors on nothing-to-squash; the orchestrator decides whether to call it. |
| 5 | Should --cleanup-tag be automatic based on state? | Yes — the script reads `cleanupTagsAutomatically` from the per-iteration state file. `--cleanup-tag` flag is a force-override. Single source of truth — the state file decides, not the orchestrator's memory. |
| 6 | Should commands take explicit flags or read from state files? | Read from state files. Two positional args (`global_state_json`, `iter_state_json`) + only `--phase` as a flag. iter-id, attempt, title, cleanupTagsAutomatically all come from files. Single source of truth for 4+ scripts that need per-iteration context (GTO, GTC, GIM, GVR). |

## Open Questions

None.

## 15. Future Considerations (GTO_FUT)

| ID | Area | Description |
|----|------|-------------|
| GTO_FUT_1 | Rebase command | A `rebase` command that replays the iteration branch onto the workstream tip. Currently the orchestrator runs `git rebase` directly. If rebase logic grows complex (conflict detection, green/rebase/green invariant), it may warrant its own command. |
| GTO_FUT_2 | Merge command | A `merge` command that fast-forward merges the iteration branch onto the workstream. Currently the orchestrator handles this directly. Same rationale as FUT_1. |
| GTO_FUT_3 | Squash message customization | Allow the orchestrator to pass a custom commit body (not just title). Currently no body — the squash commit is intentionally minimal. |

## 16. FB Items Addressed

- FB_31 — Final loop commit required human prompting. Squash is now deterministic via script.
