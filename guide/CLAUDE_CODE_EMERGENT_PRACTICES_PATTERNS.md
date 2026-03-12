# Claude Code: Emergent Practices & Patterns

> Practical lessons from building plet — emergent practices and patterns for getting Claude Code to work well as an autonomous agent.

## Highest Leverage

If you read nothing else, these are the tips with the biggest payoff relative to effort. The top three form a reinforcing loop: fight passive execution (Claude surfaces observations) → institutional memory (observations get captured) → pattern evolution (captured observations become conventions become skills). Each one makes the others more effective. Tips 4 and 5 (Chat UX, Standardize conventions) are examples of what this loop produces — patterns that were noticed, captured, and formalized.

| Tip | Why it's high leverage | Effort |
|-----|----------------------|--------|
| **Fight passive execution** | Single highest-leverage tip. Root cause behind at least half the other tips. If Claude naturally volunteered opinions, flagged concerns, and recommended instead of presenting — you wouldn't need NLR, you wouldn't need "flag concerns proactively," you wouldn't need "show work then recommend." It's one behavioral deficit that fans out into a dozen symptoms. Every instruction that says "proactively do X" is a patch for this one underlying bias. | Medium — requires persistent CLAUDE.md instructions and even then you'll still have to pull opinions out sometimes |
| **Institutional memory needs explicit investment** | Without it, every session starts from near-zero. It's the difference between a collaborator with amnesia and one with a notebook. NOTES.md, FEEDBACK.md, auto-memory, state files, runtime artifacts — none of these happen naturally. Every piece of persistent knowledge requires deliberate design: what gets captured, where it lives, when it's written, who reads it. | Medium — designing the system takes thought, but maintaining it is just discipline |
| **Pattern evolution** (observation → convention → skill) | The only tip that's self-improving. It's the mechanism for generating all the other tips. Recognize patterns, capture them in NOTES.md, promote to CLAUDE.md when confirmed, evolve into skills when complex enough. The system gets better every session. Depends on institutional memory — you can't evolve patterns you didn't capture. | Medium-Low — noticing is easy, but promoting through the lifecycle (NOTES → CLAUDE.md → skill) takes real revisiting and formalization |
| **Chat UX is real UX** | Numbers-letters, batch shorthand, "ok" to approve, code blocks for indentation — small interaction design investments that compound across every session. You interact with Claude hundreds of times a day; even 5% friction reduction is massive. | Low — define formats once, reference them by shorthand (NL, NLR) |
| **Standardize vocabulary, formats, and conventions** | Claude drifts on terminology and formats constantly. One defined term or format eliminates an entire class of ambiguity — across sessions, across agents, through compaction. But don't overstandardize: lock down the plumbing, leave the problem-solving free. | Low — write a vocabulary table and ID format spec, takes an hour |

### Honorary Mentions

These are slightly more situational — still high value, but they tend to matter most in specific contexts (TDD workflows, agent decomposition, empirical debugging) rather than universally across every session.

| Tip | Why it's high leverage | Effort |
|-----|----------------------|--------|
| **Iterations must fit in one context window** | If you're decomposing work for autonomous agents, this is a hard architectural constraint. Get it wrong and nothing downstream works. Context compaction mid-iteration causes the agent to lose implementation state — it forgets what it was doing. Err aggressively on smaller iterations; two small ones are always safer than one large one. Not flashy, but load-bearing. | Low — it's a sizing decision, not a tool |
| **Red/green test discipline** | Well-known in TDD but transforms autonomous agent work. Failing test → implement → green gives crash recovery (tests tell the next agent where you left off), progress visibility, and confidence that changes work. Without it, agents write code with no verification anchor. | Low — it's a discipline, not a tool |
| **Independent verification (goldilocks)** | Early signal, one data point — but the spectrum matters. Self-verification rubber-stamps. Adversarial verification invents phantom issues to justify its existence. Independent verification (separate agent, no knowledge of process, checks the result) is the sweet spot. | Medium — requires separate agent contexts and clear verification prompts |
| **Test assumptions empirically** | Claude can test things about itself *right now* — spawn a subagent, try a prompt, check what's in context. Costs minutes. Prevents building entire systems on wrong assumptions. The subagent context inheritance findings in this doc came from exactly this: a guess, a test, a correction. | Very low — just ask "can you test this right now?" |

