# plet_invoke.py (INV)

> Status: complete

> **Convention:** Every section can have supporting prose above or below its table — context, rationale, examples, caveats. Tables capture the *requirements*; prose captures the *why*.

## 1. Purpose (INV_PUR)

Launches Claude Code subprocesses for implement and verify phases. Assembles the prompt (via `plet_prompt.py`), spawns `claude -p`, captures streaming transcript, returns exit code. This is the execution bridge between plet's deterministic orchestration and Claude's non-deterministic work.

**Why a script:** The orchestrator needs a reliable way to: (1) assemble the right prompt, (2) launch with correct flags, (3) capture the full transcript for debugging/replay, (4) return a clean exit signal. Without a dedicated script, each step is fragile and varies between invocations.

**Key design choice:** Subprocess over native Agent tool. Subprocess invocations (`claude -p --output-format stream-json`) provide reliable transcript capture. Native Agent tool subagents run inside Claude Code with no portable way to capture raw I/O.

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_PUR_1 | Launches a Claude Code subprocess with the assembled prompt for a specific iteration and phase. | P0 |
| INV_PUR_2 | Captures streaming JSONL output to a transcript file, line by line, with flush-after-each-line for GUI live-tail. | P0 |
| INV_PUR_3 | Returns the subprocess exit code to the caller. | P0 |

## 2. Agent Personas (INV_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| INV_AGT_1 | orchestrator script | spawning implement/verify subagent | `run` |
| INV_AGT_2 | human | manual testing — launch a single subagent | `run` |

## 3. Commands

**Command summary:**

- **`run`** (RUN) — Launch a Claude Code subprocess with transcript capture. Assembles the prompt (via plet_prompt.py), launches `claude -p`, and captures streaming JSONL output to the trace transcript file. Called by the orchestrator for each implement/verify phase.

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | run | Structured JSON result (not the subprocess output — the invocation metadata) |
| `--pretty` | run | Indent JSON (requires `--output json`) |
| `--fields f1,f2` | run | Limit JSON fields (requires `--output json`) |
| `--dry-run` | run | Preview the command that would be executed without launching |

**JSON error behavior:** Per UNV_ERR_4.

---

### 3.1 run (RUN)

#### Justification (INV_RUN_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_JUS_1 | Why: deterministic subprocess launch with transcript capture. Replaces ad-hoc agent spawning with a reliable, testable command. | P0 |
| INV_RUN_JUS_2 | When: called by orchestrator for each implement/verify phase. Also by humans for manual testing. | P0 |

#### Definition (INV_RUN_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_CMD_1 | Usage: `plet_invoke.py run <plet_dir> --iter-id ID_xxx --phase implement|verify --cwd <worktree_path> [--max-budget N] [--model MODEL] [--permission-mode MODE] [--dry-run] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating (launches subprocess that modifies files), not idempotent (each run produces new transcript)

**Concurrency:** safe for different iterations (different worktrees). NOT safe for same iteration concurrently.

#### Inputs (INV_RUN_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_INP_1 | `plet_dir` — required positional. Path to plet directory. Used by PRM to assemble prompt. | P0 |
| INV_RUN_INP_2 | `--iter-id` — iteration ID. Required. | P0 |
| INV_RUN_INP_3 | `--phase` — `implement` or `verify`. Required. | P0 |
| INV_RUN_INP_4 | `--cwd` — working directory for the subprocess. Required. Typically the worktree path from GTI. The subprocess runs in this directory. | P0 |
| INV_RUN_INP_5 | `--max-budget` — (optional) maximum USD budget for the subprocess. Maps to `claude --max-budget-usd`. | P1 |
| INV_RUN_INP_6 | `--model` — (optional) model override. Maps to `claude --model`. | P1 |
| INV_RUN_INP_7 | `--permission-mode` — (optional) permission mode. Default: `auto`. Fallback: `bypassPermissions` if auto mode is not available (older models, not enabled). Maps to `claude --permission-mode`. Valid: `auto`, `bypassPermissions`, `default`. No `--dangerously-skip-permissions` — use `--permission-mode bypassPermissions` instead. | P1 |
| INV_RUN_INP_8 | `--verbose` — (optional) pass `--verbose` to claude for extra logging. | P2 |

