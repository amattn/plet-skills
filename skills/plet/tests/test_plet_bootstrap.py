#!/usr/bin/env python3
"""Tests for plet_bootstrap.py — project setup for plet operation.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_bootstrap.py
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from util_fixture import make_temp_git_repo as make_git_repo

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_bootstrap.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True,
        text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Expected exit {}, got {}.\nstdout: {}\nstderr: {}".format(
                expect_exit, result.returncode, result.stdout, result.stderr
            )
        )
    return result.stdout.strip(), result.stderr.strip(), result.returncode


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print("  PASS  {}".format(name))
    else:
        failed += 1
        print("  FAIL  {}{}".format(name, ": " + detail if detail else ""))


# ---------------------------------------------------------------------------
# help + version
# ---------------------------------------------------------------------------


def test_help():
    print("\n## --help and --version")
    out, _, _ = run(["--help"])
    check("--help exits 0", True)
    check("--help has content", len(out) > 20)

    out, _, _ = run(["--version"])
    check("--version has name", "plet_bootstrap" in out)

    run(["setup", "--help"])
    check("setup --help exits 0", True)

    run(["check", "--help"])
    check("check --help exits 0", True)


# ---------------------------------------------------------------------------
# setup — basic
# ---------------------------------------------------------------------------


def test_setup_fresh():
    print("\n## setup — fresh project")
    d = make_git_repo()
    try:
        out, _, _ = run(["setup", d])
        check("exits 0", True)
        check("created in output", "created" in out)

        # .plet/ exists
        check(".plet/ exists", os.path.isdir(os.path.join(d, ".plet")))

        # .gitignore has entries
        with open(os.path.join(d, ".gitignore")) as f:
            gi = f.read()
        check(".plet/ in gitignore", ".plet/" in gi)
        check("settings.local.json in gitignore", ".claude/settings.local.json" in gi)
        check("CLAUDE.local.md in gitignore", "CLAUDE.local.md" in gi)

        # .gitattributes has merge driver
        with open(os.path.join(d, ".gitattributes")) as f:
            ga = f.read()
        check("plet-append in gitattributes", "plet-append" in ga)
        check("progress.md in gitattributes", "progress.md" in ga)

        # merge driver configured
        result = subprocess.run(
            ["git", "-C", d, "config", "--get", "merge.plet-append.driver"], capture_output=True, text=True
        )
        check("merge driver in git config", result.returncode == 0)

        # CLAUDE.md created
        check("CLAUDE.md exists", os.path.isfile(os.path.join(d, "CLAUDE.md")))
        with open(os.path.join(d, "CLAUDE.md")) as f:
            claude_md = f.read()
        check("CLAUDE.md has script discovery", "PLET_SCRIPTS_DIR" in claude_md)

        # .claude/settings.json has allow entries
        with open(os.path.join(d, ".claude", "settings.json")) as f:
            settings = json.load(f)
        allow = settings.get("permissions", {}).get("allow", [])
        check("allow has plet entry", any("plet_" in e for e in allow))
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — idempotent
# ---------------------------------------------------------------------------


def test_setup_idempotent():
    print("\n## setup — idempotent (second run skips)")
    d = make_git_repo()
    try:
        run(["setup", d])
        out, _, _ = run(["setup", d])
        check("all skipped", "0 created, 0 configured" in out)
        check("6 skipped", "6 skipped" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — CLAUDE.md not overwritten
# ---------------------------------------------------------------------------


def test_claude_md_not_overwritten():
    print("\n## setup — CLAUDE.md not overwritten")
    d = make_git_repo()
    try:
        custom = os.path.join(d, "CLAUDE.md")
        with open(custom, "w") as f:
            f.write("# My custom CLAUDE.md\n")
        run(["setup", d])
        with open(custom) as f:
            content = f.read()
        check("custom content preserved", "My custom CLAUDE.md" in content)
        check("plet stub NOT injected", "PLET_SCRIPTS_DIR" not in content)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — .claude/settings.json merges, not overwrites
# ---------------------------------------------------------------------------


def test_settings_merge():
    print("\n## setup — .claude/settings.json merges existing entries")
    d = make_git_repo()
    try:
        claude_dir = os.path.join(d, ".claude")
        os.makedirs(claude_dir)
        settings = {"permissions": {"allow": ["Bash(npm *)"], "defaultMode": "auto"}, "sandbox": {"enabled": True}}
        with open(os.path.join(claude_dir, "settings.json"), "w") as f:
            json.dump(settings, f)

        run(["setup", d])

        with open(os.path.join(claude_dir, "settings.json")) as f:
            result = json.load(f)

        allow = result.get("permissions", {}).get("allow", [])
        check("npm entry preserved", "Bash(npm *)" in allow)
        check("plet entry added", any("plet_" in e for e in allow))
        check("defaultMode preserved", result["permissions"]["defaultMode"] == "auto")
        check("sandbox preserved", result["sandbox"]["enabled"] is True)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — malformed settings.json
# ---------------------------------------------------------------------------


def test_settings_malformed():
    print("\n## setup — malformed .claude/settings.json")
    d = make_git_repo()
    try:
        claude_dir = os.path.join(d, ".claude")
        os.makedirs(claude_dir)
        with open(os.path.join(claude_dir, "settings.json"), "w") as f:
            f.write("not json {{{")

        out, _, _ = run(["setup", d], expect_exit=1)
        check("reports error", "error" in out.lower() or "invalid" in out.lower())
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — not a git repo
# ---------------------------------------------------------------------------


def test_setup_no_git():
    print("\n## setup — not a git repo")
    d = tempfile.mkdtemp()
    try:
        _, err, _ = run(["setup", d], expect_exit=1)
        check("error mentions git", "git" in err.lower())
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — JSON output
# ---------------------------------------------------------------------------


def test_setup_json():
    print("\n## setup — JSON output")
    d = make_git_repo()
    try:
        out, _, _ = run(["setup", d, "--output", "json"])
        data = json.loads(out)
        check("status ok", data["status"] in ("ok", "warn"))
        check("has actions", len(data["actions"]) > 0)
        check("has summary", "created" in data["summary"])
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — fresh (all warnings)
# ---------------------------------------------------------------------------


def test_check_fresh():
    print("\n## check — fresh project (warnings)")
    d = make_git_repo()
    try:
        out, _, rc = run(["check", d], expect_exit=2)
        check("exit 2 (warnings)", rc == 2)
        check("plet-dir warn", "plet-dir" in out and "warn" in out)
        check("gitignore warn", "gitignore" in out and "warn" in out)
        check("git-repo pass", "git-repo" in out and "pass" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — after setup (all pass except permissions)
# ---------------------------------------------------------------------------


def test_check_after_setup():
    print("\n## check — after setup (mostly pass)")
    d = make_git_repo()
    try:
        run(["setup", d])
        out, _, _ = run(["check", d], expect_exit=2)  # permissions warning
        check("plet-dir pass", "plet-dir" in out and "pass" in out)
        check("gitignore pass", "gitignore" in out and "pass" in out)
        check("merge-driver pass", "merge-driver" in out and "pass" in out)
        check("gitattributes pass", "gitattributes" in out and "pass" in out)
        check("claude-md pass", "claude-md" in out and "pass" in out)
        check("claude-settings pass", "claude-settings" in out and "pass" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — JSON output
# ---------------------------------------------------------------------------


def test_check_json():
    print("\n## check — JSON output")
    d = make_git_repo()
    try:
        run(["setup", d])
        out, _, _ = run(["check", d, "--output", "json"], expect_exit=2)
        data = json.loads(out)
        check("has checks", len(data["checks"]) > 0)
        check("has summary", "passed" in data["summary"])
        check("passed > 0", data["summary"]["passed"] > 0)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — not a git repo
# ---------------------------------------------------------------------------


def test_check_no_git():
    print("\n## check — not a git repo")
    d = tempfile.mkdtemp()
    try:
        out, _, rc = run(["check", d], expect_exit=2)
        check("git-repo warn", "git-repo" in out and "warn" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# gitignore — doesn't add plet/
# ---------------------------------------------------------------------------


def test_gitignore_no_plet():
    print("\n## gitignore — does NOT add plet/")
    d = make_git_repo()
    try:
        run(["setup", d])
        with open(os.path.join(d, ".gitignore")) as f:
            content = f.read()
        lines = [ln.strip() for ln in content.split("\n") if ln.strip() and not ln.startswith("#")]
        check(".plet/ present", ".plet/" in lines)
        check("plet/ NOT present", "plet/" not in lines)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    test_help()
    test_setup_fresh()
    test_setup_idempotent()
    test_claude_md_not_overwritten()
    test_settings_merge()
    test_settings_malformed()
    test_setup_no_git()
    test_setup_json()
    test_check_fresh()
    test_check_after_setup()
    test_check_json()
    test_check_no_git()
    test_gitignore_no_plet()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
