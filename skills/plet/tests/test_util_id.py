#!/usr/bin/env python3
"""Tests for util_id.py — plet ID generation utilities.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_util_id.py

Since util_id is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import os
import sys
import time

# Add scripts dir to path so we can import util_id
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# crockford_encode
# ---------------------------------------------------------------------------

def test_crockford_encode():
    print("\n## crockford_encode — basic values")
    import util_id
    check("zero", util_id.crockford_encode(0) == "0")
    check("one", util_id.crockford_encode(1) == "1")
    check("31", util_id.crockford_encode(31) == "Z")
    check("32", util_id.crockford_encode(32) == "10")
    # Crockford alphabet excludes I, L, O, U
    result = util_id.crockford_encode(1000)
    check("no I in output", "I" not in result)
    check("no L in output", "L" not in result)
    check("no O in output", "O" not in result)
    check("no U in output", "U" not in result)


# ---------------------------------------------------------------------------
# crockford_timestamp
# ---------------------------------------------------------------------------

def test_crockford_timestamp():
    print("\n## crockford_timestamp — format")
    import util_id
    ts = util_id.crockford_timestamp()
    check("10 chars", len(ts) == 10)
    # All chars should be in Crockford alphabet
    valid = set("0123456789ABCDEFGHJKMNPQRSTVWXYZ")
    check("valid chars", all(c in valid for c in ts))


def test_crockford_timestamp_monotonic():
    print("\n## crockford_timestamp — monotonically increasing")
    import util_id
    ts1 = util_id.crockford_timestamp()
    time.sleep(0.002)  # 2ms gap
    ts2 = util_id.crockford_timestamp()
    check("second >= first", ts2 >= ts1)


# ---------------------------------------------------------------------------
# normalize_iteration
# ---------------------------------------------------------------------------

def test_normalize_iteration():
    print("\n## normalize_iteration")
    import util_id
    check("ID_001 -> id001", util_id.normalize_iteration("ID_001") == "id001")
    check("ID_42 -> id42", util_id.normalize_iteration("ID_42") == "id42")
    check("proj stays proj", util_id.normalize_iteration("proj") == "proj")


# ---------------------------------------------------------------------------
# phase_attempt_segment
# ---------------------------------------------------------------------------

def test_phase_attempt_segment():
    print("\n## phase_attempt_segment")
    import util_id
    check("implement-1 -> i1", util_id.phase_attempt_segment("implement", 1) == "i1")
    check("verify-2 -> v2", util_id.phase_attempt_segment("verify", 2) == "v2")
    check("refine-1 -> r1", util_id.phase_attempt_segment("refine", 1) == "r1")
    check("plan-1 -> p1", util_id.phase_attempt_segment("plan", 1) == "p1")


# ---------------------------------------------------------------------------
# generate_plet_id
# ---------------------------------------------------------------------------

def test_generate_plet_id():
    print("\n## generate_plet_id — structure")
    import util_id
    pid = util_id.generate_plet_id("epr", "ID_001", "implement", 1)
    parts = pid.split("_")
    check("starts with prefix", parts[0] == "epr")
    check("4 segments", len(parts) == 4)
    check("timestamp is 10 chars", len(parts[1]) == 10)
    check("iteration segment", parts[2] == "id001")
    check("phase segment", parts[3] == "i1")


def test_generate_plet_id_prefixes():
    print("\n## generate_plet_id — different prefixes")
    import util_id
    check("epr prefix", util_id.generate_plet_id("epr", "ID_001", "implement", 1).startswith("epr_"))
    check("eln prefix", util_id.generate_plet_id("eln", "ID_002", "verify", 1).startswith("eln_"))
    check("eem prefix", util_id.generate_plet_id("eem", "ID_003", "refine", 2).startswith("eem_"))
    check("tev prefix", util_id.generate_plet_id("tev", "ID_001", "implement", 1).startswith("tev_"))
    check("vrp prefix", util_id.generate_plet_id("vrp", "ID_001", "verify", 1).startswith("vrp_"))


def test_generate_plet_id_uniqueness():
    print("\n## generate_plet_id — uniqueness")
    import util_id
    ids = set()
    for i in range(5):
        pid = util_id.generate_plet_id("epr", "ID_001", "implement", 1)
        ids.add(pid)
        time.sleep(0.002)  # 2ms gap for timestamp uniqueness
    check("unique IDs across calls", len(ids) == 5)


def test_generate_plet_id_proj():
    print("\n## generate_plet_id — project-level")
    import util_id
    pid = util_id.generate_plet_id("epr", "proj", "refine", 1)
    check("has proj segment", "_proj_" in pid)
    check("refine segment", pid.endswith("_r1"))


def test_generate_plet_id_plan_phase():
    print("\n## generate_plet_id — plan phase")
    import util_id
    pid = util_id.generate_plet_id("epr", "proj", "plan", 1)
    check("plan segment", pid.endswith("_p1"))


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Testing: util_id.py\n")

    test_crockford_encode()
    test_crockford_timestamp()
    test_crockford_timestamp_monotonic()
    test_normalize_iteration()
    test_phase_attempt_segment()
    test_generate_plet_id()
    test_generate_plet_id_prefixes()
    test_generate_plet_id_uniqueness()
    test_generate_plet_id_proj()
    test_generate_plet_id_plan_phase()

    print("\n{}".format("=" * 40))
    print("  {} passed, {} failed".format(passed, failed))
    print("{}".format("=" * 40))

    sys.exit(1 if failed else 0)
