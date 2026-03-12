# Self-Improving Ratchets for Claude Code

> Presentation outline — two parts, one arc. Part 1 is the patterns. Part 2 is what happens when you systematize them.

**What this is:** The structural outline for the talk. Each numbered section is a presentation segment. For detailed content behind Part 1 tips, see `CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md`. For decisions and rationale, see `guide/NOTES.md`.

**Audience:** Mixed — some new to Claude Code, some experienced. Tips accessible to newcomers, depth rewarding for experienced users.

**Format/length:** Slide deck with annotated transcripts (for presentation) + standalone written guide (for reference). Modular design — scales from lightning (~15 min, Part 1 only) to deep dive (~45-60 min, both parts + Q&A). Part 2 leads with the *how* (architectural decisions) with enough *what* for context.

---

## Part 1: The Ratchet

How to make Claude Code get better every session — and keep the gains.

### 1. The Problem: Every Session Starts from Zero

**Slide 1.1 — Title: "The Groundhog Day Problem"**
- You spend 20 minutes getting Claude up to speed on your project conventions
- Claude nails it — follows every pattern, uses the right terminology, flags the right concerns
- Session ends. Next morning: "Hello! How can I help you today?"
- *Talking point:* This is the universal Claude Code experience. Not a bug, a default.

**Slide 1.2 — "Passive Execution Mode"**
- Claude's default posture: receive instruction → execute literally → wait for next command
- Won't volunteer opinions. Won't flag concerns unless asked. Won't recommend — just lists options.
- The human carries all institutional knowledge, all quality standards, all context
- *Talking point:* It's not that Claude *can't* do these things. It defaults to not doing them. That's the gap we're going to close.

**Slide 1.3 — "What Drifts Without a Ratchet"**
- Terminology: "phase" vs "session" vs "step" — used interchangeably, meaning shifts
- Conventions: ID format changes mid-project, commit message style wanders
- Lessons: you discover the same gotcha in session 5 that you discovered in session 2
- *Talking point:* This isn't about Claude being forgetful. It has no memory *to* forget. Everything you don't write down disappears.

### 2. The Core Loop

**Slide 2.1 — "The Ratchet: Observe → Capture → Formalize"**
- **Observe** — fight passive execution. Surface patterns. "We've done this twice — is this a convention?"
- **Capture** — write it down *now*. NOTES.md, CLAUDE.md, MEMORY.md. Never defer.
- **Formalize** — promote observations to conventions to policy to skills
- Each step feeds the next. Each turn locks in progress. Progress doesn't slip backward.
- *Talking point:* This is the entire talk in one slide. Everything that follows is either a technique for turning this loop or what happens when you automate it.

**Slide 2.2 — "The Reinforcing Loop"**
- The top 3 patterns form a cycle: fight passive execution → institutional memory → pattern evolution → (back to) fight passive execution
- Fight passive execution: Claude surfaces observations
- Institutional memory: observations get captured
- Pattern evolution: captured observations become conventions become skills
- Each one makes the others more effective
- *Talking point:* This isn't three independent tips. It's one system. Weaken any leg and the others degrade.

### 3. Fight Passive Execution

**Slide 3.1 — "The Single Highest-Leverage Tip"**
- Root cause behind at least half the other tips in this talk
- Every instruction that says "proactively do X" is a patch for this one bias
- If Claude naturally volunteered opinions, flagged concerns, and recommended instead of listing — you wouldn't need most of these tips
- *Talking point:* This is the one thing that, if you could fix completely, would make half the other advice unnecessary. You can't fix it completely — but you can get 80% of the way there.

**Slide 3.2 — "From Menu to Recommendation"**
- Default Claude: "Here are options A, B, and C." (waits)
- What you want: "Here are options A, B, and C. I recommend B because..."
- NLR (numbers-letters with recommendations) — a format that *forces* a recommendation
- Show work, then recommend: (1) show full content for context, (2) surface recommendations *before* asking for approval
- *Talking point:* The format is doing behavioral work here. NLR isn't just a display preference — it's a structural nudge that changes what Claude produces.

> **📋 ANNOTATED TRANSCRIPT CANDIDATE:** Show a real before/after — same question, first with flat options, then with NLR and a recommendation. Callout: "Notice Claude didn't offer an opinion until the format required one."

