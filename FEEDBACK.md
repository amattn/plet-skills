# FEEDBACK.md

Meta-observations about plet itself — process issues, instruction gaps, tooling friction. Distinct from learnings (target project knowledge) and emergent items (execution discoveries). See PLET.md § FEEDBACK.md for format and conventions.

---

## Logalyzer Run 1 (2026-03)

### FB_1: State JSON files not updated incrementally [state] [timing]

Intermediate writes to the JSON state files didn't happen — they were typically only written at the end. Expected: state files updated as work progresses so that a crashed or interrupted agent leaves recoverable state.

`[resolved]` → R_2 in execute.md and verify.md (intermediate state writes mandated)

### FB_2: No intermediate commits [git] [timing]

Similarly, intermediate commits didn't happen during iteration execution. Work was only committed at the end. Expected: incremental commits during implementation so progress isn't lost on interruption.

`[resolved]` → R_1 in execute.md (commit-after-each-criterion rule)

### FB_3: Autonomous agents asked for confirmation [autonomy] [blocking]

Autonomous subagents asked "should I proceed?" once or twice during execution. This is effectively blocking — autonomous agents should never prompt for human input. The whole point of the loop is unattended execution. Caused a ~5 hour stall.

`[resolved]` → R_9 in execute.md and verify.md (explicit "never prompt for confirmation" rule)

### FB_4: tagBeforeSquash should be always-on [git] [config]

`tagBeforeSquash` as an opt-in flag is the wrong default. Tags should always be created before squash. Replace with `cleanupTagAutomatically` — the question isn't whether to tag, it's whether to clean up the tag afterward. When cleaning up, note the commit hash in progress.md and log that the tag was removed.

`[resolved]` → R_4: `tagBeforeSquash` replaced with `cleanupTagsAutomatically` (default false). Tags always created, commit hash logged in progress.md at creation and deletion.

### FB_5: Project needs a short project ID [config] [naming]

There needs to be a project ID in short form (e.g., `LOGA` for log analyzer). Used for namespacing branches, tags, and potentially state files across projects or subplets.

`[resolved]` → R_6 in plan.md Step 2 and state-schema.md (project ID defined during plan session)

### FB_6: Agents should not work on main branch [git] [autonomy]

Agents worked directly on `main`. The `logalyzer_workstream` branch was created manually. There should be a naming convention for workstream branches, and agents should never commit to main directly.

`[resolved]` → R_5 in execute.md and PLET.md (workstream branch conventions)

### FB_7: Batched verify commits too coarse [git] [artifacts]

One commit contained four iterations verified together — a rejection and three passes sharing a single commit. Each verify should be its own commit for clean revert, bisect, and audit.

`[resolved]` → R_3 in verify.md (one verify = one commit)

### FB_8: Uncommitted progress.md at end of run [artifacts] [timing]

The orchestrator left progress.md uncommitted at end of run, requiring manual cleanup. The system should auto-commit all runtime artifacts at the end of each phase and at loop completion.

`[resolved]` → R_1/R_2 (intermediate commits and state writes cover this case)

### FB_9: Agents used git stashes — not captured in case study archival [git] [artifacts]

During the LIBT run, agents made use of `git stash` during execution (visible in `git stash list` post-run). The case study archival process currently preserves branches and tags but does not account for stashes. Stashes are local-only git objects that can be garbage collected — if not explicitly preserved, they are silently lost. The archival checklist should include: (1) `git stash list` to inventory stashes, (2) convert relevant stashes to commits or tags before deleting branches, (3) document stash contents in the case study artifact analysis.

`[resolved]` → Banned `git stash` in agents (EX_17, execute.md, verify.md). Stashes are redundant given incremental commits. Case study checklist retained for older/non-compliant runs.
