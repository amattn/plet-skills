#!/usr/bin/env python3
"""Tests for util_git.py — pure git naming convention functions.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_util_git.py

Since util_git is an internal module (not a CLI tool), these tests
import directly rather than using subprocess.
"""

import os
import sys

# Add scripts dir to path so we can import util_git
SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "scripts")
sys.path.insert(0, SCRIPTS_DIR)

passed = 0
failed = 0


def check(name, condition, detail=""):
    """Record a test result."""
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# active_session_branch
# ---------------------------------------------------------------------------


def test_active_session_branch_with_active():
    """Lines 21-22: entry with endedAt=None found, returns its branch."""
    print("\n## active_session_branch — active session exists")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loop1/workstream", "endedAt": "2026-03-01T00:00:00Z"},
            {"branch": "plet/PROJ/loop2/workstream", "endedAt": None},
        ]
    }
    result = util_git.active_session_branch(state)
    check("returns active branch", result == "plet/PROJ/loop2/workstream")


def test_active_session_branch_multiple_active():
    """Lines 21-22: reversed iteration means last active wins."""
    print("\n## active_session_branch — multiple active (last wins)")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loop1/workstream", "endedAt": None},
            {"branch": "plet/PROJ/loop2/workstream", "endedAt": None},
        ]
    }
    result = util_git.active_session_branch(state)
    check("returns last active branch", result == "plet/PROJ/loop2/workstream")


def test_active_session_branch_no_active_fallback():
    """Line 25: no active session, falls back to last entry's branch."""
    print("\n## active_session_branch — no active, fallback to last")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loop1/workstream", "endedAt": "2026-03-01T00:00:00Z"},
            {"branch": "plet/PROJ/loop2/workstream", "endedAt": "2026-03-02T00:00:00Z"},
        ]
    }
    result = util_git.active_session_branch(state)
    check("returns last session branch", result == "plet/PROJ/loop2/workstream")


def test_active_session_branch_empty_history():
    """No sessionHistory entries at all — returns None."""
    print("\n## active_session_branch — empty history")
    import util_git

    state = {"sessionHistory": []}
    result = util_git.active_session_branch(state)
    check("returns None", result is None)


def test_active_session_branch_no_key():
    """No sessionHistory key — returns None."""
    print("\n## active_session_branch — missing key")
    import util_git

    state = {}
    result = util_git.active_session_branch(state)
    check("returns None", result is None)


# ---------------------------------------------------------------------------
# active_loop_number
# ---------------------------------------------------------------------------


def test_active_loop_number_from_branch():
    """Lines 38-44: parses loop number from branch name."""
    print("\n## active_loop_number — parses from branch")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loop3/workstream", "endedAt": None},
        ],
        "loopSessionCount": 99,
    }
    result = util_git.active_loop_number(state)
    check("returns 3 from branch", result == 3)


def test_active_loop_number_iteration_branch():
    """Lines 38-44: parses loop number from iteration branch."""
    print("\n## active_loop_number — iteration branch")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loop5/ID_001", "endedAt": None},
        ],
        "loopSessionCount": 1,
    }
    result = util_git.active_loop_number(state)
    check("returns 5 from iteration branch", result == 5)


def test_active_loop_number_invalid_loop_part():
    """Lines 43-44: ValueError/IndexError fallback when loop part is not a number."""
    print("\n## active_loop_number — invalid loop suffix")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loopXYZ/workstream", "endedAt": None},
        ],
        "loopSessionCount": 7,
    }
    result = util_git.active_loop_number(state)
    check("falls back to loopSessionCount", result == 7)


def test_active_loop_number_empty_loop_suffix():
    """Lines 43-44: 'loop' with no digits."""
    print("\n## active_loop_number — empty loop suffix")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/loop/workstream", "endedAt": None},
        ],
        "loopSessionCount": 4,
    }
    result = util_git.active_loop_number(state)
    check("falls back to loopSessionCount", result == 4)


def test_active_loop_number_no_loop_in_branch():
    """Branch without a loop part — falls back to loopSessionCount."""
    print("\n## active_loop_number — no loop in branch")
    import util_git

    state = {
        "sessionHistory": [
            {"branch": "plet/PROJ/plan1/workstream", "endedAt": None},
        ],
        "loopSessionCount": 2,
    }
    result = util_git.active_loop_number(state)
    check("falls back to loopSessionCount", result == 2)


def test_active_loop_number_no_branch():
    """No session history — falls back to loopSessionCount."""
    print("\n## active_loop_number — no branch")
    import util_git

    state = {"loopSessionCount": 10}
    result = util_git.active_loop_number(state)
    check("falls back to loopSessionCount", result == 10)


def test_active_loop_number_no_fallback():
    """No session history and no loopSessionCount — returns 0."""
    print("\n## active_loop_number — no fallback")
    import util_git

    state = {}
    result = util_git.active_loop_number(state)
    check("returns 0", result == 0)


# ---------------------------------------------------------------------------
# derive_branch_name
# ---------------------------------------------------------------------------


def test_derive_branch_name_iteration():
    """Lines 61-62: branch_type='iteration'."""
    print("\n## derive_branch_name — iteration")
    import util_git

    state = {"projectId": "LOGA", "loopSessionCount": 3, "refineSessionCount": 0}
    result = util_git.derive_branch_name(state, "iteration", iter_id="ID_001")
    check("iteration branch", result == "plet/LOGA/loop3/ID_001")


def test_derive_branch_name_workstream():
    """Workstream branch type."""
    print("\n## derive_branch_name — workstream")
    import util_git

    state = {"projectId": "LOGA", "loopSessionCount": 2, "refineSessionCount": 0}
    result = util_git.derive_branch_name(state, "workstream")
    check("workstream branch", result == "plet/LOGA/loop2/workstream")


def test_derive_branch_name_plan():
    """Line 67: branch_type='plan'."""
    print("\n## derive_branch_name — plan")
    import util_git

    state = {"projectId": "SPARK", "loopSessionCount": 5, "refineSessionCount": 0}
    result = util_git.derive_branch_name(state, "plan")
    check("plan branch", result == "plet/SPARK/plan1/workstream")


def test_derive_branch_name_refine():
    """Refine branch type."""
    print("\n## derive_branch_name — refine")
    import util_git

    state = {"projectId": "LOGA", "loopSessionCount": 1, "refineSessionCount": 2}
    result = util_git.derive_branch_name(state, "refine")
    check("refine branch", result == "plet/LOGA/refine2/workstream")


def test_derive_branch_name_unknown_type():
    """Unknown branch_type returns None."""
    print("\n## derive_branch_name — unknown type")
    import util_git

    state = {"projectId": "LOGA", "loopSessionCount": 1, "refineSessionCount": 0}
    result = util_git.derive_branch_name(state, "unknown")
    check("returns None", result is None)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_active_session_branch_with_active()
    test_active_session_branch_multiple_active()
    test_active_session_branch_no_active_fallback()
    test_active_session_branch_empty_history()
    test_active_session_branch_no_key()

    test_active_loop_number_from_branch()
    test_active_loop_number_iteration_branch()
    test_active_loop_number_invalid_loop_part()
    test_active_loop_number_empty_loop_suffix()
    test_active_loop_number_no_loop_in_branch()
    test_active_loop_number_no_branch()
    test_active_loop_number_no_fallback()

    test_derive_branch_name_iteration()
    test_derive_branch_name_workstream()
    test_derive_branch_name_plan()
    test_derive_branch_name_refine()
    test_derive_branch_name_unknown_type()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
