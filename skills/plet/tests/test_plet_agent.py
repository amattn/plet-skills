#!/usr/bin/env python3
"""Tests for plet_agent.py — the agent's unified CLI entry point.

Tests dispatch, --help, --usage, and --version for all 6 commands.
Delegates to real module functions — tested via subprocess to prove
the CLI interface works end-to-end.
"""

import io
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import plet_agent  # noqa: E402
from util_fixture import make_git_repo, make_global_state, make_iter_state, make_spec_artifacts  # noqa: E402
from util_io import iter_state_path, load_json  # noqa: E402

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_agent.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["plet_agent", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = plet_agent.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def run_subprocess(args, expect_exit=0, cwd=None):
    """Run via subprocess for CLI integration."""
    result = subprocess.run(
        [sys.executable, TOOL, "--no-log"] + args,
        capture_output=True,
        text=True,
        cwd=cwd,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            f"Exit code {result.returncode}, expected {expect_exit}.\n"
            f"stdout: {result.stdout[:500]}\nstderr: {result.stderr[:500]}"
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


def _make_project():
    """Create a temp project with git + state for testing."""
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    os.makedirs(os.path.join(plet_dir, "trace"), exist_ok=True)
    make_global_state(plet_dir, dep_map={"ITR_001": []}, lifecycles={"ITR_001": "implementing"})
    make_iter_state(
        plet_dir,
        "ITR_001",
        criteria=[
            {
                "id": "AC_1",
                "description": "Test criterion",
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
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "initial"], capture_output=True)
    return d, plet_dir


# ===========================================================================
# --help, --version, and command dispatch
# ===========================================================================


def test_help_and_version():
    print("\n## --help and --version")
    out, _, _ = run(["--help"])
    check("--help exits 0", True)
    check("--help has content", len(out) > 20)
    check("--help lists commands", "update-criterion" in out and "phase-end" in out)

    out, _, _ = run(["--version"])
    check("--version has name", "plet_agent" in out)
    check("--version has version", "0.2.0" in out)


def test_command_help():
    """Each command supports --help."""
    print("\n## Command --help")
    for cmd in ["update-criterion", "wip-commit", "add-learning", "add-emergent", "phase-end"]:
        out, _, _ = run([cmd, "--help"])
        check(f"{cmd} --help exits 0", True)
        check(f"{cmd} --help has content", len(out) > 10, f"got: {out[:50]}")


def test_unknown_command():
    print("\n## Unknown command")
    out, err, _ = run(["nonexistent"], expect_exit=1)
    check("unknown command exits 1", True)
    check("error mentions unknown", "unknown" in err.lower() or "unknown" in out.lower())


# ===========================================================================
# Dispatch to real modules
# ===========================================================================


def test_update_criterion_dispatches():
    """update-criterion delegates to iter_state.cmd_update_criterion."""
    print("\n## update-criterion dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(
            [
                "update-criterion",
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
        check("update-criterion exits 0", rc == 0, f"err: {err}")
        # Verify state was updated
        ist = load_json(iter_state_path(plet_dir, "ITR_001"))
        ac1 = ist["criteria"][0] if ist and ist.get("criteria") else {}
        check(
            "AC_1 updated",
            ac1.get("implementation", {}).get("status") == "pass",
            f"got: {ac1}",
        )
    finally:
        shutil.rmtree(d)


def test_wip_commit_dispatches():
    """wip-commit delegates to git_ops.cmd_wip_commit."""
    print("\n## wip-commit dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        # Create a file to commit
        with open(os.path.join(d, "work.txt"), "w") as f:
            f.write("work\n")
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            out, err, rc = run(
                [
                    "wip-commit",
                    plet_dir,
                    "--iter-id",
                    "ITR_001",
                    "--message",
                    "AC_1 tests pass",
                ]
            )
            check("wip-commit exits 0", rc == 0, f"err: {err}")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_add_learning_dispatches():
    """add-learning delegates to entries.cmd_add_learning."""
    print("\n## add-learning dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(
            [
                "add-learning",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--category",
                "pattern",
                "--title",
                "Test learning",
                "--content",
                "Learned something useful",
            ]
        )
        check("add-learning exits 0", rc == 0, f"err: {err}")
        with open(os.path.join(plet_dir, "learnings.md")) as f:
            learnings = f.read()
        check("learning appended", "Learned something useful" in learnings)
    finally:
        shutil.rmtree(d)


def test_add_emergent_dispatches():
    """add-emergent delegates to entries.cmd_add_emergent."""
    print("\n## add-emergent dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        out, err, rc = run(
            [
                "add-emergent",
                plet_dir,
                "--iter-id",
                "ITR_001",
                "--iter-title",
                "Test",
                "--phase",
                "implement",
                "--attempt",
                "1",
                "--category",
                "design decision",
                "--title",
                "Edge case",
                "--content",
                "Edge case discovered",
            ]
        )
        check("add-emergent exits 0", rc == 0, f"err: {err}")
        with open(os.path.join(plet_dir, "emergent.md")) as f:
            emergent = f.read()
        check("emergent appended", "Edge case discovered" in emergent)
    finally:
        shutil.rmtree(d)


def test_phase_end_dispatches():
    """phase-end delegates to phase.cmd_end."""
    print("\n## phase-end dispatch")
    import shutil

    d, plet_dir = _make_project()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            out, err, rc = run(
                [
                    "phase-end",
                    plet_dir,
                    "--iter-id",
                    "ITR_001",
                    "--phase",
                    "implement",
                    "--verdict",
                    "completed",
                    "--progress-content",
                    "All criteria implemented and tests passing.",
                ]
            )
            check("phase-end exits 0", rc == 0, f"err: {err}")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_subprocess_dispatch():
    """Verify the script works via subprocess (not just direct import)."""
    print("\n## Subprocess dispatch")
    out, err, rc = run_subprocess(["--help"])
    check("subprocess --help exits 0", rc == 0)
    check("subprocess has commands", "update-criterion" in out)


# ===========================================================================
# Auto-activity and trace emit (coverage for _auto_update_activity, _emit_trace_event)
# ===========================================================================


def test_emit_trace_event_with_env():
    """_emit_trace_event writes events when PLET env vars are set."""
    print("\n## _emit_trace_event with env")
    import json
    import shutil

    from util_io import events_path

    d, plet_dir = _make_project()
    try:
        old_env = {}
        env_vars = {
            "PLET_DIR": plet_dir,
            "PLET_ITER_ID": "ITR_001",
            "PLET_PHASE": "implement",
            "PLET_ATTEMPT": "1",
        }
        for k, v in env_vars.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            plet_agent._emit_trace_event("cli_entry", "update-criterion")
            plet_agent._emit_trace_event("cli_exit", "update-criterion", exit_code=0)

            path = events_path(plet_dir, "ITR_001", "implement", 1)
            check("trace file created", os.path.isfile(path), f"path: {path}")
            if os.path.isfile(path):
                with open(path) as f:
                    events = [json.loads(ln) for ln in f if ln.strip()]
                check("2 events", len(events) == 2, f"got {len(events)}")
                check("entry type", events[0].get("type") == "cli_entry")
                check("exit type", events[1].get("type") == "cli_exit")
                check("exit has exitCode", events[1].get("data", {}).get("exitCode") == 0)
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    finally:
        shutil.rmtree(d)


def test_emit_trace_event_no_env():
    """_emit_trace_event silently skips when env vars missing."""
    print("\n## _emit_trace_event without env")
    old_dir = os.environ.pop("PLET_DIR", None)
    old_id = os.environ.pop("PLET_ITER_ID", None)
    try:
        # Should not raise
        plet_agent._emit_trace_event("cli_entry", "test")
        check("no crash without env", True)
    finally:
        if old_dir is not None:
            os.environ["PLET_DIR"] = old_dir
        if old_id is not None:
            os.environ["PLET_ITER_ID"] = old_id


def test_auto_update_activity_criterion():
    """_auto_update_activity updates phaseActivity for update-criterion."""
    print("\n## _auto_update_activity for update-criterion")
    import shutil

    d, plet_dir = _make_project()
    try:
        old_env = {}
        env_vars = {
            "PLET_DIR": plet_dir,
            "PLET_ITER_ID": "ITR_001",
            "PLET_AGENT_ID": "test_agent",
        }
        for k, v in env_vars.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            plet_agent._auto_update_activity(
                "update-criterion",
                [
                    "update-criterion",
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
                ],
            )
            ist = load_json(iter_state_path(plet_dir, "ITR_001"))
            check(
                "phaseActivity updated",
                ist.get("phaseActivity") == "running_checks",
                f"got: {ist.get('phaseActivity')}",
            )
            check(
                "activityDetail has AC_1",
                "AC_1" in (ist.get("activityDetail") or ""),
                f"got: {ist.get('activityDetail')}",
            )
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    finally:
        shutil.rmtree(d)


def test_auto_update_activity_wip_commit():
    """_auto_update_activity updates for wip-commit."""
    print("\n## _auto_update_activity for wip-commit")
    import shutil

    d, plet_dir = _make_project()
    try:
        old_env = {}
        env_vars = {
            "PLET_DIR": plet_dir,
            "PLET_ITER_ID": "ITR_001",
            "PLET_AGENT_ID": "test_agent",
        }
        for k, v in env_vars.items():
            old_env[k] = os.environ.get(k)
            os.environ[k] = v
        try:
            plet_agent._auto_update_activity(
                "wip-commit",
                ["wip-commit", plet_dir, "--iter-id", "ITR_001", "--message", "AC_1 done"],
            )
            ist = load_json(iter_state_path(plet_dir, "ITR_001"))
            check(
                "phaseActivity is committing",
                ist.get("phaseActivity") == "committing",
                f"got: {ist.get('phaseActivity')}",
            )
            check(
                "activityDetail has message",
                "AC_1 done" in (ist.get("activityDetail") or ""),
                f"got: {ist.get('activityDetail')}",
            )
        finally:
            for k, v in old_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
    finally:
        shutil.rmtree(d)


def test_auto_update_activity_no_env():
    """_auto_update_activity silently skips without env vars."""
    print("\n## _auto_update_activity without env")
    old_dir = os.environ.pop("PLET_DIR", None)
    old_id = os.environ.pop("PLET_ITER_ID", None)
    old_agent = os.environ.pop("PLET_AGENT_ID", None)
    try:
        plet_agent._auto_update_activity("update-criterion", ["update-criterion", "plet/"])
        check("no crash without env", True)
    finally:
        if old_dir is not None:
            os.environ["PLET_DIR"] = old_dir
        if old_id is not None:
            os.environ["PLET_ITER_ID"] = old_id
        if old_agent is not None:
            os.environ["PLET_AGENT_ID"] = old_agent


def test_auto_update_activity_unmapped_command():
    """_auto_update_activity skips for commands not in the mapping."""
    print("\n## _auto_update_activity for unmapped command")
    os.environ["PLET_DIR"] = "/tmp"
    os.environ["PLET_ITER_ID"] = "ITR_001"
    os.environ["PLET_AGENT_ID"] = "test"
    try:
        plet_agent._auto_update_activity("add-learning", ["add-learning", "plet/"])
        check("unmapped command skips silently", True)
    finally:
        os.environ.pop("PLET_DIR", None)
        os.environ.pop("PLET_ITER_ID", None)
        os.environ.pop("PLET_AGENT_ID", None)


# ===========================================================================
# Summary
# ===========================================================================


def main():
    global passed, failed

    test_help_and_version()
    test_command_help()
    test_unknown_command()
    test_update_criterion_dispatches()
    test_wip_commit_dispatches()
    test_add_learning_dispatches()
    test_add_emergent_dispatches()
    test_phase_end_dispatches()
    test_subprocess_dispatch()

    # Coverage for auto-activity and trace emit
    test_emit_trace_event_with_env()
    test_emit_trace_event_no_env()
    test_auto_update_activity_criterion()
    test_auto_update_activity_wip_commit()
    test_auto_update_activity_no_env()
    test_auto_update_activity_unmapped_command()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
