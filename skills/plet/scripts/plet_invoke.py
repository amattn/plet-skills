#!/usr/bin/env python3
"""plet invoke — launch Claude Code subprocesses with transcript capture.

Assembles prompt via plet_prompt.py, launches claude -p, captures streaming
NDJSON to transcript file line by line. Returns subprocess exit code.

Usage:
    plet_invoke.py run <plet_dir> --iter-id ID_xxx --phase implement|verify
        --cwd <worktree_path> [--permission-mode MODE] [--model MODEL]
        [--max-budget N] [--verbose] [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

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
    dispatch,
    emit_error,
    emit_json,
    parse_command,
    validate_enum,
)
from util_io import (
    load_iter_state_json,
    transcript_path,
    validate_plet_dir,
)
from util_subprocess import run

SCRIPT_VERSION = "0.2.0"
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]
VALID_PERMISSION_MODES = ["auto", "bypassPermissions", "default"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def help_hint(command):
    return f"Run: plet_invoke.py {command} --help"


def scripts_dir():
    return os.path.dirname(os.path.abspath(__file__))


def _validate_run_inputs(phase, permission_mode, plet_dir, cwd, cmd_name, output_json, pretty, hint):
    """Validate phase, permission_mode, plet_dir, and cwd. Returns None on success, exit code on error."""
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1
    if permission_mode not in VALID_PERMISSION_MODES:
        print(
            "Error: invalid --permission-mode '{}' (valid: {})".format(
                permission_mode, ", ".join(VALID_PERMISSION_MODES)
            ),
            file=sys.stderr,
        )
        print(hint, file=sys.stderr)
        return 1
    valid, err = validate_plet_dir(plet_dir)
    if not valid:
        emit_error(cmd_name, err, SCRIPT_VERSION, output_json, pretty)
        return 1
    if not os.path.isdir(cwd):
        emit_error(cmd_name, f"Error: working directory not found: {cwd}", SCRIPT_VERSION, output_json, pretty)
        return 1
    return None


def find_claude():
    """Check if claude is on PATH. Returns path or None."""
    return shutil.which("claude")


def assemble_prompt(plet_dir, iter_id, phase):
    """Call plet_prompt.py assemble. Returns (prompt_text, error_msg)."""
    prm_script = os.path.join(scripts_dir(), "plet_prompt.py")
    result = run([sys.executable, prm_script, "assemble", plet_dir, "--iter-id", iter_id, "--phase", phase])
    if result.returncode != 0:
        return None, f"prompt assembly failed: {result.stderr.strip()}"
    return result.stdout, None


def build_claude_command(prompt, phase, iter_id, attempt, permission_mode, model, max_budget, verbose):
    """Build the claude -p command list."""
    cmd = [
        "claude",
        "-p",
        prompt,
        "--output-format",
        "stream-json",
        "--verbose",
        "--permission-mode",
        permission_mode,
        "--no-session-persistence",
        "--name",
        f"plet/{iter_id}/{phase}-{attempt}",
    ]
    if model:
        cmd.extend(["--model", model])
    if max_budget:
        cmd.extend(["--max-budget-usd", str(max_budget)])
    return cmd


# ---------------------------------------------------------------------------
# run helpers
# ---------------------------------------------------------------------------


def _auto_detect_permission_mode(cwd, plet_dir):
    """Auto-detect permission mode from project settings. Returns mode string."""
    project_root = os.path.dirname(os.path.abspath(plet_dir))
    for search_dir in [cwd, project_root]:
        settings_path = os.path.join(search_dir, ".claude", "settings.json")
        if os.path.isfile(settings_path):
            try:
                with open(settings_path) as _f:
                    _settings = json.load(_f)
                perms = _settings.get("permissions", {})
                if "bypassPermissions" in perms:
                    return "bypassPermissions"
                elif perms.get("defaultMode") == "auto":
                    return "auto"
            except (json.JSONDecodeError, OSError):
                pass
    return "auto"


def _build_prompt_with_env(prompt_text, plet_env):
    """Prepend environment section to prompt text."""
    env_lines = [
        "# Environment",
        "",
        "**IMPORTANT: Read your environment variables (`env | grep -E 'PLET|CLAUDE'`) for paths and context.**",
        "The key variables are listed below for reference, but always check the live env for the full set.",
        "Do NOT search the filesystem for plet scripts — use `$PLET_SCRIPTS_DIR`.",
        "",
    ]
    for key, val in sorted(plet_env.items()):
        env_lines.append(f"- `{key}={val}`")
    env_lines.append("")
    env_lines.append("Call scripts as: `$PLET_SCRIPTS_DIR/plet_iter_state.py ...`")
    env_lines.append("")
    return "\n".join(env_lines) + "\n" + prompt_text


def _log_invocation(
    plet_dir,
    iter_id,
    phase,
    attempt,
    cwd,
    permission_mode,
    prompt_text,
    model,
    max_budget,
    verbose,
    t_path,
    state_data,
    trace_dir,
):
    """Log invocation to trace event and progress.md."""
    trc_script = os.path.join(scripts_dir(), "plet_trace.py")
    if os.path.isfile(trc_script):
        invocation_data = json.dumps(
            {
                "cwd": cwd,
                "permissionMode": permission_mode,
                "promptLength": len(prompt_text),
                "model": model or "default",
                "maxBudget": max_budget or "none",
                "verbose": verbose,
                "bare": True,
                "transcriptPath": t_path,
                "prompt": prompt_text,
            }
        )
        run(
            [
                sys.executable,
                trc_script,
                "append-event",
                plet_dir,
                "--iter-id",
                iter_id,
                "--phase",
                phase,
                "--attempt",
                str(attempt),
                "--event-type",
                "invocation",
                "--data",
                invocation_data,
            ]
        )

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
        "Full prompt is in the trace event file, not repeated here."
    ).format(phase, attempt, permission_mode, model or "default", max_budget or "none", cwd, len(prompt_text), t_path)
    ent_script = os.path.join(scripts_dir(), "plet_entries.py")
    if os.path.isfile(ent_script):
        content_tmp = os.path.join(trace_dir, ".progress_content.tmp")
        with open(content_tmp, "w") as f:
            f.write(progress_content)
        ent_result = run(
            [
                sys.executable,
                ent_script,
                "add-progress",
                plet_dir,
                "--iter-id",
                iter_id,
                "--iter-title",
                iter_title,
                "--phase",
                phase,
                "--attempt",
                str(attempt),
                "--status",
                "IN_PROGRESS",
                "--content-file",
                content_tmp,
                "--allow-fences",
            ]
        )
        if ent_result.returncode != 0:
            print(f"Warning: progress entry failed: {ent_result.stderr.strip()}", file=sys.stderr)
        if os.path.isfile(content_tmp):
            os.unlink(content_tmp)


def _launch_and_capture(claude_cmd, cwd, plet_env, t_path):
    """Launch subprocess and capture transcript. Returns (exit_code, transcript_lines, elapsed)."""
    start_time = time.time()
    transcript_lines = 0

    if os.path.isfile(t_path) and os.path.getsize(t_path) > 0:
        with open(t_path, "a") as f:
            f.write("--- retry ---\n")

    sub_env = os.environ.copy()
    sub_env.update(plet_env)

    proc = sp.Popen(
        claude_cmd,
        stdout=sp.PIPE,
        stderr=sys.stderr,
        text=True,
        cwd=cwd,
        env=sub_env,
    )

    with open(t_path, "a") as transcript:
        for line in proc.stdout:
            transcript.write(line)
            transcript.flush()
            transcript_lines += 1

    proc.wait()
    elapsed = time.time() - start_time
    return proc.returncode, transcript_lines, elapsed


# ---------------------------------------------------------------------------
# run command
# ---------------------------------------------------------------------------


def cmd_run(args):
    help_text = """IMPORTANT:
    run launches a Claude Code subprocess. Use --dry-run to preview the
    command without launching. Transcript is captured line by line.

