#!/usr/bin/env python3
"""Tests for plet_schedule.py — loop scheduling decisions.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_schedule.py

Red/green, command-by-command: eligible first, then check-breakpoints, then check-retry.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from util_fixture import make_global_state as _make_global_state
from util_fixture import make_iter_state as _make_iter_state

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_schedule.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run the script with args via subprocess, assert exit code."""
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Exit code {}, expected {}.\nstdout: {}\nstderr: {}".format(
                result.returncode, expect_exit, result.stdout, result.stderr
            )
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
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

print("## eligible — help")

out, err, _ = run(["eligible", "--help"])
check("eligible help exits 0", True)
check("eligible help non-empty", len(out) > 0, "got empty output")

# ===========================================================================
# eligible — missing state.json
# ===========================================================================

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
    check("json counts queued=0", data["counts"]["queued"] == 0, "eligible iterations should not also count as queued")

# ===========================================================================
# eligible — single iteration, not queued (implementing)
# ===========================================================================

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
        "ID_002 stuck on withdrawn dep", len(stuck) == 1 and stuck[0]["iterationId"] == "ID_002", "got: " + str(stuck)
    )

# ===========================================================================
# eligible — stuck iteration (text output)
# ===========================================================================

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

print("\n## check-breakpoints — help")

out, err, _ = run(["check-breakpoints", "--help"])
check("check-breakpoints help exits 0", True)
check("check-breakpoints help non-empty", len(out) > 0)

# ===========================================================================
# check-breakpoints — missing required args
# ===========================================================================

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

print("\n## check-breakpoints — empty breakpoint arrays")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, breakpoints={"before": [], "after": []})

    out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "before"])
    check("empty before array returns miss", out == "miss", "got: " + out)

# ===========================================================================
# check-breakpoints — hit before
# ===========================================================================

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

print("\n## check-breakpoints — missing state.json")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    os.makedirs(plet_dir)

    out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_001", "--position", "before"], expect_exit=1)
    check("missing state.json exits 1", True)

# ===========================================================================
# check-breakpoints — iter-id not in dep map (still checks breakpoints)
# ===========================================================================

print("\n## check-breakpoints — iter-id not in dep map")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_global_state(plet_dir, dep_map={"ID_001": []}, breakpoints={"before": ["ID_999"], "after": []})

    out, err, _ = run(["check-breakpoints", plet_dir, "--iter-id", "ID_999", "--position", "before"])
    check("ID not in dep map still checks breakpoints", out == "hit", "got: " + out)


# ===========================================================================
# check-retry — help
# ===========================================================================

print("\n## check-retry — help")

out, err, _ = run(["check-retry", "--help"])
check("check-retry help exits 0", True)
check("check-retry help non-empty", len(out) > 0)

# ===========================================================================
# check-retry — missing required args
# ===========================================================================

print("\n## check-retry — missing required args")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_iter_state(plet_dir, "ID_001")

    out, err, _ = run(["check-retry", plet_dir], expect_exit=1)
    check("missing iter-id exits 1", True)

# ===========================================================================
# check-retry — missing state file
# ===========================================================================

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

print("\n## check-retry — no verification reports")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_iter_state(plet_dir, "ID_001")

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("no reports returns first", out == "first", "got: " + out)

# ===========================================================================
# check-retry — empty verification reports (first)
# ===========================================================================

print("\n## check-retry — empty verification reports")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    make_iter_state(plet_dir, "ID_001", verification_reports=[])

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("empty reports returns first", out == "first", "got: " + out)

# ===========================================================================
# check-retry — 1 report, under limit (continue)
# ===========================================================================

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

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("single report under limit returns continue", out == "continue", "got: " + out)

# ===========================================================================
# check-retry — strictly decreasing trend (continue, extended)
# ===========================================================================

print("\n## check-retry — strictly decreasing trend")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
                {"id": "AC_4", "status": "fail"},
                {"id": "AC_5", "status": "fail"},
            ],
        },
        {
            "attempt": 2,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "pass"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
                {"id": "AC_4", "status": "fail"},
                {"id": "AC_5", "status": "pass"},
            ],
        },
        {
            "attempt": 3,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "pass"},
                {"id": "AC_2", "status": "pass"},
                {"id": "AC_3", "status": "fail"},
                {"id": "AC_4", "status": "pass"},
                {"id": "AC_5", "status": "pass"},
            ],
        },
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 3, "verify": 3}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("decreasing 5→3→1 returns continue", out == "continue", "got: " + out)

    # Check JSON for extended limit
    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
    data = json.loads(out)
    check("json decision continue", data["decision"] == "continue")
    check("json maxAttempts extended to 6", data["maxAttempts"] == 6)
    check("json failureTrend", data["failureTrend"] == [5, 3, 1])
    check("json trendDirection decreasing", data["trendDirection"] == "decreasing")

# ===========================================================================
# check-retry — not decreasing at limit (abort)
# ===========================================================================

