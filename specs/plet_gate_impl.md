# plet_gate_impl.py (GIM)

> Status: **superseded** by `plet_gate_phase.md` (GPH). Kept as historical reference for reviewed decisions.

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*. A table row should be self-contained enough to verify independently, but the surrounding prose provides the understanding needed to write and review it well.

## 1. Purpose (GIM_PUR)

Gate script for the implement phase. The primary purpose is to give the orchestrator, subagent, or subprocess a clear signal: **you're not done yet — clean up or block.** Runs pre and post implementation, enforcing compliance checks and mandatory artifact completeness. The implement subagent runs `post` before exiting and self-corrects until it passes — its exit means "I passed my own gate."

Case study evidence: SPARK produced 0.09 learnings and 0.04 emergent entries per iteration despite a prose mandate (FOO_29). Only 6 of 23 iterations had explicit progress entries (FOO_33). State lifecycle fields were stuck at wrong values in 10 of 23 iterations (FOO_40). Prose rules failed consistently — tooling enforcement is the fix.

**Responsibility boundary:** GIM orchestrates other tools (GTC, STA, ENT) at phase boundaries. It does NOT implement checks itself — it delegates to existing scripts and aggregates their results. The orchestrator decides what to do with GIM's pass/fail/warn verdict.

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PUR_1 | Pre-implement gate: verifies git state, state file validity, and required artifacts before the implement subagent starts. Prevents starting implementation on a broken foundation. | P0 |
| GIM_PUR_2 | Post-implement gate: verifies git state, state file validity, and mandatory runtime artifact entries (progress, learnings, emergent) after the implement subagent finishes. Blocks progression to verify if artifacts are incomplete. Addresses FOO_29, FOO_33. | P0 |
| GIM_PUR_3 | Delegates to existing tools — GTC (git compliance), STA (state validation), ENT (entry completeness). Aggregates results into a single pass/fail/warn verdict. | P0 |

## 2. Agent Personas (GIM_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| GIM_AGT_1 | orchestrator script | before spawning implement subagent | `pre` |
| GIM_AGT_2 | implement subagent | before exiting — subagent runs post-gate and self-corrects until it passes | `post` |
| GIM_AGT_3 | orchestrator script | optional re-verification after subagent exits (trust but verify) | `post` |
| GIM_AGT_4 | human | manual debugging / phase boundary inspection | both commands |
| GIM_AGT_5 | GUI tool | phase transition monitoring | both commands |
| GIM_AGT_6 | case study / audit agent | post-run analysis — verify all iterations passed gates | both commands |

## 3. Commands

Command abbreviations: `PRE` (pre), `PST` (post).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | all commands | Structured JSON output instead of text. JSON always includes: `status`, `command`, `scriptVersion`, `timestamp`. |
| `--pretty` | all commands | Indent JSON output (requires `--output json`) |
| `--fields f1,f2` | all commands | Limit JSON output to named fields (requires `--output json`) |
| `--usage` | top-level only | Compact invocation syntax with examples for all commands (UNV_CMD_30) |

Both commands are read-only — `--dry-run` is NOT applicable (nothing to dry-run on a gate check).

**JSON error behavior:** When `--output json` is active, errors produce structured JSON to stdout with `"status":"error"` plus a text message to stderr. Exit code is still 1. Per UNV_ERR_4.

---

### 3.1 pre (PRE)

#### Justification (GIM_PRE_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_JUS_1 | Why: verifies the foundation is solid before the implement subagent starts. Catches wrong git state, invalid state files, and missing spec artifacts early — before an agent wastes work on a broken base. | P0 |
| GIM_PRE_JUS_2 | When: called by the orchestrator immediately before spawning the implement subagent. Also callable by humans for debugging. | P0 |
| GIM_PRE_JUS_3 | Deprecation signal: only if the orchestrator inlines all pre-checks (unlikely — gate scripts keep orchestrator logic clean). | P1 |

#### Definition (GIM_PRE_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_CMD_1 | Usage: `plet_gate_impl.py pre <plet_dir> --iter-id ITR_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GIM_PRE_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. Derives `state.json` and `state/{iter_id}.json` internally. | P0 |
| GIM_PRE_INP_2 | `--iter-id` — iteration ID (e.g., `ITR_001`). Required. Used to locate per-iteration state file. | P0 |

