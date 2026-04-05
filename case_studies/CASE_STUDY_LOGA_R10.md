# Case Study: LOGA Run 10

Tenth logalyzer run. Second run on v0.5.1 (dirty-tree fix). Validates parallel orchestrator fix.

## Observations (in progress)

### CASE_LOGA_R10_OBS_1: Plan phase doesn't use NLR format for choices

The plan agent presented two separate questions (review depth + project ID) as a flat A/B/C list instead of NLR format (numbers-letters with recommendations). CLAUDE.md § Preferences specifies NLR. The plan.md reference file should reinforce this when the agent presents choices to the user.

**Expected:**
```
1. Review depth:
   A. Full review (Steps 4-8)
   B. Quick skim then initialize
   C. Initialize directly
   Rec: C — artifacts look complete

2. Project ID:
   A. LOGA
   B. LOGAZ
   C. ANLZR
   Rec: A — short, matches prior runs
```

**Actual:** Single flat A/B/C list mixing both questions, no recommendation markers.

**Fix:** Add NLR guidance to `references/plan.md` § iteration review or a general "presenting choices" section.
