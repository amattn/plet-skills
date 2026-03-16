# specs/ Development Notes

> Tooling decisions, script design rationale, and inventory management. Migrated from root NOTES.md (2026-03-15) when tooling content grew large enough to warrant its own file. See also: root `NOTES.md` for plet project decisions, `guide/NOTES.md` for presentation decisions.

## Governing Principle: Skills for Judgment, Code for Compliance

Skills are prompt-interpreted every invocation — non-deterministic by nature. Over many iterations in a loop, independent interpretations of the same prose instructions drift. Code executes the same way every time.

**Use skills for:** judgment calls, adaptation, novel situations, decision-making — where non-determinism is a feature.

**Use code for:** schema enforcement, state management, format compliance, artifact generation — where non-determinism is a bug.

This was validated across three case studies: state schema drift (the most persistent issue) was fully solved by `plet_state.py`, while prose-only rules for learnings/emergent capture continued to be ignored by agents in the same run. The script-as-orchestrator architecture (see below) is the logical conclusion of this principle — if the orchestrator's job is mostly compliance (state transitions, dependency graph, prompt assembly, session bookkeeping), it should be code, not a skill.

**The dividing line:** If an agent keeps getting something wrong despite clear instructions, that's a signal to escalate from prose to tooling. If the task requires adapting to novel situations, it stays as a skill.

---

## Stable Label Prefixes

### Script prefixes

| Prefix | Script | Mnemonic |
|--------|--------|----------|
| UNV | `specs/conventions.md` | UNiVersal (shared across all scripts) |
| STA | `plet_state.py` | STAte |
| ENT | `plet_entries.py` | ENTries |
| FPR | `plet_fingerprint.py` | FingerPRint |
| GCL | `plet_git.py` | Git CompLiance |
| TRC | `plet_trace.py` | TRaCe |
| RTR | `plet_router.py` | RouTeR |
| INJ | `plet_inject_prompt.py` | INJect |
| ORC | `plet_orchestrator.py` | ORChestrator |
| GIM | `plet_gate_impl.py` | Gate IMpl |
| GVR | `plet_gate_verify.py` | Gate VeRify |

### Section abbreviations (used as middle segment: `ORC_CMD_1`)

| Abbrev | Section | Notes |
|--------|---------|-------|
| PUR | Purpose | §1 |
| AGT | Agent Personas | §2 |
| CMD | Commands | §3 — functional requirements |
| EDG | Edge Cases | §4 |
| ERR | Error Handling | §5 |
| IOS | Input/Output Schemas | §6 |
| AFL | Agent Flows | §7 |
| DEP | Dependencies | §8 |
| NFR | Non-Functional Requirements | §9 |
| DXP | Developer Experience | §10 |
| CRT | Critical Test Areas | §11 |
| TST | Testing & Verification | §12 |
| FUT | Future Considerations | §14 |

Sections 13 (Resolved Questions) and 15 (FB Items) don't get IDs — they reference existing IDs.

**ID format:** `SCRIPT_SECTION_N` — e.g., `ORC_CMD_1`, `GCL_EDG_3`, `UNV_NFR_2`. Append-only, never renumber.

---

#### Existing scripts audit (2026-03-15)

Audited `plet_state.py` and `plet_entries.py` against `specs/conventions.md`. Combined: 55 PASS, 5 FAIL, 5 N/A. Results recorded in each script's spec file.

**Key finding:** `plet_state.py` uses three different argument parsing patterns (inline kwarg parsing in `cmd_init`, 5 positional args in `update-criterion`, alternating pairs in `update-field`) while `plet_entries.py` consistently uses the shared `parse_kwargs()` function. The `parse_kwargs` pattern is what `scripts/CLAUDE.md` prescribes. Decision: document in specs, fix during PLAN_8 implementation — not worth a standalone fix pass.

#### Scripts coding standards — scripts/CLAUDE.md (2026-03-14)

