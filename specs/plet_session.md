# plet_session.py (SES)

> Status: draft

> Renamed from `plet_router.py` (RTR). "Session" captures all three commands: detect (what session am I in?), status (what's the session state?), preflight (is this session ready?).

## 1. Purpose (SES_PUR)

The `/plet` entry point needs to know which phase the project is in, what the current state looks like, and whether the environment is ready for work. These are three distinct questions that the SKILL.md routing logic currently answers via prose interpretation — with drift risk across compaction cycles and session boundaries. This script makes all three answers deterministic.

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PUR_1 | Phase detection from project state. Reads plet artifacts on disk and determines the correct session type (plan, loop, refine). Implements the OR_2–OR_6 routing logic as deterministic code. | P0 |
| SES_PUR_2 | Project status summary. Machine-readable snapshot of iteration counts, lifecycle distribution, blockers, active agents, and fingerprint consistency. Implements OR_12. | P0 |
| SES_PUR_3 | Pre-session environment checks. Verifies the project is ready for plet work: CLAUDE.md exists, .gitignore includes .plet/, bypassPermissions configured, spec artifacts exist, fingerprints consistent. Addresses FB_16, FB_22, FB_23. | P0 |

## 2. Agent Personas (SES_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| SES_AGT_1 | SKILL.md orchestrator | `/plet` entry point routing | `detect` |
| SES_AGT_2 | SKILL.md orchestrator | before entering loop/refine | `preflight` |
| SES_AGT_3 | orchestrator script | session start | `detect`, `preflight` |
| SES_AGT_4 | orchestrator script | between iterations (health check) | `status` |
| SES_AGT_5 | human | manual inspection / debugging | all commands |
| SES_AGT_6 | GUI tool | dashboard state display | `status`, `detect` |

## 3. Commands

Command abbreviations: `DET` (detect), `STA` (status — note: different script from plet_state.py STA prefix), `PRE` (preflight).

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

#### Justification (SES_DET_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_JUS_1 | Why: determines which session type to enter based on project state on disk. The SKILL.md routing logic (OR_2–OR_6) currently runs as prompt-interpreted prose — vulnerable to drift after compaction. This command makes routing deterministic. | P0 |
| SES_DET_JUS_2 | When: called by SKILL.md at `/plet` entry, by the orchestrator script at session start, and by GUI tools for phase display. | P0 |
| SES_DET_JUS_3 | Deprecation signal: only if the orchestrator absorbs routing entirely (unlikely — SKILL.md still needs routing for interactive sessions). | P1 |

#### Definition (SES_DET_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_CMD_1 | Usage: `plet_session.py detect [<plet_dir>] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (SES_DET_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. | P0 |

#### Outputs (SES_DET_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_OUT_1 | Text mode: bare session type to stdout: `plan`, `loop`, `refine`, or `status`. Suitable for shell capture: `SESSION=$(plet_session.py detect)`. Exit 0. | P0 |
| SES_DET_OUT_2 | JSON mode: structured detection result (see schema below). Exit 0. | P0 |
| SES_DET_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

**SES_DET JSON schema (SES_DET_OUT_2):**
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

#### Preconditions (SES_DET_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_PRE_1 | None — detect must work even when plet_dir doesn't exist (that's the "plan" signal). | P0 |

#### Postconditions (SES_DET_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_PST_1 | No files modified | P0 |
| SES_DET_PST_2 | Output is one of: `plan`, `loop`, `refine` | P0 |

#### Behaviors (SES_DET_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DET_BHV_1 | If `plet_dir` doesn't exist or `requirements.md` doesn't exist → `plan` (OR_2) | P0 |
| SES_DET_BHV_2 | If `requirements.md` exists but `iterations.md` or `state.json` missing → `plan` (OR_3) | P0 |
| SES_DET_BHV_3 | If state exists with any iterations in `queued`, `implementing`, or `verifying` → `loop` (OR_4). `ineligible` alone does NOT trigger loop. | P0 |
| SES_DET_BHV_4 | If state exists and all iterations are `complete` → `refine` (OR_5) | P0 |
| SES_DET_BHV_5 | If state exists with `blocked` iterations and none `queued`/`implementing`/`verifying` → `refine` (OR_6) | P0 |
| SES_DET_BHV_6 | Scans `plet/state/*.json` to determine iteration lifecycles. Uses `util_state.load_and_validate_iter_state()` for each. Invalid state files are skipped with warning. | P0 |
| SES_DET_BHV_7 | `reason` field in JSON explains why this session type was chosen (e.g., "3 queued iterations found" or "no plet directory"). | P0 |

---

### 3.2 status (STS)

#### Justification (SES_STS_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_JUS_1 | Why: produces a machine-readable snapshot of project state — iteration counts by lifecycle, blockers, active agents, fingerprint consistency. OR_12 says `/plet status` prints a summary. This command provides the data. | P0 |
| SES_STS_JUS_2 | When: called by the orchestrator between iterations for health checks, by GUI tools for dashboard display, and by humans for manual inspection. | P0 |
| SES_STS_JUS_3 | Deprecation signal: if a richer status dashboard replaces file-based state reading. | P1 |

#### Definition (SES_STS_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_CMD_1 | Usage: `plet_session.py status <global_state_json> <state_dir> [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (SES_STS_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_INP_1 | `global_state_json` — path to `plet/state.json`. | P0 |
| SES_STS_INP_2 | `state_dir` — path to `plet/state/` directory. | P0 |

#### Outputs (SES_STS_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_OUT_1 | Text mode: formatted summary to stdout — project name, session type, iteration counts by lifecycle, blockers listed, active agents listed. Exit 0. | P0 |
| SES_STS_OUT_2 | JSON mode: structured project status (see schema below). Exit 0. | P0 |
| SES_STS_OUT_3 | Error: specific message to stderr, exit 1 | P0 |

**SES_STS JSON schema (SES_STS_OUT_2):**
```json
{
  "status": "ok",
  "command": "status",
  "projectId": "...",
  "projectName": "...",
  "sessionType": "plan|loop|refine",
  "loopSession": N,
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

#### Preconditions (SES_STS_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_PRE_1 | `global_state_json` passes `util_state.load_and_validate_global_state()` | P0 |
| SES_STS_PRE_2 | `state_dir` exists and is a directory | P0 |

#### Postconditions (SES_STS_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_PST_1 | No files modified | P0 |

#### Behaviors (SES_STS_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_STS_BHV_1 | Scans all `*.json` files in `state_dir` (excluding `state.json`). Loads each via `util_state.load_and_validate_iter_state()`. | P0 |
| SES_STS_BHV_2 | Counts iterations by lifecycle: ineligible, queued, implementing, verifying, complete, blocked, withdrawn. | P0 |
| SES_STS_BHV_3 | Lists blocked iterations with their IDs and titles. | P0 |
| SES_STS_BHV_4 | Lists active agents (iterations where `agentId` is not null) with iteration ID and activity. | P0 |
| SES_STS_BHV_5 | Calls `detect` logic internally to include `sessionType` in output. | P0 |
| SES_STS_BHV_6 | Checks fingerprint consistency by calling `plet_fingerprint.py check` via subprocess. Reports `consistent: true/false`. If fingerprint check fails (missing files), reports `consistent: null` with detail. | P1 |
| SES_STS_BHV_7 | Invalid state files are counted and reported as warnings. | P0 |

---

### 3.3 preflight (PRF)

#### Justification (SES_PRF_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_JUS_1 | Why: verifies the project environment is ready for plet work. FB_16 (spec artifacts lost), FB_22 (bypassPermissions not configured), FB_23 (CLAUDE.md missing) all showed that plet assumed a ready environment but didn't check. This command checks. | P0 |
| SES_PRF_JUS_2 | When: called before entering any session (plan, loop, refine). The orchestrator and SKILL.md both run preflight before doing work. | P0 |
| SES_PRF_JUS_3 | Deprecation signal: if project setup becomes fully automated (unlikely — some checks are environment-specific). | P1 |

#### Definition (SES_PRF_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_CMD_1 | Usage: `plet_session.py preflight [<plet_dir>] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (SES_PRF_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/` in current working directory. Used to locate state files and spec artifacts. | P0 |

#### Outputs (SES_PRF_OUT)

Same output model as GTC: a list of checks with pass/fail/warn statuses.

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_OUT_1 | Text mode: title line `PASS/WARN/FAIL: preflight — {summary}`, then one line per check, then summary line. | P0 |
| SES_PRF_OUT_2 | JSON mode: structured preflight results (see schema below). Same output model as GTC. | P0 |
| SES_PRF_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). Same as GTC. | P0 |
| SES_PRF_OUT_4 | Error: specific message to stderr, exit 1 | P0 |

**SES_PRF JSON schema (SES_PRF_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "preflight",
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

**Exit codes:** 0 = all pass (`"ok"`), 1 = any fail (`"fail"`), 2 = warn only (`"warn"`).

#### Preconditions (SES_PRF_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_PRE_1 | None — preflight must work even on a fresh project with no plet directory. Missing artifacts are reported as check results, not precondition errors. | P0 |

#### Postconditions (SES_PRF_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_PST_1 | No files modified | P0 |
| SES_PRF_PST_2 | All checks run — no short-circuit on first failure | P0 |

#### Behaviors (SES_PRF_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_PRF_BHV_1 | **claude-md-exists**: Checks `CLAUDE.md` exists in project root. WARN if missing (FB_23). plet works without it but institutional memory is lost. | P0 |
| SES_PRF_BHV_2 | **gitignore-plet**: Checks `.gitignore` includes `.plet/` or `.plet`. WARN if missing. `.plet/` is local working state (worktrees, caches) — shouldn't be committed. | P0 |
| SES_PRF_BHV_3 | **bypass-permissions**: Checks `.claude/settings.local.json` exists and contains `bypassPermissions` (FB_22). WARN if not configured. Autonomous agents can't run without it. | P0 |
| SES_PRF_BHV_4 | **spec-artifacts**: If `plet_dir` exists, checks `requirements.md` and `iterations.md` exist. FAIL if plet_dir exists but spec artifacts are missing (FB_16 — lost artifacts make the project unresumable). PASS if plet_dir doesn't exist (fresh project, plan will create them). | P0 |
| SES_PRF_BHV_5 | **state-valid**: If `plet/state.json` exists, validates it via `util_state.load_and_validate_global_state()`. FAIL if invalid. PASS if doesn't exist (fresh project). | P0 |
| SES_PRF_BHV_6 | **fingerprints-consistent**: If all three plan artifacts exist, calls `plet_fingerprint.py check` via subprocess. WARN if stale (drift detected but not blocking). PASS if consistent. PASS if artifacts don't exist yet (fresh project). | P1 |
| SES_PRF_BHV_7 | **git-repo**: Checks current directory is inside a git repository. FAIL if not — plet requires git for branch management. | P0 |
| SES_PRF_BHV_8 | Check order: git-repo → claude-md-exists → gitignore-plet → bypass-permissions → spec-artifacts → state-valid → fingerprints-consistent. Environment checks first, then artifact checks. | P0 |

---

## 4. Edge Cases (SES_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_EDG_1 | Fresh project (no plet/ directory) — detect returns `plan`, preflight passes on artifact checks (nothing to check). | P0 |
| SES_EDG_2 | Partial setup (plet/ exists, requirements.md exists, no iterations.md) — detect returns `plan`, preflight FAIL on spec-artifacts if state.json exists (inconsistent state). | P0 |
| SES_EDG_3 | All iterations `ineligible` (waiting on deps) — detect returns `loop` only if at least one is `queued`/`implementing`/`verifying`. All `ineligible` = not actionable, treat as `refine` (user may need to adjust deps). | P0 |
| SES_EDG_4 | Mix of `complete` and `withdrawn` only — detect returns `refine` (may need new iterations). | P0 |
| SES_EDG_5 | State files corrupt — detect and status skip corrupt files with warning, make decisions based on valid files only. | P0 |
| SES_EDG_6 | `--pretty` without `--output json` — error. | P0 |
| SES_EDG_7 | `--fields` without `--output json` — error. | P0 |
| SES_EDG_8 | Duplicate flags — error via `parse_kwargs`. | P0 |
| SES_EDG_9 | `--dry-run` passed — error (all commands are read-only). | P0 |
| SES_EDG_10 | `.claude/settings.local.json` exists but doesn't contain `bypassPermissions` — WARN (may be intentionally not set for non-autonomous use). | P0 |
| SES_EDG_11 | All iterations `ineligible` only — detect returns `refine`. Circular dependencies or missing upstream work needs human intervention. | P0 |

## 5. Error Handling (SES_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_ERR_1 | Missing required args → print specific missing arg name + help text, exit 1 | P0 |
| SES_ERR_2 | Global state validation failure → error from `util_state` | P0 |
| SES_ERR_3 | `state_dir` not found → `Error: directory not found: {path}` | P0 |
| SES_ERR_4 | `state_dir` is a file → `Error: expected a directory, got file: {path}` | P0 |
| SES_ERR_5 | `--pretty` without `--output json` → `Error: --pretty requires --output json` | P0 |
| SES_ERR_6 | `--fields` without `--output json` → `Error: --fields requires --output json` | P0 |
| SES_ERR_7 | Duplicate flag → `Error: --{flag} specified more than once` | P0 |
| SES_ERR_8 | `--dry-run` passed → `Error: --dry-run is not supported (all commands are read-only)` | P0 |

## 6. Formats (SES_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_FMT_1 | Reads `plet/state.json` via `util_state` for project context. | P0 |
| SES_FMT_2 | Reads `plet/state/*.json` via `util_state` for iteration lifecycles. | P0 |
| SES_FMT_3 | Reads `plet/requirements.md`, `plet/iterations.md` for existence checks. | P0 |
| SES_FMT_4 | Reads `CLAUDE.md`, `.gitignore`, `.claude/settings.local.json` for preflight. | P0 |
| SES_FMT_5 | Writes nothing — all commands are read-only. | P0 |

## 7. Agent Flows (SES_AFL)

### SES_AFL_1: SKILL.md entry point routing

1. User invokes `/plet`
2. SKILL.md calls: `plet_session.py detect`
3. Result is `plan`, `loop`, or `refine`
4. SKILL.md routes to the appropriate session

### SES_AFL_2: Orchestrator session start

1. Orchestrator starts
2. `plet_session.py preflight plet/ --output json` — verify environment ready
3. If exit 1 (fail): abort, report issues
4. If exit 2 (warn): log warnings to progress.md, continue
5. `plet_session.py detect plet/` — confirm loop is the right session
6. Proceed with loop

### SES_AFL_3: GUI dashboard polling

1. GUI polls periodically
2. `plet_session.py status plet/state.json plet/state/ --output json`
3. GUI updates dashboard with iteration counts, active agents, blockers

### SES_AFL_4: Human inspection

1. User wants to know project state
2. `plet_session.py status plet/state.json plet/state/`
3. Formatted summary printed to terminal

## 8. Examples (SES_EXM)

### SES_EXM_1: Detect session type

```bash
# Fresh project
plet_session.py detect
# plan

# Active iterations
plet_session.py detect plet/
# loop

# All complete
plet_session.py detect plet/
# refine

# JSON output
plet_session.py detect plet/ --output json --pretty
# {
#   "status": "ok",
#   "command": "detect",
#   "sessionType": "loop",
#   "reason": "3 queued, 1 implementing",
#   "artifacts": {"requirements": true, "iterations": true, "state": true},
#   ...
# }
```

### SES_EXM_2: Project status

```bash
plet_session.py status plet/state.json plet/state/
# Project: LOGA (Log Analyzer)
# Session: loop (loop 1)
# Iterations: 13 total
#   complete: 5 | implementing: 1 | verifying: 0 | queued: 3
#   ineligible: 3 | blocked: 1 | withdrawn: 0
# Blockers: ID_008 — OAuth provider sandbox returning 500
# Active agents: ID_004 (implementing, running_checks)
# Fingerprints: consistent
```

### SES_EXM_3: Preflight checks

```bash
plet_session.py preflight plet/
# PASS: preflight — 7 passed
# PASS: git-repo — inside a git repository
# PASS: claude-md-exists — CLAUDE.md found
# PASS: gitignore-plet — .gitignore includes .plet/
# WARN: bypass-permissions — .claude/settings.local.json not found
# PASS: spec-artifacts — requirements.md and iterations.md exist
# PASS: state-valid — plet/state.json valid
# PASS: fingerprints-consistent — all fingerprints consistent
# 7 checks: 6 passed, 0 failed, 1 warnings
```

### SES_EXM_4: Preflight on fresh project

```bash
plet_session.py preflight
# WARN: preflight — 2 warnings
# PASS: git-repo — inside a git repository
# WARN: claude-md-exists — CLAUDE.md not found
# PASS: gitignore-plet — .gitignore includes .plet/
# WARN: bypass-permissions — .claude/settings.local.json not found
# PASS: spec-artifacts — no plet directory (fresh project)
# PASS: state-valid — no state.json (fresh project)
# PASS: fingerprints-consistent — no artifacts to check
# 7 checks: 5 passed, 0 failed, 2 warnings
```

## 9. Dependencies on Other Scripts (SES_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| SES_DEP_1 | imports | `util_cli` | `parse_kwargs`, `now_iso`, `dispatch`, `filter_fields` |
| SES_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
| SES_DEP_3 | calls (subprocess) | `plet_fingerprint.py` | `check` for fingerprint consistency |
| SES_DEP_4 | called by | SKILL.md | routing at `/plet` entry |
| SES_DEP_5 | called by | `plet_orchestrator.py` | session start preflight + detect |

## 10. Non-Functional Requirements (SES_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_NFR_1 | detect must be fast (< 500ms) — it's called at every `/plet` invocation. Avoid expensive operations (fingerprint check is in preflight, not detect). | P0 |
| SES_NFR_2 | status and preflight may take longer (up to 2s) — they scan directories and call subprocesses. | P1 |

## 11. Developer Experience (SES_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| SES_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| SES_DXP_2 | IMPORTANT: all commands are read-only — safe to run anytime | P0 |
| SES_DXP_3 | `detect` text output is bare session type for shell capture (exception to UNV_CMD_15, same pattern as GTI_DXP_3) | P0 |
| SES_DXP_4 | PITFALLS: detect defaults to `plet/` in cwd — run from project root. status needs both global state AND state dir paths. | P0 |
| SES_DXP_5 | Check names in preflight are stable identifiers (git-repo, claude-md-exists, gitignore-plet, bypass-permissions, spec-artifacts, state-valid, fingerprints-consistent) | P0 |

## 12. Critical Test Areas (SES_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| SES_CRT_1 | detect routing logic | Wrong session type → wrong phase entered | Test all OR_2–OR_6 scenarios: fresh, partial, queued, complete, blocked |
| SES_CRT_2 | detect with ineligible-only | Ineligible triggers loop when it shouldn't | All iterations ineligible → verify returns refine |
| SES_CRT_3 | status iteration counts | Wrong counts → misleading dashboard | Create known state, verify exact counts |
| SES_CRT_4 | status blockers listed | Blockers not surfaced | Create blocked iterations, verify listed |
| SES_CRT_5 | preflight fresh project | Fresh project fails preflight | Run preflight on empty dir, verify passes (no artifacts to check) |
| SES_CRT_6 | preflight missing CLAUDE.md | Missing CLAUDE.md not caught | Remove CLAUDE.md, verify WARN |
| SES_CRT_7 | preflight missing spec artifacts | Lost artifacts not caught (FB_16) | Create plet/ with state but no requirements, verify FAIL |
| SES_CRT_8 | preflight bypass-permissions | Missing config not caught (FB_22) | No .claude/ dir, verify WARN |
| SES_CRT_9 | preflight exit codes | Wrong exit code for warn vs fail | Verify 0/1/2 mapping |
| SES_CRT_10 | detect bare output | Extra text breaks shell capture | Verify output is exactly one word |

## 13. Testing & Verification (SES_TST)

**What to test:** See §12 Critical Test Areas (SES_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_session.py`
- Run: `python3 skills/plet/tests/test_plet_session.py`
- Harness: stdlib-only custom harness per UNV_TST_2.
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- **Fixtures:** tests create temp directories with various combinations of plet artifacts to simulate different project states.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command. detect first, then status, then preflight.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Name: router, session, or something else? | `plet_session.py` — "session" captures all three commands naturally (what session, session status, session ready?). Renamed from `plet_router.py`. |
| 2 | Should detect output `status` as a session type? | No — `status` is a command, not a session type. detect returns `plan`, `loop`, or `refine`. The user can force `/plet status` via the SKILL.md command parsing, not via detect. |
| 3 | Should preflight auto-fix issues (create CLAUDE.md, add .gitignore entry)? | No — preflight is read-only. It diagnoses, the caller fixes. Same principle as GTC (check but don't fix). |
| 4 | Should status call fingerprint check? | Yes but as P1 — it's the most expensive operation. detect deliberately avoids it for speed. |

## Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | Should SES have a `postflight` command? | GTC `check-session` handles git compliance at session end. But there may be non-git concerns that gate session end: all progress entries written, all emergent items logged, fingerprints re-embedded after refine changes, state.json sessionHistory updated. A SES `postflight` could orchestrate these checks (calling GTC + ENT check + FPR check + state validation) as a single session-end gate. Evaluate during orchestrator spec — the orchestrator is the primary caller of session-end checks. |

## 15. Future Considerations (SES_FUT)

| ID | Area | Description |
|----|------|-------------|
| SES_FUT_1 | Bootstrap command | A `bootstrap` command that auto-fixes preflight warnings: creates CLAUDE.md, adds .plet/ to .gitignore, sets up bypassPermissions. Currently left to the caller. |
| SES_FUT_2 | Health score | A composite health score (0-100) combining preflight, GTC checks, and status into one number for dashboard display. |
| SES_FUT_3 | Detailed fingerprint diff | Instead of just "consistent/stale", include which artifacts drifted and what IDs changed. Currently deferred to `plet_fingerprint.py check --output json`. |

## 16. FB Items Addressed

- FB_16 — Spec artifacts not preserved. `preflight` checks requirements.md and iterations.md exist when plet directory is present.
- FB_22 — bypassPermissions not configured. `preflight` checks .claude/settings.local.json.
- FB_23 — CLAUDE.md missing. `preflight` checks CLAUDE.md exists.
