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

### Section abbreviations

**Top-level sections** (used as: `ORC_EDG_1`):

| Abbrev | Section | Notes |
|--------|---------|-------|
| PUR | Purpose | §1 |
| AGT | Agent Personas | §2 |
| EDG | Edge Cases | §4 |
| ERR | Error Handling | §5 |
| FMT | Formats | §6 |
| AFL | Agent Flows | §7 |
| EXM | Examples | §8 |
| DEP | Dependencies | §9 |
| NFR | Non-Functional Requirements | §10 |
| DXP | Developer Experience | §11 |
| CRT | Critical Test Areas | §12 |
| TST | Testing & Verification | §13 |
| FUT | Future Considerations | §15 |

Sections 14 (Resolved Questions) and 16 (FB Items) don't get IDs — they reference existing IDs.

**Command sub-sections** (used as: `STA_VAL_BHV_1`):

| Abbrev | Sub-section | Notes |
|--------|-------------|-------|
| JUS | Justification | Why the command exists, when it's used, deprecation signals |
| CMD | Definition | What the command is, usage signature. Includes Properties and Concurrency annotations. |
| INP | Inputs | Arguments, flags, expected formats |
| OUT | Outputs | Stdout, stderr, exit codes |
| PRE | Preconditions | What must be true before the command runs. Violated precondition = specific error. |
| PST | Postconditions | What is guaranteed after successful completion. Each postcondition = a test assertion. |
| BHV | Behaviors | What the command does, rules, logic |

**Top-level sections** added in template update:

| Abbrev | Section | Notes |
|--------|---------|-------|
| EXM | Examples | §8 — copy-pasteable multi-step command sequences |

Each command also has its own 3-letter abbreviation (script-specific). Combined format: `SCRIPT_COMMAND_SUBSECTION_N`.

**Command abbreviations per script:**

| Script | Command | Abbrev |
|--------|---------|--------|
| STA | validate | VAL |
| STA | update-criterion | UPC |
| STA | update-field | UPF |
| STA | init | INI |
| ENT | add-progress | APR |
| ENT | add-learning | ALR |
| ENT | add-emergent | AEM |
| ENT | check | CHK |

New scripts define their command abbreviations in their spec files. Add them to this table when defined.

**ID format examples:**
- `STA_VAL_BHV_1` — state script, validate command, behavior, requirement #1
- `ENT_APR_INP_3` — entries script, add-progress command, input, requirement #3
- `ORC_EDG_1` — orchestrator script, edge case #1 (top-level, no command segment)

Append-only, never renumber.

---

#### specs/ directory bootstrapped (2026-03-15)

Created `specs/` at project root with full infrastructure:
- `CLAUDE.md` — how to work in specs/
- `NOTES.md` — tooling decisions (migrated from root NOTES.md, which had grown to 12% tooling content and would grow more during PLAN_8)
- `conventions.md` — 30 universal requirements (UNV_*) derived from `scripts/CLAUDE.md`. The coding standards file defines *how* to build; conventions.md defines *what* to require. Requirement IDs make compliance auditable.
- `script_template.md` — 15-section template adapted from plet's PRD template
- `PLAN.md` — build order for 10 scripts
- 10 per-script spec files (placeholders)

#### Script spec template adapted from PRD (2026-03-15)

