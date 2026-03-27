# plet_gate_verify.py (GVR)

> Status: **superseded** by `plet_gate_phase.md` (GPH). Kept as historical reference for reviewed decisions.

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*. A table row should be self-contained enough to verify independently, but the surrounding prose provides the understanding needed to write and review it well.

## 1. Purpose (GVR_PUR)

Gate script for the verify phase. Same architecture as GIM (implement gate) — pre/post checks, subagent self-correction, pass/fail/warn verdict. The verify subagent runs `post` before exiting and self-corrects until it passes.

**Simpler than GIM:** Pre-gate only checks git and state (no fingerprints, no spec-artifacts — those can't change mid-session). Post-gate is identical to GIM: git, state, entries, trace.

**Same FB motivation:** FB_29 (learnings/emergent not written), FB_33 (progress entries incomplete), FB_11 (trace files missing). Verify phase had the same compliance gaps as implement.

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PUR_1 | Pre-verify gate: verifies git state, state file validity, and lifecycle before the verify subagent starts. Simpler than GIM pre — no fingerprint or spec-artifact checks. | P0 |
| GVR_PUR_2 | Post-verify gate: verifies git state, state file validity, and mandatory runtime artifact entries after verify finishes. Identical checks to GIM post. Addresses FB_29, FB_33, FB_11. | P0 |
| GVR_PUR_3 | Delegates to existing tools — GTC (git), STA (state), ENT (entries). Same delegation pattern as GIM. | P0 |

## 2. Agent Personas (GVR_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GVR_AGT_1 | orchestrator script | before spawning verify subagent | `pre` |
| GVR_AGT_2 | verify subagent | before exiting — self-corrects until post passes | `post` |
| GVR_AGT_3 | orchestrator script | optional re-verification after subagent exits | `post` |
| GVR_AGT_4 | human | manual debugging / phase boundary inspection | both commands |
| GVR_AGT_5 | GUI tool | phase transition monitoring | both commands |
| GVR_AGT_6 | case study / audit agent | post-run analysis | both commands |

## 3. Commands

Command abbreviations: `PRE` (pre), `PST` (post).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output |
| `--pretty` | all commands | Indent JSON (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON fields (requires `--output json`) |

Both commands are read-only — `--dry-run` is NOT applicable.

**JSON error behavior:** Per UNV_ERR_4.

---

### 3.1 pre (PRE)

#### Justification (GVR_PRE_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_JUS_1 | Why: verifies git and state are clean before verify starts. Simpler than GIM pre — no fingerprints (can't change during verify), no spec-artifacts (GIM pre already checked). | P0 |
| GVR_PRE_JUS_2 | When: called by orchestrator before spawning verify subagent. | P0 |
| GVR_PRE_JUS_3 | Deprecation signal: only if orchestrator inlines all pre-checks. | P1 |

#### Definition (GVR_PRE_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_CMD_1 | Usage: `plet_gate_verify.py pre [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic

**Concurrency:** safe — read-only

#### Inputs (GVR_PRE_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. | P0 |
| GVR_PRE_INP_2 | `--iter-id` — iteration ID. Required. | P0 |

#### Outputs (GVR_PRE_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_OUT_1 | Text mode: title line `PASS/WARN/FAIL: pre — {summary}`, per-check lines, summary line. | P0 |
| GVR_PRE_OUT_2 | JSON mode: structured gate results (see schema below). | P0 |
| GVR_PRE_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). | P0 |
| GVR_PRE_OUT_4 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**GVR_PRE JSON schema (GVR_PRE_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "pre",
  "iterationId": "...",
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (GVR_PRE_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_PRE_1 | `--iter-id` present | P0 |
| GVR_PRE_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GVR_PRE_PRE_3 | `plet_dir/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GVR_PRE_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GVR_PRE_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_PST_1 | No files modified | P0 |
| GVR_PRE_PST_2 | All checks run — no early termination on first failure | P0 |
| GVR_PRE_PST_3 | Exit code reflects overall result: 0/1/2 | P0 |

#### Behaviors (GVR_PRE_BHV)

Simpler than GIM pre — only git and state, plus lifecycle check.

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PRE_BHV_1 | **git-check**: Calls `plet_git_check.py check-iteration <plet_dir> --iter-id <iter_id> --phase verify --output json`. Each GTC check prefixed with `git:`. | P0 |
| GVR_PRE_BHV_2 | **state-valid**: Calls `plet_state.py validate` on iter state. PASS if valid, FAIL if invalid. | P0 |
| GVR_PRE_BHV_3 | **lifecycle-check**: Reads lifecycle from iter state. WARN if not `verifying`. Catches orchestrator bugs (e.g., running verify on a queued/complete/implementing iteration — orchestrator should have transitioned to verifying before spawning verify). | P0 |
| GVR_PRE_BHV_4 | Check order: git-check → state-valid → lifecycle-check. | P0 |

---

### 3.2 post (PST)

#### Justification (GVR_PST_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_JUS_1 | Why: enforces mandatory artifact completeness after verify finishes. Same motivation as GIM post (FB_29, FB_33, FB_11). | P0 |
| GVR_PST_JUS_2 | When: called by verify subagent before exiting. Self-corrects until passes. | P0 |
| GVR_PST_JUS_3 | Deprecation signal: only if mandatory entry rules are removed. | P1 |

#### Definition (GVR_PST_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_CMD_1 | Usage: `plet_gate_verify.py post [<plet_dir>] --iter-id ID_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic

**Concurrency:** safe — read-only

#### Inputs (GVR_PST_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. | P0 |
| GVR_PST_INP_2 | `--iter-id` — iteration ID. Required. | P0 |

#### Outputs (GVR_PST_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_OUT_1 | Text mode: title line, per-check lines, summary line. | P0 |
| GVR_PST_OUT_2 | JSON mode: structured gate results (see schema below). | P0 |
| GVR_PST_OUT_3 | Exit codes: 0/1/2. | P0 |
| GVR_PST_OUT_4 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**GVR_PST JSON schema (GVR_PST_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "post",
  "iterationId": "...",
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (GVR_PST_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_PRE_1 | `--iter-id` present | P0 |
| GVR_PST_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GVR_PST_PRE_3 | `plet_dir/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GVR_PST_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GVR_PST_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_PST_1 | No files modified | P0 |
| GVR_PST_PST_2 | All checks run — no early termination on first failure | P0 |
| GVR_PST_PST_3 | Exit code reflects overall result: 0/1/2 | P0 |

#### Behaviors (GVR_PST_BHV)

Identical checks to GIM post — git, state, entries, trace. Phase is `verify` instead of `implement`.

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_PST_BHV_1 | **git-check**: Calls GTC `check-iteration <plet_dir> --iter-id <iter_id> --phase verify`. | P0 |
| GVR_PST_BHV_2 | **state-valid**: Re-validates iter state after subagent may have modified it. | P0 |
| GVR_PST_BHV_3 | **progress-entry**: FAIL if progress count is 0. Verify must produce at least one progress entry. | P0 |
| GVR_PST_BHV_4 | **learnings-entry**: WARN if learnings count is 0. | P0 |
| GVR_PST_BHV_5 | **emergent-entry**: WARN if emergent count is 0. Same actionable guidance as GIM. | P0 |
| GVR_PST_BHV_6 | **trace-events**: Checks `plet/trace/{iter_id}-verify-{attempt}-events.ndjson` exists, is non-empty, and passes `plet_trace.py validate` via subprocess. WARN if missing, empty, or invalid NDJSON. Catches both completely missing traces and corrupt trace files (silent data loss). | P0 |
| GVR_PST_BHV_9 | **last-verdict**: Reads `lastVerdict` from iter state. FAIL if null — the orchestrator needs the verdict to decide next steps (merge-squash, cycle-back, or block). | P0 |
| GVR_PST_BHV_10 | **verification-report**: Reads `verificationReports` from iter state. FAIL if array is empty or last entry missing required fields (`verdict`, `criteriaResults`). The report is the structured output of verify — without it, post-run analysis loses per-criterion detail. Subagent must go back and write it. | P0 |
| GVR_PST_BHV_7 | Check order: git-check → state-valid → progress-entry → learnings-entry → emergent-entry → trace-events → last-verdict → verification-report. | P0 |
| GVR_PST_BHV_8 | ENT check called once, three check results extracted. | P0 |

---

## 4. Edge Cases (GVR_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_EDG_1 | Not inside a git repo — error before any checks. | P0 |
| GVR_EDG_2 | GTC script missing — FAIL on git-check. | P0 |
| GVR_EDG_3 | STA validate script missing — FAIL on state-valid. | P0 |
| GVR_EDG_4 | ENT check script missing — FAIL on progress-entry. | P0 |
| GVR_EDG_5 | Subprocess returns non-JSON — FAIL with "could not parse output". | P0 |
| GVR_EDG_6 | Retry attempt (attempt > 1) — same checks apply. | P0 |
| GVR_EDG_7 | `--pretty` without `--output json` — error. | P0 |
| GVR_EDG_8 | `--fields` without `--output json` — error. | P0 |
| GVR_EDG_9 | `--dry-run` passed — error. | P0 |
| GVR_EDG_10 | `plet_dir` is a file — error. | P0 |
| GVR_EDG_11 | Iter state not found — error. | P0 |

## 5. Error Handling (GVR_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_ERR_1 | Missing `--iter-id` → error + help text, exit 1 | P0 |
| GVR_ERR_2 | `plet_dir` not found → `Error: directory not found: {path}` | P0 |
| GVR_ERR_3 | `plet_dir` is a file → `Error: expected a directory, got file: {path}` | P0 |
| GVR_ERR_4 | Global state validation failure → error from `util_state` | P0 |
| GVR_ERR_5 | Iter state validation failure → error from `util_state` | P0 |
| GVR_ERR_6 | Not a git repo → `Error: not inside a git repository` | P0 |
| GVR_ERR_7 | `--pretty` without `--output json` → error | P0 |
| GVR_ERR_8 | `--fields` without `--output json` → error | P0 |
| GVR_ERR_9 | `--dry-run` passed → error | P0 |

## 6. Formats (GVR_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_FMT_1 | Reads `{plet_dir}/state.json` via `util_state`. | P0 |
| GVR_FMT_2 | Reads `{plet_dir}/state/{iter_id}.json` via `util_state`. | P0 |
| GVR_FMT_3 | Reads runtime artifacts indirectly via `plet_entries.py check`. | P0 |
| GVR_FMT_4 | Writes nothing — read-only. | P0 |

## 7. Agent Flows (GVR_AFL)

### GVR_AFL_1: Normal verify phase

1. Orchestrator prepares iteration for verification
2. Orchestrator calls: `plet_gate_verify.py pre plet/ --iter-id ID_001 --output json`
3. If exit 1 (fail): abort, report issues
4. If exit 2 (warn): log warnings, continue
5. Orchestrator spawns verify subagent
6. Verify subagent does its work (criterion checks, code review, testing)
7. **Subagent** calls: `plet_gate_verify.py post plet/ --iter-id ID_001 --output json`
8. If exit 1 (fail): subagent self-corrects and re-runs post
9. Subagent repeats 7-8 until post-gate passes
10. Subagent exits — its exit signals "post-gate passed"
11. Orchestrator optionally re-runs post
12. Orchestrator proceeds (merge-squash if complete, cycle-back if rejected)

### GVR_AFL_2: Subagent self-correction loop

1. Subagent finishes verification
2. Runs post-gate → FAIL (missing progress entry)
3. Subagent writes progress entry
4. Runs post-gate → WARN (missing learnings)
5. Subagent writes learnings entry
6. Runs post-gate → PASS
7. Subagent exits cleanly

## 8. Examples (GVR_EXM)

### GVR_EXM_1: Pre-gate — all passing

```bash
plet_gate_verify.py pre plet/ --iter-id ID_001
# OK: pre — 8 passed
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:branch-exists — plet/LOGA/loop1/ID_001 exists
# PASS: git:correct-branch — on plet/LOGA/loop1/ID_001
# PASS: git:clean-worktree — no uncommitted changes
# PASS: git:linear-history — no merge commits since workstream divergence
# PASS: git:no-stashes — stash list empty
# PASS: state-valid — ID_001.json valid
# PASS: lifecycle-check — lifecycle is verifying
# 8 checks: 8 passed, 0 failed, 0 warnings
```

### GVR_EXM_2: Post-gate — missing progress entry

```bash
plet_gate_verify.py post plet/ --iter-id ID_001
# FAIL: post — 2 failed, 3 warnings
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:branch-exists — plet/LOGA/loop1/ID_001 exists
# PASS: git:correct-branch — on plet/LOGA/loop1/ID_001
# PASS: git:clean-worktree — no uncommitted changes
# PASS: git:linear-history — no merge commits since workstream divergence
# PASS: git:no-stashes — stash list empty
# PASS: state-valid — ID_001.json valid
# FAIL: progress-entry — 0 progress entries for ID_001
# WARN: learnings-entry — 0 learnings entries for ID_001
# WARN: emergent-entry — 0 emergent entries for ID_001
# WARN: trace-events — no trace events file for ID_001 verify-1
# FAIL: last-verdict — lastVerdict is null
# FAIL: verification-report — verificationReports is empty
# 13 checks: 7 passed, 3 failed, 3 warnings
```

### GVR_EXM_3: Post-gate — JSON output

```bash
plet_gate_verify.py post plet/ --iter-id ID_001 --output json --pretty
# {
#   "status": "fail",
#   "command": "post",
#   "iterationId": "ID_001",
#   "checks": [
#     {"name": "git:in-progress-operation", "status": "pass", "detail": "..."},
#     ...
#     {"name": "progress-entry", "status": "fail", "detail": "0 progress entries for ID_001"},
#     {"name": "learnings-entry", "status": "warn", "detail": "0 learnings entries for ID_001"},
#     {"name": "emergent-entry", "status": "warn", "detail": "0 emergent entries for ID_001"},
#     {"name": "trace-events", "status": "warn", "detail": "no trace events file for ID_001 verify-1"},
#     {"name": "last-verdict", "status": "fail", "detail": "lastVerdict is null"},
#     {"name": "verification-report", "status": "fail", "detail": "verificationReports is empty"}
#   ],
#   "summary": {"total": 13, "passed": 7, "failed": 3, "warnings": 3},
#   ...
# }
```

## 9. Dependencies on Other Scripts (GVR_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GVR_DEP_1 | imports | `util_cli` | `parse_kwargs`, `now_iso`, `dispatch`, shared helpers |
| GVR_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
| GVR_DEP_3 | calls (subprocess) | `plet_git_check.py` | `check-iteration --phase verify` |
| GVR_DEP_4 | calls (subprocess) | `plet_state.py` | `validate` for state schema |
| GVR_DEP_5 | calls (subprocess) | `plet_entries.py` | `check` for entry verification (post only) |
| GVR_DEP_7 | calls (subprocess) | `plet_trace.py` | `validate` for trace validation (post only) |
| GVR_DEP_6 | called by | `plet_orchestrator.py` | pre/post verify phase |

## 10. Non-Functional Requirements (GVR_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_NFR_1 | Subprocess calls use `--output json`. Text fallback if JSON parse fails. | P0 |
| GVR_NFR_2 | Gate must complete within 5 seconds. | P1 |

## 11. Developer Experience (GVR_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GVR_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure | P0 |
| GVR_DXP_2 | IMPORTANT: both commands are read-only — safe to run anytime | P0 |
| GVR_DXP_3 | PITFALLS: --iter-id required. Defaults to plet/ in cwd. | P0 |
| GVR_DXP_4 | Check names are stable identifiers: `git:*`, `state-valid`, `lifecycle-check`, `progress-entry`, `learnings-entry`, `emergent-entry`, `trace-events`, `last-verdict`, `verification-report` | P0 |

## 12. Critical Test Areas (GVR_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GVR_CRT_1 | Pre-gate passes on clean state | Gate blocks valid verifications | Create valid state + git repo, verify exit 0 |
| GVR_CRT_2 | Pre-gate fails on invalid state | Invalid state not caught | Create invalid state, verify exit 1 |
| GVR_CRT_3 | Post-gate fails on missing progress | Missing entries not caught (FB_33) | No progress entry, verify exit 1 |
| GVR_CRT_4 | Post-gate warns on missing learnings | Missing learnings not surfaced | No learnings, verify exit 2 |
| GVR_CRT_5 | Post-gate passes with all entries | Complete iteration blocked | All entries present, verify exit 0 |
| GVR_CRT_6 | GTC integration | Git checks missing | Verify git:* checks in output |
| GVR_CRT_7 | ENT check integration | Entry results not parsed | Verify progress/learnings/emergent checks |
| GVR_CRT_8 | Exit code correctness | Wrong signal | Verify 0/1/2 mapping |
| GVR_CRT_9 | JSON output parseable | Can't parse results | Verify valid JSON |
| GVR_CRT_10 | Trace events | Missing trace not surfaced | No trace file, verify WARN |
| GVR_CRT_11 | Lifecycle WARN | Wrong lifecycle not surfaced | Lifecycle=complete, verify WARN |
| GVR_CRT_12 | last-verdict null | Null verdict not caught | No verdict set, verify FAIL |
| GVR_CRT_13 | last-verdict set | Valid verdict blocked | Set lastVerdict, verify PASS |
| GVR_CRT_14 | verification-report empty | Missing report not caught | Empty verificationReports, verify FAIL |
| GVR_CRT_15 | verification-report present | Valid report blocked | Add report with verdict+criteriaResults, verify PASS |

## 13. Testing & Verification (GVR_TST)

**What to test:** See §12.

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_gate_verify.py`
- Harness: stdlib-only, subprocess calls
- Fixtures: temp git repos + state files + runtime artifacts
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8

**Implementation discipline:** Red/green, pre first, post second. GVR shares most helper functions with GIM — extract shared gate utilities if duplication is high.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Should GVR pre check spec-artifacts? | No. GIM pre already checked. Spec artifacts can't disappear mid-session. |
| 2 | Should GVR pre check fingerprints? | No. Verify can't change requirements. Fingerprint drift is irrelevant during verify. |
| 3 | Should GVR pre check lifecycle? | Yes — WARN if not `verifying`. The orchestrator must transition to `verifying` before spawning verify. `implementing` is GIM's valid state, not GVR's. |
| 4 | Should GVR share code with GIM? | Yes — extract to `util_gate_phase.py` during GVR implementation. Shared functions: run_gtc_checks, run_sta_validate, run_ent_check, check_trace_events, summarize_checks, format_text_output. GIM retrofitted to import from shared module. |
| 5 | Should post-gate check verificationReports? | Yes — both `lastVerdict` (FAIL if null, BHV_9) AND full report (FAIL if empty/missing fields, BHV_10). The report is the structured output of verify. Subagent must self-correct if missing. Promoted from GVR_FUT_2. |

### Open Questions

*(None)*

## 15. Future Considerations (GVR_FUT)

| ID | Area | Description |
|----|------|-------------|
| ~~GVR_FUT_1~~ | ~~Trace validation~~ | Promoted to GVR_PST_BHV_6. Existence + TRC validate, WARN if invalid. |
| ~~GVR_FUT_2~~ | ~~Full verification report check~~ | Promoted to GVR_PST_BHV_10. FAIL if verificationReports empty or missing required fields. |
| ~~GVR_FUT_3~~ | ~~Shared gate library~~ | Promoted to RQ_4 / implementation plan. Extract to `util_gate_phase.py` during GVR implementation. GIM retrofitted. |

## 16. FB Items Addressed

- FB_29 — Learnings/emergent not written. Post-gate WARNs if count is 0.
- FB_33 — Progress entries incomplete. Post-gate FAILs if count is 0.
- FB_11 — Trace files missing. Post-gate WARNs if trace events file missing/empty.
