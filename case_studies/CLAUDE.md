# Case Studies

Case studies are a critical feedback mechanism for improving plet. Each case study analyzes a complete plet run — artifacts, code, process — to identify what worked, what didn't, and what to change.

## Why Case Studies Matter

- They're the only way to evaluate plet end-to-end (planning through execution through verification)
- They surface systemic issues that individual runs don't reveal (e.g., state schema drift appeared in both LOGA and LIBT)
- They track whether fixes actually work across runs (comparison tables)
- They produce concrete, actionable recommendations grounded in evidence

## Existing Case Studies

| File | Project | Language | Iterations | Key Finding |
|------|---------|----------|------------|-------------|
| `LOG_ANALYZER_CASE_STUDY.md` | LOGA (logalyzer) | Go | 13 | First run baseline; learnings/emergent underutilized |
| `TODO_CLI_CASE_STUDY.md` | LIBT (todo-cli) | Python | 5 | Learnings/emergent dramatically improved; state schema still drifts |

## Standard Sections

Every case study should follow this structure. Not every section will be equally deep for every project, but all should be present.

### Section 1: Plan

- **Goal** — what are we trying to learn from this case study?
- **Methodology** — artifact analysis, code analysis, comparison, findings
- **Project profile table** — project ID, language, type, iteration count, test count, source file count, dependencies, loop/refine session counts

### Section 2: Artifact Analysis

The core of every case study. Analyze all plet runtime artifacts systematically.

#### Iteration summary table
- ID, title, status, impl attempts, verify attempts, dependencies
- Completion rate and verify first-pass rate (key metrics)
- Parallel groups identified

#### Per-iteration analysis
- Acceptance criteria count and types
- Red/green cycle details (failing tests → passing tests)
- Key patterns or decisions that emerged
- Learnings produced by this iteration

#### Runtime artifact analysis (the PLET artifacts)

- **progress.md** — entry count, formatting consistency, completeness
- **learnings.md** — entry count, themes, cross-iteration references, whether later iterations actually used earlier learnings
- **emergent.md** — entry count, themes, whether emergent→learning pipeline functioned
- **State files (plet/state/ID_*.json)** — schema consistency across files, metadata richness, lifecycle correctness
- **Trace files (plet/trace/)** — coverage (how many phases have traces?), event schema consistency, field naming

#### Timing analysis

Reconstruct the timeline from all available sources. This is not optional — timing data reveals orchestrator overhead, stalls, and phase cost distribution that are invisible from artifact content alone.

**What to reconstruct:**
- Total wall-clock duration (session start to loop complete)
- Per-iteration duration (first impl event to final verify event)
- Per-phase duration (impl vs verify separately)
- Per-criterion elapsed seconds (from state file `elapsedSeconds` fields)
- Idle/gap time between iterations (orchestrator overhead, stalls, blocking)
- Parallel group wall-clock (how long did the parallel batch take vs sequential sum?)

**Sources (cross-reference all of them):**
- `plet/state.json` — `startedAt`/`endedAt` per session (coarsest)
- `plet/state/ID_*.json` — `timestamp` and `elapsedSeconds` per criterion (finest grain, but coverage varies)
- `plet/trace/*.ndjson` — `phase_start`/`phase_end` event timestamps (reliable when traces exist)
- Git commit timestamps — bracket each phase (always available)
- `plet/progress.md` — sometimes includes timestamps in entries

**Present as:** A timeline table with iteration, phase, start time, end time, and duration. Flag any gaps > 5 minutes — these indicate stalls, blocking, or orchestrator overhead worth investigating.

#### Missing or incomplete artifacts
- Which expected artifacts are absent? (requirements.md, iterations.md, traces, etc.)
- Impact on resumability and refinability

### Section 3: Code Analysis

Review the produced codebase as a human developer would.

- **Architecture** — layer diagram, dependency flow, separation of concerns
- **Code quality** — idiom adherence, type annotations, error handling, naming
- **Test quality** — test count by file, patterns used (fixtures, isolation, mocking vs real), coverage assessment
- **Would a human write this?** — the key question. Where does agent-produced code diverge from human norms?

### Section 4: Comparison with Prior Case Studies

Side-by-side metrics table against all prior case studies. Key dimensions:

- Verify first-pass rate
- Learnings entries (per iteration)
- Emergent entries (per iteration)
- State schema consistency
- Progress format consistency
- Trace coverage
- Cross-iteration knowledge transfer
- Spec artifact preservation
- Branch contamination incidents
- Human intervention needed

Track **trends** — improved, regressed, no change.

