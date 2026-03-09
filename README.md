# plet-skills

**PLET = Progress, Learnings, Emergent, Trace** — the four runtime artifacts the system produces. Also works phonetically as Plan + Execute.

plet is a Claude Code skill that provides a spec-driven autonomous development loop. It combines interactive planning with autonomous execution, verification, and iterative refinement — all running natively inside Claude Code without requiring an external harness.

## Core Workflow

```
        HUMAN-DRIVEN                AUTONOMOUS IMPLEMENTATION LOOPS
  ┌──────────────────────┐         ┌────────────────────────────────┐
  │                      │         │                                │
  │   ┌───────────┐      │         │      ┌─────────┐               │
  │   │   Plan    │──────┼────────▶│      │ Execute │──────┐        │
  │   └───────────┘      │         │      └───┬─────┘      │        │
  │         ▲            │         │          ▲            ▼        │
  │         │            │         │          │    ┌──────────┐     │
  │   ┌─────┴──────┐     │         │          └────│  Verify  │     │
  │   │   Refine   │◀────┼─────────┤               └──────────┘     │
  │   └────────────┘     │         │                                │
  │                      │         │   loop continues until done    │
  └──────────────────────┘         └────────────────────────────────┘
```

### Phases

- **Plan** (human-driven) — Interactive requirements creation and iteration decomposition. The human steers; the agent structures. Produces a PRD (`requirements.md`), iteration definitions (`iterations.md`), and runtime state (`state.json`).
- **Loop** (autonomous) — The impl→verify cycle. Each iteration goes through two internal phases:
   - **Execute** — Agents implement iterations using red/green test discipline. Each iteration runs on its own git branch. Subagents handle independent iterations in parallel.
   - **Verify** — Independent verification in a fresh context window. The verification agent does not read implementation diffs — it verifies the *result*, not the *process*. This prevents rubber-stamping.
   - Iterations continue unassisted until complete, blocked, or paused.
- **Refine** (human-driven) — Reviews the four runtime artifacts plet is named after, triages emergent items, updates the spec, and re-plans:
  - **Progress** — What was done (append-only historical record)
  - **Learnings** — Agent-facing knowledge (helps future agents work better)
  - **Emergent** — Human-facing items (design decisions, requirement gaps, assumptions needing validation)
  - **Trace** — Full agent I/O logs per iteration for traceability

### Using plet

**Starting a new project:** Invoke `/plet` in a fresh project. The skill enters the Plan phase — asks clarifying questions, generates a requirements draft, and presents each feature area for review. Once approved, it breaks requirements into iterations with dependencies, presents those for review, initializes state, and offers to start building.

**The autonomous loop:** Strongly inspired by Ralph loops, the autonomous loop is designed to run for hours unattended. Once execution starts, plet identifies eligible iterations and spawns implementation subagents (in parallel if independent). Each subagent implements with red/green discipline, updating state and artifacts in real time. On completion, a verification subagent spawns in a fresh context and independently confirms acceptance criteria. If verification passes, the iteration is marked complete (frozen — never modified again) and merged. If it fails, it cycles back to implementation with new criteria. The orchestrator re-evaluates and spawns the next eligible iterations.

**Refinement:** When the loop completes, blocks, or the user wants to check in, `/plet` routes to the Refine phase. The skill presents pending emergent items one by one for triage — the user can approve, modify, reject, or defer each. Blocked iterations are surfaced with full context from all four artifact types. After triage, the skill updates the spec, modifies unfrozen iterations or creates new ones to reflect the changes, and offers to resume execution.

### Project Structure

```
plet/
├── requirements.md          # PRD (plan artifact)
├── iterations.md            # Iteration definitions (plan artifact)
├── state.json               # Global state (runtime)
├── state/
│   ├── ID_001.json          # Per-iteration state
│   ├── ID_002.json
│   └── ...
├── progress.md              # What was done (runtime artifact)
├── learnings.md             # Agent-facing knowledge (runtime artifact)
├── emergent.md              # Human-facing items (runtime artifact)
└── trace/
    ├── ID_001-impl-1.ndjson # Trace logs per iteration/phase/attempt
    ├── ID_001-verify-1.ndjson
    └── ...
```

