# plet_git_check.py (GTC)

> Status: approved

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*. A table row should be self-contained enough to verify independently, but the surrounding prose provides the understanding needed to write and review it well.

## 1. Purpose (GTC_PUR)

Git compliance checks called by gate scripts and the orchestrator at phase and session boundaries. Read-only — verifies git state without modifying it.

Case study evidence: agents used 42 git stashes despite an explicit ban (FB_30), orphaned worktrees after retries (FB_32), agents on wrong branches, merge commits in supposedly linear history, and unmerged completed iterations left behind at session end. These checks exist to catch compliance violations that prose rules failed to prevent.

**Split from:** Originally `plet_git.py` (8 commands, 4 concerns). Split into three scripts by audience — GTI (lifecycle), GTO (workflow ops), GTC (compliance checks). See `specs/NOTES.md` § "plet_git.py split into three scripts" for rationale.

**Responsibility boundary:** GTC is a read-only diagnostic tool — it checks git state and reports findings. It does NOT fix anything. The **caller** (gate script, orchestrator, or human) decides what to do with violations: block, warn, auto-fix, or escalate.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_PUR_1 | Read-only git compliance checks at two scopes: per-iteration (phase boundaries) and per-session (session boundaries). Verifies the invariants that prose rules failed to enforce in case studies. | P0 |
| GTC_PUR_2 | Two commands with different scopes and callers: `check-iteration` (called by gate scripts GIM/GVR at phase boundaries) and `check-session` (called by orchestrator at session start/end). | P0 |
| GTC_PUR_3 | Deterministic, machine-readable output. Gate scripts and the orchestrator parse the results to make blocking decisions. Human-readable text mode for manual debugging. | P0 |

## 2. Agent Personas (GTC_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GTC_AGT_1 | gate script (GIM) | pre/post implement phase boundary | `check-iteration` |
| GTC_AGT_2 | gate script (GVR) | pre/post verify phase boundary | `check-iteration` |
| GTC_AGT_3 | orchestrator | session start (preflight) | `check-session` |
| GTC_AGT_4 | orchestrator | session end (cleanup verification) | `check-session` |
| GTC_AGT_5 | orchestrator | between iterations (health check) | `check-iteration` or `check-session` |
| GTC_AGT_6 | human | manual debugging / audit | both commands |
| GTC_AGT_7 | GUI tool | dashboard health display / status polling | both commands |

## 3. Commands

Command abbreviations: `CKI` (check-iteration), `CKS` (check-session).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |

Both commands are read-only — `--dry-run` is NOT applicable (nothing to dry-run on a read-only check).

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 check-iteration (CKI)

#### Justification (GTC_CKI_JUS)

Gate scripts (GIM, GVR) need to verify git state is correct before and after each phase. During case studies, agents ended up on wrong branches, left dirty working trees, created merge commits, and accumulated stashes — all violations of plet's git invariants. Rather than each gate script reimplementing these checks, GTC provides a single canonical check.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_JUS_1 | Why: verifies per-iteration git invariants at phase boundaries. Catches violations that prose rules failed to prevent: wrong branch, dirty tree, merge commits, stashes. Single canonical implementation shared by gate scripts, orchestrator, and external tools. | P0 |
| GTC_CKI_JUS_2 | When: called by gate scripts (GIM pre/post, GVR pre/post) at phase boundaries. Also callable by the orchestrator between iterations, by GUI tools for health display, or by humans for debugging. | P0 |
| GTC_CKI_JUS_3 | Deprecation signal: if worktree isolation makes all these checks redundant (each subagent in a clean worktree eliminates wrong-branch and dirty-tree concerns). Even then, linear history and stash checks would remain valuable. | P1 |

#### Definition (GTC_CKI_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_CMD_1 | Usage: `plet_git_check.py check-iteration [<plet_dir>] --iter-id ID_xxx --phase implement|verify [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GTC_CKI_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_INP_1 | `plet_dir` — optional positional arg, defaults to `plet/`. Script derives `{plet_dir}/state.json` and loads via `util_state.load_and_validate_global_state()`. Provides `projectId`, `loopSessionCount`. | P0 |
| GTC_CKI_INP_2 | `--iter-id` — iteration ID (e.g., `ID_001`). Script derives `{plet_dir}/state/{iter_id}.json` and loads via `util_state.load_and_validate_iter_state()`. Provides `iterationId`. | P0 |
| GTC_CKI_INP_3 | `--phase` — `implement` or `verify`. Determines the expected branch context. | P0 |