### Section 5: Findings & Recommendations

- **What worked well** — with evidence
- **What didn't work well** — with evidence
- **Surprises** — unexpected behaviors or outcomes
- **Recommendations** — numbered (S_1, S_2, ...) with concrete options where applicable
- **Open questions** — things we still don't know

### Meta

- Case study number in sequence
- Loop/refine session count
- Any limitations on the analysis (e.g., no branch analysis, missing artifacts)

## Checklist: Things to Analyze

Use this as a sweep checklist when writing a case study. Not everything will apply to every run.

### Quantitative Metrics
- [ ] Iteration completion rate (complete / total)
- [ ] Verify first-pass rate (passed first attempt / total)
- [ ] Verify rejection count and reasons
- [ ] Total test count (final)
- [ ] Tests per iteration (to track growth)
- [ ] Source file count
- [ ] Learnings entry count (total and per-iteration)
- [ ] Emergent entry count (total and per-iteration)
- [ ] Trace file coverage (phases with traces / total phases)
- [ ] Impl attempt count per iteration (ideally 1)
- [ ] Verify attempt count per iteration (ideally 1)

### Timing and Duration
- [ ] Time elapsed per loop session (wall clock)
- [ ] Time elapsed per iteration (impl + verify)
- [ ] Time elapsed per phase (impl vs verify separately)
- [ ] Timestamps in state files (start/end per criterion, per phase)
- [ ] Trace file timestamps (can reconstruct timeline)
- [ ] Idle time between iterations (orchestrator overhead)
- [ ] Total run duration (plan start to loop complete)

Sources for timing data:
- `plet/state/ID_*.json` — may contain elapsed seconds per criterion or phase
- `plet/trace/*.ndjson` — event timestamps can reconstruct timeline
- `plet/progress.md` — sometimes includes timestamps
- Git commit timestamps — impl and verify commit times bracket each phase
- `plet/state.json` — may contain session-level timestamps

### Artifact Quality
- [ ] State file schema consistency (do all ID_*.json use the same structure?)
- [ ] Progress.md formatting consistency (same format throughout?)
- [ ] Trace event schema consistency (same field names throughout?)
- [ ] Learnings cross-referencing (do later iterations reference earlier learnings?)
- [ ] Emergent→learning pipeline (do emergent items get promoted to learnings?)
- [ ] Spec artifact preservation (are requirements.md and iterations.md present?)
- [ ] Fingerprint integrity (do fingerprints in state.json match spec artifacts?)

### Process Quality
- [ ] Red/green discipline followed? (failing test before implementation)
- [ ] Branch strategy — any contamination or merge conflicts?
- [ ] Parallel iteration handling — conflict mitigation strategies used?
- [ ] Agent autonomy — any instances of agents asking for confirmation?
- [ ] Commit hygiene — squashing, audit tags, proper messages?
- [ ] Human intervention required? When and why?

### Code Quality
- [ ] Idiomatic for the language?
- [ ] Appropriate abstraction level? (no over-engineering)
- [ ] Test isolation patterns? (tmp dirs, env vars, dependency injection)
- [ ] Dead code? Unused imports?
- [ ] Error handling appropriate for the context?
- [ ] Dependencies match spec? (no surprise additions)

### Cross-Run Patterns (for 2+ case studies)
- [ ] Which issues recur across runs? (systemic vs one-off)
- [ ] Which issues were fixed? (verify the fix worked)
- [ ] Does artifact quality degrade with project size?
- [ ] Does learnings utilization scale or drop off?
- [ ] Do different languages surface different issues?

## Recommendations for New Case Studies

1. **Vary project size.** LOGA (13 iterations) and LIBT (5 iterations) give two data points. A 20+ iteration project would test whether patterns hold at scale.

2. **Test the refine loop.** Zero refine phases across both case studies. This is the biggest untested part of plet.

3. **Test multi-loop runs.** Both case studies completed in a single loop session. A project requiring loop→refine→loop would test the full cycle.

4. **Vary languages.** Go and Python so far. A statically-typed language with a heavier toolchain (Rust, Java) would surface different friction.

5. **Track timing from the start.** Set up timing instrumentation before the run, not after. Git commit timestamps + trace file timestamps + state file timestamps should give a complete picture.

6. **Preserve all artifacts.** Ensure requirements.md and iterations.md survive into the plet/ directory. LIBT lost them — this needs to be caught early.

7. **Include user feedback.** LOGA had a dedicated "User Feedback" section (FB_1 through FB_8) that was valuable. LIBT folded this into findings. Both approaches work, but direct user observations during the run are worth capturing separately.
