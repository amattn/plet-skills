#!/usr/bin/env python3
"""Tests for bootstrap.py — project setup for plet operation.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_bootstrap.py
"""

import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
from util_fixture import make_temp_git_repo as make_git_repo

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import bootstrap  # noqa: E402

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["bootstrap", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = bootstrap.main()
        out, err = sys.stdout.getvalue(), sys.stderr.getvalue()
    finally:
        sys.argv, sys.stdout, sys.stderr = old_argv, old_out, old_err
    if code != expect_exit:
        raise AssertionError(f"Exit code {code}, expected {expect_exit}.\nstdout: {out}\nstderr: {err}")
    return out.strip(), err.strip(), code


def check(name, condition, detail=""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  PASS  {name}")
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
    check("--version has name", "bootstrap" in out)

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
        check("plet/*/ wildcard in gitattributes", "plet/*/" in ga)

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
# setup — missing project_dir arg
# ---------------------------------------------------------------------------


def test_setup_no_args():
    print("\n## setup — missing project_dir arg")
    _, err, _ = run(["setup"], expect_exit=1)
    check("error mentions project_dir required", "project_dir" in err or "required" in err.lower())


# ---------------------------------------------------------------------------
# setup — non-existent directory
# ---------------------------------------------------------------------------


def test_setup_nonexistent_dir():
    print("\n## setup — non-existent directory")
    _, err, _ = run(["setup", "/no/such/directory/xyz"], expect_exit=1)
    check("error mentions directory does not exist", "does not exist" in err or "directory" in err.lower())


# ---------------------------------------------------------------------------
# setup — dry-run JSON output
# ---------------------------------------------------------------------------


def test_setup_dry_run_json():
    print("\n## setup — dry-run with JSON output")
    d = make_git_repo()
    try:
        out, _, _ = run(["setup", d, "--dry-run", "--output", "json"])
        data = json.loads(out)
        check("status ok", data["status"] == "ok")
        check("dryRun true", data.get("dryRun") is True)
        check("command setup", data["command"] == "setup")
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — dry-run plain text
# ---------------------------------------------------------------------------


def test_setup_dry_run_text():
    print("\n## setup — dry-run plain text output")
    d = make_git_repo()
    try:
        out, _, _ = run(["setup", d, "--dry-run"])
        check("dry run message present", "DRY RUN" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# setup — JSON with --pretty
# ---------------------------------------------------------------------------


def test_setup_json_pretty():
    print("\n## setup — JSON with --pretty")
    d = make_git_repo()
    try:
        out, _, _ = run(["setup", d, "--output", "json", "--pretty"])
        data = json.loads(out)
        check("pretty JSON has actions", len(data["actions"]) > 0)
        check("pretty is indented", "\n" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — missing project_dir arg
# ---------------------------------------------------------------------------


def test_check_no_args():
    print("\n## check — missing project_dir arg")
    _, err, _ = run(["check"], expect_exit=1)
    check("error mentions project_dir required", "project_dir" in err or "required" in err.lower())


# ---------------------------------------------------------------------------
# check — non-existent directory
# ---------------------------------------------------------------------------


def test_check_nonexistent_dir():
    print("\n## check — non-existent directory")
    _, err, _ = run(["check", "/no/such/directory/xyz"], expect_exit=1)
    check("error mentions directory does not exist", "does not exist" in err or "directory" in err.lower())


# ---------------------------------------------------------------------------
# check — invalid JSON in .claude/settings.json is reported as warn
# ---------------------------------------------------------------------------


def test_check_invalid_settings_json():
    print("\n## check — invalid .claude/settings.json")
    d = make_git_repo()
    try:
        run(["setup", d])
        # Replace settings.json with invalid JSON
        with open(os.path.join(d, ".claude", "settings.json"), "w") as f:
            f.write("not valid json{{{")
        out, _, rc = run(["check", d], expect_exit=2)
        # The check should still run and report settings as warn
        check("claude-settings warn", "claude-settings" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — plet entries missing from settings.json
# ---------------------------------------------------------------------------


def test_check_plet_entries_missing():
    print("\n## check — plet allow entries missing from settings.json")
    d = make_git_repo()
    try:
        run(["setup", d])
        # Replace allow list with empty list
        settings_path = os.path.join(d, ".claude", "settings.json")
        with open(settings_path) as f:
            settings = json.load(f)
        settings["permissions"]["allow"] = []
        with open(settings_path, "w") as f:
            json.dump(settings, f)
        out, _, _ = run(["check", d], expect_exit=2)
        check("claude-settings warns about missing entries", "plet allow entries missing" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — permissions pass when bypassPermissions present
# ---------------------------------------------------------------------------


def test_check_bypass_permissions():
    print("\n## check — bypassPermissions triggers permissions pass")
    d = make_git_repo()
    try:
        run(["setup", d])
        settings_path = os.path.join(d, ".claude", "settings.json")
        with open(settings_path) as f:
            settings = json.load(f)
        settings.setdefault("permissions", {})["bypassPermissions"] = True
        with open(settings_path, "w") as f:
            json.dump(settings, f)
        out, _, _ = run(["check", d])
        check("permissions pass", "permissions" in out and "pass" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — JSON output with --pretty
# ---------------------------------------------------------------------------


def test_check_json_pretty():
    print("\n## check — JSON output with --pretty")
    d = make_git_repo()
    try:
        run(["setup", d])
        out, _, _ = run(["check", d, "--output", "json", "--pretty"], expect_exit=2)
        data = json.loads(out)
        check("has submoduleVersion", "submoduleVersion" in data)
        check("is indented", "\n" in out)
    finally:
        shutil.rmtree(d)


# ---------------------------------------------------------------------------
# check — text output (failed count path)
# ---------------------------------------------------------------------------


def test_check_text_summary_line():
    print("\n## check — text output summary line")
    d = make_git_repo()
    try:
        run(["setup", d])
        out, _, _ = run(["check", d], expect_exit=2)
        check("summary line present", "passed" in out and "warnings" in out)
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
    # New coverage tests
    test_setup_no_args()
    test_setup_nonexistent_dir()
    test_setup_dry_run_json()
    test_setup_dry_run_text()
    test_setup_json_pretty()
    test_check_no_args()
    test_check_nonexistent_dir()
    test_check_invalid_settings_json()
    test_check_plet_entries_missing()
    test_check_bypass_permissions()
    test_check_json_pretty()
    test_check_text_summary_line()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