#### Outputs (GTC_CKI_OUT)

The output model is a list of checks, each with a name, status (pass/fail/warn), and detail message. This allows gate scripts to parse results and make granular decisions (e.g., block on branch violations but warn on stashes).

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_OUT_1 | Text mode: title line `PASS/WARN/FAIL: {command} — {compressed summary}`, then one line per check (`PASS/FAIL/WARN: {name} — {detail}`), then summary line at end. Title shows worst severity. | P0 |
| GTC_CKI_OUT_2 | JSON mode: structured check results (see schema below). `status` is `"ok"` when failures=0 and warnings=0, `"warn"` when warnings>0 but failures=0, `"fail"` when failures>0. | P0 |
| GTC_CKI_OUT_4 | Exit codes: 0 (no failures, no warnings), 1 (any failure), 2 (no failures, at least one warning). Callers decide how to handle exit 2 — gate scripts may proceed with log, orchestrator may note in progress.md. | P0 |
| GTC_CKI_OUT_3 | Error (bad inputs, not a git repo): specific message to stderr, exit 1. In JSON mode, structured error to stdout + text to stderr. | P0 |

**GTC_CKI JSON schema (GTC_CKI_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "check-iteration",
  "iterationId": "...",
  "phase": "...",
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

**Exit codes:** 0 = no failures, no warnings (`"ok"`), 1 = any failure (`"fail"`), 2 = no failures, at least one warning (`"warn"`).

#### Preconditions (GTC_CKI_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_PRE_1 | All required args present: `--iter-id`, `--phase` | P0 |
| GTC_CKI_PRE_2 | `{plet_dir}/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GTC_CKI_PRE_3 | `{plet_dir}/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GTC_CKI_PRE_4 | `--phase` is `implement` or `verify` | P0 |
| GTC_CKI_PRE_5 | Current directory is inside a git repository | P0 |

#### Postconditions (GTC_CKI_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_PST_1 | No git state modified — repo is identical before and after | P0 |
| GTC_CKI_PST_2 | All checks run — no early termination on first failure (accumulate all results) | P0 |
| GTC_CKI_PST_3 | Exit code reflects overall result: 0 (no failures, no warnings), 1 (any failure), 2 (no failures, at least one warning) | P0 |

#### Behaviors (GTC_CKI_BHV)

Each check verifies one git invariant. All checks are always run — no short-circuiting on first failure. This gives the caller a complete picture rather than forcing fix-one-rerun cycles.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKI_BHV_1 | **correct-branch**: Derives expected branch `plet/{projectId}/loop{N}/{iter_id}` from global and iteration state. Checks `git branch --show-current` matches. FAIL if on wrong branch or detached HEAD. | P0 |
| GTC_CKI_BHV_2 | **clean-worktree**: Checks `git status --porcelain` is empty. FAIL if there are uncommitted changes. Detail includes count of modified/untracked files. | P0 |
| GTC_CKI_BHV_3 | **linear-history**: Checks for merge commits on the iteration branch since it diverged from the workstream. Uses `git log --merges {workstream}..HEAD`. FAIL if any merge commits found. Detail includes count and first merge commit hash. Linear history is required for clean `git bisect` and audit trails (IMP_16). | P0 |
| GTC_CKI_BHV_4 | **no-stashes**: Checks `git stash list` is empty. WARN (not FAIL) if stashes exist. Stashes are banned (FB_30) but their presence doesn't block execution — it's a compliance signal. Detail includes stash count. | P0 |
| GTC_CKI_BHV_5 | **branch-exists**: Verifies the iteration branch exists (`git rev-parse --verify refs/heads/{branch}`). FAIL if the branch doesn't exist. This catches cases where the branch was accidentally deleted or never created. Runs before correct-branch — if the branch doesn't exist, correct-branch would also fail, but this gives a more specific error. | P0 |
| GTC_CKI_BHV_6 | Check order: in-progress-operation → branch-exists → correct-branch → clean-worktree → linear-history → no-stashes. Broken git state first (blocks everything), branch existence next, stashes last (least severe — warn only). | P0 |
| GTC_CKI_BHV_8 | **in-progress-operation**: Checks for interrupted git operations — rebase (`.git/rebase-merge` or `.git/rebase-apply`), merge (`MERGE_HEAD`), cherry-pick (`CHERRY_PICK_HEAD`), bisect (`BISECT_LOG`). FAIL if any detected. Detail names which operation is in progress. More actionable than clean-worktree alone (explains *why* the tree is dirty). | P0 |
| GTC_CKI_BHV_7 | Derives workstream branch as `plet/{projectId}/loop{N}/workstream` for the linear-history check. If workstream doesn't exist, linear-history check emits WARN (can't determine merge base — likely first iteration before workstream creation). | P1 |

