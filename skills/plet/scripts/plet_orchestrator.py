#!/usr/bin/env python3
"""plet orchestrator — the main implement→verify loop as deterministic code.

Reads state, spawns subagents, processes results, manages git operations,
and loops until all iterations are complete, blocked, or a breakpoint is hit.
Returns structured NDJSON so SKILL.md knows why it stopped.

Usage:
    plet_orchestrator.py run <plet_dir> [--max-iterations N] [--sequential] [--allow-stale] [--output ndjson]

Commands:
    run     Execute the main implement→verify loop
"""

import json
import os
import subprocess
import sys
import time

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    get_plet_dir,
    now_iso,
    parse_kwargs,
    validate_known_flags,
    UNIVERSAL_FLAGS_READ,
)
from util_io import (
    load_json,
    state_json_path,
    iter_state_path,
    derive_worktree_plet_dir,
)
from util_state import load_and_validate_iter_state, load_and_validate_global_state

SCRIPT_VERSION = "0.2.0"
from util_constants import SKILL_VERSION  # noqa: E402

SCRIPTS_DIR = os.path.dirname(os.path.abspath(__file__))


def _help_hint(command):
    return "Run: plet_orchestrator.py {} --help".format(command)


def _run_script(script_name, args, cwd=None):
    """Run a plet script via subprocess, return (stdout, stderr, exit_code)."""
    script_path = os.path.join(SCRIPTS_DIR, script_name)
    result = subprocess.run(
        [sys.executable, script_path, "--no-log"] + args,
        capture_output=True, text=True, cwd=cwd,
    )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def _run_script_json(script_name, args, cwd=None):
    """Run a plet script with --output json, return parsed dict or None."""
    stdout, stderr, rc = _run_script(script_name, args + ["--output", "json"], cwd=cwd)
    if rc != 0:
        return None, stderr, rc
    try:
        return json.loads(stdout), stderr, rc
    except json.JSONDecodeError:
        return None, "Failed to parse JSON: " + stdout[:200], rc


def _update_lifecycle(global_plet_dir, iter_id, lifecycle):
    """Update lifecycle in state.json via plet_global_state.py (SF_28)."""
    _run_script("plet_global_state.py", [
        "update-lifecycle", global_plet_dir,
        "--iter-id", iter_id, "--lifecycle", lifecycle,
    ])


def _promote_eligible(global_plet_dir, output_ndjson):
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
            # No deps but ineligible — shouldn't happen, but promote anyway
            promoted.append(iter_id)
            continue
        if all(lifecycles.get(dep) == "complete" for dep in deps):
            promoted.append(iter_id)

    for iter_id in sorted(promoted):
        _update_lifecycle(global_plet_dir, iter_id, "queued")
        _emit_event({"type": "dependency_promotion",
                     "iterationId": iter_id,
                     "from": "ineligible", "to": "queued"}, output_ndjson)


def _emit_event(event, output_ndjson):
    """Emit an NDJSON event line if in ndjson mode."""
    if output_ndjson:
        event["timestamp"] = now_iso()
        print(json.dumps(event, separators=(",", ":")))
        sys.stdout.flush()


def _make_result(reason, counts, session_number=0, branch="", completed=0,
                 pause_context=None, error=None, stuck_iterations=None):
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


def _emit_text(msg, output_ndjson):
    """Emit text if NOT in ndjson mode."""
    if not output_ndjson:
        print(msg)
        sys.stdout.flush()


# ---------------------------------------------------------------------------
# run
# ---------------------------------------------------------------------------

