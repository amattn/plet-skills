#!/usr/bin/env python3
"""Tests for plet_tools.py churn command (RFT_1).

Churn analysis: files by commit count since workstream start.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
sys.path.insert(0, os.path.dirname(__file__))

from util_fixture import make_git_repo, make_global_state  # noqa: E402

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


def _make_churny_repo():
    """Create a repo with known file churn patterns.

    Commit history after workstream creation:
      - file_hot.py: 5 commits (outlier)
      - file_warm.py: 3 commits
      - file_cold.py: 1 commit
      - plet/state.json: touched but should be excludable
    """
    d = tempfile.mkdtemp()
    make_git_repo(d)
    plet_dir = os.path.join(d, "plet")
    os.makedirs(os.path.join(plet_dir, "state"), exist_ok=True)
    make_global_state(
        plet_dir,
        loop_session=1,
        session_history=[
            {
                "type": "loop",
                "session": 1,
                "branch": "plet/TEST/loop1/workstream",
                "startedAt": "2026-04-01T00:00:00Z",
                "endedAt": None,
            }
        ],
    )
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "initial state"], capture_output=True)

    # Create workstream branch
    subprocess.run(["git", "-C", d, "checkout", "-b", "plet/TEST/loop1/workstream"], capture_output=True)

    # file_hot.py: 5 commits
    for i in range(5):
        with open(os.path.join(d, "file_hot.py"), "w") as f:
            f.write(f"# version {i}\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", f"hot change {i}"], capture_output=True)

    # file_warm.py: 3 commits
    for i in range(3):
        with open(os.path.join(d, "file_warm.py"), "w") as f:
            f.write(f"# version {i}\n")
        subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
        subprocess.run(["git", "-C", d, "commit", "-m", f"warm change {i}"], capture_output=True)

    # file_cold.py: 1 commit
    with open(os.path.join(d, "file_cold.py"), "w") as f:
        f.write("# cold\n")
    # file_cold2.py: 1 commit (same commit)
    with open(os.path.join(d, "file_cold2.py"), "w") as f:
        f.write("# cold2\n")
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "cold change"], capture_output=True)

    # file_cold3.py: 1 commit
    with open(os.path.join(d, "file_cold3.py"), "w") as f:
        f.write("# cold3\n")
    subprocess.run(["git", "-C", d, "add", "-A"], capture_output=True)
    subprocess.run(["git", "-C", d, "commit", "-m", "cold3 change"], capture_output=True)

    return d, plet_dir


# ===========================================================================
# Tests
# ===========================================================================


def test_churn_text_output():
    """churn command shows files sorted by commit count."""
    print("\n## churn — text output")
    import shutil

    import git_check

    d, plet_dir = _make_churny_repo()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = git_check.cmd_churn([plet_dir])
            rc = result[0] if isinstance(result, tuple) else result
            out = result[1] if isinstance(result, tuple) else ""
            check("exits 0", rc == 0, f"rc={rc}, out={out}")
            check("file_hot.py in output", "file_hot.py" in out, f"out: {out[:200]}")
            # hot should be before warm in sorted output
            if "file_hot.py" in out and "file_warm.py" in out:
                check("hot before warm", out.index("file_hot.py") < out.index("file_warm.py"))
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_churn_json_output():
    """churn with --output json returns structured data."""
    print("\n## churn — JSON output")
    import shutil

    import git_check

    d, plet_dir = _make_churny_repo()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = git_check.cmd_churn([plet_dir, "--output", "json"])
            rc = result[0] if isinstance(result, tuple) else result
            out = result[1] if isinstance(result, tuple) else ""
            check("exits 0", rc == 0, f"rc={rc}")
            data = json.loads(out)
            check("has files", "files" in data, f"keys: {list(data.keys())}")
            files = data.get("files", [])
            check("has entries", len(files) >= 3, f"got {len(files)}")
            # First file should be the hottest
            if files:
                check("hottest is file_hot.py", files[0]["path"] == "file_hot.py", f"got: {files[0].get('path')}")
                check("has commits count", files[0].get("commits", 0) == 5, f"got: {files[0].get('commits')}")
                check("has outlier flag", "outlier" in files[0], f"keys: {list(files[0].keys())}")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_churn_outlier_detection():
    """Files with > 2x median commit count are flagged as outliers."""
    print("\n## churn — outlier detection")
    import shutil

    import git_check

    d, plet_dir = _make_churny_repo()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = git_check.cmd_churn([plet_dir, "--output", "json"])
            out = result[1] if isinstance(result, tuple) else ""
            data = json.loads(out)
            files = data.get("files", [])
            hot = next((f for f in files if f["path"] == "file_hot.py"), None)
            cold = next((f for f in files if f["path"] == "file_cold.py"), None)
            if hot:
                check("hot is outlier", hot.get("outlier") is True, f"got: {hot.get('outlier')}")
            if cold:
                check("cold is not outlier", cold.get("outlier") is False, f"got: {cold.get('outlier')}")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_churn_top_limit():
    """--top limits the number of results."""
    print("\n## churn — --top limit")
    import shutil

    import git_check

    d, plet_dir = _make_churny_repo()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            result = git_check.cmd_churn([plet_dir, "--top", "2", "--output", "json"])
            out = result[1] if isinstance(result, tuple) else ""
            data = json.loads(out)
            files = data.get("files", [])
            check("limited to 2", len(files) == 2, f"got {len(files)}")
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


def test_churn_help():
    """churn --help exits 0."""
    print("\n## churn — help")
    import git_check

    result = git_check.cmd_churn(["--help"])
    rc = result[0] if isinstance(result, tuple) else result
    check("help exits 0", rc == 0)


def test_churn_via_plet_tools():
    """churn is accessible via plet_tools.py dispatch."""
    print("\n## churn — via plet_tools.py")
    import shutil

    import plet_tools

    d, plet_dir = _make_churny_repo()
    try:
        old_cwd = os.getcwd()
        os.chdir(d)
        try:
            import io

            old_out, old_err = sys.stdout, sys.stderr
            sys.argv = ["plet_tools", "--no-log", "churn", plet_dir, "--output", "json"]
            sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
            try:
                rc = plet_tools.main()
                out = sys.stdout.getvalue()
            finally:
                sys.stdout, sys.stderr = old_out, old_err
            check("exits 0 via tools", rc == 0, f"rc={rc}")
            data = json.loads(out)
            check("has files via tools", "files" in data)
        finally:
            os.chdir(old_cwd)
    finally:
        shutil.rmtree(d)


# ===========================================================================
# Summary
# ===========================================================================


def main():
    global passed, failed

    test_churn_help()
    test_churn_text_output()
    test_churn_json_output()
    test_churn_outlier_detection()
    test_churn_top_limit()
    test_churn_via_plet_tools()

    print(f"\n{passed + failed} tests: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