#### Outputs (GIM_PRE_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_OUT_1 | Text mode: title line `PASS/WARN/FAIL: pre — {summary}`, then one line per check, then summary line. Same format as GTC and SES preflight. | P0 |
| GIM_PRE_OUT_2 | JSON mode: structured gate results (see schema below). | P0 |
| GIM_PRE_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). Same as GTC. | P0 |
| GIM_PRE_OUT_4 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**GIM_PRE JSON schema (GIM_PRE_OUT_2):**
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

#### Preconditions (GIM_PRE_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_PRE_1 | `--iter-id` present | P0 |
| GIM_PRE_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GIM_PRE_PRE_3 | `plet_dir/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GIM_PRE_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GIM_PRE_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_PST_1 | No files modified | P0 |
| GIM_PRE_PST_2 | All checks run — no early termination on first failure | P0 |
| GIM_PRE_PST_3 | Exit code reflects overall result: 0 (no failures, no warnings), 1 (any failure), 2 (no failures, at least one warning) | P0 |

#### Behaviors (GIM_PRE_BHV)

GIM pre delegates to existing tools and aggregates results. Each tool is called via subprocess with `--output json` for structured parsing.

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PRE_BHV_1 | **git-check**: Calls `git_check.py check-iteration <plet_dir> --iter-id <iter_id> --phase implement --output json`. Each GTC check becomes a GIM check with `git:` prefix (e.g., `git:correct-branch`). GTC FAIL/WARN propagate directly. | P0 |
| GIM_PRE_BHV_2 | **state-valid**: Calls `plet_state.py validate <plet_dir>/state/<iter_id>.json --output json`. PASS if valid, FAIL if invalid. Detail includes validation errors. | P0 |
| GIM_PRE_BHV_3 | **spec-artifacts**: Checks `requirements.md` and `iterations.md` exist in `plet_dir`. FAIL if either missing. | P0 |
| GIM_PRE_BHV_5 | **lifecycle-check**: Reads lifecycle from iter state. WARN if lifecycle is not `queued` or `implementing`. Catches obvious mistakes (running pre on a complete/withdrawn iteration) without blocking. | P0 |
| GIM_PRE_BHV_6 | **fingerprints-consistent**: Calls `plet_fingerprint.py check` via subprocess. WARN if stale — spec drift detected but not blocking per-iteration. Surfaces mid-loop changes to requirements that the human may want to address. | P0 |
| GIM_PRE_BHV_4 | Check order: git-check → state-valid → lifecycle-check → spec-artifacts → fingerprints-consistent. Git first, then state/lifecycle, then artifacts/fingerprints. | P0 |

---

### 3.2 post (PST)

#### Justification (GIM_PST_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_JUS_1 | Why: enforces mandatory artifact completeness after implementation finishes. FOO_29 showed agents ignoring prose entry rules. FOO_33 showed incomplete progress entries. This gate blocks verify until artifacts are complete. | P0 |
| GIM_PST_JUS_2 | When: called by the implement subagent before exiting. Subagent self-corrects until post-gate passes — its exit signals "I passed my own gate." Orchestrator can optionally re-verify (trust but verify). | P0 |
| GIM_PST_JUS_3 | Deprecation signal: only if mandatory entry rules are removed (unlikely — runtime artifacts are plet's primary value). | P1 |

#### Definition (GIM_PST_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_CMD_1 | Usage: `plet_gate_impl.py post <plet_dir> --iter-id ITR_xxx [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent, non-atomic (no writes)

**Concurrency:** safe — read-only

#### Inputs (GIM_PST_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_INP_1 | `plet_dir` — (optional) path to plet directory. Default: `plet/`. Derives `state.json` and `state/{iter_id}.json` internally. | P0 |
| GIM_PST_INP_2 | `--iter-id` — iteration ID (e.g., `ITR_001`). Required. Used to locate per-iteration state file and check entries. | P0 |

#### Outputs (GIM_PST_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_OUT_1 | Text mode: title line `PASS/WARN/FAIL: post — {summary}`, then one line per check, then summary line. | P0 |
| GIM_PST_OUT_2 | JSON mode: structured gate results (see schema below). | P0 |
| GIM_PST_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). | P0 |
| GIM_PST_OUT_4 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**GIM_PST JSON schema (GIM_PST_OUT_2):**
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

