# plet-skills Development Notes

> **See also:** `guide/NOTES.md` for presentation/guide decisions. Routing rule in CLAUDE.md § NOTES.md Routing.

## Stable Label Convention

Every H2 section has a stable label: `NOTES_XXX: Title`. H3 subsections use the parent prefix: `NOTES_PLAN_HLP: PLAN_HLP — ...` (child of `NOTES_PLN`).

**Format:** `NOTES_{PARENT}_{CHILD}: Title`
- H2: `NOTES_XXX` (3-letter code)
- H3: `NOTES_{H2CODE}_{CHILD}` (parent + child)
- H4+: `NOTES_{H2CODE}_{H3CODE}_{N}` (for numbered items within a subsection)

Labels are append-only — never renumber or rename. Use `grep NOTES_PLAN_RFT` to find all refactor loop decisions.

**Time-ordered sections:** Any section with time-ordered entries uses H3 date markers to partition the stream. Empty markers stay — they indicate no activity during that period. New entries append at the bottom under the current marker.

**Relocation rule:** When moving content between sections, fully relocate — no "Moved to" or "Extracted to" pointers. Pointers rot. The destination is the canonical location.

## Table of Contents

| Label | Section |
|-------|---------|
| NOTES_DEF | What is plet? |
| NOTES_WRK | Core Workflow |
| NOTES_DST | Platform & Distribution |
| NOTES_INV | Invariants & Critical Requirements |
| NOTES_TAX | Taxonomy & Conventions |
| NOTES_INS | Important Concepts & Insights |
| NOTES_DES | Key Design Decisions |
| NOTES_PLN | Plan Discussions |
| NOTES_LIN | Lineage |
| NOTES_PRD | PRD Status |
| NOTES_TBR | Tooling Brainstorm |
| NOTES_MON | Things to Monitor |
| NOTES_GUI | GUI Design |
| NOTES_OPN | Open Questions |
| NOTES_EXP | Example Projects |
| NOTES_SUB | Subplets — Flexible Inheritance Model |
| NOTES_SIA | Self-Improvement Analysis |

## NOTES_DEF: What is plet?

**PLET = Progress, Learnings, Emergent items, Traces** — the four runtime artifacts the system produces. 

plet is a Claude Code skill that orchestrates spec-driven autonomous development. It combines interactive planning with autonomous implementation, verification, and iterative refinement — all running natively inside Claude Code without requiring an external harness. Inspired by and builds on Ralph loops — a spec-driven autonomous coding pattern — via RIDL (Ralph Iteration Definition List), the author's implementation of that pattern. plet is a merger between Claude Code's plan mode (interactive, iterative planning) and the RIDL PRD-driven autonomous loop (structured execution with runtime artifacts).

---

## NOTES_WRK: Core Workflow

**Plan -> Loop (Implement → Verify) -> Refine**

- **Plan** = spec (interactive requirements creation, iteration decomposition)
- **Loop** = autonomous implement→verify cycle:
  - **Implement** = implement then test (red/green discipline, subagents)
  - **Verify** = independent verification in a fresh context window
- **Refine** = uses Progress, Learnings, Emergent items, and Traces to improve the spec and re-plan

---

## NOTES_DST: Platform & Distribution

- Claude Code skill (SKILL.md + bundled reference files)
- Python enforcement scripts shipped in `skills/plet/scripts/` — stdlib only, zero external dependencies. Standards in `scripts/CLAUDE.md`.
- Published to github and distributed via Claude Code plugin marketplace
- Primary users: developers using Claude Code
- GUI/monitoring repos planned as separate future projects that read the state file

---

## NOTES_INV: Invariants & Critical Requirements

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

## NOTES_TAX: Taxonomy & Conventions

Canonical definitions for plet's vocabulary, document terms, artifact categories, and ID conventions. Decision rationale and rejected alternatives live in Key Design Decisions; this section is the reference.

### NOTES_TAX_1: Vocabulary Hierarchy

```
project (LOGA)
  └─ session (plan, loop1, refine1, loop2, ...)
       └─ iteration (ITR_001, ITR_002, ...)       ← loop sessions only
            └─ phase (implement, verify)
```

**Example showing interleaved sessions:**
```
project (LOGA)
├─ plan session
├─ loop session (loop1)
│  ├─ iteration (ITR_001)
│  │  ├─ implement phase
│  │  └─ verify phase
│  ├─ iteration (ITR_002)
│  │  └─ ...
│  └─ ...
├─ refine session (refine1)
├─ loop session (loop2)
│  └─ ...
├─ refine session (refine2)
├─ refine session (refine3)
├─ loop session (loop3)
│  └─ ...
└─ ...
```

| Level | Term | Formal? | Example |
|-------|------|---------|---------|
| 0 | **project** | yes | LOGA |
| 1 | **session** | yes | loop session, refine session, plan session |
| 2 | **iteration** | yes | ITR_001 (loop sessions only) |
| 3 | **phase** | yes | implement phase, verify phase |

- **Session** = a `/plet` invocation: plan session, loop session, refine session
- **Iteration** = a unit of work with acceptance criteria (loop sessions only)
- **Phase** = implement or verify within an iteration (not plan/loop/refine)
- **Phase in traces/entries vs phase in lifecycle:** The `--phase` flag in trace and entry scripts accepts a broader vocabulary than the iteration lifecycle. Lifecycle phases are `implement` and `verify` (Level 3). Trace/entry phases also include `plan`, `refine`, `orchestrator`, and `unknown` — these label *who did the work* for observability, not where we are in the iteration lifecycle. `plan` and `refine` are Level 1 sessions, not Level 3 phases, but they're valid phase values for attribution. `orchestrator` represents loop-management work (scheduling, gating, fingerprinting) outside any iteration phase. `unknown` is the fallback when no `--phase` is provided. Gate scripts, iter_state, and git scripts retain the strict `["implement", "verify"]` — they only operate within iteration phases.
- Retry numbering (`implement-1`, `implement-2`) is a detail within phases, not a formal hierarchy level
- "Cycle" is informal shorthand for one implement run + one verify run

### NOTES_TAX_2: Document Terms

| Term | Refers to | Scope |
|------|-----------|-------|
| **requirements** / **requirements doc** | `plet/requirements.md` | plet-specific — the file plet produces and consumes |
| **PRD** | A requirements document in the ridl-skills:prd format | Generic — any tool can produce a PRD (ridl-skills:prd, plet, manual) |
| **spec** | `requirements.md` + `iterations.md` together | plet-specific — the full plan output |

"The PRD" and "the requirements doc" are synonyms inside a plet project. "Spec" is broader — it includes iterations.

### NOTES_TAX_3: Artifact Categories

> Also in PLET.md (generalized for any target project, with full directory tree). This section is the canonical source for the taxonomy's evolution; PLET.md is the portable copy.

**1. Spec artifacts** (human-created during plan session)
- `plet/requirements.md` — PRD with requirement IDs, fingerprint
- `plet/iterations.md` — iteration definitions, dependencies, acceptance criteria, fingerprint

**2. State artifacts** (agent-written, real-time updated)
- `plet/state.json` — global state (dependency map, milestones, parallel groups, breakpoints)
- `plet/state/{iteration_id}.json` — per-iteration lifecycle, attempts, criteria status, verification reports

**3. Runtime artifacts** (agent-appended, append-only)
- `plet/progress.md` — activity log (audience: humans)
- `plet/learnings.md` — knowledge base (audience: agents)
- `plet/emergent.md` — triage queue (audience: humans)

**4. Trace artifacts** (execution telemetry)
- `plet/trace/{id}-{phase}-{attempt}-transcript.ndjson` — raw I/O (captured by `plet_invoke.py` in subprocess mode)
- `plet/trace/{id}-{phase}-{attempt}-events.ndjson` — semantic events (subagent-written via `plet_trace.py`)