## Key Concepts

### Single Entry Point

Users invoke `/plet` and the skill reads the project state to determine what to do. The routing logic:

- No `plet/` directory? → Plan phase
- Requirements exist but no iterations? → Plan phase (decomposition)
- Iterations queued or in progress? → Loop phase
- All iterations complete? → Refine phase
- Blocked with nothing in progress? → Refine phase

Users can force a phase: `/plet plan`, `/plet loop`, `/plet refine`, `/plet status`.

### Verification Independence

The verification agent verifies the *result*, not the *process*. It does not initially read implementation diffs or review how the work was done. It reads the codebase as it stands, runs checks, and independently confirms acceptance criteria are met. This prevents rubber-stamping and ensures genuine independent validation. If it needs to dig deeper, it can read diffs — but never as a starting point.

### State on Disk

All plan, progress, and execution state is persisted to files. Any fresh agent can pick up work without prior context. This enables parallelization (multiple agents working on independent iterations) and ensures verification independence (fresh context window, no contamination from the implementation agent).

### Dependency-Aware Parallelism

Iterations form a dependency graph (DAG), not a strict sequence. Independent iterations run concurrently via subagents. The orchestrator re-evaluates eligible work after each iteration completes. When in doubt, add the dependency — missing dependencies are dangerous (agent wastes a cycle), while false dependencies are harmless (only reduce parallelism slightly).

```
   ID_001 (scaffolding)
      │
      ├──────────┐
      ▼          ▼
   ID_002     ID_003      ← parallel: no dependency relationship
      │          │
      ├──────────┘
      ▼
   ID_004 (depends on both)
```

### Separation of Artifacts by Audience

Each runtime artifact serves a distinct audience:

| Artifact | Audience | Purpose |
|----------|----------|---------|
| `progress.md` | Humans | What was done — append-only narrative log |
| `learnings.md` | Agents | Codebase patterns, tool quirks, techniques, debugging tips |
| `emergent.md` | Humans | Design decisions, requirement gaps, assumptions needing validation |
| `trace/` | Debugging | Full agent I/O logs per iteration in NDJSON format |

### Artifact Sync via Fingerprints

The three plan artifacts (`requirements.md`, `iterations.md`, `state.json`) stay in sync via lightweight fingerprints — nested ID arrays, not file hashes. If requirements change but iterations haven't been regenerated, plet detects the drift and warns the user.

### Blockers are Last Resort

Agents prefer making a decision and documenting it in `emergent.md` over blocking. Blocking is reserved for situations where no reasonable decision can be made without human input. When a blocker does occur, it must be documented across all four artifact types before the agent returns — the quality of blocker documentation determines whether the human can help.

### Git Branch Strategy

Each iteration works on its own branch (`plet/loop/{iteration_id}`). Agents commit incrementally for crash recovery, then squash into a single commit per phase. Completed iterations rebase onto the main branch with fast-forward merge for linear history.

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

## About This Repo

This repository contains planning artifacts (PRD, design notes) and will also contain the plet skill itself (SKILL.md + reference files) as it is developed.

A GUI application for visualizing and monitoring plet execution is planned as a **separate project**. The GUI would read plet's state files (`plet/state.json` and `plet/state/{iteration_id}.json`) to provide real-time visibility into iteration progress, agent activity, and lifecycle status. The state format is explicitly designed to support external consumers.

## Acknowledgments

plet wouldn't exist without [Ralph skills](https://github.com/snarktank/ralph) by snarktank and [chief](https://github.com/MiniCodeMonkey/chief) by MiniCodeMonkey. These were the first implementations of Ralph loops I came across, and they fundamentally changed how I think about AI engineering. The ideas of spec-driven autonomous iteration, structured runtime artifacts, and fresh-context execution are all theirs — plet is an attempt to take those ideas further.

plet also builds directly on [ridl-skills](https://github.com/amattn/ridl-skills), the author's earlier Claude Code plugin providing a 4-step pipeline for PRD-driven autonomous development using the RIDL (Ralph Iteration Definition List) system.
