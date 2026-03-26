# plet_git_iteration.py (GTI)

> Status: complete

## 1. Purpose (GTI_PUR)

Branch naming was inconsistent across case studies — agents invented their own conventions, used wrong project IDs, forgot session numbers, or created branches in the wrong namespace. Worktree isolation was identified in FB_13/FB_30/FB_35 as the solution to stash abuse and lost commits during parallel execution.

**Iteration lifecycle (where GTI fits):**

```
Orchestrator identifies eligible iteration
  │
  ▼
branch-name ── derive correct branch name from state.json
  │
  ▼
worktree-create ── isolated working directory + branch (or auto-resume)
  │
  ▼
Subagent works in worktree (implement → audit-tag → verify → audit-tag)
  │
  ▼
merge-squash to workstream (GTO) ── one commit per iteration
  │
  ▼
worktree-remove ── clean up on-disk directory, optionally delete branch
```

GTI owns the bookends: setup (branch-name, worktree-create) and teardown (worktree-remove). The middle steps — subagent work, audit tags, merge-squash — are other scripts' responsibilities.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_PUR_1 | **Git history is never lost.** Worktree operations manage on-disk working directories only — branches, commits, and tags are always preserved in git. `worktree-remove` cleans up the working directory; the branch and all its commits remain fully intact and reachable. Branch deletion is only performed when explicitly requested (`--delete-branch`) or when `cleanupBranchesAutomatically` is true, and only after the orchestrator has merge-squashed the work onto the workstream. Audit tags mark phase boundaries on the iteration branch. | P0 |
| GTI_PUR_2 | Branch naming convention enforcement. Agents call this instead of constructing branch names, eliminating naming drift across iterations. | P0 |
| GTI_PUR_3 | Worktree lifecycle management. Each iteration gets an isolated working directory — eliminates stashing (FB_30) and prevents cross-branch contamination (FB_35). | P0 |
| GTI_PUR_4 | Enforces the branch/tag conventions defined in `prd.md` § Branch and tag conventions. | P0 |

## 2. Agent Personas (GTI_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GTI_AGT_1 | orchestrator | before spawning implement subagent | `branch-name`, `worktree-create` |
| GTI_AGT_2 | orchestrator | after iteration completes or fails | `worktree-remove` |
| GTI_AGT_3 | orchestrator | session cleanup (orphaned worktrees) | `worktree-remove` |
| GTI_AGT_4 | implement/verify subagent | orientation (which branch am I on?) | `branch-name` (read-only, verify context) |
| GTI_AGT_5 | human | debugging / manual setup | all commands |
| GTI_AGT_6 | external GUI / monitoring tool | display branch/worktree status | may call `branch-name` for display, otherwise reads git state directly |

## 3. Commands

Command abbreviations: `BRN` (branch-name), `WTC` (worktree-create), `WTR` (worktree-remove).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |
| `--dry-run` | `worktree-create`, `worktree-remove` only | Preview what would be done without modifying git state. NOT available on `branch-name` (read-only). |

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 branch-name (BRN)

#### Justification (GTI_BRN_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_JUS_1 | Why: generates correct branch names from project context. Agents constructing branch names freehand produce inconsistent naming — wrong project IDs, missing session numbers, wrong separators. This command makes naming deterministic. | P0 |
| GTI_BRN_JUS_2 | When: called by the orchestrator before creating branches/worktrees, and by subagents to verify they're on the correct branch. Also useful for debugging and scripting. | P0 |
| GTI_BRN_JUS_3 | Deprecation signal: only if plet's branch naming convention changes to something that doesn't need computed names. | P1 |

#### Definition (GTI_BRN_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_CMD_1 | Usage: `plet_git_iteration.py branch-name [<plet_dir>] [--iter-id ID_xxx] [--type iteration] [--output json [--pretty] [--fields f1,f2]]` where `--type` is `iteration` (default), `workstream`, `plan`, or `refine` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes, no git operations)

**Concurrency:** safe — read-only

