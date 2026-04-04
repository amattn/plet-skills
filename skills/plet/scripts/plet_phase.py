#!/usr/bin/env python3
"""plet phase lifecycle tool — composite commands for phase boundaries.

Bundles the end-of-phase sequence (set-verdict, progress entry, trace event,
audit tag, git commit) into a single call. Reduces subagent CLI surface from
6 separate calls to 1.

Usage:
    plet_phase.py <command> <plet_dir> --iter-id ID_xxx [args]

Commands:
    end     Complete a phase: set verdict, write progress, emit trace event,
            create audit tag, commit artifacts.

Examples:
    plet_phase.py end plet/ --iter-id ID_001 --phase implement --verdict completed \\
        --progress-content "Implemented: project scaffolding. 5 AC, all green."

    plet_phase.py end plet/ --iter-id ID_001 --phase verify --verdict passed \\
        --progress-content "Verified: all 5 AC independently confirmed." \\
        --report-file /tmp/report.json
"""

import json
import os
import subprocess
import sys

SCRIPT_VERSION = "0.1.0"
from util_cli import (  # noqa: E402
    dispatch,
    emit_error,
    parse_command,
    validate_enum,
)
from util_constants import SKILL_VERSION  # noqa: E402

VALID_PHASES = ["implement", "verify"]
IMPLEMENT_VERDICTS = ["completed", "blocked"]
VERIFY_VERDICTS = ["passed", "rejected", "blocked"]

VERDICT_TO_STATUS = {
    "completed": "COMPLETE",
    "passed": "COMPLETE",
    "blocked": "BLOCKED",
    "rejected": "FAILED",
}


def _scripts_dir():
    """Return the directory containing plet scripts."""
    return os.path.dirname(os.path.abspath(__file__))


