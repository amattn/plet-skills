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


def cmd_end(args):
    """End a phase: set verdict, write progress, emit trace, audit tag, commit.

    USAGE:
        plet_phase.py end <plet_dir> --iter-id ID_xxx --phase implement|verify
            --verdict VALUE --progress-content "..."
            [--summary "..."] [--findings '[...]']
            [--report-file PATH]
            [--output json [--pretty] [--fields f1,f2]]

        plet_dir            Path to plet directory (required)
        --iter-id           Iteration ID (e.g., ID_001)
        --phase             implement or verify
        --verdict           Verdict value (implement: completed|blocked, verify: passed|rejected|blocked)
        --progress-content  Content for the completion progress entry
        --summary           Verification report summary (verify only). If provided without
                            --report-file, auto-builds report from criteria in state file.
        --findings          JSON array of finding strings (verify only, default '[]')
        --report-file       Path to verification report JSON (verify only, overrides auto-build)

    WHAT IT DOES (in order):
        1. set-verdict via plet_iter_state.py
        2. add-report (verify only — auto-built from state or from --report-file)
        3. add-progress via plet_entries.py (COMPLETE/BLOCKED/FAILED entry)
        4. append-event via plet_trace.py (phase_end event)
        5. audit-tag via plet_git_ops.py
        6. git add plet/ && git commit

    The subagent still calls gate-post separately after this — gate-post is a
    quality check with a self-correction loop, not bookkeeping.

    VERIFY EXAMPLE (auto-report from state — no --report-file needed):
        plet_phase.py end plet/ --iter-id ID_001 --phase verify --verdict passed \\
            --progress-content "Verified: all AC confirmed." \\
            --summary "All 5 criteria independently verified."
    """
    help_text = cmd_end.__doc__
    hint = "Run: plet_phase.py end --help"

    result = parse_command(
        args,
        help_text,
        known_flags={"iter_id", "phase", "verdict", "progress_content", "report_file", "summary", "findings"},
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

    # Verify phase requires --summary (for auto-report) or --report-file
    if phase == "verify" and not kwargs.get("summary") and not kwargs.get("report_file"):
        print("Error: verify phase requires --summary (for auto-report) or --report-file", file=sys.stderr)
        print(hint, file=sys.stderr)
        return 1

    return _run_end_steps(plet_dir, kwargs, phase, verdict, output_json, pretty, fields)


def _build_criteria_results(ist):
    """Build criteriaResults array from per-iteration state criteria.

    Reads verification object fields written by update-criterion.
    Returns list of dicts ready for JSON serialization.
    """
    results = []
    for c in ist.get("criteria", []):
        v = c.get("verification") or {}
        evidence = v.get("evidence", "")
        crit_status = v.get("status", "not_started")
        # add-report rejects "not_started" — map to "skipped" for unverified criteria
        if crit_status == "not_started":
            crit_status = "skipped"
        results.append(
            {
                "id": c["id"],
                "status": crit_status,
                "oneLiner": v.get("oneLiner") or evidence.split(".")[0][:120] or c.get("description", ""),
                "redTest": v.get("redTest", "none"),
                "noTestRationale": v.get("noTestRationale", ""),
                "relatedEntries": [],
            }
        )
    return results


def _run_end_steps(plet_dir, kwargs, phase, verdict, output_json, pretty, fields):
    """Execute the end-of-phase step sequence. Returns exit code."""
    iter_id = kwargs["iter_id"]
    progress_content = kwargs["progress_content"]
    report_file = kwargs.get("report_file")
    summary = kwargs.get("summary")
    findings_json = kwargs.get("findings")

    status = VERDICT_TO_STATUS.get(verdict, "COMPLETE")
    steps_done = []

    # Read iter state to get attempt number and title
    from util_io import iter_state_path, load_json

    ist = load_json(iter_state_path(plet_dir, iter_id))
    attempt = 1
    iter_title = iter_id
    if ist:
        attempts = ist.get("attempts", {})
        attempt = attempts.get(phase, 1) or 1  # 0 → 1 (phase must have started)
        iter_title = ist.get("title", iter_id)

    # Import sibling cmd functions directly (no subprocess, coverage-visible)
    from plet_entries import cmd_add_progress
    from plet_git_ops import cmd_audit_tag
    from plet_iter_state import cmd_add_report, cmd_set_verdict
    from plet_trace import cmd_append_event

    def _step(name, func, func_args):
        """Run a step, fail fast on error. Handles both int and tuple returns."""
        result = func(func_args)
        rc = result[0] if isinstance(result, tuple) else result
        if rc != 0:
            emit_error("end", f"{name} failed (exit {rc})", SCRIPT_VERSION, output_json, pretty)
            return False
        steps_done.append(name)
        return True

    # Step 1: set-verdict
    if not _step(
        "set-verdict",
        cmd_set_verdict,
        [
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
    ):
        return 1

    # Step 1.5: add-report (verify phase only)
    if phase == "verify" and (summary or report_file):
        if report_file and os.path.isfile(report_file):
            # Explicit report file — read and pass fields
            with open(report_file) as f:
                report_data = json.load(f)
            report_args = [
                plet_dir,
                "--iter-id",
                iter_id,
                "--verdict",
                report_data.get("verdict", verdict),
                "--summary",
                report_data.get("summary", ""),
                "--criteria-results",
                json.dumps(report_data.get("criteriaResults", [])),
                "--findings",
                json.dumps(report_data.get("findings", [])),
                "--related-entries",
                json.dumps(report_data.get("relatedEntries", [])),
                "--agent-id",
                "plet_phase",
            ]
        else:
            # Auto-build from criteria in state file
            criteria_results = _build_criteria_results(ist)
            report_args = [
                plet_dir,
                "--iter-id",
                iter_id,
                "--verdict",
                verdict,
                "--summary",
                summary,
                "--criteria-results",
                json.dumps(criteria_results),
                "--findings",
                findings_json or "[]",
                "--related-entries",
                "[]",
                "--agent-id",
                "plet_phase",
            ]

        if not _step("add-report", cmd_add_report, report_args):
            return 1

    # Step 2: add-progress
    if not _step(
        "add-progress",
        cmd_add_progress,
        [
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
    ):
        return 1

    # Step 3: append-event (decision — phase_end)
    event_data = json.dumps(
        {
            "description": f"{phase} phase ended with verdict: {verdict}",
            "rationale": progress_content,
        }
    )
    if not _step(
        "append-event",
        cmd_append_event,
        [
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
    ):
        return 1

    # Step 4: audit-tag
    if not _step(
        "audit-tag",
        cmd_audit_tag,
        [
            plet_dir,
            "--iter-id",
            iter_id,
            "--phase",
            phase,
        ],
    ):
        return 1

    # Step 5: git add + commit
    project_root = os.path.dirname(os.path.abspath(plet_dir))
    subprocess.run(["git", "add", "-A"], capture_output=True, cwd=project_root)
    commit_msg = f"plet: [{iter_id}] {phase} - {verdict}"
    commit_result = subprocess.run(
        ["git", "commit", "-m", commit_msg, "--allow-empty"],
        capture_output=True,
        text=True,
        cwd=project_root,
    )
    if commit_result.returncode != 0:
        emit_error("end", f"git commit failed: {commit_result.stderr[:200]}", SCRIPT_VERSION, output_json, pretty)
        return 1
    steps_done.append("git-commit")

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


cmd_end.usage = '<plet_dir> --iter-id ID_xxx --phase implement|verify --verdict VALUE --progress-content "..." [--summary "..." for verify auto-report]'  # noqa: E501
cmd_end.example = 'plet_phase.py end plet/ --iter-id ID_001 --phase verify --verdict passed --progress-content "Verified: all AC confirmed." --summary "All 5 criteria independently verified."'  # noqa: E501


def main():
    commands = {
        "end": cmd_end,
    }
    return dispatch(commands, "plet_phase", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
