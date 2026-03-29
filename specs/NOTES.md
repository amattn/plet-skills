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
| GTI | `plet_git_iteration.py` | GT Iteration lifecycle |
| GTO | `plet_git_ops.py` | GT Operations |
| GTC | `plet_git_check.py` | GT Check |
| TRC | `plet_trace.py` | TRaCe |
| GSS | `plet_gate_session.py` | Gate SeSsion (renamed from plet_session.py) |
| SES | `plet_session.py` (new) | SESsion lifecycle (prefix reused after rename) |
| SCH | `plet_schedule.py` | SCHedule |
| PRM | `plet_prompt.py` | PRoMpt |
| ORC | `plet_orchestrator.py` | ORChestrator |
| GPH | `plet_gate_phase.py` | Gate PHase |
| ~~GIM~~ | ~~`plet_gate_impl.py`~~ | Merged into GPH |
| ~~GVR~~ | ~~`plet_gate_verify.py`~~ | Merged into GPH |
| INV | `plet_invoke.py` | INVoke |

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
| FPR | extract | EXT |
| FPR | embed | EMB |
| FPR | check | CHK |
| TRC | append-event | APE |
| TRC | validate | VAL |
| TRC | query | QRY |
| GTI | branch-name | BRN |
| GTI | worktree-create | WTC |
| GTI | worktree-remove | WTR |
| GTO | audit-tag | ATG |
| GTO | merge-squash | MSQ |
| GTC | check-iteration | CKI |
| GTC | check-session | CKS |
| SES | detect | DET |
| SES | status | STS |
| SES | preflight | PRF |
| GPH | pre | PRE |
| GPH | post | PST |
| PRM | assemble | ASM |
| INV | run | RUN |

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

This insight was driven by the open question about positional args but applies across all conventions. Six requirements added/modified: UNV_CMD_10 (named args only), UNV_CMD_15 (output format), UNV_CMD_26 (--dry-run), UNV_CMD_18 (--output json), UNV_DXP_5 (help as guidance), UNV_ERR_4 (no unhandled exceptions).

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
- `references/implement.md`, `references/verify.md` — note that evidence acts as rationale for skipped criteria
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
6/9. Spawn subagents (implement + verify) — prompt payload assembly is deterministic (which files, which order), spawning + adaptation is skill
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
- `assemble-prompt` — given iteration ID + phase (implement/verify), read the iteration definition from `iterations.md`, assemble the full injection payload (reference file contents, formats.md sections, state-schema.md sections, requirements.md, learnings.md, per-iteration state). Output the assembled prompt text to stdout. The orchestrator skill pipes this to the Agent tool.

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

**What stays as Claude:** Only implement and verify subagents — the parts requiring judgment. Spawned as one-shot CLI processes with assembled prompts.

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
| `plet_fingerprint.py` | Fingerprint extraction, embedding, staleness detection | `extract`, `embed`, `check` | New |
| `plet_git.py` | Git compliance layer | `branch-name`, `create-branch`, `audit-tag`, `squash`, `worktree-create`, `worktree-remove`, `check-stashes`, `cleanup-stashes` | New (absorbs `plet_git_cleanup.py`) |
| `plet_trace.py` | Trace NDJSON schema enforcement | `validate`, `append-event`, `query` | New (already in PLAN_8) |
| `plet_router.py` | Phase detection + status | `detect`, `status`, `preflight` | New (absorbs pre-flight checker) |
| `plet_inject_prompt.py` | Prompt assembly for subagents | `assemble` (given iteration ID + phase, reads reference files, iteration def, requirements, learnings, state; outputs complete prompt text) | New |
| `plet_invoke.py` | Subprocess launch + transcript capture | `run` (assembles prompt via plet_inject_prompt, launches `claude -p --output-format stream-json`, tees JSONL to transcript file, returns exit code) | New |