#### Outputs (INV_RUN_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_OUT_1 | Text mode: `OK — {phase} subprocess exited {code}` or `ERROR — {phase} subprocess exited {code}`. Exit code matches subprocess exit code. | P0 |
| INV_RUN_OUT_2 | JSON mode: structured invocation result (see schema below). | P0 |
| INV_RUN_OUT_3 | Transcript file written: `{plet_dir}/trace/{iter_id}-{phase}-{attempt}-transcript.ndjson` | P0 |
| INV_RUN_OUT_4 | Dry-run: prints the full `claude` command that would be executed, exit 0. | P0 |
| INV_RUN_OUT_5 | Error (bad inputs): specific message to stderr, exit 1. | P0 |

**INV_RUN JSON schema (INV_RUN_OUT_2):**
```json
{
  "status": "ok|error",
  "command": "run",
  "iterationId": "...",
  "phase": "implement|verify",
  "attempt": N,
  "subprocessExitCode": N,
  "transcriptPath": "...",
  "transcriptLines": N,
  "elapsedSeconds": N,
  "scriptVersion": "0.1.0",
  "timestamp": "..."
}
```

#### Preconditions (INV_RUN_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_PRE_1 | `--iter-id`, `--phase`, `--cwd` present | P0 |
| INV_RUN_PRE_2 | `plet_dir` exists | P0 |
| INV_RUN_PRE_3 | `--cwd` exists and is a directory | P0 |
| INV_RUN_PRE_4 | `claude` binary is on PATH | P0 |
| INV_RUN_PRE_5 | Iter state file exists (for attempt number) | P0 |

#### Postconditions (INV_RUN_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_PST_1 | Transcript file exists at `{plet_dir}/trace/{iter_id}-{phase}-{attempt}-transcript.ndjson` | P0 |
| INV_RUN_PST_2 | Every line of subprocess stdout is in the transcript (no data loss) | P0 |
| INV_RUN_PST_3 | Script exit code matches subprocess exit code (pass-through) | P0 |
| INV_RUN_PST_4 | Invocation trace event written with full prompt text. Progress entry written with full prompt text. Both contain invocation details. No separate prompt file — prompt lives in trace + progress. | P0 |

