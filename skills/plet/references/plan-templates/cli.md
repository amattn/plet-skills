# Plan-Phase Template: CLI

Project type template for non-interactive terminal CLI utilities — tools invoked from the command line that take input via arguments, do work, and exit. No interactive prompts, no TUI, no long-running daemons. All input comes via CLI flags and positional arguments; all output goes to stdout (results) and stderr (errors). Commands must be scriptable, pipeable, and automatable.

Composes with `common.md` + a platform template — a Python CLI loads `common.md` + `cli.md` + `python.md`.

---

## FRQ: Functional Requirements

Each command should have a one-line description, required args, and which user persona uses it. Per-command sections define preconditions, postconditions, behaviors, inputs, outputs, and error conditions.

| ID | Requirement | Priority |
|----|-------------|----------|
| FRQ_1 | Command inventory table: each command with one-line description, required args, and which user persona uses it | P0 |
| FRQ_2 | Command-based interface: `tool <command> [args]` — not flag-based (`tool --validate`) | P0 |
| FRQ_3 | Universal flags table: flags accepted by all commands (`--help`, `--usage`, `--version`, `--output json`, `--verbose`, `--quiet`) | P0 |
| FRQ_4 | Per-command spec sections: preconditions, postconditions, behaviors, inputs, outputs, error conditions | P1 |

---

## NFR: Non-Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| NFR_1 | Exit codes: 0 = success, 1 = error, 2 = warnings-only (for check/validate commands) | P0 |
| NFR_2 | Signal handling: SIGINT/SIGTERM result in clean shutdown, no corrupted state | P0 |
| NFR_3 | Strict input validation: reject unknown flags, reject duplicate flags, require arguments rather than defaulting, validate enum values before doing work. Fail loudly on bad input — silent forgiveness hides bugs, especially when commands are generated programmatically. | P0 |
| NFR_4 | `--dry-run` on all mutating commands — preview changes without writing to disk | P0 |
| NFR_5 | Single resource per invocation — no multi-file glob, no batch aggregation. Callers control the loop. Guarantees predictable output size. | P0 |
| NFR_6 | Complex values accepted via separate mutually exclusive flags: `--data '{"key":"val"}'` for inline JSON, `--data-file path.json` for file input. Error if both provided. Prevents shell argument length limits for large payloads. | P1 |
| NFR_7 | Startup time under 500ms for common commands | P1 |
| NFR_8 | Memory: handle large inputs via streaming where possible, not loading everything into memory | P1 |

---

## FLW: User Flows

| ID | Requirement | Priority |
|----|-------------|----------|
| FLW_1 | Primary workflow: step-by-step sequence of commands for the main use case | P0 |
| FLW_2 | Multi-command pipelines: document which commands compose via piping or sequential invocation | P1 |
| FLW_3 | Error recovery flows: what the user does when a command fails mid-workflow | P1 |

---

## ARC: Technical Architecture

| ID | Requirement | Priority |
|----|-------------|----------|
| ARC_1 | Three-tier architecture: entry points (thin CLI shims that parse args and delegate) → modules (the actual logic, testable via direct import) → utilities (shared helpers). Keeps the agent/user-facing surface small while the implementation is independently testable. | P0 |
| ARC_2 | Entry point dispatch: single script dispatches to command handlers via `tool <command> [args]` pattern | P0 |
| ARC_3 | No interactive input — all input via CLI arguments. Commands must be scriptable and automatable. | P0 |
| ARC_4 | Command functions return structured results (not print directly) for testability via direct import. Entry point handles formatting and I/O. | P0 |

---

## DAT: Data Models

| ID | Requirement | Priority |
|----|-------------|----------|
| DAT_1 | Input schemas: expected formats for each input type (files, stdin, JSON args) | P0 |
| DAT_2 | Output schemas: structured output format for machine-readable mode (e.g., `--output json`) | P0 |
| DAT_3 | `--fields` flag to limit structured output to requested fields. Protects context window budget when output is consumed by agents or piped to other tools. | P1 |
| DAT_4 | Config file format: location, schema, defaults, validation | P1 |
| DAT_5 | State file schemas: if the tool maintains state, define the schema and migration strategy | P1 |

---

## DVX: Developer Experience

| ID | Requirement | Priority |
|----|-------------|----------|
| DVX_1 | Help text: every command supports `--help` with copy-pasteable examples | P0 |
| DVX_2 | Usage text: every command supports `--usage` with compact invocation syntax. Three-tier escalation: cheat sheet (if available) → `--usage` → `--help`. Each tier adds detail and tokens. | P0 |
| DVX_3 | Error messages: show what was received and what was expected. Include actionable recovery hints. | P0 |
| DVX_4 | Named arguments with `--key value` for all non-positional args. Only file paths as positional. Predictability over brevity. | P0 |
| DVX_5 | `--version` flag: prints tool name + version | P0 |
| DVX_6 | Installation: single-step install (one command or one download) | P1 |
| DVX_7 | Shell completion: tab completion for commands and flags | P2 |

---

## TST: Testing & Verification

| ID | Requirement | Priority |
|----|-------------|----------|
| TST_1 | Test the CLI interface via subprocess, not internal functions — test what users actually experience | P0 |
| TST_2 | Test `--help` and `--usage` on every command — verify exit 0 and non-empty output | P0 |
| TST_3 | Test both success and failure paths for every command | P0 |

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
| CTA_1 | Argument parsing: invalid flags, missing required args, unknown flags, duplicate flags, mutually exclusive flags | P0 |
| CTA_2 | Exit codes: verify correct exit code for every success/failure/warning path | P0 |
| CTA_3 | File I/O: atomic writes, crash during write, permissions errors, missing directories | P0 |
| CTA_4 | Structured output: `--output json` produces valid JSON with consistent schema across all commands | P1 |

---

## RCH: Quality Ratchets

| ID | Requirement | Priority |
|----|-------------|----------|
| RCH_1 | | |

---

## MET: Success Metrics

| ID | Requirement | Priority |
|----|-------------|----------|
| MET_1 | | |

---

## RFP: Refactor Policy

| ID | Requirement | Priority |
|----|-------------|----------|
| RFP_1 | | |