**Loop-specific (the orchestrator):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_orchestrator.py` | The orchestrator itself | `start-session`, `end-session`, `eligible`, `check-retry`, `run` | New |

`run` is the main loop — calls `plet_router.py preflight`, `plet_fingerprint.py check`, then cycles: `eligible` → `plet_invoke.py run` (assembles prompt + launches subprocess + captures transcript) → read updated state → `check-retry` → repeat until done.

**Note:** `check-breakpoints` may move to its own script or stay in `plet_orchestrator.py` — TBD based on whether other phases need breakpoint checking.

**Phase checkpoint scripts (called by subagents, not the orchestrator):**

| Script | Purpose | Key commands | Status |
|--------|---------|-------------|--------|
| `plet_gate_impl.py` | Implementation phase gates | `pre` (spec exists, iteration state correct, branch correct), `post` (entries exist via `plet_entries.py check`, state updated, tests pass) | New |
| `plet_gate_verify.py` | Verification phase gates | `pre` (implement committed, entries exist), `post` (verification report written, lifecycle updated, all criteria resolved) | New |

**Rationale for separate implement/verify checkpoint scripts:** Impl and verify are different agents with different contexts, different failure modes, and different checklist items. A combined script would need phase-conditional logic throughout. Separate scripts keep each focused and make `allowed-tools` entries precise — the implement agent gets `plet_gate_impl.py`, the verify agent gets `plet_gate_verify.py`.

**Rationale for `plet_inject_prompt.py` as standalone:** Prompt assembly is the highest-value command in the system — it's the bridge between deterministic state reading and Claude invocation. Making it standalone means: (1) it can be tested independently, (2) it can be called outside `plet_orchestrator.py` (e.g., manual debugging: "show me what prompt the implement agent would get"), (3) it keeps `plet_orchestrator.py` focused on orchestration logic.

**Summary:**
- Exists: 2 (`plet_state.py`, `plet_entries.py`)
- New: 8
- Total: 10
- Absorbed from PLAN_8: `plet_git_cleanup.py` → `plet_git.py`, pre-flight checker → `plet_router.py`, post-implement/post-verify → `plet_gate_impl.py`/`plet_gate_verify.py`, pre-phase context → `plet_inject_prompt.py`

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

4. **`plan` added as valid phase:** Phase list is now `plan, implement, verify, refine` (in workflow order). Plet ID segment: `p` (plan-1 → `p1`). Affects all command INP sections, error messages, format table.

5. **Phase ordering convention:** Always list in workflow order: plan, implement, verify, refine. Not alphabetical, not by frequency.

6. **Universal Inputs section (spec + template):** Universal flags (`--output json`, `--pretty`, `--fields`, `--dry-run`) listed once in a table under §3 before per-command sections. Each flag notes which commands it applies to, explicitly stating `--dry-run` is NOT available on read-only commands. Template updated with this convention.

7. **`--summary-file` flag added (ENT_APR_INP_9, P1):** Reads summary from a file path. Resolves FB_44 (multiline progress content). Mutually exclusive with `--summary`. Use for long content awkward as shell args (plan milestones, blocker details). ENT_FUT_1 marked resolved.

8. **Blocker content embedded in summary:** BLOCKED entries include "Work completed:" and "Work remaining:" sections as part of `--summary` or `--summary-file` content. Tool stays thin — enforces the envelope (fencing, metadata, IDs), content is freeform. Rejected separate `--work-completed`/`--work-remaining` flags. **Rationale:** adding flags for every format variant doesn't scale. The div fencing gives GUI entry boundaries; within entries, markdown structure is parseable enough.

9. **IN_PROGRESS added to valid progress statuses:** Status list is now IN_PROGRESS, COMPLETE, BLOCKED, FAILED, SKIPPED, MIGRATED. Needed for interim "as things come up" entries (IMP_9) and plan session checkpoints. COMPLETE for a checkpoint is misleading — IN_PROGRESS is honest. **--status remains required** (not optional with default) — agent must always specify.

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
- **ENT_DXP_6** added: PITFALLS must list common wrong values agents try (e.g., `complete` vs `COMPLETE`, `implementation` vs `implement`)
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
- **Why:** Full HELP after every error floods the agent's context window. Validation errors already say what's valid (e.g., "valid: plan, implement, verify, refine"). The hint nudges without noise.
- **Alternatives rejected:** (A) Full HELP on all errors — too noisy, wastes context. (B) No hint at all — agents may not know --help exists.
- **UNV_CMD_25 (split):** Hint goes to stderr only — never in JSON error payloads on stdout. Agents see both streams via Bash tool; programmatic callers capture them separately.
- **Added as:** UNV_CMD_24 + UNV_CMD_25 in conventions.md, updated scripts/CLAUDE.md output convention. Pattern implemented in plet_entries.py via `help_hint()` helper.
- **Applied to:** plet_entries.py (via `help_hint()`) and plet_state.py (2026-03-17).

#### UNV_IPR_1: Resolve missing util deps before implement (2026-03-17)

- **Decision:** Before implementing a script, check its Dependencies section for imports from `util_*.py`. If any listed function doesn't exist yet, build it first.
- **Why:** util_io was created for STA's needs. ENT spec declared `load_text` as a dependency, but nobody built it before starting ENT implement. Gap went unnoticed until implementation.
- **Added as:** UNV_IPR_1 in conventions.md § Implementation Prerequisites. `load_text` added to util_io.py.

#### --iteration-id → --iter-id rename (2026-03-17)

- **Decision:** Renamed plet_state.py's `--iteration-id` flag to `--iter-id` for consistency with plet_entries.py.
- **Why:** Agents switch between the two scripts constantly. Having `--iteration-id` on one and `--iter-id` on the other is the kind of inconsistency that causes mistakes. One less thing to memorize.
- **Scope:** plet_state.py (script + tests), STA spec, plan.md, script_template.md, scripts/CLAUDE.md, util_cli.py docstrings, test_util_cli.py.

#### FPR spec — command naming (2026-03-17)

- **Decision:** Commands are `extract`, `embed`, `check` — not `generate`/`compare`/`check` (from earlier NOTES inventory) or `compute` (rejected: implies math, no actual computation).
- **Why:** `extract` is read-only and precise — it pulls IDs out of file content and assembles them into a fingerprint structure. `embed` is the write operation (puts the fingerprint into the file). `compare` is subsumed by `check` which compares across all levels.
- **Fingerprint block delimiters:** `<!-- plet:fingerprint -->` HTML comment fences in markdown files. Invisible when rendered, machine-parseable, won't collide with content.
- **embed auto-computes:** `embed` internally scans the file the same way `compute` does. No need to pipe `compute` output into `embed` — one command does both (scan + write).
- **All commands take artifact_dir:** All three commands (`extract`, `embed`, `check`) take `artifact_dir` (e.g., `plet/`) and derive file paths from there. All plet artifacts live in the same directory — no need for per-file path overrides. Originally `extract` took a file path (conceptual purity — it reads one file), but unified to `artifact_dir` for interface consistency across all three commands and with STA/ENT conventions. The flexibility loss is theoretical — plet artifacts always follow the standard layout.
- **embed does NOT validate:** `embed --type state` only updates the `iterationsFingerprint` field. Full state validation is `plet_state.py validate`'s job.
- **extract not compute:** `compute` implies math. `extract` is precise — pulls IDs from content, assembles structure. Resolved during §1 review.
- **GUI persona added:** FPR_AGT_6 — external GUI polls `check` for staleness alerts/banners.
- **Review status:** §1–§3.1 approved. §3.2 embed next.

#### FPR §3 universal flags review (2026-03-17)

- **Extract abbreviation fixed:** CMP → EXT throughout. CMP was a holdover from earlier "compute" naming. Fixed heading `### 3.1 extract (EXT)` and one stale cross-reference `CMP_BHV_6` → `FPR_EXT_BHV_6`. Command abbreviations (EXT, EMB, CHK) added to NOTES.md prefix table.
- **--bump stays command-specific:** `--bump` remains in §3.2 embed only, not added to the universal flags table. Rationale: `--dry-run` is in the universal table because it's a universal *pattern* that happens to apply to one command; `--bump` is semantically tied to embed's timestamp behavior and reads better with its context.
- **§3.1 EXT_JUS approved.** No changes.
- **§3.1 EXT_CMD approved.** Fixed stale file-path usage in FPR_EXM_1 (`plet/requirements.md` → `plet/`). Confirmed artifact_dir convention per earlier decision.
- **§3.1 EXT_INP approved.** No changes.
- **§3.1 EXT_OUT approved.** Fixed typo "extractd" → "extracted". Added `"path"` field to JSON envelope (FPR_EXT_OUT_2) — shows derived file path, matches embed's output. Text mode confirmed as bare fingerprint JSON (pipeable to jq, per FPR_DXP_4).
- **§3.1 EXT_PRE approved.** Added FPR_EXT_PRE_3 (target file must exist). Confirmed extract --type iterations does NOT require requirements.md — it reads the already-embedded requirementsFingerprint from iterations.md itself. Only embed cross-reads source files.
- **§3.1 EXT_PST approved.** No changes.
- **§3.1 EXT_BHV approved.** Three changes: (1) Fixed mtime fallback conflict — BHV_1 and BHV_2 now defer to BHV_6 (current UTC) instead of file modification time. mtime is fragile (git checkout resets it). (2) BHV_2 now specifies milestone grouping mechanism: parse `**Milestone:** MS_N` metadata line per iteration definition (matches plan.md iteration structure, no heading-based grouping). (3) BHV_2 now explicitly excludes withdrawn iterations (parallel with BHV_1's SY_8 exclusion).
- **§3.2 EMB_JUS approved.** No changes.
- **§3.2 EMB_CMD approved.** No changes.
- **§3.2 EMB_INP — auto-bump on content change.** `lastNonTrivialUpdate` auto-bumps when ID arrays change vs previously embedded fingerprint. `--bump` becomes a force-bump for prose-only changes that don't affect IDs. Rationale: if IDs changed, that's definitionally non-trivial — requiring manual `--bump` is exactly the compliance drift tooling exists to eliminate. Updated INP_3, PST_5, PST_6.
- **§3.2 EMB_OUT approved.** Added `autoBumped`/`forceBumped` booleans to JSON envelope (both can be true simultaneously). Text mode appends bump reason(s).
- **§3.2 EMB_PRE approved.** Added PRE_6 clarifying no precondition on previous fingerprint existing. First embed skips auto-bump comparison, defaults per BHV_6.
- **§3.2 EMB_PST approved.** No changes (already updated during INP review).
- **§3.2 EMB_BHV approved.** Added BHV_6 (auto-bump comparison logic). Clarified BHV_2 reads *embedded* fingerprint from requirements.md, not re-extracted.
- **§3.3 CHK_JUS approved.** Confirmed "check" is the right command name — "validate" = single-file schema conformance (STA), "check" = cross-file/cross-concern assertion (ENT, FPR). "verify" avoided because it's a plet lifecycle phase.
- **§3.3 CHK_CMD approved.** Nested `--pretty`/`--fields` under `--output json` in usage lines across all scripts (FPR, STA, ENT). Convention: `[--output json [--pretty] [--fields f1,f2]]` makes the dependency self-documenting.
- **§3.3 CHK_INP approved.** Fixed INP_1 to defer per-level file requirements to PRE. Kept `--level all`.
- **§3.3 CHK_OUT approved.** Renamed `fresh`→`consistent`/`allFresh`→`allConsistent` throughout spec. Added `artifactDir` to JSON envelope.
- **§3.3 CHK_PRE approved.** No changes.
- **§3.3 CHK_PST approved.** No changes.
- **§3.3 CHK_BHV approved.** Both levels now asymmetric: re-extract from live content, compare against stored snapshot downstream. BHV_1 re-extracts from requirements.md content vs stored in iterations.md. BHV_2 re-extracts from iterations.md content vs stored in state.json. Comprehensive — catches both "embed wasn't run" and "downstream not updated."
- **§4 EDG reviewed.** EDG_1 clarified (check re-extracts from content, doesn't need embedded block in requirements.md). EDG_2 clarified (both levels affected, with precise reasoning). EDG_13 added (first embed auto-bump behavior). EDG_5 clarified: withdrawn iterations detected by `## Withdrawn` section heading in iterations.md — same exclusion pattern as SY_8. Updated EXT_BHV_2 to match. **Cascaded:** refine.md updated — withdraw procedure now includes moving iteration to `## Withdrawn` section (new step 2). Fingerprint step updated to note automatic exclusion. PRD RF_16 updated — consistency pass now checks withdrawn iterations are in `## Withdrawn` section.
- **§5 ERR approved.** Added ERR_11 (duplicate flags), ERR_12 (not a directory), ERR_13 (malformed fingerprint). Added EMB_BHV_7 (lenient read, strict write — self-healing). Added EDG_14 (structurally wrong but valid JSON) and EDG_15 (markers with unparseable content).
- **§6 FMT approved.** Added scanning disambiguation rules (MS_ → milestones, ID_ → iterations, else → requirements). Added FMT_4 (section exclusions). **Reserved prefixes cascaded:** PRD GC_1 and plan.md Requirement ID Rules both now note MS_ and ID_ are reserved.
- **§7 AFL approved.** Added AFL_3 (prose-only spec change — primary --bump use case). Renumbered plan session to AFL_4. Fixed "orchestrator" → "plan agent" in AFL_4.
- **§8 EXM approved.** Check status: `"stale"` not `"error"` for drift detection — staleness is a successful check that found drift, not a tool failure. Updated CHK_OUT_3. Split EXM_2 into auto-bump (EXM_2) and force-bump (EXM_3). Added EXM_6 (first embed, block creation) and EXM_7 (dry-run). Now 7 examples total.
- **§9 DEP approved.** No changes.
- **§10 NFR approved.** No changes.
- **§11 DXP approved.** Added DXP_5 (enum values in help/errors), DXP_6 (PITFALLS with common agent mistakes), DXP_7 (flag dependency docs). Aligned with STA/ENT patterns.
- **§12 CRT approved.** Added CRT_10 (auto-bump), CRT_11 (lenient read/strict write), CRT_12 (reserved prefix disambiguation).
- **§13 TST approved.** Fixed CRT range → section reference. Added three-way status test note. Added conventions.md cross-reference.
- **§14 Resolved Questions approved.** Added #7–#13 from this review session. Closed Open Question #1 (resolved by reserved prefixes + scanning rules).
- **§15 FUT approved.** Withdrew FUT_1 (mtime is fragile, full scan is fast enough).
- **§16 PRD Items approved.** Updated SY_7 note to reflect ## Withdrawn section exclusion.
- **FPR spec review complete.** All 16 sections approved.
- **FPR implementation complete.** `plet_fingerprint.py` (3 commands, ~680 lines) + `test_plet_fingerprint.py` (27 tests, 90 assertions). All passing, no regressions.

#### TRC spec — scope and architecture decisions (2026-03-20)

- **plet_trace.py scope: semantic events only.** Transcript capture (raw JSONL from subprocess) is NOT in scope for plet_trace.py. That belongs in a new `plet_invoke.py` script which handles prompt assembly + subprocess launch + transcript tee.
- **Subprocess over native Agent tool:** Subprocess invocations (`claude -p --output-format stream-json`) are the only architecture that provides reliable transcript capture. Native Agent tool subagents run inside Claude Code with no portable way to capture raw I/O — log file locations are implementation details. Native subagent support is a future consideration (TRC_FUT_5).
- **Trace vs progress distinction:** Trace events are agent-readable JSON capturing significant events only. Progress is human-scannable markdown capturing both minor and significant events. Different audiences, different formats, complementary.
- **New script identified: `plet_invoke.py`** — assembles prompt (via plet_inject_prompt), launches `claude -p --output-format stream-json`, tees JSONL to transcript file, returns exit code. This replaces the transcript capture responsibility that was ambiguously assigned to the orchestrator. Needs to be added to the script inventory and build plan.

#### TRC spec §1–§3.1 review decisions (2026-03-20)

- **§1 PUR approved.** Added TRC_PUR_4 (query purpose).
- **§2 AGT approved.** AGT_2 updated (verify subagent uses query). AGT_3 generalized to "orchestrator / invoke scripts."
- **§3 universal flags approved.** No changes.
- **§3.1 APE_JUS — strengthened.** Two core justifications: (1) trace data essential for self-improvement, (2) agent-based tracing saw format drift and completely missing entries/files.
- **§3.1 APE_INP — --data-file promoted to P0.** Both --data and --data-file are P0 (exactly one required). Added "required unless" wording.
- **§3.1 APE_OUT — plet IDs in output.** Text output: `OK — {plet_id} appended ...`. JSON envelope includes `pletId` field.
- **TRC_FUT_1 promoted to requirement.** Every trace event gets a `tev_` plet ID. Reuses ENT's Crockford Base32 ID generation. Greppable and cross-referenceable from day 1. Updated BHV_1, PST_3, VAL_BHV_2, §6 schema. PRD updated: `tev` moved from reserved to active prefix.
- **Plet ID context segments for trace:** `tev_{crockford32}_{iteration}_{phase_attempt}` — matches epr/eln/eem exactly. No event_type in the ID (consistency with established scheme; event type is in the JSON).
- **NFR_1 relaxed:** 500ms (not 100ms). Trace writing is not latency-critical.
- **§3.1 APE_PST_2:** added `\n` termination assertion (NDJSON convention, prevents next-append corruption).
- **§3.1 APE_BHV approved.** atomic_append for crash-safety even with single-writer.
- **§3.2 VAL_JUS approved.** No changes.
- **§3.2 VAL_CMD in review.** Paused mid-review.
- **Review status:** §1–§3.1 complete, §3.2 VAL_CMD next.

#### Transcript capture mechanics — decided (2026-03-20)

- **plet_invoke.py captures transcripts as part of subprocess management.** No separate `plet_trace_transcript.py` needed — capture is inherently part of "launch process and record its output." You can't separate launch from capture without awkward coordination.
- **Capture mechanism:** Python reads subprocess.stdout line by line and writes each line to the transcript file. Synchronous — read a line, write a line. 100% reliable, no data loss. Whether this is literally `tee` or `line-by-line append` is an implementation detail to decide during the INV spec. Both are the same mechanically.
- **Flush behavior matters for GUI:** If plet_invoke.py flushes after each line write, filesystem watchers (fswatch, FSEvents, inotify) see changes within ~100ms. If buffered, GUI sees nothing until flush. Decision: flush after each line. This enables live-tail and real-time event display.
- **Transcript validation/querying:** Not needed now. If we later need to validate or query transcript JSONL (e.g., "find all tool_use events"), that's either new commands on `plet_trace.py` or a new script. Deferred.

#### TRC spec review decisions (2026-03-21)

**File vs directory positional arg — principled split:**
- **Writes enforce naming:** `append-event` takes `trace_dir` (directory) and constructs the filename from `--iter-id`, `--phase`, `--attempt`. Agents can't misname trace files (wrong padding, separators, extension). Format compliance is the script's job.
- **Reads accept paths:** `validate` and `query` take `events_file` (file path). The file already exists with a correct name (created by `append-event`). Forcing the caller to decompose a known path into flags adds tokens for no benefit.
- **Cross-script consistency:** STA = all file paths (per-iteration, caller manages paths). ENT/FPR = all directory (derive files from command/flags). TRC = mixed (writes derive, reads accept). The mixed model is justified — not every script needs the same pattern.

**UNV_ERR_5/6 added:** Universal convention for file-vs-directory mismatch. Commands that expect a file error on directory and vice versa. Prevents confusing errors (e.g., JSON parse error when agent passes a directory to validate).

#### util_state_global.py — shared state.json reading (2026-03-22)

- **Decision:** New `util_state_global.py` module for loading and validating common state.json fields.
- **Why:** 7+ scripts read state.json (GTI, GTO, GTC, RTR, INJ, INV, ORC). Each needs `projectId`, `loopSessionCount`, `refineSessionCount` with type validation. Without a shared function, each script duplicates the same 5-line validation or gets it wrong.
- **Key function:** `load_and_validate_global_state(path)` — loads state.json, validates projectId (string, `[A-Z][A-Z0-9]{2,5}`), session counts (non-negative integers), returns a dict or prints error + returns None. Callers check for None.
- **Scope:** Full validation of global state.json — all fields, types, and constraints. Not just the 3 common fields. plet_state.py validates per-iteration files; util_state validates the global file. Clear ownership split.
- **Location:** `util_state_global.py` (not util_io) — state.json reading is a distinct concern with its own validation rules.

#### GTI spec review decisions continued (2026-03-22)

- **BRN_INP approved.** --type promoted to P0. state_json validated via util_state_global.load_and_validate_global_state().
- **BRN_OUT approved.** Bare text output exception to UNV_CMD_15 noted in DXP_3.
- **BRN_PRE approved.** PRE_2 references util_state, PRE_3/PRE_4 kept explicit for testability.
- **BRN_PST approved.** No changes.
- **BRN_BHV approved.** Split into BHV_2–BHV_5 (one per branch type with explicit counter mapping). BHV_6 for bare output.
- **WTC_JUS approved.** No changes.
- **WTC_CMD:** "atomic" → "atomic (git-managed)".
- **WTC_INP:** Worktree path namespaced by projectId: `{worktree-dir}/{projectId}/{iter_id}/`. Prevents collisions when subplets share iteration IDs (parent LOGA/ID_001 vs subplet AUTH/ID_001).
- **§3.3 WTR approved.** All sub-sections consistent with WTC changes (util_state PRE, projectId path).
- **PUR_1 added:** "Git history is never lost" invariant — worktree ops manage on-disk dirs only, branches/commits preserved. Prominent placement.
- **§4 EDG:** Collapsed EDG_7/8/15 into EDG_7 (util_state_global.load_and_validate_global_state handles all state validation). ERR_5/6 collapsed to ERR_5.
- **specs/util_modules.md created:** Single spec for all util_* modules. One section per module with function tables and validation rules. Avoids per-file spec overhead for internal modules.
- **load_state_context → load_and_validate_global_state:** Renamed everywhere. Internal split: `load_global_state` (load JSON) + `validate_global_state` (check fields). Public function composes both.
- **WTC auto-resume on existing branch:** If the iteration branch already exists (blocked→unblocked cycle), `worktree-create` auto-resumes — creates worktree on existing branch without `-b`. No `--resume` flag needed — the branch's existence IS the signal. Preserves all commits from the blocked attempt. EDG_2 and ERR_8 updated (no longer errors). CRT_11 added.
- **UNV_NFR_9 added:** subprocess calls must use explicit args lists, never shell=True. Promoted from GTI-specific to universal convention.
- **FB_47 filed:** Formalize plan session branch and worktree behavior (open questions about whether plan actually needs branches/worktrees).
- **PRD updated:** Plan branch pattern added to branch/tag convention table.

#### GTI spec review decisions (2026-03-21)

- **create-branch dropped (YAGNI):** worktree-create subsumes it — creates branch + worktree in one `git worktree add -b` operation. If bare branches needed later, add it back. 3 commands, not 4.
- **state.json as input:** All commands take `state_json` path. Script reads projectId and session counters. Self-contained — orchestrator just passes the path.
- **Plan branch type added:** `--type plan` generates `plet/{projectId}/plan1/workstream`. Added for consistency with refine (both are interactive sessions). Plan always uses 1 — no `planSessionCount` in state.json. If plan ever repeats, add the counter then.
- **Cascading:** Plan branch pattern needs adding to `prd.md` § Branch and tag conventions (currently only loop/iteration/refine/archive defined).
- **Review status:** §1, §2, §3 Universal Flags, §3.1 BRN JUS/CMD approved. BRN INP next.

#### Terminology unification: impl → implement, EX_ → IMP_ (2026-03-21)

Script-relevant changes: `VALID_PHASES` updated in plet_entries.py, plet_trace.py. `attempts.impl` → `attempts.implement` in plet_state.py and state-schema.md. `UNV_IMP_1` → `UNV_IPR_1` in conventions.md. All specs updated (phase enums, examples, filenames, error messages). Full rationale in root `NOTES.md` § Key Design Decisions.

#### TRC spec review — complete (2026-03-21)

All 16 sections reviewed and approved. Key decisions from §3.2 onward:

- **VAL_OUT per-type counts:** Both text and JSON output include countsByType (decision, criterion_update, etc.). Gate scripts can check "were any decisions logged?" without parsing the full file.
- **VAL_BHV_8/9/10 added:** pletId prefix validation (must start with `tev_`), phase validation (`implement` or `verify` only — trace events are execution-only), countsByType as explicit testable behavior.
- **VAL_PRE expanded:** required-args, file exists and readable, file-not-directory (UNV_ERR_5).
- **Malformed tables fixed:** Unescaped pipes in CMD usage lines (implement|verify, decision|criterion_update|...). Replaced with prose enum lists. DXP_6 shell `||` replaced with behavior description.
- **--raw added to query (QRY_INP_5, P0):** Bare NDJSON output — one compact JSON per line, no envelope, no indentation. Pipe-friendly for `wc -l`, `jq`, further processing. Mutually exclusive with `--output json`. Not a FUT — useful from day 1 for scripting.
- **No --iter-id/--phase filters on query:** Confirmed unnecessary — trace files are already per-iteration per-phase. All events in one file share the same context.

- **FMT_5 added:** Enum validation on data fields — criterion_update.phase, criterion_update.status, lifecycle_change.from/to, activity_change.activity. Same enums as plet_state.py. Enforced on both append and validate.
- **AFL_3 added:** Verify subagent writes trace events (not just reads implement trace).
- **AFL_5 added:** Case study / post-run analysis flow using validate + query.
- **AGT_6 updated:** GUI may use query for filtered views and validate for integrity checks (not just direct file reads).
- **DXP_8 added:** Help documents --raw as preferred for piping/scripting.
- **DXP_9 added:** Help lists type-specific required data fields inline — agents don't need to cross-reference formats.md.
- **CRT_15 added:** Enum validation in data fields test area.
- **QRY BHV prose intro:** Added design rationale paragraph — query lenient, validate strict.
- **TRC spec complete.** Next: seq 8 (implementation).

#### util_state: unified module with global + iter functions (2026-03-22)

- **One module, 6 functions:** `util_state.py` handles both global and per-iteration state. Initially split into `util_state_global.py` + `util_state_iter.py`, then re-unified — 6 functions isn't enough to justify two files.
  - `load_and_validate_global_state(path)` / `load_global_state` / `validate_global_state`
  - `load_and_validate_iter_state(path)` / `load_iter_state` / `validate_iter_state`
- **Convention established:** Scripts that need per-iteration context (GTO, GTC, GIM, GVR) take `<state_json> <iter_state>` as two positional args + `--phase` as the only flag for context. iter-id, attempt, title, cleanupTagsAutomatically all derived from files. Single source of truth — the state files decide, not the caller's memory.
- **Why two positional args + --phase:** iter-id and attempt come from the file (can't pass wrong values). Phase must be explicit because lifecycle may be mid-transition when the script is called. Title comes from iter_state.title. This eliminates 3 flags (--iter-id, --attempt, --title) and prevents orchestrator bugs from silently producing wrong tag names or commit messages.
- **Retrofit ENT/TRC deferred:** plet_entries.py and plet_trace.py use --iter-id, --phase, --attempt flags (called by subagents, not orchestrator). Retrofitting is expensive and the flag pattern works for agents. The two-state-file pattern applies to new orchestrator-called scripts (GTO, GTC, GIM, GVR). Evaluate retrofit after PLAN_9 — if case studies show agents passing wrong values, retrofit then.

#### Squash architecture redesign (2026-03-22)

- **No per-phase squashing on iteration branch.** Incremental commits stay. Tags mark phase boundaries (phase END). The iteration branch IS the full history — no audit tags needed as safety nets for destructive squash.
- **One squash at merge-to-workstream time.** `git merge --squash` from workstream creates one commit per iteration. Linear history, no merge commits. Iteration branch untouched.
- **Commit message changes:** `plet: [ID_001] - {title}` (no phase in message). Phase details in audit tags and progress.md.
- **AFL_4 (post-rebase re-squash) eliminated.** No rebase needed — merge --squash stages the diff directly.
- **GTO squash command → merge-squash.** Fundamentally different operation: runs from workstream, not iteration branch. Takes global + iter state, derives iteration branch name, runs merge --squash.
- **audit-tag simplified.** Still marks phase END, but no longer a safety net for destructive squash. Lightweight boundary markers.
- **cleanupBranchesAutomatically added.** New per-iteration state field, default false. Independent of cleanupTagsAutomatically. Controls whether the iteration branch is deleted after merge-squash. If branches deleted, tags still keep commits reachable. Both booleans default false (conservative).
**Commit flow diagram:**

```
ITERATION BRANCH (no squashing, incremental commits preserved):

  c1 ── c2 ── c3 ── v1 ── v2
               │            │
          tag:impl-1   tag:verify-1
          (phase END)  (phase END)

  Cycle-back adds more: c4 ── c5 ── v3
                               │      │
                          tag:impl-2  tag:verify-2

WORKSTREAM (one commit per iteration via git merge --squash):

  git checkout workstream
  git merge --squash plet/LOGA/loop1/ID_001
  git commit -m "plet: [ID_001] - Project scaffolding"

  B ── [ID_001] ── [ID_002] ── [ID_003] ── ...
       (all changes   (all changes   (all changes
        from iter)      from iter)     from iter)

MAIN (receives workstream, one commit per iteration):

  A ── B ── [ID_001] ── [ID_002] ── [ID_003] ── ...

CLEANUP (per-iteration state controls):
  cleanupTagsAutomatically: false (default) → audit tags preserved
  cleanupBranchesAutomatically: false (default) → iteration branches preserved
  Both independent. Tags keep commits reachable even if branch deleted.
```

- **Cascade needed:** state-schema.md (new field), prd.md (IMP_17 squash convention), execute.md/verify.md (tag and squash sections), util_modules.md (iter validation rules), GTO spec rewrite of squash sections.

#### GTC spec review (2026-03-23)

- §1 PUR approved as-is.
- §2 AGT: added GTC_AGT_7 — GUI tool persona for dashboard health display / status polling. Continues pattern from STA_AGT_8, ENT_AGT_7, FPR_AGT_6.
- §3.1 CKI_JUS_1: broadened "shared by both gate scripts" → "shared by gate scripts, orchestrator, and external tools."
- §3.1 CKI_OUT: three-tier exit codes (0=pass, 1=fail, 2=warn-only). Title line shows worst severity (PASS/WARN/FAIL). JSON status adds `"warn"` state. Rationale: exit 2 gives callers a distinct signal for warnings without forcing binary pass/fail. Gate scripts and orchestrator decide how to handle exit 2.
- §3.1 CKI_BHV: confirmed merge-commits-only for linear-history (fast-forwards are fine, duplicate commits from bad rebases are a different problem). No SKIP status — dependent checks fail naturally, check order (BHV_6) tells the story top-to-bottom. Simplest approach, no dependency-linking metadata needed.
- §3.1 CKI_BHV_8 added: in-progress-operation check — detects interrupted rebase/merge/cherry-pick/bisect. FAIL. Runs first in check order. More actionable than clean-worktree alone (explains *why* the tree is dirty).
- Clarification: plet runtime artifacts (progress.md, learnings.md, state files, traces) ARE committed on iteration branches alongside code. The branch is a complete record of the iteration's work. Added UNV_NFR_10 to conventions.md. FB_48 filed to make this explicit in PRD and reference files.
- §3.2 CKS_CMD: `--state-dir` changed to positional `state_dir`. Consistency with check-iteration's two-positional-args pattern. Script validates directory type via ERR_6/ERR_7.
- §3.2 CKS_BHV_8 added: in-progress-operation check (same as CKI_BHV_8). Session preflight is the only checkpoint before work begins — if repo has an interrupted operation, nothing else matters. Shared check name across both commands.
- §3.2 CKS_BHV_9 added: orphaned-branches — plet-namespaced branches without corresponding state files. WARN. Reverse of unmerged-complete (branch without state vs state without merge). Rejected: workstream-ahead-of-main (judgment call, not compliance) and active-iteration-branches-exist (state-level, not git-level).
- util_subprocess.py implemented: shared subprocess wrapper (run, run_git). 26 tests. No `_check` variants — callers always need custom error context, add them later if 3+ scripts duplicate the check-and-exit pattern. GTI retrofitted (removed local git_run, 54 tests pass). GTO retrofitted (removed local git_run + helpers, 48 tests pass). No regressions across all test suites.
- Naming fix: `load_and_validate_iter_state_json` → `load_and_validate_iter_state` across GTC and GTO specs (matching actual code).
- §3.2 CKS_JUS_2: GUI tools added (same as CKI_JUS_2).
- §4 EDG_14 added: multiple interrupted git operations — report all. EDG_15 added: workstream branch excluded from orphaned-branches scan.
- §7 AFL: all four flows updated — exit code 2 handling (warn → log, don't block), in-progress-operation at session preflight (FAIL → abort), orphaned-branches at session end.
- §9 DEP_6 added: util_subprocess (run_git).
- §12 CRT_14 added: orphaned-branches detection + workstream exclusion. CRT_15 added: exit code 2 (warn-only) distinct from 0 and 1.
- §3 Universal Flags, §5 ERR, §6 FMT, §10 NFR, §11 DXP, §13 TST: approved as-is.

#### SES spec review decisions (2026-03-25)

- **§1 PUR approved.** Added audience framing table: detect (machines, fast), status (humans+dashboards, moderate), preflight (gate logic, moderate).
- **Unified input pattern:** All 3 commands take optional `plet_dir` (default `plet/`), derive paths internally. No more mixed `global_state_json + state_dir` vs `plet_dir`. Simpler for callers.
- **detect stays separate from status:** Different audiences, different perf profiles. detect is a routing primitive (<500ms, bare output). status is a dashboard (<2s, rich formatted output).
- **Fingerprint check via subprocess:** status calls `plet_fingerprint.py check` via subprocess (P1). Complex logic, already implemented — reuse, don't reimplement.
- **JSON schemas:** All OUT sections use pulled-out fenced blocks with full stable labels (GSS_DET_OUT_2, not OUT_2). Convention applied across all 9 specs.
- **Postflight open question:** Added OQ_1 — should GSS have a postflight command that calls GTC + ENT check + FPR check + state validation as a session-end gate? Evaluate during orchestrator spec.
- **DXP_3:** detect bare output exception references GTI_DXP_3 precedent.
- **Router → session rename:** RTR → SES. All active references updated. FB_22/23 updated.
- **§3.2 STS approved.** Unified plet_dir input (same as detect/preflight). Added BHV_8 (progress percentage), BHV_9 (milestone breakdown — bottom of text, full in JSON). Fingerprint check graceful degradation (null if unavailable).
- **§3.3 PRF approved.** Major design decisions:
  - **bypass-permissions dropped** — plet_invoke.py uses `claude --enable-auto-mode`. FB_22 resolved by architecture.
  - **--session-type required** — `detect|plan|loop|refine`. Controls fingerprint severity. Users can force session type.
  - **Fingerprint severity by session:** loop→FAIL, refine→WARN, plan→SKIPPED. Stale specs in loop = wasted work.
  - **SKIPPED status added** — fourth check status (pass/fail/warn/skipped). Doesn't affect exit code.
  - **Full GTC check-session integrated** — preflight IS a session boundary. CKS checks included with `git:` prefix.
  - **scripts-installed check** — missing plet scripts = FAIL (corrupted installation).
  - Check order: scripts-installed → git-check (CKS) → claude-md-exists → gitignore-plet → spec-artifacts → state-valid → fingerprints-consistent.
- **§4–§16 approved.** Added ERR_9 (invalid --session-type), CRT_11 (GTC integration), CRT_12 (fingerprint SKIPPED on plan). FB_22 updated (resolved by invoke architecture).
- **SES spec review complete.**

#### Worktree + shared artifacts merge strategy (2026-03-26)

- **Problem:** Parallel iterations in separate worktrees all append to shared runtime artifacts (progress.md, learnings.md, emergent.md). When merge-squashing to workstream, the second merge sees a conflict — both branches appended to the end of the file.
- **Solution:** Sequential merge-squash. Iterations execute in parallel (the expensive part). Merge-squash is serial (fast — < 2s per iteration). This is already the natural behavior: GTO merge-squash checks out the workstream branch first (single writer constraint).
- **Why not other approaches:** Per-iteration files lose the unified narrative. Auto-resolution is fragile. Separate artifact merging adds complexity. Sequential merge is the simplest fix — 13 iterations × 2s = 26s total merge time vs hours saved by parallel execution.
- **Per-iteration files (state/{id}.json, trace/{id}-*) never conflict** — different file paths, no shared state.
- **GUI multi-directory model confirmed:** Main plet/ = session dashboard. Worktree plet/ = iteration dashboard. GUI discovers worktrees via `git worktree list --porcelain`. Both views are valid, different scopes.

#### Invocation logging + --allow-fences + invocation event type (2026-03-28)

- **INV logs to both trace AND progress.** Every subprocess launch writes: (1) invocation trace event with full prompt + invocation details in structured JSON, (2) progress entry with full prompt + invocation details in human-readable markdown. No separate prompt.md file — prompt lives in two places with different audiences.
- **Why both:** Trace is for machines (eval, comparison, replay). Progress is for humans (narrative log, case study analysis). Same data, different formats.
- **--allow-fences added to plet_entries.py.** Prompt text legitimately contains fence pattern examples (from formats.md reference file). ENT's fence rejection was too aggressive — blocked logging the exact prompt. New `--allow-fences` flag bypasses the check. Added to all three add-* commands.
- **"invocation" event type added to plet_trace.py (6th type).** Required fields: cwd, permissionMode, promptLength. Optional: prompt (full text), model, maxBudget. First event in every trace file — makes the trace self-describing.
- **Fence safety preserved by default.** --allow-fences is opt-in. Normal agent usage still gets fence rejection. Only INV (which knows it's logging a prompt) passes the flag.
- **Content-file for large prompts.** INV uses `--content-file` (not `--content`) because prompts can be 40KB+. Temp file written to trace dir, cleaned up after.

#### Eval system design direction (2026-03-28)

- **PLAN_9 redefined:** Was "comparison runs" (vague). Now "eval system + comparison runs" with per-role eval strategy (planner, implementer, verifier).
- **Key insight from prompt work:** Building plet_prompt.py surfaced that we have no way to measure whether prompt changes improve outcomes. Ad-hoc case studies (LOGA, LIBT) extracted feedback but didn't systematically compare before/after.
- **Three failure modes by role:** Planner failures = implementer/verifier blocked by vague specs. Implementer failures = rubber-stamped tests, poor coverage. Verifier failures = false negatives (things that slipped through).
- **Long-term goal:** Eval as a first-class plet feature, like skill-creator's eval framework. Metrics collection, comparison reports, trend tracking.
- **Phased approach:** Formalize case study template first (cheap), then comparison runs (PLAN_9b), then broader testing (PLAN_9c), then eval tooling (PLAN_9d).
- **Both synthetic and emergent test cases needed.** Synthetic = deliberately vague criteria, injected bugs. Emergent = real failures from case study runs.

#### INV spec + implementation (2026-03-28)

- **Single command:** `run` with `--phase implement|verify`, `--cwd <worktree>`, `--iter-id`.
- **Prompt delivery:** Full prompt string passed as direct positional arg to `claude -p`. Not stdin, not file.
- **Claude flags:** `--output-format stream-json`, `--permission-mode auto` (default) or `bypassPermissions` (fallback), `--no-session-persistence`, `--bare` (skip hooks/LSP/plugins for fast startup), `--name "plet/{iter_id}/{phase}-{attempt}"`.
- **`--bare` monitor:** May need to be optional if subagents need user skills/plugins. Fine for now since subagents are batch workers.
- **Transcript capture:** Line-by-line with flush after each write (~100ms GUI live-tail). Append-never-overwrite — retries add separator + append. No data loss.
- **Exit code pass-through:** Subprocess exit code = INV exit code. Orchestrator interprets.
- **Stderr:** Goes to INV's own stderr (visible to orchestrator), not to transcript. Only stdout (stream-json) goes to transcript.
- **State reads, doesn't write:** Reads attempt number from iter state for filename. Doesn't increment — orchestrator's job.
- **`--permission-mode auto`** requires one-time `claude --enable-auto-mode` setup (https://claude.com/blog/auto-mode). `bypassPermissions` as fallback for older models.
- **No `--dangerously-skip-permissions`:** Use `--permission-mode bypassPermissions` instead.
- **Sandboxing:** Environment-level config, not per-invocation. See FB_50.
- **`--dry-run`** supported — previews full claude command without launching.
- **Mock testing strategy:** Mock `claude` script on PATH outputs JSONL and exits with controlled code.
- **37 tests, all passing.**

#### PRM spec + implementation (2026-03-27)

- **Renamed:** `plet_inject_prompt.py` (INJ) → `plet_prompt.py` (PRM). Simpler name — "it builds the prompt."
- **Single command:** `assemble` with `--phase implement|verify`. Reads files on disk, outputs complete prompt.
- **7 sections in order:** reference-file (implement.md or verify.md), iteration-definition (extracted from iterations.md), formats, state-schema, requirements, learnings (always present — FB_38), iteration-state (formatted readably).
- **Learnings always injected (FB_38):** Even when learnings.md is empty or missing, the section appears with a "no learnings" note. Guarantees cross-iteration knowledge transfer is deterministic.
- **Iteration definition extraction:** Regex-based heading match in iterations.md. Extracts from matching heading to next same-level heading.
- **State formatted as text:** Not raw JSON — human-readable summary of lifecycle, attempts, criteria with statuses.
- **Matches current SKILL.md injection list.** Will evolve when skills are rewritten to use enforcement scripts. This version is a historical baseline — formats.md and state-schema.md may become unnecessary when agents call scripts instead of writing freehand.
- **Resolved questions:** No relevance filtering in v1 (full learnings included). No emergent.md injection (not in current SKILL.md list). No target CLAUDE.md injection (agent reads it naturally). No progress.md injection (learnings captures transferable knowledge).
- **49 tests, all passing.**

#### GVR spec review (2026-03-27)

- **Simpler pre-gate than GIM:** git-check + state-valid + lifecycle-check only. No fingerprints (can't change during verify), no spec-artifacts (can't disappear mid-session).
- **Lifecycle valid states:** GVR pre accepts only `verifying`. GIM pre accepts `queued`/`implementing`. Clean separation — each gate accepts only its phase's states.
- **last-verdict check (GVR_PST_BHV_9):** FAIL if `lastVerdict` is null after verify. The orchestrator needs the verdict to decide next steps. Full verificationReports check deferred to GVR_FUT_2.
- **Shared gate module:** Extract to `util_gate_phase.py` during implementation. 6 shared functions between GIM and GVR. GIM retrofitted to import from shared module.
- **verification-report check promoted (GVR_FUT_2 → GVR_PST_BHV_10):** FAIL if verificationReports empty or last entry missing required fields (verdict, criteriaResults). The report is the structured output of verify — subagent must self-correct.
- **Shared gate library promoted (GVR_FUT_3 → RQ_4):** Extract to `util_gate_phase.py` during implementation. GIM retrofitted.
- **Full trace validation promoted (GVR_FUT_1 → BHV_6, GIM_FUT_1 → BHV_8):** Both gate scripts now call TRC validate (not just existence check). WARN if invalid. Corrupt traces are worse than missing — silent data loss.
- **GVR spec review complete.**

#### GIM + GVR merged into plet_gate_phase.py (GPH) (2026-03-27)

- **Decision:** Merge `plet_gate_impl.py` (GIM) and `plet_gate_verify.py` (GVR) into single `plet_gate_phase.py` (GPH). The two scripts were 80% identical — `--phase implement|verify` controls the differences.
- **Why:** GIM (305 lines) and GVR (286 lines) plus util_gate_phase.py (200 lines) = 791 lines across 3 files. Merged: ~400 lines in 1 file. Eliminates util_gate_phase.py entirely. Follows GTC pattern (check-iteration already takes `--phase`).
- **Prefix change:** GIM + GVR → GPH (Gate PHase). Both old prefixes become historical.
- **Phase difference table in §1 PUR:** Shows which checks run for each phase/gate combination at a glance.
- **Key differences by phase:**
  - implement pre: git + state + lifecycle(queued/implementing) + spec-artifacts + fingerprints (5 extra)
  - verify pre: git + state + lifecycle(verifying) only (3 checks)
  - implement post: git + state + entries + trace (shared)
  - verify post: git + state + entries + trace + last-verdict(FAIL) + verification-report(FAIL) (2 extra)
- **Stable label prefix table:** GPH replaces GIM + GVR entries. Command abbreviations: PRE, PST (same as before).
- **PLAN.md:** Seq 18-21 still show GIM/GVR complete. Merged spec replaces both spec files. Implementation will replace both scripts + util_gate_phase.py.

#### GIM spec review continued (2026-03-26)

- **§1 PUR approved.** Preamble updated: primary purpose is "you're not done yet — clean up or block."
- **§2 AGT approved.** Added AGT_6 (case study / audit agent).
- **§3.1 PRE approved.** Added BHV_5 (lifecycle-check, WARN), BHV_6 (fingerprints-consistent, WARN). FUT_3 promoted. Open question resolved.
- **§3.2 PST — post does NOT repeat lifecycle/spec-artifacts/fingerprints.** Rationale: lifecycle mid-transition, spec artifacts can't disappear, fingerprints can't change during impl. Post = git + state re-verify + entry checks only.
- **Worktree merge strategy decided.** Sequential merge-squash for shared runtime artifacts. Parallel execution, serial merge (< 2s each). Already natural behavior. Cascaded to GTO RQ_7, orchestrator placeholder.
- **§3.2 PST approved.** JUS_2 fixed (subagent calls post). BHV_8 added (trace-events WARN if missing/empty, FB_11). emergent-entry WARN includes actionable guidance ("verify no decisions were made"). RQ_3 updated.
- **§4–§16 approved.** CRT_11 added (trace events). FB_11 added to §16.
- **GIM spec review complete.**

#### GIM spec review (2026-03-25)

- **Post-gate caller is the subagent, not the orchestrator.** The implement subagent runs `post` itself before exiting and self-corrects until it passes. This eliminates orchestrator retry logic for missing artifacts — the subagent's exit signal means "I passed my own gate." Orchestrator can optionally re-verify (trust but verify). AGT_2 updated, AFL_1/AFL_2 rewritten.
- **Unified input convention: `<plet_dir>` + `--iter-id` for all scripts.** All scripts take the plet directory and derive paths internally. No more explicit file paths (`<global_state_json> <iter_state_json>`). Rationale: plet_dir is the root, everything is derivable (`state.json`, `state/{iter_id}.json`, `requirements.md`, etc.). Fewer args, no mismatched files, single source of truth.

**Before (mixed conventions):**

| Script | Command | Input pattern |
|--------|---------|---------------|
| plet_state.py | validate, update-*, init | `<state_file>` (single file) |
| plet_entries.py | add-*, check | `<artifact_dir>` (plet dir) |
| plet_fingerprint.py | extract, embed, check | `<plet_dir>` |
| plet_trace.py | append-event, validate, query | `<trace_file>` (single file) |
| plet_git_iteration.py | branch-name, worktree-* | `<global_state_json>` (single file) |
| plet_git_ops.py | audit-tag, merge-squash | `<global_state_json> <iter_state_json>` (two files) |
| plet_git_check.py | check-iteration | `<global_state_json> <iter_state_json>` (two files) |
| plet_git_check.py | check-session | `<global_state_json> <state_dir>` (file + dir) |
| plet_gate_session.py | detect, status, preflight | `[<plet_dir>]` (optional dir) |

**After (unified):**

All scripts take `[<plet_dir>]` (optional, default `plet/`) as first positional arg. Commands that need per-iteration context add `--iter-id ID_xxx`. Scripts derive all paths internally via `util_io` path functions. No exceptions — every script uses the same pattern.

Retrofitting all specs first, then implementations.

**Path derivation in util_io.py:** Added 10 path functions (`state_json_path`, `iter_state_path`, `requirements_path`, etc.) + `DEFAULT_PLET_DIR` constant. Single source of truth for plet directory layout — scripts must use these functions, never construct paths manually. UNV_CMD_16 updated to reference util_io. Template and util_modules.md updated.

**Layering cleanup:** Raw JSON loading (`load_global_state_json`, `load_iter_state_json`) moves to util_io (path derivation + load_json). Validation stays in util_state. `load_and_validate_*` in util_state now takes `(plet_dir)` / `(plet_dir, iter_id)` and calls util_io internally. `validate_plet_dir()` added to util_io for directory validation.

**Shared CLI helpers (UNV_CMD_26):** `get_plet_dir`, `extract_output_flags`, `emit_json`, `emit_json_error` move to util_cli. Currently duplicated across 6-7 scripts. Single implementation, scripts import from util_cli.

**Exit code convention updated (UNV_CMD_14):** Was "0 = success, 1 = error. No other exit codes." Now allows exit 2 for check/gate commands (warnings only, no failures). GTC, SES preflight, GIM all use this. Duplicate UNV_CMD_17 ID fixed → shared helpers renumbered to UNV_CMD_26.

#### GTO spec review + implementation complete (2026-03-22)

**Spec review decisions:**
- §3.2 squash → merge-squash (MSQ): full rewrite for new architecture. `git merge --squash` from workstream, one commit per iteration.
- Commit body auto-generated from iter_state: `Phases: implement×N, verify×N` + `Criteria: N/N passed`. FUT_3 promoted.
- `--cleanup-tag` flag dropped (YAGNI). Tag/branch cleanup controlled by iter_state fields only.
- EDG_12: detached HEAD detection. EDG_14: merge conflict → error + abort (promoted from FUT_4).
- ERR updated: removed stale --iter-id/--attempt errors, added iter_state_json directory check, detached HEAD, branch not found, duplicate merge, conflict.
- Responsibility boundary documented: GTO = pure git tool (returns data), orchestrator = logging (progress + trace).
- `global_state_json` / `iter_state_json` naming unified across GTI, GTO, STA specs + implementations.

**Implementation (red/green):**
- audit-tag: 26 tests (red first, then green)
- merge-squash: 22 tests (red first, then green) — 48 total
- util_state iter functions: 59 tests (red first, then green) — 117 total for util_state
- All existing tests passing (no regressions)

#### cleanup-stashes dropped from GTO (2026-03-22)

- **Decision:** Drop `cleanup-stashes` from `plet_git_ops.py`. GTO is now 2 commands: `squash`, `audit-tag`.
- **Why:** Worktrees (GTI) eliminate the need to stash. The stash ban is in execute.md and verify.md. A cleanup command for a problem that shouldn't exist is backwards — the fix is enforcing the ban (worktrees), not cleaning up after violations.
- **Monitor:** If PLAN_9 comparison runs or future case studies show stashes appearing despite worktrees, revisit. Until then, YAGNI.

#### plet_git.py split into three scripts (2026-03-21)

**Decision:** Split `plet_git.py` (8 commands, 4 concerns) into three focused scripts by audience:

| Script | Prefix | Purpose | Commands | Caller |
|--------|--------|---------|----------|--------|
| `plet_git_iteration.py` | GIT | Iteration git lifecycle | `branch-name`, `create-branch`, `worktree-create`, `worktree-remove` | Orchestrator + agents |
| `plet_git_ops.py` | GTO | Git workflow operations | `squash`, `audit-tag` | Orchestrator only |
| `plet_git_check.py` | GTC | Git compliance checks | `check-iteration`, `check-session` | Gate scripts + orchestrator |

**Rationale:** The original 8-command script mixed three audiences (agents, orchestrator, gate scripts) and four concerns (naming, worktrees, workflow ops, compliance). The split follows the existing pattern: compliance tools agents call (like plet_state, plet_entries) vs workflow steps the orchestrator sequences vs checks gate scripts run.

**Key insight:** Squash, audit-tag, and stash cleanup are workflow steps that need orchestrator context (branch points, tag naming, session state). They don't belong in a compliance tool. Gate scripts need `check-iteration` (per-phase boundaries) and `check-session` (session boundaries) — two different scopes with different inputs.

**Retired:** `GCL` prefix (Git CompLiance) — replaced by GTI, GTO, GTC.

#### Red/green development discipline — MANDATORY (2026-03-19)

- **Command-by-command red/green is non-negotiable** for all script implementations going forward. Write tests for one command first → run and confirm they fail (red) → implement the command → run and confirm they pass (green) → move to next command. No writing the script and tests together. No writing the script first.
- **Why:** FPR was implemented script-and-tests-together, which worked but skipped the verification that tests actually catch failures. Red/green proves the tests are load-bearing — a test that was never red might always pass regardless of implementation.
- **Granularity:** command-by-command, not all-at-once. Later commands often depend on earlier ones (embed depends on extract working). Writing all tests before any implementation would require mocking or placeholder behavior that adds complexity for no benefit.

#### Structural consistency pass — --no-log convention + stale refs (2026-03-29)

- **UNV_CMD_28 added** to `specs/conventions.md`: `--no-log` flag convention. Intentionally excluded from `--help` output — this flag is for tests and GUIs only, not agent use. Cascades via `PLET_NO_LOG=1` env var.
- **`dispatch()` signature fixed** in `specs/util_modules.md`: was missing `argv` and `no_log_commands` parameters, now complete with logging behavior description.
- **PLAN.md FB_29/FB_33 updated**: stale references to `plet_gate_impl.py`/`plet_gate_verify.py` corrected to `plet_gate_phase.py` (scripts were merged).
- **11 spec files fixed** (earlier in session): `python3 skills/plet/tests/test_...` → `./skills/plet/tests/test_...` to match shebang-style convention from commit 7b8c0cc.

#### Orchestrator execution model — toolkit + run (2026-03-29)

- **Decision:** plet_orchestrator.py uses the **toolkit + run** model. Individual commands (`eligible`, `check-retry`, `start-session`, `end-session`, `check-breakpoints`) are available standalone for testing, debugging, and manual use. A `run` command implements the main loop as deterministic code, calling the individual commands internally and delegating subagent spawning to `plet_invoke.py`.
- **Why:** The main loop is the most compaction-vulnerable and drift-prone part of the system. Case studies showed orchestrator prose drifting across iterations. Making the loop deterministic code eliminates this. Individual commands stay available for SKILL.md edge cases (breakpoint responses, merge conflicts, user intervention).
- **Rejected alternatives:**
  - **(A) Toolkit only** — loop logic stays in SKILL.md prose. Rejected because this is the exact failure mode from case studies (orchestrator drift under compaction).
  - **(C) Full script-as-orchestrator** — Python script is the entry point, no SKILL.md loop. Deferred to v2 — open questions about `claude -p` capabilities need resolution first. Comparison runs should validate current architecture before committing.
- **Interaction model:** `run` returns structured JSON indicating why it paused (breakpoint hit, iteration blocked, all complete). SKILL.md decides what to do next.

#### Command distribution — 3 new scripts, 1 rename (2026-03-29)

- **Decision:** Distribute orchestrator helper commands across focused scripts rather than packing them into existing scripts.
- **Rename:** `plet_session.py` → `plet_gate_session.py`. The existing script (detect, status, preflight) is read-only session-level gate checks — parallel to `plet_gate_phase.py` for phase-level gates. Renaming makes this relationship explicit.
- **New `plet_session.py`** — mutating session lifecycle: `start-session`, `end-session`. Manages loopSessionCount, sessionHistory, workstream branches.
- **New `plet_schedule.py`** — loop scheduling decisions: `eligible` (dependency graph traversal), `check-breakpoints` (breakpoint lookup), `check-retry` (retry trend analysis). All read-only. These read state but their logic is orchestration decisions, not state CRUD.
- **New `plet_orchestrator.py`** — the main loop: `run`. Calls plet_schedule, plet_session, plet_invoke, and all existing scripts.
- **Why not add to existing scripts:** plet_state.py already 1032 lines / 4 commands — adding 3 more would push to ~1400+ / 7 commands. plet_session.py (now plet_gate_session.py) is read-only; mixing in mutating commands changes its character. Separate scripts keep each focused.
- **Rejected:** (A) all helpers in plet_state.py (too large, wrong domain — scheduling ≠ CRUD); (B) split 2+1 across plet_state and new script (inconsistent — all 3 are scheduling concerns).

**Updated script inventory (4 new scripts, 1 rename):**

| Script | Commands | Domain |
|--------|----------|--------|
| `plet_gate_session.py` (renamed) | detect, status, preflight | Session-level gate checks (read-only) |
| `plet_session.py` (new) | start-session, end-session | Session lifecycle (mutating) |
| `plet_schedule.py` (new) | eligible, check-breakpoints, check-retry | Loop scheduling decisions (read-only) |
| `plet_orchestrator.py` (new) | run | Main loop |

#### Rename plet_session.py → plet_gate_session.py complete (2026-03-29)

- Renamed 3 files: script, test, spec. Prefix SES_ → GSS_ globally (169 in spec, 2 elsewhere). All `plet_session` references updated to `plet_gate_session` across 12 files. 1247 tests pass. Parallel spawning model: eligible iterations launch concurrently, merge-squash stays serial.

#### plet_schedule.py spec (SCH) — complete (2026-03-29)

- 3 read-only commands: `eligible` (dependency graph), `check-breakpoints` (breakpoint lookup), `check-retry` (retry trend analysis per IMP_14).
- `eligible` does NOT detect stuck agents, does NOT validate graph, does NOT include `parallelGroups` — single responsibility (what's ready, not how to schedule).
- `check-retry` failure count = criteria with `status == "fail"` only. `error`/`skipped` excluded.
- `parallelGroups` excluded from eligible output — orchestrator already has state.json in hand, avoids coupling eligible to scheduling strategy.
- **Review decisions:**
  - Missing state file in dependency map → hard error (exit 1), not warning. Corruption needs manual fix.
  - Retry limit applies to verify attempts only, not total (implement + verify).
  - SCH_RTY_BHV_6: `blocked` verdict → orchestrator must NOT call check-retry. Retry only evaluates `rejected`.
  - SCH_NFR_2: uses `util_state.load_and_validate_iter_state` + explicit lifecycle enum check. Catches both structural corruption and lifecycle typos.
- **UNV_CMD_29 added:** unknown flags error. New scripts implement from the start; retrofit existing scripts in seq 33.
- **FB_52 filed:** plan/refine sessions need explicit ambiguity/gap detection steps.
- **FB_53 filed:** different software types need different planning templates.
