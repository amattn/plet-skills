#!/usr/bin/env python3
"""plet orchestrator — the main implement→verify loop as deterministic code.

Reads state, spawns subagents, processes results, manages git operations,
and loops until all iterations are complete, blocked, or a breakpoint is hit.
Returns structured NDJSON so SKILL.md knows why it stopped.

Usage:
    plet_orchestrator.py run <plet_dir> [--max-iterations N] [--allow-stale] [--output ndjson]

Commands:
    run     Execute the main implement→verify loop
"""

import json
import os
import subprocess
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import entries  # noqa: E402, I001
import fingerprint  # noqa: E402
import gate_session  # noqa: E402
import global_state  # noqa: E402
import iter_state  # noqa: E402
import schedule  # noqa: E402
import session  # noqa: E402
from util_cli import (  # noqa: E402
    dispatch,
    get_plet_dir,
    make_help_hint,
    parse_kwargs,
    validate_known_flags,
)
from util_io import (  # noqa: E402
    load_json,
    state_json_path,
)
from util_sink import FileSink, MultiplexSink, NdjsonSink, TextSink  # noqa: E402
from util_state import load_and_validate_iter_state  # noqa: E402
from util_subprocess import run_git  # noqa: E402

SCRIPT_VERSION = "0.6.0"
from util_constants import SKILL_VERSION  # noqa: E402

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


_help_hint = make_help_hint("plet_orchestrator")


# ---------------------------------------------------------------------------
# Subprocess launcher — only for invoke.py (launching Claude)
# ---------------------------------------------------------------------------


