# CLAUDE.md — plet scripts

Coding standards for Python scripts in `skills/plet/scripts/`. These scripts are enforcement tools that agents call instead of writing artifacts freehand — schema compliance, format compliance, and pre/post-phase checks.

## Design Principle

**Skills for Judgment, Code for Compliance.** These scripts exist because prose rules drift when agents interpret them independently across many iterations. The scripts make compliance automatic. See PLET.md § "Skills for Judgment, Code for Compliance."

## Hard Constraints

### Zero External Dependencies

Scripts use **Python stdlib only** — no third-party packages, no `pip install`, no `requirements.txt`. Scripts ship inside the skill package and must work on any machine with Python 3 installed. Autonomous agents cannot install packages, and target projects should never need to manage plet's dependencies.

Internal modules (`util_*.py`) are not external dependencies — they ship in the same directory, same version, same deployment. Scripts may import from `util_cli`, `util_io`, and `util_id`.

Scripts may also call other `plet_*.py` scripts — via `subprocess` or potentially direct import. The orchestrator in particular calls most other scripts. These are sibling dependencies within the same package, not external.

If a script needs functionality beyond stdlib + internal modules + sibling scripts, either find a stdlib solution or reconsider whether the feature belongs in a script.

### No Interactive Input

Scripts must **never prompt for input** — no `input()`, no `sys.stdin` reads, no interactive confirmations. All input comes via CLI arguments. Autonomous agents can't type into prompts. A script that blocks on input is a stalled agent.

### Python Version

Target **Python 3.8+** as the minimum. Avoid features from 3.10+ (`match/case`, `X | Y` union types, `tomllib`). Python 3.8 is the oldest version still widely deployed on production systems and CI environments.

## Script Standards

### File Setup

- **Shebang:** `#!/usr/bin/env python3` — portable across macOS, Linux, and CI environments
- **Executable bit:** all scripts must be `chmod +x`. Combined with the shebang, this allows direct invocation via path without prefixing `python3`. This is what makes the `allowed-tools` pattern work — `Bash(${CLAUDE_SKILL_DIR}/scripts/*)` approves only shipped scripts regardless of the Python binary name on the system
- **Module docstring:** purpose, what it enforces, usage examples for every command

### Structure

Every script follows the same structure:

1. Shebang + module docstring
2. **Imports:** stdlib + internal modules only (see Hard Constraints)
3. **Constants:** module-level, ALL_CAPS. Valid enum values, required fields, schema versions
4. **Utility functions:** shared helpers (`now_iso()`, file I/O, ID generation)
5. **Command functions:** one `cmd_<name>(args)` function per command
6. **Main dispatch:** `main()` with command dict and `sys.exit()`

### CLI Conventions

- **Command-based interface:** `script.py <command> [args]` — not flag-based (`script.py --validate`)
- **Help everywhere:** every command supports `-h` and `--help`. Top-level `script.py --help` prints the module docstring with all commands. Help text is agent-readable — include copy-pasteable examples that agents can use directly
- **Named arguments with `--`:** `--iter-id ID_001 --phase implement`. Positional args only for the first 1-2 arguments (file paths, artifact directories)
- **No argparse:** manual argument parsing via `parse_kwargs()` pattern. Keeps scripts simple, avoids argparse's verbosity, and gives full control over error messages. Use the shared `parse_kwargs` pattern from `plet_entries.py`
- **JSON for complex values:** arrays and objects passed as JSON strings: `--criteria '[{"id":"AC_1"}]'`
- **Version flag:** every script supports `--version`, printing `<script_name> <version> (built against plet skill <skill_version>)`. Example: `plet_state 0.1.0 (built against plet skill 0.1.0)`. The skill version is the version from `skills/plet/SKILL.md` frontmatter that the script was built to work with. If the skill makes a non-backward-compatible semver change (major bump), scripts built against the old version need to be reviewed and updated
- **Exit codes:** 0 = success, 1 = error (validation failure, missing args, bad input). Never use other exit codes
- **Output convention:** results to stdout, errors to stderr. On success, print a short confirmation (`OK — ...`). On error, print the specific error message plus a help hint: `Run: <script> <command> --help`. Print the full HELP text only for missing-required-args errors (where the agent needs the full interface). For validation errors (wrong enum value, bad format), the error message itself says what's valid — the hint nudges without flooding context
- **Subcommand HELP strings:** each `cmd_*` function defines a `HELP` variable at the top with usage, arguments, and examples. Printed on `--help` or when required args are missing