#### Preconditions (GIM_PST_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_PRE_1 | `--iter-id` present | P0 |
| GIM_PST_PRE_2 | `plet_dir/state.json` passes `util_state.load_and_validate_global_state()` | P0 |
| GIM_PST_PRE_3 | `plet_dir/state/{iter_id}.json` passes `util_state.load_and_validate_iter_state()` | P0 |
| GIM_PST_PRE_4 | Current directory is inside a git repository | P0 |

#### Postconditions (GIM_PST_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_PST_1 | No files modified | P0 |
| GIM_PST_PST_2 | All checks run — no early termination on first failure | P0 |
| GIM_PST_PST_3 | Exit code reflects overall result: 0 (no failures, no warnings), 1 (any failure), 2 (no failures, at least one warning) | P0 |

#### Behaviors (GIM_PST_BHV)

Post-gate re-verifies git and state (subagent may have left dirty state) and adds mandatory entry checks. Does NOT repeat lifecycle-check (mid-transition), spec-artifacts (can't disappear during impl), or fingerprints (can't change during impl).

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_PST_BHV_1 | **git-check**: Same as GIM_PRE_BHV_1. Calls GTC `check-iteration <plet_dir> --iter-id <iter_id> --phase implement`. Verifies the implement subagent left git state clean. | P0 |
| GIM_PST_BHV_2 | **state-valid**: Same as GIM_PRE_BHV_2. Re-validates `plet_dir/state/{iter_id}.json` after subagent may have modified it. | P0 |
| GIM_PST_BHV_3 | **progress-entry**: Calls `plet_entries.py check <plet_dir> --iter-id <iter_id> --output json`. FAIL if progress count is 0. The implement phase must produce at least one progress entry (FOO_33). Detail includes count. | P0 |
| GIM_PST_BHV_4 | **learnings-entry**: Uses the same ENT check result as BHV_3. WARN if learnings count is 0. Learnings are strongly encouraged but a missing learnings entry shouldn't block verify — some iterations genuinely have nothing novel to report. Detail includes count. | P0 |
| GIM_PST_BHV_5 | **emergent-entry**: Uses the same ENT check result as BHV_3. WARN if emergent count is 0. Detail message includes actionable guidance: "0 emergent entries for {iter_id} — verify no design decisions, requirement gaps, or assumptions were made during implementation. If none, this is expected. If any were made, write them before exiting." Prompts the subagent to double-check rather than silently proceeding. | P0 |
| GIM_PST_BHV_8 | **trace-events**: Checks that `plet/trace/{iter_id}-implement-{attempt}-events.ndjson` exists, is non-empty, and passes `plet_trace.py validate` via subprocess. WARN if missing, empty, or invalid NDJSON (FOO_11). Catches both completely missing traces and corrupt trace files. | P0 |
| GIM_PST_BHV_6 | Check order: git-check → state-valid → progress-entry → learnings-entry → emergent-entry → trace-events. Git and state first (structural), then artifact completeness. | P0 |
| GIM_PST_BHV_7 | ENT check is called once and results parsed for all three artifact checks (progress, learnings, emergent). Single subprocess call, three check results extracted. | P0 |

---

## 4. Edge Cases (GIM_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_EDG_1 | Not inside a git repo — error before any checks (same as GTC behavior). | P0 |
| GIM_EDG_2 | GTC script missing — FAIL on git-check with detail "git_check.py not found". | P0 |
| GIM_EDG_3 | STA validate script missing — FAIL on state-valid with detail "plet_state.py not found". | P0 |
| GIM_EDG_4 | ENT check script missing — FAIL on progress-entry with detail "plet_entries.py not found". | P0 |
| GIM_EDG_5 | Subprocess call to GTC/STA/ENT returns non-JSON stdout — FAIL with detail "could not parse output". | P0 |
| GIM_EDG_6 | Retry attempt (attempt > 1) — same checks apply. Each attempt must independently pass all gates. | P0 |
| GIM_EDG_7 | `--pretty` without `--output json` — error. | P0 |
| GIM_EDG_8 | `--fields` without `--output json` — error. | P0 |
| GIM_EDG_9 | `--dry-run` passed — error (read-only commands). | P0 |
| GIM_EDG_10 | `plet_dir` is a file — error. | P0 |
| GIM_EDG_11 | `plet_dir/state/{iter_id}.json` doesn't exist — error (iter state not found). | P0 |