def _run_script(name, args):
    """Run a sibling plet script. Returns (stdout, stderr, returncode)."""
    script = os.path.join(_scripts_dir(), name)
    result = subprocess.run(
        [sys.executable, script] + args,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def cmd_end(args):
    """End a phase: set verdict, write progress, emit trace, audit tag, commit.

    USAGE:
        plet_phase.py end <plet_dir> --iter-id ID_xxx --phase implement|verify
            --verdict VALUE --progress-content "..." [--report-file PATH]
            [--output json [--pretty] [--fields f1,f2]]

        plet_dir            Path to plet directory (required)
        --iter-id           Iteration ID (e.g., ID_001)
        --phase             implement or verify
        --verdict           Verdict value (implement: completed|blocked, verify: passed|rejected|blocked)
        --progress-content  Content for the completion progress entry
        --report-file       Path to verification report JSON (verify phase only)

    WHAT IT DOES (in order):
        1. set-verdict via plet_iter_state.py
        2. add-progress via plet_entries.py (COMPLETE/BLOCKED/FAILED entry)
        3. append-event via plet_trace.py (phase_end event)
        4. audit-tag via plet_git_ops.py
        5. git add plet/ && git commit

    The subagent still calls gate-post separately after this — gate-post is a
    quality check with a self-correction loop, not bookkeeping.
    """
    help_text = cmd_end.__doc__
    hint = "Run: plet_phase.py end --help"

    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "phase", "verdict", "progress_content", "report_file"},
        required=["iter_id", "phase", "verdict", "progress_content"],
        allow_dry_run=False,
        hint=hint,
    )
    if result == "help":
        return 0
    if result is None:
        return 1
    plet_dir, kwargs, output_json, pretty, fields, _ = result

    phase = kwargs["phase"]
    if not validate_enum(phase, VALID_PHASES, "--phase"):
        print(hint, file=sys.stderr)
        return 1

    verdict = kwargs["verdict"]
    valid_verdicts = IMPLEMENT_VERDICTS if phase == "implement" else VERIFY_VERDICTS
    if not validate_enum(verdict, valid_verdicts, "--verdict"):
        print(hint, file=sys.stderr)
        return 1

    iter_id = kwargs["iter_id"]
    progress_content = kwargs["progress_content"]
    report_file = kwargs.get("report_file")

    status = VERDICT_TO_STATUS.get(verdict, "COMPLETE")
    steps_done = []
    errors = []

    # Read iter state to get attempt number and title
    from util_io import iter_state_path, load_json

    ist = load_json(iter_state_path(plet_dir, iter_id))
    attempt = 1
    iter_title = iter_id
    if ist:
        attempts = ist.get("attempts", {})
        attempt = attempts.get(phase, 1) or 1  # 0 → 1 (phase must have started)
        iter_title = ist.get("title", iter_id)

    # Step 1: set-verdict
    _, err, rc = _run_script(
        "plet_iter_state.py",
        [
            "set-verdict",
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
            "--verdict",
            verdict,
            "--agent-id",
            "plet_phase",
        ],
    )
    if rc != 0:
        errors.append(f"set-verdict failed: {err[:200]}")
    else:
        steps_done.append("set-verdict")

    # Step 1.5: add-report (verify phase only, if report file provided)
    if phase == "verify" and report_file and os.path.isfile(report_file):
        with open(report_file) as f:
            report_data = json.load(f)
        report_json = json.dumps(report_data)
        _, err, rc = _run_script(
            "plet_iter_state.py",
            [
                "add-report",
                plet_dir,
                "--iter-id",
                iter_id,
                "--report",
                report_json,
            ],
        )
        if rc != 0:
            errors.append(f"add-report failed: {err[:200]}")
        else:
            steps_done.append("add-report")

    # Step 2: add-progress
    _, err, rc = _run_script(
        "plet_entries.py",
        [
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
            status,
            "--content",
            progress_content,
        ],
    )
    if rc != 0:
        errors.append(f"add-progress failed: {err[:200]}")
    else:
        steps_done.append("add-progress")

    # Step 3: append-event (decision — phase_end)
    event_data = json.dumps(
        {
            "description": f"{phase} phase ended with verdict: {verdict}",
            "rationale": progress_content,
        }
    )
    _, err, rc = _run_script(
        "plet_trace.py",
        [
            "append-event",
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
            "--attempt",
            str(attempt),
            "--event-type",
            "decision",
            "--data",
            event_data,
        ],
    )
    if rc != 0:
        errors.append(f"append-event failed: {err[:200]}")
    else:
        steps_done.append("append-event")

    # Step 4: audit-tag
    _, err, rc = _run_script(
        "plet_git_ops.py",
        [
            "audit-tag",
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
        ],
    )
    if rc != 0:
        errors.append(f"audit-tag failed: {err[:200]}")
    else:
        steps_done.append("audit-tag")

    # Step 5: git add (all plet artifacts + any source changes) && git commit
    project_root = os.path.dirname(os.path.abspath(plet_dir))
    subprocess.run(["git", "add", "-A"], capture_output=True, cwd=project_root)
    commit_msg = f"plet: [{iter_id}] {phase} - {verdict}"
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg, "--allow-empty"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if commit_result.returncode == 0:
        steps_done.append("git-commit")
    else:
        errors.append(f"git commit failed: {commit_result.stderr[:200]}")

    # Report
    if errors:
        msg = "Phase end partially failed: {}. Completed: {}.".format("; ".join(errors), ", ".join(steps_done))
        emit_error("end", msg, SCRIPT_VERSION, output_json, pretty)
        return 1

    if output_json:
        from util_cli import emit_json

        emit_json(
            {
                "status": "ok",
                "command": "end",
                "phase": phase,
                "verdict": verdict,
                "iterationId": iter_id,
                "steps": steps_done,
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        print(f"OK — {phase} phase ended: {verdict} ({', '.join(steps_done)})")

    return 0


cmd_end.usage = '<plet_dir> --iter-id ID_xxx --phase implement --verdict completed --progress-content "..."'  # noqa: E501
cmd_end.example = 'plet_phase.py end plet/ --iter-id ID_001 --phase implement --verdict completed --progress-content "Implemented: scaffolding. All checks pass."'  # noqa: E501


def main():
    commands = {
        "end": cmd_end,
    }
    return dispatch(commands, "plet_phase", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