#### Behaviors (INV_RUN_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_RUN_BHV_1 | **Prompt assembly:** Calls `plet_prompt.py assemble <plet_dir> --iter-id <iter_id> --phase <phase>` via subprocess. Captures stdout as the prompt text. | P0 |
| INV_RUN_BHV_2 | **Subprocess construction:** Builds command: `claude -p <prompt> --output-format stream-json --permission-mode <mode> --no-session-persistence --bare --name "plet/{iter_id}/{phase}-{attempt}"` plus optional `--max-budget-usd`, `--model`, `--verbose`. The full prompt string is passed as a direct command-line argument to `-p` (not piped via stdin, not read from a file). | P0 |
| INV_RUN_BHV_3 | **Working directory:** Subprocess is launched with `cwd=<worktree_path>` (from `--cwd`). The subagent sees the worktree as its working directory. | P0 |
| INV_RUN_BHV_4 | **Transcript capture:** Opens transcript file before launch. Reads subprocess stdout line by line. Writes each line to transcript + flushes immediately. Closes file after subprocess exits. | P0 |
| INV_RUN_BHV_5 | **Transcript path:** `{plet_dir}/trace/{iter_id}-{phase}-{attempt}-transcript.ndjson`. Creates `trace/` directory if needed. Attempt number read from iter state (`attempts.{phase}`). If transcript file already exists (retry of same attempt), append with a separator line — NEVER overwrite. Data must never be lost. | P0 |
| INV_RUN_BHV_6 | **Exit code pass-through:** Returns the subprocess exit code as the script's exit code. 0 = success, non-zero = failure. The orchestrator interprets the exit code. | P0 |
| INV_RUN_BHV_7 | **Elapsed time:** Records wall-clock elapsed time from subprocess start to finish. Included in JSON output. | P0 |
| INV_RUN_BHV_8 | **No session persistence:** Uses `--no-session-persistence` — subagent sessions are ephemeral and not resumable. Each invocation is a clean context. | P0 |
| INV_RUN_BHV_9 | **Session name:** Uses `--name "plet/{iter_id}/{phase}-{attempt}"` for identification in `claude /resume` or session listing. | P0 |
| INV_RUN_BHV_10 | **Bare mode:** Uses `--bare` — skips hooks, LSP, plugin sync, auto-memory, background prefetches. Subagents are non-interactive batch workers; IDE features add latency with no benefit. Monitor: if subagents need skills or plugins from the user's setup, `--bare` may need to be optional. | P0 |
| INV_RUN_BHV_11 | **Invocation trace event:** Calls `plet_trace.py append-event --type invocation` before launch. Data includes full prompt text + invocation details (cwd, permissionMode, promptLength, model, maxBudget, verbose, bare, transcriptPath). First event in the events file — makes the trace self-describing. | P0 |
| INV_RUN_BHV_12 | **Invocation progress entry:** Calls `plet_entries.py add-progress` before launch with status IN_PROGRESS. Content includes invocation details + full prompt text. Human-readable record in progress.md. | P0 |

---

## 4. Edge Cases (INV_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_EDG_1 | `claude` not on PATH — error before launch. | P0 |
| INV_EDG_2 | Prompt assembly fails (PRM returns non-zero) — error with PRM stderr. | P0 |
| INV_EDG_3 | Subprocess exits non-zero — not an INV error. Pass exit code through. Transcript still captured. | P0 |
| INV_EDG_4 | `--cwd` doesn't exist — error. | P0 |
| INV_EDG_5 | Transcript directory doesn't exist — create it. | P0 |
| INV_EDG_6 | Subprocess produces no output (empty transcript) — not an error. Transcript file exists but is empty. | P0 |
| INV_EDG_7 | Subprocess timeout (if `--max-budget` exceeded) — claude handles this internally, INV captures whatever was produced. | P1 |
| INV_EDG_8 | Invalid `--phase` — error. | P0 |
| INV_EDG_9 | Invalid `--permission-mode` — error. | P0 |

## 5. Error Handling (INV_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_ERR_1 | Missing required args → error + help text | P0 |
| INV_ERR_2 | Invalid `--phase` → error | P0 |
| INV_ERR_3 | `plet_dir` not found → error | P0 |
| INV_ERR_4 | `--cwd` not found → `Error: working directory not found: {path}` | P0 |
| INV_ERR_5 | `claude` not on PATH → `Error: claude not found on PATH` | P0 |
| INV_ERR_6 | Prompt assembly failed → `Error: prompt assembly failed: {stderr}` | P0 |
| INV_ERR_7 | Iter state file not found → error | P0 |

## 6. Formats (INV_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_FMT_1 | Reads iter state for attempt number: `{plet_dir}/state/{iter_id}.json` | P0 |
| INV_FMT_2 | Writes transcript: `{plet_dir}/trace/{iter_id}-{phase}-{attempt}-transcript.ndjson` (streaming NDJSON) | P0 |
| INV_FMT_4 | Writes invocation trace event (via plet_trace.py) + progress entry (via plet_entries.py). Both contain full prompt text. | P0 |
| INV_FMT_3 | Calls PRM for prompt text (reads indirectly via PRM) | P0 |

## 7. Agent Flows (INV_AFL)

### INV_AFL_1: Orchestrator launches implement subagent