## 5. Error Handling (GIM_ERR)

Errors are distinct from check failures. Errors are structural problems that prevent the gate from running (bad input, missing state files). Check failures are the gate running and finding violations.

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_ERR_1 | Missing `--iter-id` → print specific error + help text, exit 1 | P0 |
| GIM_ERR_2 | `plet_dir` not found → `Error: directory not found: {path}` | P0 |
| GIM_ERR_3 | `plet_dir` is a file → `Error: expected a directory, got file: {path}` | P0 |
| GIM_ERR_4 | Global state validation failure → error from `util_state` | P0 |
| GIM_ERR_5 | Iter state validation failure → error from `util_state` | P0 |
| GIM_ERR_6 | Not a git repo → `Error: not inside a git repository` | P0 |
| GIM_ERR_7 | `--pretty` without `--output json` → error | P0 |
| GIM_ERR_8 | `--fields` without `--output json` → error | P0 |
| GIM_ERR_9 | `--dry-run` passed → `Error: --dry-run is not supported (pre and post are read-only)` | P0 |

## 6. Formats (GIM_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_FMT_1 | Reads `plet/state.json` via `util_state` for project context. | P0 |
| GIM_FMT_2 | Reads `plet/state/{id}.json` via `util_state` for iteration context. | P0 |
| GIM_FMT_3 | Reads plet runtime artifacts (progress.md, learnings.md, emergent.md) indirectly via `plet_entries.py check`. | P0 |
| GIM_FMT_4 | Writes nothing — all commands are read-only. | P0 |

## 7. Agent Flows (GIM_AFL)

### GIM_AFL_1: Normal implement phase

1. Orchestrator prepares iteration for implementation
2. Orchestrator calls: `plet_gate_impl.py pre plet/ --iter-id ITR_001 --output json`
3. If exit 1 (fail): abort iteration, report issues
4. If exit 2 (warn): log warnings to progress.md, continue
5. Orchestrator spawns implement subagent
6. Implement subagent does its work (coding, testing, etc.)
7. **Subagent** calls: `plet_gate_impl.py post plet/ --iter-id ITR_001 --output json`
8. If exit 1 (fail): subagent self-corrects (adds missing entries, fixes state) and re-runs post
9. Subagent repeats step 7-8 until post-gate passes
10. Subagent exits — its exit signals "post-gate passed"
11. Orchestrator optionally re-runs post as trust-but-verify
12. Proceed to verify phase (GVR takes over)

### GIM_AFL_2: Subagent self-correction loop

1. Subagent finishes implementation
2. Runs post-gate → FAIL (e.g., missing progress entry)
3. Subagent writes the missing progress entry
4. Runs post-gate → WARN (missing learnings)
5. Subagent writes a learnings entry
6. Runs post-gate → PASS
7. Subagent exits cleanly

## 8. Examples (GIM_EXM)

### GIM_EXM_1: Pre-gate — all passing

```bash
plet_gate_impl.py pre plet/ --iter-id ITR_001
# PASS: pre — 10 passed
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:branch-exists — plet/LOGA/loop1/ITR_001 exists
# PASS: git:correct-branch — on plet/LOGA/loop1/ITR_001
# PASS: git:clean-worktree — no uncommitted changes
# PASS: git:linear-history — no merge commits since workstream divergence
# PASS: git:no-stashes — stash list empty
# PASS: state-valid — plet/state/ITR_001.json valid
# PASS: lifecycle-check — lifecycle is implementing
# PASS: spec-artifacts — requirements.md and iterations.md exist
# PASS: fingerprints-consistent — all fingerprints consistent
# 10 checks: 10 passed, 0 failed, 0 warnings
```