def _run_invoke_subprocess(args, cwd=None):
    """Run invoke.py via subprocess, return (stdout, stderr, exit_code).

    This is the ONLY subprocess call left — launching Claude is genuinely
    a subprocess (separate process with its own stdin/stdout).
    """
    script_path = os.path.join(SCRIPTS_DIR, "invoke.py")
    result = subprocess.run(
        [sys.executable, script_path, "--no-log"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


# Injectable launcher — override for testing
_run_invoke = _run_invoke_subprocess


# ---------------------------------------------------------------------------
# Direct-call helpers (replacing _run_script pattern)
# ---------------------------------------------------------------------------


def _call_cmd(cmd_func, args):
    """Call a module command function directly, return (exit_code, stdout, stderr).

    Captures stdout/stderr since cmd functions print to them.
    """
    import io

    old_out, old_err = sys.stdout, sys.stderr
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        result = cmd_func(args)
        out = sys.stdout.getvalue().strip()
        err = sys.stderr.getvalue().strip()
    finally:
        sys.stdout, sys.stderr = old_out, old_err

    if isinstance(result, tuple):
        rc, cmd_out, cmd_err = result
        # Tuple return: output is in the tuple, not stdout
        return rc, cmd_out or out, cmd_err or err
    elif isinstance(result, int):
        return result, out, err
    else:
        return 0, out, err


def _call_cmd_json(cmd_func, args):
    """Call a module command with --output json, return (parsed_dict, stderr, exit_code)."""
    rc, out, err = _call_cmd(cmd_func, args + ["--output", "json"])
    if rc != 0:
        return None, err, rc
    try:
        return json.loads(out), err, rc
    except json.JSONDecodeError:
        return None, "Failed to parse JSON: " + out[:200], rc


def _update_lifecycle(global_plet_dir, iter_id, lifecycle_val):
    """Update lifecycle in state.json via global_state module (SF_28)."""
    _call_cmd(
        global_state.cmd_update_lifecycle,
        [global_plet_dir, "--iter-id", iter_id, "--lifecycle", lifecycle_val],
    )


def _promote_eligible(global_plet_dir, sink):
    """Promote ineligible → queued for iterations whose deps are all complete.

    Reads state.json, checks each ineligible iteration's dependencies,
    and promotes to queued if all deps are complete. This must run before
    each eligible() check so newly-satisfied iterations are picked up.
    """
    gs_path = state_json_path(global_plet_dir)
    state = load_json(gs_path)
    if state is None:
        return

    dep_map = state.get("dependencyMap", {})
    lifecycles = state.get("lifecycles", {})
    promoted = []

    for iter_id, deps in dep_map.items():
        if lifecycles.get(iter_id) != "ineligible":
            continue
        if not deps:
            promoted.append(iter_id)
            continue
        if all(lifecycles.get(dep) == "complete" for dep in deps):
            promoted.append(iter_id)

    for iter_id in sorted(promoted):
        _update_lifecycle(global_plet_dir, iter_id, "queued")
        sink.event(
            {"type": "dependency_promotion", "iterationId": iter_id, "from": "ineligible", "to": "queued"},
        )


def _make_result(
    reason, counts, session_number=0, branch="", completed=0, pause_context=None, error=None, stuck_iterations=None
):
    """Build a result event dict."""
    remaining = sum(counts.get(k, 0) for k in ("queued", "implementing", "verifying", "ineligible"))
    result = {
        "type": "result",
        "status": "error" if reason == "error" else "ok",
        "command": "run",
        "reason": reason,
        "sessionType": "loop",
        "sessionNumber": session_number,
        "branch": branch,
        "iterationsCompleted": completed,
        "iterationsBlocked": counts.get("blocked", 0),
        "iterationsRemaining": remaining,
        "counts": counts,
        "pauseContext": pause_context or ({"iterationId": None, "phase": None, "error": error} if error else None),
        "scriptVersion": SCRIPT_VERSION,
    }
    if stuck_iterations:
        result["stuckIterations"] = stuck_iterations
    return result


# ---------------------------------------------------------------------------
# run helpers
# ---------------------------------------------------------------------------


def _handle_verify_verdict(
    verdict,
    iter_id,
    global_plet_dir,
    sink,
    completed_this_run,
    counts,
):
    """Process the verify verdict and update lifecycle. Returns (new_completed, blocked)."""
    if verdict is None:
        sink.text("  Verify did not set verifyVerdict — blocking")
        _update_lifecycle(global_plet_dir, iter_id, "blocked")
        return completed_this_run, True
    elif verdict == "passed":
        return _handle_passed_verdict(iter_id, global_plet_dir, sink, completed_this_run, counts)
    elif verdict == "rejected":
        return _handle_rejected_verdict(
            iter_id,
            global_plet_dir,
            sink,
            completed_this_run,
            counts,
        )
    elif verdict == "blocked":
        _update_lifecycle(global_plet_dir, iter_id, "blocked")
        sink.event({"type": "iteration_complete", "iterationId": iter_id, "lifecycle": "blocked"})
        return completed_this_run, True
    return completed_this_run, False


def _handle_passed_verdict(iter_id, global_plet_dir, sink, completed_this_run, counts):
    """Handle a passed verify verdict. Returns (new_completed, blocked).

    Sequential mode: iteration commits are already on the workstream branch.
    No rebase-commit needed — just mark complete and commit state.
    """
    _update_lifecycle(global_plet_dir, iter_id, "complete")
    completed_this_run += 1
    sink.event({"type": "iteration_complete", "iterationId": iter_id, "lifecycle": "complete"})
    sink.text(f"[{completed_this_run}] {iter_id}: passed")
    return completed_this_run, False


def _decrement_remaining_retries(plet_dir, iter_id):
    """Decrement remainingRetries in state.json (global state, orchestrator-owned).

    Used for verify rejection budget — prevents infinite retry loops.
    """
    gs_path = state_json_path(plet_dir)
    try:
        with open(gs_path) as f:
            data = json.load(f)
        retries = data.get("remainingRetries", {})
        current = retries.get(iter_id, 3)
        retries[iter_id] = max(0, current - 1)
        data["remainingRetries"] = retries
        with open(gs_path + ".tmp", "w") as f:
            json.dump(data, f, indent=2)
            f.write("\n")
        os.rename(gs_path + ".tmp", gs_path)
    except (OSError, json.JSONDecodeError):
        pass  # Best-effort


def _handle_rejected_verdict(iter_id, global_plet_dir, sink, completed_this_run, counts):
    """Handle a rejected verify verdict: decrement remainingRetries, check retry. Returns (new_completed, blocked)."""
    _decrement_remaining_retries(global_plet_dir, iter_id)
    retry_data, _, _ = _call_cmd_json(schedule.cmd_check_retry, [global_plet_dir, "--iter-id", iter_id])
    decision = retry_data.get("decision", "abort") if retry_data else "abort"
    if decision == "continue" or decision == "first":
        _update_lifecycle(global_plet_dir, iter_id, "queued")
        sink.event({"type": "iteration_complete", "iterationId": iter_id, "lifecycle": "queued"})
        sink.text(f"[{completed_this_run + 1}] {iter_id}: rejected, retry queued")
    else:
        _update_lifecycle(global_plet_dir, iter_id, "blocked")
        sink.event({"type": "iteration_complete", "iterationId": iter_id, "lifecycle": "blocked"})
        sink.text(
            f"[{completed_this_run + 1}] {iter_id}: rejected, retry exhausted — blocked",
        )
    return completed_this_run, False


def _setup_session(global_plet_dir, counts, allow_stale, sink):
    """Run preflight, fingerprint check, and start session. Returns (session_number, branch, error_code).
    error_code is None on success."""
    # Validate state.json before anything else — if corrupt, nothing works
    val_rc, _, val_err = _call_cmd(global_state.cmd_validate, [global_plet_dir])
    if val_rc != 0:
        msg = f"state.json validation failed: {val_err[:200]}"
        print(f"Error: {msg}", file=sys.stderr)
        result = _make_result("error", counts, error=msg)
        sink.event(result)
        return 0, "", 1

    sink.text("Running preflight...")
    pf_rc, _, pf_err = _call_cmd(gate_session.cmd_preflight, [global_plet_dir, "--session-type", "loop"])
    if pf_rc == 1:
        print(f"Error: preflight failed: {pf_err}", file=sys.stderr)
        result = _make_result("error", counts, error="preflight failed")
        sink.event(result)
        return 0, "", 1

    fp_data, fp_err, fp_rc = _call_cmd_json(fingerprint.cmd_check, [global_plet_dir, "--level", "all"])
    is_stale = fp_rc != 0 or (fp_data and not fp_data.get("allConsistent", True))
    if is_stale:
        if not allow_stale:
            msg = "Fingerprints stale. Use --allow-stale to override."
            print(f"Error: {msg}", file=sys.stderr)
            result = _make_result("error", counts, error=msg)
            sink.event(result)
            return 0, "", 1
        sink.text("Warning: fingerprints stale (--allow-stale)")

    session_data, ss_err, ss_rc = _call_cmd_json(session.cmd_start_session, [global_plet_dir, "--type", "loop"])
    if ss_rc != 0 or session_data is None:
        print(f"Error: start-session failed: {ss_err}", file=sys.stderr)
        return 0, "", 1

    session_number = session_data.get("sessionNumber", 0)
    branch = session_data.get("branch", "")
    resumed = session_data.get("resumed", False)

    sink.event(
        {
            "type": "session_start",
            "sessionType": "loop",
            "sessionNumber": session_number,
            "branch": branch,
            "resumed": resumed,
        },
    )
    sink.text("Loop {} {} on {}".format(session_number, "resumed" if resumed else "started", branch))

    if not resumed:
        run_git("checkout", "-b", branch)
    else:
        run_git("checkout", branch)

    # Commit state.json with updated loopSessionCount + session history
    run_git("add", "-A")
    run_git("commit", "-m", f"plet: [loop{session_number}] session start", "--allow-empty")

    _call_cmd(
        entries.cmd_add_progress,
        [
            global_plet_dir,
            "--iter-id",
            "SESSION",
            "--iter-title",
            "Orchestrator",
            "--phase",
            "orchestrator",
            "--attempt",
            "1",
            "--status",
            "IN_PROGRESS",
            "--content",
            f"Loop {session_number} active. Branch: {branch}.",
        ],
    )

    return session_number, branch, None


def _end_session(global_plet_dir, session_number, completed_this_run, counts, stuck, branch, sink):
    """Run postflight, end session, emit final result."""
    _call_cmd(gate_session.cmd_postflight, [global_plet_dir, "--session-type", "loop"])
    _call_cmd(session.cmd_end_session, [global_plet_dir])

    _call_cmd(
        entries.cmd_add_progress,
        [
            global_plet_dir,
            "--iter-id",
            "SESSION",
            "--iter-title",
            "Orchestrator",
            "--phase",
            "orchestrator",
            "--attempt",
            "1",
            "--status",
            "COMPLETE",
            "--content",
            "Loop {} complete. {} iterations completed, {} blocked.".format(
                session_number, completed_this_run, counts.get("blocked", 0)
            ),
        ],
    )

    # Re-read final counts
    eligible_data, _, _ = _call_cmd_json(schedule.cmd_eligible, [global_plet_dir])
    if eligible_data:
        counts = eligible_data.get("counts", counts)
        stuck = eligible_data.get("stuckIterations", [])

    all_complete = counts.get("complete", 0) + counts.get("withdrawn", 0)
    total = sum(counts.get(k, 0) for k in counts if k != "eligible")
    reason = "all_complete" if all_complete == total else "all_blocked_or_complete"

    # Commit end-session state (lifecycle updates, session endedAt, progress entry)
    run_git("add", "-A")
    run_git("commit", "-m", f"plet: [loop{session_number}] session end", "--allow-empty")

    result = _make_result(
        reason,
        counts,
        session_number=session_number,
        branch=branch,
        completed=completed_this_run,
        stuck_iterations=stuck,
    )
    sink.event(result)
    sink.text(
        "Loop {} complete: {} iterations, {} blocked".format(
            session_number, completed_this_run, counts.get("blocked", 0)
        ),
    )


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------


def _parse_run_args(args):
    """Parse and validate args for cmd_run.

    Returns (plet_dir, output_ndjson, allow_stale, max_iterations) on success,
    or None on error (messages already printed).
    """
    help_text = cmd_run.__doc__
    if "-h" in args or "--help" in args:
        print(help_text)
        return "help"

    plet_dir, remaining, dir_err = get_plet_dir(args)
    if plet_dir is None:
        return None

    try:
        kwargs = parse_kwargs(remaining)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        print(_help_hint("run"), file=sys.stderr)
        return None

    # Custom flag set — output is "ndjson" not "json", no pretty, no fields
    known = {"max_iterations", "allow_stale", "output"}
    err = validate_known_flags(kwargs, known, _help_hint("run"))
    if err:
        return None

    output_ndjson = kwargs.get("output") == "ndjson"
    allow_stale = "allow_stale" in kwargs
    max_iterations = None
    if "max_iterations" in kwargs:
        try:
            max_iterations = int(kwargs["max_iterations"])
            if max_iterations < 1:
                raise ValueError()
        except (ValueError, TypeError):
            print("Error: --max-iterations must be a positive integer", file=sys.stderr)
            print(_help_hint("run"), file=sys.stderr)
            return None

    return plet_dir, output_ndjson, allow_stale, max_iterations


def _check_nothing_to_do(eligible_ids, counts, stuck, sink):
    """Check if there's nothing to do. Returns exit code or None to continue."""
    in_progress = counts.get("implementing", 0) + counts.get("verifying", 0)
    if eligible_ids or in_progress > 0:
        return None
    all_complete = counts.get("complete", 0) + counts.get("withdrawn", 0)
    total = sum(counts.get(k, 0) for k in counts if k != "eligible")
    reason = "all_complete" if all_complete == total else "all_blocked_or_complete"
    result = _make_result(reason, counts, stuck_iterations=stuck)
    sink.event(result)
    sink.text(
        "Nothing to do: {} ({} complete, {} blocked)".format(
            reason, counts.get("complete", 0), counts.get("blocked", 0)
        ),
    )
    return 0


def _run_implement_phase(iter_id, global_plet_dir, sink, completed_this_run):
    """Run implement phase in project root (no worktree). Returns implement_verdict or None."""
    _update_lifecycle(global_plet_dir, iter_id, "implementing")
    _call_cmd(
        iter_state.cmd_start_phase,
        [global_plet_dir, "--iter-id", iter_id, "--phase", "implement"],
    )

    impl_out, impl_err, impl_rc = _run_invoke(
        ["run", global_plet_dir, "--iter-id", iter_id, "--phase", "implement", "--cwd", "."],
    )

    if impl_rc != 0:
        sink.text(f"  Invoke implement failed (rc={impl_rc}): {impl_err[:200]}")
        sink.event({"type": "error", "iterationId": iter_id, "phase": "implement", "error": impl_err[:200]})

    sink.event({"type": "iteration_phase_complete", "iterationId": iter_id, "phase": "implement"})

    ist = load_and_validate_iter_state(global_plet_dir, iter_id)
    if isinstance(ist, tuple):
        return None
    return ist.get("implementVerdict")


def _run_verify_phase(iter_id, global_plet_dir, sink, completed_this_run):
    """Run verify phase in project root (no worktree). Returns verdict string or None."""
    _update_lifecycle(global_plet_dir, iter_id, "verifying")
    _call_cmd(
        iter_state.cmd_start_phase,
        [global_plet_dir, "--iter-id", iter_id, "--phase", "verify"],
    )
    sink.event({"type": "iteration_start", "iterationId": iter_id, "phase": "verify"})
    sink.text(f"[{completed_this_run + 1}] {iter_id}: verifying...")

    _run_invoke(
        ["run", global_plet_dir, "--iter-id", iter_id, "--phase", "verify", "--cwd", "."],
    )
    sink.event({"type": "iteration_phase_complete", "iterationId": iter_id, "phase": "verify"})

    ist = load_and_validate_iter_state(global_plet_dir, iter_id)
    if isinstance(ist, tuple):
        return None
    verdict = ist.get("verifyVerdict")

    return verdict


def _run_iteration(iter_id, global_plet_dir, sink, completed_this_run, counts):
    """Run implement+verify for one iteration sequentially on the workstream.

    Returns (new_completed, was_blocked).
    """
    sink.event({"type": "iteration_start", "iterationId": iter_id, "phase": "implement"})
    sink.text(f"[{completed_this_run + 1}] {iter_id}: implementing...")

    # Implement
    implement_verdict = _run_implement_phase(iter_id, global_plet_dir, sink, completed_this_run)
    if implement_verdict is None:
        sink.text("  Implement did not set implementVerdict — blocking")
        _update_lifecycle(global_plet_dir, iter_id, "blocked")
        return completed_this_run, True

    # Verify
    verdict = _run_verify_phase(iter_id, global_plet_dir, sink, completed_this_run)

    # Handle verdict
    return _handle_verify_verdict(verdict, iter_id, global_plet_dir, sink, completed_this_run, counts)


def _get_next_eligible(global_plet_dir, sink, failed_ids, max_iterations, completed):
    """Get the next eligible iteration to run. Returns iter_id or None.

    Promotes ineligible → queued, checks eligible, filters out already-failed,
    respects max-iterations budget. Returns at most one iteration (sequential).
    """
    _promote_eligible(global_plet_dir, sink)

    eligible_data, _, rc = _call_cmd_json(schedule.cmd_eligible, [global_plet_dir])
    if rc != 0 or eligible_data is None:
        return None
    eligible_ids = eligible_data.get("eligible", [])

    actionable = [i for i in eligible_ids if i not in failed_ids]
    if not actionable:
        return None

    # Respect max-iterations budget
    if max_iterations:
        budget = max_iterations - completed
        if budget <= 0:
            return None

    return actionable[0]


def _check_breakpoint_before(iter_id, global_plet_dir, sink):
    """Check breakpoint-before for one iteration. Returns True if hit."""
    bp_data, _, _ = _call_cmd_json(
        schedule.cmd_check_breakpoints,
        [global_plet_dir, "--iter-id", iter_id, "--position", "before"],
    )
    if bp_data and bp_data.get("result") == "hit":
        sink.event({"type": "breakpoint_hit", "iterationId": iter_id, "position": "before"})
        return True
    return False


def _check_breakpoint_after(iter_id, global_plet_dir, sink):
    """Check breakpoint-after for one iteration. Returns True if hit."""
    bp_data, _, _ = _call_cmd_json(
        schedule.cmd_check_breakpoints,
        [global_plet_dir, "--iter-id", iter_id, "--position", "after"],
    )
    if bp_data and bp_data.get("result") == "hit":
        sink.event({"type": "breakpoint_hit", "iterationId": iter_id, "position": "after"})
        return True
    return False


def _run_sequential_loop(
    global_plet_dir,
    sink,
    max_iterations,
    session_number,
    branch,
    counts,
):
    """Sequential loop: run one iteration at a time until done or paused.

    Returns (completed_count, reason, counts, pause_context).
    """
    completed = 0
    failed_ids = set()
    pause_context = None
    reason = "all_complete"

    while True:
        iter_id = _get_next_eligible(global_plet_dir, sink, failed_ids, max_iterations, completed)
        if iter_id is None:
            break

        # Check breakpoint-before
        if _check_breakpoint_before(iter_id, global_plet_dir, sink):
            pause_context = {"iterationId": iter_id, "phase": None, "error": None}
            reason = "breakpoint_before"
            break

        # Run implement + verify
        completed, was_blocked = _run_iteration(iter_id, global_plet_dir, sink, completed, counts)
        if was_blocked:
            failed_ids.add(iter_id)

        # Check breakpoint-after
        if _check_breakpoint_after(iter_id, global_plet_dir, sink):
            pause_context = {"iterationId": iter_id, "phase": None, "error": None}
            reason = "breakpoint_after"
            break

        # Check max-iterations
        if max_iterations and completed >= max_iterations:
            reason = "max_iterations_reached"
            sink.text(f"Paused: max iterations reached ({completed}/{max_iterations})")
            break

    # Determine final reason if not paused
    if pause_context is None and reason == "all_complete":
        eligible_data, _, _ = _call_cmd_json(schedule.cmd_eligible, [global_plet_dir])
        if eligible_data:
            counts = eligible_data.get("counts", counts)
        all_done = counts.get("complete", 0) + counts.get("withdrawn", 0)
        total = sum(counts.get(k, 0) for k in counts if k != "eligible")
        reason = "all_complete" if all_done == total else "all_blocked_or_complete"

    return completed, reason, counts, pause_context


def cmd_run(args):
    """Execute the main implement→verify loop.

    IMPORTANT: This is the capstone — a systematic, methodical implementation
    of the loop phase that minimizes agent drift. Every step is deterministic
    code, not prose-interpreted instructions.

    USAGE
        plet_orchestrator.py run <plet_dir> [--max-iterations N] [--allow-stale] [--output ndjson]

    EXAMPLES
        plet_orchestrator.py run plet/
        plet_orchestrator.py run plet/ --output ndjson
        plet_orchestrator.py run plet/ --max-iterations 1

    PURPOSE
        Called by SKILL.md when phase is 'loop'. Manages session lifecycle,
        spawns subagents, processes verdicts, handles retry and merge.
        Returns structured output so SKILL.md knows why it stopped.
    """
    parsed = _parse_run_args(args)
    if parsed == "help":
        return 0
    if parsed is None:
        return 1
    plet_dir, output_ndjson, allow_stale, max_iterations = parsed

    user_sink = NdjsonSink() if output_ndjson else TextSink()

    # Orchestrator trace file — persists all events for post-run analysis
    trace_dir = os.path.join(plet_dir, "trace")
    os.makedirs(trace_dir, exist_ok=True)
    trace_path = os.path.join(trace_dir, "orchestrator.ndjson")
    sink = MultiplexSink(user_sink, FileSink(trace_path))

    # -------------------------------------------------------------------
    # Phase 0: Load state and pre-check
    # -------------------------------------------------------------------

    gs_path = state_json_path(plet_dir)
    global_state_data = load_json(gs_path)
    if global_state_data is None:
        print(f"Error: state.json not found at {gs_path}", file=sys.stderr)
        print(_help_hint("run"), file=sys.stderr)
        return 1

    global_state_data.get("projectId", "UNKNOWN")

    # Change to project root (parent of plet_dir) — all git ops run from here
    project_root = os.path.dirname(os.path.abspath(plet_dir))
    os.chdir(project_root)
    # Rename to global_plet_dir — this is the workstream/scheduling copy (SF_26)
    global_plet_dir = os.path.basename(os.path.abspath(plet_dir)) or "plet"

    # Pre-check: anything to do? (before starting session)
    eligible_data, err, rc = _call_cmd_json(schedule.cmd_eligible, [global_plet_dir])
    if rc != 0 or eligible_data is None:
        print(f"Error: eligible check failed: {err}", file=sys.stderr)
        return 1

    counts = eligible_data.get("counts", {})
    eligible_ids = eligible_data.get("eligible", [])
    stuck = eligible_data.get("stuckIterations", [])

    early_exit = _check_nothing_to_do(eligible_ids, counts, stuck, sink)
    if early_exit is not None:
        return early_exit

    # -------------------------------------------------------------------
    # Phase 1: Session setup
    # -------------------------------------------------------------------

    session_number, branch, err_code = _setup_session(global_plet_dir, counts, allow_stale, sink)
    if err_code is not None:
        return err_code

    # -------------------------------------------------------------------
    # Phase 2: Sequential iteration loop
    # -------------------------------------------------------------------

    completed_this_run, reason, counts, pause_context = _run_sequential_loop(
        global_plet_dir,
        sink,
        max_iterations,
        session_number,
        branch,
        counts,
    )

    # Emit result event
    stuck_data, _, _ = _call_cmd_json(schedule.cmd_eligible, [global_plet_dir])
    stuck = stuck_data.get("stuckIterations", []) if stuck_data else []
    if stuck_data:
        counts = stuck_data.get("counts", counts)

    result = _make_result(
        reason,
        counts,
        session_number=session_number,
        branch=branch,
        completed=completed_this_run,
        pause_context=pause_context,
        stuck_iterations=stuck,
    )
    sink.event(result)

    if reason in ("breakpoint_before", "breakpoint_after", "max_iterations_reached"):
        # Session stays open for resume
        return 0

    # -------------------------------------------------------------------
    # Phase 3: Session end
    # -------------------------------------------------------------------

    _end_session(global_plet_dir, session_number, completed_this_run, counts, stuck, branch, sink)
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "run": cmd_run,
    }
    return dispatch(commands, "plet_orchestrator", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
