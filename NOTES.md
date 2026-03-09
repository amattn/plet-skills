# plet-skills Development Notes

- What is plet?
- Core Workflow
- Platform & Distribution
- Invariants & Critical Requirements
- Key Design Decisions
- Global Conventions
- Lineage
- Important Concepts & Insights
- PRD Status
- Things to Monitor
- Open Questions
- Multi-Developer Analysis
- Self-Improvement Analysis

## What is plet?

**PLET = Progress, Learnings, Emergent, Trace** — the four runtime artifacts the system produces. Also works phonetically as Plan + Execute.

plet is a Claude Code skill that provides a spec-driven autonomous development loop. It combines interactive planning with autonomous execution, verification, and iterative refinement — all running natively inside Claude Code without requiring an external harness. Inspired by and builds on Ralph loops — a spec-driven autonomous coding pattern — via RIDL (Ralph Iteration Definition List), the author's implementation of that pattern. plet is a merger between Claude Code's plan mode (interactive, iterative planning) and the RIDL PRD-driven autonomous loop (structured execution with runtime artifacts).

---

## Core Workflow

**Plan -> Loop (Execute → Verify) -> Refine**

- **Plan** = spec (interactive requirements creation, iteration decomposition)
- **Loop** = autonomous impl→verify cycle:
  - **Execute** = implement then test (red/green discipline, subagents)
  - **Verify** = independent verification in a fresh context window
- **Refine** = uses Progress, Learnings, Emergent items, and Trace logs to improve the spec and re-plan

---

## Platform & Distribution

- Claude Code skill (SKILL.md + bundled reference files)
- No scripts, no external dependencies for v1.0
- Published to github and distributed via Claude Code plugin marketplace
- Primary users: developers using Claude Code
- GUI/monitoring repos planned as separate future projects that read the state file

---

## Invariants & Critical Requirements

Rules that must not be violated. An agent breaking these breaks the system.

**Design constraints:**
- **Each iteration must fit in a single context window without compaction** — this is the single most important decomposition constraint. Context compaction mid-iteration causes the agent to lose implementation state. Err aggressively on smaller iterations; two small iterations are always safer than one large one.
- **Verification agent does NOT initially read implementation diffs** — prevents rubber-stamping; verifies the result, not the process. May dig deeper later, but never as a starting point.

**Data integrity:**
- **Frozen iterations are never modified** — new work is appended as new iterations. Guarantees completed work is stable; external tools can trust `complete` status.
- **Runtime artifact format changes are additive only** — never remove or rename fields. Breaking changes require major version bump. External consumers depend on schema stability.
- **IDs are stable once assigned** — never renumber, never reuse. Gaps are expected and acceptable.

**Agent discipline:**
- **Blockers must be documented across ALL four artifact types before the agent returns** — trace, progress, emergent, learnings. The quality of blocker documentation determines whether the human can help.
- **Each approved section is written to disk immediately** — the file on disk is the source of truth. Never defer writing approved content to the end of a session.

