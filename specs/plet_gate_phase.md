# plet_gate_phase.py (GPH)

> Status: draft

> Merged from `plet_gate_impl.py` (GIM) and `plet_gate_verify.py` (GVR). One script, `--phase` controls behavior differences.

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*. A table row should be self-contained enough to verify independently, but the surrounding prose provides the understanding needed to write and review it well.

## 1. Purpose (GPH_PUR)

Phase gate script for the implement and verify phases. The primary purpose is to give the orchestrator, subagent, or subprocess a clear signal: **you're not done yet — clean up or block.** Runs pre and post each phase, enforcing compliance checks and mandatory artifact completeness. The subagent runs `post` before exiting and self-corrects until it passes — its exit means "I passed my own gate."

Case study evidence: SPARK produced 0.09 learnings and 0.04 emergent entries per iteration despite a prose mandate (FB_29). Only 6 of 23 iterations had explicit progress entries (FB_33). Trace files were missing (FB_11). Prose rules failed consistently — tooling enforcement is the fix.

**Responsibility boundary:** GPH orchestrates other tools (GTC, STA, ENT, TRC, FPR) at phase boundaries. It does NOT implement checks itself — it delegates to existing scripts and aggregates their results.

**Phase differences:** The `--phase` flag controls which checks run:

| Check | implement pre | implement post | verify pre | verify post |
|-------|:---:|:---:|:---:|:---:|
| git-check (GTC) | ✓ | ✓ | ✓ | ✓ |
| state-valid (STA) | ✓ | ✓ | ✓ | ✓ |
| lifecycle-check | ✓ (queued/implementing) | — | ✓ (verifying) | — |
| spec-artifacts | ✓ | — | — | — |
| fingerprints (FPR) | ✓ | — | — | — |
| progress-entry (ENT) | — | ✓ FAIL | — | ✓ FAIL |
| learnings-entry (ENT) | — | ✓ WARN | — | ✓ WARN |
| emergent-entry (ENT) | — | ✓ WARN | — | ✓ WARN |
| trace-events (TRC) | — | ✓ WARN | — | ✓ WARN |
| last-verdict | — | — | — | ✓ FAIL |
| verification-report | — | — | — | ✓ FAIL |

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PUR_1 | Pre-phase gate: verifies git state, state file validity, and phase-appropriate checks before the subagent starts. | P0 |
| GPH_PUR_2 | Post-phase gate: verifies git state, state file validity, mandatory runtime artifacts, and phase-specific outputs (verdict/report for verify). | P0 |
| GPH_PUR_3 | Single script with `--phase implement|verify` controlling which checks run. Eliminates code duplication between the two phases. | P0 |
| GPH_PUR_4 | Delegates to existing tools — GTC, STA, ENT, TRC, FPR. Aggregates results into pass/fail/warn. | P0 |

## 2. Agent Personas (GPH_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GPH_AGT_1 | orchestrator script | before spawning subagent | `pre --phase implement` or `pre --phase verify` |
| GPH_AGT_2 | implement subagent | before exiting — self-corrects until post passes | `post --phase implement` |
| GPH_AGT_3 | verify subagent | before exiting — self-corrects until post passes | `post --phase verify` |
| GPH_AGT_4 | orchestrator script | optional re-verification after subagent exits | `post` |
| GPH_AGT_5 | human | manual debugging / phase boundary inspection | both commands |
| GPH_AGT_6 | GUI tool | phase transition monitoring | both commands |
| GPH_AGT_7 | case study / audit agent | post-run analysis | both commands |

## 3. Commands

**Command summary:**