**5. Version control artifacts**
- Integration branch: `plet/{projectId}/loop{N}/workstream`
- Iteration branch: `plet/{projectId}/loop{N}/{iteration_id}`
- Audit tags: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` (pre-squash preservation)
- Refine branch: `plet/{projectId}/refine{N}/workstream`
- Archive tags: `archive/plet/{projectId}/loop{N}/{path}`
- Commits: `plet: [ITR_xxx] phase-N - title` (squashed per phase)

**6. Memory** (institutional knowledge, checked-in)
- `CLAUDE.md` — project-specific instructions
- `PLET.md` — plet-specific instructions
- `NOTES.md` — decisions, rationale, open questions
- `FEEDBACK_FOO.md` — meta-observations about plet itself (process issues, instruction gaps, tooling friction)

**7. Configuration** (per-project behavior modification)
- Modify planner, refiner, implement agent, verify agent behavior
- *(No files defined yet — shape TBD, see Open Questions)*

### NOTES_TAX_4: Plet Directory Variables

During the loop phase, two copies of per-iteration state files exist. Variable names distinguish which copy:

| Variable | Meaning | Who writes | Used for |
|----------|---------|-----------|----------|
| `global_plet_dir` | Workstream copy (main working tree) | Orchestrator (verdict handoff only) | Scheduling (eligible), global state (state.json), final lifecycle |
| `worktree_plet_dir` | Iteration copy (git worktree) | Subagent only | Criteria, attempts, lifecycle during iteration, reports |
| `plet_dir` | Unspecified — could be either copy | Depends on caller | Generic functions (path derivation, validation, most scripts). The caller decides which copy to pass. Scripts like plet_state.py, plet_entries.py, etc. accept `plet_dir` and are agnostic — they work with whichever copy they're given. |

**No "root" prefix** — breaks for subplets where the "root" plet dir isn't the project root. "Global" means "the scheduling/workstream copy" regardless of nesting level.

**Where the distinction matters:** Only the orchestrator needs both copies simultaneously. All other scripts receive one `plet_dir` and operate on it without knowing which copy it is. The orchestrator is the boundary where `plet_dir` (from CLI) becomes `global_plet_dir`, and where `derive_worktree_plet_dir()` produces `worktree_plet_dir`.

### NOTES_TAX_5: Two-Level Status Model

Iteration status is tracked at two levels with distinct ownership:

| Level | Field | Location | Owner | Purpose |
|-------|-------|----------|-------|---------|
| **Loop lifecycle** | `lifecycles.ITR_xxx` | state.json (global) | Orchestrator | Which phase the iteration is in |
| **Phase activity** | `phaseActivity` | per-iteration file (worktree) | Subagent | What the agent is doing right now |

**Loop lifecycle values** (orchestrator writes these):
`queued` → `implementing` → `verifying` → `complete` / `blocked` / `queued` (retry) / `withdrawn`

**Phase activity values** differ by phase:

| Activity | Implement | Verify | Shared? |
|----------|:---------:|:------:|:-------:|
| `setup` | ✓ | ✓ | read context, pre-flight |
| `writing_tests` | ✓ | | writing failing test (red step) |
| `implementing` | ✓ | | implementing to pass test (green step) |
| `verifying` | | ✓ | checking criteria against code |
| `fixing` | | ✓ | fix-in-place (VF_15) |
| `writing_report` | | ✓ | composing verification report |
| `running_checks` | ✓ | ✓ | test suite, lint, format |
| `committing` | ✓ | ✓ | git operations |
| `wrapping_up` | ✓ | ✓ | artifacts, trace, gate check |
| `idle` | ✓ | ✓ | done |

The `activityDetail` string is a human-readable description overwritten on every transition (e.g., `"red: writing failing test for AC_3"`). Combined with `lastHeartbeat`, external consumers see what the agent is doing and whether it's alive.

**Phase activity is NOT a log** — it's a "current status" window. The log lives in progress.md (append-only) and trace events (append-only NDJSON).

**Rename:** `agentActivity` → `phaseActivity` to make the two-level system explicit. `agentId` stays (identifies which agent session).

**Enum rename:** `red` → `writing_tests`, `green` → `implementing`. GUI consumers display phaseActivity as badges/labels — "red" and "green" are TDD jargon that doesn't communicate well as a UI element. "Writing Tests" and "Implementing" are self-descriptive. The red/green concept lives in activityDetail strings (e.g., "red: writing failing test for AC_3") and reference docs.

### NOTES_TAX_6: Phase Verdicts

Each phase has an explicit verdict field written by the subagent as its final act. The orchestrator reads it and decides the next lifecycle transition. Replaces the old model where subagents wrote lifecycle directly (source of merge conflicts).

| Field | Phase | Values | Replaces |
|-------|-------|--------|----------|
| `implementVerdict` | implement | `completed`, `blocked` (null initially) | lifecycle → verifying handoff |
| `verifyVerdict` | verify | `passed`, `rejected`, `blocked` (null initially) | `lastVerdict` (removed) |

**Orchestrator calls `phase-start` before spawning subagent** (not the subagent's job). Prevents stale verdict reads on crash-before-start. Verdict clearing:
- Implement: clear both `implementVerdict` and `verifyVerdict` to null
- Verify: clear only `verifyVerdict` to null (`implementVerdict: "completed"` stays)

This refines SF_26: "During the subagent's execution, only the subagent writes to worktree per-iteration state. Pre-spawn setup by the orchestrator is allowed."

**Orchestrator reads verdicts from worktree after subagent exits.** `null` verdict = crash (subagent never set it). Guard assertion: `worktree_plet_dir != global_plet_dir` before verdict reads (prevents LOGA Run 3 class of bug).

**Post-gate enforces verdict is set.** Post-implement gate checks `implementVerdict` not null. Post-verify gate checks `verifyVerdict` not null. Turns "forgot to set signal" into a recoverable failure (gate catches → subagent fixes → clean exit).

**phaseActivity is cosmetic, verdicts are load-bearing.** Only verdicts drive lifecycle transitions. Orchestrator must NEVER make decisions based on phaseActivity.

### NOTES_TAX_7: Script Split — plet_state.py → GST + IST

The lifecycle extraction (seq 39) splits `plet_state.py` along the ownership boundary:

- **global_state.py** (GST) — state.json: `init`, `update-lifecycle`, `get-lifecycle`, `validate`
- **iter_state.py** (IST) — per-iteration files with high-level agent-friendly commands: `init`, `phase-start`, `update-activity`, `update-criterion`, `set-verdict`, `heartbeat`, `validate`

Design principle: commands match agent workflow, not JSON structure. `start-phase` replaces ~5 manual `update-field` calls. `set-verdict` auto-sets `phaseActivity` to `idle`. See specs/NOTES.md for full command design and rationale.

### NOTES_TAX_8: ID Conventions

- All IDs use underscore format: `XX_N` (e.g., `FR_1`, `PL_3`, `MS_1`, `EM_5`) — underscores over dashes so a double-click selects the entire ID for copy-paste. Slightly less aesthetic but worth the ergonomic trade. Longer prefixes (3-4 chars) are acceptable when they improve readability (e.g., `PLAN_SKL`).
- Sub-groups use `XX_YY_N` (e.g., `UI_NAV_1`) when there is a logical grouping or large item count
- Append-only with gaps — new items get the next available number, deleted items leave gaps, numbers don't imply ordering, IDs are stable once assigned (never renumber, never reuse)

### NOTES_TAX_9: Prefix Table

| Prefix | Artifact type | Where used |
|--------|--------------|------------|
| `PLAN` | Build plan parts (2-3 letter codes: SKL, REF, PY, EVL, etc.) | PLAN.md |
| `FOO` | Feedback/Observation/Oversight | FEEDBACK_FOO.md |
| `FR` | Functional requirements | prd.md |
| `NF` | Non-functional requirements | prd.md |
| `ID` | Iterations | iterations.md |
| `AC` | Acceptance criteria | iterations.md |
| `MS` | Milestones | iterations.md |
| `IMP` | Implement agent rules | phase-implement.md |
| `VF` | Verify agent rules | phase-verify.md |
| `PL` | Plan session rules | plan.md |
| `CASE` | Case study recommendations | `CASE_{PROJECT}_{RUN}_{N}` — all case studies. Replaces R_, S_, SP_, R6_ |
| `EX` (extractable) | Extractable skill inventory | EXTRACTABLE.md |
| `UNV`, `STA`, `ENT`, etc. | Script spec prefixes (11 scripts + sections) | specs/*.md — see `specs/NOTES.md` § Stable Label Prefixes |

---

## NOTES_INS: Important Concepts & Insights

### NOTES_INS_1: Agent-First CLI Design (2026-03-16)

plet's enforcement scripts are **agent tools** that humans occasionally debug — not developer tools that agents happen to use. This inversion changes the entire CLI design philosophy:

- **Predictability over ergonomics** — named args everywhere, no positional shortcuts
- **Defensive validation** — treat agents as potentially careless users, never produce tracebacks
- **Self-documenting output** — `--output json` on every command with metadata and actionable recovery info
- **Safe by default** — `--dry-run` required on all mutating commands, strongly recommended in help text
- **Context-aware help** — 4-section structure: IMPORTANT → PITFALLS → USAGE → PURPOSE. Warnings before syntax. Purpose last.
- **Single resource per invocation** — scripts operate on one file/entity, agents control the loop. Predictable output size. Exception: commands whose primary job is producing a list from multiple resources.
- **Context window protection** — `--fields` limits JSON output with `fieldsIncluded`/`fieldsOmitted` metadata. Strongly recommended for high-output commands.

This complements "Skills for Judgment, Code for Compliance" — that principle says *what* to codify; agent-first CLI design says *how* to build the tools. Full details in `specs/NOTES.md` and `specs/conventions.md`.

### NOTES_INS_2: Why state on disk matters
"We highly value the ability to start with a new agent for various reasons. One is parallelization. Another is the fresh context is important for things like independent verification." — user

### NOTES_INS_3: Separation of artifacts by audience
- **progress.md** — what was done (historical record, append-only)
- **learnings.md** — agent-facing knowledge (helps future agents)
- **emergent.md** — human-facing items (needs human decision)
- **trace/** — two files per phase: `-transcript.ndjson` (raw I/O, captured by `plet_invoke.py`) and `-events.ndjson` (semantic events, subagent-written via `plet_trace.py`)

### NOTES_INS_4: Runtime artifact write safety
- All three .md artifacts are single files (humans scan one file better than multiple)
- Agents use POSIX atomic append semantics (O_APPEND) — complete self-contained blocks in a single write
- ~4KB entry limit is a readability constraint, not a technical one. On local filesystems, O_APPEND is atomic at any reasonable size due to kernel-level inode locking. PIPE_BUF (4KB Linux, 512 bytes macOS) only applies to pipes/FIFOs, not regular files.
- Per-iteration NDJSON trace files have no conflict risk (one file per phase)

### NOTES_INS_5: Verification independence
The verification agent verifies the *result*, not the *process*. It does not initially read implementation diffs. It reads the codebase as it stands, runs checks, and independently confirms acceptance criteria. If it needs to dig deeper later, it can read diffs, but never as a starting point. This prevents rubber-stamping.

### NOTES_INS_6: Blockers are critical events
Every blocker represents loss of progress and requires human investigation. Blockers must be documented across ALL four artifact types: trace (full detail), progress (BLOCKED status), emergent (what human needs to resolve), learnings (diagnostic context). "The quality of blocker documentation determines whether the human can help." — user

### NOTES_INS_7: Self-improvement is load-bearing
As models improve, skills like plet go out of date. plet needs the ability to improve itself. Two levels: micro (session-to-session via CLAUDE.md — agent notices something, offers to write it down) and macro (Future Consideration #11 — plet analyzing runtime artifacts to improve its own PRD). Both are human-gated. Without them, instructions calcify as the project evolves.

### NOTES_INS_8: When in doubt, add the dependency
Missing dependencies are dangerous (agent wastes a cycle, must self-correct). False dependencies are harmless (only reduce parallelism slightly). Always err on the side of adding a dependency.

### NOTES_INS_9: No metrics that reward lousy verification
First-pass verification rate sounds useful but incentivizes rubber-stamping. Never use metrics that reward the verification agent for passing easily.

### NOTES_INS_10: Tooling beats prose for enforcement — the plet_state.py insight

"Ship enforcement tooling alongside the instructions, in the same package." — emergent principle confirmed by SPARK case study.

State schema drift was the most persistent issue across LOGA and LIBT (5 different schemas in 5 iterations, both runs). Prose rules ("match this schema exactly") failed repeatedly. plet_state.py — a Python tool shipped inside the skill via `${CLAUDE_SKILL_DIR}/scripts/` — solved it completely. SPARK: zero schema drift across 23 iterations.

Meanwhile, learnings/emergent capture (enforced only via prose rule CASE_LOGA_R01_REC_7) regressed from LIBT's 2.2/iter to SPARK's 0.09/iter. Same agents, same run, different enforcement mechanism, dramatically different compliance.

**The deeper insight:** This validates a lesson from the RIDL/Ridler.app experience. In RIDL, the harness (code) and the loop (agent skills) were separate projects with separate implementation methodologies — developing both in parallel was hard, and keeping them consistent was harder. In plet, enforcement tools (plet_state.py) are bundled *inside* the skill itself. Same package, same version, same deployment. The agent calls a tool that guarantees correctness rather than interpreting prose instructions about what "correct" looks like.

**The fundamental limitation:** Skills are prompt-interpreted every invocation. Each time, the model re-reads instructions and makes fresh decisions about how to comply. Over 23 iterations, that's 23 independent interpretations of the same prose — and they drift. Code executes the same way every time. This means skills are fundamentally unsuited to tasks requiring regularity and consistency when invoked repeatedly in a loop. RIDL/Ridler.app had this right structurally — a code harness for the deterministic parts, agent skills for the judgment parts — even though the two-project split made development painful. plet collapsed them into one package for convenience but moved enforcement from code to prose. plet_state.py was the first step back toward code enforcement *within* the skill package.

**The design principle:** Skills for judgment and adaptation (where non-determinism is a feature). Code for format compliance, schema enforcement, artifact generation, and state management (where non-determinism is a bug). Ship the code inside the skill so they version together.

**Implication:** Any plet rule that agents consistently violate should be a candidate for tooling enforcement, not stronger prose. The pattern: (1) define the rule in prose, (2) if agents drift, build a tool that makes compliance automatic, (3) ship the tool inside the skill.

### NOTES_INS_11: Handoffs vs decisions — lifecycle transition ownership

State transitions in a multi-agent system fall into two categories, and confusing them causes bugs:

**Handoffs** — "I'm done, next step please." Owned by the sender. The agent that just finished signals completion by writing a state change. Example: the implement subagent sets lifecycle → `verifying` to signal "my work is committed, spawn verify." If it crashes, lifecycle stays `implementing` — clean signal that work didn't complete.

**Decisions** — "What happens next based on multiple inputs." Owned by the coordinator. The orchestrator evaluates verdict + merge success + retry policy to choose the next state. Example: after verify, the orchestrator sets lifecycle → `complete` (after merge), `queued` (retry), or `blocked` (exhausted). No single subagent has all the inputs needed for this decision.

**Why this matters:** If a subagent makes a decision it shouldn't (verify agent sets `complete` before merge), the state lies when merge fails. If the coordinator makes a handoff it shouldn't (orchestrator sets `verifying` instead of letting the implement agent signal), there's a gap where completion status is ambiguous.

**Enforcement:** Gate scripts enforce the model. Post-implement gate FAILs if lifecycle isn't `verifying` (handoff didn't happen). Post-verify gate FAILs if lifecycle changed from `verifying` (decision was made by wrong owner). Self-correction loops catch violations before the subagent exits.

This principle applies beyond plet — any system where multiple agents modify shared state needs clear ownership of each transition.

### NOTES_INS_12: Worktree state invariants — sole writer rule

During an iteration, per-iteration state files exist in two copies: the global copy (`global_plet_dir`, on the workstream branch) and the worktree copy (`worktree_plet_dir`, on the iteration branch). The worktree copy is authoritative during the iteration. The global copy is stale.

**The sole writer rule (SF_26):** The orchestrator writes ZERO per-iteration state during the iteration. The subagent is the sole writer to the worktree. The orchestrator writes final lifecycle to the global copy only after the iteration is done (verdict handoff, SF_27). This eliminates merge conflicts entirely — no concurrent writes to the same file.

**Why this matters:** LOGA Run 3 exposed a merge conflict when the orchestrator wrote `lifecycle → implementing` to the global copy (reservation) while the subagent wrote to the worktree copy. On merge-squash, both copies were modified → conflict. Eliminating the reservation write and making the subagent the sole writer resolved it.

**Symmetric pattern:** Both implement and verify subagents set their lifecycle as their first action (`implementing`/`verifying`). Both are sole writers to the worktree during their phase. The orchestrator only touches the global copy after the verdict.

See specs/NOTES.md § Worktree state file invariants for the full 6-invariant list and implementation details. See NOTES.md § Plet Directory Variables for the naming taxonomy.

### NOTES_INS_13: Defense in depth for load-bearing checks

Checking the same critical invariant in multiple places is acceptable and intentional — not redundancy. Each layer catches failures at a different point in the pipeline with different recovery options.

Example — `verifyVerdict` after verify:
- **Layer 1 (gate):** Post-verify gate FAILs if null. Subagent is still alive and can self-correct. Best outcome — problem fixed before anyone notices.
- **Layer 2 (orchestrator):** Defensive check after verify returns. Subagent is gone. Can only block the iteration and log. Worst-case fallback.

The layers are ordered by recovery power: earliest check has the most options (self-correct), latest check has the fewest (block and report). This pattern applies to lifecycle ownership, audit tags, state validity, and any invariant where violation means data loss or incorrect execution.

This is distinct from accidental duplication (same check, same point, no additional recovery). Defense in depth is deliberate overlap across pipeline stages. Accidental duplication is waste.

### NOTES_INS_14: Meaningful red vs meaningless red

A test that fails because the thing it's testing doesn't exist yet is **meaningless red** — it proves nothing about the test's ability to catch bad behavior. Whether it's a missing script (`FileNotFoundError`), a missing class (`ImportError`), or a missing function (`AttributeError`), the test would fail identically regardless of what it asserts. Meaningless red gives false confidence that the red/green discipline was followed.

**Meaningful red** requires the unit under test to exist and execute, but produce the wrong result. The stub accepts inputs, returns output, runs without crashing — but the output is wrong (empty list, hardcoded dummy, zero value, stub response). The test fails because the *behavior* is wrong, which proves the test would catch a real regression.

This applies at every level:
- **Scripts:** stub the script with dispatch + command functions returning dummy values before writing subprocess tests.
- **Functions:** stub the function with a signature that returns a default/zero value before writing unit tests.
- **Classes:** stub the class with method signatures that return dummies before writing tests.
- **APIs:** stub the endpoint with a handler that returns a placeholder response before writing integration tests.

The principle is the same everywhere: the test must fail because the answer is wrong, not because the infrastructure is missing. Without this, red/green is theater.

### NOTES_INS_15: Use subagents to explore during design
During the execute.md build, we used subagents to research ridler2's trace mechanism, check Claude Code flags, test tool capabilities, and verify file paths. Subagents are cheap and fast for exploratory validation — use proactively during brainstorming, not just for delegated work.

### NOTES_INS_16: NOTES.md as institutional memory
The notes file is the connective tissue between CLAUDE.md (project config) and the PRD (spec). It captures the "why" so the PRD can stay clean.

### NOTES_INS_17: How Claude memory works
Claude Code has three layers of memory:

1. **Within a conversation** — full context of everything discussed in the current session. Subject to context window limits (older messages get compressed as the window fills).
2. **Persistent memory directory** — a per-project directory on disk (`~/.claude-*/projects/*/memory/`) that survives across sessions. Not cleared automatically. Files persist until explicitly deleted or edited. A special `MEMORY.md` file (first 200 lines) is auto-loaded into every conversation's context; other files in the directory must be explicitly read.
3. **Project instructions** — `CLAUDE.md` and `NOTES.md` are loaded every session. These act as version-controlled institutional memory shared across all users/sessions.

**What gets saved to persistent memory:** stable patterns confirmed across multiple interactions, user preferences, architectural decisions, solutions to recurring problems, and anything the user explicitly asks to remember. Session-specific or speculative information is not saved.

**Subagent access:** subagents can read/write the memory directory (same filesystem), but `MEMORY.md` is not auto-injected into their context. They do get `CLAUDE.md`. The main conversation is the gatekeeper for memory writes.

**Key implication for plet:** persistent memory is per-machine, not per-repo. For shared institutional memory, use checked-in files (NOTES.md, CLAUDE.md) rather than the memory directory.

### NOTES_INS_18: Subagents load CLAUDE.md but don't follow it reliably

Claude Code auto-loads project CLAUDE.md into subagent (Agent tool) context. So rules written in CLAUDE.md are technically *visible* to subagents. But visibility is not compliance — subagents operate under task pressure with a narrower focus, and they routinely skip rules that aren't reinforced in the prompt that launched them.

**What we learned (2026-04-05):** The red/green discipline and scripts/CLAUDE.md reading requirements existed in root CLAUDE.md, but subagents launched to work on plet scripts weren't following them. The rules were in context (auto-loaded) but not enforced. The gap: the *parent agent* writing the prompt didn't include these directives explicitly.

**The fix has two layers:**
1. **Belt (CLAUDE.md callout):** Added "Script Work — Required Reading" section near the top of root CLAUDE.md with explicit "This also applies to subagents — if you launch an agent to work on plet scripts, include this directive in the prompt."
2. **Suspenders (parent agent responsibility):** The parent agent must include script-specific directives in the prompt when spawning subagents for script work. CLAUDE.md can remind the parent to do this, but it can't force the subagent to comply — only the prompt can.

**General principle:** For subagent compliance, CLAUDE.md is necessary but not sufficient. Critical rules must appear in both CLAUDE.md (so the parent agent knows the rule) AND the subagent's launch prompt (so the subagent actually follows it). Auto-memory (`MEMORY.md`) is NOT injected into subagent context.

---

## NOTES_DES: Key Design Decisions

### NOTES_DES_1: Architecture & Routing

#### Subagent must NOT squash — orchestrator owns merge-squash (2026-04-02)

Removed squash instructions from phase-implement.md and phase-verify.md. Subagents commit incrementally (wip commits for crash recovery); the orchestrator's merge-squash creates the single clean commit per phase on the workstream branch.

**Problem:** When subagents squashed their own wip commits before the orchestrator's merge-squash, the branch diverged — the squash rewrote history, creating a forked graph visible in `git log --graph`. The orchestrator's subsequent merge-squash couldn't cleanly fast-forward.

**Fix:** phase-implement.md "Tag and Squash" → "Tag" only. phase-verify.md same. Added explicit "Do NOT squash — orchestrator handles it." This keeps one owner for the squash operation.

#### Orchestrator commits state.json before worktree creation (2026-04-02)

After `start-session` increments `loopSessionCount`, the orchestrator now runs `git add -A && git commit` before creating worktrees. Previously, worktrees were created from the workstream tip which had a stale `loopSessionCount`. The subagent in the worktree would see the old value, and LOGA Run 6 showed a subagent "fixing" it — modifying state.json in the worktree (violating SF_28: orchestrator-owned).

#### Dependency promotion in orchestrator (2026-04-01)

**Bug:** After ITR_001 completed in LOGA Run 5, ITR_002 stayed `ineligible` instead of promoting to `queued`. The orchestrator called `schedule.py eligible` which only returns `queued` iterations with all deps complete. But nothing ever changed `ineligible` → `queued` when deps were satisfied.

**Fix:** Added `_promote_eligible()` to orchestrator — after each iteration completes, scans all `ineligible` iterations and promotes to `queued` when all dependencies are `complete`. Called before each `eligible()` check.

#### State.json merge=ours for worktree conflicts (2026-04-01)

**Bug:** LOGA Run 5 merge-squash failed with conflict markers in state.json. Both workstream and worktree had modified state.json — worktree had a stale copy from creation time, workstream was updated by the orchestrator during the iteration.

**Fix:** `.gitattributes` entry `plet/state.json merge=ours` — workstream version always wins on merge. Safe because state.json is orchestrator-owned (SF_28).

#### Permission mode auto-detection in plet_invoke.py (2026-04-01)

`plet_invoke.py` always passed `--permission-mode auto` regardless of project settings. Fixed to auto-detect from `.claude/settings.json` — checks for `bypassPermissions: true` or `defaultMode` and passes the correct flag.

#### Compact progress entries from dispatch auto-logger (2026-04-01)

Progress entries from the auto-logger previously dumped the full 94KB prompt into progress.md (LOGA Run 5: 12,975 lines for 3 iterations). Fixed to show invocation metadata + trace reference only — one-liner entries.

Also removed the `**Files changed:**` field entirely — git history is the source of truth for file changes.

#### Bootstrap script — bootstrap.py (2026-04-01)

New script for project setup automation. `setup` command: creates .plet/ dir, .gitignore (3 entries), .gitattributes (merge driver + merge=ours for state.json), git config for merge driver, CLAUDE.md stub, .claude/settings.json (merge allow entries), permissions check. `check` command: read-only verification of all bootstrap items + empirical sandbox detection. 46 tests.

Resolves the long-standing issue of agents spending 8+ minutes searching for scripts (LOGA Run 4). Bootstrap ensures the environment is configured before plan session begins.

#### Env var injection for subagent script discovery (2026-04-01)

`plet_invoke.py` injects 8 `PLET_*` env vars + `CLAUDE_*` pass-through into subagent subprocess and prompt header. Subagents use `$PLET_SCRIPTS_DIR` for all script calls — immediate discovery, no searching.

Env vars injected: `PLET_SCRIPTS_DIR`, `PLET_DIR`, `PLET_PROJECT_DIR`, `PLET_WORKTREE_BASE`, `PLET_ITER_ID`, `PLET_PHASE`, `PLET_ATTEMPT`, plus `CLAUDE_*` pass-through.

#### Plan branch enforcement — prose fails, enforcement needed (2026-04-01)

Runs 3, 4, and 5 all committed plan output directly to main despite SKILL.md Step 2 saying "create plan branch." Run 6 (v0.4.2) was the first run where the plan branch was created correctly. Unclear whether v0.4.2 changes fixed this or it was coincidental. Worth monitoring — if it fails again, needs script enforcement, not prose.

#### LOGA Run 6 — first fully successful scripted run (2026-04-02)

13/13 iterations completed in one continuous loop session. bypassPermissions mode, plan branch created correctly. 100% verify first-pass rate (same as Run 5). Per-iteration average ~18 min. One observed issue: subagent modified state.json in worktree (loopSessionCount), fixed post-run by committing state.json before worktree creation.

This validates the entire lifecycle extraction (seq 39-41), dependency promotion, env var injection, and all Run 4/5 fixes. Most successful run since Run 1 (prose baseline).

#### Ruff linting + pytest/coverage infrastructure (2026-04-02)

Added ruff with 9 rule sets (E, F, W, I, N, UP, B, SIM, C90). McCabe complexity threshold at 15 — started at 30 and progressively lowered. All violations fixed directly (no per-file ignores).

Added pytest + pytest-cov infrastructure. 85% coverage (was unmeasured). 2189 tests across 31 files (was 1786 across 23). All test files wrapped in `def main()` for pytest discovery. `test_all.py` auto-formats with `ruff format` before running tests. `uv.lock` committed to pin dev tooling versions.

#### parse_command() and emit_error() — shared CLI utilities (2026-04-02)

`parse_command()` in util_cli replaces the 6-step arg parsing boilerplate (parse raw, check help, check version, get plet_dir, extract kwargs, set up output). Returns "help" | None | (plet_dir, kwargs, output_json, pretty, fields, dry_run). Adopted in 17+ command functions.

`emit_error()` in util_cli provides shared JSON/text error output. Replaced 3 duplicate `_emit_error` helpers across scripts.

#### util_io as single source of truth for all file paths (2026-03-29)

Every plet file path is derived from `util_io` functions. No script constructs paths manually via `os.path.join`. Functions added during this session:
- `trace_dir_path(plet_dir)` → `{plet_dir}/trace/`
- `events_path(plet_dir, iter_id, phase, attempt)` → `{plet_dir}/trace/{id}-{phase}-{attempt}-events.ndjson`
- `transcript_path(plet_dir, iter_id, phase, attempt)` → `{plet_dir}/trace/{id}-{phase}-{attempt}-transcript.ndjson`

Previously existed: `state_json_path`, `state_dir_path`, `iter_state_path`, `requirements_path`, `iterations_path`, `progress_path`, `learnings_path`, `emergent_path`.

Replaced `trace_path` (old single-file convention) with `trace_dir_path` (per-iteration directory). Replaced `load_trace_ndjson` with `load_events_ndjson(plet_dir, iter_id, phase, attempt)`.

Custom path functions removed from scripts: `plet_invoke.py transcript_path()` (moved to util_io). `plet_gate_phase.py` manual trace path construction replaced with `events_path()`.

#### Universal invocation logging — design decisions (2026-03-29)

**Decision:** Every script invocation logs to both trace event and progress entry. Implemented in `util_cli.dispatch()` after each command completes.

**No-recursion exclusions:** Write commands on logging scripts don't log (to avoid recursion):
- `plet_entries.py`: add-progress, add-learning, add-emergent (write path)
- `plet_trace.py`: append-event (write path)
Read commands on those scripts (check, validate, query) DO log.

**`--no-log` flag:** Test-only flag. Stripped by dispatch() before routing. Cascades to child processes via `PLET_NO_LOG=1` env var. Not in help text.

**Direct imports, not subprocess:** Logging writes trace events and progress entries via `util_io.atomic_append` and `util_id.generate_plet_id` directly — no subprocess calls. Zero overhead, no cascading performance problem.

**Self-initializing artifact files:** `plet_entries.py` add-* commands auto-create progress.md/learnings.md/emergent.md if they don't exist (was an error). Required because logging may happen before bootstrap creates the files.

**Completed:**
- plet_state.py: retrofitted to plet_dir + --iter-id. All 4 commands use `resolve_state_path()` (composes get_plet_dir + parse_kwargs + validate + iter_state_path). Gate script updated to pass new interface.
- plet_trace.py: retrofitted to plet_dir + --iter-id + --phase + --attempt. All 3 commands derive events file via util_io. `derive_events_path()` thin wrapper auto-creates trace/ dir. Accepts "proj" as iter-id. Gate + invoke updated.
- plet_entries.py: auto-creates progress.md/learnings.md/emergent.md if missing (was error). Required for universal logging.
- All scripts: manual os.path.join replaced with util_io functions (ENT, FPR, GPH, INV, TRC).

**Remaining work:**
- Universal logging: infrastructure in util_cli (dispatch + _log_script_invocation), needs wiring + testing
- Test scripts: need util_io path functions (currently use manual os.path.join)
- Specs: need updating for STA/TRC retrofit, ENT auto-create, util_io new functions

#### Post-gate progress logging → universal logging (2026-03-29)

- **Started as:** gate scripts log results to progress.md (custom code in plet_gate_phase.py)
- **Evolved to:** universal convention — every script logs via dispatch()
- **Principle:** observability as infrastructure, not per-script boilerplate

#### Reference file rewrite — judgment vs compliance analysis (2026-03-28)

PLAN_RWc: rewriting phase-implement.md and phase-verify.md to delegate compliance to scripts while keeping judgment as prose. The principle: **agents call scripts for format/schema compliance, read prose for judgment calls.**

**phase-implement.md section analysis:**

| Section | Type | Action |
|---------|------|--------|
| Before You Start | Judgment | Keep prose — context reading, understanding the task |
| Red/Green Test Discipline | Judgment | Keep prose — this IS the agent's job |
| State Updates During Work | Compliance | Replace with `plet_state.py` calls |
| Runtime Artifact Writes | Compliance | Replace with `plet_entries.py` calls |
| Trace Writing | Compliance | Replace with `plet_trace.py` calls |
| Completing the Phase | Mixed | Keep judgment, add `plet_gate_phase.py post` call |
| Blocker Protocol | Judgment + Compliance | Keep judgment, script-ify artifact writes |
| Failed Attempt Protocol | Mixed | Keep judgment |
| Missing Dependency Self-Correction | Judgment | Keep prose |
| Retry Awareness | Context | Keep prose |
| Criteria Skip Rules | Compliance | Replace with `plet_state.py` calls |
| Atomic Write Rules | **DELETE** | Scripts handle atomicity |
| Summary Checklist | Update | Add gate script call |

**phase-verify.md follows the same pattern** plus verify-specific judgment sections (Independent Verification, Anti-Slop Bias, Convergence Signal, Verification Report — all judgment, all stay as prose).

**formats.md decision:** Keep condensed in prompt. Agents call scripts to write entries but still read existing entries (learnings, progress). A brief structural overview helps comprehension without the full 421-line format spec.

**state-schema.md decision:** Keep condensed in prompt. Agents call scripts for state updates but need to understand fields conceptually (lifecycle values, criteria statuses, what fields mean). Don't need the full JSON schema.

**Net effect:** phase-implement.md and phase-verify.md get thinner (compliance sections become script call references). formats.md and state-schema.md get condensed versions for the prompt (agent understanding, not agent writing).

#### Phase terminology unification (2026-03-21)

Comprehensive rename to unify phase terminology across the entire repo.

**Changes:**
1. `impl` → `implement` as the formal phase name. All four phases are now real English verbs: plan, implement, verify, refine.
2. `execute.md` → `phase-implement.md` (reference file — every reference file now matches its phase: plan.md, phase-implement.md, phase-verify.md, refine.md).
3. `EX_` → `IMP_` for PRD requirement IDs (27 IDs). EX prefix freed for EXTRACTABLE.md exclusive use.
4. `UNV_IMP_1` → `UNV_IPR_1` in conventions.md (avoids IMP_ collision).
5. `attempts.impl` → `attempts.implement` in state schema and scripts.
6. Prose "Execute" → "Implement" where it referred to the phase (workflow descriptions, agent names, section headings).

**Preserved (unchanged):**
- `implementation` / `verification` — criterion two-state model field names (noun form)
- `implementing` / `verifying` — lifecycle/activity enum values (gerund form)
- `i1`/`v1` — plet ID segments (already abbreviated)
- `EX` prefix in EXTRACTABLE.md (different meaning)
- Historical NOTES.md entries describing old names
- Case studies and FEEDBACK_FOO.md (historical artifacts from actual runs)
- Generic English uses of "execute" ("execute the user's decisions", "Code executes the same way")

**Rationale:** Three grammatical forms serve three different roles:
- **Verb** (phase name): implement, verify — "this is what you do"
- **Noun** (criterion record): implementation, verification — "the record of what was done"
- **Gerund** (lifecycle state): implementing, verifying — "what is happening now"

Each form is unambiguous in context. `impl` was the only abbreviation among four phase names — the others (plan, verify, refine) were already full words. `execute.md` was the only reference file that didn't match its phase name.

**Scope:** 25+ files across scripts, tests, specs, reference files, PRD, PLET.md, NOTES.md, README.md, SKILL.md, guide/. 533 tests, 0 failures.

#### Artifact format enforcement — A/B test (FOO_12 vs FOO_17)
- **FOO_17 (progress.md):** stronger prose — "match exactly" language + inline templates in execute.md/phase-verify.md
- **FOO_12 (state files):** tooling — Python helper script shipped via `${CLAUDE_SKILL_DIR}/scripts/` that validates/writes state files. Agents call the tool instead of writing JSON freehand.
- Comparing the two approaches in the next case study run will tell us whether tooling or prose is more effective at preventing drift. (2026-03-12)
- `${CLAUDE_SKILL_DIR}` resolves to the skill directory at runtime, giving agents a known path to bundled tools. python3 is always available; jq requires external install.
- Agents drifted from the defined format in both LOGA and LIBT — div markers, fenced code blocks, plain headers all appeared in one run
- Fix: inline template + "match exactly" language in execute.md and phase-verify.md. formats.md remains source of truth.
- **Next step if agents still drift:** validator tool (grep for div markers, check required fields) or generator tool (shell helper that outputs correctly-formatted entries from args). jq-style enforcement is also an option for state files (FOO_12). Decided to try the lighter-weight approach first. (2026-03-12)

#### Unified entry format — KV metadata + Content block (2026-03-16)

All three runtime artifact entries (progress, learning, emergent) now share the same structural pattern: KV metadata lines on top, then a `**Content:**` marker, then freeform content until the end fence. This replaces the previous per-type variations (progress had Summary/Files sections, learning had bare content, emergent had content + Outcome).

- **Files changed** (progress) and **Outcome** (emergent) stay in the KV section above the content marker
- CLI flags unified: `--summary`/`--summary-file` → `--content`/`--content-file` across all three add-* commands
- Fencing safety: content must not contain fence patterns (`<div id="plet-` or `<div id="END-plet-`). Script rejects with error if detected.
- `**Content:**` marker makes the KV→freeform boundary explicit and machine-parseable for GUI tools
- Per RT_10 (additive only), adding the Content marker is additive. Acceptable for pre-v1.

See `specs/NOTES.md` for full cascading changes list.

#### Spec artifacts must survive plan → loop → refine (FOO_16)
- LIBT lost requirements.md and iterations.md — project unresumable
- Two-layer fix: (1) plan.md Step 8.4 checkpoint verifies files exist on disk and are committed, (2) execute.md pre-flight blocks if spec artifacts are missing
- Root cause ambiguous (never written vs lost during loop) — both layers needed (2026-03-12)

#### Post-merge file verification (FOO_18)
- LIBT lost a test file during parallel branch rebase+merge — required manual restoration
- Added post-merge verification step in phase-verify.md: run full test suite + compare file list from iteration branch against workstream after ff-merge
- Catches silent file drops from both merge and rebase conflict resolution (2026-03-12)

#### Real timestamps via `date -u`, never fabricate (FOO_19)
- LIBT state.json had synthetic round-number timestamps (00:01:00Z, 21:00:00Z) — useless for timing analysis
- SKILL.md loop start, loop end, and refine start now require `date -u +%Y-%m-%dT%H:%M:%SZ`
- Explicit "never fabricate or round timestamps" language added (2026-03-12)

#### Skills can ship executable tools via `${CLAUDE_SKILL_DIR}`
- `${CLAUDE_SKILL_DIR}` resolves to the skill's directory at runtime — agents can call bundled scripts by absolute path
- plet_state.py is the first tool shipped this way
- SKILL.md frontmatter `allowed-tools: "Bash(python3 *)"` grants permission in target projects
- Target projects should also set `bypassPermissions` in `.claude/settings.local.json` for full autonomous operation (FOO_22) (2026-03-12)

#### PRD traceability tags are permanent, not build scaffolding
- Parenthetical PRD references like `(IMP_17)`, `(VF_9)` in skill files are kept permanently — not stripped before release
- Originally treated as build scaffolding with "will be stripped" notes in every file
- FOO_20 made them semantic (e.g., "per PL_DX_2" in exception text) — stripping would break cross-references
- Removed all 7 "Build note" blocks from SKILL.md and reference files (2026-03-12)

#### Subprocess invocations for subagents, not native Agent tool (2026-03-20)

Subagents run as subprocess invocations (`claude -p --output-format stream-json`), not Claude Code's native Agent tool. This is an architectural choice driven by traceability:

- **Subprocess:** produces streaming JSONL output that `plet_invoke.py` captures to the transcript file in real time. Every message, tool use, and tool result is recorded. This is the raw I/O that a GUI merges with semantic events for full fidelity debugging.
- **Native Agent tool:** runs inside Claude Code with no reliable way to capture raw I/O. Finding and copying log files from the config dir is an implementation detail that may change across versions and is non-portable across harnesses (Ridler.app, CLI, etc.).
- **Evidence:** ridler.log from a real RIDL run (2327 lines of streaming JSONL) demonstrates the output richness that subprocess invocations provide. Case studies showed trace reliability only once subprocess patterns were established.
- **Consequence:** new script `plet_invoke.py` handles prompt assembly (via `plet_inject_prompt.py`) + subprocess launch + transcript capture. This replaces the vague "orchestrator captures transcript" responsibility with deterministic code.
- **Future:** native subagents are deferred (TRC_FUT_5). They offer UI benefits but lack the traceability guarantee. If Claude Code exposes a transcript API, revisit.

#### Single skill with reference files
- One entry point (`/plet`) with state-driven routing
- Phase-specific instructions in `references/` (plan.md, phase-implement.md, phase-verify.md, refine.md)
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

Implement and verify are internal phases of one autonomous loop — the user shouldn't need to invoke them separately. `/plet loop` forces entry into the implement→verify loop. The internal phases still exist as concepts in reference files, but are not user-facing subcommands.

#### Routing: `ineligible` excluded from LOOP check

`ineligible` iterations are waiting on dependencies and aren't actionable work. Including them caused a dead-end when all remaining iterations were `blocked` + `ineligible` — routed to LOOP instead of REFINE where the human could resolve the blocker. OLP_4 now only checks for `queued`, `implementing`, or `verifying`.

#### PT_ → PL_ rename

All "plan-template" sections (PT_DX, PT_CT, PT_TV, PT_SM) renamed to PL_ prefixes because they describe plan session *behavior*, not prompt/reference file *contents*. PT (3.8) stays as the 6 requirements about the physical reference files.

#### PLET.md creation and CLAUDE.md updates (2026-03-09)

Created PLET.md as the portable plet-specific instruction file (vs CLAUDE.md which is project-specific). Key decisions:
- **PLET.md content:** What is plet?, Core Workflow, Key Concepts glossary, Artifact Taxonomy (full 7-category taxonomy with target project directory tree), Commit Conventions (target projects), plus generalized copies of Decision Discipline, Consistency Passes, and Common Misspellings from CLAUDE.md
- **Copy, don't move:** Sections shared between CLAUDE.md and PLET.md are copied and generalized, not moved. Overlap is expected and acceptable — each file serves a different audience.
- **Critical Requirements & Invariants:** Placeholder section added to PLET.md for load-bearing rules. To be populated.
- **CLAUDE.md updates:** Added "plex" to misspellings table. Added Mandatory Acknowledgment rule — agent must explicitly inform the user every time it reads/re-reads CLAUDE.md or PLET.md (silent reads not acceptable).
- **Mandatory acknowledgment reinforcement (2026-03-09):** Three-layer approach to ensure agent always acknowledges reading instruction files:
  1. **PLET.md Critical Requirements & Invariants** — added acknowledgment rule as the first invariant (portable to all plet repos)
  2. **CLAUDE.md Session Bootstrap** — instructs agent to seed auto-memory with the acknowledgment rule on first interaction; references Required Reading files generically so it stays correct as the list grows
  3. **Auto-memory** — seeded with the rule so it's in context from the first message, before any files are read
  - All three layers reference Required Reading files generically (not hardcoded names) so new files added to Required Reading are automatically covered
  - Rationale: agent was failing to prominently acknowledge reads despite the existing CLAUDE.md rule. Auto-memory provides the earliest possible reinforcement; PLET.md makes it portable; CLAUDE.md Session Bootstrap ensures auto-memory gets created in any repo.

### NOTES_DES_2: State & Data

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
    "MS_1": ["ITR_001", "ITR_002"],
    "MS_2": ["ITR_003", "ITR_004"]
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

### NOTES_DES_3: Execution

#### Git branch strategy (CASE_LOGA_R01_REC_5, CASE_LOGA_R01_REC_6)

All branches and tags are namespaced under `plet/{projectId}/`. Agents never commit to main.

**Branch and tag conventions:**

| Purpose | Pattern | Example |
|---------|---------|---------|
| Loop integration | `plet/{projectId}/loop{N}/workstream` | `plet/LOGA/loop1/workstream` |
| Iteration | `plet/{projectId}/loop{N}/{iteration_id}` | `plet/LOGA/loop1/ITR_001` |
| Audit tag | `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` | `plet/LOGA/loop1/audit/ITR_001/implement-1` |
| Refine | `plet/{projectId}/refine{N}/workstream` | `plet/LOGA/refine1/workstream` |
| Archive tag | `archive/plet/{projectId}/loop{N}/{path}` | `archive/plet/LOGA/loop1/workstream` |
| Subplet loop | `plet/{projectId}/subplet/{subId}/loop{N}/workstream` | `plet/LOGA/subplet/PRSR/loop1/workstream` |
| Subplet iteration | `plet/{projectId}/subplet/{subId}/loop{N}/{iteration_id}` | `plet/LOGA/subplet/PRSR/loop1/ITR_001` |

- `loop{N}` driven by `loopSessionCount` in state.json; `refine{N}` driven by `refineSessionCount`
- Iteration branches persist across implement and verify phases
- After iteration reaches `complete`, rebase onto the loop workstream and fast-forward merge
- Linear history is strongly preferred
- Agents commit incrementally during each phase for crash recovery
- At end of each phase, squash into a single commit
- Commit convention: `plet: [{iteration_id}] {phase}-{attempt} - {title}`
- If an iteration cycles (implement-1, verify-1, implement-2, verify-2), each phase is a separate squashed commit

#### Project ID (CASE_LOGA_R01_REC_6)

Short project identifier defined during plan session (Step 2, alongside project name), stored in `state.json` as `projectId`. Used in branch names, tag names, and potentially state file paths (e.g., `plet/LOGA/workstream`). Agent suggests 2-3 options using the numbers-letters style; user picks or overrides.

**Format:** `[A-Z][A-Z0-9]{2,5}` — 3-6 characters, starts with a letter, uppercase alphanumeric only. User-chosen during plan session.

**Rationale for 3-char minimum:** Minimizes collisions with requirement ID prefixes. Most prefixes are 2-char (`FR`, `NF`, `DX`, `EM`, `ID`, etc.), so 3+ chars avoids the common case. Some requirement prefixes can be 3-char (e.g., a hypothetical `SEC_2` for a security feature area), so collisions are still possible but rare. **Hard rule:** requirement prefixes must NEVER collide with the project ID. Since the project ID is usually defined first (during plan session), requirement prefixes are chosen to avoid it.

**Examples:** `LOGA` (log analyzer), `AUTH` (auth service), `UUGEN` (UUID generator).

**Subplet branch convention (hypothetical/future):** Subplets use a literal `subplet/` path segment: `plet/LOGA/subplet/PRSR/loop/ITR_001`. Self-documenting — the `subplet/` segment makes the hierarchy obvious. The common case (no subplets) stays clean: `plet/LOGA/loop/ITR_001`. Length is manageable since subplets are already the complex case, and sub-sub-plets are off the table so it never gets deeper.

**Rejected subplet ID alternatives:**
- Underscore-joined flat ID (`LOGA_PRSR`) — consistent format but loses visual hierarchy, overloads underscore delimiter already used in requirement IDs
- Slash without marker (`LOGA/PRSR`) — inconsistent shape between parent (1 segment) and subplet (2 segments), project ID becomes a path instead of a string
- Parent sentinel (`LOGA/ROOT`) — consistent shape but verbose for the common no-subplet case
- Separate prefix (`subplet/LOGA/PRSR/...`) — splits namespace, `plet/*` no longer captures everything

#### Parallelization
- Default: skill spawns subagents for independent iterations
- Dependency-graph-driven — iterations form a DAG, not a strict sequence
- External tools (GUI, other sessions) can also drive execution by reading the state file
- The orchestrator re-evaluates eligible work after each iteration completes

#### Missing dependency self-correction

If an agent discovers a missing dependency during execution (prerequisite work doesn't exist), it fixes the DAG in place — adds the dependency to state.json and per-iteration state, sets lifecycle to `ineligible`, documents across all four runtime artifacts, and returns. Not a blocker — the loop continues and the iteration auto-queues when the missing dep completes. Does not count against retry limit. Dependency graph validation step added to plan session iteration review.

#### Test suite execution strategy (IMP_4)

On large projects, full test suites can take 4-5 minutes. With 5 acceptance criteria, 7 full runs compounds to ~35 minutes. Adopted tiered approach: agent times the first full run and decides strategy. ~30s is a recommended threshold but agent uses discretion. Fast suite = full suite every green step. Slow suite = most relevant subset using the project's test grouping mechanisms. Full suite only at phase end as a final gate.

**Rejected alternatives:**
- Full suite only at phase end — fastest but regressions caught too late
- Full suite at checkpoints (every N criteria) — interesting but adds complexity
- Pure agent discretion with no guidance — too unstructured for v1

#### `cleanupTagsAutomatically` — audit tag lifecycle (R_4, IMP_17) — DECIDED (2026-03-10)

Always create audit tags before squash — no opt-in flag, it just happens. Log tag name and commit hash in progress.md at creation. `cleanupTagsAutomatically` (default false) controls whether to delete the tag after squash; if cleaning up, log the deletion with the commit hash in progress.md too. Tag naming: `plet/{projectId}/loop{N}/audit/{iteration_id}/{phase}-{attempt}` — hierarchical `/` separators allow GUI tools to filter at multiple levels. Config: global default in `state.json` (inherited at initialization), per-iteration override. Rejected: `tagBeforeSquash` (wrong default — tagging should be unconditional, the question is cleanup).

#### Context window management for subagent reads

Runtime artifacts grow unbounded, so subagents can't naively read everything. Tiered approach per artifact:
- **requirements.md, emergent.md** — orchestrator injects relevant sections based on the iteration's requirement IDs
- **progress.md** — skip if large, read last ~10 entries if medium-sized. State files already cover "what's done"
- **learnings.md** — skip if large; orchestrator filters by relevance (matching files/modules, requirement IDs, category tags) plus project-wide entries
- **CLAUDE.md, README.md, iteration definition, state file** — always read in full (small, essential)

#### Trace capture: raw I/O + semantic events

Subagents don't self-log full I/O — that's impractical and wasteful of context. Trace is split into two files per phase: (1) raw I/O transcript (`{id}-{phase}-{attempt}-transcript.ndjson`) captured automatically by the orchestrator from Claude Code's `--output-format stream-json` output, and (2) semantic events (`{id}-{phase}-{attempt}-events.ndjson`) written by the subagent for decisions, criterion updates, lifecycle changes, activity changes, and errors. Both have timestamps; a GUI merges by time. `-transcript` suffix chosen over `-raw`/`-stream`/`-io`/`-session` because it describes what the file contains rather than how it was captured.

### NOTES_DES_4: Verification

#### Verification reports in per-iteration state (VF_21–VF_24)

Each verification attempt appends a report to the `verificationReports` array (never overwritten). Reports have `vrp` plet IDs, a verdict, compact `criteriaResults` index, and two-level `relatedEntries` (report-level for iteration-spanning concerns, criterion-level for single-AC findings). `implementVerdict`/`verifyVerdict` fields at the iteration state top level (formerly `lastVerdict`). Written after artifact entries so plet IDs are available for `relatedEntries`.

#### Verification report `findings` field (VF_24)

Array of strings for observations beyond the summary or per-criterion one-liners. Can reference plet IDs inline as plain text. Intentionally overlaps with learnings — the report is a self-contained snapshot of one verification attempt, while learnings persist across iterations. Same insight, different lifespans and audiences. The overlap is a feature, not a bug.

#### Dual-source resolution for verification reports

The verification report is described in two places: state-schema.md (field-level schema, types, example JSON) and phase-verify.md (intent — what kind of information to capture and why). phase-verify.md avoids repeating field names and types, describing the report in terms of what to capture rather than how to structure it. Prevents drift — state-schema.md is the single source for structure.

#### Verdict enum and progress.md status semantics

Three verdict values: `passed` (all pass, iteration frozen), `rejected` (issues found, returning to implement), `blocked` (needs human input). Used `passed` instead of `complete` to avoid collision with the `complete` lifecycle value. Progress.md status reflects the *phase attempt* outcome, not the iteration outcome — a cycle-back is a `COMPLETE` phase attempt (the verify agent finished its work) with a parenthetical verdict: `COMPLETE (passed, frozen)`, `COMPLETE (rejected, cycle back)`, `BLOCKED`.

#### Retry exhaustion after `rejected` verdict

When the verify agent rejects and retry limits are exhausted (IMP_14), the orchestrator transitions to `lifecycle: "blocked"` and writes progress/emergent entries. The verify agent is unaware of retry policy — it always reports its verdict; the orchestrator decides. Chose `blocked` lifecycle over a new value like `exhausted` — the iteration genuinely needs human intervention.

#### Verification cycle-back writes red tests (VF_16)

On cycle-back (Path C — substantial issues), the verify agent writes failing tests that demonstrate each finding. The next implement agent inherits these as green-step targets — red/green handoff across the agent boundary. For non-test-expressible issues (wrong abstraction, coupling), the verify agent skips the red test and documents the rationale. The branch is left with intentionally failing tests — an explicit exception to the "all tests must pass" rule.

### NOTES_DES_5: Refine

#### Milestone assignment during refine (RFN_14, RFN_15)

Frozen milestones (all iterations `complete`) don't accept new iterations, except the most recent milestone which is never considered frozen ("complete for now") — without this exception, late-stage refinements would produce a series of single-iteration milestones. Any unfrozen milestone is fair game. Heuristics for new milestone: scope magnitude (3+), version significance, origin clustering, milestone size (6+), theme coherence. Agent states which heuristic; user overrides.

When all iterations are complete and new iterations are being added, explicitly ask the user whether to add to the most recent milestone or create a new one — don't silently default.

#### Blockers first in refine (RFN_8)

Blocked iterations are surfaced as Step 1 in the refine session, before emergent item triage. Blockers represent lost progress and are the highest priority for human attention.

**Rationale:** Blockers are stalled work — agents already spent cycles and hit a wall. Unblocking them gets value from that spent effort. Emergent items are informational — they can wait.

**Rejected alternative:** Emergent triage first (original draft ordering). User corrected: "blockers first. they are the priority."

#### No trace writing for refine phase

Refine is interactive in the main conversation, not a subagent. Decisions are captured in better places: NOTES.md for rationale, emergent.md outcomes for triage, requirements.md and iterations.md for actual changes.

**Rationale:** Trace files serve subagents — they capture decisions in contexts that are discarded. The refine session runs in the main conversation where the human is present. Writing trace would duplicate what's already in NOTES.md, emergent.md outcomes, and the artifacts themselves.

**Rejected alternative:** Writing semantic events to a refine-specific trace file. Adds overhead without value — no consumer needs it.

#### Explicit confirmation before re-queuing blocked iterations

After resolving a blocker, the agent must summarize the resolution conversation and ask "are you comfortable re-queuing this iteration?" with explicit A/B/C options (re-queue / not yet / split). No silent state file changes.

**Rationale:** Re-queuing sends work back to autonomous agents. If the resolution was incomplete or the user isn't confident, the agent will waste another cycle and potentially block again. The cost of asking is one interaction; the cost of premature re-queuing is a lost agent cycle.

**Rejected alternative:** Auto-re-queue after resolution (original draft behavior). User: "there should be very strong language asking the user if this iter is ready to be re-queued."

#### Progress.md writes during refine: per-decision + stage summary

Refine appends to progress.md at two granularities: (1) per-decision entries as they happen (each triage action, each re-queue, each revise/reset/withdraw), and (2) a stage summary after completing each step. All use `phase: refine`.

**Rationale:** Per-decision entries give the next implement agent context on why an iteration is back in the queue or why the spec changed. Stage summaries give humans a quick overview without reading every per-decision entry. Both are needed.

Also considered end-of-session summary only (loses per-decision context), per-decision only without summary (hard for humans to scan), and no progress.md writes at all. User: "it should append. not after each session but more regularly. definitely after re-queueing."

#### `withdrawn` lifecycle value

New terminal lifecycle state for iterations deliberately retired during refine. Chose `withdrawn` over alternatives: `superseded` (too specific — only covers replacement), `cancelled` (implies we just stopped, lacks the "deliberate decision" nuance), `retired` (ambiguous synonym). `withdrawn` covers all cases: superseded, user changed mind, descoped, no longer relevant.

**Rejected alternatives:** `superseded`, `cancelled`, `retired`, `obsolete`, `archived`, `displaced`, `deprecated`, `rebased`.

#### "Revise" not "Preserve" for partially complete iterations (RFN_9)

The option for updating a partially complete iteration in place is called "Revise."

**Rationale:** "Preserve" implied keeping things unchanged, but the whole point is modifying criteria while keeping existing progress. "Revise" accurately describes what happens — updating the iteration's definition while retaining completed work.

**Alternatives considered:** Update (direct but generic), Amend (formal), Adjust (implies light touch). User chose Revise — "reworking with intent" felt right.

#### Withdraw protocol: full impact summary + cascading resolution

Withdrawing is potentially disruptive. Before executing, the agent must present: (1) which PRD requirements lose coverage, (2) full downstream dependency chain affected, (3) milestone impact. User must explicitly confirm after seeing the impact. If downstream dependents exist, each must be individually resolved (revise/reset/withdraw) — no orphaned dependencies.

**Rationale:** User: "withdrawing is potentially a disruptive option and shouldn't be done lightly and especially shouldn't be done in ignorance of the ramifications." The impact summary ensures the user makes an informed decision. Cascading resolution prevents orphaned dependencies that would leave iterations stuck as `ineligible` forever.

Also considered blocking withdraw when downstream deps exist (too restrictive), auto-cascading withdraw to all dependents (too aggressive — some may be re-pointable), and allowing withdraw with no cascade (leaves broken dependency graph).

#### "More detail" option for partially complete iterations (RFN_9)

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

#### Cascading consistency pass for refine (RFN_16, Step 10)

The refine session touches more files than any other session (reads 4 artifacts, updates 6, modifies fingerprints across 3). Step 10 replaces the generic consistency pass with a structured cascading check following the data flow: decisions → requirements.md → iterations.md → state files. Each stage verifies the downstream artifact reflects everything upstream. This catches drift at the boundaries between artifacts rather than checking each file in isolation. Added as RFN_16 in the PRD.

#### `refine` phase value added to format spec

formats.md Phase field expanded from `implement | verify` to `implement | verify | refine`. Plet ID context segment `r1` (refine session 1) added alongside `i1`/`v2`. Discovered via consistency pass — refine.md prescribed `phase: refine` but the format spec didn't allow it.

#### `refineSessionCount` in state.json

Added to global state.json to track refine session number. Incremented at the start of each refine session entry. Used as the attempt number in plet ID context segments (`r1`, `r2`, etc.).

**Rationale:** Impl/verify track attempts in per-iteration state. Refine is project-level, so the counter lives in global state. Considered using timestamp-only (no counter) since the Crockford segment already gives uniqueness, but the session number enables grouping — grep `_r3` to see everything from one refine session. The grouping value was the tiebreaker.

#### `loopSessionCount` (CASE_LOGA_R01_REC_5)

Added to global `state.json` to track loop invocations. Incremented at the start of each `/plet loop` invocation. Used in branch names (`loop1`, `loop2`). Mirrors `refineSessionCount` — same suffix, same semantics. Name chosen over `loopCount` (too terse) and `loopInvocationCount` (breaks naming parallel with `refineSessionCount`).

#### Workstream branch creation (CASE_LOGA_R01_REC_5)

The orchestrator creates workstream branches at phase entry:
- **Loop:** increment `loopSessionCount`, create `plet/{projectId}/loop{N}/workstream`. If resuming an interrupted loop (branch exists), reuse it.
- **Refine:** increment `refineSessionCount`, create `plet/{projectId}/refine{N}/workstream`. All spec changes committed here.

#### Compaction recovery protocol (OLP_14)

The orchestrator is the longest-lived agent and most vulnerable to context compaction. Subagents are safe (fresh context, short-lived). Protection has three parts:

1. **Canary writes** — after each significant action (loop start, subagent spawn, subagent completion), the orchestrator writes/updates a progress.md entry with `Phase: orchestrator`, `Status: ACTIVE`, and critical state: `projectId`, `loopSessionCount`, branch name, iteration lifecycle counts.
2. **Detection** — after compaction, the orchestrator won't remember writing the canary. If it can't recall its operational state, it reads the last orchestrator ACTIVE entry for immediate orientation.
3. **Recovery** — re-read SKILL.md → state.json (including `sessionHistory`) → active per-iteration state files → confirm git branch → write recovery canary → resume.

**Rationale:** All state lives on disk by design, but the orchestrator needs to *know* to re-read it. The canary serves dual purpose: compaction detection and fast re-orientation without reading every file.

#### Session history ledger

Append-only array in `state.json` (`sessionHistory`) tracking the sequence of loop and refine sessions. Each entry has `type`, `session`, `branch`, `startedAt`, `endedAt`. The last entry is the current/active session (`endedAt: null`); the previous entry is the parent branch that the current session branched from. Solves two problems: (1) the orchestrator always knows where to branch from for the next session, (2) the full session sequence is visible without git archaeology.

**Chaining model:** Each workstream branches off the previous one — `loop1/workstream` → `refine1/workstream` → `loop2/workstream`. The first phase branches from `main`. Merge to main is always a human decision — never automatic. Merging to main may trigger deployments, CI/CD pipelines, or other side effects. The target may also not be main — the human may merge to `staging`, `test`, `qa`, or other branches depending on their workflow. plet has no opinion on the target; it only manages the workstream chain.

**Rejected alternatives:**
- Single `activeBranch` field — loses history, can't answer "what was the sequence?"
- Two fields (`activeBranch` + `parentBranch`) — better but still loses full history
- Derived from counters — ambiguous when phases repeat (two loops in a row without a refine)

#### `proj` sentinel for project-level plet IDs

Refine-phase entries that aren't tied to a specific iteration (stage summaries, triage summaries) use `proj` as the iteration context segment: `epr_01JD8X3K7M_proj_r1`. Per-iteration refine entries (re-queuing ITR_005) still use the iteration ID: `epr_01JD8X3K7M_id005_r1`. Keeps the plet ID segment structure consistent and parseable.

**Subplets note:** `proj` is unambiguous within a single plet directory. In a multi-subplet scenario, each subplet has its own artifacts, so `proj` stays scoped. See Multi-Developer Analysis open threads for cross-subplet plet ID considerations.

### NOTES_DES_6: Cross-cutting

#### Python target 3.8 → 3.11 (2026-04-06)

Bumped minimum Python version. 3.8 hit EOL October 2024. 3.11 is macOS Sonoma default. Unlocks `datetime.UTC` (fixed 584 test warnings from `utcnow()` deprecation), `match/case`, `tomllib`, `X | Y` union types.

#### Consistency passes

Four levels: Quick (grep for one pattern), Standard (grep + cross-reference IDs — the default), Sweep (inventory all instances, categorize, get approval, execute systematically — for broad convention changes), Structural (full scan, spawn agent). Quick and Standard run proactively after changes. Structural needs confirmation. Renamed from numbered "flavors" to intuitive sizing; replaced Deep (never used in practice) with Sweep (validated during vocabulary cleanup miniplan) (2026-03-10).

#### Plan phase review discipline — NLR + R/O stable tail (2026-04-05)

R10 observation (CASE_LOGA_R10_OBS_1): plan agent presented choices as flat A/B/C lists instead of NLR format. Root cause: plan.md had no NLR guidance — the plan subagent doesn't read the user's CLAUDE.md, only its reference file. Fix: rewrote Review Discipline section in `references/plan.md` modeled on `/fast-chat` skill prose patterns. Key additions: "silence is not approval" as core rule, R/O stable tail on every review prompt, NLR mechanics (batch parsing, 1b1, single-decision letters-only, fenced code blocks), full interaction transcript example. Updated Steps 1, 2, 4, 5, 6, 8 to use R/O tail. Plan.md is now self-contained on interaction style.

#### Decision Discipline (CLAUDE.md)

Discovered during the refine.md build: we designed RFN_16 (cascading consistency pass) and immediately failed to cascade it into the PRD — the exact failure mode it's designed to catch. Root cause: NOTES.md Discipline captures *what was decided* but doesn't ensure the decision *lands in all affected artifacts*. Decision Discipline is the complement: after capturing a decision in NOTES.md, trace it through the data flow (PRD → reference files → schemas → PLAN.md). Two-step flow: (1) capture (NOTES.md Discipline), (2) cascade (Decision Discipline). Kept as separate sections in CLAUDE.md — same spirit, distinct responsibilities.

#### Required Reading acknowledgment test (2026-03-09)

**What we tested:** Whether the agent reliably reads and acknowledges all Required Reading files listed in CLAUDE.md on session start — including files it hasn't seen before.

**Setup:**
1. Created `TEST_REQ_READING.md` with a simple instruction ("Tell me a short joke")
2. Added it to the Required Reading list in CLAUDE.md
3. Deleted the auto-memory `MEMORY.md` so session bootstrap had to recreate it
4. Documented the test in `ACTIVE_TEST.md`

**Method:** Quit Claude Code, relaunched, sent "hi" as the first message.

**Results — all pass:**
- Agent read CLAUDE.md, PLET.md, and TEST_REQ_READING.md before responding
- Agent prominently acknowledged all three files by name
- Agent followed the instruction in TEST_REQ_READING.md (told a joke)
- Agent noticed MEMORY.md was missing and bootstrapped it with the acknowledgment rule

**Takeaway:** The Required Reading mechanism works as designed. New files added to the list are picked up on the next session without any other changes. The auto-memory bootstrap also works — it recreated MEMORY.md from scratch when deleted.

**Cleanup:** Removed `TEST_REQ_READING.md`, `ACTIVE_TEST.md`, and the test entry from Required Reading. Added a permanent "SESSION GREETING" rule to CLAUDE.md (tell a joke on session start) — inspired by the test.

#### Archive tag convention (2026-03-09, superseded 2026-03-10)

~~Original format: `archive/plet/{projectId}/{run}/{path}`.~~ Superseded by case study archive convention below.

#### Case study archive convention (2026-03-10)

**Format:** `casestudy/{project}/{runN}/{type}/{exact original ref name}`

Where `{type}` is `branch` or `tag`, and the original ref name is preserved verbatim to track naming convention changes across runs.

**Example:**
- `casestudy/logalyzer/run1/branch/plet/loop/ITR_001` (was branch `plet/loop/ITR_001`)
- `casestudy/logalyzer/run1/branch/logalyzer_workstream` (was branch `logalyzer_workstream`)

**Purpose:** Preserve all git artifacts from a case study run for later analysis. Branches and tags are artifacts — their original names are part of the record. If plet's naming convention changes between runs, the verbatim names make that visible.

**Decision: archive only branches, skip redundant tags.** The `archive/loga/run1/...` tags from run 1 were a temporary hack to preserve branch tips before deletion — but the branches were never deleted, so the tags are 100% redundant (verified: all 11 tag/branch pairs point at identical commits). The archive tags are scaffolding, not meaningful run artifacts. Archiving them would be archiving a workaround, not the run.

**Cleanup plan (executed 2026-03-10):**
- Create 11 new tags: `casestudy/logalyzer/run1/branch/{original branch name}` for each of the 10 `plet/loop/ID_*` branches + `logalyzer_workstream`
- Delete 11 old `archive/loga/run1/...` tags (local + remote)
- Delete 11 `origin/plet/loop/...` remote branches + `origin/logalyzer_workstream`
- Delete local branch `logalyzer_workstream`
- Not touched: `subplets` tag, `origin/claude/power-tips-slide-deck-COQOh`

#### Subagent injection ordering (2026-03-09)

Moved `references/execute.md` and `references/phase-verify.md` to the top of their respective injection lists in SKILL.md. Previously, the iteration definition was injected first, pushing the behavioral reference file (which defines the agent's entire job) to second position.

**Claude Code subagent behavior (confirmed):** Subagents start with a completely fresh context window. The injected prompt is the system prompt — the subagent's entire world. There is no inherited parent context, no CLAUDE.md from the parent session, no conversation history. Only the prompt, environment details (working directory, git status), and the filesystem.

**Hypothesis:** This ordering may have contributed to the artifact quality degradation observed in Run 1 (case study § 3.5 #8). Since the injection list *is* the subagent's entire context, primacy matters even more than in a long conversation — whatever appears first has maximum weight in a clean context window. If the behavioral instructions (commit incrementally, write state in real time, write learnings/emergent) appear after the iteration definition and project context, they may receive less attention. The Run 2 comparison will test whether this change improves compliance.

#### Commit prefix update: `notes` → `docs`, add `retro` (2026-03-09)

Deprecated `notes:` prefix — too narrow, only covered NOTES.md changes. Replaced with `docs:` which covers all documentation: NOTES.md, CLAUDE.md, PLET.md, README, etc.

Added `retro:` prefix for case studies, self-improvement analysis, and post-run retrospectives. Ties into the self-improvement principle: the case study process (run → observe → recommend → apply → re-run) is a retrospective, and its commits should be identifiable as such.

Updated prefix table in CLAUDE.md: `spec`, `skill`, `plan`, `docs`, `retro`.

#### case_studies/ folder location (2026-03-09)

Case studies live in `case_studies/` at project root. Considered: `examples/` (mixes source with analysis), `docs/` (too generic), `examples/logalyzer/` (colocated but wrong scope), `examples/logalyzer/case_study/` (too nested). Chose top-level `case_studies/` because: (1) case studies are about plet's performance, not the example project, (2) scales to multiple case studies across different projects, (3) self-documenting folder name.

#### Trace files — on by default, configurable (CASE_LOGA_R01_REC_8) — DECIDED (2026-03-10)

Traces are a real feature, on by default, can be disabled via config. The logalyzer run only generated traces for ITR_001 — that's a bug in execution, not a spec problem. The format definition in state-schema.md stays. When config artifacts are designed, add a toggle to disable trace generation. Rejected: removing traces entirely (loses traceability), mandating with no opt-out (too rigid).

#### Branch isolation via git worktrees (CASE_LOGA_R01_REC_11) — DECIDED (2026-03-10)

Parallel agents each get their own git worktree for their iteration branch. True filesystem isolation — agents can't contaminate each other's branches. Claude Code supports `isolation: "worktree"` on subagents natively. The logalyzer run proved that branch discipline alone fails (ITR_006 work on ITR_011 branch). Worktree directory naming is left to Claude Code — plet controls the branch name (already defined), not the filesystem path. Rejected: sequential-only (loses parallelism), shared working directory with branch discipline (fragile, proven to fail), separate full clones (overkill when worktrees exist), plet-controlled worktree paths (unnecessary, Claude Code handles creation/cleanup).

#### Artifact quality monitoring (CASE_LOGA_R01_REC_10) — DECIDED (2026-03-10)

Two-layer enforcement, orchestrator stays simple:
- **Implement agent** self-checks before marking done — confirms it wrote learnings, emergent, and progress entries, and state file has required fields.
- **Verify agent** independently confirms — artifact entries exist for the iteration, state file schema compliance. This is additive to its existing checklist.
- **On failure:** cycle back — missing artifacts treated like a failed acceptance criterion.
- **Orchestrator does nothing** — it routes and tracks, never inspects artifact content. See orchestrator simplicity principle.
- Rejected: orchestrator-side validation (too much work for the long-lived agent), quality gating (subjective, hard to automate), warnings without teeth (didn't prevent degradation in logalyzer run).

#### Orchestrator simplicity principle (2026-03-10)

The orchestrator is the longest-lived agent and most vulnerable to context pressure. Its work should be as simple as possible — delegate complexity to short-lived subagents (implement, verify) that have fresh context windows. The orchestrator routes, spawns, and tracks; it does not judge quality or validate content. Heavy lifting belongs in subagents.

#### Co-Author tags on all agent commits (CASE_LOGA_R01_REC_13) — DECIDED (2026-03-10)

All agent-authored commits (implement, verify, merge, orchestrator) get a `Co-Authored-By` tag. Git author is the user's identity (Claude Code commits as the user), so the tag is the only signal distinguishing human commits from agent commits. Consistency matters for audit trails. Rejected: no tags (loses the only authorship signal), implement-only (inconsistent, no principled reason to exclude verify/merge).

#### Logalyzer re-run plan (2026-03-09)

Agreed to a two-phase approach: first improve plet based on case study recommendations (R_1–R_13), then re-run logalyzer from the plan checkpoint (`203c58a`, rebased from original `7cecbf5`) — same spec, fresh execution with improved plet. This gives a direct before/after comparison with the plan session output as the control variable. Detailed phasing in `case_studies/CASE_STUDY_LOGA_R01.md` § Next Steps.

#### Logalyzer run 2 setup and run 1 archival (2026-03-10)

**Context:** All FEEDBACK_FOO.md items (FOO_1–FOO_8) resolved. Ready for comparison run 2 with improved plet.

**Key decisions:**

- **Case study runs are not plet loops.** Branch naming should not conflate case study runs with actual plet lifecycle events. The `loop{N}` in branch names implies a plet session, but these are "same plan, different version of plet" comparison runs. Let plet pick its own branch names during execution — we only control the archival naming.
- **Plan checkpoint branch:** Renamed `exmaple` (typo, but important) to `casestudy/logalyzer/plan-checkpoint`. Now at `203c58a` (rebased from original `7cecbf5`; `examples/logalyzer/` content identical) — the shared starting point for all comparison runs. Not run-specific; lives outside `run{N}/` namespace.
- **Archive tag convention:** `casestudy/logalyzer/run{N}/branch/{original_branch_name}` — preserves the original branch name for traceability.

**Discoveries during archival:**

- **Run 1 archiving was incomplete.** 11 of 16 branches had been tagged previously; 4 were missing (ITR_006, ITR_007, ITR_010, ITR_012). Caught by systematically comparing local branches against existing tags.
- **ITR_007 had no branch at all** — it was already deleted without being tagged. The verify commit (`b279b73`) was reachable from other branches so it wasn't orphaned, but it had no dedicated tag. Created tag from the known commit.
- **None of the run 1 iteration branches were merged into main.** The logalyzer implementation code lives entirely on iteration branches (now archived as tags). Main only has the case study analysis and plet skill improvements. This makes sense — the logalyzer code isn't the product, the plet observations are.
- **5 of 8 existing tags matched their branch tips exactly.** Verified with `git rev-parse` comparison before deleting any branches. The 4 missing tags were created first, then all 8 branches deleted. Zero orphan commits, zero data loss.

**Data loss verification process:**
1. Listed all local branches and all tags
2. For each branch to delete: checked if a matching tag existed and if SHAs matched
3. For branches without tags: created tags at branch tips before deletion
4. For ITR_007 (no branch): confirmed commit `b279b73` was reachable and created tag
5. Post-cleanup: verified local and origin tags matched (pushed 4 new tags)

**Final state:** 4 local branches (`main`, `casestudy/logalyzer/plan-checkpoint`, 2 worktree-agent branches) + 16 archive tags on both local and origin.

#### Linear history and green/rebase/green invariant (2026-03-10)

**Problem:** Run 1 agents created merge commits (e.g., `3b825f4 Merge branch 'plet/loop/ITR_006'`) despite PLET.md and SKILL.md specifying rebase + fast-forward. Root cause: phase-verify.md had a plain `git merge` command (lines 395-402), contradicting the stated convention. execute.md had no mention of rebase at all.

**Decision:** Linear history is a hard requirement, not a preference. Never create merge commits. Added the **green/rebase/green invariant**: all tests must pass before the rebase AND again after the rebase, before the fast-forward merge. This prevents silent breakage when two independently-green branches are combined.

**Rationale:**
- Linear history enables clean `git bisect` — critical for autonomous agents producing many iterations
- Audit clarity — each commit tells a clear story, no merge bubbles
- Green/rebase/green is the safety net that makes rebase trustworthy
- Agent simplicity — rebase is simpler to reason about than merge conflict resolution in merge commits

**Ownership:** The verify agent owns the rebase step (it already owned the merge-to-workstream step). Whoever performs the rebase is responsible for the green/rebase/green invariant. This keeps the orchestrator thin.

**Changes made:**
- **prd.md** (IMP_16): strengthened from "strongly preferred" to "required", added green/rebase/green invariant, specified verify agent ownership
- **phase-verify.md**: replaced `git merge` with rebase + `git merge --ff-only`, added full green/rebase/green procedure including conflict resolution and re-squash
- **execute.md**: added "never create merge commits" critical rule
- **SKILL.md** and **PLET.md**: already correct, no changes needed

#### FEEDBACK_FOO.md formalization (CASE_LOGA_R01_REC_12) — DECIDED (2026-03-10)

FEEDBACK_FOO.md captures meta-observations about plet itself (process issues, instruction gaps, tooling friction). Distinct from learnings.md (target project) and emergent.md (execution discoveries).

Key decisions:
- **Who writes:** Humans only. Agents write to emergent.md; humans recognize which items are plet-process issues and promote them to FEEDBACK_FOO.md.
- **When:** During refine sessions or anytime the human notices a plet-process issue.
- **Format:** Tagged — `FOO_N: Title [tag1] [tag2]` + description paragraph. Seeded tags: autonomy, state, git, artifacts, timing, prompting, config. New tags welcome.
- **Mutability:** Editable. Resolved entries marked `[resolved]` with promotion target. Kept for history.
- **Promotion path:** Depends on the item — CLAUDE.md/PLET.md (rule), config artifact (setting), PRD (requirement), reference files (agent behavior).
- **Location:** Project root alongside CLAUDE.md, PLET.md, NOTES.md.
- **Rejected:** Agents writing directly to FEEDBACK_FOO.md — they can't reliably distinguish plet-process issues from project issues. The human is the filter.

#### Notes skill spec update (2026-03-12)

Updated `prd-notes-skill.md` to reflect lessons from 50+ sessions of use. Key decisions:

- **Standalone `/notes` skill** that plet's plan session can invoke. Useful independently, composable with plet.
- **Generalized from PRD to "spec"** — the skill works with any design document, not just PRDs.
- **Sections are suggested starting points, not rigid template.** Structure should evolve with emergent content. Sections may merge, split, or be retired (content migrated elsewhere).
- **Top-tier sections** (most important): Key Design Decisions, Invariants & Critical Requirements, Important Concepts & Insights, Taxonomy/Conventions. Rest are useful but lower-traffic.
- **Core Workflow / Architecture dropped** as standalone section — folded into Project Context as a one-liner.
- **PRD Change Log and Review Pass Changes merged** into Key Design Decisions as dated entries.
- **Motivation / Problem Statements dropped** — folded into decision entries as "why" context.
- **Reorganization** — new section describing when and how to restructure NOTES.md (drift signals, graduation of outgrown content, reorg pass procedure).
- **Size management** — new section acknowledging that NOTES.md consumes context and needs active management.
- **Bootstrap flow** — new section for first-time `/notes` invocation on a project.
- **Notes Discipline** — explicit framing for the operating rules as a named discipline.
- **Cascade awareness** — operating rule noting that CLAUDE.md or other directive files may define project-specific cascading instructions.
- **Consistency passes** — operating rule to run consistency passes after significant updates (level deferred to project conventions).
- **Signs content has outgrown NOTES.md** — three signals: develops internal structure, dominates parent section, stops getting updated AND matches other signals. Static content alone is fine (settled decisions are still valuable institutional memory).
- **Generalized further from "spec" to "project"** — the skill works for any repo type (code, content, specs, etc.), not just spec-driven projects. Language uses "project artifacts" throughout.
- **Multiple NOTES.md files** — new section covering when subfolders need their own NOTES.md (distinct decision history, different contributors, size), routing tables in CLAUDE.md, cross-references over duplication, on-demand loading.
- **Notes Discipline example** — operating rules section now includes the exact CLAUDE.md wording as a recommended template for projects to adopt.
- **IDs on notes entries: not recommended.** Considered formal IDs (e.g., `NOTE_KD_N`) for notes entries. Rejected — notes entries are too fluid (reorgs cause ID churn), section headers serve as natural references, and notes are read not cited by ID. IDs earn their keep in PRDs where requirements need traceability; notes entries are prose.
- **Reorg operating rule added (rule 9).** "Watch for reorg signals" — periodically assess whether structure still fits, suggest reorg when drift signals appear.
- **Multiple NOTES.md files go in subfolders.** Made explicit: second notes file is always `subfolder/NOTES.md`, never `NOTES-2.md` at root.
- **SKILL.md built** — 201 lines, covers bootstrap, Notes Discipline, reorg, routing, size management, outgrown content signals.
- **Description optimization attempted.** Ran skill-creator trigger eval (20 queries). Result: 100% precision (no false triggers), 0% recall (Claude doesn't invoke skills for implicit capture requests). Acceptable for v0.1 — CLAUDE.md Notes Discipline block handles the implicit capture behavior.
- **Plugin metadata: dual distribution attempted, reverted.** Tried two entries in marketplace.json with different `skills` paths — only plet showed up. Restructuring into separate source directories (official Anthropic pattern) would work but creates duplication/symlink issues. **Decision:** notes-md will be its own repo (`amattn/notesmd`) as a standalone plugin. The notes skill stays bundled with plet in plet-skills — installing plet-skills gets you both.

#### Notes skill review pass (2026-03-13)

Reviewed SKILL.md against skill-creator best practices. Three changes made:

- **Description rewritten for better triggering.** Led with action, added trigger phrases (`decision log`, `design journal`, `why did we decide`, `what was the rationale`, `log this`), added negative boundary (do NOT trigger for plet runtime artifacts learnings.md/emergent.md/progress.md). ~111 words, slightly over the ~100 word guideline but acceptable per skill-creator's "be pushy" advice.
- **Explicit interaction model added.** Bare `/notes` now has defined behavior: bootstrap check → status → catch-up scan → reorg check → prompt. Subcommand overrides: `/notes bootstrap`, `/notes reorg`, `/notes catch-up`. Auto-detect by default, subcommands as overrides.
- **Bootstrap language strengthened.** Added "most critical operation" framing, merged CLAUDE.md reference + discipline block into one non-negotiable step with rationale, added partial bootstrap detection (fix incomplete setups).
- **PRD trimmed to design rationale.** Operational sections compressed to summaries — enough to regenerate the skill, not a second copy. CLAUDE.md discipline blockquote preserved verbatim. Header note marks SKILL.md as authoritative implementation.
- **Dropped recommendation: SKILL.md duplication.** Initially flagged duplicate CLAUDE.md template block in SKILL.md — on re-read, no duplication exists. Only one copy at lines 72-89.

#### Extractable skills identified (2026-03-13)

Scanned CLAUDE.md, PLET.md, NOTES.md, and reference files for generalizable patterns. Seven standalone skills identified, tracked in `EXTRACTABLE.md`:

- **EX_1: /chatux** — Chat UX ergonomics. Bundles 10 patterns: NL/NLR options, batch answers, 1b1 mode, single-decision letters, "ok" approval, standard review prompt (A-E with recommend option), always suggest options, show-then-recommend, ask when ambiguous, fenced code blocks. Renamed from /nl — NL is one pattern within the broader chat UX skill.
- **EX_2: /feedback** — Meta-observation tracking. Replaces the old feedback skill plan item in PLAN.md — now part of the broader extractable skills effort (PLAN_XS).
- **EX_3: /dictation** — Voice input correction with project-specific misspelling tables.
- **EX_4: /improve** — Self-improvement / pattern detection. Agent proactively surfaces recurring patterns.
- **EX_5: /bootstrap** — Session bootstrap and compaction recovery. Three-layer defense against context loss.
- **EX_6: /discipline** — Meta-pattern for creating named behavioral disciplines. The framework that makes Notes Discipline, Decision Discipline, and Review Discipline work.

**Key decision:** /feedback removed from PLAN.md as a standalone plan item — folded into the broader extractable skills inventory (PLAN_XS).

- **EX_7: /label** — Greppable ID convention (`XX_N`). Core is the labeling system; consistency passes included as lightweight guidelines, not rigid procedure. Reframed from "consistency pass skill" — the passes only work *because* of labels, so labels are the real skill.

**Rejected from extraction:** Decision cascade (#4), Review Discipline (#7) — too coupled to /notes. Commit conventions (#8), branch workflow (#9) — too project-specific.

#### Extractable skills repo planning (2026-03-13)

- **Repo name:** `session-kit` — curated collection of session-level tools. Approachable and descriptive.
- **GitHub description:** "Battle-tested Claude Code skills for structured collaboration — decisions stick, context survives, patterns compound."
- **Includes /notes** — the notes skill moves into this repo alongside the other extractable skills.
- **EX_1 renamed /nl → /chatux** — NL is one of 10 bundled patterns. Added standard review prompt with lettered options (A. Add, B. Change, C. Remove, D. Recommendations, E. Ok). The "Recommendations" option lets the user ask the agent for suggestions with a single letter.

#### JSON-first output convention — UNV_CMD_31 (2026-04-25)

**Decision:** CLI scripts with `--output json` must use the JSON structure as the single source of truth. Plain text mode formats the JSON for human readability — no separate code path, no independent computation. Pattern: build JSON result first, pass to a text formatter. Prevents drift between text and JSON outputs.

Added as UNV_CMD_31 in `specs/conventions.md` (plet scripts) and ARC_N in `plan-templates/cli.md` (target projects). Convention going forward — existing scripts not retrofitted.

#### Prerelease version bumps per iteration — FOO_76 (2026-04-25)

**Decision:** Iterations bump version metadata to prerelease tags tied to milestones. Format: `{milestone_target_version}-iter.{N}` (e.g., `0.2.0-iter.3`). Refactor iterations at milestone boundaries promote to the release version (e.g., `0.2.0`).

Three layers: (1) `common.md` NFR + DVX entries — universal rule and DX guidance, (2) platform templates (`python.md`, `elixir.md`, `go.md`) — explicit version metadata locations per ecosystem, (3) `phase-implement.md` Version Bump step after pre-flight + `phase-refactor.md` version promote in Completing the Phase.

Version metadata location is platform-dependent — plan session identifies where it lives. Skip if project has no version metadata or plan didn't define milestone target versions.

#### Refine phase is read-only for source code — FOO_77 (2026-04-25)

**Decision:** Refine must not modify source code, tests, configuration files, or build artifacts. Refine updates plet artifacts only (requirements.md, iterations.md, state files, emergent.md, progress.md). If the refine agent identifies something that needs a code change, it should clarify an existing item, create a new requirement item, or create a new iteration for it.

Added as bold preamble to `session-refine.md`. Previous guard was only "complete iterations are frozen" — nothing about source code broadly.

#### Trace files excluded from wip-commit by design — FOO_74 (2026-04-25)

**Decision:** Keep current behavior — `wip-commit` excludes `plet/trace/` to prevent transcript feedback loop. Traces committed only at phase-end via `git add -A`. If a run crashes mid-phase, trace events and transcripts for that phase are lost.

**Future concern:** If crash recovery becomes a real problem, split the exclusion: stage `*-events.ndjson` (small, no feedback loop) but continue excluding `*-transcript.ndjson`.

### NOTES_DES_7: Vocabulary and taxonomy — DECIDED

Standardized hierarchy to eliminate overloaded terms. See **Taxonomy > Vocabulary Hierarchy** for the canonical definitions.

Key decisions:
- **"session"** for Level 1 (was "phase") — pluralizes naturally, aligns with `*SessionCount` fields
- **"phase"** freed up for Level 3 (implement/verify) — zero rename cost, already in file formats
- **"cycle"** reserved as informal only — not a formal level
- **`sessionHistory`** field with `type` key (not `phase`) inside each entry

**Rejected alternatives:**
- "mode" for Level 1 — doesn't pluralize naturally ("two loop modes" is awkward)
- "stage" for Level 1 — could also describe Level 2/3, ambiguous
- "step" for Level 3 — felt too small for a full implement or verify run
- "round" for cycle — workable but "cycle" is more intuitive
- "pass" for cycle — collides with pass/fail terminology
- `"phase"` as the key in `sessionHistory` entries — "what phase of session?" doesn't make sense; `"type"` is more natural ("what type of session?")

**Note:** In code/filenames, `{phase}` in `{phase}-{attempt}` patterns continues to refer to implement/verify (Level 3). This is consistent with the new vocabulary — no rename needed.

### NOTES_DES_8: Branch Workflow

#### Rebase before squash (not after)
- Rebase onto main *before* squashing so merge conflicts can be resolved commit-by-commit
- Previous draft had squash-then-rebase, which hides conflicts inside a single large commit
- Updated order: tag → rebase → squash → push

#### Squash commit follows commit conventions
- The squash commit is the one that lives on main, so it must use `prefix: description` format with a thematic body per § Commit Conventions

#### Tag naming convention: `session/YYYY-MM-DD-topic`
- Tags preserve pre-squash granular history
- `session/` prefix groups them and makes them discoverable
- Alternatives considered: `pre-squash/topic` (less informative, no date)

### NOTES_DES_9: Plan Template ID Convention

#### Template IDs use `_N` instead of integers (2026-04-16)

All plan-phase template files (`references/plan-templates/*.md`) now use `_N` (literal N) for every requirement ID instead of integer suffixes. When the agent composes a requirements document from multiple templates (e.g., `common.md` + `cli.md` + `python.md`), it assigns sequential integers per prefix across all sources.

**Problem:** Multiple templates defined the same ID (e.g., `RCH_1` in common.md, cli.md, and python.md). When composed, IDs collided silently — the agent might skip, overwrite, or produce duplicates depending on how it merged sections.

**Fix:** Every ID in every template is `PREFIX_N`. The composing agent is forced to renumber because there are no pre-assigned integers. session-plan.md updated with explicit renumbering instruction.

**Cross-references:** Internal cross-refs like "per DVX_7" converted to descriptive text ("per the DVX debug-number requirement") since specific IDs no longer exist in templates.

---

## NOTES_PLN: Plan Discussions

Design decisions, alternatives discussed, and rationale for each plan chunk. PLAN.md has the steps and status; this section has the "why."

### NOTES_PLAN_HLP: PLAN_HLP — Subagent CLI Re-learning

#### PLAN_HLP strategy — multi-angle approach (2026-04-03)

8 strategies across 3 categories to eliminate ~150 `--help` lookups/run. Key decisions:

- **Reshape first, document last.** Orchestrator takes over more bookkeeping (HLP_2B) and a phase-complete composite command reduces the surface (HLP_2A) *before* creating cheat sheets or inlining examples — no point documenting commands that will change.
- **Pre-fill context in prompts.** prompt.py assembles CLI examples with iter_id/phase already filled in (HLP_1C). Zero discovery needed for the most common calls.
- **Make discovery cheap.** `--usage` for terse help (HLP_3A), cheat sheet reference in `--help` output (HLP_3C).
- **Excluded:** 2C (batch artifact writes — sacrifices crash recovery). Strategy 4 options (unified CLI, Python API, SDK) — architectural changes beyond scope.
- **3B clarification:** env var points to cheat sheet file path, not inline content.

#### HLP_2A — phase.py end (2026-04-03)

New composite command that bundles end-of-phase bookkeeping into one call: set-verdict → add-progress → append-event → audit-tag → git commit. Replaces 5-6 separate CLI calls from the subagent. Wired into phase-implement.md (Completing the Phase, Blocker Protocol, Failed Attempt, Missing Dependency) and phase-verify.md (Completing the Phase, Cycle Back, Blocker Protocol). Gate-post stays as a separate subagent call — it's a quality check with a self-correction loop, not bookkeeping.

#### HLP_2B — gate-pre NOT moved to orchestrator (2026-04-03)

Attempted to add `plet_gate_phase.py pre` calls to the orchestrator before spawning subagents. Failed: the auto-logger writes progress.md and trace entries to the worktree, creating dirty files that conflict during merge-squash. Tried `--no-log` but that's a test-only flag agents don't know about. Reverted. Gate-pre stays as an optional subagent action. HLP_2B reduced to just removing redundant start-phase instructions from reference files.

#### HLP_3A — --usage flag with invocation syntax + examples (2026-04-03)

Added `--usage` to all 16 plet scripts via `dispatch()` in util_cli.py. Shows compact invocation syntax + one-line description + copy-pasteable example for each command. Three-level escalation path: cheat sheet → `--usage` → `--help`.

Implementation: each `cmd_*` function has a one-line docstring, a `.usage` attribute (required flags with placeholders), and an `.example` attribute (realistic invocation). `dispatch()` reads these to build the output. 45 functions across 16 scripts.

**Design decision:** Initially `--usage` was just one-liner descriptions (like a compact `--help`). Expanded to include invocation syntax + examples because agents still needed a second `--help` lookup for flags. The full format eliminates the second lookup — one `--usage` call teaches every command's exact syntax.

Documented in: UNV_CMD_30 (conventions.md), script_template.md, scripts/CLAUDE.md, phase-implement.md/phase-verify.md tool listings, all 19 spec Universal Flags tables.

#### test_all ruff gate (2026-04-03)

Ruff runs before any tests — if lint or format check fails, tests are skipped entirely. Previously ruff ran after tests and auto-formatted files silently. Fixed: (1) ruff check (lint) first, (2) ruff format --check (verify, no auto-fix) second, (3) suggest fix command on format failure. Missing ruff is a hard error, not a silent skip.

#### HLP_1B + 3B + 3C — cheat sheet + env var + --help footer (2026-04-03)

Shipped `references/cli-cheatsheet.md` organized by caller (subagent commands vs orchestrator commands). `plet_invoke.py` injects `PLET_CLI_REF` env var pointing to the file. Prompt header tells subagents about the escalation path. `--help` footer on all scripts (both top-level and per-command) says "Tip: --usage for compact syntax. cat $PLET_CLI_REF for full cheat sheet."

Complete escalation path: cheat sheet → `--usage` → `--help`.

HLP_1A (inline examples in reference files) deferred — HLP_1C (prompt assembler pre-fills) may make it redundant. Will validate in the next run.

#### LOGA Run 7 — PLAN_HLP validation (2026-04-04)

First run with 0.4.3 HLP improvements. Key results vs Run 6:
- --help lookups: 150 → 98 (-35%). Implement agents nearly eliminated (1.2 avg). Verify agents still heavy (82 of 98).
- phase.py end: 100% adoption (26/26). Impl→verify gaps collapsed 89% (1:47 → 0:17).
- Total wall-clock: 3:04 → 2:49 (-15 min). Code 16% more compact.
- --usage flag: 49 uses. Cheat sheet: 16 references (verify agents only).

Post-R7 improvements based on transcript analysis:
- Verify --help dominated by 2 commands: `add-report` (JSON shape) and `append-event` (event types). Added both to prompt quick ref.
- Strengthened CLI escalation in phase-verify.md to Critical block.
- Reordered prompt quick ref to match workflow (write artifacts → phase end → gate post).
- Injected `PLET_AGENT_ID` env var so agents don't invent IDs.
- Added phase-start commits to both phase-implement.md and phase-verify.md for git timeline visibility.

#### Reference file bug sweep (2026-04-04)

Found and fixed 8 bugs in phase-verify.md + phase-implement.md examples that caused CLI errors every run:
1. Wrong flag names (`--activity` → `--phase-activity`, `--detail` → `--activity-detail`)
2. Non-existent `--elapsed` flag on update-criterion + missing `--agent-id`
3. Removed `--files` flag on add-progress
4. Invalid `--event-type verdict_set` (use `decision`)
5. Invalid `--category "requirement gap"` (use `"spec gap"`)
6. Shell variable aliases (`$IST`, `$ENTRIES`) fail silently → direct `$PLET_SCRIPTS_DIR` calls
7. JSON state example → CLI invocation for failure evidence
8. Hardcoded agent IDs → `$PLET_AGENT_ID` env var

These bugs were likely causing a significant portion of the --help lookups — agents encountered errors from the examples and fell back to --help to learn the real syntax.

### NOTES_PLAN_PAR: PLAN_PAR — Parallel Orchestrator

**Decision (2026-04-04): Conflict recovery via rebase + requeue, not auto-resolve.** When merge-squash conflicts (two parallel iterations touched the same file), the orchestrator does: `git merge --abort` → rebase iteration branch onto updated workstream → set lifecycle to `queued`. The implement agent resolves conflicts on the next pass — it already has full context. Verify then checks the result. This reuses existing retry infrastructure with no new phases.

**Decision: Rebase-requeue does NOT burn an attempt.** The attempt counter tracks agent performance (did the code work?), not scheduling luck (did another iteration modify the same file?). A conflict caused by parallel timing isn't an agent failure.

**Decision: File-level conflict guidance at plan time.** The dependency tree should encode file-level conflicts, not just logical dependencies. If two iterations modify the same file, one should depend on the other — even if the features are logically independent. A dependency costs nothing; a conflict costs a full iteration cycle. Added to plan.md § Dependency Graph Validation.

**Decision: spawn + finalize split.** `_process_single_iteration` split into `_spawn_iteration` (worktree + implement + verify — parallelizable, returns result dict) and `_finalize_iteration` (verdict + merge-squash + cleanup — sequential on workstream). Breakpoints and max-iterations stay in the serial wrapper for now, move to the main loop in PAR_6. The split is the prerequisite for ThreadPoolExecutor in PAR_3.

**Design: Round-based → streaming execution (revised 2026-04-04).** Initial implementation used synchronized rounds (spawn all → wait all → finalize all → next round). User pointed out this is suboptimal: if ITR_001 finishes before ITR_002 and ITR_003, its dependent ITR_004 should spawn immediately, not wait for the round to complete.

Revised design: **streaming work queue.** ThreadPoolExecutor stays full as long as there's eligible work. As each iteration completes, it's finalized immediately (merge-squash), newly eligible iterations are checked and spawned. No synchronized round boundaries.

**Decision: Breakpoints are gentle pauses (2026-04-04).** A breakpoint (before or after) means "stop spawning new work." Everything already in-flight runs to completion and gets merged. Breakpoint-before is checked at spawn time — if hit, that iteration doesn't spawn AND no further iterations spawn. Breakpoint-after is checked after finalization — if hit, no further iterations spawn. In both cases, all active iterations finish normally.

Example: ITR_001, ITR_002, ITR_003 running. ITR_001 finishes, promotes ITR_004 and ITR_005. ITR_005 has breakpoint-before. When checking ITR_005, the breakpoint fires — ITR_005 doesn't spawn, no further spawns happen. ITR_002, ITR_003, ITR_004 (if already spawned) all run to completion and merge. Then pause.

### NOTES_PLAN_COV: PLAN_COV — Coverage Infrastructure

Canonical home: specs/NOTES.md § SPEC_PLN_COV (script tooling). Coverage infrastructure, tuple returns, test conversion, event sink, injectable runner.

### NOTES_PLAN_CLN: PLAN_CLN — Script Cleanup & Consistency

Canonical home: specs/NOTES.md § SPEC_PLN_CLN (script tooling). Validator patterns, parse_command adoption, extract_output_flags, help_hint factory, dedup-before-refactor principle.

### NOTES_PLAN_RBS: PLAN_RBS — Rebase-over-Squash

**Decision (2026-04-05): Replace merge-squash with rebase + fast-forward merge.** Individual wip commits from implement/verify survive into workstream history. No squashing.

**Why:** Every parallel run (R09, R10, R11) hit merge-squash failures. The squash operation adds complexity for a cosmetic benefit:
- Dirty-tree recovery (`_try_merge_squash`) — needed because merge-squash is sensitive to uncommitted state
- stdout/stderr conflict detection bug — `git merge --squash` puts CONFLICT on stdout, code checked stderr (4 versions undetected)
- Conflict recovery already does a rebase — the squash is an extra step on top of something that already works

**What changes:**
- `git_ops.py`: new `rebase-commit` command — `git rebase workstream` on iter branch, then `git checkout workstream && git merge --ff-only iter_branch`. Old `merge-squash` command stays (alternative strategy, some projects may prefer squashed history).
- Orchestrator: `_try_merge_squash` / `_handle_merge_conflict` simplify to rebase + ff-merge via `rebase-commit`
- Conflict recovery: rebase failure → requeue for implement (same as today, but without the merge-squash retry layer)
- Commit history: workstream shows all wip commits from each iteration, linear (rebase ensures no merge commits)

**Flow comparison:**

Current merge-squash (3 layers):
```
_handle_passed_verdict
  → _try_merge_squash
    → git add -A + commit (clean workstream for squash)
    → git merge --squash iter_branch + git commit
    → if dirty tree: clean + retry merge-squash
  → if conflict (string match on stderr/stdout):
    → _handle_merge_conflict
      → git rebase ws_branch iter_branch
      → if rebase fails: abort, requeue
      → if rebase succeeds: retry merge-squash AGAIN
      → if still fails: requeue
```

New rebase-commit (1 layer):
```
_handle_passed_verdict
  → git_ops.py rebase-commit
    → git rebase ws_branch (on iter branch)
    → if conflict: abort, return error
    → git checkout ws_branch
    → git merge --ff-only iter_branch
  → if error: requeue for implement
  → cleanup (tags, branches)
```

Key simplifications:
1. No dirty-tree recovery — rebase operates on iter branch, not workstream
2. No retry-after-rebase layer — rebase IS the operation, not a recovery step
3. No stdout/stderr string matching for conflict detection — `git rebase` returns nonzero cleanly
4. One layer instead of three (`_try_merge_squash` + `_handle_merge_conflict` + retry → just rebase-commit)

**Two commands, different conflict behavior (2026-04-05):**

| Command | On conflict | Purpose |
|---------|-------------|---------|
| `rebase-prep` | Leave rebase in progress, report conflicting files | Implement agent resolves |
| `rebase-commit` | Abort rebase, return error | Orchestrator requeues |

**Requeue flow for conflict (2026-04-05, decided):**

1. Orchestrator runs `rebase-commit` → fails (conflict)
2. Orchestrator sets lifecycle → `queued`, writes `requeue_reason: "rebase_conflict"` to iter state
3. Prompt assembler sees requeue reason, injects exact command: `git_ops.py rebase-prep plet/ --iter-id ITR_002`
4. Implement agent runs `rebase-prep` — rebase starts, conflicts reported (which files)
5. Agent resolves conflicts, `git add`, `git rebase --continue`
6. Agent continues normal implement flow
7. Verify phase — normal
8. Orchestrator runs `rebase-commit` — iter already rebased, rebase is no-op, ff-merge advances workstream

Branch state on requeue: leave as-is (option A). The `rebase-prep` command in the injected prompt prevents drift — agent can't miss it. No orchestrator branch manipulation needed.

**Full conflict resolution flow (16 steps):**

```
FIRST PASS (normal)
═══════════════════
1. Orchestrator spawns ITR_002 → implement agent runs in worktree
2. Implement agent: write code, tests, commit wip commits
3. Verify agent: checks acceptance criteria, passes
4. Orchestrator: runs rebase-commit
   → git rebase workstream ID_002_branch
   → CONFLICT (ITR_001 merged to workstream while ITR_002 was running)
   → git rebase --abort
   → returns error

REQUEUE
═══════
5. Orchestrator: lifecycle → "queued"
6. Orchestrator: writes requeue_reason: "rebase_conflict" to iter state
7. No attempt burned (scheduling luck, not agent failure)

SECOND PASS (requeued)
══════════════════════
8.  Orchestrator spawns ITR_002 again → implement agent runs in worktree
9.  Prompt includes: "⚠️ Requeued due to merge conflict.
     Run: git_ops.py rebase-prep plet/ --iter-id ITR_002"
10. Agent runs rebase-prep
    → git rebase workstream
    → CONFLICT in shared.txt
    → leaves rebase in progress
    → output: "Conflicts in: shared.txt"
11. Agent opens shared.txt, resolves conflict markers
12. Agent: git add shared.txt && git rebase --continue
13. Agent continues normal implement (tests pass, ACs met, wip commits)
14. Verify agent: checks acceptance criteria, passes

FINALIZE
════════
15. Orchestrator: runs rebase-commit
    → git rebase workstream (no-op — already rebased in step 10)
    → git checkout workstream
    → git merge --ff-only ID_002_branch
    → OK ✓
16. Orchestrator: lifecycle → "complete"
```

If another iteration merges between steps 9 and 14 with a conflicting change, step 15 fails again and the cycle repeats. In practice this is rare — the plan phase guides users to add dependencies when iterations touch the same file, so conflicts are edge cases.

**Decision (2026-04-06): `remainingRetries` — retry budget separate from attempts.** New required int field in per-iteration state, starts at 3. Decremented on agent failure (verify rejection, implement failure). NOT decremented on rebase-commit requeue (scheduling luck). `check-retry` now checks `remainingRetries > 0` — replaced the old failure-trend analysis (decreasing trend → extended limit) with a simple budget counter. Attempts is a factual counter (how many times did this run); remainingRetries is the budget (how many more chances). This distinction exists because rebase requeue increments attempts but should not consume retry budget.

**Decision (2026-04-06): Audit tags stay at pre-rebase commit hashes.** After rebase, rebased commits have new hashes. Tags still point at old (pre-rebase) commits — they're still reachable (git doesn't GC tagged commits). Historical reference, not navigational. Simplest approach. `cleanupTagsAutomatically` handles deletion for projects that want it.

**Architectural fix — stash/pop pattern (2026-04-06, revised after R12):** The orchestrator writes lifecycle updates to `state.json` on workstream during iterations (implementing → verifying). These dirty the workstream working tree. The original fix (pre-commit without `--allow-empty`) still caused rebase conflicts because the committed state.json diverged from the iteration branch's copy. R12 confirmed: even the first iteration (ITR_001) conflicted on state.json.

Final fix: `_execute_rebase_commit` stashes dirty workstream files before rebase, pops after ff-merge. No pre-commit at all — the stash preserves lifecycle updates without creating divergent commits. Rebase-commit has its own validator that skips the dirty-tree check.

**Safety valve (2026-04-06):** Rebase requeue burns a retry (`remainingRetries` decremented). Prevents infinite loops like R12. Validated in OLLR R02 — ITR_004 blocked after 3 attempts (no infinite loop).

**Rebase-prep prompt injection (2026-04-06):** On rebase-commit failure, orchestrator writes `requeue_reason: "rebase_conflict"` to iter state. Prompt assembler injects rebase-prep directive. **OLLR R02 result: injected but agent didn't follow it.** Agent re-implemented from old branch point each time. Agent-driven conflict resolution via prompt injection is unreliable.

**OLLR R01/R02 parallel conflict findings (2026-04-06):**

The rebase-commit model works well for non-conflicting parallel iterations (OLLR: ITR_003, ITR_005 both succeeded). But when iterations conflict on the same files, the recovery flow fails:

1. **Agent can't/won't rebase-prep.** Prompt injection was generated but agent didn't follow. Complex multi-step git operations (rebase-prep → resolve → git add → rebase --continue) are too fragile as agent instructions.
2. **Each retry is a full implement+verify cycle wasted.** The code was correct every time — only the merge failed. ~20 min wasted per conflict.
3. **Commit accumulation.** Each retry adds ~12 commits to the iteration branch. Rebase replays more commits each time (12 → 24 → 35), increasing conflict surface.
4. **Rebase-between-phases doesn't fully solve it.** Even if we rebase after implement but before verify, another iteration can merge during verify and invalidate the rebase. The race window shrinks but doesn't close.

**Proposed solution: Sequential fallback on first conflict (2026-04-06).**

On first rebase-commit failure, dynamically add a dependency on whatever just merged. The iteration waits its turn — runs sequentially when its new dep completes. Zero wasted cycles. The plan phase's file-conflict dependency guidance is the primary defense; sequential fallback is the runtime safety net when plan-time detection misses a conflict.

This accepts that parallel execution of file-conflicting iterations is not worth the complexity. The plan phase should catch most conflicts. When it misses one, sequential fallback is cheap and reliable.

**Alternative considered and deferred:** Orchestrator-driven rebase between implement and verify. Architecturally cleaner (verify checks integrated code), but doesn't eliminate the race (another iter can merge during verify). More complex to implement.

**Decision (2026-04-06): Implement-end rebase + dynamic parallel stop.** Two-layer defense:

**Layer 1: Implement-end rebase (proactive).** Every implement phase ends with `rebase-prep` as the last step before `phase.py end`. The implement agent rebases its iteration branch onto the current workstream. If there's a conflict, the agent resolves it — it has full context (just wrote the code). Verify then checks integrated code (as it will exist on workstream). The orchestrator's ff-merge at finalize is usually a no-op.

Why this works better than orchestrator-driven rebase or prompt injection:
- Agent has full context for conflict resolution (it just wrote the code)
- It's a standard phase-implement.md instruction, not a special-case requeue directive — more reliable
- No orchestrator complexity for conflict resolution
- Verify checks integrated code (correctness benefit)
- The common case (iterations with different durations) is handled naturally — the slower iteration rebases onto whatever merged during its implementation

**Layer 2: Dynamic parallel stop (reactive).** On first ff-merge failure, set a flag that stops spawning new parallel work. Everything in-flight finishes and merges one at a time. Requeued iterations run sequentially. Simple boolean flag in the orchestrator — no dep map manipulation.

When parallel stop triggers:
- At most one wasted verify cycle (the iter that failed ff-merge)
- The requeued iter's next implement includes a rebase (per phase-implement.md), catching up with whatever merged
- Subsequent iters run one at a time — no more races

**Three-layer defense against parallel conflicts:**
1. Plan phase: file-conflict dependency guidance (prevents most conflicts at design time)
2. Implement-end rebase: agent rebases onto workstream before verify (catches conflicts with full context)
3. Dynamic parallel stop: on first ff-merge failure, serialize remaining work (safety net for edge cases)

**What to remove:** The rebase-prep prompt injection (`requeue_reason` mechanism) is no longer needed — every implement does rebase, not just requeued ones. The complex rebase-commit stash/pop logic may also simplify since the iteration branch should already be on top of workstream after implement-end rebase.

**OLLR R02 validation:** R02 confirmed that agent-driven rebase-prep via prompt injection is unreliable (agent didn't follow it). But phase-implement.md standard instructions are more reliable — they're part of the normal flow, not a special directive. The risk of non-compliance exists but is lower, and C (parallel stop) handles the failure case.

**Decision (2026-04-06): Always rebase at start AND end of implement.** No conditional logic, no `requeue_reason`, no prompt injection. phase-implement.md instructs:
1. Start of implement: `rebase-prep` (catches anything that merged before this iteration)
2. End of implement: `rebase-prep` (catches anything that merged during implementation)
3. Gate-post enforces #2 via `merge-base --is-ancestor`

First rebase is usually a no-op. When it's not (requeued iteration), it catches the conflict early. Zero special cases — same flow for first attempt and requeued attempts.

**Decision (2026-04-06): Move `remainingRetries` to state.json, remove `requeue_reason`.**
- `remainingRetries` moves from per-iteration state to `state.json` as a parallel dict (like `lifecycles`). Orchestrator-owned, avoids dirtying per-iter state on workstream.
- `requeue_reason` removed entirely. Was used for prompt injection which is superseded by always-rebase + gate enforcement.
- Root cause of R03 stash bug: `_decrement_remaining_retries` wrote to workstream's per-iter state file, dirtying it. The dirty file blocked the next iteration's rebase-commit.

**Decision (2026-04-06): Loop runs ONCE. Never auto-restart.** OLLR R03: agent auto-started session 2 after session 1 ended, autonomously resolving merge conflicts and re-entering the loop. SKILL.md must explicitly say: after the orchestrator exits, report results and STOP. The user decides whether to run another session.

**Permission detection fix (2026-04-06):** `_auto_detect_permission_mode` in plet_invoke.py checked for `"bypassPermissions" in perms` (top-level key) but the actual setting is `defaultMode: "bypassPermissions"`. Fixed to check both. OLLR R02: subagent launched with auto mode despite parent having bypassPermissions.

**What doesn't change:**
- Sequential finalization — still one iteration at a time on workstream
- Audit tags — still mark phase boundaries
- Branch/tag cleanup options — still configurable
- Breakpoints, streaming execution — unaffected

**Tradeoff:** Workstream history is noisier (many small commits vs one per iteration). But: `git log --oneline` is still readable, audit tags still mark boundaries, and the operational simplicity is worth more than cosmetic history.

**Implementation complete (2026-04-06):** RBS_1-24 done. Key changes from the original design:
- `remainingRetries` moved from per-iter state to `state.json` (avoids dirtying workstream per-iter files)
- `requeue_reason` removed entirely (always-rebase supersedes prompt injection)
- Always rebase at start AND end of implement (not conditional on requeue)
- Gate-post enforces rebase (`merge-base --is-ancestor`)
- Dynamic parallel stop on first rebase-commit failure
- `wip-commit` command excludes `plet/trace/` (breaks transcript feedback loop)
- Loop runs ONCE — never auto-restart

### NOTES_PLAN_SEQ: PLAN_SEQ — Sequential Simplification

**Decision (2026-04-06): Abandon parallel orchestration (PLAN_PAR), simplify to sequential-only.**

**Core goal: agents should spend most of their time implementing or verifying, not dealing with plet mechanics.** R06 showed 53% of implement-phase Bash calls were plet infrastructure. Parallel added more mechanics (worktree lifecycle, branch management, conflict recovery, requeue flow) without delivering net improvement. Simplification means less time on plet plumbing, more time on the user's code.

**Why:** The data is clear. Sequential 0.4.x had a perfect completion record (R06-R08: 39/39 iterations, zero human interventions). Everything since — parallel + merge-squash (0.5.x) and parallel + rebase-commit (0.6.x) — has been fighting git mechanics:
- 0.5.x parallel: 27/39 (69%), 2 human interventions
- 0.6.x parallel: 17/24 (71%), multiple interventions
- R14 (0.6.2): per-iteration pace 2-3x slower than 0.5.x best

The theoretical 46% speedup from parallelism never materialized — overhead and failure recovery ate it.

**What stays:**
- All script/tooling improvements (gate scripts, phase.py, coverage infra, plet_state.py, etc.)
- RBS rebase-commit for clean linear history on the workstream
- Audit tags — tag at end of every phase, every iteration, and every loop
- One workstream branch per loop (`plet/{projectId}/loop{N}/workstream`)
- Fresh subagent per iteration (fresh context, same branch)

**What goes:**
- PLAN_PAR (parallel orchestrator, ThreadPoolExecutor, streaming work queue)
- Per-iteration branches (`plet/{projectId}/loop{N}/{iter_id}`)
- Per-iteration worktrees (`.plet/worktrees/...`)
- All merge conflict handling (no merges = no conflicts)
- Dynamic parallel stop, requeue flow, conflict recovery
- `rebase-prep` at start of implement (no conflicts to prep for)

**Maybe:**
- One worktree per loop for subplets (PLAN_SUB)

**The model:** Sequential iterations, all on one workstream branch, rebase onto main at end. Audit tag each phase/iteration/loop boundary. No branch juggling, no merge conflicts, no worktree lifecycle. This kills the entire class of bugs from R09-R11 by eliminating the thing that caused them.

**What RBS becomes without parallel:** Just the clean linear history benefit. Implement commits wip-commit on workstream, audit tag at phase boundaries. At loop end, the workstream has a nice linear history of all iterations. Rebase onto main before merge.

#### NOTES_PLAN_SEQ_OVERHEAD: Agent Overhead Analysis (2026-04-06)

**Estimated overhead (pre-R14):**

Per AC (currently ~5 plet calls each):
- `iter_state.py update-criterion` — state tracking
- `git_ops.py wip-commit` — incremental commit
- `plet_entries.py add-progress` — audit trail
- `plet_trace.py append-event` — telemetry
- `plet_entries.py add-learning` — (if any)

Per phase (~5 more):
- `git_ops.py rebase-prep` — start + end (PLAN_SEQ already removes)
- `git_ops.py audit-tag` — history preservation
- `phase.py end` — verdict + gate checks
- `plet_entries.py add-progress` — phase summary

Estimated: ~30 plet Bash calls vs ~10-15 application calls for a 5-AC iteration. R06 measured 53% infrastructure.

**Actual R14 data (measured from trace files):**

| Command | Total calls | Pattern |
|---------|------------|---------|
| `update-activity` | 42 | Exactly 1 per phase attempt (42 attempts total) |
| `update-criterion` | 42 | Exactly 1 per phase attempt — agents batch all ACs in a single call |

Key finding: agents already batch `update-criterion` — they call it **once per phase**, not once per AC. The per-AC data IS in the state files (detailed evidence per criterion), but agents write it all at once. This means the per-AC call overhead is lower than estimated.

The real overhead comes from the other per-phase calls: progress entries (auto-generated noise → 4,497 lines), trace events, heartbeat, rebase-prep, gate post, and artifact cleanup commits (4-6 commits × 1.6m avg = 20.9m of impl→vfy gap ceremony).

**Implication for `update-activity`:** 42 calls = pure ceremony. Agent calls it once to announce presence. Move to orchestrator — auto-generated at `phase-start` (renamed from `start-phase`). Agent never calls it.

#### NOTES_PLAN_SEQ_OQ: Open Questions — What Else Can Be Simplified?

All open. To be considered carefully before implementation.

**OQ_1: What should the agent NOT do anymore?**

- **OQ_1A: Progress entries → auto-generated from state.** `[decided]` Synthesized from `phaseActivity` and `activityDetail` fields in the iter state file. When those fields change (via `update-criterion` or `update-field`), the iter state script auto-generates a progress entry. Agent never thinks about progress. Progress becomes a derived artifact.

- **OQ_1B: Trace files → auto-generated by CLI shim.** `[decided]` The CLI dispatch shim creates a trace event on script entry and another just before output is written to stdout/stderr. The 3-tuple return pattern makes this easy — the shim wraps every script call with entry/exit events. Agent never calls `plet_trace.py`. Zero agent overhead.

- **OQ_1C: Audit tags → phase-end and iter-end scripts.** `[decided]` Phase-end script writes phase-level tags. Iteration-end script writes iter-level tags (may need to create `plet_iter.py end` or similar). Orchestrator writes loop-end tag. Agent never calls `audit-tag`.

- **OQ_1D: wip-commit per criterion → keep.** `[decided]` Keep per-criterion wip-commits (status quo). Worth the overhead for crash recovery.

- **OQ_1E: Gate scripts → keep, but simplify learnings/emergent.** `[decided]` Keep gate scripts — agent needs to clean up after itself. Learnings/emergent: ask after every green AC (not enforced throughout, but prompted at each AC boundary). Two tight questions: "Did you learn anything that might help other human or autonomous developers? → add to learnings. Did anything emergent come up that needs human clarification in the next refine? → add to emergent." Starting with per-AC (B) — can optimize to once-at-end (A) later and compare quality. Gate scripts simplify accordingly.

**OQ_2: What stays as agent responsibility?**

- **OQ_2A: `plet_state.py update-criterion` (per AC).** `[decided]` Keep. Verify agent needs per-AC status to know what to check. Core signal.

- **OQ_2B: `phase.py end` (per phase).** `[decided]` Keep. One call to wrap up.

- **OQ_2C: Learnings/emergent → optional, asked after every green AC.** `[decided]` Per OQ_1E. Two tight questions after each green AC. Starting with per-AC frequency (B) — can optimize to once-at-end (A) later and compare entry quality between approaches.

**OQ_3: Prompt/context payload — burn less context on plet docs?**

- **OQ_3A: Slim `formats.md` maximally, ideally drop.** `[decided]` The CLI interface IS the format. Audit what formats.md contains that isn't already enforced by `plet_state.py` / `plet_entries.py` — if the tools handle it, the docs are redundant context burn. Slim as much as possible; drop entirely if audit shows nothing the tools don't cover.

- **OQ_3B: Slim `state-schema.md` maximally, ideally drop.** `[decided]` Same reasoning as 3A. Audit needed. If `plet_state.py` enforces the schema, agents don't need to internalize it from prose.

- **OQ_3C: Slim `phase-implement.md` — strip parallel/worktree/branch/conflict/rebase + look for other opportunities.** `[decided]` Not just mechanical removal of parallel sections. Be smart — look for anything else that's ceremony, redundant with tooling, or no longer load-bearing post-PLAN_SEQ.

- **OQ_3D: Inline `cli-cheatsheet.md` into both `phase-implement.md` and `phase-verify.md`.** `[decided]` Both agents need the cheatsheet. Inline into each rather than maintaining a separate file. One fewer injected file per phase.

- **OQ_3E: Slim `phase-verify.md` — strip parallel/worktree/branch + look for other opportunities.** `[decided]` Same approach as 3C. Strip the obvious parallel content, then look for more.

**OQ_4: State schema — fields that become unnecessary?**

- **OQ_4A: `parallelGroup` — remove.** `[decided]` No parallel execution.

- **OQ_4B: `remainingRetries` — keep for verify rejections only.** `[decided]` Simplified: only decremented on verify rejection or implement failure. No conflict requeue decrement (that concept is gone). Still useful as a budget to prevent infinite retry loops on genuinely broken iterations.

- **OQ_4C: `requeue_reason` — remove.** `[decided]` No conflict requeue, no prompt injection.

- **OQ_4D: `lastHeartbeat` / stale detection — remove.** `[decided]` Orchestrator waits synchronously for the subprocess. No need to poll for liveness. Heartbeat was designed for parallel where the orchestrator needed to detect stuck agents.

**Post-decision summary — agent's implement phase for a 5-AC iteration:**

Per AC:
- `plet_state.py update-criterion` — state tracking (auto-generates progress entry + trace event)
- `git_ops.py wip-commit` — incremental commit
- (optional) `plet_entries.py add-learning` — after green, if anything learned
- (optional) `plet_entries.py add-emergent` — after green, if anything emergent

Per phase:
- `phase.py end` — verdict, gate checks, audit tag

Total: **~12-16 plet calls** (down from ~30). The agent *thinks* about 2 mandatory per AC (update-criterion, wip-commit) + 2 optional reflections per AC + 1 per phase (phase end). Progress, traces, and tags are invisible infrastructure. Learnings/emergent frequency starts at per-AC (B) — compare with once-at-end (A) in a later run.

**What RBS becomes without parallel:** Just the clean linear history benefit. Implement commits wip-commit on workstream, audit tag at phase boundaries. At loop end, the workstream has a nice linear history of all iterations. Rebase onto main before merge.

#### NOTES_PLAN_SEQ_SCRIPTS: Script Restructure — Three Entry Points (2026-04-06)

**Decision: Collapse 14 CLI scripts into 3 entry points + importable modules.**

The current 14 `plet_*.py` scripts each have shebangs, CLI dispatch, and subprocess-based tests. This creates:
- Agent must know 4 different scripts to call 5 commands
- CLI shim (dispatch logging, auto-trace, auto-progress) must be consistent across 14 files
- All 2245 tests use `subprocess.run()` — slow (~50s), coverage requires special `coverage_all.sh` harness
- 14 entries in `allowed-tools`

**Proposed layout:**

```
scripts/
  # CLI entry points (shebang, plet_ prefix, allowed-tools, dispatch shim)
  plet_agent.py          # 5 commands — the agent's entire plet vocabulary
  plet_orchestrator.py   # run (the loop) + bootstrap + status/diagnostics
  plet_tools.py       # plan/refine-phase tools: init, fingerprint, validate

  # Importable modules (no shebang, no plet_ prefix, not directly callable)
  global_state.py        # global state (from plet_global_state)
  iter_state.py          # iter state (from plet_iter_state)
  entries.py             # learning/emergent formatting + append
  git_ops.py             # audit-tag, wip-commit, rebase-commit
  gate.py                # session + phase gates (merge both)
  prompt.py              # prompt assembly
  invoke.py              # subprocess launch + transcript capture
  schedule.py            # eligible, breakpoints, retry
  session.py             # start/end session
  fingerprint.py         # extract, embed, check
  trace.py               # validate, query (append-event auto via CLI shim)
  phase.py               # phase-end composite logic
  bootstrap.py           # project setup logic

  # Unchanged internal modules
  util_cli.py            # dispatch, parsing, CLI shim (now only in 3 files)
  util_io.py / util_id.py / util_state.py / util_format.py
  util_subprocess.py / util_git.py / util_constants.py
```

**plet_agent.py commands (agent's entire vocabulary):**

| Command | When | Side effects |
|---------|------|-------------|
| `update-criterion` | per AC | Auto-progress, auto-trace |
| `wip-commit` | per AC | Stages source + plet/ |
| `add-learning` | per AC (optional) | Append to learnings.md |
| `add-emergent` | per AC (optional) | EM_{iter_id}_{N} convention |
| `phase-end` | once per phase | Verdict, gate, audit tag |

**plet_orchestrator.py commands:**

| Command | When |
|---------|------|
| `run` | Loop phase — the main sequential implement→verify loop |

**plet_tools.py commands (as implemented):**

| Command | When |
|---------|------|
| `bootstrap` | Before plan — project setup (CLAUDE.md, .gitignore, plet/ dir) |
| `init` | Plan phase — create state.json + per-iter state files |
| `fingerprint-extract` | Plan/refine — extract fingerprints from spec artifacts |
| `fingerprint-embed` | Plan/refine — embed fingerprints into state.json |
| `fingerprint-check` | Plan/refine — check fingerprint staleness |
| `validate` | Diagnostic — schema checks |
| `detect` | Diagnostic — what phase are we in |
| `status` | Diagnostic — session summary, iteration states |

**Key benefits:**
1. **Agent simplicity:** one script, five commands. Agent's entire plet vocabulary.
2. **CLI shim in 3 files only:** auto-progress, auto-trace, dispatch logging consistent and contained.
3. **Testing:** modules are directly importable → `from state import cmd_update_lifecycle`. No subprocess overhead. Coverage via native pytest-cov, no `coverage_all.sh` hack. Only 3 entry points need subprocess tests (CLI parsing/dispatch).
4. **Orchestrator imports directly:** `import state; state.update_lifecycle(...)` instead of `_run_script("plet_state.py", [...])`. Faster, native exception handling, no exit-code parsing.
5. **Allowed-tools:** 3 entries instead of 14.

**What this changes in the orchestrator:** Currently uses `_run_script` / `_run_script_subprocess` / `_run_script_json_subprocess` to call sibling scripts via subprocess. Post-restructure, the orchestrator imports modules directly (e.g., `import iter_state; iter_state.update_lifecycle(...)`). The `_run_script` pattern survives only for `plet_invoke.py run` (launching claude — that's genuinely a subprocess).

**R14 actual data (validates the design):**
- `update-activity`: 42 calls = 1 per phase attempt. Pure ceremony — move to orchestrator at `phase-start`.
- `update-criterion`: 42 calls = 1 per phase attempt. Agents already batch all ACs in one call, not per-AC. The per-AC overhead concern was overestimated.
- The real overhead is the other per-phase calls: progress entries, trace events, heartbeat, rebase-prep, gate post, and artifact cleanup commits.

**Commands kept for internal use (not agent-facing):**
- `update-activity` — orchestrator calls at `phase-start`
- `add-progress` — auto-generated by state change hooks
- `append-event` — auto-generated by CLI shim

**Rename:** `start-phase` → `phase-start` (verb-last for consistency with `phase-end`).

**Open questions (not blocking):**
- `plet_tools.py` — own script or fold into orchestrator? `[decided]` Own script. Three entry points confirmed: `plet_agent.py`, `plet_orchestrator.py`, `plet_tools.py`.
- State module naming — merge into `state.py` or keep `iter_state.py + global_state.py` separate? `[decided]` Keep separate. Two distinct modules: `iter_state.py` and `global_state.py`.
- Migration: part of PLAN_SEQ or prerequisite? `[decided]` Part of PLAN_SEQ (Phase 2 handles it via SEQ_12).

#### NOTES_PLAN_SEQ_IMPL: Implementation Decisions (2026-04-07)

**trace.py → traces.py:** Renamed to avoid shadowing stdlib `trace` module. Without this, `import trace` in test files resolved to stdlib depending on sys.path ordering. The `s` suffix is minimal and unambiguous.

**plet_tools.py fingerprint commands:** Decided on `fingerprint-extract`, `fingerprint-embed`, `fingerprint-check` as flat hyphenated commands (not nested sub-commands). Matches the `dispatch()` single-level routing and keeps the CLI simple. User confirmed this pattern.

**Orchestrator direct imports:** Replaced `_run_script`/`_run_script_json` subprocess pattern with `_call_cmd`/`_call_cmd_json` which call module functions directly with stdout/stderr capture. Only `_run_invoke` stays subprocess (launching Claude is genuinely a separate process). Injectable via `plet_orchestrator._run_invoke = mock_fn` for testing. ~30% test speedup (35s → 26s) from eliminating subprocess overhead.

**phase-end ordering (decided with user):**
1. add-report (verify only)
2. add-progress
3. append-event (trace)
4. set-verdict
5. gate-post — **hard fail** on rc=1 (failures), warnings (rc=2) pass
6. git commit (only after gate passes)
7. audit-tag (tags the gate-passing commit)

**Why gate before commit:** If gate fails, nothing is sealed. Agent fixes issues and retries — steps 1-4 are idempotent on retry. The audit tag always marks a commit that passed quality checks.

**Why warnings don't block:** Gate warnings (rc=2) are informational — missing learnings/emergent was downgraded from WARN to removed entirely. Only hard failures (rc=1: missing verdict, missing progress, invalid state) block.

**Gate-post is quality-only (decided with user):** Removed all infrastructure checks from post gate:
- Removed: git branch checks (branch-exists, correct-branch, clean-worktree, linear-history, no-stashes)
- Removed: audit-tag existence check
- Removed: learnings-entry and emergent-entry checks (no longer required)
- Kept: state-valid, implement/verify-verdict, progress-entry, trace-events, verification-report, verdict-consistency
- Git infrastructure checks remain in **pre** gate only
- Audit-tag verification moved to **postflight** (orchestrator calls after all iterations)

**Postflight audit-tag verification:** Added `_append_audit_tag_check` to gate_session.cmd_postflight. Verifies implement and verify audit tags exist for every completed iteration. Missing tags produce a warn (postflight never blocks). This is the infrastructure counterpart to phase-end's quality gate.

**git_check.py sequential simplification:**
- Removed `check_branch_exists` (no per-iteration branches in sequential mode)
- `check_correct_branch` now checks workstream branch instead of iteration branch
- 6 checks → 5 checks in check-iteration

**Learnings/emergent no longer gate-enforced (user decision):** Gate-post no longer checks for learnings or emergent entries. These are still available as agent commands (`add-learning`, `add-emergent`) but are purely optional. The prompt may still ask the agent to reflect after each AC — but there's no gate enforcement.

**SEQ_37-38 design discussion (pending, 2026-04-07):** Before implementing the phase-implement.md and phase-verify.md rewrites, do a design discussion covering:
- **High-level org audit:** What's the current structure, what works, what doesn't?
- **Minimize agent wandering:** Everything should be a clear, short checklist. Agents should never wonder "what do I do next?" — the reference file should be a sequence of steps, not prose to interpret.
- **Old script names:** Both files still reference the old 14-script names (pre-SEQ_12 rename). Must update to 3-entry-point model (`plet_agent.py`, `plet_orchestrator.py`, `plet_tools.py`).
- **Per-AC reflection:** Fold into the per-AC flow inline (after update-criterion, before wip-commit) rather than the current generated prompt section (SEQ_31). May drop the generated prompt section entirely — the commands are already in the CLI quick reference.
- **update-activity:** May need to bring back as an agent-facing command. Currently moved to orchestrator at phase-start, but agents may need to signal what they're doing (e.g., "reading context", "writing tests", "running tests"). Revisit whether the overhead is worth the observability.
- **Cheatsheet inline:** cli-cheatsheet.md content gets inlined into both files (SEQ_39 removes the separate file).

### NOTES_PLAN_IDR: PLAN_IDR — Iteration ID Rename

**Decision (2026-04-07): Rename `ID_` prefix to `ITR_`, deferred until before PLAN_SUB.**

**Problem:** `ID_` is too generic for target projects. In a real codebase, developers have database IDs, CSS IDs, DOM element IDs, etc. Grepping for `ID_` in a target project produces noise. `ITR_001` is ambiguous outside the plet context.

**Why `ITR_`:** Unambiguous, plet-specific, short. `IT_` is overloaded (IT as in "information technology"). `ITER_` is longer than necessary. `ITR_` is the sweet spot.

**Why defer:** The rename touches the entire system — scripts, ~1030 tests, reference files, PRD, state file names (`ITR_NNN.json` → `ITR_NNN.json`), branch names, commit messages, audit tags, `util_id.py` validation, case studies, PLAN.md, NOTES.md. Large sweep for a cosmetic change that doesn't cause functional issues today. The friction becomes real when subplets (PLAN_SUB) bring multi-project scenarios where external developers work alongside plet in the same repo.

**Approach:** Sweep-level consistency pass. The rename is mechanical — no judgment calls, just find-and-replace with verification. But the volume is high, so it needs a systematic inventory.

**Emergent ID format unaffected:** `EM_{iter_id}_{N}` (e.g., `EM_ITR_001_3`) remains unambiguous because each subplet has its own `emergent.md`. No cross-subplet collision.

**Timing:** Before PLAN_SUB, after PLAN_SEQ. The sequential simplification reduces the surface area (fewer branch/worktree references), making the rename cheaper.

**Scoping decisions (2026-04-08):**

Surface area audit: 7 literal `"ITR_NNN"` in scripts, 1174 in tests, 430 `iter_id` variable references (no change — variable name stays), 5 reference files, PRD, specs. ~1200 total renames.

- **Historical artifacts left as-is.** Case studies and historical NOTES document runs that used `ID_` prefix. Rewriting history adds no value. Only active/forward-looking content is renamed (scripts, tests, reference files, SKILL.md, PRD, specs, active NOTES sections).
- **Category-by-category execution.** Scripts first (7 literals, verify green), then util_id/util_state (validation regex), then tests (bulk 1174), then docs. Multiple commits, each verified green. Smaller commits make breakage debuggable.
- **Hard cut, no transition period.** `ITR_` only — no dual-accept regex. All consumers are in this repo. No external API to worry about.
- **State file names: pattern only.** `ITR_001.json` → `ITR_001.json` in script path derivation code. Actual files in target projects are created fresh each run — no migration needed.

### NOTES_PLAN_RFT: PLAN_RFT — Refactor Loop

**Decision (2026-04-05): Milestone-boundary refactor via synthetic iteration.** When all iterations in a milestone reach `complete`, the orchestrator injects a synthetic refactor iteration before promoting the next milestone's iterations to eligible.

**Why milestone boundary (not per-iteration or periodic):**
- Cross-cutting refactoring needs full codebase context — no single iteration's agent can see patterns like "16 scripts have duplicate helper functions"
- Milestones are natural integration points — all pieces of a feature set are done
- Avoids wasting time refactoring code that's still evolving
- Matches how we actually did PLAN_CLN — waited for all scripts to be migrated, then swept

**Why not part of verify:** Verify's job is checking correctness against acceptance criteria. Refactoring is about improving the codebase that's already correct. Different goals, different context needs. Verify sees one iteration; refactor needs to see everything.

**Design sketch:**
- Synthetic iteration: `ITR_RFT_1`, `ITR_RFT_2`, etc. — one per milestone
- Not in the original dependency map — injected by orchestrator when milestone completes
- Implement phase: agent audits codebase for patterns, inconsistencies, tech debt. Applies fixes. Runs tests.
- Verify phase: agent checks that all tests pass, no regressions, refactoring was mechanical (no behavior changes)
- Acceptance criteria: generated from emergent items tagged as tech-debt, plus automated quality checks (lint, complexity, coverage)
- If refactor iteration fails verify: block it like any other — human reviews in refine

**Decision (2026-04-05): Milestones as native execution barriers.** Milestones are not cosmetic groupings — they're integration points. Every iteration in MS_2 implicitly depends on all of MS_1 being complete (plus any explicit within-milestone deps). This eliminates cross-milestone parallelism by design: you don't start building MS_2 features on an un-integrated, un-refactored MS_1 foundation.

The refactor iteration (`ITR_RFT_1`) is the last iteration in each milestone. All MS_2 iterations depend on it. The dependency map encodes this — the orchestrator doesn't need milestone awareness, it just follows the DAG.

**Implication for plan phase:** Milestone definition becomes a first-class design decision, not a labeling step. The plan phase must guide users to define milestones as self-contained, buildable increments:
- Each milestone should be a coherent feature set that integrates as a unit
- Don't split tightly coupled work across milestones (creates artificial barriers)
- Milestone boundaries are stable interface points — within a milestone, things evolve; at the boundary, everything is clean
- The refactor pass at each boundary enforces this

**Implementation:** Plan phase generates the dependency map with milestone barriers:
1. Within-milestone deps: explicit, per-iteration (same as today)
2. Cross-milestone deps: implicit barrier — all MS_N+1 iterations depend on ITR_RFT_N
3. Refactor iteration added to each milestone during plan decomposition
4. User reviews refactor iterations alongside regular ones

The orchestrator changes zero — it sees the DAG and follows it. The streaming loop, parallel execution, breakpoints all work unchanged.

**Resolved questions (2026-04-05):**

**Q: Refactor agent access to learnings/emergent?** A: Agent reads both files as part of its audit (same way it reads the codebase). NOT injected into prompt by orchestrator. The phase-refactor.md reference file tells the agent to read them. Agent triages what's relevant.

**Q: Refactor budget?** A: Single attempt — one implement + one verify. Block if verify fails. Trivial fix-ups (typos, missed imports) handled in-place during the single attempt, same as verify's fix-in-place pattern. If verify fails, human reviews in refine. Refactoring shouldn't spiral.

**Q: Minimum milestone size?** A: Always included. The refactor looks at the entire codebase, not just the milestone's iterations. Even a single-iteration milestone might reveal patterns in older code. User can remove `ITR_RFT_N` during plan review if not needed.

**Q: Acceptance criteria generation?** A: Three layers:
1. **Refactor goals** — defined once during plan phase, project-level. Defaults (ruff clean, McCabe ≤15, coverage holds, all tests pass) plus user-specified goals ("files under 300 lines", "consistent error handling", "extract shared patterns when 3+ duplicates"). These apply to every refactor iteration.
2. **Agent-proposed ACs** — the refactor agent reads the codebase + emergent.md + learnings.md, proposes specific ACs ("I'll extract the duplicate handler pattern in cmd/"). Verify checks these.
3. **Emergent pipeline** — things the refactor notices but shouldn't fix go into emergent.md ("this pattern will get worse when MS_3 adds more subcommands"). Refine session triages them into the next refactor's goals or a dedicated iteration. Closes the loop: emergent → refactor goals → refactor → emergent.

**Q: Is "refactor" a new phase?** A: Yes — `--phase refactor` everywhere. Different reference file (phase-refactor.md), different AC patterns, different prompt. Clean separation from implement/verify.

**Q: Refactor iteration structure?** A: `refactor → verify`, not `implement → verify`. Refactor replaces implement as phase 1. Verify is always phase 2 (checks the work). Regular iterations: implement→verify. Refactor iterations: refactor→verify.

**Q: Verdict fields?** A: Two booleans, not an enum. Refactor can't block — it always completes (worst case: revert changes, file emergent items).

```json
{
  "refactorChanges": true,   // did code change?
  "refactorDeferrals": true  // were emergent items filed for refine?
}
```

Orchestrator routing:
- `refactorChanges: true` → verify phase (check the changes)
- `refactorChanges: false` → skip verify, mark complete (nothing to check)
- `refactorDeferrals` is informational — doesn't affect routing

A refactor that breaks tests reverts all changes, sets `refactorChanges: false`, files everything as emergent (`refactorDeferrals: true`). The refine session handles it.

**Q: Time budget?** A: Explicit, defined per-project in plan phase. Stored in refactor iteration state. Default TBD (maybe 20 min). Orchestrator passes to invoke. If agent hits limit: revert uncommitted changes, file remaining as emergent, set `changes: false, deferrals: true`.

**Taxonomy update:**
- Phase values: implement, verify, refactor (3 total)
- Lifecycle states: implementing, verifying, refactoring (3 gerunds)
- Verdict fields: implementVerdict, verifyVerdict (enums); refactorChanges, refactorDeferrals (booleans)
- Attempts: attempts.implement, attempts.verify, attempts.refactor (3 counters)
- Reference files: phase-implement.md, phase-verify.md, phase-refactor.md (3 files)

**Plan phase presentation decisions (2026-04-05, partially resolved):**

1. **When introduced:** During milestone definition (Step 5), right before milestones — natural integration point.
2. **Refactor goals:** Defaults + user-specified. Defaults are pattern-oriented + artifact-oriented (not quality ratchets — those are already enforced by linter/test suite). Discussion ongoing about exact defaults. Quality ratchet items (ruff clean, McCabe, coverage) don't belong as refactor goals — they're NFRs.
3. **Where goals live:** New section in requirements.md — "Refactor Policy and Goals", placed before milestone definitions. Refactor iterations in iterations.md reference the policy.
4. **Removable:** Yes — user deletes `ITR_RFT_N` during review like any iteration. No special mechanism.
5. **Presentation:** Grouped summary — all refactor iterations presented together at the end, not interleaved. Needs real-run validation.
6. **Placement in requirements.md:** Still open — between §4.5 and §5 (quality-adjacent) vs before §9 (milestone-adjacent). Leaning toward quality-adjacent but not decided.

**Default refactor goals (2026-04-05, decided):**

Pattern-oriented:
1. Extract duplicated logic when 3+ copies exist across files
2. Flag files over 500 lines for review — split only if there's a clear seam (not just because it's long)
3. Consolidate scattered constants/config into centralized locations
4. Reduce excessive special-case branching (if/elif chains that grew organically across iterations)

Artifact-oriented:
5. Review emergent.md for deferred cleanup items
6. Review learnings.md entries from at least this milestone's iterations
7. Audit high-churn files (via `git_check.py churn` command — new, detects files touched by many iterations)

Rejected: quality ratchet items (ruff, McCabe, coverage) — already enforced by linter/test suite, not refactor goals. Deep nesting / high complexity — same, linter job.

Note on #7: `churn` command added to PLAN_RFT scope — natural home in git_check.py which already does git analysis. Lists files by commit count since workstream start, flags outliers.

**Still open:**

1. **§Refactor Policy placement in requirements.md.** Between §4.5 and §5 (quality-adjacent) vs before §9 (milestone-adjacent). Leaning quality-adjacent.

#### NOTES_PLAN_RFT_SIMPLIFY: Simplification (2026-04-08)

**Decision: Don't create a new phase — use implement→verify with a different reference file.**

The original design proposed `--phase refactor` as a third phase with its own lifecycle state (`refactoring`), custom verdict fields (`refactorChanges`/`refactorDeferrals` booleans), custom orchestrator routing (skip verify if no changes, auto-revert on failure), and schema changes across 5+ modules. PLAN_SEQ taught us that every piece of infrastructure has to be maintained, tested, and debugged through real runs. The parallel orchestrator looked right on paper and took months to prove it didn't work. Simpler won every time.

**Refactor iterations are implement→verify iterations with a different reference file.** A refactor iteration IS an implementation iteration — the agent audits, fixes, and tests, then verify checks the work. The difference is the *guidance* (what the agent looks for), not the *lifecycle*.

Concrete mechanism:
- `ITR_RFT_1` is a normal iteration in the dependency map
- `prompt.py` detects the `ITR_RFT_` prefix and injects `phase-refactor.md` instead of `phase-implement.md`
- Standard `implementVerdict: completed|blocked`, standard lifecycle, standard gate
- The verify agent follows normal `phase-verify.md`

**What this eliminates:**
- No new `--phase refactor` value (no validator changes, no gate changes, no trace changes, no entries changes)
- No new `refactoring` lifecycle state
- No `refactorChanges`/`refactorDeferrals` custom verdict fields
- No schema migration
- No custom orchestrator routing (skip verify, auto-revert)
- No time budget mechanism
- No "refactor can't block" special case — blocks like any other iteration, human reviews in refine

**Standard verdicts, not custom booleans.** The `refactorChanges`/`refactorDeferrals` pair was information that's already observable: "Did code change?" = `git diff`. "Were deferrals filed?" = count of emergent entries. Use standard `implementVerdict: completed|blocked`.

**Separate milestone barriers from refactor iterations.** Two independent features:
1. Milestone barriers — all MS_2 iterations depend on all MS_1 being complete. Pure dependency graph change at plan time. No scripts, no phases.
2. Refactor iterations — synthetic iteration at each barrier with refactor guidance.

Build (1) first. It's independently valuable. Then (2) is just adding `ITR_RFT_N` iterations to the plan with the right deps.

**Refactor goals should be minimal at plan time.** One AC per goal: "Extract duplicated logic when 3+ copies exist." The refactor agent discovers specifics at runtime by reading the codebase. Over-specifying plan-time ACs constrains the agent before it's seen the code.

**Refactor can block (single attempt).** Simplest flow: if verify fails, it blocks like any other iteration. Human reviews in refine. No special revert-and-file-emergent mechanism. This is the normal flow — no special handling needed.

**Build churn command first.** `plet_tools.py churn` is independently useful, low-risk, gives the refactor agent concrete data, and a human can run it after any loop.

**No time budget mechanism.** Adds testing burden for marginal value. Agents have natural context limits. If too large, agent blocks. Human reviews in refine.

**Estimated effort:** ~2 days vs ~2 weeks for the original design. Most of the work is writing `phase-refactor.md` (the reference file). The prompt routing is ~5 lines. Milestone barriers are plan-phase guidance + dependency generation.

#### NOTES_PLAN_RFT_CHURN: Churn Analysis of plet-skills (2026-04-08)

Ran `churn` on the plet-skills repo itself to validate the tool and see what it reveals.

**Finding: churn in this repo is sweep-driven, not structural.** The two script outliers (`prompt.py` at 9, `iter_state.py` at 7 commits since PLAN_SEQ start) were touched by the same cross-cutting sweeps: PLAN_SEQ rename, PLAN_IDR rename, version centralization, schema deprecation. Not "god objects that keep getting patched" — files that contain things every sweep touches (enum values, help text, version strings).

**Finding: size is a better signal than churn for this codebase.** Largest scripts: `fingerprint.py` (1203), `iter_state.py` (1185), `gate_session.py` (1049), `traces.py` (825). Each is self-contained — many commands but each command is independent. The only marginal candidate for extraction is `gate_session.py`'s preflight check suite, which is a long sequential list that could become its own module. Cosmetic, not urgent.

**Implication for phase-refactor.md:** The churn command is more useful for target projects (where agents accumulate tech debt across iterations) than for plet-skills itself. The reference file should guide agents to look at churn output as a starting point, but not rely on it exclusively — size, complexity, and pattern signals (from NOTES_PLAN_RFT Tier 2 heuristics) are complementary.

#### NOTES_PLAN_RFT_HEURISTICS: Sweep/Refactor Heuristics (2026-04-08)

**Archaeology of 228 commits touching scripts/.** Categorized every commit to identify what caused us to refactor and what signals preceded each effort. 87 commits (38%) were refactoring/sweeps, 87 (38%) new features, 50 (22%) maintenance (bug fixes, version bumps, docs).

**The 7 sweeps/refactors that happened (chronological):**

1. **Ruff Introduction** (10 commits, v0.4.2). No linting existed. First real run (LOGA R5) surfaced code quality issues during debugging. Added ruff, incrementally lowered McCabe threshold (30→25→20→15). 720 errors on first pass.

2. **PLAN_COV — Convention Migration** (17 commits, v0.4.4). Scripts printed to stdout directly — couldn't capture output for testing. Tuple return convention `(code, stdout, stderr)` across all 17 scripts + dispatch layer. Prerequisite for measurable coverage.

3. **PLAN_CLN — Script Cleanup** (11 commits, v0.5.0). After all 14 scripts were built, inconsistencies were visible across the whole set. 5 different validator return patterns, 16 duplicate `help_hint` functions, `emit_error` defined 3 times, dead code from early experiments. Each script was built independently following specs — inconsistency was invisible during serial construction.

4. **Lifecycle Extraction** (12 commits, v0.4.0). LOGA R3: worktree state divergence bug. Per-iteration state files had lifecycle fields that the orchestrator also modified, causing merge conflicts. Root cause: two writers (orchestrator + subagent) modifying the same field in the same file.

5. **PLAN_RBS — Rebase over Squash** (22 commits, v0.6.0-0.6.2). LOGA R9-R11: merge-squash failures across 3 consecutive runs with different symptoms. R9: dirty tree. R10: CONFLICT on stdout not stderr. R11: state file corruption from undetected conflict markers in JSON. Each fix patched one symptom; the root cause was the merge-squash strategy itself.

6. **PLAN_SEQ — Sequential Simplification** (10 commits, v0.7.0). R09-R14 data: parallel never achieved the theoretical 46% speedup. 69-71% completion rates vs 100% sequential. Stripped ThreadPoolExecutor, worktrees, iter branches, conflict recovery. Consolidated 14 scripts → 3 entry points. Decision driven by quantitative metrics across 6 case study runs.

7. **PLAN_IDR — ID Rename** (3 commits, v0.7.0+). Proactive: anticipated grep noise when subplets bring multi-project scenarios. `ID_` too generic. Cheap after PLAN_SEQ reduced the surface area.

**Identified 7 recurring heuristics that triggered refactoring:**

| # | Heuristic | Trigger Signal | Fix or Emergent? |
|---|-----------|---------------|------------------|
| 1 | First real run surfaces hidden debt | Case study finds issues prose reviews missed | Fix (run linter/coverage as first audit action) |
| 2 | Testing infrastructure can't reach the code | Coverage gaps, untestable patterns | **Emergent** (architectural judgment needed) |
| 3 | All components built, cross-cutting inconsistency visible | N scripts with N patterns for the same operation | Fix (grep for duplicates, align) |
| 4 | Runtime bug from shared mutable state | Two writers, one file, no clear owner | **Emergent** (ownership boundary decision) |
| 5 | Repeated failures in the same subsystem | learnings/emergent mention the same file 3+ times | Fix (investigate and address root cause) |
| 6 | Quantitative data showing feature doesn't deliver | Metric comparison shows overhead > benefit | **Emergent** (requires human decision to remove/replace) |
| 7 | Naming ambiguity / grep noise | Identifiers collide with unrelated code | **Emergent** (rename scope requires human approval) |

**Decision: Heuristics 2, 4, 7 are emergent-only in refactor iterations.** The refactor agent should detect these signals (run coverage, look for shared state, grep for collisions) and file emergent items, but not fix them. They require architectural judgment that belongs in refine. Added as "Emergent-Only Signals" (signals 8-10) in phase-refactor.md.

Heuristics 1, 3, 5 are directly actionable by the refactor agent — they map to the existing signal categories in phase-refactor.md (run toolchain, grep for duplicates, check learnings/emergent).

#### NOTES_PLAN_RFT_REVIEW: phase-refactor.md Evaluation (2026-04-08)

Evaluated phase-refactor.md using skill-creator evaluation framework. 11 findings, 6 changes made. Key decisions:

**`--phase implement` confusion (finding 11, medium).** Refactoring iterations use `--phase implement` despite the file being titled "Refactoring Iteration." Added explicit note: "This iteration uses `--phase implement` — the refactoring difference is in the guidance, not the lifecycle."

**Real-time state updates (finding 1, medium).** Both phase-implement.md and phase-verify.md have a critical rule about updating state in real time for external consumers. phase-refactor.md was missing it. Added.

**What "mechanical" means (finding 6, medium).** "Keep it mechanical" was undefined. Clarified: "Mechanical means the before and after are functionally identical — same inputs, same outputs, same side effects. If you need to think about whether the behavior changes, it's not mechanical — defer it."

**Linter/formatter at start (finding 9, removed).** The implement phase already ran formatter + linter as final checks, and verify's gate confirmed it. Code arrives clean at the refactor iteration. Removed the redundant step from "Before You Start" — only the "Completing the Phase" run matters (catches issues introduced by the refactor agent's changes).

**Test count invariant (finding 8, revised).** "Test count hasn't decreased" is wrong as an invariant. Legitimate refactoring can decrease count: redundant tests consolidated, parameterized tests replacing copy-paste, tests for extracted code replaced by tests for the new location. The real invariant is "coverage doesn't decrease" but coverage isn't always available. Revised to: "If test count decreased, document why (consolidated, removed redundant, etc.). If coverage measurement is available, verify coverage held or improved."

**Survey timing (finding 3, low).** "5-10 minutes" is meaningless to an agent. Changed to action-scoped: "Read these three sources. Note relevant items. Don't fix anything yet."

**Ordering caveat (finding 4, low).** Added: "If your acceptance criteria include only one signal type, order doesn't matter."

**Gate check list (finding 10, low).** Added to Completing the Phase so the agent knows what `phase-end` will verify.

#### NOTES_PLAN_RFT_REVIEW_IMPL_VERIFY: phase-implement.md + phase-verify.md Evaluation (2026-04-08)

Evaluated both files using skill-creator framework. 15 total findings across both files + cross-file consistency. 7 changes made.

**phase-implement.md changes:**
- (Finding 2) "Orchestrator-managed" context → "Also read" — agent should always read requirements.md
- (Finding 4) Added note: update-criterion auto-generates progress entries
- (Finding 5) **state.json contradiction resolved.** "Do NOT modify state.json" vs "Add missing dependency to dependencyMap." Decision: Option B — agent files emergent + blocks, human fixes DAG in refine. Agent never modifies orchestrator-owned state. Rewrote Missing Dependency section (IMP_24).
- (Finding 6) Stale gate check list removed learnings/emergent WARN (removed in PLAN_SEQ)

**phase-verify.md changes:**
- (Finding 8) Added "Never create merge commits" critical rule
- (Finding 10) Added *why* for "no implementation code" rule — separation ensures independent verification of the fix
- (Finding 11) Evidence comparison "update accordingly" → explicit: change status from pass to fail with discrepancy evidence

**Not changed (acceptable):** orchestrator-managed framing (finding 2 — partially addressed), status summary anchoring bias (finding 9 — workable), retry re-verify (finding 12 — edge case), no verify Failed Attempt Protocol (finding 13 — verify rarely hits context limits).

---

Autonomous agents accumulate tech debt iteration by iteration — each implementation subagent optimizes locally for its acceptance criteria without seeing the broader codebase trajectory. Regular refactoring should be built into the loop to mitigate this.

Options explored:
- **Refactor step within each iteration:** After verify passes, a brief refactor pass before marking complete. Lightweight but frequent.
- **Periodic refactor phase:** A dedicated refactor iteration injected every N iterations (e.g., every 3-5). Heavier but catches cross-iteration debt.
- **Refine-triggered refactor:** The refine session surfaces tech debt from learnings/emergent items and creates refactor iterations. Already partially supported — emergent items can capture "this code needs cleanup" — but not formalized.
- **Milestone boundary refactor:** A refactor pass at the end of each milestone before moving to the next. Natural checkpoint. ← **Selected.**

Key questions:
- Should refactoring have its own reference file (like execute.md but for cleanup)?
- How does a refactor iteration define acceptance criteria? ("Code is cleaner" is not verifiable.)
- Does the verify agent already catch some of this via code quality review? If so, is a separate phase redundant?
- Should refactor iterations be auto-generated or human-approved during refine?

**Hard invariant: No refactoring unless all tests pass green.** Refactoring without green tests is rearranging code you can't verify. Regression risk is too high.

**Debug number exception to magic numbers rule:** 12-digit debug number literals (PL_DX_2) must NOT be flagged as magic numbers or hardcoded values. They are intentionally unique hardcoded constants — grepping the codebase for any debug number must return exactly 1 result. Never generate debug numbers at runtime (e.g., `random.randint`). One-liner to generate: `head -c 16 /dev/urandom | shasum | tr -cd '0-9' | cut -c1-12`

**Two-tier refactoring model:**

**Tier 1: Per-loop minor refactor** — cheap, obvious, local scope. Things any competent developer would clean up before committing. Handled by the implementation/verify agents as part of normal loop work, not a separate phase.

- Very large or complex functions/modules/files (contextual thresholds — a 200-line parser may be fine, a 200-line controller is a red flag)
- Functions/methods with high cyclomatic complexity or deep nesting
- Tests requiring excessive setup or mocking (coupling smell)
- Tests breaking across iterations that didn't directly touch that area (fragile coupling)
- Growing parameter lists (introduce options/config object, or question whether the function does too much)
- Unused imports/variables/dead code within touched files
- Magic numbers or hardcoded values that should be named constants (exception: 12-digit debug number literals per PL_DX_2)
- Inconsistent error handling within touched files (new pattern doesn't match existing)
- Placeholder comments (`// TODO`, `# FIXME`) left by the agent — should never survive past verify
- Generic error handling (catching all exceptions, swallowing errors, `except Exception: pass`)
- Missing resource cleanup (file handles, DB connections, temp files not closed)
- Inefficient patterns (local: N+1 queries, unnecessary copies, O(n²) where O(n) is obvious)
- Race conditions (obvious: shared mutable state without synchronization in one file)

**Tier 2: Milestone boundary full refactor** — signals that require cross-iteration perspective. Triggered when all iterations in a milestone reach `complete` (tests green by definition). Full analysis across all heuristics before starting the next milestone. Produces proposed refactor iterations that go through the normal loop (acceptance criteria, verify, the whole process).

Design signals (require judgment):
- **Excessive special cases** — the signature autonomous agent smell. Each iteration adds an `if` branch. After 5 iterations, you've got a function of special cases that should be a cleaner abstraction. Detectable: conditional branch count, `if type == "X"` / `elif type == "Y"` chains, switch-like structures that grew organically.
- **Code or logic at the wrong conceptual level** — business logic in utility functions, presentation logic in data layers, infrastructure concerns in domain code. Agent checks against `requirements.md` which defines the intended architecture.
- **Abstraction opportunities** — multiple iterations independently wrote similar helpers. Only visible when you look across all of them.

Structural signals (cheap to detect):
- Duplicate or near-duplicate code across files touched by different iterations
- High-churn files (touched by many iterations = likely god object or kitchen-sink module)
- Import tangles — circular dependencies, modules importing from too many places
- API surface area creep — modules exposing too many public functions/methods across iterations (module boundary is wrong)
- Configuration/constants scattered across files that should be centralized

Pattern signals (from plet's own artifacts):
- `learnings.md` entries mentioning the same file or module repeatedly
- `emergent.md` items about workarounds or inability to cleanly separate concerns
- Multiple iterations modifying the same function/class
- Verify agents flagging code quality issues that suggest deeper structure problems

Cross-iteration accumulation signals (verify catches these per-iteration, but accumulation across iterations is a refactoring signal):
- Placeholder comments accumulating across the codebase
- Generic error handling patterns spreading
- Inefficient patterns (systemic: every iteration repeats the same expensive operation that should be cached at a higher level)
- Hidden coupling — cross-iteration implicit dependencies not in the import graph. Module A works fine until module B changes because they share assumptions.
- Race conditions (emergent: multiple iterations independently added concurrent access to the same resource)
- Missing resource cleanup patterns spreading across modules

Convention drift signals:
- Inconsistent naming across iterations (mixed `snake_case` / `camelCase` for similar things)
- Mixed patterns for the same operation (different error handling strategies, etc.)
- Dead code left behind by iterations that changed direction

Test signals:
- Test files that became catch-alls (each iteration appended to the nearest test file rather than organizing by concern)
- Test files growing faster than implementation files

**Escape hatch:** The refine session can create refactor iterations mid-milestone if the human or learnings surface something urgent ("this module is becoming unmaintainable"). Same hard invariant applies — tests must be green.

Not a v1 blocker — the current verify phase catches obvious code quality issues — but worth designing in before tech debt compounds across real usage.

### NOTES_PLAN_VER: PLAN_VER — Verify Phase Evaluation

**Decision (2026-04-07): VF_7-11 split between verify and refactor.** The five quality-gate sections in phase-verify.md (VF_7 Spec Fidelity, VF_8 Test Quality, VF_9 Code Quality, VF_10 Security Surface, VF_11 Spec Gaps) are a code-review checklist that agents mostly ignore. R05 transcript analysis: agents gave single sentences ("No security concerns") or skipped entirely.

Split by natural home:
- **Stay in verify:** VF_7 (Spec Fidelity) — this IS verification. VF_11 (Spec Gaps) — directly spec-related.
- **Move to phase-refactor.md (PLAN_RFT):** VF_9 (Code Quality) — cross-cutting codebase health, not per-AC verification. Already covered by PLAN_RFT Tier 1 (per-loop minor refactor) and Tier 2 (milestone boundary) heuristics.
- **Split:** VF_8 (Test Quality) — "tests actually test the AC" stays in verify; "test suite is well-designed" moves to refactor. VF_10 (Security) — AC-relevant security stays in verify; broad security audit moves to refactor.

**Rationale (from NOTES_PLAN_RFT):** "Verify's job is checking correctness against acceptance criteria. Refactoring is about improving the codebase that's already correct. Different goals, different context needs. Verify sees one iteration; refactor needs to see everything."

**Evidence (OLLR R05 transcripts):** Verify agents naturally do functional verification well — independently run code, compare to spec, check tests aren't tautological. They don't do broad code quality audits. Lean into the strength instead of asking them to also be code reviewers.

**Decision (2026-04-07): Collapse Anti-Slop Bias (VF_12) + Convergence Signal (VF_13) into single "Verification Rigor" section.** Both sections pulled in opposite directions ("assume debt" vs "approve if cosmetic"). With VF_9 moved to refactor, the "hidden debt" framing belongs there. Verify's rigor is: confirm AC are genuinely satisfied, not just that tests pass. Approve when all AC are confirmed. No broad code quality audit.

**Decision (2026-04-07): Result-first verification becomes the main loop structure.** Per-criterion workflow: (1) independently verify the AC (run code, read source, compare to spec — absorbs VF_7 Spec Fidelity), (2) check the test isn't tautological (kept from VF_8), (3) flag spec gaps if found (kept from VF_11), (4) update-criterion with evidence. This matches what agents actually do well in practice (R05 transcripts). Separate sections for VF_7/VF_8/VF_11 collapse into inline steps of the per-criterion loop.

**Decision (2026-04-07): Remove fix-in-place (Path B) entirely.** Verify agent never writes implementation code. Two paths only: approve (all AC pass) or cycle back (write failing tests, hand off to implement). Rationale: (1) clean verify/implement separation — no gray area about what's "small enough," (2) strengthens the red test handoff pattern (verify writes failing test, implement makes it green), (3) fix-in-place was never used across R01-R05 — zero practical frequency, (4) simplifies phase-verify.md by removing an entire decision branch. If cycle-back overhead proves painful in future runs, reintroduce with concrete criteria (under ~20 lines, additive only, no logic changes).

**Decision (2026-04-07): Remove Artifact Audit (VF_20) from phase-verify.md.** Artifact completeness is already enforced by phase-end gate checks (progress entry FAIL, learnings/emergent WARN). Verify agent checking the same things manually is redundant. R05: zero agents performed this. "Log but continue" means no teeth. Gate is the enforcement mechanism, not agent behavior.

**Decision (2026-04-07): Add per-criterion-type verification guidance.** Short table mapping criterion types (behavioral, structural, negative, documentation, integration) to verification approaches. Not prescriptive — agent uses judgment to pick the most practical method or combination. Keeps it under 10 lines. Agents already do this intuitively (R05: ran commands for behavioral, read source for structural); writing it down makes it consistent.

**Decision (2026-04-07): Verify-first, evidence-after ordering.** The verify agent does NOT read the per-iteration state file (implementation evidence) before verifying. Prompt injects only a status summary (AC_1 [pass], etc.), not evidence text. The agent reads iterations.md + requirements.md + source code, verifies each AC independently, then reads the full state file ONCE after all criteria are verified to compare findings against implementation evidence and note discrepancies. This preserves true independence — reading evidence first biases verification.

**Decision (2026-04-07): Move pre-flight checks out of verify.** In sequential mode, implement's phase-end gate already verifies tests pass, git clean, etc. Code hasn't changed between implement-end and verify-start. Verify trusts the gate passed. Removes redundant work.

**Decision (2026-04-07): Remove verify-start wip-commit.** Matters less with sequential execution. Audit tags + update-activity cover the same ground.

**Decision (2026-04-07): No git history review in verify.** "Verify the result, not the process" (VF_2) is a core principle. Git history is process. If the code is correct and tests pass, how it got there doesn't matter for verification.

**Decision (2026-04-07): Phase-end as paragraph, not checklist.** The verify agent doesn't care what phase-end does internally. Present as: "Call phase-end. It handles verdict, report, gate, commit, audit tag. If it fails, fix and retry." Keep the explicit example with --verdict, --summary, etc.

**Decision (2026-04-07): Evidence comparison deferred to after per-criterion loop.** Agent reads the state file once after all criteria are independently verified, compares all findings at once, notes discrepancies. Avoids awkward "read only AC_1's evidence" per-criterion and matches how agents actually read files. Section titled "After All Criterion Workflows Complete."

**Proposed phase-verify.md outline (2026-04-07):**

```
# Verify Phase — Verification Subagent

## Preamble
   ~4 critical rules: autonomous, real-time state updates,
   result not process (VF_2), no git stash

## Agent Tool
   plet_agent.py — 6 commands table (update-activity added)
   CLI lookup: --usage first, --help if needed

## Branch/State Context
   Workstream branch, sole writer, don't modify state.json

## Before You Start
   ### Set Up State
      update-activity setup / "reading context"
      (no verify-start wip-commit — removed)
   ### Read Context
      CLAUDE.md, README.md, iterations.md, requirements.md,
      learnings, emergent.
      Do NOT read the per-iteration state file yet — preserve
      independence for the verification pass.
      (no pre-flight — moved to implement, verify trusts the gate)

## Independent Verification (MAIN LOOP)
   ### Verification Rigor (collapsed VF_12 + VF_13)
      Confirm AC genuinely satisfied, don't rubber-stamp.
      "The prompt includes a status summary from implementation.
      Verify each criterion independently regardless of listed status."
   ### Criterion Type Guidance
      Table: behavioral (run + compare), structural (read source,
      trace logic), negative (trigger error path), documentation
      (read file, check content), integration (exercise path).
      Agent uses judgment to pick approach or combine.
   ### Per-Criterion Workflow
      For each AC:
      1. update-activity "verifying AC_N: {description}"
      2. Independently verify (approach per criterion type)
      3. Check the test isn't tautological (from VF_8)
      4. Flag spec gaps if found → emergent (from VF_11)
      5. update-criterion with evidence
         - Name what you ran/read and what you confirmed
         - Note the verification approach (behavioral, structural, etc.)
         - If FAIL: mark fail and continue — don't stop at first failure
      6. wip-commit

## After All Criterion Workflows Complete
   Read the full per-iteration state file. Compare independent
   findings against implementation evidence for each criterion.
   Note discrepancies — if implementation evidence describes
   behavior you didn't observe, update the criterion accordingly.

## Rejection Protocol (promoted from old Path C)
   Verify all criteria first, then for each failed criterion:
   - Write a failing test, confirm it fails against current code
   - update-criterion --status fail --red-test test_name
   - If not test-expressible: --red-test none --no-test-rationale "..."
   - New criteria for issues not in original AC: add with status fail
   Document in emergent (for human) + learnings (for next implement agent)
   phase-end --verdict rejected --summary "..."
   Verify writes TESTS only, never implementation code.

## Completing the Phase
   Write remaining artifacts (learnings, emergent).
   Paragraph: call phase-end with --verdict, --summary, --progress-content.
   Explicit example preserved. If it fails, fix and retry.

## Blocker Protocol (~10 lines, last resort)

## Runtime Artifact Writes
   learnings + emergent, as things come up, keep under 4KB

## Activity Updates (reference table)
   setup, running_checks, implementing (cycle-back red tests only),
   committing, wrapping_up

## Retry Awareness (short paragraph)
   Focus on previously-failed criteria. Don't re-verify criteria
   that already passed unless reason to doubt.

## Criteria Skip Rules (~5 lines)
```

**Additional outline decisions (2026-04-07):**
- Per-criterion workflow: if a criterion fails, mark it fail and continue verifying the rest. Don't stop at first failure — implement agent needs the complete picture.
- Rejection Protocol expanded: red-test handoff details preserved (--red-test test_name, --red-test none --no-test-rationale). Verify agent can add new criteria for issues not in original AC list (add with status fail, write failing test, cycle back).
- Verification Rigor: one sentence addressing prompt bias — "The prompt includes a status summary from implementation. Verify each criterion independently regardless of its listed status."
- Evidence guidance in step 5: "Name what you ran/read and what you confirmed. Note the verification approach."
- Pre-flight checks moved to implement phase (verify trusts the gate). No verify-start wip-commit.
- Phase-end presented as paragraph with explicit example, not checklist.
- Verify's "Final Checks" (formatter, linter, full test suite) correctly removed — with fix-in-place gone, verify never modifies implementation code. Approval: no code changes, implement gate already passed. Rejection: intentionally failing tests would be misleading in a full suite run.

**Decision (2026-04-08): Auto-emit update-activity from plet_agent.py dispatch.** R06 showed 79 explicit update-activity calls — agents comply well but it's overhead at every transition. Instead of the agent calling update-activity separately, inject it into `_dispatch_with_trace`: before each command runs, dispatch auto-sets phaseActivity based on the command name.

Auto-activity mapping:
- `update-criterion` → `running_checks` (detail derived from criterion arg)
- `wip-commit` → `committing` (detail derived from message arg)
- `phase-end` → `wrapping_up` (detail: "completing phase")
- `add-learning`, `add-emergent` → no activity change (minor operations)
- `update-activity` → skip (agent explicit call, no auto-emit)

Agent still explicitly calls update-activity for:
- `setup` — once at phase start ("reading context")
- `implementing` — during red/green steps ("red: writing failing test for AC_1", "green: implementing AC_1")
- `running_checks` — verify agent before each criterion ("verifying AC_1: description") — sets the detail string before the work starts; the auto-emit from update-criterion fires after

This cuts the explicit call surface from ~79 to ~20-25 per run (the meaningful transitions where the agent is announcing what it's ABOUT to do). The mechanical transitions (committing, wrapping up) happen automatically.

Implementation location: `plet_agent.py _dispatch_with_trace`, using PLET_DIR, PLET_ITER_ID, PLET_AGENT_ID env vars.

---

### NOTES_PLAN_MSV: PLAN_MSV — Milestone-Scoped Verify

Move verify from per-iteration to per-milestone. Instead of implement→verify for every iteration, run implement-only for all iterations in a milestone, then one verify pass at the milestone boundary that checks all ACs together — alongside or merged with the refactor iteration.

**Motivation — case study data across 24 runs:**
- Per-iteration verify has a ~96% rubber-stamp rate (~150 verify phases, 5 rejections total)
- The 5 catches were all integration gaps (missing modules, unwired functions, incomplete features) — exactly the kind of thing that's *more* visible at milestone scope when all pieces are in place
- Per-iteration verify costs 25-35% of loop time per run

**Why milestone scope may be better for catching integration gaps:**
- A per-iteration verify sees one piece in isolation — it can't see that module A calls module B which doesn't exist yet (B is a later iteration in the same milestone)
- A milestone verify sees the complete feature set together — wiring bugs, missing modules, and integration gaps are all visible
- The refactor iteration already sits at the milestone boundary with full codebase context

**Cost model — not a simple N→M reduction.** Per-iteration verify checks 3-5 ACs. Milestone verify would check a whole milestone's worth (15-25+ ACs). Per-verify cost goes up even as the count goes down. Net savings are real (fewer agent spawns, less bookkeeping overhead, less duplicate context loading) but the per-pass token cost will be significantly higher than a single per-iteration verify. Needs a real run to measure.

**Safety net:** The implement gate already runs tests and lint after every iteration. Outright breakage (failing tests, syntax errors) is caught immediately. What per-iteration verify would have caught — subtle integration issues — are better caught at milestone scope anyway.

**Risk — late discovery:** A broken AC isn't caught until milestone boundary, potentially 5-8 iterations later. Mitigation: the implement gate catches functional breakage; only subtle spec-compliance issues slip through. And those are exactly what a broader-context milestone verify catches better.

**Open questions:**
- Milestone verify overwhelmed by scope? 20+ ACs in one pass may exceed what a single agent does well. Mitigation: batch by iteration within the milestone pass, or prioritize cross-iteration integration ACs. Needs a real run to test.
- How does milestone verify report per-AC results? (One big report vs. per-iteration sub-reports)

**Status:** Design option, not decided. Needs a real run to compare per-iteration vs. milestone verify on the same project.

#### NOTES_PLAN_MSV_0: Milestone verify fixes in-place (2026-04-10)

**Decision:** Milestone verify fixes issues in-place (option C). Check all milestone ACs, fix problems found, report what was fixed. If something is too big to fix in-place, block the refactor iteration and the human triages in refine (fallback).

**Why this makes sense at milestone scope:** The "verify never writes code" principle was designed for per-iteration independence — preventing the verify agent from rubber-stamping by fixing its own implementation. At milestone scope that concern doesn't apply: the verify agent didn't write any of the code it's checking. It has full codebase context, it's already staring at the problem, and punting through a re-queue cycle is expensive for something the agent can fix directly.

**This makes milestone verify essentially a new kind of verify** — closer to a combined review-and-fix pass than the old read-only check. The verify/refactor distinction at milestone scope is: refactor improves code that's already correct; verify confirms correctness and fixes what isn't.

#### NOTES_PLAN_MSV_1: Core insight — verify's value is at integration boundaries (2026-04-10)

Every real catch across 24 case studies was an integration gap — missing modules, unwired functions, incomplete features. These are *more* visible when you can see the whole milestone together, not less. Per-iteration verify is checking the wrong scope for the only class of bugs it catches.

#### NOTES_PLAN_MSV_2: SPARK reanalysis — even the hardest case supports milestone scope (2026-04-10)

SPARK R01 is the strongest argument for per-iteration verify (4 rejections, 17% rate — dramatically higher than other projects). But examining the specific catches:
- ID_013 (missing `PubSubHelper`) — integration gap, caught better at milestone scope
- ID_015 (AC_5 incomplete) — integration gap, caught better at milestone scope
- ID_007 (lost commits) — impl/git issue, not a verify catch at all
- ID_005 — unspecified

2 of 4 rejections would have been caught at milestone scope. The case for per-iteration verify is weaker than it looks even in the hardest scenario.

#### NOTES_PLAN_MSV_3: Refactor iteration already provides the infrastructure (2026-04-10)

No new "milestone verify" needed. The refactor iteration at every milestone boundary already runs implement→verify. The gap: its verify checks the *refactor work*, not the original ACs.

**Smallest possible change:** Expand the refactor iteration's verify scope to include spot-checking ACs from the milestone's iterations, not just the refactor changes. No new infrastructure, no new phases, no new schema. Just a reference file update.

#### NOTES_PLAN_MSV_4: Cost model — savings are real but not linear (2026-04-10)

A milestone verify checking 15-25 ACs is a bigger job than one checking 3-5. Per-verify cost goes up even as the count goes down. But real savings exist beyond AC checking time:
- **Agent spawn overhead** — each per-iteration verify loads CLAUDE.md, PLET.md, reference files, state, iteration file. ~30-40% of verify time regardless of AC count (R16: 52% of verify tool calls were bookkeeping)
- **Git operations** — each per-iteration verify does its own commit/squash cycle
- **Orchestrator round-trips** — dispatch, wait, read verdict, transition lifecycle

Even if milestone verify takes 3x longer checking ACs, heavy savings on infrastructure overhead that currently multiplies across every iteration.

#### NOTES_PLAN_MSV_5: Risks assessed (2026-04-10)

**Compounding subtle bugs.** Each iteration builds on the previous one's wrong assumption. By milestone boundary, the bug is deeply embedded. Counter: verify has never caught a logic bug across 24 runs — only integration gaps. The implement gate (tests + lint) catches functional breakage immediately. This risk is theoretical and unobserved.

**Loss of per-iteration confidence signal.** The green checkmark after each iteration feels good even when it's a rubber stamp. Counter: the implement gate's green (tests pass, lint clean, git clean) provides the same signal without a separate agent.

**Late discovery.** A broken AC isn't caught until milestone boundary, potentially 5-8 iterations later. Counter: outright breakage is caught by the implement gate. What slips through is subtle spec-compliance issues — exactly what a broader-context milestone verify catches better.

#### NOTES_PLAN_MSV_6: Recommendation (2026-04-10)

**Milestone-scoped verify by default. No per-iteration verify. Optional per-iteration flag for plan-time override.**

1. Regular iterations: implement only (gate enforces tests + lint + git clean)
2. Milestone boundary: refactor iteration's verify scope expands to include AC spot-checking across the milestone's iterations
3. Plan-time opt-in: `verify: true` on individual iterations the human flags as high-risk — escape hatch, not the default

**Sequencing:** Don't build the opt-in flag first. Start with just dropping per-iteration verify and expanding milestone verify scope. Run a real comparison. If milestone catches everything (expected), the per-iteration opt-in may never be needed.

**PLAN_VER rewrite enables this.** phase-verify.md is already scoped to functional AC checking. Adapting it for milestone scope (check N iterations' ACs instead of 1) is a reference file change, not an architectural change.

#### NOTES_PLAN_MSV_7: Implementation decisions (2026-04-11)

**MSV_2/MSV_3 are no-ops.** Analysis during implementation revealed:
- `LOOP_LIFECYCLES` in `gate_session.py` is session-level, not per-iteration. `verifying` must stay for refactor iters. No change needed.
- `verifyVerdict` clearing in `iter_state.py` is harmless — sets `None` to `None` for regular iters. No change needed.

**Milestone iteration list uses dependency map.** `state.json.dependencyMap[ITR_RFT_1]` already contains exactly the list of iterations whose ACs the verify agent should check. No new data structure needed. `prompt.py` reads the dep list, extracts iteration blocks from `iterations.md`, and injects them as a `milestone-iterations` prompt section.

**Per-iteration verify opt-in flag deferred.** MSV_6 recommended it as an escape hatch. Not built — start with pure MSV (no per-iteration verify at all), validate with a real run. If needed, add later.

**Verify rejection protocol changed.** Old: verify writes failing tests, leaves them on the branch. New (milestone scope): verify fixes issues in-place (small/scoped) or marks criterion failed with evidence + learnings (large/risky). No code writes from verify that aren't fixes.

#### NOTES_PLAN_MSV_8: Implementation complete (2026-04-11)

All MSV steps done except MSV_10 (real run comparison). Changes across 6 script/test files + 4 reference/doc files. 100/100 orchestrator tests, 80/80 prompt tests. Consistency pass updated 13 files for stale `implement→verify` references.

#### NOTES_PLAN_MSV_9: MSV_10 validation — LOGA R17 results (2026-04-13)

**Result: MSV partially validated.** Verify skip works perfectly. Milestone AC verification is broken.

**What worked:** All 13 regular iterations correctly skipped verify (verifyVerdict: null, attempts.verify: 0). Orchestrator routing `implementing → complete` is reliable. 90m wall clock — fastest LOGA ever (18% faster than R16). ~14m saved from eliminating per-iteration verify.

**What broke:** `update-criterion` can only write to the current iteration's state file. When ITR_RFT_1's verify agent tried milestone ACs using prefixed IDs (`ITR_001_AC_1`), all calls returned exitCode 1 ("criterion not found"). Agent self-corrected to own 4 ACs only. Same pattern on ITR_RFT_2. ITR_RFT_3 had a partial workaround: plan agent baked milestone checks into the refactor AC definitions (AC_1-3 explicitly verify ITR_012/013 functionality), but this was inconsistent — RFT_1 and RFT_2 had generic refactor ACs only.

**Key positive:** ITR_RFT_1 verify caught a real integration gap — `--from`/`--to`/`--field` CLI flags implemented in filter package but never wired to `main.go`. Fixed in-place. This validates the MSV hypothesis that integration issues are caught at milestone boundaries.

**Fix needed (P1):** Cross-iteration AC verification. Options: (a) allow update-criterion to target other iterations' state files, (b) copy milestone ACs into refactor state at plan time, (c) write a milestone verification report without using update-criterion, (d) have plan agent consistently embed milestone checks in refactor AC definitions (ITR_RFT_3 pattern). See CASE_LOGA_R17_REC_1.

**Other findings:** Plan phase counts as implement attempt 1, pushing real work to attempt 2 (i2/v2 suffixes). 16 tiny 1-line plan trace files. No plan branch created. Learnings recovered to 14 (R16: 2). See full case study: CASE_STUDY_LOGA_R17.md.

#### NOTES_PLAN_MSV_10: Both MSV and VOS paused — staying on 0.7.0 (2026-04-13)

**Decision:** Continue with 0.7.0 per-iteration verify. Pause both MSV and VOS.

**Rationale:** R17 showed MSV's implementation was inconclusive — the milestone-scoped verify didn't actually verify milestone iteration ACs due to a tooling gap (`update-criterion` can't write cross-iteration). But the deeper question is whether verify adds meaningful value on well-specced projects like LOGA. The 96% rubber-stamp rate across 24 runs may reflect good specs rather than wasted verification — if that's the case, optimizing verify (MSV) or parallelizing it (VOS) is solving a problem that may not need solving. Keep per-iteration verify as-is in 0.7.0 until a project surfaces where verify demonstrably catches issues that warrant the engineering investment to change the verify model.

---

### NOTES_PLAN_VOS: PLAN_VOS — Verify on the Side

Alternative to PLAN_MSV. Run verify in parallel with the next iteration's implement, using audit tags for git isolation and restricting verify to artifact-only writes (no code changes). Both MSV and VOS solve the same problem (verify costs 25-35% of loop time); they differ in approach.

**Origin:** During PLAN_MSV implementation planning (2026-04-11), the question arose: instead of deferring verify to milestone boundaries, could verify run in parallel with implement? The audit tag mechanism already creates immutable snapshots after each implement phase — verify can read those without conflicting with the next implement.

#### NOTES_PLAN_VOS_0: Core insight — audit tags enable safe parallelism (2026-04-11)

The key enabler is that plet already creates audit tags after every implement phase (`git_ops.py audit-tag`). These are immutable git refs pointing to the exact code state after implement. If verify checks out an audit tag (via worktree), it reads frozen code while implement works on the live branch. No merge conflicts possible.

The second enabler: restricting verify to artifact-only writes. Current verify writes:
- Criterion updates (per-iteration state file) ✓ safe — different file than next implement's state
- Verdict (per-iteration state file) ✓ safe — same reason
- Learnings, emergent (append-only runtime artifacts) ✓ safe — append is conflict-free
- Trace events (NDJSON append) ✓ safe
- **Failing tests (rejection protocol)** ✗ this is the one code write — must be removed

Removing the "write failing tests" part of rejection protocol is the only behavioral change to verify. Everything else is already artifact-only.

#### NOTES_PLAN_VOS_1: Rejection without code writes (2026-04-11)

**Decision:** Rejection communicates via structured criterion updates + learnings narrative, not code.

Current rejection protocol: verify writes a failing test, marks criterion as failed with `--red-test` flag, sets verdict to "rejected." The failing test gives the next implement attempt a concrete starting point.

VOS rejection protocol: verify marks criterion as failed with rationale (`update-criterion --status failed --rationale "..."`), writes a detailed learning entry explaining what's wrong and how to fix it, sets verdict to "rejected." The next implement attempt reads structured criterion status (which ACs failed) + narrative learnings (why, what to look for).

**Why this is arguably better:** A failing test written by the verify agent is often low-quality — it's written quickly, in a different context window, without full understanding of the implementation. A detailed learning entry with specific file paths, expected vs. actual behavior, and suggested fix approach gives the next implement agent more actionable information.

#### NOTES_PLAN_VOS_2: Pipeline flow and stop-on-reject (2026-04-11)

**Pipeline behavior:**
```
Normal flow (96% case):
  implement 1 → [verify 1 in background] → implement 2 → [verify 2 in background] → ...
  verify 1 passes → complete. verify 2 passes → complete. Full speed.

Rejection flow (4% case):
  implement 1 → [verify 1 in background] → implement 2 starts → verify 1 REJECTS
  → pipeline pauses after implement 2 finishes
  → implement 1 re-queued with learnings from verify 1
  → implement 2 work may be wasted (built on rejected foundation)
```

**Stop-on-reject, not rollback:** When verify rejects, the orchestrator doesn't try to undo the in-progress implement. It lets it finish, then pauses. The rejected iteration goes back to `queued`. The next iteration that was being implemented may need to re-run after the fix, but that's a scheduling decision, not a rollback.

**Worst case:** implement N+1 completes successfully, then verify N rejects. N+1's work was built on a bad foundation. But:
- The 4% rejection rate means this is rare
- N+1's work may still be valid if the rejection is isolated to N
- If not, N+1 goes back to queued after N is re-implemented — same as today's sequential behavior, just delayed by one iteration

#### NOTES_PLAN_VOS_3: State concurrency analysis (2026-04-11)

**Already safe by design (SF_28):**
- Per-iteration state files are separate — verify N writes to `state/ITR_001.json` while implement N+1 writes to `state/ITR_002.json`. No conflict.
- Global `state.json` is orchestrator-owned. Subagents don't write lifecycle. The orchestrator serializes lifecycle updates (already single-threaded in `_update_lifecycle()`).
- Runtime artifacts (learnings, emergent, progress) are append-only. Concurrent appends to the same file could interleave, but `atomic_append()` uses temp-file-then-append, so individual entries stay intact.

**One new concern:** The orchestrator currently calls `_run_iteration()` sequentially — implement then verify. Making verify parallel means the orchestrator needs to track a background verify while running the next implement. This is the main orchestrator complexity addition.

#### NOTES_PLAN_VOS_4: MSV vs. VOS comparison (2026-04-11)

| Dimension | MSV (Milestone-Scoped) | VOS (Verify on the Side) |
|-----------|----------------------|--------------------------|
| Verify timing | Milestone boundary only | Every iteration, in parallel |
| Verify scope | All milestone ACs at once | Single iteration ACs |
| Code change | ~10 lines orchestrator | Significant orchestrator rework |
| Git complexity | None (skip verify) | Worktree management on audit tags |
| Rejection protocol | Fix in-place at milestone | Structured feedback via artifacts |
| Catch timing | Late (milestone boundary) | Same as today (per-iteration) |
| Time savings | 25-35% of loop time | ~same savings (verify overlapped, not eliminated) |
| Implementation risk | Low (remove behavior) | Medium (add parallel behavior) |
| New infrastructure | None | Worktree management, parallel dispatch, pipeline state |

**Key tradeoff:** MSV is dramatically simpler but defers catching issues to milestone boundaries. VOS keeps per-iteration catching but adds orchestrator complexity. Given the 96% rubber-stamp rate, MSV's deferral is low-risk. But VOS preserves the safety net for the projects where verify actually matters (SPARK: 17% rejection rate).

#### NOTES_PLAN_VOS_5: Decided — sibling worktree on audit tag, not nested (2026-04-11)

**Decision:** Verify runs in a sibling worktree created from the audit tag. Git worktrees are peers (not nested) — a worktree can create sibling worktrees because they all share the same `.git` dir. This works even when the target project is already in a worktree (normal plet workflow after PLAN_SEQ).

**This is distinct from PLAN_SEQ's removal of worktrees.** PLAN_SEQ said "humans manage their own worktrees for development." VOS says "orchestrator manages a temporary worktree for verification." Different use case: short-lived, automated, read-only on code, invisible to the human.

```
main repo (.git)
├── worktree A (human's plet run — implement works here)
└── worktree B (verify's read-only snapshot — audit tag, temp)
```

#### NOTES_PLAN_VOS_6: Decided — verify write boundary (2026-04-11)

**Decision:** Verify in VOS is read-only on code, write-only on artifacts. Specific boundary:

**Safe writes (allowed):**
- `plet/state/ITR_N.json` — own iteration state only (criterion updates, verdict). No conflict with implement N+1 which writes `ITR_N+1.json`.
- `plet/learnings.md` — append-only via `atomic_append`. Concurrent appends from implement are safe (entries are self-contained blocks).
- `plet/emergent.md` — same as learnings.
- `plet/trace/ITR_N-verify-*` — own trace files, namespaced by iteration+phase+attempt.

**Not allowed:**
- Any source code or test files (worktree is disposable)
- `plet/state.json` (orchestrator-owned per SF_28)
- `plet/progress.md` (orchestrator writes progress, not verify)
- Git operations (no commits, no tags, no branches from the worktree)

**Key consequence:** The current rejection protocol ("write failing tests") is removed. Rejection communicates via structured criterion updates (`--status failed --rationale "..."`) + learnings narrative. This is arguably better — failing tests written by verify in a different context window are often low-quality; detailed learnings with file paths and expected vs. actual behavior give the next agent more actionable information.

#### NOTES_PLAN_VOS_7: Open — rejection response options (2026-04-11)

The load-bearing design question for VOS. When verify rejects and implement has moved past that iteration, what happens? Six options identified:

**Option 1: Re-queue + pause (stop the line).** Verify N rejects → orchestrator pauses after current implement finishes → N goes back to queued → re-implement N → resume. Pro: foundation solid before building more. Con: wastes all work after N, pipeline stalls (loses VOS throughput benefit), new pause/resume state machine. Expensive recovery for a 4% event.

**Option 2: Defer to refactor (forward-only, existing mechanism).** Verify N rejects → findings in learnings, criterion marked failed → implements keep flowing → refactor iteration at milestone boundary addresses failed ACs alongside code quality work. Pro: zero orchestrator changes, forward-only, refactor infrastructure already exists. Con: rejected AC stays failed for 5-8 iterations, refactor scope grows, multiple rejections could overwhelm refactor, blurs refactor vs. verify responsibility.

**Option 3: Patch iteration (forward-only, new targeted fix).** Verify N rejects → orchestrator dynamically inserts a new iteration (ITR_FIX_N or similar) scoped to the rejected ACs. Pro: targeted fix, forward-only, doesn't bloat refactor. Con: dynamically creating iterations is new infrastructure, new naming convention, scheduling complexity, plan artifacts become mutable at runtime.

**Option 4: Fold into next implement (expand neighbor's scope).** Verify N rejects → learnings flow to next implement agent who addresses failed ACs as part of their work. Pro: no new iterations, no stalls, no orchestrator changes, learnings already in prompt context. Con: next iteration may be unrelated, unpredictable scope expansion, cascading bloat if next also rejects, muddies iteration accountability.

**Option 5: Record only — human triages at refine.** Verify N rejects → findings go to emergent.md → pipeline keeps flowing → human decides at refine. Pro: simplest orchestrator, human judgment. Con: fix deferred until refine, undermines VOS's advantage over MSV (early per-iteration signal without early action ≈ no signal).

**Option 6: Severity-based routing.** Verify classifies severity → critical: pause (option 1) / minor: defer to refactor (option 2). Pro: proportional response. Con: verify agent decides severity (judgment in automation), two code paths, more design decisions about severity thresholds.

**Uncomfortable observation:** Options 2 and 5 converge toward MSV — if rejection findings just flow forward, VOS is doing the same thing as MSV (catch at boundary) but with extra machinery. VOS's advantage over MSV is early signal, but only if early signal causes early action. Options 1 and 3 preserve early action but add orchestrator complexity.

**Not yet decided.** Depends on clarifying verify's primary goals — what is verify actually trying to accomplish? The answer shapes which rejection response makes sense.

#### NOTES_PLAN_VOS_8: Open questions (updated 2026-04-11)

- **Pipeline depth:** Max 1 verify in flight? Leaning max 1 (implement typically takes longer than verify, natural constraint).
- **Pipeline advance on verify-in-flight:** If verify N still running when implement N+1 finishes, does N+2 start? Depends on rejection response decision (VOS_7). If implements can flow freely (options 2-5), then yes. If pause-on-reject (option 1), then constrained.
- **Worktree cleanup:** Orchestrator cleans up after reading verdict (leaning this way — handles crash case too).
- **Head-to-head comparison:** Both MSV and VOS should be tested on the same project. Criteria: wall-clock time, total tokens, catch rate, implementation complexity, failure mode behavior.
- **What are verify's primary goals?** Must answer before choosing rejection response. Is verify catching bugs? Ensuring spec compliance? Providing confidence signal? The answer determines whether early action on rejection matters.

#### NOTES_PLAN_VOS_9: Verify's primary goals — case study evidence (2026-04-11)

Analysis of what verify actually catches across 24 runs, to determine whether per-iteration verify (VOS) or milestone-scoped verify (MSV) is the right design:

| Goal | Evidence | Per-iteration value |
|------|----------|-------------------|
| Catch implementation bugs | 0 caught across 24 runs. Implement gate (tests + lint) catches functional breakage. | None proven |
| Catch integration gaps | ALL 5 real rejections were this (missing modules, unwired functions, incomplete features) | Proven, but better at milestone scope — per-iteration verify sees N in isolation, can't check integration with N+1 |
| Spec compliance checking | Overlaps with integration gaps. Rejections were "AC says X should exist, it doesn't" — not subtle interpretation differences | Proven, same as above |
| Confidence signal | 96% rubber stamp. Informational value low precisely because it almost never says no | Minimal |
| Cross-iteration consistency | Integration gap catches ARE this. But per-iteration verify can't check against future iterations | Better at milestone scope |
| Surface emergent items | Occasional, but implement agents do this too. Side effect, not primary purpose | Minimal |

**Conclusion:** Verify's only proven value is integration gap detection, and integration gaps are more visible at milestone scope when all pieces are present. This means MSV is the right design — it catches the only class of bugs verify has ever caught, at the scope where they're most visible, with dramatically less complexity than VOS.

#### NOTES_PLAN_VOS_10: Interim conclusion — VOS paused, MSV preferred (2026-04-11)

**Decision:** Pause VOS. Proceed with MSV.

**Rationale:** The VOS design exploration surfaced a critical question: what are verify's primary goals? Examining 24 runs of case study data, verify's only proven value is catching integration gaps. Integration gaps are better caught at milestone scope (MSV) than per-iteration scope (VOS), because the verify agent can see all pieces together.

VOS adds significant orchestrator complexity (parallel dispatch, sibling worktrees on audit tags, artifact-only write boundary, rejection response handling) to preserve per-iteration verify — but per-iteration verify's advantage over milestone verify is precisely the thing the data says doesn't matter.

**Not dead, just paused.** VOS has useful design artifacts that may apply elsewhere:
- Sibling worktree on audit tag pattern — useful for parallel subplets, CI integration
- Artifact-only write boundary — clean separation of concerns
- Rejection-via-learnings (no code writes) — arguably better than current failing-test rejection protocol regardless of VOS/MSV

**Reactivation trigger:** If MSV real runs (MSV_10) show that milestone-scoped verify misses integration gaps that per-iteration would have caught — particularly on SPARK-like projects with higher rejection rates.

MSV is the simpler bet. Build it, run a real comparison (MSV_10). If milestone-scoped verify catches everything (expected from 24-run data), VOS is unnecessary complexity. If milestone-scoped verify misses issues that per-iteration would have caught — particularly on SPARK-like projects with higher rejection rates — then VOS becomes the right answer, and the audit-tag + artifacts-only design is ready to implement.

The VOS design work is not wasted either way — the "verify on audit tag, artifacts-only writes" pattern may be useful for other purposes (parallel subplets, CI integration, etc.).

---

### NOTES_PLAN_NTS: PLAN_NTS — Notes Reorganization

**Decision (2026-04-05):** NOTES.md reorganized into plan-chunk sections with stable labels. PLAN.md stays lean (steps + status) with pointers to NOTES.md for rationale. Each plan chunk gets a `NOTES_XXX` section.

### NOTES_PLAN_FOUNDATION: Early Plans (SKL, REF, PKG, CS, NOT, XS, FT, PY, RW)

Completed foundation plans. Grouped here since each is small individually.

#### PLAN_SKL: SKILL.md — Main Orchestrator
Single entry point `/plet` with routing logic based on state detection. File: `skills/plet/SKILL.md`.

#### PLAN_REF: Reference Files
6 reference files injected into subagent prompts: formats.md, state-schema.md, plan.md, phase-implement.md, phase-verify.md, refine.md. All under `skills/plet/references/`.

#### PLAN_PKG: Packaging
Plugin metadata: `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`.

#### PLAN_CS: Case Study Feedback Loop
8 case studies across 3 projects (LOGA, LIBT, SPARK). All feedback tracked in `FEEDBACK_FOO.md` (FOO_1–FOO_72). Stable labels: `CASE_{PROJECT}_{RUN}_{N}`.

FEEDBACK_FOO.md 5-phase overhaul (2026-04-03): stable labels, cross-referencing, resolution pass, new items, coverage check.

Additional work: vocabulary cleanup ("X phase" → "X session"), taxonomy consolidation, case study methodology (`case_studies/CLAUDE.md`), git stash ban (FOO_9), state file enforcement via plet_state.py (FOO_12), spec artifact preservation (FOO_16), post-merge verification (FOO_18), real timestamps (FOO_19), allowed-tools for plet_state.py.

#### PLAN_NOT: Notes Skill
Standalone `/notes` skill for living development notes. File: `skills/notes/SKILL.md` (v0.1.1). Bootstrap, Notes Discipline, reorg, routing, size management. Published in session-kit.

#### PLAN_XS: Extractable Skills
6 skills shipped to session-kit: /dictation, /fast-chat, /notes, /stable-label, /warmup, /sharpen. Published to marketplace (v0.5.0).

#### PLAN_FT: Feedback Triage
Review and resolve open FOO items. 72 total: 67 resolved, 5 withdrawn, 2 deferred.

Key routing: 12 items deferred to PLAN_PY (script handles deterministically): FOO_11 (trace schema), FOO_13 (worktrees), FOO_22 (permissions), FOO_23 (bootstrap), FOO_29 (learnings enforcement), FOO_30 (stash elimination), FOO_31 (end-session), FOO_32 (worktree cleanup), FOO_33 (progress completeness), FOO_35 (lost commits), FOO_38 (knowledge transfer), FOO_40 (lifecycle). 5 resolved as plan-session prose fixes (FOO_24-28).

#### PLAN_PY: Python Tooling
14 enforcement scripts + 6 utility modules. Detailed build plan: `specs/PLAN.md` (47 tasks). Follows "Skills for Judgment, Code for Compliance" principle.

#### PLAN_RW: PRD + ORC + SKILL.md + Reference Files Rewrite
Scripts, prose, and orchestrator complete. LOGA Run 6 validated (13/13, zero human intervention). Phases: PRD catch-up, SKILL.md rewrite, reference files rewrite, ORC spec, ORC implementation, SKILL.md + artifact integration.

Emergent work: lifecycle ownership model, 3 new scripts (schedule, session, orchestrator), 1 rename (session → gate_session), 1 new util (util_git), gate/schedule updates, UNV_CMD_29, NDJSON standardization.

#### PLAN_OVH: Plet Infrastructure Overhead (deferred)
R06: 53% of implement-phase Bash calls were plet infrastructure. Dominated by discovery cost (80 --help lookups, start-phase retries), not artifact writes. Deferred after PLAN_HLP. R08 showed 8.8m/iter (down from 14.2m) with zero --help lookups — may be moot. Re-evaluate if infra is still >40% after parallel run.

### NOTES_PLAN_SUB: PLAN_SUB — Subplets

#### NOTES_PLAN_SUB_TEMPLATES: Project-level plan-templates

Subplets should support a project-level `plan-templates/` directory for projects that define their own templates. When a target project has custom plan-templates (e.g., `plet/plan-templates/`), subplets inherit or override them rather than falling back solely to plet's built-in `references/plan-templates/`. This lets projects add domain-specific DX, testing, or ratchet requirements that apply to all subplets within the project.

### NOTES_PLAN_PRD: PLAN_PRD — PRD Reorganization & Sync

**Trigger:** Audit on 2026-04-08 found PRD significantly out of sync after PLAN_SEQ, PLAN_RFT, PLAN_IDR, and lifecycle extraction. 26 commits since last PRD touch, zero direct prd.md changes.

#### NOTES_PLAN_PRD_AUDIT: Audit Findings (2026-04-08)

**ES Script Inventory — major drift.** PRD lists 14 agent-callable scripts with `plet_` prefix naming. Actual system: 3 entry points (`plet_agent.py`, `plet_tools.py`, `plet_orchestrator.py`) + importable modules (dropped `plet_` prefix). `plet_state.py` split into `global_state.py` + `iter_state.py`. ~8 new scripts/modules not in PRD at all. Test count: PRD says "1230+", actual ~1,060 (consolidation during PLAN_SEQ).

**Missing concepts — zero PRD coverage:**
1. Refactor iterations (ITR_RFT_* prefix, milestone barriers, phase-refactor.md routing, prompt.py detection)
2. Project bootstrap (bootstrap.py: git config, .gitattributes, .gitignore, CLAUDE.md stub, settings.json)
3. Orchestrator loop as cohesive unit (behavior scattered across OR, IMP, VF, SF)
4. Session lifecycle management (start-session, end-session, workstream branch creation)
5. Loop scheduling (eligible selection, breakpoint evaluation, retry budget)
6. Phase-end composite (phase.py end — bundles 6 steps into 1 command)
7. Churn analysis (plet_tools.py churn)
8. Git merge driver (plet_merge_driver.py)

**Stale field names in SF:** `agentActivity` → `phaseActivity`, `lastVerdict` → `implementVerdict`/`verifyVerdict`, per-iteration `lifecycle` field removed (now in state.json.lifecycles per SF_28).

**Reference files:** PRD lists 6, actual 8 (added phase-refactor.md, cli-spec-template.md).

**IMP stale references:** Per-iteration branches no longer exist (single workstream per loop). Merge/squash flow simplified.

#### NOTES_PLAN_PRD_OUTLINE: Approved Outline

Reorganization separates Phases (what happens) from Infrastructure (how it works) from Tooling (what enforces it).

```
OVR  Overview
PER  User Personas
TAX  Taxonomy
GCN  Global Conventions — promoted from buried subsection
PHA  Phases
     PHA_PL   Plan
     PHA_OLP  Orchestrator Loop — NEW
     PHA_IMP  Implement
     PHA_VF   Verify
     PHA_RFT  Refactor — NEW
     PHA_RFN  Refine
INF  Infrastructure
     INF_SF   State Files
     INF_RT   Runtime Artifacts
     INF_SY   Artifact Sync & Fingerprints
     INF_PT   Prompt & Reference Files
     INF_BS   Project Bootstrap — NEW
TLG  Tooling (ES)
     TLG_ES   Architecture (3 entry points + modules)
     TLG_EP   Entry Points
     TLG_MD   Module Inventory
     TLG_UT   Utility Modules
     TLG_PP   Subagent Execution Pipeline
DST  Distribution
--- What ---
NFR  Non-Functional Requirements
FLW  User Flows
--- How ---
ARC  Technical Architecture
DVX  Developer Experience (+ DVX_TMPL)
--- Quality ---
TST  Testing & Verification (+ TST_TMPL)
VFC  Verification Commands (+ VFC_TMPL)
CTA  Critical Test Areas (+ CTA_TMPL)
RCH  Quality Ratchets (+ RCH_TMPL)
MET  Success Metrics (+ MET_TMPL)
--- Delivery ---
MIL  Release Milestones
--- Meta ---
QES  Questions
FUT  Future Considerations
WDN  Withdrawn & Deprecated
```

**Key structural changes (2026-04-08):**
- GC promoted to top-level (governs everything)
- New PHA_OLP consolidates scattered orchestrator behavior
- New PHA_RFT for shipped feature with zero coverage
- New INF_BS for shipped feature with zero coverage
- SY pulled out of OR (fingerprints are infrastructure, not routing)
- ES restructured as TLG with 3-tier architecture

**Section reorder (2026-04-15):** Tail sections (after DST) reordered by concern: What (problem) → How (solution) → Quality (verification) → Delivery (planning) → Meta. Previously used §N numbering order which had §4.5/§9b hacks.

#### NOTES_PLAN_PRD_GCN: GCN Review (2026-04-08)

- GC_2 stays in GCN_ID — the section is "Global Conventions", broad enough
- Iteration branch row removed from GCN_BR — per-iteration branches don't exist post-PLAN_SEQ
- Added WDN (Withdrawn & Deprecated) section at end of PRD for removed items with stable label preservation. Grouped by origin section. Moved SF_19, IMP_20, and the iteration branch pattern there.

#### NOTES_PLAN_PRD_PL: PHA_PL Review (2026-04-08)

- PL_3: "ridl-skills:prd" → "plet's standard PRD format" (old skill name)
- PL_17 added: confirm before loop launch (FOO_66). Never auto-launch.
- PL_18 added: generate ITR_RFT_N refactor iterations at milestone boundaries (PLAN_RFT). Details in PHA_RFT.
- Bootstrap (FOO_64/67) deferred to INF_BS. Planning branch (FOO_65) deferred to PHA_OLP.

#### NOTES_PLAN_PRD_OLP: PHA_OLP Review (2026-04-08)

- OR_ renamed to OLP_ (38 occurrences, 7 files)
- OLP_10 kept in PHA_OLP with cross-ref to INF_BS (bootstrap handles the actual creation)
- OLP_13 (criteria skip) moved to GC_4 — cross-cutting convention, not orchestrator-specific. WDN redirect added.
- OLP_15 (sessionHistory) kept as-is — mixing data + behavior is fine for this length
- Added OLP_16–OLP_22: session lifecycle, scheduling, core loop, phase-end composite, branch creation, single-run semantics
- Detail levels: OLP_19/20/21 full (core loop, phase-end, branches are critical paths). OLP_16/17/18/22 medium.

#### NOTES_PLAN_PRD_IMP: PHA_IMP Review (2026-04-08)

- Scope narrowed: IMP is now purely subagent behavior. Orchestrator behaviors moved to PHA_OLP.
- Moved to WDN: IMP_1, 3, 5, 11, 12, 15, 16, 21, 22 (9 IDs). All have PHA_OLP cross-refs.
- IMP_2: updated script names (`plet_invoke.py` → `invoke.py`, `plet_prompt.py` → `prompt.py`), reframed as subagent prompt content.
- IMP_10: updated script names (`plet_invoke.py` → `invoke.py`, `plet_trace.py` → `traces.py`), removed "lifecycle changes" from trace events list (subagent doesn't write lifecycle).
- IMP_13: "sets lifecycle to blocked" → "sets `implementVerdict: 'blocked'`" (SF_28 compliance).
- IMP_24: "sets its own lifecycle to ineligible" → "sets `implementVerdict: 'blocked'`" + orchestrator recalculates eligibility.
- Section intro updated: "This section covers what the implement subagent does" with PHA_OLP cross-ref.

#### NOTES_PLAN_PRD_VF: PHA_VF Review (2026-04-08)

- VF_18: script names updated (traces.py, invoke.py)
- VF_19: moved to WDN — redundant with OLP_18
- VF_25 added: per-AC reflection step. Makes verification mechanical (verify → reflect → record) instead of holistic judgment. Applies to both implement and verify phases. Rationale: reduces agent churning on what to do next.

#### NOTES_PLAN_PRD_MECH: Mechanical Process Principle (2026-04-08)

**Observation:** Subagents are significantly faster when given a fixed mechanical process (do A → do B → do C) than when asked to exercise judgment about what to do next. Churning on "what should I do now?" wastes tokens and wall clock. The per-AC reflection step (VF_25) validated this — measurable speed improvement.

**Principle:** Reference files for implement, verify, and refactor should prescribe a step-by-step sequence per acceptance criterion, not a list of concerns to weigh. The agent's job is judgment *within* each step (is this criterion satisfied?), not judgment *about* which step comes next.

**Applies to:** phase-implement.md, phase-verify.md, phase-refactor.md — the three subagent reference files. Each should have a clear per-criterion workflow loop that the agent follows mechanically.

#### NOTES_PLAN_PRD_RCH: RCH Section Added (2026-04-08)

- New RCH section after NFR. Three initial ratchets: coverage (91%), lint (0 warnings), test health (all pass).
- Ratchet discipline: bump threshold when metric sustainably exceeds it.
- Candidates for future ratchets: cyclomatic complexity, file size, doc coverage.
- TLG_ES intro updated: removed test count, added RCH cross-ref, added three-tier architecture description.
- TLG_EP intro updated: describes thin shim pattern.
- TST_PL intro updated: removed test count, added RCH_1 cross-ref.

#### NOTES_PLAN_PRD_TLG: TLG Review (2026-04-08)

- TLG_ES: requirements ES_1–ES_8 accurate, no changes needed.
- TLG_EP: filled in — 3 entry points with all commands listed. plet_agent.py (6 commands), plet_tools.py (8 commands), plet_orchestrator.py (1 command).
- TLG_MD: filled in — 16 modules with commands. Includes phase.py, schedule.py, session.py, bootstrap.py, plet_merge_driver.py (all missing from old PRD). plet_git_iteration.py confirmed deleted (PLAN_SEQ removed worktrees).
- TLG_UT: filled in — 9 utility modules. Added util_format.py, util_git.py, util_constants.py, util_sink.py (all missing from old PRD).
- TLG_PP: pipeline diagram already updated in restructure pass.

#### NOTES_PLAN_PRD_BS: INF_BS Review (2026-04-08)

- 3 requirements added (BS_1–BS_3). Covers: idempotent setup, read-only check, plan-phase integration.
- BS_1 details the 5 setup steps from bootstrap.py (merge driver, gitattributes, gitignore, CLAUDE.md stub, settings.json).
- BS_2 connects to OLP_16 preflight.
- BS_3 connects to PL_17 (confirm before mutating).

#### NOTES_PLAN_PRD_RT: INF_RT Review (2026-04-08)

- RT_3: emergent ID format updated to `EM_{iter_id}_{N}` (gate validates this post-PLAN_SEQ)
- RT_4: script names updated (invoke.py, traces.py)
- RT_5: "lifecycle transitions" → "verdict updates" (SF_28 compliance)

#### NOTES_PLAN_PRD_PT: INF_PT Review (2026-04-08)

- PT_7: script name updated (prompt.py)
- PT_8 added: phase-refactor.md reference file with ITR_RFT_* routing
- PT_9 added: plan-templates directory with two-dimensional composition (project type × platform). Currently PL_DX/PL_TV/PL_CT/PL_SM live inline in DVX_TMPL — PT_9 is the future home.
- PT_10 withdrawn before publication — cli-spec-template.md will become a plan-template (project type), not its own requirement
- Section reorganized into 4 groups: subagent refs, schema refs, plan templates, prompt assembly

#### NOTES_PLAN_PRD_TAX: TAX Section Added (2026-04-08)

- New TAX section added after PER, before GCN. Three subsections: TAX_VH (vocabulary), TAX_DT (document terms), TAX_AC (artifact categories).
- Content from NOTES_TAX_1/2/3 — canonical definitions promoted from NOTES to PRD.
- TAX_4 (dir variables) and TAX_5 (status model) kept in NOTES — implementation details.
- TAX_AC updated for current state: removed per-iteration branches, updated script names, updated state.json description (lifecycles not parallel groups).

#### NOTES_PLAN_PRD_RFT: PHA_RFT Review (2026-04-08)

- 7 requirements added (RFT_1–RFT_7). Covers: prefix routing, milestone barriers, plan generation, mechanical workflow, minimal ACs, single attempt, churn tool.
- Design follows NOTES_PLAN_RFT_SIMPLIFY: no new phase, no schema changes, no custom verdicts. Just a different reference file.
- RFT_4 references GC_5 (mechanical process principle).

#### NOTES_PLAN_PRD_DST: DST Review (2026-04-08)

- DS_4 added: global and project-level installation (alternative to marketplace).

#### NOTES_PLAN_PRD_MIL: MIL Review (2026-04-08)

- Historical milestones condensed to one-line summaries (v0.1–v0.7).
- MIL_NX: PLAN_PRD, PLAN_SUB, PLAN_EVL, PT_9 as forward candidates.

#### NOTES_PLAN_PRD_QES: QES Rename (2026-04-08)

- RSQ → QES with QES_RSLV / QES_OPEN subsections.
- Resolved questions numbered as stable labels QES_1–QES_11.

#### NOTES_PLAN_PRD_PASS: Final Consistency Pass (2026-04-08)

Structural pass across entire repo. Findings:

**Fixed in this session:**
- IMP_9 stale SF_18 reference removed
- CTA stale ~4KB reference updated
- FUT #14 shortened with PT_9 cross-ref

**Fixed in FIX_5 session (2026-04-09):**
- `formats.md:39` — removed withdrawn SF_18 ID from heading
- `formats.md:53` — `section 3.6` → `§ INF_RT`
- `refine.md:407` — `agentActivity` → `phaseActivity`
- `refine.md:419-421` — removed dead `parallelGroups` section
- `NOTES.md:390` — `lastVerdict` → `verifyVerdict`
- `NOTES.md:918` — `lastVerdict convenience field` → `implementVerdict/verifyVerdict fields`
- `PLAN.md:19,496` — test count 1056 left as-is (historical marker from PLAN_COV completion, not current state claim)
- Script names updated across SKILL.md, reference files, scripts/CLAUDE.md, formats.md, state-schema.md, plan.md, refine.md: `plet_fingerprint.py` → `plet_tools.py`/`fingerprint.py`, `plet_invoke.py` → `invoke.py`, `plet_trace.py` → `traces.py`, `plet_entries.py` → `entries.py`
- scripts/CLAUDE.md inventory table rewritten: 3 entry points + 15 domain modules + 9 util modules
- `guide/` files: `agentActivity` → `phaseActivity` (2 files)

#### NOTES_PLAN_PRD_OQ: Open Questions

*No open questions at this time.*

#### NOTES_PLAN_PRD_LABELS: Section Label Conventions

**H2:** 3-letter stable label (`XXX`). Navigational groupings.
**H3:** `XXX_YYY` where YYY matches the existing requirement ID prefix. Grep for `IMP` finds both `PHA_IMP` (section) and `IMP_1` (requirement).
**No section numbers.** Labels replace numbers — no renumbering churn on reorganization.

**H2-only sections** (DST, NFR, etc.): H2 label may not exactly match req prefix (DST≠DS, NFR≠NF). Accepted tradeoff — only 2-3 cases.

**RF → RFN rename (2026-04-08):** Refine requirement prefix renamed from `RF_` to `RFN_` to distinguish from `RFT_` (refactor). 49 occurrences across 5 files. `RFN` greps clean, `REF` rejected due to collision with `references/`.

#### NOTES_PLAN_PRD_RESOLVED: Resolved Questions

**OQ_PRD_1: PL_DX / PL_TV / PL_CT / PL_SM template placement.**
**Decision:** Extract to `references/plan-templates/`. Plan phase loads `common.md` + applicable type/platform templates.

Templates define what plet's plan phase injects into *target project* PRDs. The PRD's `_TMPL` sections are the source of truth (plet's own requirements for what templates contain). `plan-templates/common.md` is the derived implementation artifact that target projects consume.

**Two independent template dimensions:**
- **Project type** (what you're building): common, webapp, cli, library, mobile, etc.
- **Platform** (what you're building with): mac, linux, elixir, python, go, etc.

These compose independently — a Python CLI project loads `common.md` + `cli.md` + `python.md`. A Phoenix webapp loads `common.md` + `webapp.md` + `elixir.md`.

**For PRD_7 (updated 2026-04-15):** Go straight to the folder structure — no interim single file. PT_9 collapsed into PRD_7.

**Structure:**
```
references/plan-templates/
├── common.md      — applies to ALL projects (PL_DX, PL_TV, PL_VFC, PL_CT, PL_SM, PL_RCH)
├── cli.md         — project type: CLI tools (stub)
├── webapp.md      — project type: web applications (stub)
├── library.md     — project type: libraries/packages (stub)
├── python.md      — platform: Python (stub)
├── elixir.md      — platform: Elixir/Phoenix (stub)
├── go.md          — platform: Go (stub)
└── ...
```

**Source-of-truth chain (2026-04-15):** PRD (`DVX_TMPL`, `TST_TMPL`, `VFC_TMPL`, `CTA_TMPL`, `RCH_TMPL`, `MET_TMPL`) defines what the templates contain — this is the root source of truth. `references/plan-templates/common.md` is the implementation artifact derived from the PRD. `session-plan.md` references `plan-templates/` instead of inlining templates (eliminates three-copy problem). Two copies total: PRD (authoritative) → plan-templates/ (derived).

#### NOTES_PLAN_PRD_RATCHETS: PL_RCH Formalization (2026-04-15)

**Decision:** Add PL_RCH as a formal template section alongside PL_DX/PL_TV/PL_VFC/PL_CT/PL_SM.

FOO_73 added ratchets to the PRD template outline and conventions, but never created formal PL_RCH requirement IDs. Every other plan-phase template section has IDs — ratchets should too. Expanded from initial 3 to 6 after MET cleanup relocated specific ratchets (coverage, lint, format, test pass rate) from MET to RCH.

| ID | Requirement | Priority |
|----|-------------|----------|
| PL_RCH_1 | Plan session defines quality ratchets — metrics that can only improve, with current threshold and enforcement mechanism | P0 |
| PL_RCH_2 | Test coverage ratchet — coverage percentage must not decrease | P0 |
| PL_RCH_3 | Lint-clean ratchet — zero linter warnings | P0 |
| PL_RCH_4 | Format compliance ratchet — 100% format compliance | P0 |
| PL_RCH_5 | Test pass rate ratchet — all tests pass | P0 |
| PL_RCH_6 | Ratchet thresholds updated upward when sustained improvement observed | P1 |

#### NOTES_PLAN_PRD_TEMPLATE_LABELS: Stable Labels in PRD Template (2026-04-15)

**Decision:** Replace §N numbered sections in the session-plan.md PRD template with stable label prefixes. The PRD itself already uses stable labels (GCN, PER, DVX, etc.) but the template outline still used §1–§14 numbering. Mismatch caused §4.5 and §9b hacks for inserted sections.

New template section headers grouped by concern: **What** (GCN, PER, FRQ, NFR, FLW), **How** (ARC, DAT, DVX), **Quality** (TST, CTA, RCH, MET), **Delivery** (MIL, RFP), **Meta** (QES, FUT). Stable labels replace §N numbers. Same ordering applied to PRD, common.md, and session-plan.md template outline.

New labels introduced: FRQ (functional requirements container), DAT (data models), RFP (refactor policy — split from MIL).

#### NOTES_PLAN_PRD_TMPL_RENAME: _TP → _TMPL Suffix (2026-04-15)

**Decision:** Rename all `_TP` suffixes to `_TMPL` (DVX_TP → DVX_TMPL, etc.). `_TP` was too terse and not recognizable. `_TMPL` is the standard abbreviation for "template" (Go templates, etc.).

#### NOTES_PLAN_PRD_VFC: VFC Extraction (2026-04-15)

**Decision:** Extract verification commands from TST into a dedicated `VFC` section. These commands (test, lint, format, typecheck, build, package) run as gates at every phase completion — implement, verify, refactor. They're a quality concern, not a testing philosophy item. Placed in the Quality group: TST → VFC → CTA → RCH → MET.

VFC in common.md is lean (command categories + VFC_1 for warnings-as-errors). Platform templates (`python.md`, `elixir.md`, `go.md`) will provide specific commands per category.

#### NOTES_PLAN_PRD_MET_CLEANUP: MET Section Cleanup (2026-04-15)

**Decision:** MET contained items that belonged elsewhere:
- Test coverage, lint-clean, format compliance, test pass rate → **RCH** (these are ratchets)
- Code smells checklist → **DVX** Resilience (DVX_22/PL_DX_26)
- Test pass rate → **RCH** (always 100%, it's a ratchet)

MET now contains only project-level success metrics: defect rate, defect escape rate, blocker rate.

#### NOTES_PLAN_PRD_COMMON_IDS: common.md ID Convention (2026-04-15)

**Decision:** IDs in common.md match their section labels, not the PRD's PL_ prefix. Users of common.md never see the plet PRD. Mapping: PL_DX → DVX, PL_TV → TST, PL_CT → CTA, PL_SM → MET, PL_RCH → RCH. All renumbered sequentially within each section. PRD keeps its PL_ prefix IDs as source of truth.

#### NOTES_PLAN_PRD_META_REMOVAL: Meta-instruction Removal (2026-04-15)

**Decision:** Removed "plan session defines X" meta-instructions from common.md (RCH_1, MET_1, TST_14, VFC_1, CTA_3). common.md is a template for *target project PRDs* — product requirements, not agent process instructions. The section's existence IS the instruction. Meta-instructions remain in the plet PRD (where they're plet's own requirements for how the plan agent should behave).

#### NOTES_PLAN_PRD_TST_FIXES: TST Corrections (2026-04-15)

**TST_2 added: Meaningful red.** The unit under test must exist as a runnable stub before tests are written. A test that fails because the file doesn't exist (`FileNotFoundError`) is not meaningful red — it proves nothing about the test's ability to catch bad behavior. The stub must return dummy values so the test fails because the answer is wrong.

**TST_9 rewritten: One-directional traceability.** Every requirement must have at least one test, but not every test maps to a requirement. Sanity checks, integration tests, and regression tests are expected and welcome without requirement IDs. Previous wording ("every test traces to a requirement") was wrong.

#### NOTES_PLAN_PRD_INLINE: Drop Inline Templates from session-plan.md (2026-04-15)

**Decision:** Remove the ~150-line inline PL_ template copy from session-plan.md. Replace with a reference to `references/plan-templates/`. Eliminates the three-copy problem (PRD + plan-templates/ + session-plan.md → PRD + plan-templates/).

**Why:** Three copies means three places to update when a PL_ item changes. The plan agent is interactive (human-driven), not a constrained subagent — it can read one more file. session-plan.md becomes shorter and more focused on the plan workflow.

#### NOTES_PLAN_PRD_STUBS: Interactive Stub Fill-out (2026-04-15)

**Decision:** Each plan-template stub (cli.md, webapp.md, library.md, python.md, elixir.md, go.md) gets its own PRD_7 line item and is filled out via interactive review session with the user. Not auto-generated — each project type and platform has domain-specific templates that need human judgment.

#### NOTES_PLAN_PRD_CLI: cli.md Template Fill-out (2026-04-16)

Filled cli.md from patterns in specs/conventions.md, specs/NOTES.md (SPEC_INS_2: Agent-First CLI Design, SPEC_INS_3: Require Arguments Never Default), and scripts/CLAUDE.md. Key patterns pulled in:

- **Agent-first CLI philosophy:** tools are agent tools that humans occasionally debug, not the reverse. Predictability over ergonomics.
- **Strict input validation (NFR_3):** reject unknown/duplicate flags, require args rather than defaulting. Silent forgiveness hides bugs.
- **Three-tier architecture (ARC_1/ARC_4):** entry points → modules → utilities. Command functions return structured results for testability via direct import.
- **Mutually exclusive inline/file flags (NFR_6):** `--data` for inline JSON, `--data-file` for file input. Separate flags rather than `@file` convention — cleaner for strict validation.
- **Context window protection (DAT_3):** `--fields` limits structured output. Every unnecessary token costs.
- **Three-tier help escalation (DVX_2):** cheat sheet → `--usage` → `--help`.

RCH/MET/RFP left as stubs — project-specific, covered by common.md defaults.

#### NOTES_PLAN_PRD_PYTHON: python.md Template Fill-out (2026-04-16)

Filled python.md from plet's own tooling choices. Key patterns: ruff for lint+format (single tool, fast), pytest+pytest-cov+pytest-xdist for testing, pyproject.toml as single config, `uv` for dependency management, shebang+chmod for direct execution, type hints on all signatures, `shell=True` prohibition, McCabe ≤15 complexity ratchet. VFC section has concrete default commands for all 7 categories.

#### NOTES_PLAN_PRD_ELIXIR: elixir.md Template Fill-out (2026-04-16)

Filled elixir.md from patterns observed in havenhm/admin (mature Phoenix 1.8 + LiveView + Ecto project). Key patterns:

- **Context-based organization (ARC_2):** `lib/app_name/` contexts as bounded domains with public APIs. Schemas, helpers, workers private to context directory. Direct match to Phoenix conventions.
- **Ecto discipline (ARC_3/ARC_6):** schemas co-locate moduledoc, fields, changesets, validations. Repo access only — raw SQL justified and documented.
- **Supervision tree (ARC_4):** all long-running processes supervised in application.ex. BEAM's "let it crash" requires explicit restart strategies.
- **Runtime config (NFR_3):** `runtime.exs` for secrets/host config. Compile-time config for secrets is a common Elixir footgun.
- **ExUnit ecosystem (TST):** async tests, DataCase/ConnCase helpers, SQL Sandbox isolation, fixture factories per context, tag-based filtering for external deps.
- **VFC concrete defaults:** `mix test`, `mix format --check-formatted`, `mix credo --strict`, `mix dialyzer`, `mix compile --warnings-as-errors`, `mix release`. Credo/Dialyzer conditional on deps being present.
- **Ratchets:** format + warnings-as-errors are universal P0. Credo/Dialyzer are P1 (common but not universal in Elixir ecosystem).
- **Figlet banners (DVX_4):** observed in admin repo for section dividers in large modules — aids grep and scanning.

FRQ/FLW/DAT/CTA/MET/RFP left as stubs — project-specific, covered by common.md defaults.

### NOTES_PLAN_EVL: PLAN_EVL — Eval System

<!-- Future — design decisions go here when work begins -->

---

## NOTES_LIN: Lineage

plet draws from three sources:

1. Ralph loops (both the general pattern and the snarktank/chief implementations)
2. RIDL (the author's opinionated implementation of Ralph loops)
3. Plan mode as seen in Claude Code, Cursor, etc. (interactive refinement)

### NOTES_LIN_1: What Ralph loops get right
- Autonomous iterations — agents do real work, not just suggestions
- Fresh context windows — each iteration starts clean, no contamination
- Spec first — the PRD drives everything, not ad hoc prompting
- PRD decomposition into agent-sized, iterable chunks
- Runtime artifacts (progress.md, etc.) — structured output that outlives the agent session
- State tracking via prd.json — machine-readable iteration status persisted to disk
- Snarktank's numbers-letters Q&A system for interactive clarification — adopted by plet's plan session

### NOTES_LIN_2: Where Ralph loops fell short
- No verification phase — no independent check that work was done correctly
- No refinement loop — spec is static, doesn't evolve from what agents learn
- Fairly linear — no parallel iteration support
- No multi-developer support — single developer, single session
- Requires external scaffolding (runner, harness) that must stay in sync with the loop's formats — hard to iterate on one without breaking the other

### NOTES_LIN_3: What RIDL added over Ralph loops
- Two-phase iteration split (implementation → verification) — the key structural addition
- Separate learnings.md from progress.md — agent-facing knowledge vs historical record, different audiences
- Three-file pipeline (prd.md → ridl.md → ridl.json) — cleaner decomposition than alternatives, each file has a clear purpose
- Trace logging for full execution traceability

### NOTES_LIN_4: Where RIDL loops fell short
- ridl.json too rigid (sequential ordering, no parallel iterations, no phase tracking, no agent activity state)
- External harness dependency (Ridler.app required) — same scaffolding sync problem as Ralph loops
- Too much logic in the runner — tight coupling between harness and loop behavior
- Still no multi-dev support
- Still fairly linear despite the DAG concept in ridl.json
- Felt like using three separate tools (prd skill, ridl skill, Ridler.app) to accomplish one workflow

### NOTES_LIN_5: What plan mode brings
- Interactive, iterative spec refinement
- The spec is a living document that improves as agents discover gaps
- Human steering at natural checkpoints

### NOTES_LIN_6: What plet adds
- Self-sufficient orchestration — runs natively inside Claude Code, no external harness or runner
- Single entry point (`/plet`) with state-driven routing — user never needs to remember which phase they're in
- Interactive plan session with human steering built in — PRD creation and iteration decomposition in one flow
- Dependency graph with parallel execution — not strictly sequential
- Split state architecture with lifecycle phases, agent activity, heartbeats, and two-state-per-criterion model
- Real-time agent activity state — GUI can show what the agent is doing, not just pass/fail
- Built-in refine session — triages emergent items, updates the spec, re-plans
- Living spec — improves as agents discover gaps, not a static document
- Four runtime artifacts (PLET) with distinct audiences — not just a log file

---

## NOTES_PRD: PRD Status

All sections reviewed and approved. The PRD is the source of truth for requirement IDs and counts.

### NOTES_PRD_1: Key design annotations by section (not duplicated in PRD)
- **GC**: GC_2 — agents prefer making decisions + logging over blocking
- **OR**: OLP_4 includes `verifying` lifecycle. OLP_11 removed (merged into `/plet loop`). OLP_13 — skip scoped to individual acceptance criteria, not iterations
- **PL**: Plan session intro is prose above the table (interactive, human-driven). PL_12 — write to disk on approval. PL_13–PL_14 are P1
- **SF**: P0s first. Split state architecture. SF_24 — schema version migration. SF_25 — entry fencing for git merge safety
- **IMP**: IMP_23 — heartbeat writes. IMP_24 — missing dependency self-correction (does not count against retries). IMP_25 — false dependencies are harmless
- **VF**: VF_7–VF_13 are the VSDD-inspired deep verification items. VF_19–VF_20 are P1
- **RT**: Formats defined at high level; templates in references/formats.md. Stable contract (additive only). RT_11 — plet ID scheme for entry IDs
- **RF**: RFN_1 — refine is human-driven with clean UX. Blocked iterations surfaced alongside emergent items
- **PT**: Physical reference files only. Trace NDJSON schema in state-schema.md (PT_6)
- **NF**: No performance section (intentional). No priority column (all fundamental). NF_8 — state format for external GUI consumers
- **DX**: DX_1 — dev dependency, downgraded to P1
- **PL_DX**: Three principles: Readability, Debug-ability, Resilience. PL_DX_17 — living notes doc
- **PL_CT**: Renamed from PT_CT
- **PL_TV**: Red/green first (PL_TV_1). Sanity check test (PL_TV_9), anti-mock-overreliance (PL_TV_10)
- **PL_SM**: Renamed from PT_SM

---

## NOTES_TBR: Tooling Brainstorm

Tools shipped inside the skill package via `${CLAUDE_SKILL_DIR}/scripts/`. The pattern: prose rules that agents consistently violate → deterministic tooling that makes compliance automatic. See "Skills for Judgment, Code for Compliance" in § Important Concepts.

### NOTES_TBR_1: plet_state.py (shipped, validated)

State file management — `init`, `update-criterion`, `update-field`, `validate`. Zero schema drift across 23 SPARK iterations. The success story that proved tooling > prose.

### NOTES_TBR_2: plet_entries.py (shipped)

Runtime artifact entry writer. Addresses FOO_29 (learnings/emergent regression) and FOO_33 (progress.md incomplete). Same pattern as plet_state.py — agents call a tool instead of composing markdown freehand.

**Commands:**
- `add-progress <dir> --iter-id ITR_xxx --iter-title "..." --phase implement --attempt 1 --status COMPLETE --content "..." [--content-file path] [--files '["path — desc"]'] [--dry-run] [--output json]`
- `add-learning <dir> --iter-id ITR_xxx --iter-title "..." --category gotcha --title "..." --content "..." [--content-file path] --phase implement --attempt 1 [--dry-run] [--output json]`
- `add-emergent <dir> --iter-id ITR_xxx --iter-title "..." --title "..." --phase implement --category "design decision" --content "..." [--content-file path] --attempt 1 [--dry-run] [--output json]`
- `check <dir> --iter-id ITR_xxx` — reports which artifacts have entries, exits 1 if any are missing (pre-verify gate for R_7)

**Features:**
- Generates correct Crockford Base32 plet IDs automatically (RT_11)
- Enforces entry fencing (SF_25) — div start/end markers for git merge safety
- Auto-assigns EM_N numbers for emergent entries (append-only, GC_1)
- Validates phases, statuses, and categories against allowed values
- Atomic appends (temp file + append, no read-then-overwrite)
- Prints generated plet ID to stdout for cross-referencing

### NOTES_TBR_3: plet_fingerprint.py (candidate) ★ strong

Fingerprint computation and drift detection. Fingerprints span 3 files (requirements.md → iterations.md → state.json) with nested ID arrays + `lastNonTrivialUpdate` timestamps. Computing, embedding, and comparing these is purely mechanical — agents doing this by hand across refine sessions will drift on structure, miss updates, or compute incorrectly.

PRD refs: SY_1–SY_8

**What it would do:**
- `compute --file requirements.md` — extract and compute fingerprint from file
- `check` — compare fingerprints across all 3 files, report drift (stale iterations, stale state)
- `update --file iterations.md` — recompute and embed fingerprint
- Enforces the exact nested structure from SY_1/SY_2/SY_3

**Why it matters:** Fingerprint drift is silent — no one notices until an agent operates on stale spec. Currently enforced by prose only. The three-file chain makes hand-computation error-prone.

### NOTES_TBR_4: plet_id.py (candidate) ★ strong

Plet ID generation. The composable ID scheme (type prefix + Crockford Base32 timestamp + context segments) is complex enough that agents will get it wrong across 23+ iterations.

PRD refs: RT_11, Plet ID Scheme

**What it would do:**
- `generate --type epr --iter-id ITR_001 --phase implement --attempt 1` — generate a correct plet ID
- Handles Crockford Base32 encoding (not standard base32 — excludes I/L/O/U, specific casing)
- Handles iteration ID normalization (ITR_001 → id001)
- Handles phase/attempt encoding (implement-1 → i1, verify-2 → v2, refine-1 → r1)

**Why it matters:** Crockford Base32 is uncommon — agents will approximate with standard base32 or invent their own encoding. Incorrect IDs break cross-referencing and merge fencing (SF_25).

### NOTES_TBR_5: plet_preflight.py (candidate) ★ strong

Pre-flight validation before implementation starts. Currently prose — agents can skip steps. FOO_16 (LIBT lost spec artifacts) proved the cost of missing a check.

PRD refs: IMP_19, FOO_16

**What it would do:**
- `check` — run all pre-flight checks: project builds, tests pass, working tree clean, spec artifacts exist on disk (requirements.md, iterations.md), state files parseable
- `check --skip-tests` — fast mode (spec + state only, for quick validation)
- Returns structured pass/fail with specific failure reasons
- Could also check bypassPermissions (FOO_22) and CLAUDE.md existence (FOO_23)

**Why it matters:** Pre-flight is a checklist — exactly the kind of thing agents skip under time pressure. Making it a single tool call means compliance is easier than non-compliance.

### NOTES_TBR_6: plet_report.py (candidate) ★ strong

Verification report scaffolding. The report structure is detailed (VF_21–VF_24): vrp plet ID, verdict, criteriaResults array (one per criterion with status, summary, redTest, relatedEntries), report-level relatedEntries, findings array. This drifts across 23 verify phases when agents compose it from prose descriptions.

PRD refs: VF_21–VF_24

**What it would do:**
- `scaffold --iter-id ITR_001 --attempt 1` — read state file criteria, generate report skeleton with correct plet ID, empty criteriaResults for each AC, empty findings array
- `finalize --iter-id ITR_001 --verdict passed` — validate completed report (all criteria have results, verdict is consistent with criteria statuses), write to state file's verificationReports array
- Generates the vrp plet ID automatically (uses plet_id.py internally or shared logic)

**Why it matters:** The report is the most structured output the verify agent produces. It has nested arrays, cross-references, and a specific append-only contract. Scaffolding it means the agent fills in judgments (evidence, findings) while the tool handles structure.

### NOTES_TBR_7: plet_trace.py (candidate) ○ medium

Trace event writer. Trace coverage improved dramatically in SPARK (51 files) but event schemas still vary. A tool that writes events in the canonical NDJSON schema would prevent the field-naming drift seen in earlier runs (`timestamp` vs `ts`, `iterationId` vs `iteration`).

PRD refs: IMP_10, RT_4, RT_5

**What it would do:**
- `emit --event phase_start --iter-id ITR_xxx --phase implement --attempt 1` — append canonical event to trace file
- `emit --event criterion_start --iter-id ITR_xxx --criterion AC_1` — track criterion-level timing
- Enforces the event schema from formats.md automatically

### NOTES_TBR_8: plet_graph.py (candidate) ○ medium

Dependency graph evaluation. "Which iterations are eligible?" is a pure graph algorithm on the dependency map + lifecycle states. No judgment needed — currently the orchestrator reasons about this by reading state files, which is error-prone at scale.

PRD refs: IMP_1, IMP_5, IMP_21, SF_23

**What it would do:**
- `eligible` — list iteration IDs ready for pickup (all deps complete, lifecycle queued)
- `status` — print graph with lifecycle annotations
- `validate` — check for cycles, missing deps, orphans, dependencies on withdrawn iterations

**Why it matters:** At 23+ iterations with complex dependency chains, manual graph reasoning compounds errors. The SPARK run had no dependency-related failures, but as projects grow this becomes riskier.

### NOTES_TBR_9: plet_consistency.py (candidate) ○ medium

Refine consistency pass automation. The cascading check at end of refine (RFN_16) has three mechanical steps: (1) every decision reflected in requirements, (2) iterations reflect spec (all requirements covered, no dangling references, frozen iterations untouched), (3) state reflects iterations (dependency map, milestones, fingerprints).

PRD ref: RFN_16

**What it would do:**
- `check` — run all three levels, report mismatches
- `check --level 2` — iterations vs requirements only
- Reports: uncovered requirements, dangling iteration references, orphaned state files, fingerprint drift (delegates to plet_fingerprint.py)

**Why it matters:** Steps 2 and 3 are pure cross-referencing — exactly what tooling does better than prose. Step 1 (decisions → requirements) still needs judgment. Partial automation is still valuable.

### NOTES_TBR_10: plet_git.py (candidate) △ light

Git operations wrapper. FOO_30 (42 stashes despite ban), FOO_32 (orphaned worktrees), FOO_35 (lost commits) all point to agents improvising git operations. A constrained git helper could:
- Branch creation/switching without stash (use worktrees instead)
- Post-iteration cleanup (drop stashes, remove worktrees)
- Audit tag creation before squash
- Final loop commit automation (FOO_31)

**Caution:** Git is complex and agents need flexibility. This tool should wrap common operations with guardrails, not replace git entirely. Start with the narrowest pain point (worktree lifecycle) and expand only if needed.

### NOTES_TBR_11: Canary write helper (candidate) △ light

Structured canary entry generation (OLP_14). Format: projectId, loopSessionCount, branch name, iteration lifecycle counts. Simple enough to bundle into plet_entries.py as a `add-canary` subcommand rather than its own tool.

PRD ref: OLP_14

### NOTES_TBR_12: Schema migration helper (candidate) △ light

Auto-migrate state files with older schemaVersion by adding new fields with defaults (SF_24). Deterministic and safe to automate. Could be a plet_state.py subcommand (`migrate`) rather than its own tool.

PRD ref: SF_24

### NOTES_TBR_13: Prioritization

**★ Strong** — complex format + repetitive + case-study-validated drift:
1. **plet_entries.py** — ✅ SHIPPED. Addresses FOO_29 (learnings/emergent regression) and FOO_33 (progress.md incomplete).
2. **plet_fingerprint.py** — silent drift across 3 files. Fingerprint errors cascade.
3. **plet_id.py** — Crockford Base32 is uncommon enough that agents will get it wrong.
4. **plet_preflight.py** — checklist compliance. FOO_16 proved the cost of skipping.
5. **plet_report.py** — most structured output in the verify phase. Scaffolding separates judgment from format.

**○ Medium** — would help, less urgent or less proven drift:
6. **plet_trace.py** — trace coverage improving; schema consistency is the remaining gap.
7. **plet_graph.py** — pure algorithm, no drift yet but risk grows with project size.
8. **plet_consistency.py** — partially automatable; refine phase not yet tested in case studies.

**△ Light** — useful but better as subcommands of other tools:
9. **plet_git.py** — real issues but may be solved by worktree isolation (FOO_13) instead.
10. **Canary write helper** — bundle into plet_entries.py.
11. **Schema migration** — bundle into plet_state.py.

---

## NOTES_MON: Things to Monitor

### NOTES_MON_1: Injection payload sizes

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
- phase-verify.md: ~5,100 tokens (519 lines)
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

### NOTES_MON_2: state-schema.md size

549 lines as of Phase 2b.3. Largest reference file — it's injected in full to verify subagents (who need all sections). No split needed — the file is logically cohesive. Splitting would create cross-reference overhead without reducing injection size. Revisit if it grows past ~700 lines or verify agents show signs of context exhaustion. Also noted in PLAN.md under "Watch: combined injection size."

### NOTES_MON_3: Consistency drift patterns

As consistency passes are used, note what keeps drifting (which files, which patterns, which levels catch it). This data will inform whether to build a dedicated skill or subcommand.

### NOTES_MON_4: Verify retry rate across runs

Track verify first-pass rate and retry causes across case study runs. Goldilocks framing: 0% = rubber-stamping, 50%+ = implement consistently broken, 15-25% may be healthy. Only non-verify retries (git issues, crashes) warrant investigation. Current data: LOGA 85%, LIBT 100%, SPARK 83%.

### NOTES_MON_5: Extracted skills losing integration context

Observed when comparing /fast-chat (session-kit) against NL/NLR conventions in plet-skills. Extracted skills capture mechanics but lose integration with surrounding workflows (Notes Discipline, Decision Discipline, consistency passes). Tracked as SPI_1 in session-kit's SHARPEN.md. Worth auditing /stable-label and /sharpen for similar loss.

### NOTES_MON_6: Post-compaction recovery effectiveness

The three-layer compaction defense (CLAUDE.md POST-COMPACTION RULE → PLET.md MANDATORY ACKNOWLEDGMENT → auto-memory MEMORY.md) appears to be working. Observed 2 compactions in a single session (2026-03-09) — both times, the agent immediately produced "I have just read CLAUDE.md and PLET.md." without prompting. This is the canary behaving as designed, not a false positive: the agent re-read the files and acknowledged before continuing work. Continue monitoring across sessions and across different repos to confirm reliability.

### NOTES_MON_7: Infrastructure overhead fixed tax

LOGA R15: ~20 plet tool calls per agent invocation as a fixed tax regardless of iteration complexity. Implement agents 35-48% infra overhead, verify agents ~59%. Overall ~40-45%. The fixed calls include: setup activity, read context (3-5 calls), update-criterion per AC, wip-commit per AC, add-learning, add-emergent, phase-end. Most are necessary. Worth monitoring whether auto-emit reduces the explicit call count enough to move the needle (OLLR R07: explicit calls down 32%, but total state changes up 72%).

### NOTES_MON_8: Dead activity enum values

LOGA R15 (199 calls) and OLLR R06 (79 calls): `committing` and `verifying` are defined phase-activity values that no agent ever uses. Effective vocabulary is 4 values: `setup`, `implementing`, `running_checks`, `wrapping_up`. With auto-emit, `committing` and `wrapping_up` are now set automatically. Consider pruning unused values or documenting they're for edge cases only.

### NOTES_MON_9: Learnings quantity pattern

LOGA R15: exactly 2 learnings per iteration (1 implement, 1 verify), 26 total. Eerily consistent — suggests agents produce artifacts to meet an implied quota rather than when genuinely useful. OLLR R07 (post-PLAN_VER): 5 learnings for 6 iterations — dropped from R06's 12. The leaner phase-verify.md may reduce verify-phase learnings. Monitor whether quality improves even as quantity drops.

### NOTES_MON_10: progress.md volume scaling

OLLR runs: ~235 lines/iteration. LOGA R15: ~223 lines/iteration. Auto-progress from CLI shim events (SEQ_20-21) is the primary driver. At this rate, a 20-iteration project produces ~4500 lines. May need a summary/compaction strategy if this becomes unwieldy for agent context windows.

### NOTES_MON_11: Coverage gap from auto-emit

`plet_agent.py` at 54% coverage (lines 107-147: `_auto_update_activity` untested). Overall coverage 90.74% vs 91% threshold. The auto-emit function needs dedicated tests. Not blocking IDR but should be fixed before next version bump.

---

## NOTES_GUI: GUI Design

Central collection of GUI-relevant design decisions made across specs. The GUI is a separate project (see PRD §1 Overview) that reads plet's state files for visualization. These decisions shape what the GUI needs to handle.

### NOTES_GUI_1: Multi-directory model (worktrees)

During parallel execution, each iteration has its own `plet/` directory in its worktree. The GUI must watch multiple directories:

- **Session dashboard** — main repo `plet/`. Shows aggregate state: iteration counts, milestones, overall progress. Updated by the orchestrator and after merge-squash.
- **Iteration dashboard** — each worktree `plet/` (`.plet/worktrees/{projectId}/{iter_id}/plet/`). Shows live agent state: activity, criterion updates, progress entries. Disappears after merge-squash.
- **Discovery** — `git worktree list --porcelain` to find active worktrees.

See FOO_49 for full context.

### NOTES_GUI_2: State file formats for external consumers

Per STA_AGT_8, ENT_AGT_7, FPR_AGT_6, GTC_AGT_7, GSS_AGT_6 — external GUI personas are documented across all script specs. State files use JSON for machine readability. `--output json` on every command enables programmatic consumption.

### NOTES_GUI_3: Transcript live-tail

`plet_invoke.py` flushes after each line write to the transcript file. Filesystem watchers (fswatch, FSEvents, inotify) see changes within ~100ms. GUI can live-tail transcript and events files during execution.

### NOTES_GUI_4: Trace merge for unified view

GUI merges `-events.ndjson` and `-transcript.ndjson` by timestamp for a unified view. Raw transcript provides full fidelity; semantic events provide structure. See formats.md § GUI Integration.

---

## NOTES_OPN: Open Questions

### NOTES_OPN_1: Consistency checking as a skill?

Could consistency passes become a standalone skill (`/consistency`) or plet subcommand (`/plet check`)? Premature for v1 — the CLAUDE.md instructions work well as agent conventions.

Key questions:
- Is it plet-specific (knows PRD ↔ NOTES ↔ PLAN ↔ reference files) or general-purpose?
- Quick/Standard/Sweep are essentially "use Grep/Read intelligently" — does a skill add value?
- What recurring drift patterns emerge from real usage?
- Should it compose with plet phases (auto-run after plan changes or refine)?

### NOTES_OPN_2: case_studies/README.md → CLAUDE.md

**Decision (2026-03-11):** The case study methodology/template file is agent directives (primary audience: agents producing case studies), not a human-facing directory index. Renamed to CLAUDE.md so Claude Code auto-loads it when agents work in the `case_studies/` directory. No separate README.md needed — the existing case studies table is in CLAUDE.md and agents get the instructions automatically without needing to be told "go read this file."

#### Case study → FEEDBACK_FOO.md pipeline formalized (2026-03-12)

**Decision:** Every case study recommendation (CASE_LOGA_R01_REC_1, CASE_LIBT_R01_REC_1, etc.) must have a corresponding FOO entry in FEEDBACK_FOO.md. FEEDBACK_FOO.md is the single intake queue — no recommendation lives only in a case study.

**Resolution states:** `[resolved]` (committed), `[resolved, unverified]` (committed but not validated in a run), `[resolved, verified]` (confirmed working in a subsequent case study).

**Pipeline:** case study recommendation → FOO entry → artifact changes → mark resolved → verify in next run.

**Where documented:** Brief rule in FEEDBACK_FOO.md intro, detailed process in case_studies/CLAUDE.md.

**Observation:** LOGA CASE_LOGA_R01_REC_7, REC8, REC10, REC11, REC12, REC13 bypassed FEEDBACK_FOO.md — went directly from case study to NOTES.md decisions to PLAN.md status. This left them with less tracking visibility. The new convention prevents this.

#### PLAN.md uses stable labels (PLAN_N prefix) — DECIDED (2026-03-14)

Positional "Part N" numbering caused cascading renumbers whenever a new part was inserted. Switched to stable label IDs (`PLAN_N`) following the project's existing append-only convention. New parts get the next available number regardless of position. A master table at the top of PLAN.md shows sequence (Seq column) and status — Seq numbers are freely reorderable display positions, PLAN_N IDs are permanent. Replaces the old sequencing diagram. Added `PLAN` to the prefix table in NOTES.md § Global Conventions.

#### Bootstrap phase before plan — DECIDED (2026-03-14)

plet's core workflow changes from **Plan → Loop → Refine** to **Bootstrap → Plan → Loop → Refine**. The bootstrap phase runs before plan and ensures the project environment is ready for plet: CLAUDE.md exists with Required Reading and Notes Discipline, NOTES.md exists, FEEDBACK_FOO.md exists, `bypassPermissions` is configured. Same pattern as /warmup and /notes bootstrap flows in session-kit. Resolves FOO_22 and FOO_23.

#### Git stash policy revised — allow with cleanup (2026-03-14)

Revises the ban from FOO_9. SPARK run showed 42 stashes despite the ban — stashing is fundamental to how agents handle parallel branch work, not an occasional shortcut. New policy: stashes are OK to use, but the agent/subagent that creates a stash must be the same agent/subagent that cleans it up. No orphaning stashes for someone else to handle. Worktree-as-default (FOO_13) should reduce stash usage naturally. Future consideration: the orchestrator creates worktrees and passes paths to subagents, rather than subagents managing their own.

#### Verify retry rate Goldilocks framing (2026-03-14)

Withdrawing FOO_36 (24% retry overhead) and FOO_37 (83% first-pass rate). A 0% retry rate means verify might not be catching anything (rubber-stamping). A very high retry rate (50%+) means implement is consistently producing bad work. Somewhere in the middle is healthy — verify catching real issues is the system working as designed. Only non-verify retries (git issues, crashes) are worth investigating. The user's framing: "there is a Goldilocks zone where we want verify to find problems because that's what it's there for, but if verify is constantly finding problems in every iteration then something is wrong."

#### Refine decomposition must happen after triage — DECIDED (2026-03-14)

Resolves FOO_41 and FOO_42. In SPARK, the refine agent created iterations on a per-feedback-item basis during triage, resulting in artificially small 1:1 FOO-to-iteration mappings. The fix: (1) triage ALL feedback/emergent items first (resolve, defer, or withdraw each), (2) look at the resolved items as a group, (3) THEN decompose into iterations with natural groupings and Goldilocks-sized chunks, (4) create state files in Step 8 after the full iteration list is reviewed and approved. No creating iterations or state files during triage.

#### Tooling decisions migrated to specs/NOTES.md (2026-03-15)

Script tooling decisions (coding standards, orchestrator analysis, script inventory, script-as-orchestrator architecture, spec file location, PLAN_FT triage analysis) moved to `specs/NOTES.md`. See that file for all tooling design rationale.

#### Ban git stash in agents (FOO_9) — DECIDED (2026-03-11), REVISED (2026-03-14)

**Problem:** LIBT run agents used `git stash` during execution. Stashes are local-only, invisible to the orchestrator/other agents/external tools, and vulnerable to garbage collection. The case study archival process didn't capture them.

**Decision:** Ban `git stash` entirely. Agents use incremental commits for crash recovery (IMP_17 already requires this), making stashes redundant and strictly worse. Eliminates the archival problem at the source.

**Alternative rejected:** Allow stashes but require cleanup or archival — adds complexity for zero benefit over incremental commits.

**Changes:** execute.md (critical rule), phase-verify.md (critical rule), prd.md (IMP_17 clarification), case_studies/CLAUDE.md (checklist item retained for older runs), FEEDBACK_FOO.md (FOO_9 resolved).

#### Stable labels for case studies — DECIDED (2026-04-03)

Adopted `CASE_{PROJECT}_{RUN}_{QUALIFIER}` as the stable label convention for all case study items. Qualifiers: section mnemonics (ARCH, TRAC), findings (W_1, F_3, S_2), recommendations (REC_1), open questions (OQ_1). Replaces ad-hoc prefixes (R_, S_, SP_, R6_) that were inconsistent across studies and impossible to grep reliably.

All 8 case studies relabeled. Files renamed from `*_CASE_STUDY.md` → `CASE_STUDY_{PROJECT}_{RUN}.md` for consistent, greppable naming. Old labels replaced in FEEDBACK_FOO.md, NOTES.md, and PLAN.md. Convention documented in `case_studies/CLAUDE.md` and `NOTES.md` prefix table.

#### FEEDBACK_FOO.md 5-phase overhaul (2026-04-03)

Systematic cleanup of FEEDBACK_FOO.md to bring cross-referencing, resolution status, and coverage up to date after Run 6:

- **Phase 0:** Label format decision (CASE_ prefix)
- **Phase 1:** Label all case studies + rename files
- **Phase 2:** Cross-reference every REC ↔ FOO item. Found 8 orphaned RECs (6 from R02 resolved-without-FOO, 2 from R06).
- **Phase 3:** Resolution pass — audit every FOO item against current code. Many PLAN_PY deferrals (FOO_11, FOO_13, FOO_22, FOO_23, FOO_29–FOO_33, FOO_35, FOO_38, FOO_40) updated to `[resolved, verified]` based on Run 6 results.
- **Phase 4:** New FOO items filed (FOO_69–FOO_72: parallel scheduling, milestone refactor, phase "unknown" CLI, worktree cleanup).
- **Phase 5:** Final consistency pass — no stale labels, no old filenames, all RECs covered.

**Result:** FOO_1–FOO_72. After full triage (2026-04-03): 70 resolved, 5 withdrawn, 3 deferred, 2 open (FOO_25 deferred, FOO_69 pending timing analysis).

#### FB → FOO rename — DECIDED (2026-04-03)

Renamed `FEEDBACK.md` → `FEEDBACK_FOO.md` and all `FB_N` → `FOO_N` to align with the `/feedback-foo` skill convention (FOO = Feedback, Observation, Oversight). 342 `FB_N` occurrences across 35 files, 56 `FEEDBACK.md` references across 10 files, ~70 bare `FB` references. Prefix table updated: `FB` → `FOO`.

#### Never-merge-to-main rule strengthened — DECIDED (2026-04-03)

SKILL.md had contradicting directives: Git Strategy said "Agents never commit to main" but the plan phase STOP message said "Merge to main when you're ready." In LOGA Run 6, the agent quoted the rule correctly but had already violated it — the suggestion was read as an instruction. Fixed in three locations: plan phase STOP message (removed merge suggestion, added explicit prohibition), loop all_complete handler ("do not merge unless asked"), Git Strategy (added "or merge" + "requires direct, explicit, confirmed human instruction"). The loop branches from the plan workstream — merging to main is not required for any plet workflow.

#### Orchestrator owns start-phase — DECIDED (2026-04-03)

FOO_61: `iter_state.py start-phase` was only called by subagents via prose instructions in phase-implement.md/phase-verify.md. In LOGA Run 2, the subagent never called it — attempt counters stayed at 0. Moved to the orchestrator: `_run_implement_phase` and `_run_verify_phase` now call `start-phase` before spawning the subagent. Attempt counting, phase timestamps, and verdict clearing are deterministic. Mock claude updated to not duplicate the increment.

#### Gate validates verdict values — DECIDED (2026-04-03)

FOO_63: `check_implement_verdict` and `check_verify_verdict` in gate_phase.py only checked for null, not valid values. Any non-null string (including typos like `"readyForVerification"`, `"complete"`) passed silently. Added value validation against `IMPLEMENT_VERDICTS` (completed, blocked) and `VERIFY_VERDICTS` (passed, rejected, blocked). Found invalid values in 4 test fixtures and the mock claude — exactly the class of bug FOO_63 described.

#### Orchestrator validates state.json at startup — DECIDED (2026-04-03)

Dead code audit found `global_state.py validate` had zero production callers. Added as the first step in `_setup_session`, before preflight or fingerprint checks. If state.json is corrupt, the orchestrator exits immediately with a clear error rather than proceeding with invalid state. Also found `get-lifecycle` and `plet_trace.py query` have no production callers — kept as diagnostic/query tools for humans and GUI.

#### Emergent ID convention: EM_{iter_id}_{N} — DECIDED (2026-04-06)

R14 showed broken EM numbering from parallel execution — EM_6 appeared twice, EM_7 three times, etc. Agents from different parallel iterations each started their own counter. Sequential fixes the race but the flat `EM_N` convention is fragile regardless. New convention: `EM_{iter_id}_{N}` (e.g., `EM_ITR_004_1`, `EM_ITR_006_3`). Namespaced to the iteration that produced it. No collisions even in parallel. Greppable per-iteration. Same pattern as the existing plet ID format (`eem_01KNJV4CJS_id001_i2`) but human-readable.

#### Abandon parallel, go sequential — DECIDED (2026-04-06)

PLAN_SEQ. Data: sequential 0.4.x had 100% completion (R06-R08: 39/39, 0 interventions). Parallel 0.5.x-0.6.x had ~70% completion with multiple interventions. R14 (v0.6.2, parallel) achieved 13/13 but wall clock (1h53m) was identical to R08 (sequential) — 8 rebase retries consumed all parallelism savings. Core goal: agents should spend time implementing/verifying, not managing plet mechanics. R06 showed 53% of implement-phase calls were infrastructure; parallel added more.

See NOTES.md § NOTES_PLAN_SEQ for full rationale, OQ decisions, and overhead analysis.

#### PLAN_RBS complete, parallel aspects superseded — DECIDED (2026-04-06)

RBS_18-25 all done. The parallel-specific aspects (conflict recovery, requeue flow, rebase-prep) are superseded by PLAN_SEQ which strips parallel entirely. RBS value that remains: linear history via wip-commit + rebase-commit on workstream, rebase onto main at loop end.

#### R14 case study — key findings (2026-04-06)

LOGA R14: v0.6.2, parallel, 13/13, 1h53m. Key findings:
- **Parallel = zero net speedup.** 8 retries (~95m) consumed the parallelism savings. Wall clock identical to R08 (sequential, 0.4.x).
- **Sequential estimate: 2h29m.** Sum of first-attempt durations (137.3m) + overhead. 36m slower than R08, but ~18m is impl→vfy gap ceremony (post-gate artifact cleanup, pre-rebase prep) that PLAN_SEQ eliminates.
- **Impl→vfy gaps are ceremony, not spawn time.** 20.9m total (avg 1.6m/iter) spent on 4-6 artifact cleanup commits between implement-completed and verify-start. With PLAN_SEQ: ~3m total.
- **Learnings/emergent: 64 entries, 41 genuine (64%).** 14 were parallel-specific (rebase conflict learnings), 7 were template/filler (gate-gaming). The genuine 41 entries (3.2/iter) are a real improvement over R06 (0.2/iter), driven by PLAN_RW reference files + plet_entries.py + prompt.py learnings injection.
- **Post-gate dirty worktree (EM_9)** is structurally broken — gate writes progress, dirties worktree, agent commits to fix, gate runs again. Recurring across multiple iterations.
- **Emergent EM ID numbering broken** by parallel execution — agents from different iterations each started their own counter.

#### Phase vocabulary exception — orchestrator and unknown — DECIDED (2026-04-03)

FOO_71: Orchestrator-level script calls had no valid phase value, producing `*-unknown-1-events.ndjson` files. Added `orchestrator` as a valid phase in plet_trace.py, plet_entries.py, and util_cli.py dispatch logger. `unknown` remains the fallback when no `--phase` is provided. Documented the taxonomy exception: trace/entry phases (`plan`, `implement`, `verify`, `refine`, `orchestrator`, `unknown`) are broader than iteration lifecycle phases (`implement`, `verify`). The broader set labels "who did the work" for observability; the narrow set is where we are in the iteration lifecycle.

#### PLAN stable codes — DECIDED (2026-04-03)

Renamed `PLAN_N` numeric IDs to 2-3 letter mnemonic codes (PLAN_SKL, PLAN_REF, PLAN_PY, PLAN_EVL, etc.) so plan items never need reordering. Same principle as stable labels. Dropped the Seq column from the master table. 101 occurrences across 12 files.

#### LOGA Run 6 timing analysis — key findings (2026-04-03)

Detailed per-iteration timing analysis from transcript files. Key findings:
- **53% of implement-phase Bash calls are plet infrastructure** (state updates, progress entries, trace events, gate checks), not application code. → PLAN_OVH
- **~150 `--help` lookups per run** — fresh subagents re-learn CLI invocation syntax. → PLAN_HLP
- **46% parallelism opportunity** — critical path 1h40m vs sequential 3h4m (1.86x speedup). → PLAN_PAR
- Verify is 0.64x of implement time (avg 4:15 vs 6:36)
- Later iterations trend longer (growing codebase)
- 43 min (23%) is pure orchestrator overhead (subagent spawn/teardown)

#### Auto-build verification report from state (2026-04-04)

`phase.py end --summary "..."` auto-builds the verification report from criteria in the state file. Agents never construct criteriaResults JSON manually. The only new inputs are `--summary` (prose headline) and optionally `--findings` (JSON array of observation strings). Everything else is derived from `update-criterion` calls already in the state file.

#### Verification report fields on update-criterion (2026-04-04)

Added `oneLiner`, `redTest`, `noTestRationale` fields to the verification object in the state file, written by `update-criterion`. Conditional requirements:
- `--red-test` required when `--phase verification --status fail`
- `--no-test-rationale` required when `--red-test none` AND `--status fail`
- Pass path: all fields auto-default (oneLiner from first sentence of evidence)

`_build_criteria_results` in phase.py reads these from state instead of hardcoding. SCHEMA_VERSION bumped to 0.4.0 (additive fields).


**Validation return convention — completed (2026-04-04):** Unified all shared validation functions in util_cli.py to a consistent return pattern:
- **Error:** always `(1, "", error_msg)` — a 3-tuple callers can `return` directly
- **Success:** returns a useful value — the validated data for `validate_enum` (returns the value) and `validate_int` (returns parsed int), `None` for checks (`validate_known_flags`, `require_kwargs`), 6-tuple for `parse_command`
- Callers distinguish by type: `if err: return err` for None/tuple checks, `if isinstance(result, tuple): return result` for value-returning validators, `if len(result) == 3: return result` for parse_command

Also cleaned up:
- `get_plet_dir` → returns 3-tuple `(plet_dir, remaining, err_str)` (was 2-tuple, error printed)
- `extract_output_flags` → returns 6-tuple with `err_msg` as 6th element (was 5-tuple, error printed)
- `parse_command` → returns `(0, help_text, "")` for help, `(1, "", err)` for error, 6-tuple for success (was `"help"`, `None`, 6-tuple — callers needed three-way check)
- `_load_session_state`, `_check_active_sessions` in session.py → return error strings instead of printing
- Zero `print(file=sys.stderr)` remaining in any validation path. Only dispatch() (the stdout/stderr boundary), orchestrator/invoke (streaming), and merge_driver (git-called) still print directly.
- ~60 call sites updated across all 17 scripts. Coverage improved: 87.1% → 87.4%.

### NOTES_OPN_3: Case study timing analysis

**Decision (2026-03-11):** Timing analysis is a required subsection of Artifact Analysis in case studies, not just a checklist item. Applied going forward (next case study), not retroactively to LOGA/LIBT. Timing data exists in both projects (state file `elapsedSeconds`, trace `phase_start`/`phase_end` timestamps, git commit timestamps, `state.json` `startedAt`/`endedAt`) but neither case study systematically analyzed it. The README template now specifies what to reconstruct, which sources to cross-reference, and how to present it (timeline table, flag gaps > 5 minutes).

### NOTES_OPN_4: PLET.md shape and content
What goes in PLET.md vs CLAUDE.md? PLET.md is plet-specific instructions that apply in *any* repo using plet; CLAUDE.md is project-specific. See Artifact Taxonomy § Memory.

**Draft (2026-03-09):** PLET.md created and populated with initial content. Sections copied (generalized, not moved) from CLAUDE.md: Common Misspellings (plet-specific subset), Decision Discipline, Consistency Passes. New sections added that belong only in PLET.md (not CLAUDE.md): What is plet?, Core Workflow, Key Concepts glossary, Artifact Taxonomy (incorporating the full 7-category taxonomy from NOTES.md with a directory tree showing the full target project root), Commit Conventions (target projects), and a placeholder Critical Requirements & Invariants section. Overlap between CLAUDE.md and PLET.md is expected and acceptable per the existing rule.

### NOTES_OPN_5: FEEDBACK_FOO.md shape and workflow — RESOLVED
Resolved 2026-03-10. See Key Design Decisions § FEEDBACK_FOO.md formalization.

### NOTES_OPN_6: Skills need a Quick Reference

If a user asks "how do I use /plet?" the agent reads the entire SKILL.md (hundreds of lines) — expensive and slow for a simple question. Python scripts solved this with `--help`. Skills could use the same pattern: a short Quick Reference section near the top of SKILL.md, or a convention where invoking `/plet help` or `/plet version` prints a summary. Not plet-specific — this is a skill-creator or session-kit convention worth proposing upstream.

### NOTES_OPN_7: Analyze OpenAI Symphony

OpenAI's [Symphony](https://github.com/openai/symphony) framework looks like it has significant overlap with plet's approach. Need to analyze it and understand:
- What concepts/patterns overlap with plet?
- What does Symphony do differently?
- Are there ideas worth incorporating?
- How does plet differentiate?

Priority: informational — not blocking any current work, but worth understanding the competitive landscape and potentially learning from their design choices.

### NOTES_OPN_8: Configuration artifact shape
Per-project behavior modification for planner, refiner, implement agent, and verify agent. No files or format defined yet. Key questions: one file or per-phase files? Declarative (key-value) or prose instructions? How does it compose with reference files? See Artifact Taxonomy § Configuration.

### NOTES_OPN_9: PRD input and disambiguation

plet's plan session should accept any existing PRD as input, regardless of which skill or tool created it, and use it to produce a `requirements.md`. The PRD generation step is upstream of plet — plet operationalizes whatever spec it's given.

Known PRD-generation approaches:
- **snarktank** — adversarial multi-persona PRD generation
- **ridl (ridl-skills:prd)** — structured PRD with requirement tables
- **plet (plan session)** — interactive spec refinement (can also generate from scratch)
- Presumably many other PRD/spec skills exist in the ecosystem

Key questions:
- When multiple PRD skills are loaded, how does the user signal which style they want? Need some disambiguation UX — "snarktank-style PRD? ridl-style? plet requirements doc? SKILLNAME-style?"
- No auto-detection of existing PRDs — the user says "read this first" or "start with this doc." But plet should let the user know that if they have an existing PRD, spec, or list of requirements, that's usually a great place to start.
- Existing docs are always just a starting point — plet's plan session asks clarifying questions if the doc is insufficient, same as starting from scratch

---

## NOTES_EXP: Example Projects

Example projects live in subdirectories of `plet-skills/`. Their purpose is to serve as real target projects for plet's first runs — exercising the full plan → loop → refine workflow against actual code, not speculative samples.

### NOTES_EXP_1: Log Analyzer CLI (Go)

**Directory:** `examples/logalyzer/` (planned)
**Language:** Go
**Input:** NDJSON log files (one JSON object per line)

**Why this is a good plet target:**
- Structured input, clear operations, easy to test
- Naturally decomposes into iterations with clean boundaries
- Each iteration is independently testable and builds on the previous
- Go's `testing` package fits red/green discipline perfectly
- NDJSON is conveniently the same format as plet's own trace output

**Proposed iterations (to compare against plet plan mode output):**

1. **Parse & validate** — read NDJSON, reject malformed lines, report line counts
2. **Filter by field** — `logalyzer filter --level=ERROR`, `--after=2026-03-01`
3. **Summary stats** — count by level, top N sources/keys, time range
4. **Search** — regex or substring match across message fields
5. **Output formats** — table, JSON summary, CSV
6. **Time bucketing** — group events by minute/hour/day, show ASCII histograms
7. **Pipe-friendly** — stdin support, composable with other Unix tools

**Decision:** Go chosen over Python (also a good fit) for compiled binary, strong stdlib for JSON/CLI, and single-binary distribution. Shell + jq rejected — testing is clunky.

### NOTES_EXP_2: Elixir Phoenix LiveView UUID Generator

**Directory:** `examples/uuidgen/` (planned)
**Language:** Elixir, Phoenix, LiveView

**Why this is a good plet target:**
- UUID variants are well-specified — clear acceptance criteria per variant
- Each variant is a natural iteration
- Multiple layers (backend logic, LiveView UI) exercise different concerns
- Elixir's `mix test` fits red/green discipline
- LiveView adds interactive UI complexity beyond pure CLI

**Proposed iterations (to compare against plet plan mode output):**

1. Project scaffold + v4 (random) generation
2. v1 (timestamp-based)
3. v5 (name-based, SHA-1) — needs namespace input
4. v7 (Unix epoch timestamp) — the modern one
5. LiveView UI — generate, display, copy-to-clipboard
6. Batch generation, format options (with/without hyphens, uppercase)
7. UUID parsing/validation — paste one in, show its version and components

### NOTES_EXP_3: Meta-goal

Run plet plan mode on each project and compare its iteration decomposition against these brainstormed iterations. This tests whether plet's interactive planning produces comparable or better decompositions. Differences are interesting data for refine.

---

## NOTES_SUB: Subplets — Flexible Inheritance Model

Subplets solve two related problems:

**1. Scale management.** A single requirements doc for dozens or hundreds of features is unmanageable — for humans and agents. The solution is multiple plets in the same repo, each scoped to a feature (or bug, issue, or any discrete work item).

**2. Existing codebase adaptation.** For a large existing codebase (100-300k+ lines), the root plet surveys the codebase and establishes a template — discovering and codifying conventions, quality ratchets, NFRs, and architectural constraints that already exist or should exist. This is a discovery step, not greenfield planning. Developers then create subplets for individual work items from their backlog.

**Developer workflow:** A developer looks at the backlog, picks a work item, creates a subplet for it. That subplet inherits the root template, gets its own branch (optionally a worktree), and the developer drives it through plan → loop → refine independently. A single developer can drive one or more subplets concurrently.

**Terminology:** The root plet is the top-level plet for the project. Subplets are plets that inherit from the root plet or from other subplets. The name "subplet" reflects that they exist within a larger project structure, not that they are structurally inferior — every subplet is a full plet (plan → loop → refine). The root plet cannot inherit; subplets can inherit from any plet (root or subplet).

**A "template" plet** is just a plet that other plets happen to inherit from — it's not structurally special. It might only ever plan/refine (defining NFRs, ratchets). Or it might loop too (implementing shared infrastructure). Doesn't matter — it's a full plet either way.

Multi-developer parallelism is a *consequence* of this decomposition, not the motivation. Different developers naturally pick up different subplets. But the primary drivers are scale management and existing codebase adaptation.

### NOTES_SUB_1: Flexible inheritance (2026-04-09, updated 2026-04-10)

**Decision:** Flexible inheritance. Any subplet can declare "I inherit from plet X" — where X can be the root plet or another subplet. The root plet cannot inherit. Inheritance is a pointer, not a rigid tree structure.

**Mechanism:** A plet reads its inheritance source at two points:
- **Plan phase** — incorporates inherited constraints into the plet's own requirements
- **Refine phase** — re-reads inheritance source, surfaces changes as emergent items

No runtime mechanism. No special state. No orchestrator awareness. Just "read a file" at two points where the agent is already reading context.

**Chains work naturally.** Plet A inherits from B, B inherits from C. At plan/refine, read up the chain.

**What typically inherits** (flexible — not every item must inherit, and projects can define their own inheritance scope):
- **NFRs** — performance budgets, accessibility standards, security requirements
- **Quality ratchets** — coverage thresholds, lint rules, type strictness levels
- **DX conventions** — error handling patterns, logging standards, naming conventions
- **Refactor goals** — file size limits, duplication thresholds, API consistency rules
- **Cross-cutting architectural decisions** — shared schemas, API contracts, dependency rules

A subplet typically tightens inherited constraints rather than weakening them, but relaxation is allowed when justified. Without inheritance, plets drift toward their own conventions and integration becomes a consistency nightmare.

**Updating snapshots.** Inheritance is snapshot-based — the subplet captures inherited constraints at plan time. Snapshots are refreshed at each plan or refine phase, picking up any changes from the source. If the source plet tightens coverage from 80% to 90%, the next plan or refine of any inheriting subplet picks it up.

### NOTES_SUB_2: What this replaces (2026-04-09)

Earlier design (NOTES_SUB_7, SUB_8, SUB_10, SUB_11) assumed a rigid parent/child hierarchy where a "parent plet" was the umbrella that decomposed into "subplets." This created problems:
- The "parent" didn't loop — so it wasn't really a plet
- Parent plan phase was a different workflow than normal planning
- One level of nesting only (arbitrary restriction)

The flexible inheritance model fixes these issues while retaining the "subplet" name. The key change: inheritance is flexible (any subplet can inherit from any plet), not a rigid single-parent tree. A template plet is just a plet. A feature subplet is a full plet. The root plet is the only one that cannot inherit.

### NOTES_SUB_3: Scenarios identified

1. **Small team, single PRD (2-3 devs):** Low coupling. Each dev runs their own plet session on their own branch. Merge point is git. Mostly works already.
2. **Large team, many features (10+ devs):** One plet per feature. A shared template plet defines NFRs/ratchets/conventions. Developers are assigned feature plets.
3. **Handoff mid-loop:** One dev starts, another picks up. Stresses institutional memory design — are `emergent.md`, `learnings.md`, and `state.json` enough for a stranger to resume?
4. **Cross-cutting dependencies:** Two plets with a sequencing constraint. Git is the integration point — one plet merges first, the other rebases.
5. **Build + QA in parallel:** Two plet sessions, same codebase, different goals, overlapping files.
6. **Refactor + feature collision:** Broad refactor vs deep feature — maximally painful merge conflicts.
7. **Spec change mid-flight:** Template plet updates NFRs while feature plets are mid-loop. Next refine picks up the change.

### NOTES_SUB_4: Key insights

**The pattern is coupling, not team size.** 2-3 devs on one PRD have high coupling. 10 devs with per-feature PRDs have low coupling *until they don't* (shared schemas, APIs). Handoff and spec-change are about *temporal* coupling.

**Git-first isolation.** Each plet runs on its own branch with its own `plet/` directory. Merge point is git. The orchestrator has zero awareness of other plets.

**plet's split state architecture already does most of the heavy lifting.** The main gap is human-level coordination (who's working on what), not agent-level coordination (solved by the DAG + lifecycle states).

### NOTES_SUB_5: Open threads
- Emergent/blocker ownership: `assignee` field on emergent entries (additive to current format)
- Refine is naturally single-threaded — one human refines at a time, others consume updated spec
- The `proj` sentinel in plet IDs is scoped to a single plet directory. If cross-plet IDs ever need disambiguation, the format will need a plet-qualified alternative.
- ~~How does the inheritance pointer work concretely?~~ → resolved: `state.json` field `"inheritsFrom": ["../../plet"]` — array of relative paths. See NOTES_SUB_11.
- ~~What happens when an inheritance chain has a conflict?~~ → resolved: last-in-array wins with warning. See NOTES_SUB_12.
- ~~Subplet orchestrator discovery~~ → resolved: each plet has its own human driver (NOTES_SUB_8)
- ~~Subplet completion rollup~~ → resolved: human-driven (NOTES_SUB_8). Optional status command could scan sibling `plet/state.json` files.
- ~~Does the orchestrator need to know about siblings?~~ → resolved: no (NOTES_SUB_8). Zero sibling awareness.
- ~~Naming convention: `{feature-name}` or `{developer-name}`?~~ → resolved: `{feature-name}`. Plets are feature decomposition, not developer assignment.
- ~~Parent plet doesn't loop~~ → resolved: no parent/child hierarchy (NOTES_SUB_1). A template plet can loop or not — it's just a plet.
- ~~What does the concrete `survey.md` artifact look like?~~ → resolved: See NOTES_SUB_13.
- ~~How does plan phase consume `survey.md`?~~ → resolved: See NOTES_SUB_13.
- ~~When re-running survey, diff or re-scan?~~ → resolved: diff, lightweight. See NOTES_SUB_16.
- ~~Subplet creation flow~~ → resolved: `/plet subplet AUTH` interactive flow. See NOTES_SUB_14.
- ~~External backlog integration~~ → resolved: manual only, no external integrations. See NOTES_SUB_15.

### NOTES_SUB_6: No cross-plet dependencies (2026-04-05)

**Decision:** Plets are independent work streams. No cross-plet dependencies in the DAG. If a plet needs work from a sibling, it is blocked until the sibling merges to the shared branch and the blocked plet rebases.

Git is the integration point, not the orchestrator. Each plet has its own DAG, its own milestones, its own refactor iterations. Cross-plet coupling is a planning error — the work should either be in the same plet or sequenced.

### NOTES_SUB_7: Inheritance of refactor goals (2026-04-05)

**Decision:** Plets share inherited refactor heuristics by default. A plet can add its own goals on top but inherits the baseline from its inheritance source.

**Subsumed (2026-04-09):** This is now a specific case of the general inheritance model (NOTES_SUB_1). Refactor goals are one of many concerns that inherit.

### NOTES_SUB_8: Each plet has its own human driver (2026-04-05)

**Decision:** Each plet is a full plet instance driven by one human. The human runs `/plet plan`, `/plet loop`, `/plet refine` independently. No cross-plet orchestration. Humans coordinate between plets the same way they coordinate between branches — through communication and git.

### NOTES_SUB_9: One branch per plet (2026-04-06, updated 2026-04-09)

**Decision:** Each plet gets its own branch. The branch is the unit of isolation — it has its own `plet/` directory with its own state, requirements, iterations, and runtime artifacts. The orchestrator has zero awareness of other plet branches.

Worktrees are optional and at the developer's discretion. plet operates on whatever `plet/` directory is in the current working directory.

**Lifecycle:**
1. Developer creates a branch for a feature plet
2. Developer checks out the branch (or creates a worktree — their choice)
3. Plet runs independently (plan → loop → refine), reading inheritance source at plan and refine
4. When done, developer merges branch back to the shared integration branch via git

### NOTES_SUB_11: Inheritance pointer mechanism (2026-04-26)

**Decision:** `state.json` field `"inheritsFrom": ["../../plet", "../auth/plet"]` — array of relative paths to source plet directories. Empty array or missing field means no inheritance (root plet).

**Mechanism:** Plan/refine reads each source's `requirements.md` and incorporates relevant items (NFR, RCH, DVX sections) into the subplet's own `requirements.md`, marking inherited items with their source. The subplet's `requirements.md` IS the snapshot — no separate snapshot file needed.

**Why array:** Supports inheriting from multiple sources (root template + a sibling's API contract). Single inheritance is the common case but multi-source is needed for real scenarios (e.g., feature plet inherits from root template AND from the auth plet's API contract).

**Rejected:**
- Convention file (`plet/inherits.md`) — over-engineered, the pointer is just "where to look"
- Separate snapshot file — the subplet's requirements.md already captures what was inherited
- Single path instead of array — artificially limits inheritance to one source

### NOTES_SUB_17: Directory layout (2026-04-26)

**Decision:** Every plet gets a project ID directory under `plet/`. Root plet is always `plet/ROOT/`. Subplets are siblings: `plet/AUTH/`, `plet/BILLING/`, etc.

```
myproject/
  plet/
    ROOT/          ← root plet (reserved name)
      state.json
      requirements.md
      iterations.md
      ...
    AUTH/           ← subplet
      state.json   ← inheritsFrom: ["../ROOT"]
      ...
    BILLING/        ← subplet
      state.json
      ...
```

- `plet_dir` is always `plet/{PROJECT_ID}` — uniform, no special cases
- `ROOT` is reserved — it's the default inheritance source
- Subplets get `inheritsFrom: ["../ROOT"]` by default on creation
- During plan, user can opt out of ROOT inheritance or add other subplets
- Breaking change from current `plet/` layout → 0.8.0

**Rejected:**
- `plet/subplets/{name}/plet/` — double-nested, ugly paths
- `plet/subplets/{name}/` as plet dir — breaks "plet dir is always called plet/" convention (moot now — plet dir is `plet/{ID}`)
- Sibling layout outside `plet/` — splits plet artifacts across top-level dirs
- User-picked root name — ambiguous which plet is root without a marker; ROOT as reserved is unambiguous

### NOTES_SUB_18: Branch naming — flat, no projectId (2026-04-26)

**Decision:** `plet/{pletId}/loop{N}/workstream`. Mirrors the directory layout 1:1. No project-level ID in branches — plet ID (ROOT, AUTH) is sufficient since branches are repo-scoped.

Examples:
- `plet/ROOT/loop1/workstream`
- `plet/AUTH/loop1/workstream`
- `plet/AUTH/loop1/ITR_003`
- `plet/ROOT/plan1/workstream`
- `plet/ROOT/refine1/workstream`

**Supersedes:** Old convention `plet/{projectId}/subplet/{subId}/loop{N}/workstream` — designed for parent/child hierarchy which was replaced by flat sibling model (NOTES_SUB_17).

**Rejected:**
- `plet/{projectId}/{pletId}/loop{N}/...` — extra segment that's identical for every branch in the repo
- Keeping `subplet/` segment — contradicts flat directory layout

### NOTES_SUB_16: Survey re-run behavior (2026-04-26)

**Decision:** Diff against previous survey, but lightweight — a note at the end of the survey prompt telling the agent to compare against the existing `survey.md` and highlight what changed. No dedicated diff tooling. This is rare enough that a prompt-level instruction suffices.

**Rejected:**
- Full re-scan (overwrite) — loses visibility into what changed
- Dedicated diff tooling — over-engineered for a rare operation

### NOTES_SUB_15: External backlog integration (2026-04-26)

**Decision:** Manual only. Developer reads their backlog (GitHub Issues, Linear, etc.), creates a subplet, and writes requirements during the plan phase. No external integrations.

**Rationale:** Matches plet's zero-external-dependencies philosophy. The developer is the filter — not every issue becomes a subplet. MCP integration could be added later if real usage shows the need, but it's not blocking.

### NOTES_SUB_14: Subplet creation flow (2026-04-26)

**Decision:** `/plet subplet AUTH` starts an interactive flow in SKILL.md. Creates the subplet directory structure, sets up `state.json` with `inheritsFrom`, creates the branch, and offers to start plan immediately. CLI tooling (`plet_tools.py`) does the mechanical work under the hood.

**Rationale:** Subplet creation is a one-time setup that benefits from guidance — inheritance source, naming, branch creation. The interactive flow ensures nothing is missed. Power users can call the underlying CLI directly.

**Rejected:**
- Raw CLI only — no guidance for first-time users
- Manual setup + plan detection — too easy to miss steps (inheritance pointer, branch naming)

### NOTES_SUB_13: survey.md format (2026-04-26)

**Decision:** `survey.md` uses structured sections matching `common.md` template categories — NFR, RCH, DVX, ARC, etc. Each section contains discovered values with evidence (where in the codebase the convention was found). Plan agent reads `survey.md` and lifts items directly into `requirements.md` during the plan phase.

**Rationale:** Survey's purpose is to inform requirements. Matching the structure means plan can consume it mechanically — no interpretation step needed. The evidence subsections (e.g., "coverage threshold 85% — from `pyproject.toml` `fail_under`") give the human traceability during plan review.

**Rejected:**
- Free-form by discovery method — requires plan agent to interpret and categorize, adding a lossy translation step
- Defer — the format is straightforward given the decision that survey feeds requirements

### NOTES_SUB_12: Inheritance conflict resolution (2026-04-26)

**Decision:** Last-in-array wins. Order of `inheritsFrom` determines priority — later entries override earlier ones. Plan/refine agent warns when it detects a conflict (e.g., "Source A says 80% coverage, Source B says 90% — using 90% from B since it's later in inheritsFrom"). Human can reorder or override during the interactive session.

**Rationale:** Conflicts are rare in practice. Most subplets inherit from one source. When multiple sources exist, the array order is an explicit, visible decision the developer made. Adding complexity (strictest-wins logic, error handling) for a rare case isn't worth it.

**Rejected:**
- Strictest wins — adds implicit logic that's hard to reason about ("which direction is stricter for a naming convention?")
- Error on conflict — too much friction for a rare case
- Explicit override with justification — over-engineered when array ordering + a warning suffices

### NOTES_SUB_10: `/plet survey` — existing codebase adaptation (2026-04-10)

**Decision:** Existing codebase adaptation is a new plet command (`/plet survey`), not a separate skill or project. The output of a survey is exactly what the root plet template needs, and keeping it inside plet means the inheritance mechanism works without glue.

**Motivation:** plet needs to work with existing large codebases (100-300k+ lines), not just greenfield projects. A developer joining a large webapp shouldn't have to write requirements from scratch. The root plet should discover and codify what's already there.

**plet workflow becomes:** Survey → Plan → Loop → Refine (survey is optional, used for existing codebases).

**What survey produces (decision: 1C):** Both — a `survey.md` captures raw findings (discovered conventions, patterns, quality levels, architectural constraints), then the plan phase distills these into `requirements.md` (NFRs, ratchets, conventions as formal requirements). Two artifacts because the raw survey has value beyond what gets distilled.

**Iterative, not one-shot (decision: 2B):** Survey can be re-run to pick up codebase changes. Initial survey establishes the template; re-runs update it as the codebase evolves (including changes made outside of plet by other developers).

**Developer workflow with survey:**
1. Root plet runs `/plet survey` on the existing codebase → produces `survey.md`
2. Root plet runs `/plet plan` → distills survey into `requirements.md` (template)
3. Developer looks at backlog (GitHub issues, Linear, etc.), picks a work item
4. Developer creates a subplet that inherits from the root template
5. Developer drives subplet through plan → loop → refine on their own branch

**Deferred:**
- How survey handles context window limits on a large codebase (implementation detail)
- ~~Subplet creation flow~~ → resolved: See NOTES_SUB_14.
- ~~External backlog integration~~ → resolved: See NOTES_SUB_15.

**Open questions added to NOTES_SUB_5:**
- ~~What does the concrete `survey.md` artifact look like?~~ → resolved: See NOTES_SUB_13.
- ~~How does plan phase consume `survey.md`?~~ → resolved: See NOTES_SUB_13.
- ~~When re-running survey, diff or re-scan?~~ → resolved: See NOTES_SUB_16.

---

## NOTES_SIA: Self-Improvement Analysis

Self-Improvement Analysis workflows are planned for plet v3.x.y — not a v1 concern
Future Consideration #11


### NOTES_SIA_1: Why this is load-bearing

Most skills are static instructions written for today's model capabilities. They accumulate workarounds that become dead weight as models improve. execute.md alone is ~430 lines — some will be unnecessary in 6 months. Without a feedback loop, plet calcifies.

### NOTES_SIA_2: Runtime artifacts are uniquely well-positioned

plet already produces structured, categorized data about its own performance: learnings capture what tripped agents up, emergent items capture spec gaps, trace files capture the full decision chain, progress captures pass/fail patterns. That's exactly the telemetry needed for self-analysis. Most systems would have to bolt on instrumentation — plet already has it.

### NOTES_SIA_3: Design tension — meta-loop symmetry

plet improving its own PRD is refine-on-refine. The refine session already analyzes runtime artifacts to improve the *target project's* spec. Self-improvement is the same pattern aimed inward. Elegant symmetry, but "improve the project" and "improve the tool" need a clear boundary. A separate skill or mode is the right approach.

### NOTES_SIA_4: Things to watch for

- **Model-capability vs design-flaw distinction:** Remove guardrails no longer needed vs fix heuristics that were always wrong. Different remedies.
- **Testability of version bumps:** PRD changes need validation against a reference project. Otherwise self-edits are flying blind.
- **Bootstrapping question:** Can plet use plet to improve plet? Appealing but version consistency problem.

### NOTES_SIA_5: Case study as a self-improvement mechanism

The logalyzer case study (CASE_STUDY_LOGA_R01.md) demonstrated a concrete self-improvement workflow: run plet on a real project → collect user feedback and autonomous branch analysis → synthesize into recommendations → apply improvements → re-run the same project from the same plan checkpoint to measure the delta. This is manual self-improvement, but the structure is clear and repeatable:

1. **Run** — build something with plet
2. **Observe** — user feedback (subjective) + branch analysis (data-driven)
3. **Recommend** — specific, actionable changes to plet artifacts
4. **Apply** — update reference files, spec, schemas
5. **Re-run** — same project, same plan, improved system — direct before/after comparison

This pattern could eventually be automated as part of the self-improvement skill planned for v3.x.y. The case study format itself could become a template for post-loop retrospectives.

### NOTES_SIA_6: Consistency passes — a complete self-improvement cycle

The consistency pass documentation went through a full draft → use → observe → redesign cycle:

1. **Draft** — four numbered "flavors" codified during skill build (Phase 2), documented in CLAUDE.md and PLET.md
2. **Use** — applied heavily during case study feedback work (CASE_LOGA_R01_REC_1–REC13), vocabulary cleanup, convention changes
3. **Observe** — the user noticed the agent had stopped announcing flavors and asked: "have your passes changed or evolved?" This was the monitoring event — not a formal mechanism, but a human noticing behavioral drift from documentation
4. **Analyze** — reviewed actual usage and found: flavor 1+3 were always combined (→ Standard), flavor 2 (Deep) was never used standalone, the vocabulary cleanup used a miniplan pattern not in the taxonomy, and the numbered naming was awkward to say in conversation
5. **Redesign** — replaced numbered flavors with Quick/Standard/Sweep/Structural based on actual practice. Dropped Deep, added Sweep (validated by the vocabulary cleanup miniplan)

The Sweep pattern originated from the vocabulary cleanup miniplan (`VOCABULARY_CLEANUP.md`): `2ee9b83` (taxonomy standardize), `c7a5b6b` (cleanup execution — ~69 changes across 12 files), `95176e8` (miniplan file deleted after completion). Notably, the miniplan survived a context compaction — the agent picked up the categorized inventory and continued executing without losing track. This durability is what makes it a distinct level: the plan lives on disk, so it's compaction-safe.

Key insight: the "monitoring" was organic — a human observing that practice had diverged from documentation. This is the self-improvement loop working at the simplest level: human notices drift, surfaces it, agent analyzes usage data, both redesign together. No telemetry or automation needed — just attention and willingness to question whether the docs still match reality.

This validates the CLAUDE.md Self-Improvement policy: "If you've seen it twice, it's a pattern. If it's not written down, it will be forgotten by the next session." The consistency pass conventions *were* written down, but they calcified — the redesign came from noticing they no longer matched practice.

### NOTES_SIA_7: Why capturing this now matters

Thinking about self-improvement during v1 design means the artifacts won't accidentally make it hard later. The runtime artifact formats, structured trace data, and separation of concerns all serve double duty as operational output and self-improvement telemetry.