### GIM_EXM_2: Post-gate — missing progress entry

```bash
plet_gate_impl.py post plet/ --iter-id ITR_001
# FAIL: post — 1 failed, 2 warnings
# PASS: git:in-progress-operation — no interrupted git operations
# PASS: git:branch-exists — plet/LOGA/loop1/ITR_001 exists
# PASS: git:correct-branch — on plet/LOGA/loop1/ITR_001
# PASS: git:clean-worktree — no uncommitted changes
# PASS: git:linear-history — no merge commits since workstream divergence
# PASS: git:no-stashes — stash list empty
# PASS: state-valid — plet/state/ITR_001.json valid
# FAIL: progress-entry — 0 progress entries for ITR_001
# WARN: learnings-entry — 0 learnings entries for ITR_001
# WARN: emergent-entry — 0 emergent entries for ITR_001
# WARN: trace-events — no trace events file for ITR_001 implement-1
# 11 checks: 7 passed, 1 failed, 3 warnings
```

### GIM_EXM_3: Post-gate — JSON output

```bash
plet_gate_impl.py post plet/ --iter-id ITR_001 --output json --pretty
# {
#   "status": "fail",
#   "command": "post",
#   "iterationId": "ITR_001",
#   "checks": [
#     {"name": "git:in-progress-operation", "status": "pass", "detail": "..."},
#     ...
#     {"name": "progress-entry", "status": "fail", "detail": "0 progress entries for ITR_001"},
#     {"name": "learnings-entry", "status": "warn", "detail": "0 learnings entries for ITR_001"},
#     {"name": "emergent-entry", "status": "warn", "detail": "0 emergent entries for ITR_001"},
#     {"name": "trace-events", "status": "warn", "detail": "no trace events file for ITR_001 implement-1"}
#   ],
#   "summary": {"total": 11, "passed": 7, "failed": 1, "warnings": 3},
#   ...
# }
```

## 9. Dependencies on Other Scripts (GIM_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| GIM_DEP_1 | imports | `util_cli` | `parse_kwargs`, `now_iso`, `dispatch`, `filter_fields` |
| GIM_DEP_2 | imports | `util_state` | `load_and_validate_global_state`, `load_and_validate_iter_state` |
| GIM_DEP_3 | calls (subprocess) | `git_check.py` | `check-iteration --phase implement` for git compliance |
| GIM_DEP_4 | calls (subprocess) | `plet_state.py` | `validate` for state schema compliance |
| GIM_DEP_5 | calls (subprocess) | `plet_entries.py` | `check` for mandatory entry verification (post only) |
| GIM_DEP_7 | calls (subprocess) | `plet_fingerprint.py` | `check` for fingerprint consistency (pre only) |
| GIM_DEP_8 | calls (subprocess) | `plet_trace.py` | `validate` for trace validation (post only) |
| GIM_DEP_6 | called by | `plet_orchestrator.py` | pre/post implement phase |

## 10. Non-Functional Requirements (GIM_NFR)

See `specs/conventions.md` for universal requirements.

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_NFR_1 | Subprocess calls to GTC/STA/ENT use `--output json` for structured parsing. Text fallback if JSON parse fails. | P0 |
| GIM_NFR_2 | Gate must complete within 5 seconds — all subprocess calls are fast (no network, no large file scans). | P1 |

## 11. Developer Experience (GIM_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| GIM_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure (UNV_DXP_5) | P0 |
| GIM_DXP_2 | IMPORTANT: both commands are read-only — no `--dry-run` needed, safe to run anytime | P0 |
| GIM_DXP_3 | PITFALLS: --iter-id is required for both commands. Defaults to plet/ in cwd — run from project root. | P0 |
| GIM_DXP_4 | Check names are stable identifiers: `git:*` (GTC checks prefixed), `state-valid`, `lifecycle-check`, `spec-artifacts`, `fingerprints-consistent`, `progress-entry`, `learnings-entry`, `emergent-entry`, `trace-events` | P0 |