- **`pre`** (PRE) — Pre-phase gate. Verifies foundation before work starts: git state, iteration state, lifecycle, phase-specific preconditions. Called by the orchestrator (or subagent) before each implement/verify phase.
- **`post`** (PST) — Post-phase gate. Verifies artifact completeness before subagent exits: entries exist, state updated, tests pass, trace written. Subagents self-correct until this passes.

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output |
| `--pretty` | all commands | Indent JSON (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON fields (requires `--output json`) |
| `--phase` | all commands | Required. `implement` or `verify`. Controls which checks run. |

Both commands are read-only — `--dry-run` is NOT applicable.

**JSON error behavior:** Per UNV_ERR_4.

---

### 3.1 pre (PRE)

#### Justification (GPH_PRE_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_JUS_1 | Why: verifies the foundation before the subagent starts. Catches wrong git state, invalid state files, and phase-specific issues early. | P0 |
| GPH_PRE_JUS_2 | When: called by the orchestrator immediately before spawning the subagent. | P0 |
| GPH_PRE_JUS_3 | Deprecation signal: only if the orchestrator inlines all pre-checks. | P1 |

#### Definition (GPH_PRE_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_CMD_1 | Usage: `plet_gate_phase.py pre [<plet_dir>] --iter-id ID_xxx --phase implement|verify [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic

**Concurrency:** safe — read-only

#### Inputs (GPH_PRE_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. | P0 |
| GPH_PRE_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| GPH_PRE_INP_3 | `--phase` — `implement` or `verify`. Required. Controls which checks run. | P0 |

#### Outputs (GPH_PRE_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_OUT_1 | Text mode: title line `PASS/WARN/FAIL: pre — {summary}`, per-check lines, summary line. | P0 |
| GPH_PRE_OUT_2 | JSON mode: structured gate results (see schema below). | P0 |
| GPH_PRE_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). | P0 |
| GPH_PRE_OUT_4 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**GPH_PRE JSON schema (GPH_PRE_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "pre",
  "iterationId": "...",
  "phase": "implement|verify",
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (GPH_PRE_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_PRE_1 | `--iter-id` and `--phase` present | P0 |
| GPH_PRE_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GPH_PRE_PRE_3 | `plet_dir/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GPH_PRE_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GPH_PRE_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_PST_1 | No files modified | P0 |
| GPH_PRE_PST_2 | All checks run — no early termination on first failure | P0 |
| GPH_PRE_PST_3 | Exit code reflects overall result: 0/1/2 | P0 |

#### Behaviors (GPH_PRE_BHV)

All pre-gates run git-check and state-valid. Additional checks depend on `--phase`.

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PRE_BHV_1 | **git-check**: Calls GTC `check-iteration --phase {phase}`. Each check prefixed with `git:`. Both phases. | P0 |
| GPH_PRE_BHV_2 | **state-valid**: Calls STA `validate`. Both phases. | P0 |
| GPH_PRE_BHV_3 | **lifecycle-check**: Reads lifecycle from iter state. **implement**: WARN if not `queued`/`implementing`. **verify**: WARN if not `verifying`. Both phases. | P0 |
| GPH_PRE_BHV_4 | **spec-artifacts**: Checks `requirements.md` and `iterations.md` exist. FAIL if missing. **implement only** — spec artifacts can't disappear mid-session. | P0 |
| GPH_PRE_BHV_5 | **fingerprints-consistent**: Calls FPR `check`. WARN if stale. **implement only** — verify can't change requirements. | P0 |
| GPH_PRE_BHV_6 | Check order: git-check → state-valid → lifecycle-check → spec-artifacts (impl only) → fingerprints (impl only). | P0 |

---

### 3.2 post (PST)

#### Justification (GPH_PST_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_JUS_1 | Why: enforces mandatory artifact completeness after the subagent finishes. FB_29, FB_33, FB_11. | P0 |
| GPH_PST_JUS_2 | When: called by the subagent before exiting. Self-corrects until passes. | P0 |
| GPH_PST_JUS_3 | Deprecation signal: only if mandatory entry rules are removed. | P1 |

#### Definition (GPH_PST_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_CMD_1 | Usage: `plet_gate_phase.py post [<plet_dir>] --iter-id ID_xxx --phase implement|verify [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic

**Concurrency:** safe — read-only

#### Inputs (GPH_PST_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. | P0 |
| GPH_PST_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| GPH_PST_INP_3 | `--phase` — `implement` or `verify`. Required. Controls which checks run. | P0 |

#### Outputs (GPH_PST_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_OUT_1 | Text mode: title line, per-check lines, summary line. | P0 |
| GPH_PST_OUT_2 | JSON mode: structured gate results (see schema below). | P0 |
| GPH_PST_OUT_3 | Exit codes: 0/1/2. | P0 |
| GPH_PST_OUT_4 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**GPH_PST JSON schema (GPH_PST_OUT_2):**
```json
{
  "status": "ok|warn|fail",
  "command": "post",
  "iterationId": "...",
  "phase": "implement|verify",
  "checks": [
    {"name": "...", "status": "pass|fail|warn", "detail": "..."}
  ],
  "summary": {"total": N, "passed": N, "failed": N, "warnings": N},
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (GPH_PST_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_PRE_1 | `--iter-id` and `--phase` present | P0 |
| GPH_PST_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GPH_PST_PRE_3 | `plet_dir/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GPH_PST_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GPH_PST_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_PST_1 | No files modified | P0 |
| GPH_PST_PST_2 | All checks run — no early termination on first failure | P0 |
| GPH_PST_PST_3 | Exit code reflects overall result: 0/1/2 | P0 |

#### Behaviors (GPH_PST_BHV)

Post-gate re-verifies git and state, then checks artifacts. Verify adds verdict and report checks.

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_PST_BHV_1 | **git-check**: Calls GTC `check-iteration --phase {phase}`. Both phases. | P0 |
| GPH_PST_BHV_2 | **state-valid**: Re-validates iter state. Both phases. | P0 |
| GPH_PST_BHV_3 | **progress-entry**: ENT check. FAIL if 0. Both phases. | P0 |
| GPH_PST_BHV_4 | **learnings-entry**: ENT check. WARN if 0. Both phases. | P0 |
| GPH_PST_BHV_5 | **emergent-entry**: ENT check. WARN if 0 with actionable guidance. Both phases. | P0 |
| GPH_PST_BHV_6 | **trace-events**: Checks `plet/trace/{iter_id}-{phase}-{attempt}-events.ndjson` exists + TRC validate. WARN if missing/empty/invalid. Both phases. | P0 |
| GPH_PST_BHV_7 | **last-verdict**: Reads `lastVerdict` from iter state. FAIL if null. **verify only** — implement doesn't produce verdicts. | P0 |
| GPH_PST_BHV_8 | **verification-report**: Reads `verificationReports` from iter state. FAIL if empty or last entry missing `verdict`/`criteriaResults`. **verify only**. | P0 |
| GPH_PST_BHV_9 | ENT check called once, three check results extracted. Both phases. | P0 |
| GPH_PST_BHV_10 | Check order: git-check → state-valid → lifecycle-handoff → audit-tag → progress → learnings → emergent → trace → last-verdict (verify only) → verification-report (verify only) → lifecycle-unchanged (verify only). | P0 |
| GPH_PST_BHV_11 | **lifecycle-handoff**: Reads lifecycle from iter state. **implement post**: FAIL if not `verifying` — the implement subagent must set lifecycle → `verifying` as its handoff signal before exiting. Self-correction: subagent sets it and re-runs post gate. | P0 |
| GPH_PST_BHV_12 | **lifecycle-unchanged**: Reads lifecycle from iter state. **verify post only**: FAIL if not `verifying` — the verify subagent must NOT touch lifecycle. If it changed to `complete`, `implementing`, or `blocked`, that violates the ownership model (orchestrator owns post-verify transitions). Self-correction: subagent reverts lifecycle to `verifying` and re-runs post gate. | P0 |
| GPH_PST_BHV_13 | **audit-tag**: Checks git tag exists for current phase: `plet/{projectId}/loop{N}/audit/{iter_id}/{phase}-{attempt}`. FAIL if missing — the subagent must create the audit tag before exiting (FB_55). Both phases. | P0 |

---

## 4. Edge Cases (GPH_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_EDG_1 | Not inside a git repo — error before any checks. | P0 |
| GPH_EDG_2 | GTC script missing — FAIL on git-check. | P0 |
| GPH_EDG_3 | STA validate script missing — FAIL on state-valid. | P0 |
| GPH_EDG_4 | ENT check script missing — FAIL on progress-entry. | P0 |
| GPH_EDG_5 | Subprocess returns non-JSON — FAIL with "could not parse output". | P0 |
| GPH_EDG_6 | Retry attempt (attempt > 1) — same checks apply. | P0 |
| GPH_EDG_7 | `--pretty` without `--output json` — error. | P0 |
| GPH_EDG_8 | `--fields` without `--output json` — error. | P0 |
| GPH_EDG_9 | `--dry-run` passed — error. | P0 |
| GPH_EDG_10 | `plet_dir` is a file — error. | P0 |
| GPH_EDG_11 | Iter state not found — error. | P0 |
| GPH_EDG_12 | Invalid `--phase` — error. | P0 |

## 5. Error Handling (GPH_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_ERR_1 | Missing `--iter-id` or `--phase` → error + help text, exit 1 | P0 |
| GPH_ERR_2 | Invalid `--phase` → `Error: invalid --phase '{value}' (valid: implement, verify)` | P0 |
| GPH_ERR_3 | `plet_dir` not found → `Error: directory not found: {path}` | P0 |
| GPH_ERR_4 | `plet_dir` is a file → `Error: expected a directory, got file: {path}` | P0 |
| GPH_ERR_5 | Global state validation failure → error from `util_state` | P0 |
| GPH_ERR_6 | Iter state validation failure → error from `util_state` | P0 |
| GPH_ERR_7 | Not a git repo → `Error: not inside a git repository` | P0 |
| GPH_ERR_8 | `--pretty` without `--output json` → error | P0 |
| GPH_ERR_9 | `--fields` without `--output json` → error | P0 |
| GPH_ERR_10 | `--dry-run` passed → error | P0 |

## 6. Formats (GPH_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_FMT_1 | Reads `{plet_dir}/state.json` via `util_state`. | P0 |
| GPH_FMT_2 | Reads `{plet_dir}/state/{iter_id}.json` via `util_state`. | P0 |
| GPH_FMT_3 | Reads runtime artifacts indirectly via `plet_entries.py check`. | P0 |
| GPH_FMT_4 | Writes nothing — read-only. | P0 |

## 7. Agent Flows (GPH_AFL)

### GPH_AFL_1: Normal phase execution

1. Orchestrator prepares iteration
2. Orchestrator calls: `plet_gate_phase.py pre plet/ --iter-id ID_001 --phase implement --output json`
3. If exit 1 (fail): abort, report issues
4. If exit 2 (warn): log warnings, continue
5. Orchestrator spawns subagent
6. Subagent does its work
7. **Subagent** calls: `plet_gate_phase.py post plet/ --iter-id ID_001 --phase implement --output json`
8. If exit 1 (fail): subagent self-corrects and re-runs post
9. Subagent repeats 7-8 until passes
10. Subagent exits — its exit signals "post-gate passed"
11. Orchestrator optionally re-runs post
12. Proceed to next phase

### GPH_AFL_2: Subagent self-correction loop

1. Subagent finishes work
2. Runs post-gate → FAIL (missing progress entry)
3. Subagent writes the missing entry
4. Runs post-gate → WARN (missing learnings)
5. Subagent writes a learnings entry
6. Runs post-gate → PASS
7. Subagent exits cleanly

## 8. Examples (GPH_EXM)

### GPH_EXM_1: Implement pre-gate — all passing

```bash
plet_gate_phase.py pre plet/ --iter-id ID_001 --phase implement
# OK: pre — 10 passed
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:branch-exists — plet/LOGA/loop1/ID_001 exists
# PASS: git:correct-branch — on plet/LOGA/loop1/ID_001
# PASS: git:clean-worktree — no uncommitted changes
# PASS: git:linear-history — no merge commits
# PASS: git:no-stashes — stash list empty
# PASS: state-valid — ID_001.json valid
# PASS: lifecycle-check — lifecycle is implementing
# PASS: spec-artifacts — requirements.md and iterations.md exist
# PASS: fingerprints-consistent — all fingerprints consistent
# 10 checks: 10 passed, 0 failed, 0 warnings
```

### GPH_EXM_2: Verify pre-gate — simpler

```bash
plet_gate_phase.py pre plet/ --iter-id ID_001 --phase verify
# OK: pre — 8 passed
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:branch-exists — plet/LOGA/loop1/ID_001 exists
# PASS: git:correct-branch — on plet/LOGA/loop1/ID_001
# PASS: git:clean-worktree — no uncommitted changes
# PASS: git:linear-history — no merge commits
# PASS: git:no-stashes — stash list empty
# PASS: state-valid — ID_001.json valid
# PASS: lifecycle-check — lifecycle is verifying
# 8 checks: 8 passed, 0 failed, 0 warnings
```

### GPH_EXM_3: Verify post-gate — missing entries + verdict

```bash
plet_gate_phase.py post plet/ --iter-id ID_001 --phase verify
# FAIL: post — 3 failed, 3 warnings
# PASS: git:in-progress-operation — no interrupted git operations
# ...
# PASS: state-valid — ID_001.json valid
# FAIL: progress-entry — 0 progress entries for ID_001
# WARN: learnings-entry — 0 learnings entries for ID_001
# WARN: emergent-entry — 0 emergent entries for ID_001
# WARN: trace-events — no trace events file for ID_001 verify-1
# FAIL: last-verdict — lastVerdict is null
# FAIL: verification-report — verificationReports is empty
# 13 checks: 7 passed, 3 failed, 3 warnings
```

### GPH_EXM_4: Implement post-gate — JSON output

```bash
plet_gate_phase.py post plet/ --iter-id ID_001 --phase implement --output json --pretty
# {
#   "status": "ok",
#   "command": "post",
#   "iterationId": "ID_001",
#   "phase": "implement",
#   "checks": [
#     {"name": "git:in-progress-operation", "status": "pass", "detail": "..."},
#     ...
#     {"name": "progress-entry", "status": "pass", "detail": "1 progress entries for ID_001"},
#     {"name": "learnings-entry", "status": "pass", "detail": "1 learnings entries for ID_001"},
#     {"name": "emergent-entry", "status": "pass", "detail": "1 emergent entries for ID_001"},
#     {"name": "trace-events", "status": "pass", "detail": "trace events file valid (512 bytes)"}
#   ],
#   "summary": {"total": 10, "passed": 10, "failed": 0, "warnings": 0},
#   ...
# }
```

Note: implement post has no `last-verdict` or `verification-report` checks. Verify post would include those two additional checks.

## 9. Dependencies on Other Scripts (GPH_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GPH_DEP_1 | imports | `util_cli` | shared CLI helpers |
| GPH_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
| GPH_DEP_3 | calls (subprocess) | `plet_git_check.py` | `check-iteration --phase {phase}` |
| GPH_DEP_4 | calls (subprocess) | `plet_state.py` | `validate` |
| GPH_DEP_5 | calls (subprocess) | `plet_entries.py` | `check` (post only) |
| GPH_DEP_6 | calls (subprocess) | `plet_trace.py` | `validate` (post only) |
| GPH_DEP_7 | calls (subprocess) | `plet_fingerprint.py` | `check` (implement pre only) |
| GPH_DEP_8 | called by | `plet_orchestrator.py` | pre/post both phases |

## 10. Non-Functional Requirements (GPH_NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_NFR_1 | Subprocess calls use `--output json`. Text fallback if JSON parse fails. | P0 |
| GPH_NFR_2 | Gate must complete within 5 seconds. | P1 |

## 11. Developer Experience (GPH_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GPH_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure | P0 |
| GPH_DXP_2 | IMPORTANT: both commands are read-only — safe to run anytime | P0 |
| GPH_DXP_3 | PITFALLS: --iter-id and --phase both required. Defaults to plet/ in cwd. | P0 |
| GPH_DXP_4 | Check names are stable identifiers: `git:*`, `state-valid`, `lifecycle-check`, `spec-artifacts`, `fingerprints-consistent`, `progress-entry`, `learnings-entry`, `emergent-entry`, `trace-events`, `last-verdict`, `verification-report` | P0 |

## 12. Critical Test Areas (GPH_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GPH_CRT_1 | Pre-gate passes (both phases) | Gate blocks valid work | Clean state + git, verify exit 0 |
| GPH_CRT_2 | Pre-gate fails on invalid state | Invalid state not caught | Invalid state.json, verify exit 1 |
| GPH_CRT_3 | Post-gate fails on missing progress | FB_33 not enforced | No progress entry, verify exit 1 |
| GPH_CRT_4 | Post-gate warns on missing learnings | Missing learnings not surfaced | No learnings, verify exit 2 |
| GPH_CRT_5 | Post-gate passes with all entries | Complete iteration blocked | All entries, verify exit 0 |
| GPH_CRT_6 | GTC integration | Git checks missing | Verify git:* checks in output |
| GPH_CRT_7 | ENT check integration | Entry results not parsed | Verify progress/learnings/emergent |
| GPH_CRT_8 | Exit code correctness | Wrong signal | Verify 0/1/2 |
| GPH_CRT_9 | JSON output parseable | Can't parse | Verify valid JSON |
| GPH_CRT_10 | Implement pre has spec-artifacts+fingerprints | Missing phase-specific checks | Verify present for impl, absent for verify |
| GPH_CRT_11 | Verify post has verdict+report | Missing verify-specific checks | Verify present for verify, absent for impl |
| GPH_CRT_12 | Trace events validated | Corrupt traces not surfaced | Invalid trace, verify WARN |
| GPH_CRT_13 | Lifecycle check phase-specific | Wrong valid states | impl=queued/implementing, verify=verifying |
| GPH_CRT_14 | Invalid --phase | Bad phase not caught | --phase bogus, verify error |

## 13. Testing & Verification (GPH_TST)

**What to test:** See §12.

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_gate_phase.py`
- Harness: stdlib-only, subprocess calls
- Fixtures: temp git repos + state files + runtime artifacts
- Red/green, pre first, post second. Test both phases.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Two scripts or one? | One. GIM and GVR were 80% identical. `--phase` flag controls differences. Eliminates util_gate_phase.py module and code duplication. |
| 2 | Learnings/emergent FAIL or WARN? | WARN. Progress is mandatory (FAIL). Learnings/emergent strongly encouraged but not blocking. |
| 3 | Lifecycle transitions? | Not GPH's job. Validates state schema but doesn't enforce transitions. |
| 4 | Verification report check? | FAIL if verificationReports empty or missing fields. verify only. |
| 5 | Trace validation? | Existence + TRC validate. WARN if invalid. Both phases. |
| 6 | Stable label prefix? | GPH (Gate PHase). Replaces GIM + GVR. |

## 15. Future Considerations (GPH_FUT)

| ID | Area | Description |
|----|------|-------------|
| GPH_FUT_1 | Entry quality check | Beyond count > 0, check entries have meaningful content. |
| GPH_FUT_2 | Configurable severity | Allow per-project override of WARN/FAIL severity per check. |

## 16. FB Items Addressed

- FB_29 — Learnings/emergent not written. Post-gate WARNs if count is 0.
- FB_33 — Progress entries incomplete. Post-gate FAILs if count is 0.
- FB_11 — Trace files missing/corrupt. Post-gate WARNs.
- FB_40 — State lifecycle. Validates schema, defers transitions to orchestrator.
