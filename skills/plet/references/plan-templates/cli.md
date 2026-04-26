# Plan-Phase Template: CLI

Project type template for non-interactive terminal CLI utilities — tools invoked from the command line that take input via arguments, do work, and exit. No interactive prompts, no TUI, no long-running daemons. All input comes via CLI flags and positional arguments; all output goes to stdout (results) and stderr (errors). Commands must be scriptable, pipeable, and automatable.

Composes with `common.md` + a platform template — a Python CLI loads `common.md` + `cli.md` + `python.md`.

**Template IDs use `_N` (literal N), not integers.** During plan composition, the agent collects items from all applicable templates and assigns sequential integer IDs in the final requirements document.

---

## FRQ: Functional Requirements

Each command should have a one-line description, required args, and which user persona uses it. Per-command sections define preconditions, postconditions, behaviors, inputs, outputs, and error conditions.

| ID | Requirement | Priority |
|----|-------------|----------|
| FRQ_N | Command inventory table: each command with one-line description, required args, and which user persona uses it | P0 |
| FRQ_N | Command-based interface: `tool <command> [args]` — not flag-based (`tool --validate`) | P0 |
| FRQ_N | Universal flags table: flags accepted by all commands (`--help`, `--usage`, `--version`, `--output json`, `--verbose`, `--quiet`) | P0 |
| FRQ_N | Per-command spec sections: preconditions, postconditions, behaviors, inputs, outputs, error conditions | P1 |

---

## NFR: Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR_N | Exit codes: 0 = success, 1 = error, 2 = warnings-only (for check/validate commands) | P0 |
| NFR_N | Signal handling: SIGINT/SIGTERM result in clean shutdown, no corrupted state | P0 |
| NFR_N | Strict input validation: reject unknown flags, reject duplicate flags, require arguments rather than defaulting, validate enum values before doing work. Fail loudly on bad input — silent forgiveness hides bugs, especially when commands are generated programmatically. | P0 |
| NFR_N | `--dry-run` on all mutating commands — preview changes without writing to disk | P0 |
| NFR_N | Single resource per invocation — no multi-file glob, no batch aggregation. Callers control the loop. Guarantees predictable output size. | P0 |
| NFR_N | Complex values accepted via separate mutually exclusive flags: `--data '{"key":"val"}'` for inline JSON, `--data-file path.json` for file input. Error if both provided. Prevents shell argument length limits for large payloads. | P1 |
| NFR_N | Startup time under 500ms for common commands | P1 |
| NFR_N | Memory: handle large inputs via streaming where possible, not loading everything into memory | P1 |

---

## FLW: User Flows

| ID | Requirement | Priority |
|----|-------------|----------|
| FLW_N | Primary workflow: step-by-step sequence of commands for the main use case | P0 |
| FLW_N | Multi-command pipelines: document which commands compose via piping or sequential invocation | P1 |
| FLW_N | Error recovery flows: what the user does when a command fails mid-workflow | P1 |

---

## ARC: Technical Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| ARC_N | Three-tier architecture: entry points (thin CLI shims that parse args and delegate) → modules (the actual logic, testable via direct import) → utilities (shared helpers). Keeps the agent/user-facing surface small while the implementation is independently testable. | P0 |
| ARC_N | Entry point dispatch: single script dispatches to command handlers via `tool <command> [args]` pattern | P0 |
| ARC_N | No interactive input — all input via CLI arguments. Commands must be scriptable and automatable. | P0 |
| ARC_N | Command functions return structured results (not print directly) for testability via direct import. Entry point handles formatting and I/O. | P0 |
| ARC_N | JSON-first output: the JSON structure is the single source of truth. Plain text mode formats the JSON for human readability — no separate code path, no independent computation. Build JSON first, pass to a text formatter. Prevents drift between `--output json` and default text output. | P0 |

---

## DAT: Data Models

| ID | Requirement | Priority |
|----|-------------|----------|
| DAT_N | Input schemas: expected formats for each input type (files, stdin, JSON args) | P0 |
| DAT_N | Output schemas: structured output format for machine-readable mode (e.g., `--output json`) | P0 |
| DAT_N | `--fields` flag to limit structured output to requested fields. Protects context window budget when output is consumed by agents or piped to other tools. | P1 |
| DAT_N | Config file format: location, schema, defaults, validation | P1 |
| DAT_N | State file schemas: if the tool maintains state, define the schema and migration strategy | P1 |

---

## DVX: Developer Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| DVX_N | Help text: every command supports `--help` with copy-pasteable examples | P0 |
| DVX_N | Usage text: every command supports `--usage` with compact invocation syntax. Three-tier escalation: cheat sheet (if available) → `--usage` → `--help`. Each tier adds detail and tokens. | P0 |
| DVX_N | Error messages: show what was received and what was expected. Include actionable recovery hints. | P0 |
| DVX_N | Named arguments with `--key value` for all non-positional args. Only file paths as positional. Predictability over brevity. | P0 |
| DVX_N | `--version` flag: prints tool name + version | P0 |
| DVX_N | Installation: single-step install (one command or one download) | P1 |
| DVX_N | Shell completion: tab completion for commands and flags | P2 |

---

## TST: Testing & Verification

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_N | Test the CLI interface via subprocess, not internal functions — test what users actually experience | P0 |
| TST_N | Test `--help` and `--usage` on every command — verify exit 0 and non-empty output | P0 |
| TST_N | Test both success and failure paths for every command | P0 |

---

## VFC: Verification Commands

| Category | Command |
|----------|---------|
| test | |
| format-check | |
| format-fix | |
| lint | |
| typecheck | |
| build | |
| package | |

---

## CTA: Critical Test Areas

| ID | Requirement | Priority |
|----|-------------|----------|
| CTA_N | Argument parsing: invalid flags, missing required args, unknown flags, duplicate flags, mutually exclusive flags | P0 |
| CTA_N | Exit codes: verify correct exit code for every success/failure/warning path | P0 |
| CTA_N | File I/O: atomic writes, crash during write, permissions errors, missing directories | P0 |
| CTA_N | Structured output: `--output json` produces valid JSON with consistent schema across all commands | P1 |

---

## RCH: Quality Ratchets

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_N | | |

---

## MET: Success Metrics

| ID | Requirement | Priority |
|----|-------------|----------|
| MET_N | | |

---

## RFP: Refactor Policy

| ID | Requirement | Priority |
|----|-------------|----------|
| RFP_N | | |