---

## Session & Memory Management

- **Auto-memory bootstrap:** On first interaction, write a `MEMORY.md` to the auto-memory directory with non-negotiable behaviors. This ensures critical rules are in context from message one, before CLAUDE.md is even read.
- **Mandatory acknowledgment on file reads:** Require Claude to explicitly state which instruction files it read. Silent reads lead to stale behavior — the user should never have to wonder.
- **Post-compaction re-read:** Compaction is a memory loss event. After compaction, re-read CLAUDE.md and all required files immediately. Don't trust compressed memory — re-read the source of truth.
- **Session greeting:** A short joke on first response. Trivial but confirms the session bootstrapped correctly and read CLAUDE.md.
- **Write approved content to disk immediately:** Never defer writing to end of session. The file on disk is the source of truth. If context is lost, the approved text survives.

## Subagent Patterns

- **Fresh context windows for independence:** Each subagent (impl, verify) runs in a fresh context. No shared memory between them. This prevents contamination and ensures genuine independence.
- **Subagents never ask for confirmation:** Autonomous agents must never prompt "should I proceed?" — it's effectively blocking. Resolve ambiguity by making a decision and documenting it.
- **Verification independence:** The verify agent checks the *result*, not the *process*. It reads the codebase as-is and runs checks independently. No reading impl diffs first. Prevents rubber-stamping.
- **Subagents inherit CLAUDE.md and auto-memory, but not skills or tools:** Tested empirically — subagents (via the Agent tool) receive CLAUDE.md and MEMORY.md in their context automatically. They do NOT get the skills list or deferred tools. They also don't inherit conversational context — they start fresh with only your prompt plus the auto-injected project files. (Note: Agent SDK custom subagents are different — those do NOT get CLAUDE.md by default and must use explicit `skills` injection.)
- **The "may or may not be relevant" caveat can backfire:** CLAUDE.md content is injected with a system note saying "this context may or may not be relevant to your tasks." This can cause Claude to deprioritize or ignore CLAUDE.md instructions, especially short or unconventional ones. If you have critical instructions in CLAUDE.md, make them assertive and unambiguous — don't rely on subtle hints.
- **All state lives on disk:** Subagents never inherit prior context — they read state files. Any fresh agent can pick up work without prior conversation history.

## Context Window Discipline

- **Iterations must fit in one context window:** The single most important decomposition constraint. Compaction mid-iteration causes the agent to lose implementation state. Two small iterations > one large one.
- **Watch combined injection size:** When injecting reference files into subagent prompts, monitor total payload. Leave enough context for the agent to do its actual work.
- **Orchestrator canary writes:** After each significant action, write a progress entry with critical state (project ID, branch, counts). After compaction, recover by reading the last canary entry.

## Prompt Engineering

- **Show work, then recommend:** (1) Show full content for context, (2) proactively surface recommendations before asking for approval. Don't wait to be asked.
- **Numbers-letters decision format:** Numbered questions with lettered options. Wrap in code blocks — without them, markdown collapses indentation. Single question = letters only, drop the number.
- **Suggest concrete options:** Always offer 2–3 concrete choices. Don't make the user invent from scratch. Agent recommends, human decides.
- **Blockers are last resort:** Prefer making a decision and documenting it over blocking for human input. Document the decision in emergent.md so it can be reviewed later.

## Decision Capture

- **Update notes immediately, never defer:** After every decision, before moving to the next topic. "I'll catch up later" always fails. Decisions accumulate faster than memory.
- **Decision cascading:** After capture in NOTES.md, cascade through all affected artifacts: PRD, reference files, schemas, PLAN.md. A decision that lives only in one place will be lost or contradicted.
- **Batch answers still get individual entries:** "1A, 2C, 3D" = three separate NOTES.md entries with individual rationale.

## Consistency & Drift Prevention

- **Four levels of consistency passes:** Quick (grep one pattern), Standard (grep stale patterns + cross-ref IDs), Sweep (inventory all instances, categorize, get approval), Structural (full semantic scan, spawn agent). Run Quick/Standard proactively.
- **Fingerprints for artifact sync:** Nested ID arrays + timestamp. If requirements change but iterations haven't been regenerated, detect the drift automatically.
- **Announce which level you ran:** Always tell the user. Transparency builds trust in the process.