### Idempotency

Where practical, commands should be **safe to run twice** with the same result:
- `validate` on a valid file always returns 0
- `check` on an iteration with entries always reports the same counts
- `init` on an existing file should error (not overwrite) — creation is not idempotent, but the failure mode is safe

Mutations (`update-criterion`, `update-field`, `add-progress`) are inherently not idempotent, but should be predictable — running the same update twice produces the expected state, and appending the same entry twice produces two entries (not a corruption).

### File I/O

- **Atomic writes for state files:** write to `path.tmp`, then `os.rename(tmp, path)`. External readers never see partial JSON
- **Atomic appends for runtime artifacts:** write to temp file, read it back, append to target, remove temp. See `plet_entries.py:atomic_append()`
- **Always add trailing newline** after JSON (`f.write("\n")`) so files are POSIX-compliant and diff-friendly
- **Never read-modify-write runtime artifacts.** Append only. State files are read-modify-write (single writer per iteration)

### Error Handling

- **Validate inputs before doing work.** Check required args, enum values, file existence before touching any files
- **Specific error messages:** `Error: invalid lifecycle 'running' (valid: ineligible, queued, ...)` — always show what was received and what was expected
- **Fail fast:** first error exits. Don't accumulate errors across unrelated operations (validation is the exception — accumulate all schema errors, then report)

### Naming

- **CLI tool scripts:** `plet_<domain>.py` — e.g., `plet_state.py`, `plet_entries.py`, `plet_trace.py`, `plet_git.py`. Callable via `Bash()`, listed in `allowed-tools`, executable (`chmod +x`)
- **Internal modules:** `util_<concern>.py` — e.g., `util_cli.py`, `util_io.py`, `util_id.py`. Imported by `plet_*.py` scripts, never called directly, not listed in `allowed-tools`, not executable. The `plet_` prefix signals "CLI tool"; `util_` signals "internal dependency."
- **Command names:** lowercase, hyphen-separated — e.g., `update-criterion`, `add-progress`, `check-stashes`
- **Function names:** `cmd_<command_with_underscores>` — e.g., `cmd_update_criterion`, `cmd_add_progress`

### Testing

Tests live at `skills/plet/tests/` (sibling to `scripts/`, not inside it).

**File naming:** `test_<script_name>.py` — e.g., `test_plet_state.py`, `test_plet_entries.py`

**Zero dependencies applies to tests too.** No pytest, no unittest, no third-party test frameworks. Tests use a minimal custom harness built on stdlib only. This matches the constraint on the scripts themselves — if the scripts can't use third-party packages, neither can their tests.

**Run with:** `./skills/plet/tests/test_<script_name>.py` — each test file is directly executable.

**Run all:** `./skills/plet/tests/test_all.py` — runs all test files in parallel with progress (default, ~27s). Tell the user the expected duration before running. Use `-s` for sequential (~68s), `-v` for verbose (sequential with pass/fail counts), or `-q` for quiet summary only.

**Test harness pattern** (consistent across all test files):

```python
TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_<name>.py")

passed = 0
failed = 0

def run(args, expect_exit=0):
    """Run the script with args via subprocess, assert exit code."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(...)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def check(name, condition, detail=""):
    """Record a test result — pass or fail with detail."""
    global passed, failed
    ...
```

**Key principles:**
- **Test the CLI interface**, not internal functions. Every test calls the script via `subprocess.run()` — this tests what agents actually experience
- **Temp fixtures:** each test creates temp files/directories, runs commands against them, validates output + file contents, then cleans up. Use `tempfile.mkdtemp()` for directories, `tempfile.NamedTemporaryFile()` for files
- **Tests must clean up after themselves** — no leftover temp files
- **Test both success and failure paths** — valid input returns 0 with expected output, invalid input returns 1 with a helpful error message
- **Test `--help` on every command** — verify it exits 0 and produces output (agents rely on help text)

