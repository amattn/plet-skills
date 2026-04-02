# LOGA Run 5 Case Study

> **Status:** Not started
>
> **Run date:** TBD
> **Project:** LOGA (logalyzer) — Go
> **Plet version:** 0.4.1
> **Context:** First run without sandbox mode. Validates env var injection (seq 44), bootstrap (seq 42), compact progress (seq 43), session history branch lookup (seq 45), plan phase UX (seq 47). Continues from Run 4 state (ID_001 complete, ID_002 blocked, ID_003–ID_013 ineligible).

## Meta

- Case study #7 in sequence
- Prior runs: Run 1 (baseline), Run 2 (first scripts), Run 3 (worktree conflict), Run 4 (lifecycle extraction — sandbox blocked)
- **Goal:** Complete multiple iterations without sandbox interference. Validate 0.4.1 fixes.

## Section 1: Plan

### Goal

1. Validate env var injection — subagent finds scripts immediately (no 8-min search)
2. Validate compact progress entries (one-liner + trace ID)
3. Validate session history branch lookup (no loop0/loop3 mismatch)
4. Complete multiple iterations (Run 4 only completed 1)
5. First run without sandbox — establish baseline for non-sandbox operation

### Project Profile

| Field | Value |
|-------|-------|
| Project ID | LOGA |
| Language | Go |
| Type | CLI tool (log analyzer) |
| Iterations | 13 |
| Plet version | 0.4.1 |
| Sandbox | Disabled |
| Loop sessions | TBD |
| Refine sessions | TBD |

### Starting State

| ID | Lifecycle | Notes |
|----|-----------|-------|
| ID_001 | complete | Done in Run 4 |
| ID_002 | blocked | Sandbox failure in Run 4 — needs requeue |
| ID_003–ID_013 | ineligible | Waiting on dependencies |

**Decision:** Fresh repo. No stale state from Run 4 failed sessions.

---

## Observations (live, during run)

<!-- Add observations here as they happen. -->

### Plan phase

1. **Script discovery working.** Agent found scripts path immediately — no 8-minute search like Run 4. Used `$SCRIPTS` variable from the CLAUDE.md stub or plugin context.

2. **Allow pattern doesn't match.** `Bash(plet_*.py*)` in settings.json doesn't match `$SCRIPTS/plet_fingerprint.py ...` because the command starts with the variable assignment. Claude Code prompts for approval on every plet script call. Option 2 ("don't ask again for similar commands") works as project-level auto-allow.

3. **No sandbox, no auto mode, no bypassPermissions.** Running with bare permissions + allow list only. Every non-plet Bash command and every Write/Edit needs manual approval. This will block subagents in the loop phase.

4. **Plan committed to main — no plan branch.** Despite SKILL.md Step 2 saying "create plan branch," the agent committed directly to main. Same issue as Run 3 (#2) and Run 4 (#2). Third time — prose instructions don't work for this. Need a script to enforce branch creation, or accept that plan commits go to main. (→ FB item: plan branch creation needs enforcement, not prose)

5. **Agent correctly instructed user to fix permissions.** Detected insufficient permissions (no auto mode, no bypassPermissions) and told the user what to add to settings.json. Bootstrap `check` permissions warning working as designed.

### Loop phase

6. **Permission prompts only for parent agent, not subagents.** SKILL.md agent prompted for gate-session and orchestrator script calls (parent context). Once orchestrator spawned subagent via plet_invoke.py, bypassPermissions kicked in — no more prompts. This is correct behavior.

7. **Env var injection working.** Subagent uses `$PLET_SCRIPTS_DIR` for all script calls. No searching. Immediate discovery.

8. **Bash working — no sandbox blocks.** `go mod init`, `go test`, `go build`, `git add && git commit` all executing. No EPERM errors. Sandbox disabled = full tool access.

9. **IST scripts called correctly.** start-phase, update-activity (with --phase-activity + --activity-detail + --agent-id), update-criterion — all via `$PLET_SCRIPTS_DIR`. Git commits with plet format (`wip: [ID_001] ...`).

10. **Go toolchain friction.** GOROOT/GOTOOLCHAIN version mismatch between homebrew Go and system Go. Not a plet issue — environment config. Subagent worked around it.

11. **BUG: No dependency promotion — ineligible iterations never become queued.** After ID_001 completed, ID_002 (depends on ID_001) stayed `ineligible` instead of being promoted to `queued`. The orchestrator calls `schedule.py eligible` which only returns `queued` iterations with all deps complete. But `ineligible` iterations are never promoted — nobody writes `queued` to state.json when deps are satisfied. GST `init` sets `ineligible` for iterations with deps, but nothing changes it later. The orchestrator needs a dependency promotion step after each completion. (→ critical bug fix)

12. **BUG: Merge conflict in state.json during merge-squash.** After ID_002 implement+verify succeeded, merge-squash failed with conflict markers in `sessionHistory[0].endedAt`. Both workstream and iteration branch modified state.json — the worktree had a stale copy from when the worktree was created, and the workstream was updated by the orchestrator (lifecycle transitions, session end). The merge-squash tries to merge the iteration branch (which has the stale state.json) into workstream — conflict. This is the same class of bug as Run 3 but in state.json instead of per-iteration files. (→ critical bug: state.json should be excluded from merge-squash, or the orchestrator should git-checkout state.json before merge)

13. **"Files changed" mostly useless.** 19 entries with the field: 9 say "(none)" (auto-logged), 6 are template examples from embedded reference docs, 4 have real files (subagent-written). The auto-logger can't know what files changed — only the subagent can. Consider removing "Files changed" from auto-logged entries or making it optional in the format.

---

## Section 2: Artifact Analysis

TBD

## Section 3: Code Analysis

TBD

## Section 4: Comparison with Prior Runs

| Metric | Run 1 | Run 2 | Run 3 | Run 4 | Run 5 |
|--------|:---:|:---:|:---:|:---:|:---:|
| Iterations completed | 13/13 | 1/13 | 0/13 | 1/13 | TBD |
| Verify first-pass rate | TBD | N/A | N/A | 1/1 | TBD |
| Worktree merge conflicts | N/A | N/A | 1 (fatal) | 0 | TBD |
| Lifecycle source | per-iter | per-iter | per-iter | state.json | state.json |
| Sandbox | N/A | N/A | N/A | Yes (blocked) | No |
| Script discovery time | N/A | N/A | N/A | ~8 min | TBD |
| Env vars injected | No | No | No | No (v0.4.0) | Yes (v0.4.1) |

## Section 5: Findings & Recommendations

TBD