Created `skills/plet/scripts/CLAUDE.md` as the coding standards file for plet's enforcement scripts. Key conventions: zero third-party dependencies (stdlib only — agents can't pip install), no interactive input (agents can't type into prompts), Python 3.8+ minimum, `#!/usr/bin/env python3` shebang + `chmod +x` for direct invocation, `--help` on every command (agent-readable), `--version` with script version and plet skill version for compatibility tracking, idempotency where practical, command-based CLI interface with `parse_kwargs` pattern, atomic file I/O, tests at `skills/plet/tests/` using subprocess-based custom harness (also zero deps).

#### Script --version includes skill compatibility (2026-03-14)

Every script supports `--version`, printing `<script_name> <version> (built against plet skill <skill_version>)`. If the skill makes a non-backward-compatible semver change (major bump), scripts built against the old version need to be reviewed and updated. Added to both plet_state.py and plet_entries.py.

#### SKILL.md allowed-tools tightened (2026-03-14)

Changed from `Bash(python3 *)` (approves any Python command) to path-specific entries: `Bash(${CLAUDE_SKILL_DIR}/scripts/plet_state.py *)` and `Bash(${CLAUDE_SKILL_DIR}/scripts/plet_entries.py *)`. More secure — only approves shipped scripts. New scripts get added as they're built.

#### Loop orchestrator responsibilities — tooling analysis (2026-03-15)

Enumerated 18 discrete responsibilities of the loop orchestrator (SKILL.md § Loop Phase) and classified each by scriptability:

**Fully scriptable (8 items, 44%):**
1. Increment `loopSessionCount` — state mutation (already handled by `plet_state.py`)
3. Session history entry — append entry, close previous `endedAt`, capture timestamp
4. Fingerprint check — compare ID arrays + timestamps across requirements/iterations/state, return stale/ok
5. Identify eligible iterations — graph traversal: deps all `complete` + lifecycle `queued` → eligible list
12. Re-evaluate dependency graph — same as #5, called after each completion
13. Check breakpoints — lookup in `state.json`, return hit/miss
14. Retry logic — count attempts, check trend (strictly decreasing → extend to 6, else abort at 3)
17. Capture end timestamp — timestamp + state mutation

**Partially scriptable (5 items, 28%):**
2. Branch management — deterministic name/create, but judgment needed for unexpected git state
6/9. Spawn subagents (impl + verify) — prompt payload assembly is deterministic (which files, which order), spawning + adaptation is skill
10. One verify per iteration — enforcement constraint
15. Compaction recovery — state reading + orientation summary is code, deciding what to do is skill
16. Git hygiene — tag naming, commit message formatting, squash sequencing are code; merge conflict resolution is skill

**Skill-only (4 items, 22%):**
7. Parallel spawning — deciding when is code, orchestrating concurrent Agent tool calls is runtime
8. Monitor completion — depends on Agent tool lifecycle
11. Handle verification result — severity assessment, fix-in-place vs cycle-back
18. Offer options to user — human interaction

#### plet_orchestrator.py scope (2026-03-15)

**Decision:** Build `plet_orchestrator.py` to cover the fully scriptable + deterministic-assembly portions. This is the orchestrator's compliance layer — the stuff that drifts when interpreted as prose across invocations.

**Commands (proposed):**

Session lifecycle:
- `start-session` — increment `loopSessionCount`, append `sessionHistory` entry, create branch name, return session metadata. Handles both new and resumed sessions.
- `end-session` — capture end timestamp, set `endedAt` on current `sessionHistory` entry.

Dependency graph:
- `eligible` — read `state.json` + all per-iteration state files, return list of eligible iteration IDs (deps `complete`, lifecycle `queued`). This is the core scheduling function.
- `check-breakpoints` — given an iteration ID and position (before/after), check `state.json` breakpoints, return hit/miss.

Retry logic:
- `check-retry` — given iteration ID, read attempt history, apply trend analysis, return continue/abort/extend.

Fingerprint:
- `check-fingerprints` — compare fingerprints across `requirements.md`, `iterations.md`, `state.json`. Return ok/stale with specific mismatch details.

Prompt assembly:
- `assemble-prompt` — given iteration ID + phase (impl/verify), read the iteration definition from `iterations.md`, assemble the full injection payload (reference file contents, formats.md sections, state-schema.md sections, requirements.md, learnings.md, per-iteration state). Output the assembled prompt text to stdout. The orchestrator skill pipes this to the Agent tool.

**Design notes:**
- Follows `scripts/CLAUDE.md` conventions (zero deps, no interactive input, Python 3.8+, atomic I/O)
- `assemble-prompt` is the highest-value command — it eliminates the most common source of orchestrator drift (forgetting a file, wrong injection order, stale content)
- `eligible` + `check-retry` together replace ~60% of the orchestrator's between-spawn decision logic
- `check-fingerprints` can also be called by the routing logic (before phase dispatch), not just the loop
- All commands are read-only except `start-session` and `end-session` — minimizes blast radius of bugs

**Relationship to PLAN_8:**
This is a superset of PLAN_8's "pre-flight checker" and "lifecycle finalizer" candidates. `plet_orchestrator.py` covers the loop-specific orchestrator logic; the other PLAN_8 candidates (`plet_trace.py`, `plet_git_cleanup.py`, pre/post-phase checkpoints) remain separate scripts for their respective domains.

#### Script-as-orchestrator architecture (2026-03-15)

**Insight:** Claude Code's CLI mode (`claude -p "prompt" --dangerously-skip-permissions`) can be invoked from a Python subprocess. This means the loop orchestrator could be a Python script rather than a skill — a deterministic process that spawns Claude one-shot processes as subagents.

**Current design:** Orchestrator is a skill (prompt-interpreted, long-lived Claude context). Vulnerable to compaction, drift, non-deterministic prose interpretation. The entire compaction recovery protocol (SKILL.md § Compaction Recovery Protocol) exists because the orchestrator is a Claude session.

**Alternative:** Orchestrator is `plet_orchestrator.py`. It reads state, identifies eligible iterations, assembles prompts, launches `claude -p` subprocesses, captures output, updates state, loops. The orchestrator *never compacts* because it has no context window. Steps 1–3 and 5–7 from the loop responsibilities analysis are exactly the fully-scriptable items.

**What stays as Claude:** Only impl and verify subagents — the parts requiring judgment. Spawned as one-shot CLI processes with assembled prompts.

**Key tradeoffs:**
- **Compaction:** eliminated entirely (script has no context window)
- **Drift:** eliminated for orchestrator logic (deterministic code)
- **Parallelism:** standard subprocess management vs Agent tool limitations
- **Transcript capture:** free (stdout/stderr) vs manual copy to trace/
- **Judgment calls:** must be pre-coded or deferred to subagents (can't adapt in-flight)
- **Error recovery:** must be explicitly coded vs Claude reasoning about failures
- **Permissions:** `--dangerously-skip-permissions` bypasses all safety checks. Named that way for a reason. But plet subagents are already designed for full autonomy (FB_3) — they need unrestricted tool access anyway.

**Impact on PLAN_8:** This changes `plet_orchestrator.py` from "helper commands the skill calls" to potentially "the orchestrator itself." The `assemble-prompt` command becomes the bridge — it produces the exact prompt text that gets piped to `claude -p`.

**Open questions:**
- Does `claude -p` support all the tools subagents need (Read, Write, Edit, Bash, Grep, etc.)? Need to verify capabilities in one-shot mode.
- How does the script detect subagent success vs failure? Exit codes? Parsing stdout for state file updates? Having the subagent write state files directly (already the design)?
- Can `claude -p` run in worktree-isolated mode? Or does the script need to manage worktrees itself (which it could — `git worktree add/remove` is trivial to script)?
- What's the interaction model? The script runs as a `Bash()` tool call from a parent Claude session? Or the user runs it directly from terminal? Both?
- How does the user set breakpoints, pause, or intervene? Current design uses `state.json` breakpoints read by the orchestrator — that still works since the script reads state.json too.
- Cost/billing visibility — does `claude -p` usage show up in the same billing/usage tracking?

**Not a v1 blocker** — the current skill-as-orchestrator design works. But this could be a v2 architectural shift that eliminates the entire compaction recovery protocol and most orchestrator drift categories. Worth prototyping after PLAN_9 (comparison runs validate the current architecture first).

#### Full script inventory for script-as-orchestrator (2026-03-15)

If the loop orchestrator becomes a Python script, the full inventory of plet scripts is 10 scripts across 3 categories.

**Cross-cutting (used by multiple phases):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_state.py` | Per-iteration state CRUD + validation | `validate`, `update-criterion`, `update-field`, `init` | Exists |
| `plet_entries.py` | Runtime artifact entries | `add-progress`, `add-learning`, `add-emergent`, `check` | Exists |
| `plet_fingerprint.py` | Fingerprint generation, comparison, staleness detection | `generate`, `compare`, `check` | New |
| `plet_git.py` | Git compliance layer | `branch-name`, `create-branch`, `audit-tag`, `squash`, `worktree-create`, `worktree-remove`, `check-stashes`, `cleanup-stashes` | New (absorbs `plet_git_cleanup.py`) |
| `plet_trace.py` | Trace NDJSON schema enforcement | `validate`, `append-event`, `query` | New (already in PLAN_8) |
| `plet_router.py` | Phase detection + status | `detect`, `status`, `preflight` | New (absorbs pre-flight checker) |
| `plet_inject_prompt.py` | Prompt assembly for subagents | `assemble` (given iteration ID + phase, reads reference files, iteration def, requirements, learnings, state; outputs complete prompt text) | New |

**Loop-specific (the orchestrator):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_orchestrator.py` | The orchestrator itself | `start-session`, `end-session`, `eligible`, `check-retry`, `run` | New |

`run` is the main loop — calls `plet_router.py preflight`, `plet_fingerprint.py check`, then cycles: `eligible` → `plet_inject_prompt.py assemble` → spawn `claude -p` → capture output → read updated state → `check-retry` → repeat until done.

**Note:** `check-breakpoints` may move to its own script or stay in `plet_orchestrator.py` — TBD based on whether other phases need breakpoint checking.

**Phase checkpoint scripts (called by subagents, not the orchestrator):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_gate_impl.py` | Implementation phase gates | `pre` (spec exists, iteration state correct, branch correct), `post` (entries exist via `plet_entries.py check`, state updated, tests pass) | New |
| `plet_gate_verify.py` | Verification phase gates | `pre` (impl committed, entries exist), `post` (verification report written, lifecycle updated, all criteria resolved) | New |

**Rationale for separate impl/verify checkpoint scripts:** Impl and verify are different agents with different contexts, different failure modes, and different checklist items. A combined script would need phase-conditional logic throughout. Separate scripts keep each focused and make `allowed-tools` entries precise — the impl agent gets `plet_gate_impl.py`, the verify agent gets `plet_gate_verify.py`.

**Rationale for `plet_inject_prompt.py` as standalone:** Prompt assembly is the highest-value command in the system — it's the bridge between deterministic state reading and Claude invocation. Making it standalone means: (1) it can be tested independently, (2) it can be called outside `plet_orchestrator.py` (e.g., manual debugging: "show me what prompt the impl agent would get"), (3) it keeps `plet_orchestrator.py` focused on orchestration logic.

**Summary:**
- Exists: 2 (`plet_state.py`, `plet_entries.py`)
- New: 8
- Total: 10
- Absorbed from PLAN_8: `plet_git_cleanup.py` → `plet_git.py`, pre-flight checker → `plet_router.py`, post-impl/post-verify → `plet_gate_impl.py`/`plet_gate_verify.py`, pre-phase context → `plet_inject_prompt.py`

**Monitor:** `plet_git.py` has the most commands (8) across 4 concerns (branches, worktrees, tags, squash/stash). If it gets unwieldy during implementation, split into `plet_branch.py`, `plet_worktree.py`, `plet_tag.py`, `plet_stash.py`. Keep as-is for now — assess during build.

#### Script specs location — specs/ at project root (2026-03-15)

Each script gets its own behavioral spec file in `specs/` at the project root. Not inside the skill package — specs are about what to build, not part of the shipped artifact.

**Why not subsections of prd.md:** Each script has enough edge cases and behavioral nuances that one line or one section per script doesn't work — too thin or too heavy for the main PRD. Per-script files grow organically as edge cases are discovered.

**Why not inside skills/plet/scripts/:** Specs are design artifacts, not shipped code. Clean separation between "what to build" (specs/) and "how to build" (scripts/CLAUDE.md) and "the built thing" (scripts/*.py).

**Shape:** Lightweight behavioral specs — purpose, command signatures, input/output contracts, edge cases, error behaviors. No PRD ceremony (no personas, milestones, success metrics). Closer to how `state-schema.md` and `formats.md` define contracts than how `prd.md` defines requirements.

**Structure:**
```
specs/
├── prd.md                 # existing prd.md, moved here
├── plet_fingerprint.md
├── plet_git.md
├── plet_trace.md
├── plet_router.md
├── plet_inject_prompt.md
├── plet_orchestrator.md
├── plet_gate_impl.md
├── plet_gate_verify.md
└── (plet_state.md, plet_entries.md — retroactive, written during PLAN_8)
```

**Rejected:** Single tooling section in prd.md (can't capture per-script edge cases), separate prd-tooling.md (unnecessary ceremony), specs inside skill package (conflates design artifacts with shipped code), no specs at all (loses traceability).

**Decision:** PRD keeps its familiar name (`prd.md`) in the new location for now — easy to change later.

#### PLAN_7 triage reshaped by script-as-orchestrator (2026-03-15)

The script-as-orchestrator architecture changes the resolution path for most PLAN_7 feedback items. Of 26 open items:

- **5 already resolved** (FB_36, FB_37, FB_41, FB_42, FB_45) — withdrawn or done in earlier sessions
- **12 defer to PLAN_8 tooling** — problems caused by orchestrator drift or agent non-compliance that the scripts handle deterministically. No prose fixes needed.
- **5 need PLAN_7 prose fixes** — all plan session issues (FB_24–FB_28) unaffected by the orchestrator change
- **4 research/minor** — triage individually (FB_21, FB_34, FB_39, FB_43) plus FB_44 as a `plet_entries.py` enhancement

**Key insight:** The plan session is the only phase still fully skill-driven (interactive, judgment-heavy). Its feedback items are the only ones that need prose fixes. Loop and verify issues are almost entirely subsumed by the script orchestrator and gate scripts.