1. Orchestrator creates worktree via GTI
2. Calls: `plet_invoke.py run plet/ --iter-id ID_001 --phase implement --cwd .plet/worktrees/TEST/ID_001`
3. INV assembles prompt via PRM
4. INV launches `claude -p` in the worktree
5. INV captures transcript line by line
6. Subprocess finishes → INV returns exit code
7. Orchestrator checks exit code, proceeds to gate/verify

### INV_AFL_2: Dry-run preview

1. Human wants to see what command would be run
2. `plet_invoke.py run plet/ --iter-id ID_001 --phase implement --cwd /tmp/wt --dry-run`
3. Prints full `claude -p "..." --output-format stream-json --permission-mode auto ...`
4. Exit 0

## 8. Examples (INV_EXM)

### INV_EXM_1: Launch implement subagent

```bash
plet_invoke.py run plet/ --iter-id ID_001 --phase implement \
    --cwd .plet/worktrees/TEST/ID_001
# OK — implement subprocess exited 0
```

### INV_EXM_2: Dry-run

```bash
plet_invoke.py run plet/ --iter-id ID_001 --phase implement \
    --cwd .plet/worktrees/TEST/ID_001 --dry-run
# DRY RUN — would execute:
# claude -p "..." --output-format stream-json --permission-mode auto \
#   --no-session-persistence --name "plet/ID_001/implement-1"
# Transcript would be written to: plet/trace/ID_001-implement-1-transcript.ndjson
```

### INV_EXM_3: JSON output

```bash
plet_invoke.py run plet/ --iter-id ID_001 --phase implement \
    --cwd .plet/worktrees/TEST/ID_001 --output json --pretty
# {
#   "status": "ok",
#   "command": "run",
#   "iterationId": "ID_001",
#   "phase": "implement",
#   "attempt": 1,
#   "subprocessExitCode": 0,
#   "transcriptPath": "plet/trace/ID_001-implement-1-transcript.ndjson",
#   "transcriptLines": 847,
#   "elapsedSeconds": 142,
#   ...
# }
```

## 9. Dependencies on Other Scripts (INV_DEP)

| ID | Direction | Script | Relationship |
|----|-----------|--------|-------------|
| INV_DEP_1 | imports | `util_cli` | shared CLI helpers |
| INV_DEP_2 | imports | `util_io` | path derivation, load functions |
| INV_DEP_3 | imports | `util_subprocess` | `run` for PRM subprocess call |
| INV_DEP_4 | calls (subprocess) | `plet_prompt.py` | `assemble` for prompt text |
| INV_DEP_5 | calls (subprocess) | `claude` | the actual subagent |
| INV_DEP_7 | calls (subprocess) | `plet_trace.py` | `append-event --type invocation` — invocation details + full prompt |
| INV_DEP_8 | calls (subprocess) | `plet_entries.py` | `add-progress` — invocation details + full prompt (human-readable) |
| INV_DEP_6 | called by | `plet_orchestrator.py` | spawns subagents |

## 10. Non-Functional Requirements (INV_NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_NFR_1 | Line-by-line capture with flush — no buffering. GUI live-tail within ~100ms. | P0 |
| INV_NFR_2 | No data loss — every line from subprocess stdout appears in transcript. | P0 |
| INV_NFR_3 | No external dependencies — stdlib subprocess for claude, util_subprocess for PRM. | P0 |

## 11. Developer Experience (INV_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| INV_DXP_1 | Help text follows IMPORTANT/PITFALLS/USAGE/PURPOSE structure | P0 |
| INV_DXP_2 | IMPORTANT: --dry-run previews the full claude command without launching | P0 |
| INV_DXP_3 | PITFALLS: --cwd is required (must be an existing worktree). Transcript is never overwritten — appends on retry. | P0 |
| INV_DXP_4 | Session name includes iter-id and phase for easy identification in claude /resume | P0 |

## 12. Critical Test Areas (INV_CRT)