**Slide 3.3 — "Flag Concerns Before Being Asked"**
- If something looks wrong, suboptimal, or inconsistent — say so *before* the human notices
- The human is paying for judgment, not just execution
- CLAUDE.md instruction: "Flag concerns before being asked" — and even with the instruction, you'll still have to pull opinions out sometimes
- *Talking point:* Design for the failure mode. The instruction helps a lot but doesn't fully solve it. Plan to ask "any concerns?" at key moments even after you've told Claude to volunteer them.

**Slide 3.4 — "Concrete Options Beat Open-Ended Questions"**
- "What do you think?" puts all the work on the human
- "Here are three options, I recommend B because..." is what a collaborator does
- Always suggest 2-3 concrete choices. Don't make the user invent from scratch.
- *Talking point:* This is a specific instance of fighting passive execution — but it's worth calling out because the failure mode ("What would you like to do?") is so common.

### 4. Institutional Memory

**Slide 4.1 — "Nothing Persists Without Deliberate Design"**
- Left to its defaults, Claude keeps everything in conversation context
- Context compaction = memory loss event. Session end = total amnesia.
- Every piece of persistent knowledge requires deliberate design: what gets captured, where it lives, when it's written, who reads it
- *Talking point:* This isn't optional. Without institutional memory, every other technique in this talk has a one-session half-life.

**Slide 4.2 — "The Memory Stack"**
- **Auto-memory bootstrap** (MEMORY.md) — loads before CLAUDE.md, ensures critical rules survive from message one
- **CLAUDE.md** — project-level policy. "This is how we do things."
- **NOTES.md** — institutional memory. Decisions, rationale, rejected alternatives.
- **FEEDBACK.md** — meta-observations about the process itself
- **State files** — structured runtime state (for autonomous agents)
- *Talking point:* Each layer serves a different audience and persistence need. The stack is ordered by "how early does this need to be in context?"

**Slide 4.3 — "Write Now, Never Later"**
- "I'll catch up on notes later" always fails
- Decisions accumulate faster than memory
- After every decision, before moving to the next topic — update NOTES.md
- Batch answers ("1A, 2C, 3D") still get individual entries
- *Talking point:* This is a discipline, not a feature. No tool enforces it — you enforce it through CLAUDE.md instructions and vigilance. The cost of writing is seconds. The cost of lost rationale is re-litigating settled decisions next session.

> **📋 ANNOTATED TRANSCRIPT CANDIDATE:** Show a CLAUDE.md excerpt with the "write immediately, never defer" instruction, then a real interaction where Claude captures a decision in NOTES.md mid-conversation — before the human even asks.

**Slide 4.4 — "Compaction Is a Memory Loss Event"**
- Context compaction compresses prior messages to fit the window
- Nuance, conventions, decision context — lost in compression
- Post-compaction rule: re-read CLAUDE.md and all required files immediately
- The source of truth is the *file*, not your compressed memory of it
- *Talking point:* This is why institutional memory lives on disk, not in context. Files survive compaction. Memory doesn't.

### 5. Pattern Evolution: Observation → Convention → Skill

**Slide 5.1 — "The Only Self-Improving Tip"**
- This is the meta-tip: the mechanism that generates all the other tips
- Patterns evolve through a lifecycle: observation → convention → policy → skill
- Each level is more formalized, more durable, more shareable
- *Talking point:* Every other technique in this talk went through this lifecycle. They weren't designed upfront — they surfaced through iteration.

**Slide 5.2 — "The Lifecycle"**
- **NOTES.md:** "We've done this twice — might be a pattern." Low commitment. Observation.
- **CLAUDE.md:** "This is how we do things." Policy. Enforced by instructions.
- **Skill:** Automated, reusable, shareable across projects. The pattern is now a tool.
- *Talking point:* The key is recognizing promotion signals. If you keep re-encoding the same instruction, it needs to live at a higher level of abstraction.

**Slide 5.3 — "Real Example: Consistency Passes"**
- Started as: "hey, can you grep for stale references?" (ad-hoc)
- Became: four-level framework in CLAUDE.md — Quick, Standard, Sweep, Structural
- Candidate for: a reusable skill that any project can invoke
- *Talking point:* Notice the progression. Nobody sat down and designed a four-level consistency pass framework. It emerged from repeated need, got captured, got formalized, and is now a candidate for automation.

### 6. The Practical Toolkit

**Slide 6.1 — "Chat UX Is Real UX"**
- You interact with Claude hundreds of times a day. 5% friction reduction is massive.
- **Numbers-letters (NL/NLR):** Structured decisions with optional recommendations
- **Batch shorthand:** "1A, 2C, 3D" — answer multiple questions in one message
- **"ok" to approve:** One-word approval for reviewed content
- **Code blocks for indentation:** Markdown collapses whitespace; code blocks preserve it
- *Talking point:* These aren't cosmetic. They change the shape of the interaction. NLR changes what Claude produces. Batch shorthand changes how fast you iterate. Small investments, enormous compound returns.