#### Inputs (GTI_BRN_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. Derives `state.json` path internally as `{plet_dir}/state.json`. Loaded and fully validated via `util_state.load_and_validate_global_state()`. Returns validated fields including `projectId`, `loopSessionCount`, `refineSessionCount`. | P0 |
| GTI_BRN_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`). Required for `--type iteration`. | P0 |
| GTI_BRN_INP_3 | `--type` — branch type: `iteration` (default), `workstream`, `plan`, or `refine`. Determines the pattern and which session counter to read. | P0 |

#### Outputs (GTI_BRN_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_OUT_1 | Text mode: prints the branch name to stdout (bare, no prefix — suitable for `$(...)` capture). Exit 0. | P0 |
| GTI_BRN_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| GTI_BRN_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

**GTI_BRN JSON schema (GTI_BRN_OUT_2):**
```json
{
  "status": "ok",
  "command": "branch-name",
  "branchName": "plet/LOGA/loop1/ID_001",
  "type": "iteration",
  "projectId": "LOGA",
  "sessionNum": 1
}
```

#### Preconditions (GTI_BRN_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_PRE_1 | All required args present: `--iter-id` (when type is iteration) | P0 |
| GTI_BRN_PRE_2 | `plet_dir` exists and is a directory (or default `plet/` exists) | P0 |
| GTI_BRN_PRE_3 | `{plet_dir}/state.json` passes `util_state.load_and_validate_global_state()` (full global state validation) | P0 |
| GTI_BRN_PRE_4 | `{plet_dir}/state.json` contains `projectId` (string, matches `[A-Z][A-Z0-9]{2,5}`) | P0 |
| GTI_BRN_PRE_5 | `{plet_dir}/state.json` contains the session counter for the requested type: `loopSessionCount` for iteration/workstream, `refineSessionCount` for refine. Plan always uses 1 (no counter in state.json). | P0 |
| GTI_BRN_PRE_6 | `--iter-id` matches pattern `ID_N+` when provided | P0 |
| GTI_BRN_PRE_7 | `--type` is `iteration`, `workstream`, `plan`, or `refine` | P0 |

#### Postconditions (GTI_BRN_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_PST_1 | No git state modified (read-only) | P0 |
| GTI_BRN_PST_2 | Output matches the branch convention in `prd.md` § Branch and tag conventions | P0 |

#### Behaviors (GTI_BRN_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_BRN_BHV_1 | Reads `projectId` and session count from `state.json`. Does not modify the file. | P0 |
| GTI_BRN_BHV_2 | `--type iteration`: `plet/{projectId}/loop{N}/{iter_id}` where N = `loopSessionCount` | P0 |
| GTI_BRN_BHV_3 | `--type workstream`: `plet/{projectId}/loop{N}/workstream` where N = `loopSessionCount` | P0 |
| GTI_BRN_BHV_4 | `--type plan`: `plet/{projectId}/plan1/workstream` — always 1, no counter in state.json | P0 |
| GTI_BRN_BHV_5 | `--type refine`: `plet/{projectId}/refine{N}/workstream` where N = `refineSessionCount` | P0 |
| GTI_BRN_BHV_6 | Text output is bare branch name (no newline prefix, no "OK —") for easy shell capture: `BRANCH=$(plet_git_iteration.py branch-name --iter-id ID_001)` | P0 |

---

### 3.2 worktree-create (WTC)

#### Justification (GTI_WTC_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_JUS_1 | Why: creates an isolated working directory for an iteration. Without worktrees, parallel agents share one working directory, requiring stashing to switch branches. SPARK produced 42 stashes (FB_30) and lost commits during branch switching (FB_35). Worktrees eliminate both problems. | P0 |
| GTI_WTC_JUS_2 | When: called by the orchestrator before spawning an implement subagent. The worktree path is passed to the subagent as its working directory. | P0 |
| GTI_WTC_JUS_3 | Deprecation signal: if Claude Code natively supports worktree isolation for subagents (e.g., Agent tool's `isolation: "worktree"` parameter), this command may become unnecessary. | P1 |

#### Definition (GTI_WTC_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_CMD_1 | Usage: `plet_git_iteration.py worktree-create [<plet_dir>] --iter-id ID_xxx [--base BRANCH] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (creates git worktree and branch), not idempotent (errors if worktree exists), atomic (git-managed — `git worktree add` either fully succeeds or fails, edge-case cleanup via `git worktree prune`)

