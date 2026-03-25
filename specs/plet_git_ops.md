# plet_git_ops.py (GTO)

> Status: complete

## 1. Purpose (GTO_PUR)

Each phase of an iteration produces incremental commits for crash recovery (IMP_17). These stay on the iteration branch — no per-phase squashing. Audit tags mark phase boundaries. When the iteration reaches `complete`, all work is merge-squashed into a single commit on the workstream. Agents doing this by hand produced inconsistent commit messages, forgot audit tags, and failed to log metadata to progress.md. This script makes the workflow deterministic.

These commands are called by the orchestrator — they need orchestrator context (state files, session state) and are not called directly by subagents.

**Iteration git workflow (where GTO fits):**

```
Subagent finishes implement phase
  │
  ▼
audit-tag ── marks implement phase END on iteration branch (GTO)
  │
  ▼
Subagent finishes verify phase
  │
  ▼
audit-tag ── marks verify phase END on iteration branch (GTO)
  │
  ▼
merge-squash ── one commit per iteration on workstream (GTO)
  │              (optionally cleans up tags and branch)
  ▼
worktree-remove ── clean up working directory (GTI)
```

GTO owns audit-tag (phase boundary markers) and merge-squash (iteration → workstream). Worktree cleanup is GTI's responsibility. Audit tags are always created, even if verify made no commits (consistent audit trail).

**Responsibility boundary:** GTO is a pure git tool — it does git operations and returns results (tag names, commit hashes, squashed counts). It does NOT write to progress.md or trace files. The **orchestrator** is responsible for logging GTO results: calling `plet_entries.py add-progress` with the tag/squash metadata and `plet_trace.py append-event` for the lifecycle record. GTO returns the data; the orchestrator logs it.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_PUR_1 | **Git history is never lost.** Incremental commits stay on the iteration branch. Audit tags mark phase boundaries. The workstream gets one clean commit per iteration via merge-squash. Tags and branches optionally cleaned up after merge (controlled by per-iteration state). | P0 |
| GTO_PUR_2 | Deterministic merge workflow. Agents constructing commit messages, managing tags, and merging to workstream freehand drift on format and sequencing. This script makes every step canonical. | P0 |
| GTO_PUR_3 | Audit tag lifecycle management. Tags mark phase END on the iteration branch. Optionally deleted after merge-squash if `cleanupTagsAutomatically` is true (commit hashes logged for recovery). | P0 |

## 2. Agent Personas (GTO_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GTO_AGT_1 | orchestrator | after each phase completes | `audit-tag` (marks phase END) |
| GTO_AGT_2 | orchestrator | after iteration reaches complete | `merge-squash` (one commit to workstream) |
| GTO_AGT_4 | human | manual cleanup / debugging | both commands |

## 3. Commands

Command abbreviations: `ATG` (audit-tag), `MSQ` (merge-squash).

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
| GTO_ATG_JUS_1 | Why: marks phase boundaries on the iteration branch. Tags provide a stable reference to the exact commit where each phase ended — useful for debugging, post-run analysis, and tracing which commits belong to which phase. Unlike branch HEAD which moves, tags are fixed anchors. | P0 |
| GTO_ATG_JUS_2 | When: called by the orchestrator after each phase completes (implement or verify). Always created — even if verify made no commits (consistent audit trail). Tags persist on the iteration branch even after merge-squash to workstream. | P0 |
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
| GTO_ATG_INP_2 | `iter_state_json` — path to per-iteration state file (e.g., `plet/state/ID_001.json`). Loaded via `util_state.load_and_validate_iter_state()`. Provides `iterationId`, `attempts`. | P0 |
| GTO_ATG_INP_3 | `--phase` — `implement` or `verify`. Required because lifecycle may be mid-transition when this is called. Attempt number derived from `iter_state_json.attempts[phase]`. | P0 |