print("\n## check-retry — not decreasing at limit")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
            ],
        },
        {
            "attempt": 2,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "pass"},
            ],
        },
        {
            "attempt": 3,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
            ],
        },
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 3, "verify": 3}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("not decreasing 3→2→3 at limit returns abort", out == "abort", "got: " + out)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
    data = json.loads(out)
    check("json decision abort", data["decision"] == "abort")
    check("json maxAttempts default 3", data["maxAttempts"] == 3)
    check("json trendDirection not_decreasing", data["trendDirection"] == "not_decreasing")

# ===========================================================================
# check-retry — flat trend at limit (abort)
# ===========================================================================

print("\n## check-retry — flat trend at limit")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [{"id": "AC_1", "status": "fail"}],
        },
        {
            "attempt": 2,
            "verdict": "rejected",
            "criteriaResults": [{"id": "AC_1", "status": "fail"}],
        },
        {
            "attempt": 3,
            "verdict": "rejected",
            "criteriaResults": [{"id": "AC_1", "status": "fail"}],
        },
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 3, "verify": 3}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("flat 1→1→1 at limit returns abort", out == "abort", "got: " + out)

# ===========================================================================
# check-retry — not decreasing but under limit (continue)
# ===========================================================================

print("\n## check-retry — not decreasing but under limit")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
            ],
        },
        {
            "attempt": 2,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
            ],
        },
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 2, "verify": 2}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("increasing but under limit returns continue", out == "continue", "got: " + out)

# ===========================================================================
# check-retry — error/skipped not counted as failures
# ===========================================================================

print("\n## check-retry — error/skipped excluded from failure count")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "error"},
                {"id": "AC_3", "status": "skipped"},
                {"id": "AC_4", "status": "fail"},
            ],
        },
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 1, "verify": 1}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
    data = json.loads(out)
    check("failure trend counts only fail", data["failureTrend"] == [2], "got: " + str(data.get("failureTrend")))

# ===========================================================================
# check-retry — report with no criteriaResults (0 failures)
# ===========================================================================

print("\n## check-retry — report with no criteriaResults")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {"attempt": 1, "verdict": "rejected"},
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 1, "verify": 1}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
    data = json.loads(out)
    check(
        "no criteriaResults treated as 0 failures", data["failureTrend"] == [0], "got: " + str(data.get("failureTrend"))
    )

# ===========================================================================
# check-retry — extended limit, 4th attempt still decreasing (continue)
# ===========================================================================

print("\n## check-retry — extended limit, 4th attempt")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
                {"id": "AC_4", "status": "fail"},
            ],
        },
        {
            "attempt": 2,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
                {"id": "AC_4", "status": "pass"},
            ],
        },
        {
            "attempt": 3,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "pass"},
                {"id": "AC_4", "status": "pass"},
            ],
        },
        {
            "attempt": 4,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "pass"},
                {"id": "AC_3", "status": "pass"},
                {"id": "AC_4", "status": "pass"},
            ],
        },
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 4, "verify": 4}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("4th attempt still decreasing returns continue", out == "continue", "got: " + out)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001", "--output", "json"])
    data = json.loads(out)
    check("json trend 4→3→2→1", data["failureTrend"] == [4, 3, 2, 1])
    check("json max 6", data["maxAttempts"] == 6)

# ===========================================================================
# check-retry — extended limit exhausted at 6 (abort)
# ===========================================================================

print("\n## check-retry — extended limit exhausted at 6")

with tempfile.TemporaryDirectory() as tmp:
    plet_dir = os.path.join(tmp, "plet")
    reports = [
        {"attempt": i, "verdict": "rejected", "criteriaResults": [{"id": "AC_1", "status": "fail"}]}
        for i in range(1, 7)  # 6 reports, all with 1 failure (flat but got extended somehow)
    ]
    # Actually make it strictly decreasing for first 3, then flat
    reports = [
        {
            "attempt": 1,
            "verdict": "rejected",
            "criteriaResults": [
                {"id": "AC_1", "status": "fail"},
                {"id": "AC_2", "status": "fail"},
                {"id": "AC_3", "status": "fail"},
            ],
        },
        {
            "attempt": 2,
            "verdict": "rejected",
            "criteriaResults": [{"id": "AC_1", "status": "fail"}, {"id": "AC_2", "status": "fail"}],
        },
        {"attempt": 3, "verdict": "rejected", "criteriaResults": [{"id": "AC_1", "status": "fail"}]},
        {
            "attempt": 4,
            "verdict": "rejected",
            "criteriaResults": [{"id": "AC_1", "status": "fail"}],
        },  # flat — no longer decreasing
        {"attempt": 5, "verdict": "rejected", "criteriaResults": [{"id": "AC_1", "status": "fail"}]},
        {"attempt": 6, "verdict": "rejected", "criteriaResults": [{"id": "AC_1", "status": "fail"}]},
    ]
    make_iter_state(plet_dir, "ID_001", attempts={"implement": 6, "verify": 6}, verification_reports=reports)

    out, err, _ = run(["check-retry", plet_dir, "--iter-id", "ID_001"])
    check("6 attempts exhausted returns abort", out == "abort", "got: " + out)


# ===========================================================================
# Summary
# ===========================================================================

print("\n{} tests: {} passed, {} failed".format(passed + failed, passed, failed))
sys.exit(1 if failed else 0)