## Self-Improvement Loops

- **Surface patterns immediately:** If you've seen it twice, it's a pattern. If it's not written down, it'll be forgotten by next session. Propose, don't wait to be asked.
- **Observation taxonomy:** NOTES.md for low-commitment observations ("might be a pattern"). CLAUDE.md for formalized policy ("this is how we do things"). Capture first, promote when confirmed.
- **Common misspellings table:** Document voice-input misheard terms in a lookup table. Keeps Claude from being confused by dictation artifacts.
- **FEEDBACK.md for meta-observations:** Separate from runtime artifacts. Captures process issues, instruction gaps, tooling friction about the system itself. Tagged by category.

## Testing & Verification

- **Red/green discipline:** Write a failing test (red), confirm it fails, implement until green, run full suite. Incremental tests are crash recovery — they tell the next agent where you left off.
- **Intermediate commits for crash recovery:** Commit after each red step and green step. Work that isn't committed is work that can be lost. Squash later.
- **Anti-slop bias:** Assume the first correct version has hidden debt. Don't rubber-stamp because tests pass. Look for: TODOs, catch-all handlers, O(n²), missing cleanup, injection vectors.
- **Convergence signal:** An iteration is done when critiques reduce to cosmetic/stylistic only. Variable naming and whitespace = done. Logic issues = another cycle.
- **Evidence must be specific:** "Tests pass" is not evidence. Name the test, describe what it asserts, include the outcome, note the scope of the run.
- **Independent verification is the goldilocks zone:** Three levels — *verification* (same agent checks its own work, rubber-stamps everything), *independent verification* (separate agent checks the result with no knowledge of the process), and *adversarial verification* (agent actively tries to break it, finds phantom issues, nitpicks to justify its existence). Independent is the sweet spot: genuine validation without invented problems.

## Git Workflow

- **Never commit to main:** Use workstream branches. `plet/{projectId}/loop{N}/workstream` for integration, individual branches per iteration.
- **Squash with audit tags:** Commit incrementally for crash recovery, squash per phase. Always create an audit tag before squashing to preserve the pre-squash state.
- **Linear history via fast-forward merge:** Rebase iteration branch onto workstream, fast-forward merge. Clean linear history.
- **Archive tags for cleanup:** `archive/plet/{projectId}/loop{N}/{path}`. Lightweight, survive `git fetch --prune`, don't pollute branch listings.

## Runtime Artifacts

- **Append-only operations:** Use `cat >>` not read-then-overwrite. Avoids conflicts with parallel agents writing to the same file.
- **Entry fencing:** Wrap entries in unique boundary lines so git merge can distinguish entries from parallel agents and resolve without conflicts.
- **Separate artifacts by audience:** progress.md → humans (narrative). learnings.md → agents (patterns, techniques). emergent.md → humans (decisions, gaps). trace/ → debugging (full I/O logs).
- **Real-time state updates:** Update state files as you work, not batched at the end. External consumers read these to know what the agent is doing. Batch updates make the system appear dead.
- **Heartbeat updates:** Update `agentActivity` as you transition between activities. 5+ minutes stale = assumed crashed.

## Architecture Insights

- **Parallel execution is messier than sequential:** Merge conflicts, cross-branch contamination, batched operations. Sequential is cleaner in every dimension. Parallelism is valuable but has real costs.
- **Dependency graph over strict sequence:** Iterations form a DAG. Independent ones run concurrently. When in doubt, add the dependency — missing dependencies waste cycles, false dependencies only reduce parallelism.
- **Atomic writes for state:** Write to temp file, then POSIX rename. Direct writes OK when each file has a single writer.
- **Skip criteria when impossible:** Mark `skipped` with required rationale. Don't block on criteria that can't be satisfied — document and move on.

## Vocabulary Discipline

