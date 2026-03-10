# Vocabulary Cleanup Plan

77 occurrences of "X phase" across 14 files where "X" is plan/loop/refine (Level 1 terms). Each needs manual review — not all should change.

## Rules

**Change to "session"** when referring to:
- A specific invocation: "during the refine phase" → "during the refine session"
- A countable event: "after two loop phases" → "after two loop sessions"
- The bounded period of work: "the loop phase runs autonomously" → "the loop session runs autonomously"

**Keep "phase"** when:
- It's a section heading/label: `### Plan Phase`, `### Loop Phase` — these are navigation aids, not taxonomy
- It refers to impl/verify (Level 3): "the impl phase", "verification phase" — correct usage
- It's inside plan.md/execute.md/verify.md/refine.md referring to itself: "this phase" — the reference files *are* phase-level instructions
- It's a PRD section title: "3.4 Execute Phase (EX)" — structural, not prose

**Judgment calls:**
- "route to the Plan phase" — could go either way; "Plan phase" here is more of a label
- "entering the plan phase" — session is slightly better but phase isn't wrong
- Routing flowchart labels (`PLAN phase`, `LOOP phase`) — keep as-is, they're labels

## File triage (by count)

| File | Count | Strategy |
|------|-------|----------|
| NOTES.md | 21 | Review each — mix of historical decisions and active docs |
| prd.md | 13 | Review each — section titles stay, requirement prose changes |
| SKILL.md | 9 | Review each — headings stay, routing labels stay, prose changes |
| plan.md | 7 | Mostly self-referential ("this phase") — likely keep most |
| case_studies/ | 6 | Skip — historical record |
| refine.md | 5 | Mostly self-referential — likely keep most |
| formats.md | 4 | Review — likely "plan phase" references in format descriptions |
| README.md | 3 | Change — user-facing prose |
| PLAN.md | 2 | Change — build plan prose |
| prd-notes-skill.md | 2 | Change — prose |
| state-schema.md | 2 | Review — field descriptions |
| CLAUDE.md | 1 | Review |
| PLET.md | 1 | Review |
| verify.md | 1 | Likely self-referential — keep |

## Execution order

1. Skip: case_studies/ (historical)
2. Skip: plan.md, execute.md, verify.md, refine.md self-references ("this phase")
3. Do first: README.md, PLAN.md, prd-notes-skill.md (small, clear prose)
4. Do next: SKILL.md, prd.md (larger, need judgment on headings vs prose)
5. Do last: NOTES.md (largest count, most nuanced)
6. Spot-check: formats.md, state-schema.md, CLAUDE.md, PLET.md