### Allowed Tools

Scripts that need to be callable by agents without permission prompts must be listed in `skills/plet/SKILL.md` frontmatter under `allowed-tools`:

```yaml
allowed-tools:
  - Bash(${CLAUDE_SKILL_DIR}/scripts/plet_state.py *)
  - Bash(${CLAUDE_SKILL_DIR}/scripts/plet_entries.py *)
```

Add new scripts to this list as they're built. The path-based pattern (`scripts/*`) approves only shipped scripts — more secure than `Bash(python *)` which would approve arbitrary Python commands.

## Current Inventory

### CLI Tools (`plet_*.py`)

| Script | Purpose | Commands |
|--------|---------|----------|
| `plet_state.py` | State file schema enforcement | `validate`, `update-criterion`, `update-field`, `init` |
| `plet_entries.py` | Runtime artifact entry formatting | `add-progress`, `add-learning`, `add-emergent`, `check` |
| `plet_fingerprint.py` | Fingerprint extraction, embedding, staleness detection | `extract`, `embed`, `check` |
| `plet_trace.py` | Trace NDJSON schema enforcement | `append-event`, `validate`, `query` |
| `plet_git_iteration.py` | Git iteration lifecycle (branches, worktrees) | `branch-name`, `worktree-create`, `worktree-remove` |
| `plet_git_ops.py` | Git workflow operations | `audit-tag`, `merge-squash` |
| `plet_git_check.py` | Git compliance checks | `check-iteration`, `check-session` |
| `plet_gate_session.py` | Session-level gate checks (read-only) | `detect`, `status`, `preflight`, `postflight` |
| `plet_gate_phase.py` | Phase gate (pre/post, `--phase implement\|verify`) | `pre`, `post` |
| `plet_prompt.py` | Prompt assembly for subagents | `assemble` |
| `plet_invoke.py` | Subprocess launch + transcript capture | `run` |
| `plet_schedule.py` | Loop scheduling decisions (read-only) | `eligible`, `check-breakpoints`, `check-retry` |
| `plet_session.py` | Session lifecycle management (mutating) | `start-session`, `end-session` |
| `plet_orchestrator.py` | Main implement→verify loop (the capstone) | `run` |

### Internal Modules (`util_*.py`)

| Module | Purpose | Key functions |
|--------|---------|---------------|
| `util_cli.py` | Argument parsing, validation, timestamps, dispatch, output filtering, shared CLI helpers | `parse_kwargs`, `require_kwargs`, `validate_enum`, `validate_int`, `now_iso`, `dispatch`, `filter_fields`, `get_plet_dir`, `extract_output_flags`, `emit_json`, `emit_json_error` |
| `util_io.py` | Atomic file I/O, path derivation, plet dir validation, convenience JSON loaders | `load_json`, `atomic_write_json`, `atomic_append`, `load_text`, `state_json_path`, `iter_state_path`, `requirements_path`, `load_global_state_json`, `load_iter_state_json`, `validate_plet_dir`, `DEFAULT_PLET_DIR` |
| `util_id.py` | Plet ID generation (Crockford Base32, timestamps, context segments) | `generate_plet_id`, `crockford_encode`, `crockford_timestamp`, `normalize_iteration`, `phase_attempt_segment` |
| `util_state.py` | State file validation and validated loading (global + per-iteration) | `load_and_validate_global_state(plet_dir)`, `load_and_validate_iter_state(plet_dir, iter_id)`, `validate_global_state`, `validate_iter_state` |
| `util_format.py` | Canonical markdown templates for runtime artifact entries | `now_iso`, `build_progress_entry`, `build_learning_entry`, `build_emergent_entry` |
| `util_subprocess.py` | Subprocess execution with capture, error formatting, timeout | `run`, `run_git` |
| `util_git.py` | Pure git naming conventions (branch names, no git ops) | `derive_branch_name` |