**Concurrency:** safe per iteration — different iterations create different worktrees. Concurrent create on same iteration is an error (worktree path collision).

#### Inputs (GTI_WTC_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. Derives `state.json` path internally as `{plet_dir}/state.json`. | P0 |
| GTI_WTC_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`) | P0 |
| GTI_WTC_INP_3 | `--base` — (optional) base branch to branch from. Default: the loop workstream branch (derived from state.json). | P1 |
| GTI_WTC_INP_4 | `--worktree-dir` — (optional) parent directory for worktrees. Default: `.plet/worktrees/`. The iteration worktree is created at `{worktree-dir}/{projectId}/{iter_id}/` — namespaced by projectId to prevent collisions when subplets share the same iteration IDs. | P1 |

#### Outputs (GTI_WTC_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_OUT_1 | Text mode: `OK — created worktree at {path} on branch {branch}` (fresh) or `OK — resumed worktree at {path} on existing branch {branch}` (resume), exit 0 | P0 |
| GTI_WTC_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| GTI_WTC_OUT_3 | Dry-run: `DRY RUN — would create worktree at {path} on branch {branch}` — no git operations, exit 0 | P0 |

**GTI_WTC JSON schema (GTI_WTC_OUT_2):**
```json
{
  "status": "ok",
  "command": "worktree-create",
  "worktreePath": "...",
  "branchName": "...",
  "baseBranch": "...",
  "iterationId": "...",
  "resumed": bool
}
```
| GTI_WTC_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (GTI_WTC_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_PRE_1 | All required args present: `--iter-id` | P0 |
| GTI_WTC_PRE_2 | `plet_dir` exists and is a directory (or default `plet/` exists). `{plet_dir}/state.json` passes `util_state.load_and_validate_global_state()` (full global state validation). | P0 |
| GTI_WTC_PRE_3 | `--iter-id` matches pattern `ID_N+` | P0 |
| GTI_WTC_PRE_4 | Worktree path does not already exist (error if it does — no silent overwrite) | P0 |
| GTI_WTC_PRE_5 | If branch already exists, auto-resume: create worktree on existing branch (no `-b`). This handles blocked→unblocked iterations where partial work is committed on the branch. If branch does NOT exist, create fresh (`-b`). | P0 |
| GTI_WTC_PRE_6 | Base branch exists (default: workstream, or `--base` if provided) | P0 |
| GTI_WTC_PRE_7 | Current directory is inside a git repository | P0 |

#### Postconditions (GTI_WTC_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_PST_1 | Worktree directory exists at `{worktree-dir}/{projectId}/{iter_id}/` | P0 |
| GTI_WTC_PST_2 | Branch `plet/{projectId}/loop{N}/{iter_id}` exists, checked out in the worktree | P0 |
| GTI_WTC_PST_3 | Branch is based on the workstream (or `--base`) commit | P0 |
| GTI_WTC_PST_4 | `git worktree list` includes the new worktree | P0 |

#### Behaviors (GTI_WTC_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTC_BHV_1 | Reads `projectId` and `loopSessionCount` from state.json to derive branch name | P0 |
| GTI_WTC_BHV_2 | Derives base branch: `plet/{projectId}/loop{N}/workstream` (or `--base` override) | P0 |
| GTI_WTC_BHV_3 | If branch does not exist (fresh): `git worktree add -b {branch} {path} {base}`. If branch already exists (resume): `git worktree add {path} {branch}`. Auto-detected — no flag needed. Handles blocked→unblocked iterations seamlessly. | P0 |
| GTI_WTC_BHV_4 | Creates the worktree parent directory if it doesn't exist | P0 |
| GTI_WTC_BHV_5 | Worktree path convention: `{worktree-dir}/{projectId}/{iter_id}/` — iteration ID as directory name for easy identification | P0 |

---

### 3.3 worktree-remove (WTR)

#### Justification (GTI_WTR_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_JUS_1 | Why: cleans up worktrees after an iteration completes, fails, or is retried. FB_32 showed orphaned worktrees from retried iterations. Without cleanup, worktrees accumulate and consume disk space. | P0 |
| GTI_WTR_JUS_2 | When: called by the orchestrator after an iteration reaches `complete`, `blocked`, or `withdrawn` lifecycle, and during session cleanup. | P0 |
| GTI_WTR_JUS_3 | Deprecation signal: same as worktree-create — if native isolation handles cleanup. | P1 |

#### Definition (GTI_WTR_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_CMD_1 | Usage: `plet_git_iteration.py worktree-remove [<plet_dir>] --iter-id ID_xxx [--delete-branch] [--worktree-dir DIR] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (removes git worktree, optionally deletes branch), not idempotent (errors if worktree doesn't exist)

**Concurrency:** safe — removing a worktree that a subagent is using would be destructive, but the orchestrator controls sequencing (only removes after the subagent has exited).

#### Inputs (GTI_WTR_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. Derives `state.json` path internally as `{plet_dir}/state.json`. | P0 |
| GTI_WTR_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`) | P0 |
| GTI_WTR_INP_3 | `--delete-branch` — (optional flag) also delete the iteration branch after removing the worktree. Default: keep the branch (it may be needed for rebase/merge). | P1 |
| GTI_WTR_INP_4 | `--worktree-dir` — (optional) parent directory for worktrees. Default: `.plet/worktrees/`. | P1 |

#### Outputs (GTI_WTR_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_OUT_1 | Text mode: `OK — removed worktree at {path}` (+ `and branch {branch}` if --delete-branch), exit 0 | P0 |
| GTI_WTR_OUT_2 | JSON mode: structured output (see schema below). Exit 0. | P0 |
| GTI_WTR_OUT_3 | Dry-run: `DRY RUN — would remove worktree at {path}` — no git operations, exit 0 | P0 |

**GTI_WTR JSON schema (GTI_WTR_OUT_2):**
```json
{
  "status": "ok",
  "command": "worktree-remove",
  "worktreePath": "...",
  "branchName": "...",
  "branchDeleted": bool
}
```
| GTI_WTR_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

#### Preconditions (GTI_WTR_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_PRE_1 | All required args present: `--iter-id` | P0 |
| GTI_WTR_PRE_2 | `plet_dir` exists and is a directory (or default `plet/` exists). `{plet_dir}/state.json` passes `util_state.load_and_validate_global_state()` (full global state validation). | P0 |
| GTI_WTR_PRE_3 | `--iter-id` matches pattern `ID_N+` | P0 |
| GTI_WTR_PRE_4 | Worktree exists at the derived path | P0 |
| GTI_WTR_PRE_5 | Current directory is inside a git repository | P0 |

#### Postconditions (GTI_WTR_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_PST_1 | Worktree directory no longer exists | P0 |
| GTI_WTR_PST_2 | `git worktree list` no longer includes the removed worktree | P0 |
| GTI_WTR_PST_3 | If `--delete-branch`, branch no longer exists. Otherwise branch is preserved. | P0 |

#### Behaviors (GTI_WTR_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_WTR_BHV_1 | Derives worktree path from state.json + iter-id: `{worktree-dir}/{projectId}/{iter_id}/` | P0 |
| GTI_WTR_BHV_2 | Removes worktree: `git worktree remove {path}` (uses `--force` if working directory has untracked files — worktree cleanup should not be blocked by build artifacts) | P0 |
| GTI_WTR_BHV_3 | If `--delete-branch`: derives branch name from state.json and deletes it with `git branch -D {branch}` after worktree removal | P0 |
| GTI_WTR_BHV_4 | Runs `git worktree prune` after removal to clean up stale worktree metadata | P1 |

---

## 4. Edge Cases (GTI_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_EDG_1 | Worktree path already exists on `worktree-create` — error (no silent overwrite, may be orphaned from a crash) | P0 |
| GTI_EDG_2 | Branch already exists on `worktree-create` — auto-resume: create worktree on existing branch without `-b`. This is the normal path for blocked→unblocked iterations. Output indicates resume vs fresh. | P0 |
| GTI_EDG_3 | Worktree doesn't exist on `worktree-remove` — error (nothing to remove) | P0 |
| GTI_EDG_4 | Base branch doesn't exist on `worktree-create` — error with specific message naming the missing branch | P0 |
| GTI_EDG_5 | `--delete-branch` on a branch that's checked out elsewhere — error from git, pass through with context | P0 |
| GTI_EDG_6 | Not inside a git repository — error before any git operations | P0 |
| GTI_EDG_7 | `state.json` fails `util_state.load_and_validate_global_state()` validation (missing fields, wrong types, invalid projectId format) — error with specific field/issue from util_state | P0 |
| GTI_EDG_9 | Worktree has uncommitted changes on `worktree-remove` — remove with `--force` (build artifacts, uncommitted scratch). The orchestrator has already committed meaningful work via squash before calling remove. | P0 |
| GTI_EDG_10 | `--pretty` without `--output json` — error | P0 |
| GTI_EDG_11 | `--fields` without `--output json` — error | P0 |
| GTI_EDG_12 | Duplicate flags — error via `parse_kwargs` | P0 |
| GTI_EDG_13 | `branch-name --type plan` always uses 1 (no counter in state.json), `--type refine` uses `refineSessionCount`, iteration/workstream use `loopSessionCount` | P0 |
| GTI_EDG_14 | `branch-name --type workstream` omits `--iter-id` (not needed for workstream) | P0 |
| GTI_EDG_15 | ~~`projectId` pattern validation~~ — subsumed by GTI_EDG_7 (`util_state.load_and_validate_global_state()` validates projectId format) |  |

## 5. Error Handling (GTI_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| GTI_ERR_2 | Invalid `--iter-id` format → `Error: --iter-id '{value}' does not match expected pattern ID_N+` | P0 |
| GTI_ERR_3 | `state.json` not found → `Error: file not found: {path}` | P0 |
| GTI_ERR_4 | `state.json` invalid JSON → `Error: invalid JSON in {path}: {parse_error}` | P0 |
| GTI_ERR_5 | `state.json` validation failure → error from `util_state.load_and_validate_global_state()` with specific field/issue (missing field, wrong type, invalid format) | P0 |
| GTI_ERR_7 | Worktree path already exists → `Error: worktree path already exists: {path}. Remove with worktree-remove first.` | P0 |
| GTI_ERR_8 | ~~Branch already exists~~ — no longer an error. Auto-resume behavior (GTI_WTC_BHV_3, GTI_EDG_2). |  |
| GTI_ERR_9 | Base branch doesn't exist → `Error: base branch not found: {branch}. Create the workstream branch first.` | P0 |
| GTI_ERR_10 | Worktree not found on remove → `Error: no worktree at {path}` | P0 |
| GTI_ERR_11 | Not a git repository → `Error: not inside a git repository` | P0 |
| GTI_ERR_12 | Invalid `--type` → `Error: invalid --type '{value}' (valid: iteration, workstream, plan, refine)` | P0 |
| GTI_ERR_13 | Git operation failed → `Error: git command failed: {stderr}` (pass through git's error with context) | P0 |
| GTI_ERR_14 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| GTI_ERR_15 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| GTI_ERR_16 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| GTI_ERR_17 | `plet_dir` is a file → `Error: expected a directory, got file: {path}` | P0 |
| GTI_ERR_18 | `plet_dir` not found → `Error: directory not found: {path}` | P0 |

## 6. Formats (GTI_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_FMT_1 | Reads `{plet_dir}/state.json` for `projectId`, `loopSessionCount`, `refineSessionCount` | P0 |
| GTI_FMT_2 | Branch naming convention per `prd.md`: `plet/{projectId}/loop{N}/{iter_id}`, `plet/{projectId}/loop{N}/workstream`, `plet/{projectId}/plan1/workstream`, `plet/{projectId}/refine{N}/workstream` | P0 |
| GTI_FMT_3 | Worktree path convention: `{worktree-dir}/{projectId}/{iter_id}/` (default worktree-dir: `.plet/worktrees/`) | P0 |

## 7. Agent Flows (GTI_AFL)

### GTI_AFL_1: Orchestrator sets up iteration for implementation

1. Orchestrator identifies ID_001 as eligible
2. `plet_git_iteration.py worktree-create --iter-id ID_001`
3. Script creates worktree at `.plet/worktrees/LOGA/ID_001/` on branch `plet/LOGA/loop1/ID_001`
4. Orchestrator passes worktree path to implement subagent as working directory
5. Subagent works in isolation

### GTI_AFL_2: Orchestrator cleans up after completion

1. Iteration ID_001 reaches `complete` lifecycle
2. Orchestrator runs merge-squash to workstream (via plet_git_ops.py)
3. `plet_git_iteration.py worktree-remove --iter-id ID_001`
4. Worktree cleaned up (branch cleanup handled by GTO merge-squash if cleanupBranchesAutomatically)

### GTI_AFL_3: Orchestrator cleans up orphaned worktrees at session start

1. New loop session starts
2. Orchestrator scans for existing worktrees (via plet_git_check.py check-session)
3. For each orphaned worktree: `plet_git_iteration.py worktree-remove --iter-id {id}`
4. Clean state for new session

### GTI_AFL_4: Subagent verifies its branch context

1. Implement subagent starts in a worktree
2. `plet_git_iteration.py branch-name --iter-id ID_001`
3. Compares output to `git branch --show-current`
4. Confirms it's on the correct branch before proceeding

## 8. Examples (GTI_EXM)

### GTI_EXM_1: Generate branch names

```bash
# Iteration branch (uses default plet/ directory)
plet_git_iteration.py branch-name --iter-id ID_001
# plet/LOGA/loop1/ID_001

# Workstream branch
plet_git_iteration.py branch-name --type workstream
# plet/LOGA/loop1/workstream

# Plan branch
plet_git_iteration.py branch-name --type plan
# plet/LOGA/plan1/workstream

# Refine branch
plet_git_iteration.py branch-name --type refine
# plet/LOGA/refine1/workstream

# JSON output for scripting
plet_git_iteration.py branch-name --iter-id ID_003 --output json
# {"status":"ok","command":"branch-name","branchName":"plet/LOGA/loop1/ID_003","type":"iteration","projectId":"LOGA","sessionNum":1,...}
```

### GTI_EXM_2: Create and remove a worktree

```bash
# Create (uses default plet/ directory)
plet_git_iteration.py worktree-create --iter-id ID_001
# OK — created worktree at .plet/worktrees/LOGA/ID_001/ on branch plet/LOGA/loop1/ID_001

# Create with explicit plet directory
plet_git_iteration.py worktree-create custom/plet --iter-id ID_001
# OK — created worktree at .plet/worktrees/LOGA/ID_001/ on branch plet/LOGA/loop1/ID_001

# Verify
ls .plet/worktrees/LOGA/ID_001/
# (project files visible in isolated worktree)

git worktree list
# /path/to/project                  abc1234 [main]
# /path/to/project/.plet/worktrees/LOGA/ID_001  def5678 [plet/LOGA/loop1/ID_001]

# Remove (keep branch for rebase/merge)
plet_git_iteration.py worktree-remove --iter-id ID_001
# OK — removed worktree at .plet/worktrees/LOGA/ID_001/

# Remove with branch deletion (after merge)
plet_git_iteration.py worktree-remove --iter-id ID_001 --delete-branch
# OK — removed worktree at .plet/worktrees/LOGA/ID_001/ and branch plet/LOGA/loop1/ID_001
```

### GTI_EXM_3: Dry-run

```bash
plet_git_iteration.py worktree-create --iter-id ID_005 --dry-run
# DRY RUN — would create worktree at .plet/worktrees/LOGA/ID_005/ on branch plet/LOGA/loop1/ID_005
```

## 9. Dependencies on Other Scripts (GTI_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GTI_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields` |
| GTI_DEP_2 | imports | `util_state` | `load_and_validate_global_state` |
| GTI_DEP_3 | called by | `plet_orchestrator.py` | iteration setup/teardown |

No outgoing calls to other `plet_*.py` scripts — `plet_git_iteration.py` is a leaf CLI tool. Calls `git` directly via `subprocess`.

## 10. Non-Functional Requirements (GTI_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_NFR_1 | Git operations via `subprocess.run()` with explicit args per UNV_NFR_9 (no shell=True) — prevents injection | P0 |
| GTI_NFR_2 | All git stderr captured and included in error messages — agents need git's error output to understand failures | P0 |
| GTI_NFR_3 | Worktree operations are fast (< 2s typical) — no long-running git operations | P1 |

## 11. Developer Experience (GTI_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTI_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| GTI_DXP_2 | Help text for mutating commands strongly recommends `--dry-run` in IMPORTANT section | P0 |
| GTI_DXP_3 | `branch-name` text output is bare (no "OK —" prefix) for shell capture: `BRANCH=$(plet_git_iteration.py branch-name ...)`. Explicit exception to UNV_CMD_15 — `branch-name` is a pure value-producing command, not a mutation confirmation. | P0 |
| GTI_DXP_4 | Each command's PITFALLS lists common git mistakes: wrong base branch, stale worktrees, branch name typos | P0 |
| GTI_DXP_5 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json`; `--dry-run` only on mutating commands | P0 |
| GTI_DXP_6 | Error messages include git's stderr when a git command fails — agents need the underlying error to diagnose issues | P0 |

## 12. Critical Test Areas (GTI_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GTI_CRT_1 | Branch name correctness | Wrong convention, wrong project ID | Generate names for all types, verify against expected patterns |
| GTI_CRT_2 | Worktree creation | Worktree not created, wrong branch | Create worktree, verify directory exists and git worktree list includes it |
| GTI_CRT_3 | Worktree removal | Worktree not removed, branch accidentally deleted | Remove worktree, verify gone from list. Test with/without --delete-branch |
| GTI_CRT_4 | Error on existing worktree | Silent overwrite | Create twice, verify second call errors |
| GTI_CRT_5 | Error on existing branch | Reuse of stale branch | Create with existing branch name, verify error |
| GTI_CRT_6 | state.json reading | Wrong field, missing field | Test with missing projectId, missing sessionCount |
| GTI_CRT_7 | --dry-run | Dry-run creates worktree | Verify no git state changes after dry-run |
| GTI_CRT_8 | Not a git repo | Crash or confusing error | Run outside git repo, verify clean error |
| GTI_CRT_9 | Orphaned worktree cleanup | Force-remove fails on dirty worktree | Create worktree with untracked files, remove, verify success |
| GTI_CRT_10 | ProjectId namespace in worktree path | Subplet worktrees collide without projectId | Create worktrees with different projectIds + same iter-id, verify paths are distinct |
| GTI_CRT_11 | Auto-resume on existing branch | Fresh create when should resume, or vice versa | Create worktree, remove worktree (keep branch), create again — verify resumed flag true and branch commits preserved |

## 13. Testing & Verification (GTI_TST)

**What to test:** See §12 Critical Test Areas (GTI_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_git_iteration.py`
- Run: `python3 skills/plet/tests/test_plet_git_iteration.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- **Git fixtures:** tests create temporary git repos (`git init` in tmpdir) with mock state.json and workstream branches. Tests must clean up all git state (worktrees, branches) after completion.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Separate `create-branch` command? | Dropped — `worktree-create` subsumes it. If bare branches are needed later, add it back. YAGNI. |
| 2 | Read state.json or take individual flags? | Read state.json — script is self-contained, derives `state.json` from `plet_dir` (default `plet/`). |
| 3 | Original 8-command scope? | Split into three scripts (GTI, GTO, GTC) by audience. See specs/NOTES.md. |
| 4 | Plan session counter? | Plan always uses 1 — plan sessions don't repeat in the current workflow. Branch is `plet/{projectId}/plan1/workstream`. No `planSessionCount` needed in state.json. If plan ever repeats, add the counter then. |
| 5 | Who validates global state.json fields? | New `util_state.py` module — `load_and_validate_global_state()` does full validation. 7+ scripts read state.json; shared function prevents duplicated validation. plet_state.py stays focused on per-iteration files. |
| 6 | Worktree path collisions with subplets? | Namespace by projectId: `{worktree-dir}/{projectId}/{iter_id}/`. Parent LOGA/ID_001 and subplet AUTH/ID_001 get distinct paths. |
| 7 | How do blocked→unblocked iterations resume? | Auto-resume: if branch already exists, `worktree-create` reuses it (`git worktree add {path} {branch}` without `-b`). No `--resume` flag — the branch's existence is the signal. Preserves all commits from the blocked attempt. |
| 8 | Function naming for state.json loading? | `load_and_validate_global_state()` (public). Internal split: `load_global_state()` (load JSON) + `validate_global_state()` (check fields). Explicit name, clean decomposition. |

## Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | ~~Should `.plet/worktrees/` be added to `.gitignore` automatically?~~ | Resolved: not GTI's job. `.plet/` should be gitignored entirely (worktrees, temp files, future caches). Preflight (`plet_session.py`) checks `.gitignore` has `.plet/` and warns if not. GTI is a leaf tool, not a project setup wizard. |
| 2 | How does the subagent know its worktree path? | The orchestrator passes it as a working directory argument to `claude -p`. Need to verify `claude -p` supports `--cwd` or equivalent. If not, the orchestrator `cd`s into the worktree before spawning. |

## 15. Future Considerations (GTI_FUT)

| ID | Area | Description |
|----|------|-------------|
| GTI_FUT_1 | `create-branch` command | Add if non-worktree workflows are needed (e.g., sequential single-branch mode). |
| GTI_FUT_2 | Worktree health check | A `worktree-status` command reporting the state of all active worktrees (branch, dirty/clean, last commit). May belong in plet_git_check.py instead. |
| GTI_FUT_3 | Native Claude Code worktree support | If Claude Code's Agent tool adds native worktree isolation, this script may become a thin wrapper or unnecessary. Monitor `isolation: "worktree"` parameter. |
| GTI_FUT_4 | Worktree path lookup | A `worktree-path` command that returns the worktree path for a given iteration ID (inverse of worktree-create). If subagents have trouble locating their worktree directory, this gives them a reliable way to query it from state.json + convention. |
| GTI_FUT_5 | Monitor auto-resume edge cases | The branch-exists = resume, branch-absent = fresh heuristic covers all known scenarios (blocked→unblocked, interrupted/crashed, verify cycle-back, refine re-open). Monitor during PLAN_9 comparison runs and future case studies for edge cases where this heuristic produces the wrong behavior — e.g., stale branches from abandoned sessions, branch name collisions from session counter bugs. |

## 16. FB Items Addressed

- FB_13 — Branch isolation via worktrees (decided, now implemented)
- FB_30 — 42 git stashes despite ban (worktrees eliminate stashing need)
- FB_32 — Orphaned worktree after retry (worktree-remove handles cleanup)
- FB_35 — Agent lost commits during implementation (worktree isolation prevents cross-branch contamination)
