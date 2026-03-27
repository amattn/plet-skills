"""Shared gate functions for implement and verify phase gates.

Internal module — imported by plet_gate_impl.py and plet_gate_verify.py.
Not a CLI tool, not listed in allowed-tools.

Provides the common check functions that both gate scripts delegate to:
GTC (git checks), STA (state validation), ENT (entry checks), trace
(existence + TRC validate), plus summarize and format output.
"""

import json
import os
import sys

from util_io import iter_state_path
from util_subprocess import run


# ---------------------------------------------------------------------------
# Subprocess helpers
# ---------------------------------------------------------------------------

def scripts_dir():
    """Return the directory containing plet scripts."""
    return os.path.dirname(os.path.abspath(__file__))


def run_tool(script_name, args):
    """Run a sibling plet script via subprocess. Returns (parsed_json, raw_result).

    Returns (None, None) if the script doesn't exist.
    Returns (None, result) if JSON parsing fails.
    """
    script_path = os.path.join(scripts_dir(), script_name)
    if not os.path.isfile(script_path):
        return None, None
    result = run([sys.executable, script_path] + args)
    try:
        data = json.loads(result.stdout)
        return data, result
    except (json.JSONDecodeError, ValueError):
        return None, result


# ---------------------------------------------------------------------------
# Check functions — each returns a check dict or list of check dicts
# ---------------------------------------------------------------------------

def run_gtc_checks(plet_dir, iter_id, phase):
    """Call plet_git_check.py check-iteration and return list of check dicts.

    Each GTC check is prefixed with 'git:' (e.g., git:correct-branch).
    """
    checks = []
    data, result = run_tool("plet_git_check.py", [
        "check-iteration", plet_dir, "--iter-id", iter_id,
        "--phase", phase, "--output", "json",
    ])
    if data is None and result is None:
        checks.append({"name": "git-check", "status": "fail",
                        "detail": "plet_git_check.py not found"})
    elif data is None:
        checks.append({"name": "git-check", "status": "fail",
                        "detail": "could not parse plet_git_check.py output"})
    else:
        for gc in data.get("checks", []):
            checks.append({
                "name": "git:{}".format(gc["name"]),
                "status": gc["status"],
                "detail": gc.get("detail", ""),
            })
    return checks


def run_sta_validate(plet_dir, iter_id):
    """Call plet_state.py validate and return a check dict."""
    is_path = iter_state_path(plet_dir, iter_id)
    data, result = run_tool("plet_state.py", [
        "validate", is_path, "--output", "json",
    ])
    if data is None and result is None:
        return {"name": "state-valid", "status": "fail",
                "detail": "plet_state.py not found"}
    if data is None:
        return {"name": "state-valid", "status": "fail",
                "detail": "could not parse plet_state.py output"}
    if result.returncode == 0:
        return {"name": "state-valid", "status": "pass",
                "detail": "{} valid".format(os.path.basename(is_path))}
    errors = data.get("errors", [])
    detail = "; ".join(errors[:3]) if errors else "validation failed"
    return {"name": "state-valid", "status": "fail", "detail": detail}


def run_ent_check(plet_dir, iter_id):
    """Call plet_entries.py check and return list of check dicts.

    Single subprocess call, three check results: progress (FAIL if 0),
    learnings (WARN if 0), emergent (WARN if 0 with guidance).
    """
    checks = []
    data, result = run_tool("plet_entries.py", [
        "check", plet_dir, "--iter-id", iter_id, "--output", "json",
    ])
    if data is None and result is None:
        for name in ("progress-entry", "learnings-entry", "emergent-entry"):
            checks.append({"name": name, "status": "fail",
                            "detail": "plet_entries.py not found"})
        return checks
    if data is None:
        for name in ("progress-entry", "learnings-entry", "emergent-entry"):
            checks.append({"name": name, "status": "fail",
                            "detail": "could not parse plet_entries.py output"})
        return checks

    artifacts = data.get("artifacts", {})

    # Progress — FAIL if 0
    p_count = artifacts.get("progress", {}).get("count", 0)
    if p_count > 0:
        checks.append({"name": "progress-entry", "status": "pass",
                        "detail": "{} progress entries for {}".format(p_count, iter_id)})
    else:
        checks.append({"name": "progress-entry", "status": "fail",
                        "detail": "0 progress entries for {}".format(iter_id)})

    # Learnings — WARN if 0
    l_count = artifacts.get("learnings", {}).get("count", 0)
    if l_count > 0:
        checks.append({"name": "learnings-entry", "status": "pass",
                        "detail": "{} learnings entries for {}".format(l_count, iter_id)})
    else:
        checks.append({"name": "learnings-entry", "status": "warn",
                        "detail": "0 learnings entries for {}".format(iter_id)})

    # Emergent — WARN if 0 with actionable guidance
    e_count = artifacts.get("emergent", {}).get("count", 0)
    if e_count > 0:
        checks.append({"name": "emergent-entry", "status": "pass",
                        "detail": "{} emergent entries for {}".format(e_count, iter_id)})
    else:
        checks.append({"name": "emergent-entry", "status": "warn",
                        "detail": "0 emergent entries for {} — verify no design decisions, "
                        "requirement gaps, or assumptions were made. "
                        "If none, this is expected. If any were made, write them before "
                        "exiting.".format(iter_id)})

    return checks


