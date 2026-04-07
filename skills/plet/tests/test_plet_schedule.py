#!/usr/bin/env python3
"""Tests for schedule.py — loop scheduling decisions.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_schedule.py
    pytest skills/plet/tests/test_schedule.py

Red/green, command-by-command: eligible first, then check-breakpoints, then check-retry.
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from util_fixture import make_global_state as _make_global_state
from util_fixture import make_iter_state as _make_iter_state

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

import schedule  # noqa: E402

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["schedule", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = schedule.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def make_global_state(plet_dir, dep_map=None, breakpoints=None, lifecycles=None):
    """Create a minimal global state.json — delegates to shared fixture."""
    return _make_global_state(plet_dir, dep_map=dep_map, lifecycles=lifecycles, loop_session=1, breakpoints=breakpoints)


def make_iter_state(plet_dir, iter_id, attempts=None, verification_reports=None, verify_verdict=None):
    """Create a minimal per-iteration state file — delegates to shared fixture."""
    return _make_iter_state(
        plet_dir,
        iter_id=iter_id,
        attempts=attempts,
        verification_reports=verification_reports,
        verify_verdict=verify_verdict,
    )


# ===========================================================================
# eligible — help
# ===========================================================================


def test_eligible_help():
    print("## eligible — help")

    out, err, _ = run(["eligible", "--help"])
    check("eligible help exits 0", True)
    check("eligible help non-empty", len(out) > 0, "got empty output")


# ===========================================================================
# eligible — missing state.json
# ===========================================================================


def test_eligible_missing_state_json():
    print("\n## eligible — missing state.json")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        os.makedirs(plet_dir)
        out, err, _ = run(["eligible", plet_dir], expect_exit=1)
        check("missing state.json exits 1", True)
        check("error mentions state.json", "state.json" in err.lower() or "state.json" in out.lower(), "stderr: " + err)


# ===========================================================================
# eligible — empty dependency map
# ===========================================================================


def test_eligible_empty_dependency_map():
    print("\n## eligible — empty dependency map")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, dep_map={})

        # Text mode
        out, err, _ = run(["eligible", plet_dir])
        check("empty dep map returns none", out == "none", "got: " + out)

        # JSON mode
        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        check("json empty eligible list", data["eligible"] == [], "got: " + str(data.get("eligible")))
        check("json counts all zero", data["counts"]["eligible"] == 0)


# ===========================================================================
# eligible — single iteration, no deps, queued
# ===========================================================================


def test_eligible_single_queued_no_deps():
    print("\n## eligible — single queued iteration, no deps")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})

        out, err, _ = run(["eligible", plet_dir])
        check("single queued returns ID_001", out == "ID_001", "got: " + out)

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        check("json eligible contains ID_001", data["eligible"] == ["ID_001"])
        check("json counts eligible=1", data["counts"]["eligible"] == 1)
        check(
            "json counts queued=0",
            data["counts"]["queued"] == 0,
            "eligible iterations should not also count as queued",
        )


# ===========================================================================
# eligible — single iteration, not queued (implementing)
# ===========================================================================


def test_eligible_implementing_not_eligible():
    print("\n## eligible — single iteration, implementing (not eligible)")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "implementing"})

        out, err, _ = run(["eligible", plet_dir])
        check("implementing not eligible", out == "none", "got: " + out)

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        check("json implementing counted", data["counts"]["implementing"] == 1)


# ===========================================================================
# eligible — linear chain: A → B → C
# ===========================================================================


def test_eligible_linear_chain():
    print("\n## eligible — linear chain A → B → C")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": ["ID_001"],
                "ID_003": ["ID_002"],
            },
            lifecycles={
                "ID_001": "complete",
                "ID_002": "queued",
                "ID_003": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir])
        check("chain: only B eligible", out == "ID_002", "got: " + out)


# ===========================================================================
# eligible — diamond: A → B, A → C, B+C → D
# ===========================================================================


def test_eligible_diamond_dependency():
    print("\n## eligible — diamond dependency graph")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        dep_map = {
            "ID_001": [],
            "ID_002": ["ID_001"],
            "ID_003": ["ID_001"],
            "ID_004": ["ID_002", "ID_003"],
        }
        # A complete, B+C queued, D queued
        make_global_state(
            plet_dir,
            dep_map=dep_map,
            lifecycles={
                "ID_001": "complete",
                "ID_002": "queued",
                "ID_003": "queued",
                "ID_004": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir])
        lines = out.strip().split("\n")
        check("diamond: B and C eligible", sorted(lines) == ["ID_002", "ID_003"], "got: " + str(lines))
        check("diamond: D not eligible (deps not complete)", "ID_004" not in lines)

        # Now complete B, C still queued — D still not eligible
        make_global_state(
            plet_dir,
            dep_map=dep_map,
            lifecycles={
                "ID_001": "complete",
                "ID_002": "complete",
                "ID_003": "queued",
                "ID_004": "queued",
            },
        )
        out, err, _ = run(["eligible", plet_dir])
        lines = out.strip().split("\n")
        check("diamond partial: C eligible", "ID_003" in lines)
        check("diamond partial: D not yet (C not complete)", "ID_004" not in lines)

        # Complete C too — now D is eligible
        make_global_state(
            plet_dir,
            dep_map=dep_map,
            lifecycles={
                "ID_001": "complete",
                "ID_002": "complete",
                "ID_003": "complete",
                "ID_004": "queued",
            },
        )
        out, err, _ = run(["eligible", plet_dir])
        check("diamond resolved: D eligible", out.strip() == "ID_004", "got: " + out)


# ===========================================================================
# eligible — parallel independent (no deps)
# ===========================================================================


def test_eligible_parallel_independent():
    print("\n## eligible — parallel independent iterations")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": [],
                "ID_003": [],
            },
            lifecycles={
                "ID_001": "queued",
                "ID_002": "queued",
                "ID_003": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir])
        lines = out.strip().split("\n")
        check("all three eligible", sorted(lines) == ["ID_001", "ID_002", "ID_003"], "got: " + str(lines))


# ===========================================================================
# eligible — all lifecycle values (only queued+deps complete is eligible)
# ===========================================================================


def test_eligible_lifecycle_filtering():
    print("\n## eligible — lifecycle filtering")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": [],
                "ID_003": [],
                "ID_004": [],
                "ID_005": [],
                "ID_006": [],
                "ID_007": [],
            },
            lifecycles={
                "ID_001": "queued",
                "ID_002": "ineligible",
                "ID_003": "implementing",
                "ID_004": "verifying",
                "ID_005": "complete",
                "ID_006": "blocked",
                "ID_007": "withdrawn",
            },
        )

        out, err, _ = run(["eligible", plet_dir])
        check("only queued is eligible", out == "ID_001", "got: " + out)

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        counts = data["counts"]
        check("counts ineligible=1", counts["ineligible"] == 1)
        check("counts implementing=1", counts["implementing"] == 1)
        check("counts verifying=1", counts["verifying"] == 1)
        check("counts complete=1", counts["complete"] == 1)
        check("counts blocked=1", counts["blocked"] == 1)
        check("counts withdrawn=1", counts["withdrawn"] == 1)


# ===========================================================================
# eligible — missing per-iteration state file (hard error)
# ===========================================================================


def test_eligible_missing_iter_state_file():
    print("\n## eligible — missing state file for iteration in dep map")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, dep_map={"ID_001": [], "ID_002": ["ID_001"]}, lifecycles={"ID_001": "complete"})
        # ID_002 lifecycle intentionally missing

        out, err, _ = run(["eligible", plet_dir], expect_exit=1)
        check("missing state file exits 1", True)
        check("error mentions ID_002", "ID_002" in err or "ID_002" in out, "stderr: " + err)


# ===========================================================================
# eligible — invalid lifecycle value (caught by enum check)
# ===========================================================================


def test_eligible_invalid_lifecycle_value():
    print("\n## eligible — invalid lifecycle value")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "complet"})  # typo

        out, err, _ = run(["eligible", plet_dir], expect_exit=1)
        check("invalid lifecycle exits 1", True)
        check("error mentions invalid lifecycle", "lifecycle" in err.lower() or "complet" in err, "stderr: " + err)


# ===========================================================================
# eligible — sorted output order
# ===========================================================================


def test_eligible_sorted_output():
    print("\n## eligible — output sorted by ID")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_003": [],
                "ID_001": [],
                "ID_002": [],
            },
            lifecycles={
                "ID_001": "queued",
                "ID_002": "queued",
                "ID_003": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir])
        lines = out.strip().split("\n")
        check("output sorted", lines == ["ID_001", "ID_002", "ID_003"], "got: " + str(lines))


# ===========================================================================
# eligible — stuck iterations (blocked dep)
# ===========================================================================


def test_eligible_stuck_blocked_dep():
    print("\n## eligible — stuck iteration (dep is blocked)")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": ["ID_001"],
                "ID_003": ["ID_002"],
            },
            lifecycles={
                "ID_001": "blocked",
                "ID_002": "queued",
                "ID_003": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        check("no eligible", data["eligible"] == [])
        check("stuckIterations present", "stuckIterations" in data, "keys: " + str(list(data.keys())))
        stuck = data.get("stuckIterations", [])
        stuck_ids = [s["iterationId"] for s in stuck]
        check("ID_002 is stuck", "ID_002" in stuck_ids, "got: " + str(stuck_ids))
        # ID_003 depends on ID_002 which is queued (not blocked) — not directly stuck.
        # Transitive stuckness (ID_002 is stuck so ID_003 is transitively stuck) is
        # a future concern. Direct detection catches the important case.
        check("ID_003 not directly stuck (dep is queued)", "ID_003" not in stuck_ids, "got: " + str(stuck_ids))

        # Check unsatisfiable deps reported
        id002_stuck = [s for s in stuck if s["iterationId"] == "ID_002"][0]
        check(
            "ID_002 unsatisfiable dep is ID_001",
            "ID_001" in id002_stuck["unsatisfiableDeps"],
            "got: " + str(id002_stuck.get("unsatisfiableDeps")),
        )


# ===========================================================================
# eligible — stuck iteration (dep is withdrawn)
# ===========================================================================


def test_eligible_stuck_withdrawn_dep():
    print("\n## eligible — stuck iteration (dep is withdrawn)")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": ["ID_001"],
            },
            lifecycles={
                "ID_001": "withdrawn",
                "ID_002": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        stuck = data.get("stuckIterations", [])
        check(
            "ID_002 stuck on withdrawn dep",
            len(stuck) == 1 and stuck[0]["iterationId"] == "ID_002",
            "got: " + str(stuck),
        )


# ===========================================================================
# eligible — stuck iteration (text output)
# ===========================================================================


def test_eligible_stuck_text_output():
    print("\n## eligible — stuck iteration text output")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": ["ID_001"],
            },
            lifecycles={
                "ID_001": "blocked",
                "ID_002": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir])
        check("text mentions stuck", "stuck" in out.lower(), "got: " + out)
        check("text mentions ID_002", "ID_002" in out, "got: " + out)


# ===========================================================================
# eligible — not stuck (dep is queued, could still complete)
# ===========================================================================


def test_eligible_not_stuck_dep_queued():
    print("\n## eligible — dep is queued (not stuck, just waiting)")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": ["ID_001"],
            },
            lifecycles={
                "ID_001": "queued",
                "ID_002": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        stuck = data.get("stuckIterations", [])
        check("no stuck iterations (dep is queued)", len(stuck) == 0, "got: " + str(stuck))


# ===========================================================================
# eligible — not stuck (dep is implementing, in progress)
# ===========================================================================


def test_eligible_not_stuck_dep_implementing():
    print("\n## eligible — dep is implementing (not stuck, in progress)")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            dep_map={
                "ID_001": [],
                "ID_002": ["ID_001"],
            },
            lifecycles={
                "ID_001": "implementing",
                "ID_002": "queued",
            },
        )

        out, err, _ = run(["eligible", plet_dir, "--output", "json"])
        data = json.loads(out)
        stuck = data.get("stuckIterations", [])
        check("no stuck (dep in progress)", len(stuck) == 0, "got: " + str(stuck))


# ===========================================================================
# check-breakpoints — help
# ===========================================================================


def test_check_breakpoints_help():
    print("\n## check-breakpoints — help")

    out, err, _ = run(["check-breakpoints", "--help"])
    check("check-breakpoints help exits 0", True)
    check("check-breakpoints help non-empty", len(out) > 0)


# ===========================================================================
# check-breakpoints — missing required args
# ===========================================================================


def test_check_breakpoints_missing_args():
    print("\n## check-breakpoints — missing required args")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir)

        # Missing both --iter-id and --position
        out, err, _ = run(["check-breakpoints", plet_dir], expect_exit=1)
        check("missing args exits 1", True)

        # Missing --position
        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001"], expect_exit=1)
        check("missing position exits 1", True)

        # Missing --iter-id
        out, err, _ = run(["check-breakpoints", plet_dir, "--position", "before"], expect_exit=1)
        check("missing iter-id exits 1", True)

        # Invalid --position
        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "during"], expect_exit=1)
        check("invalid position exits 1", True)
        check("error mentions valid values", "before" in err and "after" in err, "stderr: " + err)


# ===========================================================================
# check-breakpoints — no breakpoints field (always miss)
# ===========================================================================


def test_check_breakpoints_no_field():
    print("\n## check-breakpoints — no breakpoints field")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir)  # no breakpoints kwarg

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "before"])
        check("no breakpoints field returns miss", out == "miss", "got: " + out)

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "after"])
        check("no breakpoints field after also miss", out == "miss", "got: " + out)


# ===========================================================================
# check-breakpoints — empty breakpoint arrays
# ===========================================================================


def test_check_breakpoints_empty_arrays():
    print("\n## check-breakpoints — empty breakpoint arrays")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, breakpoints={"before": [], "after": []})

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "before"])
        check("empty before array returns miss", out == "miss", "got: " + out)


# ===========================================================================
# check-breakpoints — hit before
# ===========================================================================


def test_check_breakpoints_hit_before():
    print("\n## check-breakpoints — hit before")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            breakpoints={
                "before": ["ID_001", "ID_003"],
                "after": ["ID_002"],
            },
        )

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "before"])
        check("ID_001 before is hit", out == "hit", "got: " + out)

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_002", "--position", "before"])
        check("ID_002 before is miss", out == "miss", "got: " + out)

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_003", "--position", "before"])
        check("ID_003 before is hit", out == "hit", "got: " + out)


# ===========================================================================
# check-breakpoints — hit after
# ===========================================================================


def test_check_breakpoints_hit_after():
    print("\n## check-breakpoints — hit after")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            breakpoints={
                "before": ["ID_001"],
                "after": ["ID_002", "ID_004"],
            },
        )

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_002", "--position", "after"])
        check("ID_002 after is hit", out == "hit", "got: " + out)

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "after"])
        check("ID_001 after is miss", out == "miss", "got: " + out)


# ===========================================================================
# check-breakpoints — JSON output
# ===========================================================================


def test_check_breakpoints_json_output():
    print("\n## check-breakpoints — JSON output")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(
            plet_dir,
            breakpoints={
                "before": ["ID_003"],
                "after": [],
            },
        )

        out, err, _ = run(
            ["check-breakpoints", plet_dir, "--iter-id", "ID_003", "--position", "before", "--output", "json"]
        )
        data = json.loads(out)
        check("json status ok", data["status"] == "ok")
        check("json command", data["command"] == "check-breakpoints")
        check("json result hit", data["result"] == "hit")
        check("json iterationId", data["iterationId"] == "ID_003")
        check("json position", data["position"] == "before")

        out, err, _ = run(
            ["check-breakpoints", plet_dir, "--iter-id", "ID_999", "--position", "before", "--output", "json"]
        )
        data = json.loads(out)
        check("json result miss", data["result"] == "miss")


# ===========================================================================
# check-breakpoints — missing state.json
# ===========================================================================


def test_check_breakpoints_missing_state_json():
    print("\n## check-breakpoints — missing state.json")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        os.makedirs(plet_dir)

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "before"], expect_exit=1)
        check("missing state.json exits 1", True)


# ===========================================================================
# check-breakpoints — iter-id not in dep map (still checks breakpoints)
# ===========================================================================


def test_check_breakpoints_iter_not_in_dep_map():
    print("\n## check-breakpoints — iter-id not in dep map")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_global_state(plet_dir, dep_map={"ID_001": []}, breakpoints={"before": ["ID_999"], "after": []})

        out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_999", "--position", "before"])
        check("ID not in dep map still checks breakpoints", out == "hit", "got: " + out)


# ===========================================================================
# check-retry — help
# ===========================================================================


def test_check_retry_help():
    print("\n## check-retry — help")

    out, err, _ = run(["check-retry", "--help"])
    check("check-retry help exits 0", True)
    check("check-retry help non-empty", len(out) > 0)


# ===========================================================================
# check-retry — missing required args
# ===========================================================================


def test_check_retry_missing_args():
    print("\n## check-retry — missing required args")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_iter_state(plet_dir, "ID_001")

        out, err, _ = run(["check-retry", plet_dir], expect_exit=1)
        check("missing iter-id exits 1", True)


# ===========================================================================
# check-retry — missing state file
# ===========================================================================


def test_check_retry_missing_state_file():
    print("\n## check-retry — missing state file")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        os.makedirs(os.path.join(plet_dir, "state"))

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"], expect_exit=1)
        check("missing state file exits 1", True)
        check("error mentions ID_001", "ID_001" in err or "ID_001" in out, "stderr: " + err)


# ===========================================================================
# check-retry — no verification reports (first)
# ===========================================================================


def test_check_retry_no_reports():
    print("\n## check-retry — no verification reports, remainingRetries=3")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_iter_state(plet_dir, "ID_001")
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
        check("remainingRetries=3 returns continue", out == "continue", "got: " + out)


# ===========================================================================
# check-retry — empty verification reports (first)
# ===========================================================================


def test_check_retry_empty_reports():
    print("\n## check-retry — empty verification reports, remainingRetries=3")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_iter_state(plet_dir, "ID_001", verification_reports=[])
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
        check("remainingRetries=3 returns continue", out == "continue", "got: " + out)


# ===========================================================================
# check-retry — 1 report, under limit (continue)
# ===========================================================================


def test_check_retry_single_report_under_limit():
    print("\n## check-retry — single report, under limit")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        reports = [
            {
                "attempt": 1,
                "verdict": "rejected",
                "criteriaResults": [
                    {"id": "AC_1", "status": "pass"},
                    {"id": "AC_2", "status": "fail"},
                    {"id": "AC_3", "status": "fail"},
                ],
            }
        ]
        make_iter_state(plet_dir, "ID_001", attempts={"implement": 1, "verify": 1}, verification_reports=reports)
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
        check("single report under limit returns continue", out == "continue", "got: " + out)


# ===========================================================================
# check-retry — remainingRetries > 0 (continue)
# ===========================================================================


def test_check_retry_remaining_retries_positive():
    print("\n## check-retry — remainingRetries=2 returns continue")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_iter_state(plet_dir, "ID_001", attempts={"implement": 1, "verify": 1})
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})
        # Set remainingRetries in state.json
        gp = os.path.join(plet_dir, "state.json")
        with open(gp) as f:
            gs = json.load(f)
        gs["remainingRetries"] = {"ID_001": 2}
        with open(gp, "w") as f:
            json.dump(gs, f, indent=2)
            f.write("\n")

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
        check("remainingRetries=2 returns continue", out == "continue", "got: " + out)

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
        data = json.loads(out)
        check("json decision continue", data["decision"] == "continue")
        check("json remainingRetries", data["remainingRetries"] == 2)


# ===========================================================================
# check-retry — not decreasing at limit (abort)
# ===========================================================================


def test_check_retry_remaining_retries_zero():
    print("\n## check-retry — remainingRetries=0 returns abort")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_iter_state(plet_dir, "ID_001", attempts={"implement": 3, "verify": 3})
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})
        gp = os.path.join(plet_dir, "state.json")
        with open(gp) as f:
            gs = json.load(f)
        gs["remainingRetries"] = {"ID_001": 0}
        with open(gp, "w") as f:
            json.dump(gs, f, indent=2)
            f.write("\n")

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
        check("remainingRetries=0 returns abort", out == "abort", "got: " + out)

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
        data = json.loads(out)
        check("json decision abort", data["decision"] == "abort")
        check("json remainingRetries 0", data["remainingRetries"] == 0)


# ===========================================================================
# check-retry — remainingRetries=1 (continue, last chance)
# ===========================================================================


def test_check_retry_remaining_retries_one():
    print("\n## check-retry — remainingRetries=1 (last chance)")

    with tempfile.TemporaryDirectory() as tmp:
        plet_dir = os.path.join(tmp, "plet")
        make_iter_state(plet_dir, "ID_001", attempts={"implement": 2, "verify": 2})
        make_global_state(plet_dir, dep_map={"ID_001": []}, lifecycles={"ID_001": "queued"})
        gp = os.path.join(plet_dir, "state.json")
        with open(gp) as f:
            gs = json.load(f)
        gs["remainingRetries"] = {"ID_001": 1}
        with open(gp, "w") as f:
            json.dump(gs, f, indent=2)
            f.write("\n")

        out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
        check("remainingRetries=1 returns continue", out == "continue", "got: " + out)


# ===========================================================================
# Summary
# ===========================================================================


def main():
    test_eligible_help()
    test_eligible_missing_state_json()
    test_eligible_empty_dependency_map()
    test_eligible_single_queued_no_deps()
    test_eligible_implementing_not_eligible()
    test_eligible_linear_chain()
    test_eligible_diamond_dependency()
    test_eligible_parallel_independent()
    test_eligible_lifecycle_filtering()
    test_eligible_missing_iter_state_file()
    test_eligible_invalid_lifecycle_value()
    test_eligible_sorted_output()
    test_eligible_stuck_blocked_dep()
    test_eligible_stuck_withdrawn_dep()
    test_eligible_stuck_text_output()
    test_eligible_not_stuck_dep_queued()
    test_eligible_not_stuck_dep_implementing()
    test_check_breakpoints_help()
    test_check_breakpoints_missing_args()
    test_check_breakpoints_no_field()
    test_check_breakpoints_empty_arrays()
    test_check_breakpoints_hit_before()
    test_check_breakpoints_hit_after()
    test_check_breakpoints_json_output()
    test_check_breakpoints_missing_state_json()
    test_check_breakpoints_iter_not_in_dep_map()
    test_check_retry_help()
    test_check_retry_missing_args()
    test_check_retry_missing_state_file()
    test_check_retry_no_reports()
    test_check_retry_empty_reports()
    test_check_retry_single_report_under_limit()
    test_check_retry_remaining_retries_positive()
    test_check_retry_remaining_retries_zero()
    test_check_retry_remaining_retries_one()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
