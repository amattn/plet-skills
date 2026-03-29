# plet_gate_session.py (GSS)

> Status: complete

> Renamed from `plet_gate_session.py` (SES) → `plet_gate_session.py` (GSS). Read-only session-level gate checks — parallel to `plet_gate_phase.py` for phase-level gates. Originally renamed from `plet_router.py` (RTR).

## 1. Purpose (GSS_PUR)

The `/plet` entry point needs to know which phase the project is in, what the current state looks like, and whether the environment is ready for work. These are three distinct questions that the SKILL.md routing logic currently answers via prose interpretation — with drift risk across compaction cycles and session boundaries. This script makes all three answers deterministic.

**Three commands, three audiences:**

| Command | Question | Audience | Performance |
|---------|----------|----------|-------------|
| `detect` | "What should I do next?" | Machines (SKILL.md routing, orchestrator) | Fast (< 500ms) — bare output, no scans |
| `status` | "What's the state of the world?" | Humans + dashboards (GUI, manual inspection) | Moderate (< 2s) — scans state files, optional fingerprint check |
| `preflight` | "Is the environment ready?" | Gate logic (go/no-go before any session) | Moderate (< 2s) — checks files, settings, fingerprints |

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PUR_1 | Phase detection from project state. Reads plet artifacts on disk and determines the correct session type (plan, loop, refine). Implements the OR_2–OR_6 routing logic as deterministic code. | P0 |
| GSS_PUR_2 | Project status summary. Machine-readable snapshot of iteration counts, lifecycle distribution, blockers, active agents, and fingerprint consistency. Implements OR_12. | P0 |
| GSS_PUR_3 | Pre-session environment checks. Verifies the project is ready for plet work: scripts installed, git health (via GTC check-session), CLAUDE.md exists, .gitignore includes .plet/, spec artifacts exist, state valid, fingerprints consistent. Addresses FB_16, FB_23. | P0 |

## 2. Agent Personas (GSS_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GSS_AGT_1 | SKILL.md orchestrator | `/plet` entry point routing | `detect` |
| GSS_AGT_2 | SKILL.md orchestrator | before entering loop/refine | `preflight` |
| GSS_AGT_3 | orchestrator script | session start | `detect`, `preflight` |
| GSS_AGT_4 | orchestrator script | between iterations (health check) | `status` |
| GSS_AGT_5 | human | manual inspection / debugging | all commands |
| GSS_AGT_6 | GUI tool | dashboard state display | `status`, `detect` |

## 3. Commands

**Command summary:**

