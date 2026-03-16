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
| UNV_CMD_10 | Named arguments with `--` for options. Positional args only for the first 1-2 arguments (file paths, artifact directories) | P0 |
| UNV_CMD_11 | No argparse — manual parsing via `parse_kwargs()` pattern | P0 |
| UNV_CMD_12 | Complex values (arrays, objects) passed as JSON strings | P0 |
| UNV_CMD_13 | Every script supports `--version`, printing `<script_name> <version> (built against plet skill <skill_version>)` | P0 |
| UNV_CMD_14 | Exit codes: 0 = success, 1 = error. No other exit codes | P0 |
| UNV_CMD_15 | Output: results to stdout, errors to stderr. Success prints `OK — ...`. Errors print the error and the command's help text | P0 |
| UNV_CMD_16 | Each `cmd_*` function defines a `HELP` variable at the top with usage, arguments, and examples | P0 |

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

## Naming

| ID | Requirement | Priority |
|----|-------------|----------|
| UNV_DXP_1 | Script names: `plet_<domain>.py` | P0 |
| UNV_DXP_2 | Command names: lowercase, hyphen-separated (e.g., `update-criterion`) | P0 |
| UNV_DXP_3 | Function names: `cmd_<command_with_underscores>` (e.g., `cmd_update_criterion`) | P0 |

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

1. **`parse_kwargs` as shared utility** — `plet_entries.py` has a shared `parse_kwargs()` function; `plet_state.py` duplicates the logic inline. Should `parse_kwargs` be extracted into a shared module that all scripts import? Or should each script copy the pattern? Shared module risks violating the "zero deps" spirit (internal dep is still a dep); copy-paste risks drift. Current convention (UNV_CMD_11) says "use the `parse_kwargs` pattern" but doesn't specify shared vs copied.

2. **Positional args limit** — UNV_CMD_10 says "positional only for the first 1-2 arguments." `plet_state.py update-criterion` uses 5 positional args. Is this a violation to fix, or does `update-criterion`'s ergonomic case justify an exception? Migrating to `--criterion-id AC_1 --phase implementation --status pass --evidence "..."` is more consistent but more verbose for a high-frequency command.

3. **`update-field` alternating pairs** — `plet_state.py update-field` uses `field value field value` without `--` prefixes — a third parsing pattern. Is this an intentional ergonomic exception (it reads naturally: `update-field lifecycle implementing`) or an inconsistency to fix? If exception, document it. If fix, migrate to `--field lifecycle --value implementing` or similar.

4. **Boolean flag support** — `plet_entries.py`'s `parse_kwargs` handles `--flag` without a value as `True`. `plet_state.py`'s inline parser does not. Should boolean flags be a required capability of all kwarg parsing, or is it only needed where a script actually uses boolean flags?