PITFALLS:
    - --iter-id, --phase, and --cwd are all REQUIRED
    - --cwd must be an existing directory (the worktree)
    - Transcript appends on retry — never overwrites, never loses data
    - --bare skips hooks/LSP/plugins for faster startup

USAGE:
    plet_invoke.py run <plet_dir> --iter-id ID_xxx
        --phase implement|verify --cwd <worktree_path>
        [--permission-mode MODE] [--model MODEL] [--max-budget N]
        [--verbose] [--dry-run]
        [--output json [--pretty] [--fields f1,f2]]

    plet_dir           Path to plet directory (required)
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
    cmd_name = "run"
    hint = help_hint(cmd_name)
    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "phase", "cwd", "permission_mode", "model", "max_budget", "verbose"},
        required=["iter_id", "phase", "cwd"],
        allow_dry_run=True,
        hint=hint,
    )
    if result == "help":
        return 0
    if result is None:
        return 1
    plet_dir, kwargs, output_json, pretty, fields, dry_run = result

    iter_id = kwargs["iter_id"]
    phase = kwargs["phase"]
    cwd = kwargs["cwd"]
    permission_mode = kwargs.get("permission_mode")
    if permission_mode is None:
        permission_mode = _auto_detect_permission_mode(cwd, plet_dir)
    model = kwargs.get("model")
    max_budget = kwargs.get("max_budget")
    verbose = kwargs.get("verbose", False) is True

    err = _validate_run_inputs(phase, permission_mode, plet_dir, cwd, cmd_name, output_json, pretty, hint)
    if err is not None:
        return err

    state_data = load_iter_state_json(plet_dir, iter_id)
    if state_data is None:
        emit_error(cmd_name, f"Error: iteration state not found for {iter_id}", SCRIPT_VERSION, output_json, pretty)
        return 1
    attempt = state_data.get("attempts", {}).get(phase, 0) + 1

    t_path = transcript_path(plet_dir, iter_id, phase, attempt)

    prompt_text, prm_err = assemble_prompt(plet_dir, iter_id, phase)
    if prompt_text is None:
        emit_error(cmd_name, f"Error: {prm_err}", SCRIPT_VERSION, output_json, pretty)
        return 1

    plet_env = _build_plet_env(plet_dir, cwd, iter_id, phase, attempt)
    prompt_text = _build_prompt_with_env(prompt_text, plet_env)
    claude_cmd = build_claude_command(prompt_text, phase, iter_id, attempt, permission_mode, model, max_budget, verbose)

    if dry_run:
        cmd_str = " ".join(f'"{c}"' if " " in c or len(c) > 100 else c for c in claude_cmd)
        if output_json:
            emit_json(
                {
                    "status": "ok",
                    "command": cmd_name,
                    "iterationId": iter_id,
                    "phase": phase,
                    "attempt": attempt,
                    "claudeCommand": cmd_str,
                    "transcriptPath": t_path,
                    "dryRun": True,
                },
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        else:
            print("DRY RUN — would execute:")
            print(cmd_str)
            print(f"\nTranscript would be written to: {t_path}")
        return 0

    return _execute_run(
        cmd_name,
        claude_cmd,
        plet_dir,
        plet_env,
        iter_id,
        phase,
        attempt,
        cwd,
        permission_mode,
        prompt_text,
        model,
        max_budget,
        verbose,
        t_path,
        state_data,
        output_json,
        pretty,
        fields,
    )


def _build_plet_env(plet_dir, cwd, iter_id, phase, attempt):
    """Build plet environment variables dict."""
    env = {
        "PLET_SCRIPTS_DIR": scripts_dir(),
        "PLET_DIR": os.path.abspath(plet_dir) if plet_dir else "",
        "PLET_PROJECT_DIR": os.path.abspath(cwd),
        "PLET_WORKTREE_BASE": os.path.abspath(os.path.join(os.path.dirname(plet_dir), ".plet", "worktrees")),
        "PLET_ITER_ID": iter_id,
        "PLET_PHASE": phase,
        "PLET_ATTEMPT": str(attempt),
    }
    for passthrough in ("CLAUDE_SKILL_DIR", "CLAUDE_CONFIG_DIR"):
        if passthrough in os.environ:
            env[passthrough] = os.environ[passthrough]
    return env


def _execute_run(
    cmd_name,
    claude_cmd,
    plet_dir,
    plet_env,
    iter_id,
    phase,
    attempt,
    cwd,
    permission_mode,
    prompt_text,
    model,
    max_budget,
    verbose,
    t_path,
    state_data,
    output_json,
    pretty,
    fields,
):
    """Execute the claude subprocess (non-dry-run path)."""
    if find_claude() is None:
        emit_error(cmd_name, "Error: claude not found on PATH", SCRIPT_VERSION, output_json, pretty)
        return 1

    trace_dir = os.path.dirname(t_path)
    if not os.path.isdir(trace_dir):
        os.makedirs(trace_dir, exist_ok=True)

    _log_invocation(
        plet_dir,
        iter_id,
        phase,
        attempt,
        cwd,
        permission_mode,
        prompt_text,
        model,
        max_budget,
        verbose,
        t_path,
        state_data,
        trace_dir,
    )

    sub_exit, transcript_lines, elapsed = _launch_and_capture(claude_cmd, cwd, plet_env, t_path)

    if output_json:
        emit_json(
            {
                "status": "ok" if sub_exit == 0 else "error",
                "command": cmd_name,
                "iterationId": iter_id,
                "phase": phase,
                "attempt": attempt,
                "subprocessExitCode": sub_exit,
                "transcriptPath": t_path,
                "transcriptLines": transcript_lines,
                "elapsedSeconds": round(elapsed, 1),
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        if sub_exit == 0:
            print(f"OK — {phase} subprocess exited 0")
        else:
            print(f"ERROR — {phase} subprocess exited {sub_exit}", file=sys.stderr)

    return sub_exit


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "run": cmd_run,
    }
    return dispatch(commands, "plet_invoke", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