**Slide 6.2 — "Standardize the Plumbing, Not the Problem-Solving"**
- Vocabulary: one term per concept, defined once, used everywhere. "Session" not "phase" for top-level.
- Formats: ID format (`XX_N`), commit conventions, file naming — one way, no improvising
- What NOT to standardize: problem-solving approach, creative decisions, implementation strategy
- *Talking point:* Standardization reduces drift and survives compaction. But overstandardize and you constrain the agent's useful autonomy. Lock down the plumbing — terminology, IDs, formats. Leave the problem-solving free.

**Slide 6.3 — "Decision Capture and Cascading"**
- Step 1: Capture the decision in NOTES.md (what, why, what was rejected)
- Step 2: Cascade through affected artifacts — PRD, schemas, PLAN.md, reference files
- A decision that lives in only one place will be lost or contradicted
- *Talking point:* Capture and cascade are complementary. NOTES.md is the first stop, not the last. Ask: "does this decision affect any other artifact?"

**Slide 6.4 — "Test Assumptions Empirically"**
- Claude can test things about itself *right now*
- Spawn a subagent, try a prompt, check what's in context
- Costs minutes. Prevents building entire systems on wrong assumptions.
- Real example: subagent context inheritance — guessed what subagents inherit, tested it, corrected three wrong assumptions
- *Talking point:* This is one of the highest-leverage questions you can ask: "Can you test this right now?" Don't reason about how things should work. Try it.

> **📋 ANNOTATED TRANSCRIPT CANDIDATE:** Show the actual subagent inheritance test — the hypothesis, the test prompt, the surprising result. Callout: "Three assumptions corrected in 2 minutes. Without this test, we'd have built the entire subagent model on wrong assumptions."

### 7. Putting It Together

**Slide 7.1 — "A Session That Improves the Next Session"**
- Session N: notice a pattern, capture it in NOTES.md
- Session N+1: promote to CLAUDE.md, Claude now follows it automatically
- Session N+2: refine based on real usage, the convention gets better
- Each session starts from a higher baseline than the last
- *Talking point:* This is the ratchet. Not a grand system — a habit. Notice, capture, formalize. Repeat. The compound returns are enormous.

**Slide 7.2 — "From Copilot to Collaborator"**
- Copilot: executes what you say, waits for the next instruction
- Collaborator: has opinions, remembers context, flags concerns, improves over time
- The gap between them is entirely bridgeable — with the techniques in this talk
- *Talking point:* And if you take these patterns seriously enough... you might want to automate them. Which brings us to Part 2.

---

## Part 2: From Ratchet to Engine — plet

What happens when you take Part 1's patterns seriously enough to automate them.

### 8. What Is plet? (Just Enough Context)

**Slide 8.1 — "The Ratchet, Industrialized"**
- Spec-driven autonomous development loop for Claude Code
- Interactive human-driven spec + orchestrated autonomous build loops
- The human ratchets the spec forward. plet builds it without hand-holding.
- *Talking point:* This isn't "fully autonomous AI coding." The human stays in the loop exactly where human judgment matters — requirements, trade-offs, approval — and drops out where it doesn't.

**Slide 8.2 — "Three Sessions, One Arc"**
- **Plan** — human and Claude build the spec interactively (the ratchet from Part 1)
- **Loop** — autonomous: decompose → implement → verify → iterate
- **Refine** — human reviews, feeds back, system improves
- *Talking point:* Plan is Part 1 in action. Loop is Part 2. Refine closes the circle. We're going to focus on Loop — that's where the architectural decisions live.

### 9. Architectural Decisions (The Core of Part 2)

**Slide 9.1 — "One Context Window Per Iteration"**
- The hardest-won lesson: context compaction mid-iteration = agent forgets what it was doing
- Not "might cause issues." *Will lose implementation state.* The agent literally stops knowing what it was building.
- Design consequence: every unit of work must fit in a single context window
- Two small iterations are always safer than one large one
- *Talking point:* This is an architectural constraint, not a preference. Get it wrong and nothing downstream works. It drove every other sizing decision in the system.

**Slide 9.2 — "All State Lives on Disk"**
- Subagents start with fresh context windows — no shared memory, no inherited conversation
- Everything they need to pick up work: state.json, progress.md, learnings.md, emergent.md
- Any fresh agent can resume from any point by reading the state files
- *Talking point:* This is institutional memory from Part 1, made mechanical. The "write to disk immediately" discipline becomes a hard requirement when agents crash and new ones need to continue.