Mapped plet's PRD template (plan.md §1–§14) to a lightweight script spec. Key adaptations:
- User Personas → **Agent Personas** (callers are agents, not end users)
- User Flows → **Agent Flows** (step-by-step invocation sequences)
- Data Models → **Input/Output Schemas** (JSON shapes, file formats)
- Release Milestones → omitted (scripts ship with plet skill)
- Success Metrics → omitted (scripts either work or don't)
- Developer Experience → **kept** (agents are developers too — CLI ergonomics matter)
- Added: Edge Cases, Error Handling, FB Items Addressed (not in PRD template)

Decision to keep DX: even though scripts follow scripts/CLAUDE.md for coding standards, per-script CLI ergonomics (output format, help quality, agent-readability) warrant their own section.

#### Stable label naming decisions (2026-03-15)

- `GIT` rejected as too generic for `plet_git.py` — chose `GCL` (Git CompLiance)
- `CTA` rejected for Critical Test Areas (commonly means Call To Action) — chose `CRT`
- Agent Flows abbreviated as `AFL` (not `FLO` from initial proposal)
- `UNV` chosen for universal/shared conventions (over CMN, SCV)
- 3-letter prefixes per stable-label convention (existing PRD uses 2-letter from ridl-skills legacy; new prefixes use 3)

#### Build order rationale (2026-03-15)

10 scripts ordered: existing first (validate template), leaves before dependents, gates before orchestrator, orchestrator last (capstone). See `specs/PLAN.md` for full order and rationale per script.

#### Template expanded with pre/post, examples, properties, concurrency (2026-03-15)

Four additions to the per-command template structure:

1. **Preconditions (PRE)** — what must be true before the command runs. Every violated precondition should produce a specific error. Biggest gap in the original template — BHV says what happens, but not what must hold first.
2. **Postconditions (PST)** — what is guaranteed after successful completion. Each postcondition maps directly to a test assertion, making the testing section nearly mechanical.
3. **Properties annotation** on CMD — one-liner: read-only|mutating, idempotent|not, atomic|non-atomic. Tells agents at a glance which commands are safe to retry.
4. **Concurrency annotation** on CMD — one-liner: safe|single-writer|see NFR. Per-command rather than script-level because different commands have different concurrency profiles (e.g., `validate` is safe, `update-field` is single-writer).

Also added §8 Examples (EXM) as a top-level section — real copy-pasteable multi-step sequences with realistic data. More expansive than help text, more concrete than Agent Flows.

Template is now 16 sections (was 15). Per-command sub-sections: 7 (was 4, added JUS, PRE, and PST). Section numbering shifted: Examples at §8, Dependencies at §9, etc.

#### Key Insight: Agent-First CLI Design (2026-03-16)

These scripts are **agent tools** that humans occasionally debug — not developer tools that agents happen to use. That inversion changes the entire CLI design philosophy:

- **Predictability over ergonomics** — named args everywhere, no positional shortcuts. Agents generate commands programmatically; brevity doesn't matter, consistency does.
- **Defensive validation** — treat agents as potentially careless users. Every input validated, every error path caught. Scripts must never produce Python tracebacks.
- **Self-documenting output** — `--output json` on every command. Machine-parseable with metadata (status, command, version, timestamp). Error output includes actionable recovery info (e.g., valid values, available IDs).
- **Safe by default** — `--dry-run` required on all mutating commands. Help text **strongly recommends** dry-run before mutation, with the recommendation appearing near the top of help output (before usage details).
- **Context-aware help** — help text uses 4-section structure: IMPORTANT → PITFALLS → USAGE → PURPOSE. Warnings and gotchas before syntax. Purpose last (agent already decided to run it). Agent guidance first, additional content welcome.
- **Single resource per invocation** — scripts operate on one file/entity. Agents control the loop (how many, stop early, parallelize). Predictable output size per call. No multi-file aggregation in scripts. **Exception:** commands whose primary job is producing a list from multiple resources (e.g., scanning all state files for eligible iterations). When the list IS the output, multi-resource scanning is the point — but `--fields` is especially critical for these commands.
- **Context window protection** — `--fields field1,field2` limits JSON output. Response includes `fieldsIncluded` and `fieldsOmitted` so the agent knows what was filtered. Especially critical for commands that could return large output even for a single resource (validation errors, entry listings). Help text should strongly recommend `--fields` for high-output commands.

This insight was driven by the open question about positional args but applies across all conventions. Six requirements added/modified: UNV_CMD_10 (named args only), UNV_CMD_15 (output format), UNV_CMD_17 (--dry-run), UNV_CMD_18 (--output json), UNV_DXP_5 (help as guidance), UNV_ERR_4 (no unhandled exceptions).

#### Open questions #2-4 resolved: agent-first CLI design (2026-03-16)

All three remaining open questions resolved by the agent-first CLI design insight:
- **#2 (positional args):** Fix — only file path stays positional. Everything else named.
- **#3 (update-field pairs):** Fix — migrate to named args. Alternating pairs were a human ergonomic shortcut.
- **#4 (boolean flags):** Required — `--dry-run` and `--output json` are boolean flags on every mutating command. `parse_kwargs` must support them.

#### skipRationale field deprecated (2026-03-16)

**Decision:** Remove `skipRationale` as a separate field. When `--status skipped`, the `--evidence` field serves as the skip rationale. Validator checks evidence is non-empty for skipped criteria instead of checking for `skipRationale`.

**Rationale:** `skipRationale` was always a copy of what `evidence` already contained. Separate field is redundant data in the JSON. Simplifies the two-state model.

**Cascading changes needed:**
- `references/state-schema.md` — remove `skipRationale` from criterion schema
- `skills/plet/scripts/plet_state.py` — validator checks evidence non-empty for skipped, not skipRationale
- `references/execute.md`, `references/verify.md` — note that evidence acts as rationale for skipped criteria
- Existing state files with `skipRationale` — harmless extra field, validator ignores it

**Monitor:** If agents produce poor skip rationale using the evidence framing, consider renaming `--evidence` to `--reason` or adding `--skip-rationale` as an alias.

#### update-field migrated to --data JSON object (2026-03-16)

**Decision:** `update-field` accepts `--data '{"field":"value"}'` instead of alternating positional pairs (`field value field value`).

**Rationale (agent-first):**
- Agents think in JSON — it's their native output format. Generating `'{"lifecycle":"implementing"}'` is trivial.
- One format, zero ambiguity — no `=` splitting edge cases, no repeated-flag collection, no shell quoting surprises.
- Consistent with existing patterns — `--criteria` and `--dependencies` in `init` already accept JSON strings.
- All value types for free — strings, numbers, booleans, arrays, objects, null. No special handling per type.
- Simplest implementation — one `json.loads()` call + iterate keys.

**Rejected:**
- `--set key=value` (repeated flag) — common pattern (docker, kubectl) but introduces `=` splitting edge cases. Values containing `=` need first-split-only logic. Repeated flag collection is a new pattern for `parse_kwargs`.
- `--field`/`--value` pairs — most consistent with parse_kwargs but extremely verbose. Double the tokens of other options.
- Keep alternating positional pairs — violates UNV_CMD_10 (named args only). Was a human ergonomic shortcut; agents don't benefit from it.

#### Open question #1 resolved: shared utility modules (2026-03-16)

**Decision:** Extract shared patterns into internal utility modules. Two files: `util_cli.py` (argument parsing, validation, timestamps, dispatch) and `util_io.py` (atomic JSON writes, atomic appends, JSON loading).

**Naming convention:** `plet_*.py` = CLI tool (callable via Bash, listed in allowed-tools, executable). `util_*.py` = internal module (imported by plet scripts, never called directly, not in allowed-tools, not executable). The prefix signals the file's role at a glance.

**Why two files, not one:** Sets precedent for separation by concern even though ~150 lines would fit in one file. CLI concerns (args, validation, dispatch) are conceptually distinct from I/O concerns (atomic writes, JSON loading). Easier to test in isolation.

**Why not copy-paste:** 10 scripts × ~10 shared functions = 100 copies to maintain. An internal module is a different kind of dependency than a third-party package — it ships in the same directory, same version, same deployment. The "zero deps" constraint (UNV_CMD_1) is about external packages agents can't install.

**Testing note:** Internal modules are tested via direct import, not subprocess — a new pattern. Every other test calls scripts via `subprocess.run()`. The util tests import functions directly since there's no CLI interface to test.

#### Justification sub-section added per command (2026-03-15)

Each command now has a Justification (JUS) section — first sub-section, before Definition. Three requirements:
1. **Why** — what problem this command solves that no other command covers
2. **When** — the specific workflow context where it's invoked
3. **Deprecation signal** — conditions under which the command becomes redundant

Motivation: `init` might become unnecessary if other commands auto-create files. Without documenting the deprecation signal, we'd never know when to simplify. Commands should justify their existence, not just describe their behavior — especially in a 10-script system where overlap is likely.

#### Commands section restructured with sub-sections (2026-03-15)

§3 Commands was too broad — a single section for definitions, inputs, outputs, and behaviors. Restructured into four sub-sections per command, each with its own abbreviation:
- `CMD` — definition (what it is, usage signature)
- `INP` — inputs (arguments, flags, formats)
- `OUT` — outputs (stdout, stderr, exit codes)
- `BHV` — behaviors (rules, logic, side effects)

Each command also gets a 3-letter abbreviation (script-specific). Full ID format: `SCRIPT_COMMAND_SUBSECTION_N` (e.g., `STA_VAL_BHV_1`).

Template updated. Both retroactive specs (STA, ENT) updated with stable labels throughout.

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
├── plet_state.md
├── plet_entries.md
├── plet_fingerprint.md
├── plet_git.md
├── plet_trace.md
├── plet_router.md
├── plet_inject_prompt.md
├── plet_orchestrator.md
├── plet_gate_impl.md
└── plet_gate_verify.md
```

`prd.md` stays at project root — it's the plet PRD, not a script spec. `specs/` is exclusively for script behavioral specs.

**Rejected:** Single tooling section in prd.md (can't capture per-script edge cases), separate prd-tooling.md (unnecessary ceremony), specs inside skill package (conflates design artifacts with shipped code), no specs at all (loses traceability), moving prd.md into specs/ (PRD is a different artifact type — mixing it with script specs muddies the directory's purpose).

#### ENT spec review decisions (2026-03-16)

Decisions made during §2–§3.1 review of `plet_entries.md`:

1. **GUI persona added (ENT_AGT_7):** External GUI reads artifact files directly for visualization. Same pattern as STA_AGT_8. Drives atomic append requirement — GUI must never see partial entries.

2. **Plan session agent added (ENT_AGT_8):** Plan agent writes progress entries after key milestones (requirements approved, iterations defined, state initialized). Uses `add-progress` only.

3. **Refine agent uses add-learning (ENT_AGT_3 updated):** Refine sessions produce learnings from triage patterns. Was `add-progress, add-emergent` → now `add-progress, add-learning, add-emergent`.

4. **`plan` added as valid phase:** Phase list is now `plan, impl, verify, refine` (in workflow order). Plet ID segment: `p` (plan-1 → `p1`). Affects all command INP sections, error messages, format table.

5. **Phase ordering convention:** Always list in workflow order: plan, impl, verify, refine. Not alphabetical, not by frequency.

6. **Universal Inputs section (spec + template):** Universal flags (`--output json`, `--pretty`, `--fields`, `--dry-run`) listed once in a table under §3 before per-command sections. Each flag notes which commands it applies to, explicitly stating `--dry-run` is NOT available on read-only commands. Template updated with this convention.

7. **`--summary-file` flag added (ENT_APR_INP_9, P1):** Reads summary from a file path. Resolves FB_44 (multiline progress content). Mutually exclusive with `--summary`. Use for long content awkward as shell args (plan milestones, blocker details). ENT_FUT_1 marked resolved.

8. **Blocker content embedded in summary:** BLOCKED entries include "Work completed:" and "Work remaining:" sections as part of `--summary` or `--summary-file` content. Tool stays thin — enforces the envelope (fencing, metadata, IDs), content is freeform. Rejected separate `--work-completed`/`--work-remaining` flags. **Rationale:** adding flags for every format variant doesn't scale. The div fencing gives GUI entry boundaries; within entries, markdown structure is parseable enough.

9. **IN_PROGRESS added to valid progress statuses:** Status list is now IN_PROGRESS, COMPLETE, BLOCKED, FAILED, SKIPPED, MIGRATED. Needed for interim "as things come up" entries (EX_9) and plan session checkpoints. COMPLETE for a checkpoint is misleading — IN_PROGRESS is honest. **--status remains required** (not optional with default) — agent must always specify.

10. **Missing entries motivation (ENT_APR_JUS_1):** Added second failure mode: entries went missing during runs, possibly from agents erroneously removing/overwriting when composing markdown freehand. Atomic append addresses both format drift and content loss.

#### Unified entry format — KV metadata + freeform content block (2026-03-16)

**Decision:** All three runtime artifact entry types (progress, learning, emergent) share the same structural pattern: KV metadata lines on top, then a `**Content:**` marker, then freeform content until the end fence.

**Structure:**
```
<div id="plet-{id}"></div>

---

### [header]
**Key:** value
**Key:** value
...
**Content:**
[freeform content — everything until end fence]

<div id="END-plet-{id}"></div>
```

**What moves to KV section:**
- Progress: Files changed stays as KV (`**Files changed:**` + bullet list above the content marker)
- Emergent: Outcome stays as KV (`**Outcome:** pending` above the content marker)

**CLI flag unification:** `--summary` (progress) and `--content` (learning/emergent) unified to `--content` and `--content-file` across all three commands. `--summary-file` becomes `--content-file`.

**Fencing safety:** Content must not contain fence patterns (`<div id="plet-` or `<div id="END-plet-`). Script rejects with error if detected. Agent-first: fail loudly rather than silently escaping.

**Rationale:**
- Tool is simpler (one builder pattern, not three)
- GUI is simpler (one parser — scan for `**Content:**` line, everything after it is the body)
- Format is easier to explain and extend
- `**Content:**` marker makes the KV→freeform boundary explicit and machine-parseable

**Cascading changes needed:**
- `references/formats.md` — update all three entry format templates
- `specs/plet_entries.md` — rename --summary/--summary-file to --content/--content-file for add-progress, unify INP/BHV sections
- `prd.md` — RT_1 description may need update (references "summary")
- Existing case study artifacts — old format still parseable (fencing unchanged), but new entries use new format

**Impact:** This is a format change. Per RT_10 (additive only), adding the `**Content:**` marker is additive. Moving Files changed and Outcome above the content marker changes field ordering but not field names. Considered acceptable for pre-v1.

#### KV section consistency across entry types (2026-03-16)

Unified the KV metadata sections across all three entry types:

1. **No bullets on emergent** — was `- **Key:**`, now `**Key:**` like progress/learning.
2. **PletId always first, Timestamp always second** — consistent ordering.
3. **Iteration field unified** — all three use `**Iteration:** [ID_xxx] [iteration title]`. Emergent's `**Source:**` renamed to `**Iteration:**` (same data, same format).
4. **Phase added to learning** — progress and emergent had Phase, learning didn't. Now all three carry Phase. Attempt NOT added to learning (noise for knowledge entries; plet ID encodes it).

**CLI flag rename:**
- `--iteration` → `--iter-id` (iteration ID)
- `--title` on progress → `--iter-title` (iteration title)
- `--source` on emergent → `--iter-title` (was composing `[ID] title`, now uses same flag as progress)
- `--title` stays on learning/emergent = the item's own title (goes in ### header)
- New `--iter-title` added to learning (was missing iteration title entirely)

**Rationale:** `--iter-id` and `--iter-title` are always about the iteration. `--title` is always about the item. No collisions, no dual meanings. The `--iter` prefix groups iteration fields visually.

#### ENT spec review decisions continued (2026-03-17)

Decisions made during §3.4–§9 review of `plet_entries.md`:

11. **check validates --iter-id format:** Same `ID_N+` or `proj` validation as plet_state.py. Catches typos early — an agent passing "id_001" would get 0 entries and think entries are missing when really the search pattern is wrong.

12. **NOT_INITIALIZED vs MISSING in check (BHV_4/BHV_5):** Missing artifact file is NOT the same as "0 entries." If the file doesn't exist, nothing can create entries (add-* commands require existing files). Split into two behaviors: BHV_4 (file exists, 0 entries → MISSING), BHV_5 (file doesn't exist → NOT_INITIALIZED). JSON includes `initialized` boolean per artifact. Both exit 1.

13. **Empty content is an error (EDG_15/16, ERR_15):** Both `--content ""` and empty `--content-file` produce an error. An entry with no content is useless.

14. **--files non-array JSON is an error (EDG_17, ERR_16):** Explicit validation — passing a string or object instead of array gets a clean error.

15. **--content-file permissions error (EDG_18, ERR_17):** Distinct from "not found" — clean error message with reason.

16. **--iter-id validated on all commands (ERR_18):** Not just check — add-progress, add-learning, add-emergent all validate `ID_N+` or `proj` format.

17. **--attempt > 0 enforced (ERR_19):** "Positive integer" means > 0 explicitly. Zero and negative values get specific error.

18. **AFL_4: Plan session milestone flow:** Plan agent writes progress entry after key milestones using `--iter-id proj --phase plan`.

19. **EXM_4/5 added:** Plan session milestone example + IN_PROGRESS interim checkpoint example.

20. **DEP_2 updated:** util_io dependency includes `load_text` for --content-file support.

#### load_text added to util_io (2026-03-17)

**Decision:** Add `load_text(path)` to `util_io.py` — parallel to `load_json`. Returns string on success, None on failure. Clean errors to stderr for: file not found, not readable, empty. Used by `--content-file` in plet_entries.py and any future scripts that read plain text files from CLI args.

**Rationale:** `--content-file`, `--data` (plet_state), and similar file-reading flags all need the same error handling pattern. Centralizing in util_io eliminates drift across scripts for the common failure modes (not found, permissions, empty).

#### PLAN_7 triage reshaped by script-as-orchestrator (2026-03-15)

The script-as-orchestrator architecture changes the resolution path for most PLAN_7 feedback items. Of 26 open items:

- **5 already resolved** (FB_36, FB_37, FB_41, FB_42, FB_45) — withdrawn or done in earlier sessions
- **12 defer to PLAN_8 tooling** — problems caused by orchestrator drift or agent non-compliance that the scripts handle deterministically. No prose fixes needed.
- **5 need PLAN_7 prose fixes** — all plan session issues (FB_24–FB_28) unaffected by the orchestrator change
- **4 research/minor** — triage individually (FB_21, FB_34, FB_39, FB_43) plus FB_44 as a `plet_entries.py` enhancement

**Key insight:** The plan session is the only phase still fully skill-driven (interactive, judgment-heavy). Its feedback items are the only ones that need prose fixes. Loop and verify issues are almost entirely subsumed by the script orchestrator and gate scripts.

#### ENT spec §10–§11 review decisions (2026-03-17)

- **ENT_NFR_4** qualified: "within a single-writer scenario" — parallel EM_N races acknowledged, resolved during refine
- **ENT_NFR_5** added: cross-file concurrent appends allowed (no cross-file locking)
- **ENT_NFR_6** added: external readers must never see partial entries (atomic append guarantee for GUI consumers)
- **ENT_DXP_6** added: PITFALLS must list common wrong values agents try (e.g., `complete` vs `COMPLETE`, `implementation` vs `impl`)
- **ENT_DXP_7** added: help text documents flag dependencies (--pretty/--fields require --output json, --content/--content-file mutually exclusive)
- **Open question resolved (--status):** `--status` stays required for consistency. IN_PROGRESS is suppressed from the header line (ENT_APR_BHV_8) — visually clean without sacrificing CLI consistency. Formats.md updated.
- **ENT_FUT_5 withdrawn:** BLOCKED --work-completed/--work-remaining won't be CLI flags. BLOCKED details are content guidance for agents. Info is recoverable from state files, tests, and git history if omitted.

#### ENT spec §12–§16 + audit findings review (2026-03-17)

- **ENT_CRT_10** added: --content-file handling test area (file not found, empty, permissions, mutual exclusivity)
- **ENT_CRT_11** added: check command accuracy test area (counts, NOT_INITIALIZED vs 0, exit codes)
- §13 (Testing) approved as-is — shebang covered by conventions reference
- §14 (Resolved Questions) approved — RQ_10 and RQ_11 added for status suppression and BLOCKED decisions
- §15 (Future): ENT_FUT_1 resolved (cross-ref to RQ_7), ENT_FUT_5 withdrawn
- §16 (FB Items): FB_44 updated to resolved via --content-file
- Audit findings approved — 9 implementation tasks guide Seq 3 implementation
- **ENT spec complete** — all 16 sections reviewed and approved

#### ENT spec holistic review recommendations (2026-03-17)

- **ENT_FUT_2 promoted:** --content-file added to all three add-* commands (ALR_INP_9, ALR_PRE_7/8, ALR_BHV_6, AEM_INP_9, AEM_PRE_7/8, AEM_BHV_7). Near-zero marginal cost during rewrite.
- **Fence rejection clarified:** applies regardless of content source (--content or --content-file). All three BHV fence rules updated.
- **check restricted to ID_N+:** `proj` removed from ENT_CHK_PRE_3. R_7 mandatory rule is per-iteration; project-level entries are optional milestones. Open question added for what a proj-level check might look like.
- **EXM_5 updated:** shows IN_PROGRESS suppression per ENT_APR_BHV_8.

#### STA spec holistic review (2026-03-17)

- **Audit findings cleared:** all 22 findings resolved in implementation (verified 2026-03-17). Items removed, section kept empty for future audits.
- **STA_ERR_24 removed:** no mutual exclusions exist — specifying an error for a non-existent case was misleading. Add back when needed.
- **Open Questions promoted:** moved from inline note under §14 to a proper Open Questions section matching ENT format.
- STA_FUT_1 (schema migration) left as future — no schema changes yet.
- **--data-file added:** STA_UPF_INP_3, STA_UPF_PRE_6, STA_UPF_BHV_6, STA_ERR_25–28, STA_EDG_17–19. Consistent with ENT's --content-file pattern. STA_FUT_5 (stdin) withdrawn.

#### UNV_CMD_24/25: Help hint on errors (2026-03-17)

- **Decision:** Validation errors print a one-line hint (`Run: <script> <command> --help`) instead of the full HELP text. Full HELP only printed for missing-required-args errors.
- **Why:** Full HELP after every error floods the agent's context window. Validation errors already say what's valid (e.g., "valid: plan, impl, verify, refine"). The hint nudges without noise.
- **Alternatives rejected:** (A) Full HELP on all errors — too noisy, wastes context. (B) No hint at all — agents may not know --help exists.
- **UNV_CMD_25 (split):** Hint goes to stderr only — never in JSON error payloads on stdout. Agents see both streams via Bash tool; programmatic callers capture them separately.
- **Added as:** UNV_CMD_24 + UNV_CMD_25 in conventions.md, updated scripts/CLAUDE.md output convention. Pattern implemented in plet_entries.py via `help_hint()` helper.
- **Applied to:** plet_entries.py (via `help_hint()`) and plet_state.py (2026-03-17).

#### UNV_IMP_1: Resolve missing util deps before impl (2026-03-17)

- **Decision:** Before implementing a script, check its Dependencies section for imports from `util_*.py`. If any listed function doesn't exist yet, build it first.
- **Why:** util_io was created for STA's needs. ENT spec declared `load_text` as a dependency, but nobody built it before starting ENT impl. Gap went unnoticed until implementation.
- **Added as:** UNV_IMP_1 in conventions.md § Implementation Prerequisites. `load_text` added to util_io.py.

#### --iteration-id → --iter-id rename (2026-03-17)

- **Decision:** Renamed plet_state.py's `--iteration-id` flag to `--iter-id` for consistency with plet_entries.py.
- **Why:** Agents switch between the two scripts constantly. Having `--iteration-id` on one and `--iter-id` on the other is the kind of inconsistency that causes mistakes. One less thing to memorize.
- **Scope:** plet_state.py (script + tests), STA spec, plan.md, script_template.md, scripts/CLAUDE.md, util_cli.py docstrings, test_util_cli.py.