def check_trace_events(plet_dir, iter_id, phase, attempt):
    """Check trace events file exists, is non-empty, and validates.

    Calls plet_trace.py validate if the file exists. WARN on any issue.
    """
    trace_dir = os.path.join(plet_dir, "trace")
    filename = "{}-{}-{}-events.ndjson".format(iter_id, phase, attempt)
    trace_file = os.path.join(trace_dir, filename)

    if not os.path.isfile(trace_file):
        return {"name": "trace-events", "status": "warn",
                "detail": "no trace events file for {} {}-{}".format(iter_id, phase, attempt)}

    size = os.path.getsize(trace_file)
    if size == 0:
        return {"name": "trace-events", "status": "warn",
                "detail": "trace events file empty for {} {}-{}".format(iter_id, phase, attempt)}

    # Run TRC validate
    data, result = run_tool("plet_trace.py", ["validate", trace_file])
    if result is not None and result.returncode != 0:
        return {"name": "trace-events", "status": "warn",
                "detail": "trace events file invalid for {} {}-{}".format(iter_id, phase, attempt)}

    return {"name": "trace-events", "status": "pass",
            "detail": "trace events file valid ({} bytes)".format(size)}


def check_lifecycle(iter_state, valid_states, phase_name):
    """Check lifecycle is appropriate for pre-gate.

    Args:
        iter_state: parsed iteration state dict
        valid_states: set of acceptable lifecycle values
        phase_name: human-readable phase name for error messages
    """
    lifecycle = iter_state.get("lifecycle", "unknown")
    if lifecycle in valid_states:
        return {"name": "lifecycle-check", "status": "pass",
                "detail": "lifecycle is {}".format(lifecycle)}
    expected = " or ".join(sorted(valid_states))
    return {"name": "lifecycle-check", "status": "warn",
            "detail": "lifecycle is {} (expected {})".format(lifecycle, expected)}


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

def summarize_checks(checks):
    """Compute summary counts and overall status.

    Returns (overall, counts, exit_code) where:
    - overall: "ok", "warn", or "fail"
    - counts: dict with total, passed, failed, warnings
    - exit_code: 0, 1, or 2
    """
    counts = {"total": len(checks), "passed": 0, "failed": 0, "warnings": 0}
    for c in checks:
        if c["status"] == "pass":
            counts["passed"] += 1
        elif c["status"] == "fail":
            counts["failed"] += 1
        elif c["status"] == "warn":
            counts["warnings"] += 1

    if counts["failed"] > 0:
        overall = "fail"
        exit_code = 1
    elif counts["warnings"] > 0:
        overall = "warn"
        exit_code = 2
    else:
        overall = "ok"
        exit_code = 0

    return overall, counts, exit_code


def format_text_output(command, checks, overall, counts):
    """Format check results as text lines."""
    lines = []
    # Title line
    if overall == "ok":
        title_detail = "{} passed".format(counts["passed"])
    elif overall == "fail":
        parts = []
        if counts["failed"] > 0:
            parts.append("{} failed".format(counts["failed"]))
        if counts["warnings"] > 0:
            parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
        title_detail = ", ".join(parts)
    else:
        title_detail = "{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else "")
    lines.append("{}: {} — {}".format(overall.upper(), command, title_detail))

    # Per-check lines
    for c in checks:
        lines.append("{}: {} — {}".format(c["status"].upper(), c["name"], c["detail"]))

    # Summary line
    parts = ["{} passed".format(counts["passed"]), "{} failed".format(counts["failed"])]
    parts.append("{} warning{}".format(counts["warnings"], "s" if counts["warnings"] != 1 else ""))
    lines.append("{} checks: {}".format(counts["total"], ", ".join(parts)))

    return "\n".join(lines)