## 12. Critical Test Areas (GIM_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| GIM_CRT_1 | Pre-gate passes on clean state | Gate blocks valid implementations | Create valid state + git repo, verify exit 0 |
| GIM_CRT_2 | Pre-gate fails on invalid state | Invalid state not caught, agent starts on broken base | Create invalid state.json, verify exit 1 |
| GIM_CRT_3 | Post-gate fails on missing progress | Missing entries not caught (FOO_33) | Create iteration with no progress entry, verify exit 1 |
| GIM_CRT_4 | Post-gate warns on missing learnings | Missing learnings not surfaced | Create iteration with no learnings, verify exit 2 |
| GIM_CRT_5 | Post-gate passes with all entries | Complete iteration blocked incorrectly | Create iteration with all entries, verify exit 0 |
| GIM_CRT_6 | GTC integration | GTC checks not included | Run gate, verify git:* checks appear in output |
| GIM_CRT_7 | ENT check integration | ENT results not parsed | Run post-gate, verify progress/learnings/emergent checks |
| GIM_CRT_8 | Exit code correctness | Orchestrator gets wrong signal | Verify 0/1/2 mapping |
| GIM_CRT_9 | JSON output parseable | Orchestrator can't parse results | Verify valid JSON with correct structure |
| GIM_CRT_10 | Missing dependency script | Gate crashes instead of reporting FAIL | Remove a script, verify FAIL check (not crash) |
| GIM_CRT_11 | Trace events existence | Missing trace not surfaced (FOO_11) | Create iteration with no trace file, verify WARN |

## 13. Testing & Verification (GIM_TST)

**What to test:** See §12 Critical Test Areas (GIM_CRT).

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_gate_impl.py`
- Run: `./skills/plet/tests/test_plet_gate_impl.py`
- Harness: stdlib-only custom harness per UNV_TST_2.
- All tests call the script via `subprocess.run()` (UNV_TST_4).
- **Fixtures:** tests create temp directories with git repos, state files, and plet runtime artifacts. Tests must create real git state (branches, clean worktree) for GTC integration to work.
- See `specs/conventions.md` UNV_TST_1–UNV_TST_8 for full testing conventions.

**Implementation discipline:** Red/green, command-by-command. pre first (simpler, fewer subprocess calls), post second (adds ENT check).

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | Should learnings/emergent be FAIL or WARN? | WARN. Progress is mandatory (FAIL) because it's the primary record of work done. Learnings and emergent are strongly encouraged but some iterations genuinely have nothing novel — blocking on them creates friction without value. The WARN surfaces the gap without blocking. |
| 2 | Should GIM check lifecycle transitions (FOO_40)? | No — lifecycle transitions are the orchestrator's responsibility. GIM validates state schema (via STA validate) but doesn't check whether lifecycle is in the "right" state. The orchestrator manages transitions; GIM checks artifacts. |
| 3 | Should GIM check trace events? | Yes — existence + TRC validate, WARN if missing/empty/invalid. Promoted from existence-only to full validation. Corrupt traces are worse than missing — silent data loss. |

### Open Questions

~~Should GIM pre-gate check lifecycle?~~ — Resolved: added as GIM_PRE_BHV_5. WARN if not queued/implementing.

## 15. Future Considerations (GIM_FUT)

| ID | Area | Description |
|----|------|-------------|
| ~~GIM_FUT_1~~ | ~~Trace validation~~ | Promoted to GIM_PST_BHV_8. Existence + TRC validate, WARN if invalid. |
| GIM_FUT_2 | Entry quality check | Beyond count > 0, check that progress entries have meaningful content (non-empty summary, files listed). Requires ENT to expose content quality metrics. |
| GIM_FUT_3 | ~~Lifecycle pre-check~~ | Promoted to GIM_PRE_BHV_5. WARN if lifecycle not queued/implementing. |

## 16. FOO Items Addressed

- FOO_29 — Learnings/emergent entries not written. Post-gate calls `plet_entries.py check` and WARNs if learnings/emergent count is 0.
- FOO_33 — Progress entries incomplete. Post-gate calls `plet_entries.py check` and FAILs if progress count is 0.
- FOO_11 — Trace file generation incomplete. Post-gate WARNs if trace events file missing or empty.
- FOO_40 — State lifecycle transitions. GIM validates state schema (STA validate) but defers lifecycle transition logic to the orchestrator.