def cmd_run(args):
    """Execute the main implement→verify loop.

    IMPORTANT: This is the capstone — a systematic, methodical implementation
    of the loop phase that minimizes agent drift. Every step is deterministic
    code, not prose-interpreted instructions.

    USAGE
        plet_orchestrator.py run <plet_dir> [--max-iterations N] [--sequential] [--allow-stale] [--output ndjson]

    EXAMPLES
        plet_orchestrator.py run plet/
        plet_orchestrator.py run plet/ --output ndjson
        plet_orchestrator.py run plet/ --max-iterations 1 --sequential

    PURPOSE
        Called by SKILL.md when phase is 'loop'. Manages session lifecycle,
        spawns subagents, processes verdicts, handles retry and merge.
        Returns structured output so SKILL.md knows why it stopped.
    """
    HELP = cmd_run.__doc__
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    plet_dir, remaining = get_plet_dir(args)
    if plet_dir is None:
        return 1
    kwargs = parse_kwargs(remaining)

    # Custom flag set — output is "ndjson" not "json", no pretty, no fields
    known = {"max_iterations", "sequential", "allow_stale", "output"}
    if not validate_known_flags(kwargs, known, _help_hint("run")):
        return 1

    output_ndjson = kwargs.get("output") == "ndjson"
    sequential = "sequential" in kwargs
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
            return 1

    # -------------------------------------------------------------------
    # Phase 0: Load state and pre-check
    # -------------------------------------------------------------------

    gs_path = state_json_path(plet_dir)
    global_state = load_json(gs_path)
    if global_state is None:
        print("Error: state.json not found at {}".format(gs_path), file=sys.stderr)
        print(_help_hint("run"), file=sys.stderr)
        return 1

    project_id = global_state.get("projectId", "UNKNOWN")

    # Change to project root (parent of plet_dir) — all git ops run from here
    project_root = os.path.dirname(os.path.abspath(plet_dir))
    os.chdir(project_root)
    # Rename to global_plet_dir — this is the workstream/scheduling copy (SF_26)
    global_plet_dir = os.path.basename(os.path.abspath(plet_dir)) or "plet"

    # Pre-check: anything to do? (before starting session)
    eligible_data, err, rc = _run_script_json("plet_schedule.py", ["eligible", global_plet_dir])
    if rc != 0 or eligible_data is None:
        print("Error: eligible check failed: {}".format(err), file=sys.stderr)
        return 1

    counts = eligible_data.get("counts", {})
    eligible_ids = eligible_data.get("eligible", [])
    stuck = eligible_data.get("stuckIterations", [])

    # Nothing to do?
    in_progress = counts.get("implementing", 0) + counts.get("verifying", 0)
    if not eligible_ids and in_progress == 0:
        all_complete = counts.get("complete", 0) + counts.get("withdrawn", 0)
        total = sum(counts.get(k, 0) for k in counts if k != "eligible")
        reason = "all_complete" if all_complete == total else "all_blocked_or_complete"

        result = _make_result(reason, counts, stuck_iterations=stuck)
        _emit_event(result, output_ndjson)
        if not output_ndjson:
            _emit_text("Nothing to do: {} ({} complete, {} blocked)".format(
                reason, counts.get("complete", 0), counts.get("blocked", 0)),
                output_ndjson)
        return 0

    # -------------------------------------------------------------------
    # Phase 1: Session setup
    # -------------------------------------------------------------------

    # Preflight
    _emit_text("Running preflight...", output_ndjson)
    _, pf_err, pf_rc = _run_script("plet_gate_session.py", ["preflight", global_plet_dir,
                                    "--session-type", "loop"])
    if pf_rc == 1:
        print("Error: preflight failed: {}".format(pf_err), file=sys.stderr)
        result = _make_result("error", counts, error="preflight failed")
        _emit_event(result, output_ndjson)
        return 1

    # Fingerprint check
    fp_data, fp_err, fp_rc = _run_script_json("plet_fingerprint.py", ["check", global_plet_dir, "--level", "all"])
    is_stale = fp_rc != 0 or (fp_data and not fp_data.get("allConsistent", True))
    if is_stale:
        if not allow_stale:
            detail = ""
            if fp_data:
                detail = fp_data.get("levels", {})
            msg = "Fingerprints stale. Use --allow-stale to override."
            print("Error: {}".format(msg), file=sys.stderr)
            result = _make_result("error", counts, error=msg)
            _emit_event(result, output_ndjson)
            return 1
        _emit_text("Warning: fingerprints stale (--allow-stale)", output_ndjson)

    # Start session
    session_data, ss_err, ss_rc = _run_script_json("plet_session.py",
                                                    ["start-session", global_plet_dir, "--type", "loop"])
    if ss_rc != 0 or session_data is None:
        print("Error: start-session failed: {}".format(ss_err), file=sys.stderr)
        return 1

    session_number = session_data.get("sessionNumber", 0)
    branch = session_data.get("branch", "")
    resumed = session_data.get("resumed", False)

    _emit_event({
        "type": "session_start",
        "sessionType": "loop",
        "sessionNumber": session_number,
        "branch": branch,
        "resumed": resumed,
    }, output_ndjson)
    _emit_text("Loop {} {} on {}".format(
        session_number, "resumed" if resumed else "started", branch), output_ndjson)

    # Create workstream branch if needed
    if not resumed:
        subprocess.run(["git", "checkout", "-b", branch], capture_output=True)
    else:
        subprocess.run(["git", "checkout", branch], capture_output=True)

    # Write ACTIVE canary
    _run_script("plet_entries.py", ["add-progress", global_plet_dir,
                "--iter-id", "SESSION", "--iter-title", "Orchestrator",
                "--phase", "orchestrator", "--attempt", "1",
                "--status", "IN_PROGRESS",
                "--content", "Loop {} active. Branch: {}.".format(session_number, branch)])

    # -------------------------------------------------------------------
    # Phase 2: Iteration loop
    # -------------------------------------------------------------------

    completed_this_run = 0
    failed_this_round = set()  # guard against infinite retry of same iteration
    max_rounds = 100  # safety limit

    for _round in range(max_rounds):
        # Promote ineligible → queued where deps are satisfied
        _promote_eligible(global_plet_dir, output_ndjson)

        # Re-evaluate eligible
        eligible_data, _, rc = _run_script_json("plet_schedule.py", ["eligible", global_plet_dir])
        if rc != 0 or eligible_data is None:
            break
        eligible_ids = eligible_data.get("eligible", [])
        counts = eligible_data.get("counts", {})
        stuck = eligible_data.get("stuckIterations", [])

        _emit_event({
            "type": "orchestrator_eligible_round",
            "eligible": eligible_ids,
            "stuckIterations": stuck,
            "counts": counts,
        }, output_ndjson)

        in_progress = counts.get("implementing", 0) + counts.get("verifying", 0)
        if not eligible_ids and in_progress == 0:
            break

        if not eligible_ids:
            # Nothing new to start, but something is in progress
            # (shouldn't happen in this sequential model — break for now)
            break

        # Filter out iterations that already failed this round (prevent infinite loop)
        actionable = [i for i in eligible_ids if i not in failed_this_round]
        if not actionable:
            break  # all eligible iterations failed — exit loop

        # Process iterations (sequential for now, parallel is future)
        for iter_id in actionable:
            # Breakpoint before
            bp_data, _, _ = _run_script_json("plet_schedule.py",
                ["check-breakpoints", global_plet_dir, "--iter-id", iter_id, "--position", "before"])
            if bp_data and bp_data.get("result") == "hit":
                _emit_event({"type": "breakpoint_hit", "iterationId": iter_id,
                             "position": "before"}, output_ndjson)
                result = _make_result("breakpoint_before", counts,
                    session_number=session_number, branch=branch,
                    completed=completed_this_run,
                    pause_context={"iterationId": iter_id, "phase": None, "error": None})
                _emit_event(result, output_ndjson)
                # Don't end session on breakpoint — leave active for resume
                return 0

            _emit_event({"type": "iteration_start", "iterationId": iter_id,
                         "phase": "implement"}, output_ndjson)
            _emit_text("[{}] {}: implementing...".format(
                completed_this_run + 1, iter_id), output_ndjson)

            # Create worktree
            wt_data, wt_err, wt_rc = _run_script_json("plet_git_iteration.py",
                ["worktree-create", global_plet_dir, "--iter-id", iter_id])

            if wt_rc != 0 or wt_data is None:
                _emit_text("  Error creating worktree: {}".format(wt_err), output_ndjson)
                _update_lifecycle(global_plet_dir, iter_id, "blocked")
                failed_this_round.add(iter_id)
                continue

            worktree_path = os.path.abspath(wt_data.get("worktreePath", ""))
            worktree_plet_dir = derive_worktree_plet_dir(worktree_path, global_plet_dir)

            # IMPLEMENT — orchestrator owns lifecycle (SF_28)
            _update_lifecycle(global_plet_dir, iter_id, "implementing")

            impl_out, impl_err, impl_rc = _run_script("plet_invoke.py", ["run", global_plet_dir,
                "--iter-id", iter_id, "--phase", "implement",
                "--cwd", worktree_path])

            if impl_rc != 0:
                _emit_text("  Invoke implement failed (rc={}): {}".format(
                    impl_rc, impl_err[:200]), output_ndjson)
                _emit_event({"type": "error", "iterationId": iter_id,
                             "phase": "implement", "error": impl_err[:200]}, output_ndjson)

            _emit_event({"type": "iteration_phase_complete", "iterationId": iter_id,
                         "phase": "implement"}, output_ndjson)

            # Guard assertion: worktree_plet_dir != global_plet_dir (prevents Run 3 bug)
            assert worktree_plet_dir != global_plet_dir, \
                "worktree_plet_dir must differ from global_plet_dir"

            # Check implementVerdict from WORKTREE (SF_28 — subagent sets it)
            iter_state = load_and_validate_iter_state(worktree_plet_dir, iter_id)
            implement_verdict = iter_state.get("implementVerdict") if iter_state else None
            if implement_verdict is None:
                _emit_text("  Implement did not set implementVerdict — blocking", output_ndjson)
                _update_lifecycle(global_plet_dir, iter_id, "blocked")
                _run_script("plet_git_iteration.py", ["worktree-remove", global_plet_dir,
                    "--iter-id", iter_id])
                failed_this_round.add(iter_id)
                continue

            # VERIFY — orchestrator sets verifying before spawn (SF_28)
            _update_lifecycle(global_plet_dir, iter_id, "verifying")

            _emit_event({"type": "iteration_start", "iterationId": iter_id,
                         "phase": "verify"}, output_ndjson)
            _emit_text("[{}] {}: verifying...".format(
                completed_this_run + 1, iter_id), output_ndjson)

            _run_script("plet_invoke.py", ["run", global_plet_dir,
                "--iter-id", iter_id, "--phase", "verify",
                "--cwd", worktree_path])

            _emit_event({"type": "iteration_phase_complete", "iterationId": iter_id,
                         "phase": "verify"}, output_ndjson)

            # Guard assertion (repeated before verify verdict read)
            assert worktree_plet_dir != global_plet_dir, \
                "worktree_plet_dir must differ from global_plet_dir"

            # Read verifyVerdict from WORKTREE (SF_28 — was lastVerdict)
            iter_state = load_and_validate_iter_state(worktree_plet_dir, iter_id)
            verdict = iter_state.get("verifyVerdict") if iter_state else None

            if verdict is None:
                _emit_text("  Verify did not set verifyVerdict — blocking", output_ndjson)
                _update_lifecycle(global_plet_dir, iter_id, "blocked")
            elif verdict == "passed":
                # Merge-squash to workstream
                # SF_28 simplification: no per-iteration state file revert needed.
                # Orchestrator never writes to per-iteration files on workstream.
                # Commit pending state.json changes before merge-squash.
                subprocess.run(["git", "add", "-A"], capture_output=True)
                subprocess.run(["git", "commit", "-m",
                    "plet: state before merge-squash {}".format(iter_id),
                    "--allow-empty"], capture_output=True)

                ms_out, ms_err, ms_rc = _run_script("plet_git_ops.py", ["merge-squash", global_plet_dir,
                    "--iter-id", iter_id])
                if ms_rc != 0:
                    _emit_event({"type": "error", "iterationId": iter_id,
                                 "error": "merge-squash failed: " + ms_err[:200]}, output_ndjson)
                    _emit_text("  merge-squash failed — blocking: {}".format(ms_err[:200]), output_ndjson)
                    _update_lifecycle(global_plet_dir, iter_id, "blocked")
                    _emit_event({"type": "iteration_complete", "iterationId": iter_id,
                                 "lifecycle": "blocked"}, output_ndjson)
                    failed_this_round.add(iter_id)
                else:
                    _update_lifecycle(global_plet_dir, iter_id, "complete")
                    completed_this_run += 1
                    _emit_event({"type": "iteration_merged", "iterationId": iter_id}, output_ndjson)
                    _emit_event({"type": "iteration_complete", "iterationId": iter_id,
                                 "lifecycle": "complete"}, output_ndjson)
                    _emit_text("[{}] {}: passed, merged".format(
                        completed_this_run, iter_id), output_ndjson)
            elif verdict == "rejected":
                # Check retry — read from worktree (has verification reports)
                retry_data, _, _ = _run_script_json("plet_schedule.py",
                    ["check-retry", worktree_plet_dir, "--iter-id", iter_id])
                decision = retry_data.get("decision", "abort") if retry_data else "abort"
                if decision == "continue" or decision == "first":
                    _update_lifecycle(global_plet_dir, iter_id, "queued")
                    _emit_event({"type": "iteration_complete", "iterationId": iter_id,
                                 "lifecycle": "queued"}, output_ndjson)
                    _emit_text("[{}] {}: rejected, retry queued".format(
                        completed_this_run + 1, iter_id), output_ndjson)
                else:
                    _update_lifecycle(global_plet_dir, iter_id, "blocked")
                    _emit_event({"type": "iteration_complete", "iterationId": iter_id,
                                 "lifecycle": "blocked"}, output_ndjson)
                    _emit_text("[{}] {}: rejected, retry exhausted — blocked".format(
                        completed_this_run + 1, iter_id), output_ndjson)
            elif verdict == "blocked":
                _update_lifecycle(global_plet_dir, iter_id, "blocked")
                _emit_event({"type": "iteration_complete", "iterationId": iter_id,
                             "lifecycle": "blocked"}, output_ndjson)

            # Cleanup worktree
            _run_script("plet_git_iteration.py", ["worktree-remove", global_plet_dir,
                "--iter-id", iter_id])

            # Breakpoint after
            bp_data, _, _ = _run_script_json("plet_schedule.py",
                ["check-breakpoints", global_plet_dir, "--iter-id", iter_id, "--position", "after"])
            if bp_data and bp_data.get("result") == "hit":
                _emit_event({"type": "breakpoint_hit", "iterationId": iter_id,
                             "position": "after"}, output_ndjson)
                result = _make_result("breakpoint_after", counts,
                    session_number=session_number, branch=branch,
                    completed=completed_this_run,
                    pause_context={"iterationId": iter_id, "phase": None, "error": None})
                _emit_event(result, output_ndjson)
                return 0

            # Max iterations check
            if max_iterations and completed_this_run >= max_iterations:
                result = _make_result("max_iterations_reached", counts,
                    session_number=session_number, branch=branch,
                    completed=completed_this_run)
                _emit_event(result, output_ndjson)
                _emit_text("Paused: max iterations reached ({}/{})".format(
                    completed_this_run, max_iterations), output_ndjson)
                return 0

    # -------------------------------------------------------------------
    # Phase 3: Session end
    # -------------------------------------------------------------------

    # Postflight
    _run_script("plet_gate_session.py", ["postflight", global_plet_dir, "--session-type", "loop"])

    # End session
    _run_script("plet_session.py", ["end-session", global_plet_dir])

    # Write COMPLETE canary
    _run_script("plet_entries.py", ["add-progress", global_plet_dir,
                "--iter-id", "SESSION", "--iter-title", "Orchestrator",
                "--phase", "orchestrator", "--attempt", "1",
                "--status", "COMPLETE",
                "--content", "Loop {} complete. {} iterations completed, {} blocked.".format(
                    session_number, completed_this_run, counts.get("blocked", 0))])

    # Re-read final counts
    eligible_data, _, _ = _run_script_json("plet_schedule.py", ["eligible", global_plet_dir])
    if eligible_data:
        counts = eligible_data.get("counts", counts)
        stuck = eligible_data.get("stuckIterations", [])

    all_complete = counts.get("complete", 0) + counts.get("withdrawn", 0)
    total = sum(counts.get(k, 0) for k in counts if k != "eligible")
    reason = "all_complete" if all_complete == total else "all_blocked_or_complete"

    result = _make_result(reason, counts,
        session_number=session_number, branch=branch,
        completed=completed_this_run, stuck_iterations=stuck)
    _emit_event(result, output_ndjson)
    _emit_text("Loop {} complete: {} iterations, {} blocked".format(
        session_number, completed_this_run, counts.get("blocked", 0)), output_ndjson)
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    commands = {
        "run": cmd_run,
    }
    return dispatch(
        commands, "plet_orchestrator", SCRIPT_VERSION, SKILL_VERSION, __doc__
    )


if __name__ == "__main__":
    sys.exit(main())