#### Outputs (GTO_ATG_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_OUT_1 | Text mode: `OK — created audit tag {tag_name} at {commit_hash}` to stdout, exit 0 | P0 |
| GTO_ATG_OUT_2 | JSON mode: structured output (see schema below). Exit 0. `replaced` is true if tag already existed (force-updated). `previousHash` is the old commit hash when replaced, null otherwise. | P0 |
| GTO_ATG_OUT_3 | Dry-run: `DRY RUN — would create audit tag {tag_name} at {commit_hash}`, exit 0 | P0 |

**GTO_ATG JSON schema (GTO_ATG_OUT_2):**
```json
{
  "status": "ok",
  "command": "audit-tag",
  "tagName": "...",
  "commitHash": "...",
  "iterationId": "...",
  "phase": "...",
  "attempt": N,
  "replaced": bool,
  "previousHash": "... or null"
}
```
| GTO_ATG_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (GTO_ATG_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ATG_PRE_1 | All required args present: `global_state_json`, `iter_state_json`, `--phase` | P0 |
| GTO_ATG_PRE_2 | `global_state_json` passes `util_state.load_and_validate_global_state()` | P0 |
| GTO_ATG_PRE_3 | `iter_state_json` passes `util_state.load_and_validate_iter_state()` | P0 |
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

### 3.2 merge-squash (MSQ)

#### Justification (GTO_MSQ_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_JUS_1 | Why: merges all iteration work into a single clean commit on the workstream. Incremental commits stay on the iteration branch (full history preserved); the workstream gets one commit per iteration. Without this, the workstream accumulates dozens of "WIP", "fix test", "red step" commits per iteration. | P0 |
| GTO_MSQ_JUS_2 | When: called by the orchestrator after an iteration reaches `complete` lifecycle (all phases done, all criteria pass). Runs from the workstream branch, not the iteration branch. | P0 |
| GTO_MSQ_JUS_3 | Deprecation signal: only if plet moves to a non-squash workflow. | P1 |

#### Definition (GTO_MSQ_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_CMD_1 | Usage: `plet_git_ops.py merge-squash <global_state_json> <iter_state_json> [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (creates commit on workstream), not idempotent (running twice creates a duplicate commit)

**Concurrency:** not safe — single writer on workstream at a time

#### Inputs (GTO_MSQ_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_INP_1 | `global_state_json` — path to `plet/state.json`. Loaded via `util_state.load_and_validate_global_state()`. Provides `projectId`, `loopSessionCount`. | P0 |
| GTO_MSQ_INP_2 | `iter_state_json` — path to per-iteration state file. Loaded via `util_state.load_and_validate_iter_state()`. Provides `iterationId`, `title`, `cleanupTagsAutomatically`, `cleanupBranchesAutomatically`. | P0 |

#### Outputs (GTO_MSQ_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_OUT_1 | Text mode: `OK — merged to workstream: plet: [{iter_id}] - {title} ({commit_hash})` to stdout, exit 0 | P0 |
| GTO_MSQ_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| GTO_MSQ_OUT_3 | Dry-run: `DRY RUN — would merge-squash {iteration_branch} to {workstream}: plet: [{iter_id}] - {title}`, exit 0 | P0 |

**GTO_MSQ JSON schema (GTO_MSQ_OUT_2):**
```json
{
  "status": "ok",
  "command": "merge-squash",
  "commitMessage": "...",
  "commitHash": "...",
  "iterationBranch": "...",
  "workstreamBranch": "...",
  "tagsCleaned": [...],
  "branchDeleted": bool
}
```
| GTO_MSQ_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (GTO_MSQ_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_PRE_1 | All required args present: `global_state_json`, `iter_state_json` | P0 |
| GTO_MSQ_PRE_2 | `global_state_json` passes `util_state.load_and_validate_global_state()` | P0 |
| GTO_MSQ_PRE_3 | `iter_state_json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GTO_MSQ_PRE_4 | Current directory is inside a git repository | P0 |
| GTO_MSQ_PRE_5 | Currently on the workstream branch (script verifies via `git branch --show-current`) | P0 |
| GTO_MSQ_PRE_6 | Iteration branch exists (derived from state) | P0 |
| GTO_MSQ_PRE_7 | Iteration branch has commits ahead of workstream (there is work to merge). Error if branches are at the same commit. | P0 |
| GTO_MSQ_PRE_8 | Working tree is clean — `git status --porcelain` returns empty | P0 |
| GTO_MSQ_PRE_9 | Not on a detached HEAD — `git symbolic-ref HEAD` succeeds | P0 |

#### Postconditions (GTO_MSQ_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_PST_1 | Workstream has one new commit containing all iteration changes | P0 |
| GTO_MSQ_PST_2 | Commit message matches convention: `plet: [{iter_id}] - {title}` | P0 |
| GTO_MSQ_PST_3 | All file changes from the iteration branch are in the new commit | P0 |
| GTO_MSQ_PST_4 | Iteration branch is untouched (incremental commits + audit tags preserved) | P0 |
| GTO_MSQ_PST_5 | If `cleanupTagsAutomatically`, all audit tags for this iteration are deleted (hashes in output) | P0 |
| GTO_MSQ_PST_6 | If `cleanupBranchesAutomatically`, iteration branch is deleted (after tags are handled) | P0 |
| GTO_MSQ_PST_7 | Linear history on workstream — no merge commits | P0 |

#### Behaviors (GTO_MSQ_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_MSQ_BHV_1 | Derives workstream branch: `plet/{projectId}/loop{N}/workstream`. Verifies currently checked out. | P0 |
| GTO_MSQ_BHV_2 | Derives iteration branch: `plet/{projectId}/loop{N}/{iter_id}`. Verifies exists. | P0 |
| GTO_MSQ_BHV_3 | Merge-squash: `git merge --squash {iteration_branch}` then `git commit -m "plet: [{iter_id}] - {title}"`. All iteration changes become one commit on workstream. No merge commit created (linear history). | P0 |
| GTO_MSQ_BHV_4 | Reads `title` from `iter_state_json.title` for commit message. Single source of truth. | P0 |
| GTO_MSQ_BHV_5 | Commit message title: `plet: [{iter_id}] - {title}`. No phase — the iteration is the unit on workstream. Body auto-generated from iter_state: lifecycle summary (phases completed, attempt counts) and criteria summary (passed/failed/skipped counts). Example body: `Phases: implement×1, verify×1\nCriteria: 3/3 passed` | P0 |
| GTO_MSQ_BHV_6 | Tag cleanup: if `iter_state_json.cleanupTagsAutomatically` is true, finds all audit tags matching `plet/{projectId}/loop{N}/audit/{iter_id}/*`, deletes each with `git tag -d`, includes tag names and commit hashes in output. The orchestrator logs this to progress.md. | P0 |
| GTO_MSQ_BHV_7 | Branch cleanup: if `iter_state_json.cleanupBranchesAutomatically` is true, deletes the iteration branch with `git branch -D {branch}` after tag cleanup. Included in output. | P0 |
| GTO_MSQ_BHV_8 | All git operations via `subprocess.run()` with explicit args per UNV_NFR_9 (no shell=True). | P0 |

---

## 4. Edge Cases (GTO_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_EDG_1 | Nothing to merge (iteration branch at same commit as workstream) — error. Iteration had no changes. | P0 |
| GTO_EDG_2 | Dirty working tree on merge-squash — error. Uncommitted changes would be silently included. | P0 |
| GTO_EDG_3 | Audit tag already exists — `audit-tag` uses `git tag -f` to update (idempotent). Handles re-runs after crash. | P0 |
| GTO_EDG_4 | `cleanupTagsAutomatically` is true but audit tag doesn't exist — warning, not error. Tag may have been cleaned up in a previous run. | P0 |
| GTO_EDG_5 | Not on workstream branch when running merge-squash — error. Must checkout workstream first. | P0 |
| GTO_EDG_6 | Not inside a git repo — error before any git operations. | P0 |
| GTO_EDG_7 | state.json fails `util_state.load_and_validate_global_state()` — error with specific field/issue. | P0 |
| GTO_EDG_8 | `--pretty` without `--output json` — error. | P0 |
| GTO_EDG_9 | `--fields` without `--output json` — error. | P0 |
| GTO_EDG_10 | Duplicate flags — error via `parse_kwargs`. | P0 |
| GTO_EDG_11 | Re-run merge-squash after success — iteration branch unchanged, but workstream has moved. `git merge --squash` would re-apply the same changes, creating a duplicate. Detect by checking if iteration branch is an ancestor of workstream HEAD. | P0 |
| GTO_EDG_12 | Detached HEAD — error. merge-squash requires being on the workstream branch. | P0 |
| GTO_EDG_13 | `cleanupBranchesAutomatically` true but branch already deleted — warning, not error. | P0 |
| GTO_EDG_14 | `git merge --squash` encounters conflicts — error. Script aborts the merge (`git merge --abort`), reports conflicting files in output. The orchestrator decides: block, spawn resolution subagent, or alert human. Conflicts are rare by design (dependency graph prevents overlap) but indicate unexpected file overlap. | P0 |

## 5. Error Handling (GTO_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| GTO_ERR_2 | Invalid `--phase` → `Error: invalid --phase '{value}' (valid: implement, verify)` | P0 |
| GTO_ERR_3 | Global state validation failure → error from `util_state.load_and_validate_global_state()` | P0 |
| GTO_ERR_4 | Iter state validation failure → error from `util_state.load_and_validate_iter_state()` | P0 |
| GTO_ERR_5 | Not a git repo → `Error: not inside a git repository` | P0 |
| GTO_ERR_6 | Nothing to merge → `Error: iteration branch {branch} has no changes ahead of workstream` | P0 |
| GTO_ERR_7 | Dirty working tree → `Error: working tree is dirty (git status --porcelain non-empty) — commit changes before merge-squash` | P0 |
| GTO_ERR_8 | Not on workstream → `Error: must be on workstream branch {expected}, currently on {actual}` | P0 |
| GTO_ERR_15 | Iteration branch not found → `Error: iteration branch not found: {branch}` | P0 |
| GTO_ERR_16 | Duplicate merge-squash → `Error: iteration branch {branch} is already merged into workstream` | P0 |
| GTO_ERR_17 | Merge conflict → `Error: merge --squash has conflicts in {N} files: {file_list}. Merge aborted. Orchestrator must resolve or block.` | P0 |
| GTO_ERR_9 | Git command failed → `Error: git command failed: {stderr}` | P0 |
| GTO_ERR_10 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| GTO_ERR_11 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| GTO_ERR_12 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| GTO_ERR_13 | `global_state_json` is a directory → `Error: expected a file, got directory: {path}` (UNV_ERR_5) | P0 |
| GTO_ERR_14 | `iter_state_json` is a directory → `Error: expected a file, got directory: {path}` (UNV_ERR_5) | P0 |

## 6. Formats (GTO_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTO_FMT_1 | Reads `plet/state.json` via `util_state` for `projectId`, `loopSessionCount`. Reads `plet/state/{id}.json` via `util_state` for `iterationId`, `title`, `attempts`, `cleanupTagsAutomatically`. | P0 |
| GTO_FMT_2 | Audit tag convention: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` | P0 |
| GTO_FMT_3 | Workstream commit message: title line `plet: [{iteration_id}] - {title}`, body auto-generated with lifecycle summary (phases × attempts) and criteria summary (passed/failed/skipped counts). | P0 |

## 7. Agent Flows (GTO_AFL)

### GTO_AFL_1: Phase end — audit tag (implement or verify)

1. Subagent finishes phase (implement or verify)
2. Orchestrator runs: `plet_git_ops.py audit-tag plet/state.json plet/state/ID_001.json --phase implement`
3. Tag created: `plet/LOGA/loop1/audit/ID_001/implement-1` at current HEAD
4. Incremental commits stay on iteration branch (no squashing)
5. If verify: same flow with `--phase verify`. Tag always created even if verify made no commits (consistent audit trail)

### GTO_AFL_2: Iteration complete — merge-squash to workstream

1. Iteration reaches `complete` lifecycle (all phases done, all criteria pass)
2. Orchestrator checks out workstream: `git checkout plet/LOGA/loop1/workstream`
3. Orchestrator runs: `plet_git_ops.py merge-squash plet/state.json plet/state/ID_001.json`
4. One commit on workstream: `plet: [ID_001] - Project scaffolding`
5. If `cleanupTagsAutomatically`: all audit tags for ID_001 deleted, hashes logged
6. If `cleanupBranchesAutomatically`: iteration branch deleted
7. Orchestrator logs results to progress.md and trace

## 8. Examples (GTO_EXM)

### GTO_EXM_1: Full iteration lifecycle (audit-tag + merge-squash)

```bash
# During iteration: audit-tag at each phase end
plet_git_ops.py audit-tag plet/state.json plet/state/ID_001.json --phase implement
# OK — created audit tag plet/LOGA/loop1/audit/ID_001/implement-1 at abc1234

plet_git_ops.py audit-tag plet/state.json plet/state/ID_001.json --phase verify
# OK — created audit tag plet/LOGA/loop1/audit/ID_001/verify-1 at def5678

# After iteration completes: merge-squash to workstream
git checkout plet/LOGA/loop1/workstream
plet_git_ops.py merge-squash plet/state.json plet/state/ID_001.json
# OK — merged to workstream: plet: [ID_001] - Project scaffolding (ghi9012)
#   Phases: implement×1, verify×1
#   Criteria: 3/3 passed
```

### GTO_EXM_2: Merge-squash with auto cleanup (both flags true)

```bash
git checkout plet/LOGA/loop1/workstream
plet_git_ops.py merge-squash plet/state.json plet/state/ID_001.json
# OK — merged to workstream: plet: [ID_001] - Project scaffolding (ghi9012)
#   Tag plet/LOGA/loop1/audit/ID_001/implement-1 deleted (was at abc1234)
#   Tag plet/LOGA/loop1/audit/ID_001/verify-1 deleted (was at def5678)
#   Branch plet/LOGA/loop1/ID_001 deleted
```

### GTO_EXM_3: Dry-run merge-squash

```bash
plet_git_ops.py merge-squash plet/state.json plet/state/ID_001.json --dry-run
# DRY RUN — would merge-squash plet/LOGA/loop1/ID_001 to workstream: plet: [ID_001] - Project scaffolding
```

### GTO_EXM_4: JSON output

```bash
plet_git_ops.py merge-squash plet/state.json plet/state/ID_001.json --output json --pretty
# {
#   "status": "ok",
#   "command": "merge-squash",
#   "commitMessage": "plet: [ID_001] - Project scaffolding",
#   "commitHash": "ghi9012",
#   "iterationBranch": "plet/LOGA/loop1/ID_001",
#   "workstreamBranch": "plet/LOGA/loop1/workstream",
#   "tagsCleaned": [],
#   "branchDeleted": false,
#   ...
# }
```

## 9. Dependencies on Other Scripts (GTO_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GTO_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields` |
| GTO_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
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
| GTO_DXP_3 | PITFALLS: running merge-squash from iteration branch instead of workstream, forgetting audit-tag before merge-squash, dirty working tree, merge-squash after branch already deleted | P0 |
| GTO_DXP_4 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json` | P0 |
| GTO_DXP_5 | Error messages include git's stderr when a git command fails | P0 |
| GTO_DXP_6 | Output includes commit hashes (short, 7 chars) for cross-referencing with progress.md | P0 |

## 12. Critical Test Areas (GTO_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GTO_CRT_1 | Audit tag creation | Tag not created or wrong name | Create tag, verify it exists with correct name pointing to HEAD |
| GTO_CRT_2 | Merge-squash correctness | Changes lost or wrong files | Create commits on iteration branch, merge-squash to workstream, verify all changes present |
| GTO_CRT_3 | Commit message format | Wrong convention | Merge-squash, verify message matches `plet: [ID_xxx] - title` (no phase) |
| GTO_CRT_4 | Must be on workstream | Runs from wrong branch | Call merge-squash from iteration branch, verify error |
| GTO_CRT_5 | Nothing to merge | Silent no-op | Call merge-squash when branches at same commit, verify error |
| GTO_CRT_6 | Dirty working tree | Uncommitted changes included | Create uncommitted changes on workstream, verify merge-squash errors |
| GTO_CRT_7 | cleanupTagsAutomatically | Tags not deleted | Merge-squash with cleanupTagsAutomatically=true, verify all iteration tags gone |
| GTO_CRT_8 | cleanupBranchesAutomatically | Branch not deleted | Merge-squash with cleanupBranchesAutomatically=true, verify branch gone |
| GTO_CRT_9 | --dry-run | Dry-run modifies git state | Verify no commits, no tags deleted, no branches deleted after dry-run |
| GTO_CRT_10 | Audit tag idempotency | Re-run fails on existing tag | Create tag twice, verify second succeeds (--force) |
| GTO_CRT_11 | Duplicate merge-squash | Re-run creates duplicate commit | Merge-squash twice, verify second errors (branch already ancestor of workstream) |

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
| 2 | Per-phase squash or per-iteration? | Per-iteration. One `git merge --squash` at iteration completion. No per-phase squashing on the iteration branch. Incremental commits + audit tags preserve phase history. Simpler, eliminates post-rebase re-squash. |
| 3 | Should audit-tag error on existing tag? | No — use `git tag -f` for idempotency. Handles re-runs after crash gracefully. |
| 4 | Rebase or merge --squash? | `git merge --squash` — stages all iteration changes as one commit on workstream. No rebase needed. Linear history maintained (no merge commits). Simpler than rebase + ff-merge; eliminates conflict resolution re-squash scenario. |
| 5 | Should tag cleanup be automatic or flag-based? | Automatic — reads `cleanupTagsAutomatically` from iter_state_json. No `--cleanup-tag` flag (YAGNI). Single source of truth — state file decides. Manual cleanup: `git tag -d` directly. |
| 6 | Should commands take explicit flags or read from state files? | Read from state files. Two positional args (`global_state_json`, `iter_state_json`) + only `--phase` as a flag. iter-id, attempt, title, cleanupTagsAutomatically all come from files. Single source of truth for 4+ scripts that need per-iteration context (GTO, GTC, GIM, GVR). |

## Open Questions

None.

## 15. Future Considerations (GTO_FUT)

| ID | Area | Description |
|----|------|-------------|
| GTO_FUT_1 | ~~Rebase command~~ | Withdrawn — merge --squash replaces rebase + ff-merge. No rebase needed in the new architecture. |
| GTO_FUT_2 | ~~Merge command~~ | Withdrawn — merge-squash command handles the merge. No separate ff-merge step. |
| GTO_FUT_3 | ~~Commit body customization~~ | Promoted to requirement — body auto-generated from iter_state (lifecycle + criteria summaries). See GTO_MSQ_BHV_5. |
| GTO_FUT_4 | ~~Merge conflict handling~~ | Promoted to EDG_14 + ERR_17. Error and abort on conflict — orchestrator decides resolution. |

## 16. FB Items Addressed

- FB_31 — Final loop commit required human prompting. Squash is now deterministic via script.