- **`detect`** (DET) — Determine which session type to enter (plan, loop, refine, or status). Read-only routing primitive. Called by SKILL.md at every `/plet` invocation.
- **`status`** (STA) — Project status dashboard: iteration counts, blockers, active agents. Read-only. Called by SKILL.md for `/plet status` and by humans for inspection. (Note: STA abbreviation is different from plet_state.py's STA prefix.)
- **`preflight`** (PRE) — Pre-session environment checks (scripts installed, git health, fingerprints consistent). Read-only. Returns go/no-go verdict. Called before every session.

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |

All commands are read-only — `--dry-run` is NOT applicable.

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Both modes always emit text to stderr for human debugging. Per UNV_ERR_4.

---

### 3.1 detect (DET)

#### Justification (GSS_DET_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_JUS_1 | Why: determines which session type to enter based on project state on disk. The SKILL.md routing logic (OR_2–OR_6) currently runs as prompt-interpreted prose — vulnerable to drift after compaction. This command makes routing deterministic. | P0 |
| GSS_DET_JUS_2 | When: called by SKILL.md at `/plet` entry, by the orchestrator script at session start, and by GUI tools for phase display. | P0 |
| GSS_DET_JUS_3 | Deprecation signal: only if the orchestrator absorbs routing entirely (unlikely — SKILL.md still needs routing for interactive sessions). | P1 |

#### Definition (GSS_DET_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_CMD_1 | Usage: `plet_gate_session.py detect [<plet_dir>] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GSS_DET_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. | P0 |

#### Outputs (GSS_DET_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_OUT_1 | Text mode: bare session type to stdout: `plan`, `loop`, `refine`, or `status`. Suitable for shell capture: `SESSION=$(plet_gate_session.py detect)`. Exit 0. | P0 |
| GSS_DET_OUT_2 | JSON mode: structured detection result (see schema below). Exit 0. | P0 |
| GSS_DET_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

**GSS_DET JSON schema (GSS_DET_OUT_2):**
```json
{
  "status": "ok",
  "command": "detect",
  "sessionType": "plan|loop|refine",
  "reason": "...",
  "artifacts": {
    "requirements": true|false,
    "iterations": true|false,
    "state": true|false
  },
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (GSS_DET_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_PRE_1 | None — detect must work even when plet_dir doesn't exist (that's the "plan" signal). | P0 |

#### Postconditions (GSS_DET_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_PST_1 | No files modified | P0 |
| GSS_DET_PST_2 | Output is one of: `plan`, `loop`, `refine` | P0 |

#### Behaviors (GSS_DET_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DET_BHV_1 | If `plet_dir` doesn't exist or `requirements.md` doesn't exist → `plan` (OR_2) | P0 |
| GSS_DET_BHV_2 | If `requirements.md` exists but `iterations.md` or `state.json` missing → `plan` (OR_3) | P0 |
| GSS_DET_BHV_3 | If state exists with any iterations in `queued`, `implementing`, or `verifying` → `loop` (OR_4). `ineligible` alone does NOT trigger loop. | P0 |
| GSS_DET_BHV_4 | If state exists and all iterations are `complete` → `refine` (OR_5) | P0 |
| GSS_DET_BHV_5 | If state exists with `blocked` iterations and none `queued`/`implementing`/`verifying` → `refine` (OR_6) | P0 |
| GSS_DET_BHV_6 | Scans `plet/state/*.json` to determine iteration lifecycles. Uses `util_state.load_and_validate_iter_state()` for each. Invalid state files are skipped with warning. | P0 |
| GSS_DET_BHV_7 | `reason` field in JSON explains why this session type was chosen (e.g., "3 queued iterations found" or "no plet directory"). | P0 |

---

### 3.2 status (STS)

#### Justification (GSS_STS_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_JUS_1 | Why: produces a machine-readable snapshot of project state — iteration counts by lifecycle, blockers, active agents, fingerprint consistency. OR_12 says `/plet status` prints a summary. This command provides the data. | P0 |
| GSS_STS_JUS_2 | When: called by the orchestrator between iterations for health checks, by GUI tools for dashboard display, and by humans for manual inspection. | P0 |
| GSS_STS_JUS_3 | Deprecation signal: if a richer status dashboard replaces file-based state reading. | P1 |

#### Definition (GSS_STS_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_CMD_1 | Usage: `plet_gate_session.py status [<plet_dir>] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GSS_STS_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. Derives `state.json` and `state/` paths internally. Same input pattern as detect and preflight. | P0 |

#### Outputs (GSS_STS_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_OUT_1 | Text mode: formatted summary to stdout — project name, session type, iteration counts by lifecycle, blockers listed, active agents listed. Exit 0. | P0 |
| GSS_STS_OUT_2 | JSON mode: structured project status (see schema below). Exit 0. | P0 |
| GSS_STS_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

**GSS_STS JSON schema (GSS_STS_OUT_2):**
```json
{
  "status": "ok",
  "command": "status",
  "projectId": "...",
  "projectName": "...",
  "sessionType": "plan|loop|refine",
  "loopSession": N,
  "progress": {"complete": N, "total": N, "percent": N},
  "iterations": {
    "total": N,
    "ineligible": N,
    "queued": N,
    "implementing": N,
    "verifying": N,
    "complete": N,
    "blocked": N,
    "withdrawn": N
  },
  "milestones": {
    "MS_1": {"name": "...", "complete": N, "total": N, "iterations": {"ID_001": "complete", "ID_002": "implementing"}}
  },
  "blockers": [
    {"iterationId": "...", "title": "..."}
  ],
  "activeAgents": [
    {"iterationId": "...", "agentId": "...", "activity": "..."}
  ],
  "fingerprints": {"consistent": true|false|null},
  "warnings": ["..."],
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (GSS_STS_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_PRE_1 | `plet_dir` exists and is a directory | P0 |
| GSS_STS_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GSS_STS_PRE_3 | `plet_dir/state/` exists and is a directory | P0 |

#### Postconditions (GSS_STS_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_PST_1 | No files modified | P0 |

#### Behaviors (GSS_STS_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_STS_BHV_1 | Scans all `*.json` files in `state_dir` (excluding `state.json`). Loads each via `util_state.load_and_validate_iter_state()`. | P0 |
| GSS_STS_BHV_2 | Counts iterations by lifecycle: ineligible, queued, implementing, verifying, complete, blocked, withdrawn. | P0 |
| GSS_STS_BHV_3 | Lists blocked iterations with their IDs and titles. | P0 |
| GSS_STS_BHV_4 | Lists active agents (iterations where `agentId` is not null) with iteration ID and activity. | P0 |
| GSS_STS_BHV_5 | Calls `detect` logic internally to include `sessionType` in output. | P0 |
| GSS_STS_BHV_6 | Checks fingerprint consistency by calling `plet_fingerprint.py check` via subprocess. Reports `consistent: true/false`. If fingerprint check fails (missing files or script not found), reports `consistent: null` with detail. Graceful degradation — status always produces a result. | P1 |
| GSS_STS_BHV_7 | Invalid state files are counted and reported as warnings. | P0 |
| GSS_STS_BHV_8 | Reports progress as `complete / total` with percentage. | P0 |
| GSS_STS_BHV_9 | Milestone breakdown: reads milestones from global state, cross-references iteration IDs to show per-milestone progress. In text output, milestones appear at the bottom (detail, not headline). In JSON output, included as a `milestones` object. | P0 |

---

### 3.3 preflight (PRF)

#### Justification (GSS_PRF_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_JUS_1 | Why: verifies the project environment is ready for plet work. FB_16 (spec artifacts lost), FB_22 (bypassPermissions not configured), FB_23 (CLAUDE.md missing) all showed that plet assumed a ready environment but didn't check. This command checks. | P0 |
| GSS_PRF_JUS_2 | When: called before entering any session (plan, loop, refine). The orchestrator and SKILL.md both run preflight before doing work. | P0 |
| GSS_PRF_JUS_3 | Deprecation signal: if project setup becomes fully automated (unlikely — some checks are environment-specific). | P1 |

#### Definition (GSS_PRF_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_CMD_1 | Usage: `plet_gate_session.py preflight [<plet_dir>] --session-type detect|plan|loop|refine [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GSS_PRF_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. Used to locate state files and spec artifacts. | P0 |
| GSS_PRF_INP_2 | `--session-type` — required. `detect` (auto-detect via detect logic), `plan`, `loop`, or `refine`. Controls session-type-dependent checks (fingerprint severity). `detect` runs auto-detection internally. `plan`/`loop`/`refine` override — allows forcing a session type (e.g., "I'm about to loop" even if detect says "refine"). | P0 |

#### Outputs (GSS_PRF_OUT)

Same output model as GTC: a list of checks with pass/fail/warn statuses.

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_OUT_1 | Text mode: title line `PASS/WARN/FAIL: preflight — {summary}`, then one line per check, then summary line. | P0 |
| GSS_PRF_OUT_2 | JSON mode: structured preflight results (see schema below). Same output model as GTC. | P0 |
| GSS_PRF_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). Same as GTC. | P0 |
| GSS_PRF_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

**GSS_PRF JSON schema (GSS_PRF_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "preflight",
  "sessionType": "detect|plan|loop|refine",
  "checks": [
    {"name": "...", "status": "pass|fail|warn|skipped", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N, "skipped": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

**Check statuses:** `pass` (checked, ok), `fail` (checked, violation), `warn` (checked, concern), `skipped` (intentionally not evaluated — e.g., fingerprints during plan). Skipped checks don't affect the exit code.

**Exit codes:** 0 = no failures, no warnings (`"ok"`), 1 = any fail (`"fail"`), 2 = warn only (`"warn"`).

#### Preconditions (GSS_PRF_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_PRE_1 | None — preflight must work even on a fresh project with no plet directory. Missing artifacts are reported as check results, not precondition errors. | P0 |

#### Postconditions (GSS_PRF_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_PST_1 | No files modified | P0 |
| GSS_PRF_PST_2 | All checks run — no short-circuit on first failure | P0 |

#### Behaviors (GSS_PRF_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_PRF_BHV_1 | **claude-md-exists**: Checks `CLAUDE.md` exists in project root. WARN if missing (FB_23). plet works without it but institutional memory is lost. | P0 |
| GSS_PRF_BHV_2 | **gitignore-plet**: Checks `.gitignore` includes `.plet/` or `.plet`. WARN if missing. `.plet/` is local working state (worktrees, caches) — shouldn't be committed. | P0 |
| GSS_PRF_BHV_3 | ~~**bypass-permissions**~~: Dropped. `plet_invoke.py` launches subprocesses with `claude --enable-auto-mode` — project-level permission settings don't matter for subprocess invocations. The invoke script owns the permission model. | — |
| GSS_PRF_BHV_4 | **spec-artifacts**: If `plet_dir` exists, checks `requirements.md` and `iterations.md` exist. FAIL if plet_dir exists but spec artifacts are missing (FB_16 — lost artifacts make the project unresumable). PASS if plet_dir doesn't exist (fresh project, plan will create them). | P0 |
| GSS_PRF_BHV_5 | **state-valid**: If `plet/state.json` exists, validates it via `util_state.load_and_validate_global_state()`. FAIL if invalid. PASS if doesn't exist (fresh project). | P0 |
| GSS_PRF_BHV_6 | **fingerprints-consistent**: Severity depends on session type (from `--session-type`): **plan** → SKIPPED (plan creates/overwrites spec artifacts, fingerprint check is irrelevant). **loop** → calls `plet_fingerprint.py check` via subprocess; PASS if consistent, FAIL if stale (agents would implement against stale requirements — wasted work). **refine** → calls `plet_fingerprint.py check`; PASS if consistent, WARN if stale (refine is where you fix staleness). Fingerprint script's own errors bubble up as-is. If `plet_fingerprint.py` itself is missing, caught by scripts-installed check. | P0 |
| GSS_PRF_BHV_7 | **git-check**: Calls `plet_git_check.py check-session` via subprocess. Preflight IS a session boundary — CKS was designed for this. FAIL/WARN results from CKS are included in preflight output (each CKS check becomes a preflight check with its original name prefixed: `git:in-progress-operation`, `git:orphaned-worktrees`, etc). Replaces the standalone git-repo check — CKS already checks for git repo internally. If `plet_git_check.py` is missing, caught by scripts-installed. | P0 |
| GSS_PRF_BHV_9 | **scripts-installed**: Verifies key plet scripts exist in `${CLAUDE_SKILL_DIR}/scripts/` (plet_state.py, plet_entries.py, plet_fingerprint.py, plet_trace.py, plet_git_iteration.py, plet_git_ops.py, plet_git_check.py, plet_invoke.py). FAIL if any missing — corrupted installation. | P0 |
| GSS_PRF_BHV_8 | Check order: scripts-installed → git-check (CKS) → claude-md-exists → gitignore-plet → spec-artifacts → state-valid → fingerprints-consistent. Scripts first (can't run anything without them), then git health (CKS), then project-level checks. | P0 |

---

## 4. Edge Cases (GSS_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_EDG_1 | Fresh project (no plet/ directory) — detect returns `plan`, preflight passes on artifact checks (nothing to check). | P0 |
| GSS_EDG_2 | Partial setup (plet/ exists, requirements.md exists, no iterations.md) — detect returns `plan`, preflight FAIL on spec-artifacts if state.json exists (inconsistent state). | P0 |
| GSS_EDG_3 | All iterations `ineligible` (waiting on deps) — detect returns `loop` only if at least one is `queued`/`implementing`/`verifying`. All `ineligible` = not actionable, treat as `refine` (user may need to adjust deps). | P0 |
| GSS_EDG_4 | Mix of `complete` and `withdrawn` only — detect returns `refine` (may need new iterations). | P0 |
| GSS_EDG_5 | State files corrupt — detect and status skip corrupt files with warning, make decisions based on valid files only. | P0 |
| GSS_EDG_6 | `--pretty` without `--output json` — error. | P0 |
| GSS_EDG_7 | `--fields` without `--output json` — error. | P0 |
| GSS_EDG_8 | Duplicate flags — error via `parse_kwargs`. | P0 |
| GSS_EDG_9 | `--dry-run` passed — error (all commands are read-only). | P0 |
| GSS_EDG_10 | ~~`.claude/settings.local.json` bypass-permissions check~~ — Dropped. `plet_invoke.py` uses `claude --enable-auto-mode` for subprocesses. |  |
| GSS_EDG_11 | All iterations `ineligible` only — detect returns `refine`. Circular dependencies or missing upstream work needs human intervention. | P0 |

## 5. Error Handling (GSS_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| GSS_ERR_2 | Global state validation failure → error from `util_state` | P0 |
| GSS_ERR_3 | `plet_dir` not found → `Error: directory not found: {path}` | P0 |
| GSS_ERR_4 | `plet_dir` is a file → `Error: expected a directory, got file: {path}` | P0 |
| GSS_ERR_5 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| GSS_ERR_6 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| GSS_ERR_7 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| GSS_ERR_8 | `--dry-run` passed → `Error: --dry-run is not supported (all commands are read-only)` | P0 |
| GSS_ERR_9 | Invalid `--session-type` → `Error: invalid --session-type '{value}' (valid: detect, plan, loop, refine)` | P0 |

## 6. Formats (GSS_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_FMT_1 | Reads `plet/state.json` via `util_state` for project context. | P0 |
| GSS_FMT_2 | Reads `plet/state/*.json` via `util_state` for iteration lifecycles. | P0 |
| GSS_FMT_3 | Reads `plet/requirements.md`, `plet/iterations.md` for existence checks. | P0 |
| GSS_FMT_4 | Reads `CLAUDE.md`, `.gitignore` for preflight. Calls `plet_git_check.py` and `plet_fingerprint.py` via subprocess. | P0 |
| GSS_FMT_5 | Writes nothing — all commands are read-only. | P0 |

## 7. Agent Flows (GSS_AFL)

### GSS_AFL_1: SKILL.md entry point routing

1. User invokes `/plet`
2. SKILL.md calls: `plet_gate_session.py detect`
3. Result is `plan`, `loop`, or `refine`
4. SKILL.md routes to the appropriate session

### GSS_AFL_2: Orchestrator session start

1. Orchestrator starts
2. `plet_gate_session.py preflight plet/ --session-type loop --output json` — verify environment ready for loop
3. If exit 1 (fail): abort, report issues
4. If exit 2 (warn): log warnings to progress.md, continue
5. `plet_gate_session.py detect plet/` — confirm loop is the right session
6. Proceed with loop

### GSS_AFL_3: GUI dashboard polling

1. GUI polls periodically
2. `plet_gate_session.py status plet/ --output json`
3. GUI updates dashboard with iteration counts, active agents, blockers

### GSS_AFL_4: Human inspection

1. User wants to know project state
2. `plet_gate_session.py status plet/`
3. Formatted summary printed to terminal

## 8. Examples (GSS_EXM)

### GSS_EXM_1: Detect session type

```bash
# Fresh project
plet_gate_session.py detect
# plan

# Active iterations
plet_gate_session.py detect plet/
# loop

# All complete
plet_gate_session.py detect plet/
# refine

# JSON output
plet_gate_session.py detect plet/ --output json --pretty
# {
#   "status": "ok",
#   "command": "detect",
#   "sessionType": "loop",
#   "reason": "3 queued, 1 implementing",
#   "artifacts": {"requirements": true, "iterations": true, "state": true},
#   ...
# }
```

### GSS_EXM_2: Project status

```bash
plet_gate_session.py status plet/
# Project: LOGA (Log Analyzer)
# Session: loop (loop 1)
# Progress: 5/13 (38%)
# Iterations: 13 total
#   complete: 5 | implementing: 1 | verifying: 0 | queued: 3
#   ineligible: 3 | blocked: 1 | withdrawn: 0
# Blockers: ID_008 — OAuth provider sandbox returning 500
# Active agents: ID_004 (implementing, running_checks)
# Fingerprints: consistent
# Milestones:
#   MS_1 (Scaffolding & Core): 3/3 complete
#   MS_2 (API & Frontend): 2/7 complete
#   MS_3 (Polish): 0/3 complete
```

### GSS_EXM_3: Preflight checks

```bash
plet_gate_session.py preflight plet/ --session-type detect
# PASS: preflight — 12 passed
# PASS: scripts-installed — all plet scripts found
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:workstream-exists — plet/LOGA/loop1/workstream exists
# PASS: git:orphaned-worktrees — no orphaned plet worktrees
# PASS: git:orphaned-branches — no plet branches without state files
# PASS: git:no-stashes — stash list empty
# PASS: git:unmerged-complete — all complete iterations merged
# PASS: claude-md-exists — CLAUDE.md found
# PASS: gitignore-plet — .gitignore includes .plet/
# PASS: spec-artifacts — requirements.md and iterations.md exist
# PASS: state-valid — plet/state.json valid
# PASS: fingerprints-consistent — all fingerprints consistent
# 12 checks: 12 passed, 0 failed, 0 warnings
```

### GSS_EXM_4: Preflight on fresh project

```bash
plet_gate_session.py preflight --session-type detect
# WARN: preflight — 1 warning
# PASS: scripts-installed — all plet scripts found
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:workstream-exists — no workstream, no active iterations (ok)
# PASS: git:orphaned-worktrees — no orphaned plet worktrees
# PASS: git:orphaned-branches — no plet branches without state files
# PASS: git:no-stashes — stash list empty
# PASS: git:unmerged-complete — no complete iterations to check
# WARN: claude-md-exists — CLAUDE.md not found
# PASS: gitignore-plet — .gitignore includes .plet/
# PASS: spec-artifacts — no plet directory (fresh project)
# PASS: state-valid — no state.json (fresh project)
# SKIPPED: fingerprints-consistent — plan session, check not applicable
# 12 checks: 10 passed, 0 failed, 1 warning, 1 skipped
```

## 9. Dependencies on Other Scripts (GSS_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GSS_DEP_1 | imports | `util_cli` | `parse_kwargs`, `now_iso`, `dispatch`, `filter_fields` |
| GSS_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
| GSS_DEP_3 | calls (subprocess) | `plet_fingerprint.py` | `check` for fingerprint consistency |
| GSS_DEP_6 | calls (subprocess) | `plet_git_check.py` | `check-session` for git health at preflight |
| GSS_DEP_4 | called by | SKILL.md | routing at `/plet` entry |
| GSS_DEP_5 | called by | `plet_orchestrator.py` | session start preflight + detect |

## 10. Non-Functional Requirements (GSS_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_NFR_1 | detect must be fast (< 500ms) — it's called at every `/plet` invocation. Avoid expensive operations (fingerprint check is in preflight, not detect). | P0 |
| GSS_NFR_2 | status and preflight may take longer (up to 2s) — they scan directories and call subprocesses. | P1 |

## 11. Developer Experience (GSS_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GSS_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| GSS_DXP_2 | IMPORTANT: all commands are read-only — safe to run anytime | P0 |
| GSS_DXP_3 | `detect` text output is bare session type for shell capture (exception to UNV_CMD_15, same pattern as GTI_DXP_3) | P0 |
| GSS_DXP_4 | PITFALLS: all commands default to `plet/` in cwd — run from project root. All three commands use the same input pattern (optional plet_dir). | P0 |
| GSS_DXP_5 | Check names in preflight are stable identifiers: scripts-installed, git:* (CKS checks prefixed), claude-md-exists, gitignore-plet, spec-artifacts, state-valid, fingerprints-consistent | P0 |

## 12. Critical Test Areas (GSS_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GSS_CRT_1 | detect routing logic | Wrong session type → wrong phase entered | Test all OR_2–OR_6 scenarios: fresh, partial, queued, complete, blocked |
| GSS_CRT_2 | detect with ineligible-only | Ineligible triggers loop when it shouldn't | All iterations ineligible → verify returns refine |
| GSS_CRT_3 | status iteration counts | Wrong counts → misleading dashboard | Create known state, verify exact counts |
| GSS_CRT_4 | status blockers listed | Blockers not surfaced | Create blocked iterations, verify listed |
| GSS_CRT_5 | preflight fresh project | Fresh project fails preflight | Run preflight on empty dir, verify passes (no artifacts to check) |
| GSS_CRT_6 | preflight missing CLAUDE.md | Missing CLAUDE.md not caught | Remove CLAUDE.md, verify WARN |
| GSS_CRT_7 | preflight missing spec artifacts | Lost artifacts not caught (FB_16) | Create plet/ with state but no requirements, verify FAIL |
| GSS_CRT_8 | ~~preflight bypass-permissions~~ | Dropped — plet_invoke.py uses `claude --enable-auto-mode`. |  |
| GSS_CRT_9 | preflight exit codes | Wrong exit code for warn vs fail | Verify 0/1/2 mapping |
| GSS_CRT_10 | detect bare output | Extra text breaks shell capture | Verify output is exactly one word |
| GSS_CRT_11 | preflight GTC integration | CKS checks missing from preflight | Run preflight, verify git:* checks appear in output |
| GSS_CRT_12 | preflight fingerprint SKIPPED on plan | Fingerprint check runs unnecessarily on plan | Run preflight --session-type plan, verify fingerprints-consistent is SKIPPED |

## 13. Testing & Verification (GSS_TST)

**What to test:** See §12 Critical Test Areas (GSS_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_gate_session.py`
- Run: `./skills/plet/tests/test_plet_gate_session.py`
- Harness: stdlib-only custom harness per UNV_TST_2.
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- **Fixtures:** tests create temp directories with various combinations of plet artifacts to simulate different project states.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command. detect first, then status, then preflight.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Name: router, session, or something else? | `plet_gate_session.py` — "session" captures all three commands naturally (what session, session status, session ready?). Renamed from `plet_router.py`. |
| 2 | Should detect output `status` as a session type? | No — `status` is a command, not a session type. detect returns `plan`, `loop`, or `refine`. The user can force `/plet status` via the SKILL.md command parsing, not via detect. |
| 3 | Should preflight auto-fix issues (create CLAUDE.md, add .gitignore entry)? | No — preflight is read-only. It diagnoses, the caller fixes. Same principle as GTC (check but don't fix). |
| 4 | Should status call fingerprint check? | Yes but as P1 — it's the most expensive operation. detect deliberately avoids it for speed. |
| 5 | Should preflight check bypassPermissions? | No — dropped. `plet_invoke.py` launches subprocesses with `claude --enable-auto-mode` (see https://claude.com/blog/auto-mode). Project-level permission settings don't affect subprocess invocations. The invoke script owns the permission model. FB_22 resolved by architecture, not by preflight checks. |

## Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | Should SES have a `postflight` command? | GTC `check-session` handles git compliance at session end. But there may be non-git concerns that gate session end: all progress entries written, all emergent items logged, fingerprints re-embedded after refine changes, state.json sessionHistory updated. A SES `postflight` could orchestrate these checks (calling GTC + ENT check + FPR check + state validation) as a single session-end gate. Evaluate during orchestrator spec — the orchestrator is the primary caller of session-end checks. |

## 15. Future Considerations (GSS_FUT)

| ID | Area | Description |
|----|------|-------------|
| GSS_FUT_1 | Bootstrap command | A `bootstrap` command that auto-fixes preflight warnings: creates CLAUDE.md, adds .plet/ to .gitignore, sets up bypassPermissions. Currently left to the caller. |
| GSS_FUT_2 | Health score | A composite health score (0-100) combining preflight, GTC checks, and status into one number for dashboard display. |
| GSS_FUT_3 | Detailed fingerprint diff | Instead of just "consistent/stale", include which artifacts drifted and what IDs changed. Currently deferred to `plet_fingerprint.py check --output json`. |

## 16. FB Items Addressed

- FB_16 — Spec artifacts not preserved. `preflight` checks requirements.md and iterations.md exist when plet directory is present.
- FB_22 — bypassPermissions not configured. Resolved by architecture: `plet_invoke.py` uses `claude --enable-auto-mode` for subprocesses (see https://claude.com/blog/auto-mode). Preflight check dropped — project-level permission settings don't affect subprocess invocations.
- FB_23 — CLAUDE.md missing. `preflight` checks CLAUDE.md exists.