- **Standardizing vocabulary pays off:** Claude drifts on terminology — "phase" vs "session" vs "step," "task" vs "iteration" vs "story." Every ambiguous term becomes a source of subtle misunderstanding that compounds across sessions and agents. Invest early in a precise vocabulary with clear definitions. It also survives compaction better (one known definition reconstructs meaning from compressed context) and lets fresh subagents get up to speed faster (no guessing what a term means). The upfront cost is small; the downstream savings are enormous.
- **Standardizing formats pays off:** Same logic as vocabulary — ID formats, commit message conventions, file naming patterns, artifact structures. When Claude knows there's exactly one way to write an ID (`XX_N`) or name a branch (`plet/{projectId}/loop{N}/...`), it stops improvising. Reduces drift, survives compaction, and eliminates a whole class of "which format did we use?" questions.
- **Don't overstandardize:** Standardize the things that need to be consistent (vocabulary, IDs, formats, branch names). But too much standardization constrains agents — they lose autonomy and the ability to be creative where it matters. Standardize the plumbing, not the problem-solving.
- **"Session" not "phase" for top-level:** Plan/Loop/Refine are sessions. Phase is impl/verify within an iteration. Mixing these causes confusion at every level.
- **ID format: underscore, append-only:** `XX_N` format. Deleted items leave gaps — never renumber, never reuse. Numbers don't imply ordering; document position does.
- **Zero-pad in filenames only:** `ID_001.json` for lexical sort. No zero-padding in prose or artifact content.

## Interaction Patterns

- **Claude defaults to passive execution — fight it:** Claude's natural mode is: receive instruction, execute literally, wait for next command. You will constantly find yourself asking "any thoughts?" and "any recommendations?" The instruction to "proactively surface recommendations" exists in CLAUDE.md *because* the behavior doesn't come naturally — and even with the instruction, you'll still have to pull opinions out. Expect this and design your instructions to counteract it aggressively.
- **Chat interfaces have UX too — invest in it:** Numbers-letters format (NL/NLR), batch answer shorthand ("1A, 2C, 3D"), code blocks for indentation, "ok" to approve — these are all UX improvements for a text-based interface. Small investments in interaction design compound across every session. Don't accept the default conversational style as given.
- **Concrete options beat open-ended questions:** "What do you think?" puts all the work on the human. "Here are three options, I recommend B because..." is what a good collaborator does. Always suggest 2-3 concrete choices with a recommendation. NLR (numbers-letters with recommendations) exists because NL alone is just a menu with no guidance.
- **Thematic lists over flat lists:** When presenting anything longer than ~5 items — commit messages, summaries, options, changes — group by theme with headers. A flat list of 15 bullets is a wall; 3 themed groups of 5 is scannable. This applies to commit bodies, review summaries, consistency pass results, anything. Claude defaults to flat enumeration; push for thematic grouping.
- **Do it now, not later:** Writing to disk, updating NOTES.md, running consistency passes, cascading decisions — Claude's instinct is to defer and batch. "I'll update notes at the end" always fails. Decisions accumulate faster than memory. Force immediacy.
- **Flag concerns before being asked:** If something looks wrong, suboptimal, or inconsistent — say so. Don't present it neutrally and wait for the human to notice. The human is paying for your judgment, not just your execution.
- **Institutional memory needs explicit investment:** NOTES.md, FEEDBACK.md, state files, runtime artifacts — none of these happen naturally. Left to its defaults, Claude will keep everything in conversation context and lose it at compaction or session end. Every piece of institutional memory (for both agents and humans) requires deliberate design: what gets captured, where it lives, when it's written, who reads it.

## Pattern Evolution

- **Good patterns evolve:** Observations start in NOTES.md ("we've done this twice"). If confirmed, they get promoted to CLAUDE.md as policy. If they become complex enough, they become skills. This is the natural lifecycle — observation → convention → automation. Examples: consistency passes started as an ad-hoc checklist, became a four-level framework, and may eventually become a skill. NOTES.md discipline and FEEDBACK.md followed a similar arc.
- **Recognize the promotion signals:** When you find yourself writing the same CLAUDE.md instruction in multiple projects, it might be a skill. When a NOTES.md entry keeps getting referenced, it should be in CLAUDE.md. When a FEEDBACK.md item keeps recurring, it's a requirement. The pattern is: if you keep re-encoding it, it needs to live at a higher level of abstraction.
- **Test your assumptions empirically:** Claude can test things about itself right now — spawn a subagent, try a prompt, check what's in context. Don't rely on docs or reasoning about how things "should" work. "Can you test this right now?" is one of the highest-leverage questions you can ask. The subagent context inheritance findings in this doc came from exactly this: a guess, a test, a correction. Costs minutes, prevents building on wrong assumptions.