**Slide 9.3 — "Independent Verification (The Goldilocks Zone)"**
- Three levels, only one works:
  - **Self-verification:** Same agent checks its own work. Rubber-stamps everything.
  - **Adversarial verification:** Agent tries to break it. Invents phantom problems to justify its existence.
  - **Independent verification:** Separate agent, no knowledge of the process, checks the result. Fresh eyes.
- *Talking point:* We tested all three. Self-review catches nothing interesting. Adversarial review wastes cycles on imagined issues. Independent review — separate context, reads the codebase cold, runs its own checks — is the sweet spot. Genuine validation without invented problems.

**Slide 9.4 — "Red/Green as Crash Recovery"**
- Failing test (red) → implement → passing test (green) → commit
- Well-known TDD discipline — but it transforms autonomous agent work
- If an agent crashes mid-iteration: the tests tell the next agent exactly where you left off
- Red = "this is what needs to be done." Green = "this is done."
- Commit after each red and green step — work that isn't committed is work that can be lost
- *Talking point:* Tests aren't just for correctness. They're the recovery mechanism. Without them, a crashed agent leaves no trail. With them, the next agent picks up seamlessly.

**Slide 9.5 — "Append-Only Artifacts and Entry Fencing"**
- Multiple agents writing to the same file? Use `cat >>`, not read-then-overwrite
- Wrap entries in unique boundary lines so git can distinguish and auto-merge
- Separate artifacts by audience: progress.md (humans), learnings.md (agents), emergent.md (decisions)
- *Talking point:* These are boring infrastructure decisions. They prevent the exciting failure mode where parallel agents silently clobber each other's work.

### 10. The Subagent Model

**Slide 10.1 — "Fresh Context for Genuine Independence"**
- Each subagent runs in its own context window — no contamination from the orchestrator
- Orchestrator → impl agent → verify agent pipeline
- The verify agent checks the *result*, not the *process* — no reading impl diffs first
- *Talking point:* Independence isn't just nice to have. Self-review always rubber-stamps. The verify agent must be genuinely ignorant of how the code was written — it reads the codebase cold and forms its own opinion.

**Slide 10.2 — "What Subagents Inherit (And What They Don't)"**
- **Inherit:** CLAUDE.md, auto-memory (MEMORY.md) — project conventions survive
- **Don't inherit:** Skills, tools, conversational context — they start fresh
- Tested empirically — not from docs, not from reasoning. Actually spawned a subagent and checked.
- *Talking point:* This is "test assumptions empirically" from Part 1. We guessed what subagents would inherit, tested it, and corrected three wrong assumptions. The entire subagent architecture was adjusted based on a 2-minute test.

**Slide 10.3 — "Heartbeats and Canary Writes"**
- Agents update `agentActivity` as they work — 5+ minutes stale = assumed crashed
- Canary writes: after each significant action, write a progress entry with critical state
- After compaction or crash, recover by reading the last canary entry
- *Talking point:* These are the operational details that make autonomous agents actually work in practice. Without them, you can't tell a slow agent from a dead one.

### 11. The Virtuous Cycle

**Slide 11.1 — "The System That Builds Itself"**
- plet runs generate learnings (learnings.md)
- Learnings feed back into the system (FEEDBACK.md → requirements → implementation)
- The ratchet from Part 1, now turning automatically
- *Talking point:* This is the payoff. Not just "Claude builds software." Claude builds software, learns from building it, and gets better at building the next thing. The system that builds software also builds itself.

**Slide 11.2 — "From Tool to Evolving Collaborator"**
- Part 1: manual ratchet — notice, capture, formalize. Human-driven.
- Part 2: automated ratchet — observe, build, learn, improve. System-driven.
- The arc of the talk: the same patterns, at increasing levels of automation
- Not fully autonomous — the human still drives the *what*. But the *how* keeps getting better on its own.
- *Talking point:* The transition from Part 1 to Part 2 should feel inevitable. "Of course you'd automate this." That's the ratchet working.

---

## Appendix: Key References
- `CLAUDE_CODE_EMERGENT_PRACTICES_PATTERNS.md` — source material for Part 1
- `prd.md` — plet PRD
- `skills/plet/SKILL.md` — the plet skill definition
- `NOTES.md` (root) — institutional memory for the plet project
- `guide/NOTES.md` — institutional memory for the presentation/guide