**Self-improvement:**
- **Agents must surface improvements to their own instructions** — when an agent notices a pattern, convention, or recurring issue not yet captured in CLAUDE.md or project instructions, it offers to write it down. Human approves, instructions improve, next session is better. This is the micro self-improvement loop (session-to-session via CLAUDE.md). Both are human-gated. Both are load-bearing — without them, instructions calcify as the project evolves.
- **A future version of plet should be able to improve itself given enough generated artifacts** — the macro self-improvement loop (Future Consideration #11). plet's generated artifacts — runtime (progress, learnings, emergent, trace), planning (requirements.md, iterations.md), and execution logs — are exactly the telemetry needed to analyze its own performance and inform PRD improvements.

---

## Key Design Decisions

### Architecture & Routing

#### Single skill with reference files
- One entry point (`/plet`) with state-driven routing
- Phase-specific instructions in `references/` (plan.md, execute.md, verify.md, refine.md)
- User never has to remember which step they're on — `/plet` reads state and figures it out
- Can force a phase with `/plet plan`, `/plet loop`, `/plet refine`, `/plet status`

#### Relationship to RIDL and external harness
- plet replaces the external RIDL harness as the primary engine
- The harness (e.g., Ridler.app) becomes an **optional GUI** that reads the state file for visualization/monitoring
- plet is self-sufficient — the state file is the shared contract
- plet coexists with ridl-skills — no command conflicts (`/plet` vs `/ridl-skills:*`)

#### Three plan artifacts (not two)
- **`plet/requirements.md`** — comprehensive PRD (human-readable spec with requirement tables, architecture, milestones). Equivalent to ridl-skills:prd output.
- **`plet/iterations.md`** — human-readable iteration definitions with user stories, acceptance criteria, dependencies. Equivalent to ridl.md.
- **`plet/state.json`** — machine-readable runtime state (lifecycle phases, agent activity, criterion statuses, timestamps). Replaces ridl.json with much richer tracking.

#### Loop routing: `/plet execute` + `/plet verify` merged into `/plet loop`

Execute and verify are internal phases of one autonomous loop — the user shouldn't need to invoke them separately. `/plet loop` forces entry into the impl→verify loop. The internal phases still exist as concepts in reference files, but are not user-facing subcommands.

#### Routing: `ineligible` excluded from LOOP check

`ineligible` iterations are waiting on dependencies and aren't actionable work. Including them caused a dead-end when all remaining iterations were `blocked` + `ineligible` — routed to LOOP instead of REFINE where the human could resolve the blocker. OR_4 now only checks for `queued`, `implementing`, or `verifying`.

#### PT_ → PL_ rename

All "plan-template" sections (PT_DX, PT_CT, PT_TV, PT_SM) renamed to PL_ prefixes because they describe plan phase *behavior*, not prompt/reference file *contents*. PT (3.8) stays as the 6 requirements about the physical reference files.

### State & Data

#### State file design (motivation and additions over ridl.json)

ridl.json had several gaps: rigid sequential ordering (no parallel iterations), no phase-level tracking (only criteria statuses), no agent activity state (GUI blind until test status changes), and no real-time visibility (no heartbeat).

State file additions:
- **Split architecture**: global `plet/state.json` for project-wide data + per-iteration `plet/state/{iteration_id}.json` for runtime state. Eliminates write conflicts during parallel execution.
- **Iteration lifecycle**: `ineligible` (deps not met), `queued` (ready for pickup), `implementing`, `verifying`, `complete`, `blocked`
- **Agent activity**: `idle`, `reading_context`, `implementing`, `running_checks`, `committing`, `wrapping_up` with human-readable `activityDetail` (e.g., "red: writing failing test for AC_3")
- **Agent ID**: which agent session is working on an iteration
- **Dependencies**: per-iteration array + global dependency map for efficient eligibility evaluation
- **Parallel groups**: top-level grouping of concurrently executable iterations
- **Timestamps**: `lastUpdated` at top level and per-iteration; `lastHeartbeat` for stale detection (> 5 min = potentially crashed)
- **Two-state-per-criterion model**: each criterion has separate `implementation` and `verification` objects (each with status, evidence, timestamp, elapsedSeconds), plus a derived top-level `status`
- **Criterion statuses**: `not_started`, `fail`, `pass`, `error`, `skipped` (with `skipRationale` for untestable criteria)
- **Structured progress data**: phase timestamps, per-phase attempt counts, summary, files changed. state.json is snapshot of now; progress.md is append-only history.
- **Breakpoints**: top-level `before`/`after` arrays of iteration IDs — orchestrator pauses at these points. Separate from lifecycle (user directive to orchestrator, not iteration property).
- **Schema version**: `schemaVersion` field independent of spec version, for format evolution
- **Atomic writes**: agents write to temp file then rename (POSIX atomic rename). Acceptable for v1: direct Write tool (single writer per state file, no concurrent corruption risk).

#### Artifact sync via fingerprints

Lightweight consistency checking across plan artifacts without file hashing. Fingerprints combine nested ID arrays (structural tracking, useful in git history) with a `lastNonTrivialUpdate` timestamp (content drift detection):
- **requirements.md** includes a fingerprint: `lastNonTrivialUpdate` timestamp, milestones as array, requirement IDs grouped by prefix. Future Considerations and Open Questions are excluded.
- **iterations.md** stores two fingerprints: the requirements fingerprint it was generated from, and its own iterations fingerprint
- **state.json** stores the iterations fingerprint only (which embeds the requirements fingerprint). Staleness is checked sequentially.
- Stale artifacts trigger a user-facing warning with option to regenerate or consistency pass
- Frozen iterations are always preserved during regeneration
- Agents determine triviality — typo fixes don't bump the timestamp. Edge cases: ask the human.

Example fingerprint structures:

**requirements.md fingerprint:**
```json
{
  "lastNonTrivialUpdate": "2026-03-07T14:30:00Z",
  "milestones": ["MS_1", "MS_2"],
  "requirements": {
    "FR": ["FR_1", "FR_2", "FR_3"],
    "NF": ["NF_1", "NF_2"],
    "DX": ["DX_1", "DX_2"]
  }
}
```

**iterations.md fingerprint:**
```json
{
  "requirementsFingerprint": { "...": "..." },
  "lastNonTrivialUpdate": "2026-03-07T15:00:00Z",
  "iterations": {
    "MS_1": ["ID_001", "ID_002"],
    "MS_2": ["ID_003", "ID_004"]
  }
}
```

#### `elapsedSeconds` tracking

Added to both per-criterion implementation/verification objects and at the iteration level. Per-criterion captures time from start to completion. Iteration level tracks per-phase-attempt durations (`impl_1`, `verify_1`, etc.) and `total`. Updated opportunistically — on heartbeat writes, on any state file write, and at end of each phase. No dedicated writes needed.

#### Plet ID scheme and entry fencing

**Problem:** Runtime artifacts (progress.md, learnings.md, emergent.md) are append-only markdown files. When parallel agents append entries at nearly the same time, git merge conflicts arise because every entry boundary is an identical `---` separator.

**Solution:** Plet IDs + start/end fences. Each entry gets a globally unique, two-way decodable plet ID and is wrapped in fences that give git unique anchor lines.

**Plet ID format:** `{type}_{crockford32}_{...context segments}`
- Type prefix: 3 chars by convention, 4 allowed. First char must be a letter (a-z). Remaining: letters or digits.
- Crockford Base32 timestamp: Unix milliseconds (always 10 chars). Alphanumeric only (0-9, A-Z excluding I/L/O/U), lexicographically sortable.
- Context segments after type+timestamp are type-specific, underscore-separated.
- Runtime artifact entries use: `{iteration}_{phase_attempt}` (e.g., `id001_i1`)
- Casing: type prefix lowercase, Crockford timestamp uppercase, context segments per type spec. Parsers must be case-insensitive.
- Known type prefixes: `epr` (entry progress), `eln` (entry learnings), `eem` (entry emergent), `vrp` (verification report). Reserved: `ttr` (trace transcript), `tev` (trace events).
- Example: `epr_01JD8X3K7M_id001_i1`
- Properties: globally unique, time-sortable, two-way decodable (split on `_`), self-describing (type prefix), composable, extensible

**EM_N vs plet ID distinction (RT_3, RT_11):** Emergent items carry two IDs: the `EM_N` semantic ID (human-facing, stable, referenced in refine conversations) and the plet ID (structural, for fencing and cross-references). Different purposes, both appear on every emergent entry.

**Fence structure:**
- Start fence: `<div id="plet-{pletId}"></div>` — invisible HTML anchor, unique for git
- Visual separator: `---` on its own line (renders as horizontal rule)
- End fence: `<div id="END-plet-{pletId}"></div>` — symmetric with start fence
- The `plet-` prefix is HTML namespace hygiene. The plet ID itself is the portable reference used in JSON fields, grep, and conversation.

**Crockford Base32 prefix filtering:** Because Crockford Base32 is lexicographically sortable, leading characters correspond to rough time buckets — useful for grep-based temporal filtering without decoding:

| Prefix chars | Time span per prefix value | Practical use |
|-------------|---------------------------|---------------|
| 1 | ~1,115 years | Epoch-level (all modern dates share `0`) |
| 2 | ~34.8 years | Generational (all 2020s-2050s share `01`) |
| 3 | ~1.1 years | Annual (`01K` ≈ 2026) |
| 4 | ~12.4 days | Biweekly sprint |
| 5 | ~9.3 hours | Work session |
| 6 | ~17.5 minutes | Fine-grained session segment |
| 7 | ~32.8 seconds | Near-exact moment |
| 8 | ~1.0 second | Subsecond precision |
| 9 | ~32 ms | Millisecond precision (rarely useful for grep) |

Practical sweet spots: prefix 4 (sprint/week), prefix 5 (session), prefix 3 (annual).

**Rejected fencing alternatives:**
- (A) Unique separator lines (`--- plet 01JD... ---`): breaks the thematic break — renders as plain text
- (B) HTML comment pairs: both fences invisible, no addressable anchor
- (C) Hybrid separator + HTML comment: inconsistent metaphors
- (D) One entry per file: eliminates merge conflicts but contradicts "single file for humans to scan"
- (E) Entry ID in H3 heading: decided to keep existing H3 format, add separate `**PletId:**` KV line
- (F) Single `plet-entry-` prefix: IDs not self-describing without file context. Replaced by 3-letter type prefixes.
- (G) End fence as HTML comment: lacks visual symmetry with `<div>` start fence

### Execution

#### Git branch strategy
- Each iteration works on its own branch (`plet/loop/{iteration_id}`) — changed from `plet/{iteration_id}` to match the hierarchical `/` convention used by audit tags (`plet/audit/...`). GUI tools get clean second-level filtering.
- Branch persists across impl and verify phases
- After iteration reaches `complete`, rebase onto main working branch and fast-forward merge
- Linear history is strongly preferred
- Agents commit incrementally during each phase for crash recovery
- At end of each phase, squash into a single commit
- Commit convention: `plet: [{iteration_id}] {phase}-{attempt} - {title}`
- If an iteration cycles (impl-1, verify-1, impl-2, verify-2), each phase is a separate squashed commit

#### Parallelization
- Default: skill spawns subagents for independent iterations
- Dependency-graph-driven — iterations form a DAG, not a strict sequence
- External tools (GUI, other sessions) can also drive execution by reading the state file
- The orchestrator re-evaluates eligible work after each iteration completes

#### Missing dependency self-correction

If an agent discovers a missing dependency during execution (prerequisite work doesn't exist), it fixes the DAG in place — adds the dependency to state.json and per-iteration state, sets lifecycle to `ineligible`, documents across all four runtime artifacts, and returns. Not a blocker — the loop continues and the iteration auto-queues when the missing dep completes. Does not count against retry limit. Dependency graph validation step added to plan phase iteration review.

#### Test suite execution strategy (EX_4)

On large projects, full test suites can take 4-5 minutes. With 5 acceptance criteria, 7 full runs compounds to ~35 minutes. Adopted tiered approach: agent times the first full run and decides strategy. ~30s is a recommended threshold but agent uses discretion. Fast suite = full suite every green step. Slow suite = most relevant subset using the project's test grouping mechanisms. Full suite only at phase end as a final gate.

**Rejected alternatives:**
- Full suite only at phase end — fastest but regressions caught too late
- Full suite at checkpoints (every N criteria) — interesting but adds complexity
- Pure agent discretion with no guidance — too unstructured for v1

#### `tagBeforeSquash` — audit tags before squash (EX_17)

Incremental commits are squashed at end of each phase for clean history. `tagBeforeSquash` preserves the pre-squash state as a git tag so the chain of work can be audited. Tag naming: `plet/audit/{iteration_id}/{phase}-{attempt}` — hierarchical `/` separators allow GUI tools to filter at three levels. Config: global default in `state.json` (inherited at initialization), per-iteration override. Auto-enables if verification fails. Default off.

#### Context window management for subagent reads

Runtime artifacts grow unbounded, so subagents can't naively read everything. Tiered approach per artifact:
- **requirements.md, emergent.md** — orchestrator injects relevant sections based on the iteration's requirement IDs
- **progress.md** — skip if large, read last ~10 entries if medium-sized. State files already cover "what's done"
- **learnings.md** — skip if large; orchestrator filters by relevance (matching files/modules, requirement IDs, category tags) plus project-wide entries
- **CLAUDE.md, README.md, iteration definition, state file** — always read in full (small, essential)

#### Trace capture: raw I/O + semantic events

Subagents don't self-log full I/O — that's impractical and wasteful of context. Trace is split into two files per phase: (1) raw I/O transcript (`{id}-{phase}-{attempt}-transcript.jsonl`) captured automatically by the orchestrator from Claude Code's `--output-format stream-json` output, and (2) semantic events (`{id}-{phase}-{attempt}-events.ndjson`) written by the subagent for decisions, criterion updates, lifecycle changes, activity changes, and errors. Both have timestamps; a GUI merges by time. `-transcript` suffix chosen over `-raw`/`-stream`/`-io`/`-session` because it describes what the file contains rather than how it was captured.

### Verification

#### Verification reports in per-iteration state (VF_21–VF_24)

Each verification attempt appends a report to the `verificationReports` array (never overwritten). Reports have `vrp` plet IDs, a verdict, compact `criteriaResults` index, and two-level `relatedEntries` (report-level for iteration-spanning concerns, criterion-level for single-AC findings). `lastVerdict` convenience field at the iteration state top level. Written after artifact entries so plet IDs are available for `relatedEntries`.

#### Verification report `findings` field (VF_24)

Array of strings for observations beyond the summary or per-criterion one-liners. Can reference plet IDs inline as plain text. Intentionally overlaps with learnings — the report is a self-contained snapshot of one verification attempt, while learnings persist across iterations. Same insight, different lifespans and audiences. The overlap is a feature, not a bug.

#### Dual-source resolution for verification reports

The verification report is described in two places: state-schema.md (field-level schema, types, example JSON) and verify.md (intent — what kind of information to capture and why). verify.md avoids repeating field names and types, describing the report in terms of what to capture rather than how to structure it. Prevents drift — state-schema.md is the single source for structure.

#### Verdict enum and progress.md status semantics

Three verdict values: `passed` (all pass, iteration frozen), `rejected` (issues found, returning to impl), `blocked` (needs human input). Used `passed` instead of `complete` to avoid collision with the `complete` lifecycle value. Progress.md status reflects the *phase attempt* outcome, not the iteration outcome — a cycle-back is a `COMPLETE` phase attempt (the verify agent finished its work) with a parenthetical verdict: `COMPLETE (passed, frozen)`, `COMPLETE (rejected, cycle back)`, `BLOCKED`.

#### Retry exhaustion after `rejected` verdict

When the verify agent rejects and retry limits are exhausted (EX_14), the orchestrator transitions to `lifecycle: "blocked"` and writes progress/emergent entries. The verify agent is unaware of retry policy — it always reports its verdict; the orchestrator decides. Chose `blocked` lifecycle over a new value like `exhausted` — the iteration genuinely needs human intervention.

#### Verification cycle-back writes red tests (VF_16)

On cycle-back (Path C — substantial issues), the verify agent writes failing tests that demonstrate each finding. The next impl agent inherits these as green-step targets — red/green handoff across the agent boundary. For non-test-expressible issues (wrong abstraction, coupling), the verify agent skips the red test and documents the rationale. The branch is left with intentionally failing tests — an explicit exception to the "all tests must pass" rule.

### Refine

#### Milestone assignment during refine (RF_14, RF_15)

Frozen milestones (all iterations `complete`) don't accept new iterations, except the most recent milestone which is never considered frozen ("complete for now") — without this exception, late-stage refinements would produce a series of single-iteration milestones. Any unfrozen milestone is fair game. Heuristics for new milestone: scope magnitude (3+), version significance, origin clustering, milestone size (6+), theme coherence. Agent states which heuristic; user overrides.

When all iterations are complete and new iterations are being added, explicitly ask the user whether to add to the most recent milestone or create a new one — don't silently default.

#### Blockers first in refine (RF_8)

Blocked iterations are surfaced as Step 1 in the refine phase, before emergent item triage. Blockers represent lost progress and are the highest priority for human attention.

**Rationale:** Blockers are stalled work — agents already spent cycles and hit a wall. Unblocking them gets value from that spent effort. Emergent items are informational — they can wait.

**Rejected alternative:** Emergent triage first (original draft ordering). User corrected: "blockers first. they are the priority."

#### No trace writing for refine phase

Refine is interactive in the main conversation, not a subagent. Decisions are captured in better places: NOTES.md for rationale, emergent.md outcomes for triage, requirements.md and iterations.md for actual changes.

**Rationale:** Trace files serve subagents — they capture decisions in contexts that are discarded. The refine phase runs in the main conversation where the human is present. Writing trace would duplicate what's already in NOTES.md, emergent.md outcomes, and the artifacts themselves.

**Rejected alternative:** Writing semantic events to a refine-specific trace file. Adds overhead without value — no consumer needs it.

#### Explicit confirmation before re-queuing blocked iterations

After resolving a blocker, the agent must summarize the resolution conversation and ask "are you comfortable re-queuing this iteration?" with explicit A/B/C options (re-queue / not yet / split). No silent state file changes.

**Rationale:** Re-queuing sends work back to autonomous agents. If the resolution was incomplete or the user isn't confident, the agent will waste another cycle and potentially block again. The cost of asking is one interaction; the cost of premature re-queuing is a lost agent cycle.

**Rejected alternative:** Auto-re-queue after resolution (original draft behavior). User: "there should be very strong language asking the user if this iter is ready to be re-queued."

#### Progress.md writes during refine: per-decision + stage summary

Refine appends to progress.md at two granularities: (1) per-decision entries as they happen (each triage action, each re-queue, each revise/reset/withdraw), and (2) a stage summary after completing each step. All use `phase: refine`.

**Rationale:** Per-decision entries give the next impl agent context on why an iteration is back in the queue or why the spec changed. Stage summaries give humans a quick overview without reading every per-decision entry. Both are needed.

Also considered end-of-session summary only (loses per-decision context), per-decision only without summary (hard for humans to scan), and no progress.md writes at all. User: "it should append. not after each session but more regularly. definitely after re-queueing."

#### `withdrawn` lifecycle value

New terminal lifecycle state for iterations deliberately retired during refine. Chose `withdrawn` over alternatives: `superseded` (too specific — only covers replacement), `cancelled` (implies we just stopped, lacks the "deliberate decision" nuance), `retired` (ambiguous synonym). `withdrawn` covers all cases: superseded, user changed mind, descoped, no longer relevant.

**Rejected alternatives:** `superseded`, `cancelled`, `retired`, `obsolete`, `archived`, `displaced`, `deprecated`, `rebased`.

#### "Revise" not "Preserve" for partially complete iterations (RF_9)

The option for updating a partially complete iteration in place is called "Revise."

**Rationale:** "Preserve" implied keeping things unchanged, but the whole point is modifying criteria while keeping existing progress. "Revise" accurately describes what happens — updating the iteration's definition while retaining completed work.

**Alternatives considered:** Update (direct but generic), Amend (formal), Adjust (implies light touch). User chose Revise — "reworking with intent" felt right.

#### Withdraw protocol: full impact summary + cascading resolution

Withdrawing is potentially disruptive. Before executing, the agent must present: (1) which PRD requirements lose coverage, (2) full downstream dependency chain affected, (3) milestone impact. User must explicitly confirm after seeing the impact. If downstream dependents exist, each must be individually resolved (revise/reset/withdraw) — no orphaned dependencies.

**Rationale:** User: "withdrawing is potentially a disruptive option and shouldn't be done lightly and especially shouldn't be done in ignorance of the ramifications." The impact summary ensures the user makes an informed decision. Cascading resolution prevents orphaned dependencies that would leave iterations stuck as `ineligible` forever.

Also considered blocking withdraw when downstream deps exist (too restrictive), auto-cascading withdraw to all dependents (too aggressive — some may be re-pointable), and allowing withdraw with no cascade (leaves broken dependency graph).

#### "More detail" option for partially complete iterations (RF_9)

Added a 4th option (D) to the revise/reset/withdraw prompt: "More detail — show me the full context before I decide." Shows full criteria status/evidence, progress entries, learnings, emergent entries, and trace highlights. After presenting detail, the agent recommends A/B/C before re-presenting the options.

**Rationale:** The initial summary (which criteria pass/fail, attempt count) may not be enough for the user to make a confident decision. Option D lets the user dig deeper before committing. The agent's recommendation after showing detail helps the user who wants guidance but had to see the evidence first.

#### Always walk through every refine step, even when empty

When a step has zero items (e.g., no blockers, no pending emergent items), the agent explicitly tells the user and moves on: "No blocked iterations — moving to Step 2." Never skip steps silently.

**Rationale:** User: "we want the user to be confident that we are not skipping steps. it's just that this time there are no items in those steps." Skipping to a later step makes the user wonder what was missed.

Also considered skipping empty steps (efficient but erodes trust) and jumping straight to status summary (misses learnings review, which can surface patterns even without pending items).

#### Learnings-driven spec changes use plet ID for traceability

When a learnings pattern leads to a spec change in the learnings review step, the requirement text references the learnings entry's plet ID (e.g., `(eln_01JD8X3K7M_id001_i1)`) — same pattern as triage using `(EM_N)`.

**Rationale:** Every spec change should be traceable to its source. Learnings entries already have plet IDs, so this is zero-cost traceability.

Also considered creating an emergent entry for each learnings-driven change then immediately approving it (consistent EM_N trail but busywork), and no traceability reference at all. User: "learnings have a plet ID. use that as the equivalent of EM_N."

#### Cascading consistency pass for refine (RF_16, Step 10)

The refine phase touches more files than any other phase (reads 4 artifacts, updates 6, modifies fingerprints across 3). Step 10 replaces the generic consistency pass with a structured cascading check following the data flow: decisions → requirements.md → iterations.md → state files. Each stage verifies the downstream artifact reflects everything upstream. This catches drift at the boundaries between artifacts rather than checking each file in isolation. Added as RF_16 in the PRD.

#### `refine` phase value added to format spec

formats.md Phase field expanded from `impl | verify` to `impl | verify | refine`. Plet ID context segment `r1` (refine session 1) added alongside `i1`/`v2`. Discovered via consistency pass — refine.md prescribed `phase: refine` but the format spec didn't allow it.

#### `refineSessionCount` in state.json

Added to global state.json to track refine session number. Incremented at the start of each refine phase entry. Used as the attempt number in plet ID context segments (`r1`, `r2`, etc.).

**Rationale:** Impl/verify track attempts in per-iteration state. Refine is project-level, so the counter lives in global state. Considered using timestamp-only (no counter) since the Crockford segment already gives uniqueness, but the session number enables grouping — grep `_r3` to see everything from one refine session. The grouping value was the tiebreaker.

#### `proj` sentinel for project-level plet IDs

Refine-phase entries that aren't tied to a specific iteration (stage summaries, triage summaries) use `proj` as the iteration context segment: `epr_01JD8X3K7M_proj_r1`. Per-iteration refine entries (re-queuing ID_005) still use the iteration ID: `epr_01JD8X3K7M_id005_r1`. Keeps the plet ID segment structure consistent and parseable.

**Subplets note:** `proj` is unambiguous within a single plet directory. In a multi-subplet scenario, each subplet has its own artifacts, so `proj` stays scoped. See Multi-Developer Analysis open threads for cross-subplet plet ID considerations.

### Cross-cutting

#### Consistency pass flavors

Four flavors codified: (1) pattern grep, (2) section read, (3) cross-reference check, (4) full structural scan. Flavors 1-3 use standard read-only tools and need no confirmation. Flavor 4 spawns an Explore agent — confirm first unless clearly warranted. Always state which flavor was used and recommend escalation if results suggest it.

#### Decision Discipline (CLAUDE.md)

Discovered during the refine.md build: we designed RF_16 (cascading consistency pass) and immediately failed to cascade it into the PRD — the exact failure mode it's designed to catch. Root cause: NOTES.md Discipline captures *what was decided* but doesn't ensure the decision *lands in all affected artifacts*. Decision Discipline is the complement: after capturing a decision in NOTES.md, trace it through the data flow (PRD → reference files → schemas → PLAN.md). Two-step flow: (1) capture (NOTES.md Discipline), (2) cascade (Decision Discipline). Kept as separate sections in CLAUDE.md — same spirit, distinct responsibilities.

---

## Global Conventions

- All IDs use underscore format: `XX_N` (e.g., `FR_1`, `PL_3`, `MS_1`, `EM_5`) — underscores over dashes so a double-click selects the entire ID for copy-paste. Slightly less aesthetic but worth the ergonomic trade.
- Sub-groups use `XX_YY_N` (e.g., `UI_NAV_1`) when there is a logical grouping or large item count

### ID Stability (decided)

Considered approaches for stable IDs when editing PRDs:

- **Renumbering**: rejected — breaks cross-references
- **Letter suffixes (`XX_Na`)**: rejected — user dislikes the aesthetic
- **Sub-numbering (`XX_N_N`)**: considered for ordered insertion, adds complexity
- **Semantic IDs (`FR_AUTH_TOKEN`)**: verbose, meaning can drift
- **Append-only with gaps**: **chosen** — simplest, guarantees stability. Gaps visually signal "this was added later."

**Rules:**
1. New items get the next available number in their prefix group
2. Deleted items leave a gap
3. Numbers don't imply ordering — document position determines order
4. IDs are stable once assigned — never renumber, never reuse

---

## Lineage

plet draws from three sources:

1. Ralph loops (both the general pattern and the snarktank/chief implementations)
2. RIDL (the author's opinionated implementation of Ralph loops)
3. Plan mode as seen in Claude Code, Cursor, etc. (interactive refinement)

### What Ralph loops get right
- Autonomous iterations — agents do real work, not just suggestions
- Fresh context windows — each iteration starts clean, no contamination
- Spec first — the PRD drives everything, not ad hoc prompting
- PRD decomposition into agent-sized, iterable chunks
- Runtime artifacts (progress.md, etc.) — structured output that outlives the agent session
- State tracking via prd.json — machine-readable iteration status persisted to disk
- Snarktank's numbered-letter Q&A system for interactive clarification — adopted by plet's plan phase

### Where Ralph loops fell short
- No verification phase — no independent check that work was done correctly
- No refinement loop — spec is static, doesn't evolve from what agents learn
- Fairly linear — no parallel iteration support
- No multi-developer support — single developer, single session
- Requires external scaffolding (runner, harness) that must stay in sync with the loop's formats — hard to iterate on one without breaking the other

### What RIDL added over Ralph loops
- Two-phase iteration split (implementation → verification) — the key structural addition
- Separate learnings.md from progress.md — agent-facing knowledge vs historical record, different audiences
- Three-file pipeline (prd.md → ridl.md → ridl.json) — cleaner decomposition than alternatives, each file has a clear purpose
- Trace logging for full execution traceability

### Where RIDL loops fell short
- ridl.json too rigid (sequential ordering, no parallel iterations, no phase tracking, no agent activity state)
- External harness dependency (Ridler.app required) — same scaffolding sync problem as Ralph loops
- Too much logic in the runner — tight coupling between harness and loop behavior
- Still no multi-dev support
- Still fairly linear despite the DAG concept in ridl.json
- Felt like using three separate tools (prd skill, ridl skill, Ridler.app) to accomplish one workflow

### What plan mode brings
- Interactive, iterative spec refinement
- The spec is a living document that improves as agents discover gaps
- Human steering at natural checkpoints

### What plet adds
- Self-sufficient orchestration — runs natively inside Claude Code, no external harness or runner
- Single entry point (`/plet`) with state-driven routing — user never needs to remember which phase they're in
- Interactive plan phase with human steering built in — PRD creation and iteration decomposition in one flow
- Dependency graph with parallel execution — not strictly sequential
- Split state architecture with lifecycle phases, agent activity, heartbeats, and two-state-per-criterion model
- Real-time agent activity state — GUI can show what the agent is doing, not just pass/fail
- Built-in refine phase — triages emergent items, updates the spec, re-plans
- Living spec — improves as agents discover gaps, not a static document
- Four runtime artifacts (PLET) with distinct audiences — not just a log file

---

## Important Concepts & Insights

### Why state on disk matters
"We highly value the ability to start with a new agent for various reasons. One is parallelization. Another is the fresh context is important for things like independent verification." — user

### Separation of artifacts by audience
- **progress.md** — what was done (historical record, append-only)
- **learnings.md** — agent-facing knowledge (helps future agents)
- **emergent.md** — human-facing items (needs human decision)
- **trace/** — two files per phase: `-transcript.jsonl` (raw I/O, orchestrator-captured) and `-events.ndjson` (semantic events, subagent-written)

### Runtime artifact write safety
- All three .md artifacts are single files (humans scan one file better than multiple)
- Agents use POSIX atomic append semantics (O_APPEND) — complete self-contained blocks in a single write
- ~4KB entry limit is a readability constraint, not a technical one. On local filesystems, O_APPEND is atomic at any reasonable size due to kernel-level inode locking. PIPE_BUF (4KB Linux, 512 bytes macOS) only applies to pipes/FIFOs, not regular files.
- Per-iteration NDJSON trace files have no conflict risk (one file per phase)

### Verification independence
The verification agent verifies the *result*, not the *process*. It does not initially read implementation diffs. It reads the codebase as it stands, runs checks, and independently confirms acceptance criteria. If it needs to dig deeper later, it can read diffs, but never as a starting point. This prevents rubber-stamping.

### Blockers are critical events
Every blocker represents loss of progress and requires human investigation. Blockers must be documented across ALL four artifact types: trace (full detail), progress (BLOCKED status), emergent (what human needs to resolve), learnings (diagnostic context). "The quality of blocker documentation determines whether the human can help." — user

### Self-improvement is load-bearing
As models improve, skills like plet go out of date. plet needs the ability to improve itself. Two levels: micro (session-to-session via CLAUDE.md — agent notices something, offers to write it down) and macro (Future Consideration #11 — plet analyzing runtime artifacts to improve its own PRD). Both are human-gated. Without them, instructions calcify as the project evolves.

### When in doubt, add the dependency
Missing dependencies are dangerous (agent wastes a cycle, must self-correct). False dependencies are harmless (only reduce parallelism slightly). Always err on the side of adding a dependency.

### No metrics that reward lousy verification
First-pass verification rate sounds useful but incentivizes rubber-stamping. Never use metrics that reward the verification agent for passing easily.

### Use subagents to explore during design
During the execute.md build, we used subagents to research ridler2's trace mechanism, check Claude Code flags, test tool capabilities, and verify file paths. Subagents are cheap and fast for exploratory validation — use proactively during brainstorming, not just for delegated work.

### NOTES.md as institutional memory
The notes file is the connective tissue between CLAUDE.md (project config) and the PRD (spec). It captures the "why" so the PRD can stay clean.

---

## PRD Status

All sections reviewed and approved. The PRD is the source of truth for requirement IDs and counts.

### Key design annotations by section (not duplicated in PRD)
- **GC**: GC_2 — agents prefer making decisions + logging over blocking
- **OR**: OR_4 includes `verifying` lifecycle. OR_11 removed (merged into `/plet loop`). OR_13 — skip scoped to individual acceptance criteria, not iterations
- **PL**: Plan phase intro is prose above the table (interactive, human-driven). PL_12 — write to disk on approval. PL_13–PL_14 are P1
- **SF**: P0s first. Split state architecture. SF_24 — schema version migration. SF_25 — entry fencing for git merge safety
- **EX**: EX_23 — heartbeat writes. EX_24 — missing dependency self-correction (does not count against retries). EX_25 — false dependencies are harmless
- **VF**: VF_7–VF_13 are the VSDD-inspired deep verification items. VF_19–VF_20 are P1
- **RT**: Formats defined at high level; templates in references/formats.md. Stable contract (additive only). RT_11 — plet ID scheme for entry IDs
- **RF**: RF_1 — refine is human-driven with clean UX. Blocked iterations surfaced alongside emergent items
- **PT**: Physical reference files only. Trace NDJSON schema in state-schema.md (PT_6)
- **NF**: No performance section (intentional). No priority column (all fundamental). NF_8 — state format for external GUI consumers
- **DX**: DX_1 — dev dependency, downgraded to P1
- **PL_DX**: Three principles: Readability, Debug-ability, Resilience. PL_DX_17 — living notes doc
- **PL_CT**: Renamed from PT_CT
- **PL_TV**: Red/green first (PL_TV_1). Sanity check test (PL_TV_9), anti-mock-overreliance (PL_TV_10)
- **PL_SM**: Renamed from PT_SM

---

## Things to Monitor

### Injection payload sizes

Each subagent gets a phase-specific reference file plus shared context. Updated estimates as of Phase 2b.3:

**Implementation subagent:**
- execute.md: ~4,100 tokens (442 lines)
- formats.md: ~2,500 tokens (392 lines)
- state-schema.md (relevant sections): ~3,000 tokens
- requirements.md: varies (5K-15K depending on project)
- learnings.md: varies (filtered for relevance)
- iteration definition: ~500 tokens
- **Total: ~18K-28K tokens**, leaving 170K+ of 200K for actual work.

**Verification subagent:**
- verify.md: ~5,100 tokens (519 lines)
- formats.md: ~2,500 tokens (392 lines)
- state-schema.md: ~4,300 tokens (549 lines — full file, verify needs all sections)
- requirements.md: varies (5K-15K)
- learnings.md: varies (filtered for relevance)
- iteration definition: ~500 tokens
- **Total: ~20K-30K tokens**, leaving 170K+ of 200K for actual work.

**Plan subagent:**
- plan.md: ~4,100 tokens (443 lines)
- formats.md: ~2,500 tokens
- **Total: ~7K-10K tokens** (lightest payload).

Comfortable for now across all phases. If context pressure becomes an issue, edge case sections (blocker, failed attempt, missing dependency, skip) could be split into a separate reference file only injected when relevant. Monitor during real usage.

### state-schema.md size

549 lines as of Phase 2b.3. Largest reference file — it's injected in full to verify subagents (who need all sections). No split needed — the file is logically cohesive. Splitting would create cross-reference overhead without reducing injection size. Revisit if it grows past ~700 lines or verify agents show signs of context exhaustion. Also noted in PLAN.md under "Watch: combined injection size."

### Consistency drift patterns

As consistency passes are used, note what keeps drifting (which files, which patterns, which flavors catch it). This data will inform whether to build a dedicated skill or subcommand.

---

## Open Questions

### Consistency checking as a skill?

Could the consistency pass flavors become a standalone skill (`/consistency`) or plet subcommand (`/plet check`)? Premature for v1 — the CLAUDE.md instructions work well as agent conventions.

Key questions:
- Is it plet-specific (knows PRD ↔ NOTES ↔ PLAN ↔ reference files) or general-purpose?
- Flavors 1-3 are essentially "use Grep/Read intelligently" — does a skill add value?
- What recurring drift patterns emerge from real usage?
- Should it compose with plet phases (auto-run after plan changes or refine)?

### PRD input and disambiguation

plet's plan phase should accept any existing PRD as input, regardless of which skill or tool created it, and use it to produce a `requirements.md`. The PRD generation step is upstream of plet — plet operationalizes whatever spec it's given.

Known PRD-generation approaches:
- **snarktank** — adversarial multi-persona PRD generation
- **ridl (ridl-skills:prd)** — structured PRD with requirement tables
- **plet (plan phase)** — interactive spec refinement (can also generate from scratch)
- Presumably many other PRD/spec skills exist in the ecosystem

Key questions:
- When multiple PRD skills are loaded, how does the user signal which style they want? Need some disambiguation UX — "snarktank-style PRD? ridl-style? plet requirements doc? SKILLNAME-style?"
- No auto-detection of existing PRDs — the user says "read this first" or "start with this doc." But plet should let the user know that if they have an existing PRD, spec, or list of requirements, that's usually a great place to start.
- Existing docs are always just a starting point — plet's plan phase asks clarifying questions if the doc is insufficient, same as starting from scratch

---

## Multi-Developer Analysis

plet is currently designed for a single developer driving a single Claude Code session. Multi-developer workflows are planned for plet v2.x.y — not a v1 concern, but the state file architecture should not accidentally preclude it.

### Scenarios identified

1. **Small team, single PRD (2-3 devs):** Low coupling. Each dev runs their own plet session on their own branch. Merge point is git. Mostly works already.
2. **Large team, large PRD (10+ devs):** Natural decomposition is one PRD per feature. Hard part is the *seams* — when one dev's iteration changes an API another dev consumes.
3. **Handoff mid-loop:** One dev starts, another picks up. Stresses institutional memory design — are `emergent.md`, `learnings.md`, and `state.json` enough for a stranger to resume?
4. **Parallel PRDs with cross-cutting dependencies:** Two separate plet loops with a sequencing constraint between them.
5. **Build + QA in parallel:** Two plet sessions, same codebase, different goals, overlapping files.
6. **Refactor + feature collision:** Broad refactor vs deep feature — maximally painful merge conflicts.
7. **Spec change mid-flight:** PRD updated while multiple devs are mid-loop. Each orchestrator reads `prd.md` at launch — mid-session change is invisible until restart.

### Key insights

**The pattern is coupling, not team size.** 2-3 devs on one PRD have high coupling. 10 devs with per-feature PRDs have low coupling *until they don't* (shared schemas, APIs). Handoff and spec-change are about *temporal* coupling.

**Git-first isolation is probably the answer for v1.** Each developer runs their own session on their own branch with their own `plet/state.json`. Merge point is git.

**The hard problem is shared iterations, not shared state.** Different developers on *different* iterations from the same plan already works — the split state architecture minimizes conflicts. Same iterations = conflicts everywhere.

**plet's split state architecture already does most of the heavy lifting.** The main gap is human-level coordination (who's working on what), not agent-level coordination (solved by the DAG + lifecycle states).

### Three multi-developer modes

- **Fork mode** (easiest): Each developer forks the plet directory. Fully independent. Runtime artifacts conflict on merge but they're append-only — conflict resolution is straightforward.
- **Claim mode** (medium): Shared plan, developers "claim" iterations. The `agentId` / lifecycle fields already support this — `implementing` with an agent ID is effectively a claim.
- **Shared orchestration** (hardest): Single orchestrator aware of multiple humans. Probably not worth it — Claude Code sessions are single-user.

### `subplets/` directory for hierarchical decomposition

A simpler multi-developer model could use `subplets/` containing multiple independent `plet/` directories:

```
plet/                          # top-level PRD
subplets/
  auth/plet/                   # detailed PRD for auth feature
  billing/plet/                # detailed PRD for billing
```

Benefits: namespace isolation, each instance fully self-contained, cross-PRD visibility by scanning siblings, simpler than claim/shared orchestration.

**Multi-developer complexity spectrum:**

| Mode | Coupling | New machinery |
|------|----------|---------------|
| Fork | None | None (git only) |
| Flat `subplets/` | Colocated, independent | Naming convention |
| Hierarchical `plet/` + `subplets/` | Parent references children | Reference syntax, rollup status |
| Claim | Shared plan, divided ownership | Locking/claim semantics |
| Shared orchestration | Single plan, multiple humans | Multi-user orchestrator |

### Open threads
- Emergent/blocker ownership: `assignee` field on emergent entries (additive to current format)
- Refine is naturally single-threaded — one human refines at a time, others consume updated spec
- Does the orchestrator need to know about sibling `subplets/`?
- How do iterations in one subplet express dependencies on a sibling?
- Naming convention: `subplets/{feature-name}/` or `subplets/{developer-name}/`?
- The `proj` sentinel in plet IDs (used for project-level refine entries) is scoped to a single plet directory. If cross-subplet plet IDs ever need to be disambiguated, the iteration segment format will need a subplet-qualified alternative — constrained by underscore-as-delimiter and double-click-select ergonomics.

---

## Self-Improvement Analysis

Self-Improvement Analysis workflows are planned for plet v3.x.y — not a v1 concern
Future Consideration #11


### Why this is load-bearing

Most skills are static instructions written for today's model capabilities. They accumulate workarounds that become dead weight as models improve. execute.md alone is ~430 lines — some will be unnecessary in 6 months. Without a feedback loop, plet calcifies.

### Runtime artifacts are uniquely well-positioned

plet already produces structured, categorized data about its own performance: learnings capture what tripped agents up, emergent items capture spec gaps, trace files capture the full decision chain, progress captures pass/fail patterns. That's exactly the telemetry needed for self-analysis. Most systems would have to bolt on instrumentation — plet already has it.

### Design tension: meta-loop symmetry

plet improving its own PRD is refine-on-refine. The refine phase already analyzes runtime artifacts to improve the *target project's* spec. Self-improvement is the same pattern aimed inward. Elegant symmetry, but "improve the project" and "improve the tool" need a clear boundary. A separate skill or mode is the right approach.

### Things to watch for

- **Model-capability vs design-flaw distinction:** Remove guardrails no longer needed vs fix heuristics that were always wrong. Different remedies.
- **Testability of version bumps:** PRD changes need validation against a reference project. Otherwise self-edits are flying blind.
- **Bootstrapping question:** Can plet use plet to improve plet? Appealing but version consistency problem.

### Why capturing this now matters

Thinking about self-improvement during v1 design means the artifacts won't accidentally make it hard later. The runtime artifact formats, structured trace data, and separation of concerns all serve double duty as operational output and self-improvement telemetry.
