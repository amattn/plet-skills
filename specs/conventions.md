# Script Conventions (UNV)

Universal requirements across all plet scripts. Per-script specs reference this file rather than duplicating these requirements. Implementation guidance (how to satisfy these requirements) lives in `skills/plet/scripts/CLAUDE.md`.

## Hard Constraints

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_CMD_1 | Scripts use **Python stdlib only** — no third-party packages, no `pip install`, no `requirements.txt`. Scripts ship inside the skill package and must work on any machine with Python 3 installed. | P0 |
| UNV_CMD_2 | Scripts must **never prompt for input** — no `input()`, no `sys.stdin` reads, no interactive confirmations. All input comes via CLI arguments. | P0 |
| UNV_CMD_3 | Target **Python 3.8+** as the minimum. Avoid features from 3.10+ (`match/case`, `X | Y` union types, `tomllib`). | P0 |

## File Setup

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_CMD_4 | Shebang line: `#!/usr/bin/env python3` | P0 |
| UNV_CMD_5 | All scripts must be `chmod +x` for direct invocation | P0 |
| UNV_CMD_6 | Module docstring: purpose, what it enforces, usage examples for every command | P0 |

## Script Structure

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_CMD_7 | Scripts follow a fixed structure: shebang + docstring → imports → constants → utility functions → command functions (`cmd_<name>`) → main dispatch (`main()` with command dict and `sys.exit()`) | P0 |

## CLI Conventions

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_CMD_8 | Command-based interface: `script.py <command> [args]` — not flag-based | P0 |
| UNV_CMD_9 | Every command supports `-h` and `--help`. Top-level `--help` prints the module docstring. Help text is agent-readable with copy-pasteable examples | P0 |
| UNV_CMD_10 | Only file path / artifact directory as positional arg. All other arguments use named `--key value` format. Agents generate commands programmatically — predictability matters more than brevity. | P0 |
| UNV_CMD_11 | No argparse — manual parsing via `parse_kwargs()` pattern | P0 |
| UNV_CMD_12 | Complex values (arrays, objects) passed as JSON strings | P0 |
| UNV_CMD_13 | Every script supports `--version`, printing `<script_name> <version> (built against plet skill <skill_version>)` | P0 |
| UNV_CMD_14 | Exit codes: 0 = success, 1 = error. No other exit codes | P0 |
| UNV_CMD_15 | Output: results to stdout, errors to stderr. Default is human-readable text. `--output json` produces structured machine-readable output with metadata (status, command, path, scriptVersion, timestamp). Both formats must include the same information. | P0 |
| UNV_CMD_16 | Each `cmd_*` function defines a `HELP` variable at the top with usage, arguments, and examples | P0 |
| UNV_CMD_17 | All mutating commands must support `--dry-run`. Dry-run output matches real output except no files are modified. Exit 0 on success preview. | P0 |
| UNV_CMD_18 | All commands must support `--output json` for structured output. JSON includes at minimum: `status`, `command`, `scriptVersion`, `timestamp`. Error output includes `error` message and actionable recovery info (e.g., `available` values). | P0 |

## Idempotency

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_NFR_1 | Read-only commands (validate, check) must be safe to run repeatedly with the same result | P0 |
| UNV_NFR_2 | Creation commands (init) must error on existing files rather than overwriting | P0 |
| UNV_NFR_3 | Mutation commands must be predictable — same update twice produces expected state | P1 |

## File I/O

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_NFR_4 | Atomic writes for state files: write to `path.tmp`, then `os.rename(tmp, path)` | P0 |
| UNV_NFR_5 | Atomic appends for runtime artifacts: write to temp, read back, append, remove temp | P0 |
| UNV_NFR_6 | Trailing newline after JSON for POSIX compliance and diff-friendliness | P0 |
| UNV_NFR_7 | Never read-modify-write runtime artifacts — append only. State files are read-modify-write (single writer per iteration) | P0 |

## Error Handling

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_ERR_1 | Validate all inputs before doing work — check required args, enum values, file existence before touching files | P0 |
| UNV_ERR_2 | Specific error messages: show what was received and what was expected | P0 |
| UNV_ERR_3 | Fail fast on first error. Exception: validation commands accumulate all schema errors before reporting | P0 |
| UNV_ERR_4 | Scripts must never produce unhandled exceptions. Every error path produces a clean message to stderr. Agents must never see Python tracebacks. Wrap all type conversions, file operations, and JSON parsing in try/except with specific messages. | P0 |

## Naming

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_DXP_1 | CLI tool scripts: `plet_<domain>.py` — callable via `Bash()`, listed in `allowed-tools` | P0 |
| UNV_DXP_2 | Command names: lowercase, hyphen-separated (e.g., `update-criterion`) | P0 |
| UNV_DXP_3 | Function names: `cmd_<command_with_underscores>` (e.g., `cmd_update_criterion`) | P0 |
| UNV_DXP_4 | Internal modules: `util_<concern>.py` — imported by `plet_*.py` scripts, never called directly, not listed in `allowed-tools`, not executable | P0 |
| UNV_DXP_5 | Help text uses 4-section structure: **IMPORTANT** (dry-run recommendation, key warnings) → **PITFALLS** (common mistakes, wrong values, gotchas) → **USAGE** (syntax, arguments, examples) → **PURPOSE** (what/when/why — last because agent already decided to run it). Help text is agent guidance first; additional content welcome. | P0 |

## Testing

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_TST_1 | Tests live at `skills/plet/tests/`, named `test_<script_name>.py` | P0 |
| UNV_TST_2 | Zero dependencies applies to tests — no pytest, no unittest, stdlib-only custom harness | P0 |
| UNV_TST_3 | Each test file is directly executable: `python3 skills/plet/tests/test_<name>.py` | P0 |
| UNV_TST_4 | Tests call the script via `subprocess.run()` — test the CLI interface, not internal functions | P0 |
| UNV_TST_5 | Tests create temp fixtures, validate output + file contents, then clean up | P0 |
| UNV_TST_6 | Test both success and failure paths | P0 |
| UNV_TST_7 | Test `--help` on every command — verify exit 0 and non-empty output | P0 |

## Allowed Tools

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_NFR_8 | Scripts callable by agents must be listed in `skills/plet/SKILL.md` frontmatter under `allowed-tools` with path-specific patterns | P0 |

## Open Questions

1. ~~**`parse_kwargs` as shared utility**~~ **RESOLVED:** Extract into `util_cli.py`. All scripts import from shared internal modules (`util_*.py`). Internal modules are not external dependencies — they ship in the same directory. See UNV_DXP_4.

2. ~~**Positional args limit**~~ **RESOLVED:** Only file path / artifact directory stays positional. Everything else becomes named args. Agents generate commands programmatically — brevity doesn't matter, predictability does. UNV_CMD_10 updated.

3. ~~**`update-field` alternating pairs**~~ **RESOLVED:** Same as #2 — migrate to named args. The alternating pair pattern was an ergonomic shortcut for humans; agents need predictability. Will need a new CLI design for multi-field updates (e.g., repeated `--field` / `--value` pairs, or JSON object input).

4. ~~**Boolean flag support**~~ **RESOLVED:** Yes, required. `--dry-run` and `--output json` are boolean flags on every mutating command. `parse_kwargs` in `util_cli.py` must support bare `--flag` as True. This is now load-bearing, not optional.
