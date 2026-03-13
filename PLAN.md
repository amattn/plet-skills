# Build Plan: plet-skills

## Current State

Parts 1–3 complete (skill, reference files, packaging). Part 4 (case study feedback) in progress — applying improvements from LOGA and LIBT case studies. Open items tracked in FEEDBACK.md (FB_1–FB_21).

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

Two case studies completed. All feedback tracked in `FEEDBACK.md` (FB_1–FB_21).

### LOGA Run 1 (logalyzer, Go, 13 iterations)

**Analysis:** `case_studies/LOG_ANALYZER_CASE_STUDY.md`

Produced R_1–R_13. Status:

| Rec | Description | Status |
|-----|-------------|--------|
| R_1 | Intermediate commits during impl | ✓ Done (`e25e952`) |
| R_2 | Intermediate state writes | ✓ Done (`e25e952`) |
| R_3 | One verify = one commit | ✓ Done (`037a2ab`) |
| R_4 | Tag lifecycle — always tag, `cleanupTagsAutomatically` | ✓ Done |
| R_5 | Workstream branch conventions | ✓ Done (`bad4261`) |
| R_6 | Short project ID | ✓ Done (`bad4261`) |
| R_7 | Mandatory learnings/emergent entries | ✓ Done (`e25e952`) |
| R_8 | Trace file generation — decided, not fully implemented | → FB_11 |
| R_9 | Subagent non-blocking | ✓ Done |
| R_10 | Artifact quality monitoring — decided, not fully implemented | → FB_12 |
| R_11 | Branch isolation — decided, not validated | → FB_13 |
| R_12 | FEEDBACK.md formalization | ✓ Done → FB_14 |
| R_13 | Co-Author tag convention — decided, not validated | → FB_15 |

### LIBT Run 1 (todo-cli, Python, 5 iterations)

**Analysis:** `case_studies/TODO_CLI_CASE_STUDY.md`

Produced S_1–S_8. All tracked as FB_10–FB_21 in FEEDBACK.md. Key improvements over LOGA: learnings/emergent dramatically better, zero orchestrator stalls, 100% first-pass verify rate. Recurring issues: state schema drift, progress format drift, trace inconsistency.

### Additional work done during Part 4

- Vocabulary cleanup: "X phase" → "X session" for Level 1 terms (~69 changes across 12 files)
- Taxonomy consolidation in NOTES.md (vocabulary hierarchy, document terms, artifact categories)
- "Development loop" → "development orchestrator" rename
- Project name/ID collection step added to plan.md (Step 2)
- Numbers-letters presenting options convention formalized in PLET.md
- Session Bootstrap moved near top of PLET.md
- Compaction recovery defense validated (3-layer: CLAUDE.md → PLET.md → auto-memory)
- SKILL.md frontmatter description rewritten with session summaries
- Case study methodology formalized (`case_studies/CLAUDE.md`)
- Case study → FEEDBACK.md pipeline formalized
- Git stash banned in agents (FB_9)
- Linear history and green/rebase/green invariant enforced (EX_16)
- Version corrected to 0.1.0 across all files (history rewritten)

### Part 4 next steps

- Resolve open FB items (FB_12, FB_16–FB_20) — fix artifact gaps before rerunning

---

## Part 5: Notes Skill ← NEXT

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

## Part 6: Feedback Skill

Formalize the FEEDBACK.md pattern that emerged organically during the logalyzer run.

**Key responsibilities:**
- Maintain a `FEEDBACK.md` as institutional memory about plet itself (meta-observations)
- Distinct audience from learnings.md (learnings = target project, feedback = plet process)
- Define entry format, categories, and promotion path to memory/config artifacts
- Agent and human write access — agents append during loop, humans curate during refine

**File:** `skills/feedback/SKILL.md` *(or integrated into plet skill — TBD)*

**Depends on:** ~~Part 4 R_12 design decisions~~ Cleared — R_12/FB_14 resolved. FEEDBACK.md exists with format conventions and intake pipeline.

---

## Part 7: Comparison Runs

Re-run case studies with improved plet to validate fixes.

- **7a:** Re-run logalyzer from plan checkpoint (`203c58a`, rebased from original `7cecbf5`) with improved plet
- **7b:** Compare Run 1 vs Run 2, identify impact of changes
- **7c:** Broader testing (refine session, harder project)

---

## Part 8: Examples (deferred, trigger met)

Real artifacts exist archived as `casestudy/logalyzer/run1/*` and `casestudy/todo-cli/run1/*` tags. Examples can now be captured from real output rather than written speculatively.

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

## Sequencing

```
Part 1     SKILL.md                          ── foundation           ✓ COMPLETE
              ↓
Part 2     reference files (schemas +        ── schemas & prompts    ✓ COMPLETE
            session prompts)
              ↓
Part 3     plugin metadata                   ── packaging            ✓ COMPLETE
              ↓
Part 4     case study feedback loop          ── apply feedback       ← ACTIVE
              ↓
Part 5     notes skill                       ── standalone /notes    ← NEXT
              ↓
Part 6     feedback skill                    ── standalone /feedback or plet integration
              ↓
Part 7     comparison runs                   ── rerun + validate
              ↓
Part 8     examples/ (deferred)              ── capture from real run
```

## Notes

- Each file will be presented for review before moving to the next
- SKILL.md references the reference files by relative path (e.g., `references/execute.md`)
- All reference files live under `skills/plet/references/` to keep the skill self-contained
- Version starts at 0.1.0 across all files
- The PRD stays in `prd.md` as the source of truth; these skill files implement it
- **Watch: combined injection size.** verify.md (~515 lines) + formats.md + state-schema.md sections + requirements + learnings all get injected into the verify subagent prompt. Monitor whether the combined payload leaves enough context for the verify agent to do its actual work.