| ID | Area | Risk if broken | Suggested test approach |
|----|------|---------------|----------------------|
| INV_CRT_1 | Prompt assembly | Wrong prompt → agent does wrong work | Mock PRM, verify it's called with correct args |
| INV_CRT_2 | Subprocess construction | Wrong flags → permissions/output issues | --dry-run, verify command string |
| INV_CRT_3 | Transcript capture | Lost output → debugging impossible | Launch mock subprocess, verify transcript matches |
| INV_CRT_4 | Exit code pass-through | Wrong exit code → orchestrator misjudges | Mock subprocess with various exit codes |
| INV_CRT_5 | --cwd handling | Wrong directory → agent modifies wrong repo | --dry-run, verify cwd in command |
| INV_CRT_6 | Missing claude | Crash instead of error | Remove claude from PATH, verify error |
| INV_CRT_7 | Dry-run output | Incomplete preview | Verify full command visible |
| INV_CRT_8 | Elapsed time | Wrong timing | Verify > 0 for real invocation |
| INV_CRT_9 | Prompt logged | Can't eval without knowing what agent received | Verify invocation trace event has full prompt in data.prompt, progress entry has full prompt in content |

## 13. Testing & Verification (INV_TST)

**What to test:** See §12.

**Testing challenge:** INV launches `claude -p` which requires API access. Tests must use mocks — either a mock `claude` script on PATH or mock the subprocess call.

**Test infrastructure:**
- File: `skills/plet/tests/test_plet_invoke.py`
- Mock strategy: create a mock `claude` shell script that echoes JSONL and exits with a controlled code. Place it first on PATH for tests.
- Dry-run tests don't need mocks — they verify command construction only.
- Red/green discipline.

## 14. Resolved Questions

| # | Question | Decision |
|---|----------|----------|
| 1 | How to enable auto mode for subprocesses? | `--permission-mode auto` on each `claude -p` invocation. Auto mode must first be enabled on the system via `claude --enable-auto-mode` (one-time setup, see https://claude.com/blog/auto-mode). The per-invocation flag selects the mode; the setup command enables it as an option. |
| 2 | `--cwd` flag or `cd` before launch? | `--cwd` is an INV flag, not a claude flag. INV passes it to `subprocess.run(cwd=...)`. Claude has no --cwd flag. |
| 3 | Prompt delivery mechanism? | Direct command-line argument to `-p`. The full prompt string is passed as a single positional arg: `claude -p "{prompt}"`. Not piped via stdin, not read from a file. |
| 4 | Session persistence? | Off — `--no-session-persistence`. Subagents are ephemeral. |
| 5 | Should INV control sandboxing? | No — sandboxing is environment-level config (`/sandbox` or settings.json), not per-invocation. See FB_50. |
| 6 | Capture stderr? | No — stderr goes to INV's own stderr (visible to orchestrator). Only stdout (stream-json) goes to transcript. |
| 7 | Increment attempt counter? | No — orchestrator's job. INV reads attempt for filename but doesn't write state. |
| 8 | Transcript on retry? | Append with separator — never overwrite, never lose data. Each attempt normally gets a unique filename. If same attempt retries, append. |
| 9 | `--bare` mode? | Yes — subagents are batch workers. Skips hooks, LSP, plugins. Monitor: may need to be optional if subagents need user skills/plugins. |

### Open Questions

- Should INV support `--append-system-prompt` for injecting additional context beyond what PRM assembles?

## 15. Future Considerations (INV_FUT)

| ID | Area | Description |
|----|------|-------------|
| INV_FUT_1 | Native Agent tool | If Claude Code adds portable transcript capture for native subagents, INV could use that instead of subprocess. |
| INV_FUT_2 | Streaming event parsing | Parse the stream-json output during capture to extract progress signals (tool calls, errors) for real-time orchestrator awareness. |
| INV_FUT_3 | Retry logic | Built-in retry on transient failures (API errors, rate limits). Currently the orchestrator handles retries. |

## 16. FB Items Addressed

- FB_22 — bypassPermissions. Resolved: `--permission-mode auto` on subprocess invocations (requires one-time `claude --enable-auto-mode` setup). No project-level config needed.