---

### 3.2 check-session (CKS)

#### Justification (GTC_CKS_JUS)

At session boundaries (start and end), the orchestrator needs a global health check across the entire loop session. FB_32 showed orphaned worktrees surviving across retries. The plan references GTC check-session for scanning worktrees at session start (GTI_AFL_3 in plet_git_iteration.md). Session-end checks verify that all completed iterations have been merged and no resources are left behind.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_JUS_1 | Why: session-level git health check. Catches orphaned worktrees (FB_32), unmerged completed iterations, and lingering stashes across the entire loop session — problems that per-iteration checks can't detect. | P0 |
| GTC_CKS_JUS_2 | When: called by orchestrator at session start (preflight — discover stale state) and session end (cleanup verification — nothing left behind). Also callable by GUI tools for health display or by humans for manual health checks. | P0 |
| GTC_CKS_JUS_3 | Deprecation signal: if the orchestrator becomes deterministic enough that these issues can't arise. Unlikely — external factors (crashes, manual intervention) always leave residue. | P1 |

#### Definition (GTC_CKS_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_CMD_1 | Usage: `plet_git_check.py check-session [<plet_dir>] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GTC_CKS_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_INP_1 | `plet_dir` — optional positional arg, defaults to `plet/`. Script derives `{plet_dir}/state.json` and loads via `util_state.load_and_validate_global_state()`. Provides `projectId`, `loopSessionCount`. | P0 |
| GTC_CKS_INP_2 | Script derives `{plet_dir}/state/` as the per-iteration state directory. Used to scan all iteration state files and cross-reference their lifecycles against git state. | P0 |

#### Outputs (GTC_CKS_OUT)

Same output model as check-iteration: a list of checks with pass/fail/warn statuses.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_OUT_1 | Text mode: title line `PASS/WARN/FAIL: {command} — {compressed summary}`, then one line per check, then summary line at end. Title shows worst severity. | P0 |
| GTC_CKS_OUT_2 | JSON mode: structured check results (see schema below). `status` is `"ok"` / `"warn"` / `"fail"`. Some checks include an `items` array (e.g., orphaned worktrees, unmerged iterations). | P0 |
| GTC_CKS_OUT_3 | Error (bad inputs, not a git repo): specific message to stderr, exit 1. In JSON mode, structured error to stdout + text to stderr. | P0 |
| GTC_CKS_OUT_4 | Exit codes: 0 (no failures, no warnings), 1 (any failure), 2 (no failures, at least one warning). Callers decide how to handle exit 2. | P0 |

**GTC_CKS JSON schema (GTC_CKS_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "check-session",
  "projectId": "...",
  "loopSession": N,
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "...", "items": ["..."]}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

**Exit codes:** 0 = no failures, no warnings (`"ok"`), 1 = any failure (`"fail"`), 2 = no failures, at least one warning (`"warn"`).

