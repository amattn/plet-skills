#!/usr/bin/env python3
"""Tests for auto-progress (SEQ_20-21).

update-criterion should auto-generate a progress entry when it updates state.
The agent never calls add-progress manually for criterion updates.
"""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts  # noqa: E402

passed = 0
failed = 0


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project():
    """Create a temp project with git + state."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    make_global_state(plet_dir, dep_map={"ITR_001": []}, lifecycles={"ITR_001": "implementing"})
    make_iter_state(
        plet_dir,
        "ITR_001",
        title="Add logging",
        criteria=[
            {
                "id": "AC_1",
                "description": "Logging works",
                "implementation": {"status": "not_started"},
                "verification": {"status": "not_started"},
            },
        ],
        attempts={"implement": 1, "verify": 0},
    )
    make_spec_artifacts(plet_dir)
    for name in ["progress.md", "learnings.md", "emergent.md"]:
        with open(os.path.join(plet_dir, name), "w") as f:
            f.write(f"# {name.replace('.md', '').title()}\n\n")
    return d, plet_dir


# ===========================================================================
# Auto-progress on update-criterion
# ===========================================================================


def test_update_criterion_generates_progress():
    """update-criterion should auto-append a progress entry."""
    print("\n## Auto-progress: update-criterion triggers progress")
    import shutil

    import iter_state

    d, plet_dir = _make_project()
    try:
        result = iter_state.cmd_update_criterion(
            [
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--criterion",
                "AC_1",
                "--phase",
                "implementation",
                "--status",
                "pass",
                "--evidence",
                "tests green",
                "--agent-id",
                "test_agent",
            ]
        )
        rc = result[0] if isinstance(result, tuple) else result
        check("update-criterion exits 0", rc == 0, f"result: {result}")

        # Read progress.md — should have an auto-generated entry
        progress_path = os.path.join(plet_dir, "progress.md")
        with open(progress_path) as f:
            content = f.read()

        check(
            "progress entry generated",
            "AC_1" in content,
            f"progress.md content: {content[:200]}",
        )
        check(
            "progress mentions pass",
            "pass" in content.lower(),
            f"progress.md content: {content[:200]}",
        )
    finally:
        shutil.rmtree(d)


def test_dry_run_does_not_generate_progress():
    """--dry-run should not generate a progress entry."""
    print("\n## Auto-progress: dry-run does not trigger")
    import shutil

    import iter_state

    d, plet_dir = _make_project()
    try:
        iter_state.cmd_update_criterion(
            [
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--criterion",
                "AC_1",
                "--phase",
                "implementation",
                "--status",
                "pass",
                "--evidence",
                "tests green",
                "--agent-id",
                "test_agent",
                "--dry-run",
            ]
        )

        progress_path = os.path.join(plet_dir, "progress.md")
        with open(progress_path) as f:
            content = f.read()

        check(
            "no progress entry on dry-run",
            "AC_1" not in content,
            f"progress.md should be empty but got: {content[:200]}",
        )
    finally:
        shutil.rmtree(d)


# ===========================================================================
# Summary
# ===========================================================================


def main():
    global passed, failed

    test_update_criterion_generates_progress()
    test_dry_run_does_not_generate_progress()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
