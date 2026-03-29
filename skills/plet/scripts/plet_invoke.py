#!/usr/bin/env python3
"""plet invoke — launch Claude Code subprocesses with transcript capture.

Assembles prompt via plet_prompt.py, launches claude -p, captures streaming
JSONL to transcript file line by line. Returns subprocess exit code.

Usage:
    plet_invoke.py run [<plet_dir>] --iter-id ID_xxx --phase implement|verify --cwd <worktree_path> [--permission-mode MODE] [--model MODEL] [--max-budget N] [--verbose] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

Commands:
    run     Assemble prompt, launch subprocess, capture transcript
"""

import json
import os
import shutil
import subprocess as sp
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    parse_kwargs,
    require_kwargs,
    validate_enum,
    dispatch,
    get_plet_dir,
    extract_output_flags,
    emit_json,
    emit_json_error,
)
from util_io import (
    validate_plet_dir,
    iter_state_path,
    load_iter_state_json,
    transcript_path,
)
from util_subprocess import run


SCRIPT_VERSION = "0.1.0"
SKILL_VERSION = "0.1.1"

VALID_PHASES = ["implement", "verify"]
VALID_PERMISSION_MODES = ["auto", "bypassPermissions", "default"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def help_hint(command):
    return "Run: plet_invoke.py {} --help".format(command)


def scripts_dir():
    return os.path.dirname(os.path.abspath(__file__))


def find_claude():
    """Check if claude is on PATH. Returns path or None."""
    return shutil.which("claude")


def assemble_prompt(plet_dir, iter_id, phase):
    """Call plet_prompt.py assemble. Returns (prompt_text, error_msg)."""
    prm_script = os.path.join(scripts_dir(), "plet_prompt.py")
    result = run([sys.executable, prm_script, "assemble", plet_dir,
                  "--iter-id", iter_id, "--phase", phase])
    if result.returncode != 0:
        return None, "prompt assembly failed: {}".format(result.stderr.strip())
    return result.stdout, None


def build_claude_command(prompt, phase, iter_id, attempt, permission_mode, model, max_budget, verbose):
    """Build the claude -p command list."""
    cmd = ["claude", "-p", prompt, "--output-format", "stream-json",
           "--permission-mode", permission_mode,
           "--no-session-persistence", "--bare",
           "--name", "plet/{}/{}-{}".format(iter_id, phase, attempt)]
    if model:
        cmd.extend(["--model", model])
    if max_budget:
        cmd.extend(["--max-budget-usd", str(max_budget)])
    if verbose:
        cmd.append("--verbose")
    return cmd


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------

def cmd_run(args):
    HELP = """IMPORTANT:
    run launches a Claude Code subprocess. Use --dry-run to preview the
    command without launching. Transcript is captured line by line.

PITFALLS:
    - --iter-id, --phase, and --cwd are all REQUIRED
    - --cwd must be an existing directory (the worktree)
    - Transcript appends on retry — never overwrites, never loses data
    - --bare skips hooks/LSP/plugins for faster startup

USAGE:
    plet_invoke.py run [<plet_dir>] --iter-id ID_xxx --phase implement|verify --cwd <worktree_path> [--permission-mode MODE] [--model MODEL] [--max-budget N] [--verbose] [--dry-run] [--output json [--pretty] [--fields f1,f2]]

    plet_dir           Path to plet directory (default: plet/)
    --iter-id          Iteration ID (required)
    --phase            implement or verify (required)
    --cwd              Working directory for subprocess (required)
    --permission-mode  auto (default) or bypassPermissions
    --model            Model override (e.g., sonnet, opus)
    --max-budget       Maximum USD budget for the subprocess
    --verbose          Pass --verbose to claude
    --dry-run          Preview command without launching

PURPOSE:
    Launches a Claude Code subprocess with the assembled prompt for a
    specific iteration and phase. Captures streaming transcript for
    debugging and replay.

Examples:
    plet_invoke.py run plet/ --iter-id ID_001 --phase implement --cwd .plet/worktrees/TEST/ID_001
    plet_invoke.py run plet/ --iter-id ID_001 --phase implement --cwd /tmp/wt --dry-run
    plet_invoke.py run --iter-id ID_001 --phase verify --cwd /tmp/wt --output json
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    CMD = "run"
    hint = help_hint(CMD)
    plet_dir, remaining = get_plet_dir(args)

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        print(hint, file=sys.stderr)
        return 1

    if not require_kwargs(kwargs, ["iter_id", "phase", "cwd"], HELP):
        return 1

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    cwd = kwargs["cwd"]
    permission_mode = kwargs.get("permission_mode", "auto")
    model = kwargs.get("model")
    max_budget = kwargs.get("max_budget")
    verbose = kwargs.get("verbose", False) is True

    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    if permission_mode not in VALID_PERMISSION_MODES:
        print("Error: invalid --permission-mode '{}' (valid: {})".format(
            permission_mode, ", ".join(VALID_PERMISSION_MODES)), file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    # Validate plet_dir
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        if output_json:
            emit_json_error(CMD, err, SCRIPT_VERSION, pretty)
        else:
            print(err, file=sys.stderr)
        return 1

    # Validate --cwd
    if not os.path.isdir(cwd):
        msg = "Error: working directory not found: {}".format(cwd)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Read attempt number from iter state
    state_data = load_iter_state_json(plet_dir, iter_id)
    if state_data is None:
        msg = "Error: iteration state not found for {}".format(iter_id)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1
    attempt = state_data.get("attempts", {}).get(phase, 1)

    # Derive transcript path
    t_path = transcript_path(plet_dir, iter_id, phase, attempt)

    # Assemble prompt
    prompt_text, prm_err = assemble_prompt(plet_dir, iter_id, phase)
    if prompt_text is None:
        msg = "Error: {}".format(prm_err)
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Build claude command
    claude_cmd = build_claude_command(
        prompt_text, phase, iter_id, attempt,
        permission_mode, model, max_budget, verbose,
    )

    # Dry-run
    if dry_run:
        cmd_str = " ".join(
            '"{}"'.format(c) if " " in c or len(c) > 100 else c
            for c in claude_cmd
        )
        if output_json:
            emit_json({
                "status": "ok",
                "command": CMD,
                "iterationId": iter_id,
                "phase": phase,
                "attempt": attempt,
                "claudeCommand": cmd_str,
                "transcriptPath": t_path,
                "dryRun": True,
            }, SCRIPT_VERSION, pretty, fields)
        else:
            print("DRY RUN — would execute:")
            print(cmd_str)
            print("\nTranscript would be written to: {}".format(t_path))
        return 0

    # Check claude on PATH
    if find_claude() is None:
        msg = "Error: claude not found on PATH"
        if output_json:
            emit_json_error(CMD, msg, SCRIPT_VERSION, pretty)
        else:
            print(msg, file=sys.stderr)
        return 1

    # Create trace directory if needed
    trace_dir = os.path.dirname(t_path)
    if not os.path.isdir(trace_dir):
        os.makedirs(trace_dir, exist_ok=True)

    # Log invocation + full prompt to trace event
    trc_script = os.path.join(scripts_dir(), "plet_trace.py")
    if os.path.isfile(trc_script):
        invocation_data = json.dumps({
            "cwd": cwd,
            "permissionMode": permission_mode,
            "promptLength": len(prompt_text),
            "model": model or "default",
            "maxBudget": max_budget or "none",
            "verbose": verbose,
            "bare": True,
            "transcriptPath": t_path,
            "prompt": prompt_text,
        })
        run([sys.executable, trc_script, "append-event", plet_dir,
             "--iter-id", iter_id, "--phase", phase, "--attempt", str(attempt),
             "--event-type", "invocation", "--data", invocation_data])

    # Log invocation + full prompt to progress.md (via temp file for large prompts)
    iter_title = state_data.get("title", iter_id)
    progress_content = (
        "Launching {} subagent (attempt {})\n\n"
        "**Invocation details:**\n"
        "- Permission mode: {}\n"
        "- Model: {}\n"
        "- Max budget: {}\n"
        "- Working directory: {}\n"
        "- Prompt length: {} chars\n"
        "- Transcript: {}\n\n"
        "**Full prompt:**\n\n"
        "{}"
    ).format(phase, attempt, permission_mode, model or "default",
             max_budget or "none", cwd, len(prompt_text), t_path, prompt_text)
    ent_script = os.path.join(scripts_dir(), "plet_entries.py")
    if os.path.isfile(ent_script):
        # Use --content-file for large content (prompt can be 40KB+)
        # --allow-fences because prompt legitimately contains fence pattern examples
        content_tmp = os.path.join(trace_dir, ".progress_content.tmp")
        with open(content_tmp, "w") as f:
            f.write(progress_content)
        ent_result = run([sys.executable, ent_script, "add-progress", plet_dir,
             "--iter-id", iter_id, "--iter-title", iter_title,
             "--phase", phase, "--attempt", str(attempt),
             "--status", "IN_PROGRESS",
             "--content-file", content_tmp,
             "--allow-fences"])
        if ent_result.returncode != 0:
            print("Warning: progress entry failed: {}".format(ent_result.stderr.strip()),
                  file=sys.stderr)
        if os.path.isfile(content_tmp):
            os.unlink(content_tmp)

    # Launch subprocess with transcript capture
    start_time = time.time()
    transcript_lines = 0

    # Append separator if file exists (never overwrite)
    if os.path.isfile(t_path) and os.path.getsize(t_path) > 0:
        with open(t_path, "a") as f:
            f.write("--- retry ---\n")

    proc = sp.Popen(
        claude_cmd,
        stdout=sp.PIPE,
        stderr=sys.stderr,  # stderr passes through to orchestrator
        text=True,
        cwd=cwd,
    )

    with open(t_path, "a") as transcript:
        for line in proc.stdout:
            transcript.write(line)
            transcript.flush()
            transcript_lines += 1

    proc.wait()
    elapsed = time.time() - start_time
    sub_exit = proc.returncode

    # Output
    if output_json:
        status = "ok" if sub_exit == 0 else "error"
        emit_json({
            "status": status,
            "command": CMD,
            "iterationId": iter_id,
            "phase": phase,
            "attempt": attempt,
            "subprocessExitCode": sub_exit,
            "transcriptPath": t_path,
            "transcriptLines": transcript_lines,
            "elapsedSeconds": round(elapsed, 1),
        }, SCRIPT_VERSION, pretty, fields)
    else:
        if sub_exit == 0:
            print("OK — {} subprocess exited 0".format(phase))
        else:
            print("ERROR — {} subprocess exited {}".format(phase, sub_exit),
                  file=sys.stderr)

    return sub_exit


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "run": cmd_run,
    }
    return dispatch(
        commands, "plet_invoke", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
