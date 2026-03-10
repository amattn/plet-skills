# Build Plan: plet-skills

## Current State

Parts 1–3 complete (skill, reference files, packaging). Part 4 (case study feedback) in progress — applying R_1–R_13 improvements from the first real plet run.

---

## Parts 1–3: Foundation ✓ COMPLETE

### Part 1: SKILL.md — Main Orchestrator ✓ COMPLETE

Single entry point `/plet` with routing logic based on state detection.

**File:** `skills/plet/SKILL.md`

### Part 2: Reference Files ✓ COMPLETE

6 reference files injected into subagent prompts. Schemas first, then session prompts.

All reference files live under `skills/plet/references/`.

| Sub-part | File | Purpose |
|-----------|------|---------|
| 2a.1 | `references/formats.md` | Runtime artifact format specs |
| 2a.2 | `references/state-schema.md` | JSON schemas for state files and trace NDJSON |
| 2b.1 | `references/plan.md` | Plan session instructions |
| 2b.2 | `references/execute.md` | Implementation subagent prompt |
| 2b.3 | `references/verify.md` | Verification subagent prompt |
| 2b.4 | `references/refine.md` | Refine session instructions |

### Part 3: Packaging ✓ COMPLETE

Plugin metadata and distribution scaffolding.

**Files:** `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`

---

## Part 4: Case Study Feedback Loop ← ACTIVE

First real-world usage of plet (logalyzer) revealed 13 improvement recommendations (R_1–R_13). This part applies those improvements.

**Detailed analysis:** `case_studies/LOG_ANALYZER_CASE_STUDY.md`

### R_1–R_13 Status

| Rec | Description | Status |
|-----|-------------|--------|
| R_1 | Intermediate commits during impl | ✓ Done (`8ac341a`) |
| R_2 | Intermediate state writes | ✓ Done (`8ac341a`) |
| R_3 | One verify = one commit | ✓ Done (`83bd146`) |
| R_4 | Tag lifecycle redesign (`cleanupTagAutomatically`) | Deferred |
| R_5 | Workstream branch conventions | ✓ Done (`cf150ca`) |
| R_6 | Short project ID | ✓ Done (`cf150ca`) |
| R_7 | Mandatory learnings/emergent entries | ✓ Done (`8ac341a`) |
| R_8 | Trace file generation — decide: real feature or remove | Open |
| R_9 | Subagent non-blocking | ✓ Done (`8ac341a`) |
| R_10 | Artifact quality monitoring | Open |
| R_11 | Branch isolation during parallel execution | Open |
| R_12 | FEEDBACK.md formalization | In progress |
| R_13 | Co-Author tag convention | Open |

### Additional work done during Part 4

- Vocabulary cleanup: "X phase" → "X session" for Level 1 terms (~69 changes across 12 files)
- Taxonomy consolidation in NOTES.md (vocabulary hierarchy, document terms, artifact categories)
- "Development loop" → "development orchestrator" rename
- Project name/ID collection step added to plan.md (Step 2)
- Numbers-letters presenting options convention formalized in PLET.md
- Session Bootstrap moved near top of PLET.md
- Compaction recovery defense validated (3-layer: CLAUDE.md → PLET.md → auto-memory)
- SKILL.md frontmatter description rewritten with session summaries

### Remaining Part 4 work

- **R_12:** Finish FEEDBACK.md design (format, audience, when to write, promotion path)
- **R_8:** Decide on trace files — real feature or remove from spec
- **R_10:** Artifact quality monitoring — verify agent checks artifact completeness
- **R_11:** Branch isolation — hard-scope each impl agent to its iteration branch
- **R_13:** Co-Author tag convention — standardize across all agent-authored commits
- **R_4:** Tag lifecycle redesign (deferred — lower priority)
- Consistency pass flavor documentation review

### Part 4 next steps (from case study)

- **Part B:** Re-run logalyzer from plan checkpoint (`7cecbf5`) with improved plet
- **Part C:** Compare Run 1 vs Run 2, identify impact of changes
- **Part D:** Broader testing (refine session, harder project, case study template)

---

## Part 5: Examples (deferred, trigger met)

Real artifacts exist on the `logalyzer_workstream` branch (archived as `archive/loga/run1/*` tags). Examples can now be captured from real output rather than written speculatively.

**Files (planned):**
- `examples/README.md` — overview of examples
- `examples/requirements-snippet.md` — sample requirements.md excerpt
- `examples/iterations-snippet.md` — sample iterations.md excerpt
- `examples/state.json` — sample global state file
- `examples/state/ID_001.json` — sample per-iteration state file
- `examples/progress-snippet.md` — sample progress.md entries
- `examples/learnings-snippet.md` — sample learnings.md entries
- `examples/emergent-snippet.md` — sample emergent.md entries
- `examples/trace-snippet.ndjson` — sample trace NDJSON

---

## Part 6: Notes Skill

A standalone `/notes` skill that formalizes the living development notes pattern used during plet-skills development.

**Source spec:** `prd-notes-skill.md`

**Key responsibilities:**
- Maintain a `NOTES.md` alongside the PRD as institutional memory
- Capture decisions immediately — what was decided, why, and rejected alternatives
- Quote user preferences and principles in their own words
- Track PRD section approval status
- Log decision rationale when the PRD is updated
- Document invariants and critical requirements as checkable rules
- Keep NOTES.md scannable (headers, bold, bullets) for fast agent orientation

**File:** `skills/notes/SKILL.md`

---

## Part 7: Feedback Skill

Formalize the FEEDBACK.md pattern that emerged organically during the logalyzer run. Depends on FEEDBACK.md design from Part 4 (R_12).

**Key responsibilities:**
- Maintain a `FEEDBACK.md` as institutional memory about plet itself (meta-observations)
- Distinct audience from learnings.md (learnings = target project, feedback = plet process)
- Define entry format, categories, and promotion path to memory/config artifacts
- Agent and human write access — agents append during loop, humans curate during refine

**File:** `skills/feedback/SKILL.md` *(or integrated into plet skill — TBD)*

**Depends on:** Part 4 R_12 design decisions

---

## Sequencing

```
Part 1     SKILL.md                          ── foundation           ✓ COMPLETE
              ↓
Part 2     reference files (schemas +        ── schemas & prompts    ✓ COMPLETE
            session prompts)
              ↓
Part 3     plugin metadata                   ── packaging            ✓ COMPLETE
              ↓
Part 4     case study feedback loop          ── apply R_1–R_13      ← ACTIVE
              ↓
Part 5     examples/ (deferred)              ── capture from real run
              ↓
Part 6     notes skill                       ── standalone /notes
              ↓
Part 7     feedback skill                    ── standalone /feedback or plet integration
```

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md references the reference files by relative path (e.g., `references/execute.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