#### Preconditions (GTC_CKS_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_PRE_1 | `plet_dir` resolves to an existing directory (default `plet/`) | P0 |
| GTC_CKS_PRE_2 | `{plet_dir}/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GTC_CKS_PRE_3 | `{plet_dir}/state/` is an existing directory | P0 |
| GTC_CKS_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GTC_CKS_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_PST_1 | No git state modified — repo is identical before and after | P0 |
| GTC_CKS_PST_2 | All checks run — no early termination on first failure | P0 |
| GTC_CKS_PST_3 | Exit code reflects overall result: 0 (no failures, no warnings), 1 (any failure), 2 (no failures, at least one warning) | P0 |

#### Behaviors (GTC_CKS_BHV)

Session-level checks scan across all iterations and git state for the current loop session. The `{plet_dir}/state/` directory is scanned for `*.json` files to enumerate known iterations.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_CKS_BHV_1 | **orphaned-worktrees**: Lists git worktrees (`git worktree list --porcelain`), identifies any under the plet namespace that don't correspond to an active (non-complete, non-withdrawn) iteration. WARN for each orphaned worktree found. Detail includes worktree path and branch. Addresses FB_32. | P0 |
| GTC_CKS_BHV_2 | **no-stashes**: Checks `git stash list` is empty. WARN if stashes exist. Same as the per-iteration check but at session scope — stashes may have been created outside any iteration context. Detail includes stash count. Addresses FB_30. | P0 |
| GTC_CKS_BHV_3 | **unmerged-complete**: Scans state files in `{plet_dir}/state/` for iterations with `lifecycle: "complete"`. For each, checks if its iteration branch (`plet/{projectId}/loop{N}/{iter_id}`) is an ancestor of the workstream branch. FAIL for any complete iteration whose branch is not merged (work was declared done but never integrated). Detail lists the unmerged iteration IDs. | P0 |
| GTC_CKS_BHV_4 | **workstream-exists**: Verifies the workstream branch `plet/{projectId}/loop{N}/workstream` exists. FAIL if it doesn't exist and there are iterations in non-ineligible states (work has started but no workstream). PASS if it doesn't exist and all iterations are ineligible/queued (loop hasn't started yet). | P0 |
| GTC_CKS_BHV_5 | Check order: in-progress-operation → workstream-exists → orphaned-worktrees → orphaned-branches → no-stashes → unmerged-complete. Broken repo first, then workstream (structural), cleanup checks next, merge verification last. | P0 |
| GTC_CKS_BHV_9 | **orphaned-branches**: Lists plet-namespaced branches (`plet/{projectId}/loop{N}/*`), identifies any that don't have a corresponding state file in `{plet_dir}/state/`. WARN for each. Detail includes branch name. Reverse of unmerged-complete (branch without state, vs state without merge). | P0 |
| GTC_CKS_BHV_8 | **in-progress-operation**: Same check as CKI_BHV_8 — detects interrupted rebase, merge, cherry-pick, bisect. FAIL if any detected. Catches broken repo state at session preflight before any iterations are spawned. | P0 |
| GTC_CKS_BHV_6 | Scans `{plet_dir}/state/` for `*.json` files. Each file is loaded via `util_state.load_and_validate_iter_state()`. Files that fail validation are reported as WARN (corrupt state file) and skipped for subsequent checks. | P0 |
| GTC_CKS_BHV_7 | For unmerged-complete check: an iteration branch is "merged" if it is an ancestor of the workstream HEAD. Uses `git merge-base --is-ancestor {iter_branch} {workstream}`. If the iteration branch no longer exists (already cleaned up), treat as PASS (branch deleted = already handled). | P0 |

---

## 4. Edge Cases (GTC_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_EDG_1 | Not inside a git repo — error before any checks. | P0 |
| GTC_EDG_2 | State file validation fails — error with specific field/issue. | P0 |
| GTC_EDG_3 | Iteration branch doesn't exist in check-iteration — FAIL on branch-exists check, remaining checks still run where possible (clean-worktree and no-stashes can still run without needing the branch to exist). | P0 |
| GTC_EDG_4 | Workstream branch doesn't exist in check-iteration — linear-history check emits WARN (can't determine merge base). Other checks unaffected. | P0 |
| GTC_EDG_5 | Detached HEAD in check-iteration — branch-exists may PASS (the iteration branch ref can exist while HEAD is detached), correct-branch FAILs (`git branch --show-current` returns empty). Two independent checks, both correct. | P0 |
| GTC_EDG_6 | No state files in `{plet_dir}/state/` for check-session — all checks that depend on iteration state (unmerged-complete) are PASS (nothing to check). Orphaned worktrees and stash checks still run. | P0 |
| GTC_EDG_7 | `{plet_dir}/state/` contains non-JSON files — ignored (only `*.json` scanned). | P0 |
| GTC_EDG_8 | State file in `{plet_dir}/state/` fails validation — WARN (corrupt state file) and skip that iteration for subsequent checks. | P0 |
| GTC_EDG_9 | `--pretty` without `--output json` — error. | P0 |
| GTC_EDG_10 | `--fields` without `--output json` — error. | P0 |
| GTC_EDG_11 | Duplicate flags — error via `parse_kwargs`. | P0 |
| GTC_EDG_12 | Worktrees created outside plet namespace — ignored by orphaned-worktrees check (only scans for plet-namespaced worktrees). | P0 |
| GTC_EDG_13 | Iteration branch deleted but `cleanupBranchesAutomatically` was false — check-session treats missing branch for complete iteration as PASS (already cleaned up manually or by other means). | P0 |
| GTC_EDG_14 | Multiple interrupted git operations (e.g., rebase AND cherry-pick) — in-progress-operation reports all detected, not just the first. Detail lists each operation type found. | P0 |
| GTC_EDG_15 | Workstream branch (`plet/{projectId}/loop{N}/workstream`) is not flagged by orphaned-branches — it has no state file by design. Excluded from the orphaned-branches scan. | P0 |

## 5. Error Handling (GTC_ERR)

Errors are distinct from check failures. Errors are structural problems that prevent checks from running (bad input, not a git repo). Check failures are the checks running successfully and finding violations.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| GTC_ERR_2 | Invalid `--phase` → `Error: invalid --phase '{value}' (valid: implement, verify)` | P0 |
| GTC_ERR_3 | Global state validation failure → error from `util_state.load_and_validate_global_state()` on `{plet_dir}/state.json` | P0 |
| GTC_ERR_4 | Iter state validation failure → error from `util_state.load_and_validate_iter_state()` on `{plet_dir}/state/{iter_id}.json` | P0 |
| GTC_ERR_5 | Not a git repo → `Error: not inside a git repository` | P0 |
| GTC_ERR_6 | `plet_dir` is a file, not a directory → `Error: expected a directory, got file: {path}` (UNV_ERR_6) | P0 |
| GTC_ERR_7 | `plet_dir` doesn't exist → `Error: directory not found: {path}` | P0 |
| GTC_ERR_8 | Git command failed → `Error: git command failed: {stderr}` | P0 |
| GTC_ERR_9 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| GTC_ERR_10 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| GTC_ERR_11 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| GTC_ERR_12 | `{plet_dir}/state/` doesn't exist or is not a directory → `Error: state directory not found: {path}` | P0 |
| GTC_ERR_13 | `{plet_dir}/state/{iter_id}.json` not found → `Error: iteration state file not found: {path}` | P0 |
| GTC_ERR_14 | `--dry-run` passed → `Error: --dry-run is not supported (check-iteration and check-session are read-only)` | P0 |

## 6. Formats (GTC_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_FMT_1 | Reads `{plet_dir}/state.json` via `util_state` for `projectId`, `loopSessionCount`. | P0 |
| GTC_FMT_2 | Reads `{plet_dir}/state/{id}.json` via `util_state` for `iterationId`, `lifecycle`. | P0 |
| GTC_FMT_3 | Branch name convention: `plet/{projectId}/loop{N}/{iter_id}` (iteration), `plet/{projectId}/loop{N}/workstream` (workstream). Derived from state files, not constructed from flags. | P0 |
| GTC_FMT_4 | Writes nothing — read-only. | P0 |

## 7. Agent Flows (GTC_AFL)

### GTC_AFL_1: Gate script pre-phase check

1. Orchestrator spawns gate script (GIM or GVR) before phase begins
2. Gate script calls: `plet_git_check.py check-iteration --iter-id ID_001 --phase implement --output json`
3. Gate script parses JSON: checks `status` and individual check results
4. If exit 1 (`"fail"`): gate script blocks the phase, reports violations to orchestrator
5. If exit 2 (`"warn"`): gate script proceeds, logs warnings to progress.md
6. If exit 0 (`"ok"`): gate script proceeds

### GTC_AFL_2: Gate script post-phase check

1. Subagent finishes phase (implement or verify)
2. Gate script calls: `plet_git_check.py check-iteration --iter-id ID_001 --phase verify --output json`
3. Gate script verifies phase left git state clean
4. If exit 1: gate script reports violations to orchestrator (may not block — depends on severity)
5. If exit 2: gate script logs warnings to progress.md

### GTC_AFL_3: Orchestrator session preflight

1. Orchestrator starts a new loop session
2. Calls: `plet_git_check.py check-session --output json`
3. Inspects results:
   - in-progress-operation FAIL → abort session, alert human (broken repo state)
   - orphaned worktrees → cleanup via `plet_git_iteration.py worktree-remove`
   - orphaned branches → log warning in progress.md
   - stashes → warn in progress.md
   - unmerged complete → flag for investigation
4. Orchestrator decides: proceed, cleanup first, or alert human

### GTC_AFL_4: Orchestrator session end

1. Orchestrator finishes all iterations in the loop
2. Calls: `plet_git_check.py check-session --output json`
3. Verifies: no orphaned worktrees, no orphaned branches, no stashes, all complete iterations merged
4. Logs session health summary to progress.md

## 8. Examples (GTC_EXM)

### GTC_EXM_1: check-iteration — all passing

```bash
plet_git_check.py check-iteration --iter-id ID_001 --phase implement
# PASS: check-iteration — 6 passed
# PASS: in-progress-operation — no interrupted git operations
# PASS: branch-exists — plet/LOGA/loop1/ID_001 exists
# PASS: correct-branch — on plet/LOGA/loop1/ID_001
# PASS: clean-worktree — no uncommitted changes
# PASS: linear-history — no merge commits since workstream divergence
# PASS: no-stashes — stash list empty
# 6 checks: 6 passed, 0 failed, 0 warnings
```

### GTC_EXM_2: check-iteration — violations found

```bash
plet_git_check.py check-iteration --iter-id ID_001 --phase implement
# FAIL: check-iteration — 2 failed, 1 warning
# PASS: in-progress-operation — no interrupted git operations
# PASS: branch-exists — plet/LOGA/loop1/ID_001 exists
# FAIL: correct-branch — expected plet/LOGA/loop1/ID_001, on main
# FAIL: clean-worktree — 3 uncommitted changes (2 modified, 1 untracked)
# PASS: linear-history — no merge commits since workstream divergence
# WARN: no-stashes — 2 stashes found
# 6 checks: 3 passed, 2 failed, 1 warnings
```

### GTC_EXM_3: check-iteration — JSON output

```bash
plet_git_check.py check-iteration --iter-id ID_001 \
    --phase implement --output json --pretty
# {
#   "status": "fail",
#   "command": "check-iteration",
#   "iterationId": "ID_001",
#   "phase": "implement",
#   "checks": [
#     {"name": "in-progress-operation", "status": "pass", "detail": "no interrupted git operations"},
#     {"name": "branch-exists", "status": "pass", "detail": "plet/LOGA/loop1/ID_001 exists"},
#     {"name": "correct-branch", "status": "fail", "detail": "expected plet/LOGA/loop1/ID_001, on main"},
#     {"name": "clean-worktree", "status": "pass", "detail": "no uncommitted changes"},
#     {"name": "linear-history", "status": "pass", "detail": "no merge commits since workstream divergence"},
#     {"name": "no-stashes", "status": "warn", "detail": "2 stashes found"}
#   ],
#   "summary": {"total": 6, "passed": 4, "failed": 1, "warnings": 1},
#   "scriptVersion": "0.1.0",
#   "timestamp": "2026-03-23T10:30:00Z"
# }
```

### GTC_EXM_4: check-session — orphaned worktree found

```bash
plet_git_check.py check-session
# WARN: check-session — 1 warning
# PASS: in-progress-operation — no interrupted git operations
# PASS: workstream-exists — plet/LOGA/loop1/workstream exists
# WARN: orphaned-worktrees — 1 orphaned worktree: /tmp/plet-ID_015-impl2 (branch: plet/LOGA/loop1/ID_015)
# PASS: orphaned-branches — no plet branches without state files
# PASS: no-stashes — stash list empty
# PASS: unmerged-complete — all 3 complete iterations merged to workstream
# 6 checks: 5 passed, 0 failed, 1 warnings
```

### GTC_EXM_5: check-session — JSON output with --fields

```bash
plet_git_check.py check-session \
    --output json --fields status,checks,summary
# {"status":"ok","checks":[...],"summary":{"total":6,"passed":6,"failed":0,"warnings":0},"fieldsIncluded":["status","checks","summary"],"fieldsOmitted":["command","projectId","loopSession","scriptVersion","timestamp"]}
```

## 9. Dependencies on Other Scripts (GTC_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GTC_DEP_1 | imports | `util_cli` | `parse_kwargs`, `require_kwargs`, `validate_enum`, `now_iso`, `dispatch`, `filter_fields` |
| GTC_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
| GTC_DEP_6 | imports | `util_subprocess` | `run_git` |
| GTC_DEP_3 | called by | `plet_gate_phase.py` | pre/post checks for both implement and verify phases |
| GTC_DEP_5 | called by | `plet_orchestrator.py` | session preflight/end |

No outgoing calls to other `plet_*.py` scripts — `plet_git_check.py` is a leaf CLI tool. Calls `git` via `util_subprocess`.

## 10. Non-Functional Requirements (GTC_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_NFR_1 | Git operations via `subprocess.run()` with explicit args per UNV_NFR_9 (no shell=True) | P0 |
| GTC_NFR_2 | All git stderr captured and included in error messages | P0 |
| GTC_NFR_3 | check-session must handle large state directories efficiently — scan all `*.json` files but avoid loading full state for checks that don't need it | P1 |

## 11. Developer Experience (GTC_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GTC_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| GTC_DXP_2 | IMPORTANT: both commands are read-only — no `--dry-run` needed, safe to run anytime | P0 |
| GTC_DXP_3 | PITFALLS: check-iteration requires being in a git repo (will fail if run from wrong directory); `plet_dir` must point to the plet directory (default `plet/`), not a state file — the script derives `state.json` and `state/` paths internally | P0 |
| GTC_DXP_4 | Help text documents flag dependencies: `--pretty` and `--fields` require `--output json` | P0 |
| GTC_DXP_5 | Error messages include git's stderr when a git command fails | P0 |
| GTC_DXP_6 | Check names are stable identifiers (in-progress-operation, branch-exists, correct-branch, clean-worktree, linear-history, no-stashes, workstream-exists, orphaned-worktrees, orphaned-branches, unmerged-complete) — gate scripts and orchestrator can match on them. in-progress-operation is shared by both commands. | P0 |

## 12. Critical Test Areas (GTC_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GTC_CRT_13 | in-progress-operation detection | Interrupted rebase/merge/cherry-pick not caught, next phase starts with broken git state | Create .git/rebase-merge dir, verify FAIL |
| GTC_CRT_1 | correct-branch detection | Wrong branch not caught, phase runs on wrong code | Create iteration branch, checkout different branch, verify FAIL |
| GTC_CRT_2 | clean-worktree detection | Dirty tree not caught, uncommitted changes leak into phase | Create uncommitted changes, verify FAIL |
| GTC_CRT_3 | linear-history detection | Merge commits not caught, git bisect breaks | Create a merge commit on iteration branch, verify FAIL |
| GTC_CRT_4 | stash detection | Stashes not caught, agent violating stash ban goes unnoticed | Create stashes, verify WARN |
| GTC_CRT_5 | orphaned-worktree detection | Orphaned worktrees not caught, disk fills up | Create worktree, mark iteration complete, verify WARN |
| GTC_CRT_6 | unmerged-complete detection | Complete iteration not merged, work lost | Mark iteration complete, don't merge, verify FAIL |
| GTC_CRT_7 | All checks run (no short-circuit) | First failure masks subsequent violations | Create multiple violations, verify all reported |
| GTC_CRT_8 | Exit code correctness | Gate script gets wrong signal | Verify exit 0 on all-pass, exit 1 on any-fail |
| GTC_CRT_9 | JSON output parseable | Gate script can't parse results | Verify valid JSON, correct structure, all fields present |
| GTC_CRT_10 | Read-only guarantee | Check accidentally modifies git state | Run check, verify no new commits/branches/tags/stashes |
| GTC_CRT_11 | Detached HEAD handling | Detached HEAD not caught or causes crash | Detach HEAD, run check-iteration, verify FAIL on correct-branch |
| GTC_CRT_12 | --dry-run rejection | Agent passes --dry-run and expects behavior | Pass --dry-run, verify error message |
| GTC_CRT_14 | orphaned-branches detection | Orphaned branches not caught, stale branches accumulate | Create plet branch with no state file, verify WARN. Verify workstream branch excluded. |
| GTC_CRT_15 | Exit code 2 (warn-only) | Callers can't distinguish warn from pass | Create stashes only (no failures), verify exit 2 and status "warn" |

## 13. Testing & Verification (GTC_TST)

**What to test:** See §12 Critical Test Areas (GTC_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_git_check.py`
- Run: `python3 skills/plet/tests/test_plet_git_check.py`
- Harness: stdlib-only custom harness per UNV_TST_2. Uses `run()` (subprocess) and `check()` (assert).
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- **Git fixtures:** tests create temporary git repos with mock state.json, iteration state files, branches, worktrees, and controlled git state (dirty files, merge commits, stashes). Tests must clean up all git state after completion.
- **Worktree tests:** some tests need to create and inspect worktrees. These require a bare or non-bare repo that supports worktree operations. Use `tempfile.TemporaryDirectory()` for isolation.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command. check-iteration first (simpler, fewer git operations), check-session second (scans directory, cross-references state).

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Should stash violations be FAIL or WARN? | WARN. Stashes are banned (FB_30) but their presence doesn't block execution — they're a compliance signal. Exit code 2 (warnings only) gives callers a distinct signal without forcing a block. The caller (gate script, orchestrator) decides how to handle exit 2. |
| 2 | Should check-iteration verify audit tags exist? | No. Audit tags are GTO's responsibility and are created after each phase ends. check-iteration runs at phase boundaries (before/after) — tags may not exist yet at pre-phase check. Tag verification belongs in a hypothetical post-merge check, not phase-boundary checks. |
| 3 | Should the script take `--checks` to run only specific checks? | No for now (YAGNI). All checks are fast (git operations). If a use case emerges for selective checking, add it then. Gate scripts can already filter by parsing the JSON output. |
| 4 | check-session: scan state files or take explicit iteration list? | Scan state files. The state directory is the source of truth for which iterations exist. Taking an explicit list requires the caller to know all iterations — redundant with the state directory. |
| 5 | Should check-session verify workstream has no unexpected commits? | No. The workstream is the orchestrator's domain — it creates merge-squash commits there. "Unexpected" commits could be legitimate manual intervention. Out of scope for a compliance checker. |

### Open Questions

- Should check-iteration verify that the iteration branch is based on the correct workstream commit (i.e., not stale)? This would catch cases where the workstream advanced but the iteration branch wasn't rebased. Deferred — may be overreach for a compliance checker vs. the orchestrator's responsibility.

## 15. Future Considerations (GTC_FUT)

| ID | Area | Description |
|----|------|-------------|
| GTC_FUT_1 | Worktree health check | A `check-worktree` command reporting detailed state of a specific worktree (branch, dirty/clean, last commit, divergence from workstream). Candidate from GTI_FUT_2. |
| GTC_FUT_2 | `--checks` flag | Selective check execution — run only named checks. Useful if specific checks become expensive or if callers want to skip known-failing checks. |
| ~~GTC_FUT_3~~ | ~~`--fix` mode~~ | Withdrawn. GTC is read-only by design. Fixes belong in the caller (orchestrator calls GTI worktree-remove, etc.). |

## 16. FB Items Addressed

- FB_30 — Agents used 42 git stashes despite ban. `check-iteration` and `check-session` detect stashes at phase and session boundaries.
- FB_32 — Orphaned worktree after retry. `check-session` detects orphaned worktrees that don't correspond to active iterations.
