#!/usr/bin/env python3
"""Tests for plet_fingerprint.py — fingerprint generation, embedding, and staleness detection.

Zero dependencies beyond stdlib. Run with:
    python3 skills/plet/tests/test_plet_fingerprint.py

Creates temp fixtures, runs commands via subprocess, validates output, cleans up.
"""

import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from util_io import (state_json_path, requirements_path, iterations_path)

TOOL = os.path.join(os.path.dirname(__file__), "..", "scripts", "plet_fingerprint.py")

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run plet_fingerprint.py with args, return (stdout, stderr, exit_code)."""
    result = subprocess.run(
        [sys.executable, TOOL] + args,
        capture_output=True, text=True,
    )
    if result.returncode != expect_exit:
        raise AssertionError(
            "Expected exit {}, got {}\n"
            "  args: {}\n"
            "  stdout: {}\n"
            "  stderr: {}".format(
                expect_exit, result.returncode, args,
                result.stdout, result.stderr,
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
        msg = "  FAIL  {}".format(name)
        if detail:
            msg += ": {}".format(detail)
        print(msg)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------

REQUIREMENTS_MD = """# Product Requirements Document

## 1. Overview

A test project.

## 3. Functional Requirements

### 3.1 Core (FR)

| ID | Requirement | Priority |
|----|-------------|----------|
| FR_1 | First requirement | P0 |
| FR_2 | Second requirement | P0 |
| FR_3 | Third requirement | P1 |

### 3.2 Non-Functional (NF)

| ID | Requirement | Priority |
|----|-------------|----------|
| NF_1 | Performance | P0 |
| NF_2 | Reliability | P1 |

## 5. Developer Experience (DX)

| ID | Requirement | Priority |
|----|-------------|----------|
| DX_1 | Good error messages | P0 |

## 9. Release Milestones

| ID | Name |
|----|------|
| MS_1 | MVP |
| MS_2 | Beta |

## 13. Future Considerations

| # | Area | Description |
|---|------|-------------|
| FC_1 | Should be excluded | Future stuff |
| DX_99 | Also excluded | Not a real req |

### Open Questions

| # | Question |
|---|----------|
| NF_99 | Should also be excluded |
"""

ITERATIONS_MD = """# Iterations

### ID_001: Project scaffolding

**Milestone:** MS_1
**Dependencies:** none
**Requirements:** FR_1

### ID_002: Core functionality

**Milestone:** MS_1
**Dependencies:** ID_001
**Requirements:** FR_2, FR_3

### ID_003: Beta features

**Milestone:** MS_2
**Dependencies:** ID_001, ID_002
**Requirements:** NF_1, NF_2

## Withdrawn

### ID_004: Removed feature

**Milestone:** MS_2
**Dependencies:** none
**Requirements:** DX_1
"""

STATE_JSON = {
    "schemaVersion": "0.1.0",
    "lastUpdated": "2026-03-07T14:30:00Z",
}


def make_artifacts(tmpdir):
    """Create minimal plan artifacts in tmpdir."""
    with open(requirements_path(tmpdir), "w") as f:
        f.write(REQUIREMENTS_MD)
    with open(iterations_path(tmpdir), "w") as f:
        f.write(ITERATIONS_MD)
    with open(state_json_path(tmpdir), "w") as f:
        json.dump(STATE_JSON, f, indent=2)
        f.write("\n")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_help_all_commands():
    print("\n## Help on every command")

    stdout, _, _ = run(["--help"])
    check("top-level help exits 0", True)
    check("top-level mentions extract", "extract" in stdout)
    check("top-level mentions embed", "embed" in stdout)
    check("top-level mentions check", "check" in stdout)

    for cmd in ["extract", "embed", "check"]:
        stdout, _, _ = run([cmd, "--help"])
        check("{} --help exits 0".format(cmd), True)
        check("{} help has content".format(cmd), len(stdout) > 50)
        check("{} help has IMPORTANT".format(cmd), "IMPORTANT" in stdout)
        check("{} help has PITFALLS".format(cmd), "PITFALLS" in stdout)
        check("{} help has PURPOSE".format(cmd), "PURPOSE" in stdout)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "plet_fingerprint" in stdout and "0.1.0" in stdout)


def test_extract_requirements():
    print("\n## Extract requirements fingerprint")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "requirements"])
        fp = json.loads(stdout)

        check("has lastNonTrivialUpdate", "lastNonTrivialUpdate" in fp)
        check("has milestones", fp["milestones"] == ["MS_1", "MS_2"])
        check("has FR group", fp["requirements"]["FR"] == ["FR_1", "FR_2", "FR_3"])
        check("has NF group", fp["requirements"]["NF"] == ["NF_1", "NF_2"])
        check("has DX group", fp["requirements"]["DX"] == ["DX_1"])
        check("no FC group (excluded)", "FC" not in fp["requirements"],
              "FC was: {}".format(fp["requirements"].get("FC")))
        check("DX_99 excluded (Future Considerations)", "DX_99" not in fp["requirements"].get("DX", []))
        check("NF_99 excluded (Open Questions)", "NF_99" not in fp["requirements"].get("NF", []))
        check("MS_ not in requirements", "MS" not in fp["requirements"])
        check("ID_ not in requirements", "ID" not in fp["requirements"])


def test_extract_iterations():
    print("\n## Extract iterations fingerprint")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "iterations"])
        fp = json.loads(stdout)

        check("has lastNonTrivialUpdate", "lastNonTrivialUpdate" in fp)
        check("MS_1 has ID_001, ID_002",
              fp["iterations"]["MS_1"] == ["ID_001", "ID_002"])
        check("MS_2 has ID_003 only",
              fp["iterations"]["MS_2"] == ["ID_003"])
        check("ID_004 excluded (withdrawn)",
              "ID_004" not in fp["iterations"].get("MS_2", []))


def test_extract_json_output():
    print("\n## Extract JSON output mode")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "requirements",
                            "--output", "json", "--pretty"])
        data = json.loads(stdout)

        check("status ok", data["status"] == "ok")
        check("command extract", data["command"] == "extract")
        check("type requirements", data["type"] == "requirements")
        check("has path", "path" in data)
        check("has fingerprint", "fingerprint" in data)
        check("has scriptVersion", "scriptVersion" in data)
        check("has timestamp", "timestamp" in data)


def test_extract_fields_filter():
    print("\n## Extract --fields filter")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "requirements",
                            "--output", "json", "--fields", "status,fingerprint"])
        data = json.loads(stdout)

        check("has status", "status" in data)
        check("has fingerprint", "fingerprint" in data)
        check("has fieldsIncluded", "fieldsIncluded" in data)


def test_embed_requirements():
    print("\n## Embed requirements fingerprint")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["embed", d, "--type", "requirements", "--bump"])
        check("success message", "OK" in stdout and "requirements" in stdout)
        check("force-bumped", "force-bumped" in stdout)

        # Verify fingerprint block was written
        with open(requirements_path(d)) as f:
            content = f.read()
        check("has fingerprint marker", "<!-- plet:fingerprint -->" in content)

        # Re-extract and verify it matches
        stdout2, _, _ = run(["extract", d, "--type", "requirements"])
        fp = json.loads(stdout2)
        check("extract after embed has FR", "FR" in fp["requirements"])


def test_embed_chain():
    print("\n## Embed full chain (requirements → iterations → state)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # Embed all three
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        run(["embed", d, "--type", "state"])

        # Check should pass
        stdout, _, _ = run(["check", d])
        check("all consistent after embed chain", "all fingerprints consistent" in stdout)


def test_embed_auto_bump():
    print("\n## Embed auto-bump on ID change")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # First embed (no previous — uses default timestamp)
        run(["embed", d, "--type", "requirements"])

        # Get the timestamp
        stdout1, _, _ = run(["extract", d, "--type", "requirements"])
        fp1 = json.loads(stdout1)
        ts1 = fp1["lastNonTrivialUpdate"]

        # Add a new requirement
        req_path = requirements_path(d)
        with open(req_path) as f:
            content = f.read()
        content = content.replace(
            "| FR_3 | Third requirement | P1 |",
            "| FR_3 | Third requirement | P1 |\n| FR_4 | New requirement | P0 |",
        )
        with open(req_path, "w") as f:
            f.write(content)

        # Embed again — should auto-bump
        import time
        time.sleep(1)  # ensure timestamp differs
        stdout2, _, _ = run(["embed", d, "--type", "requirements",
                             "--output", "json"])
        data = json.loads(stdout2)

        check("autoBumped is true", data["autoBumped"] is True)
        check("forceBumped is false", data["forceBumped"] is False)
        check("timestamp changed", data["fingerprint"]["lastNonTrivialUpdate"] != ts1)


def test_embed_no_bump_when_unchanged():
    print("\n## Embed preserves timestamp when IDs unchanged")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # First embed
        run(["embed", d, "--type", "requirements", "--bump"])
        stdout1, _, _ = run(["extract", d, "--type", "requirements"])
        ts1 = json.loads(stdout1)["lastNonTrivialUpdate"]

        # Second embed — no changes
        import time
        time.sleep(1)
        stdout2, _, _ = run(["embed", d, "--type", "requirements",
                             "--output", "json"])
        data = json.loads(stdout2)

        check("autoBumped is false", data["autoBumped"] is False)
        check("forceBumped is false", data["forceBumped"] is False)
        check("timestamp preserved", data["fingerprint"]["lastNonTrivialUpdate"] == ts1)


def test_embed_dry_run():
    print("\n## Embed --dry-run")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # Read original content
        with open(requirements_path(d)) as f:
            original = f.read()

        stdout, _, _ = run(["embed", d, "--type", "requirements", "--bump", "--dry-run"])
        check("dry run message", "DRY RUN" in stdout)

        # File should be unchanged
        with open(requirements_path(d)) as f:
            after = f.read()
        check("file unchanged", original == after)


def test_check_all_consistent():
    print("\n## Check all consistent")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        run(["embed", d, "--type", "state"])

        stdout, _, _ = run(["check", d])
        check("text output says consistent", "all fingerprints consistent" in stdout)

        stdout_json, _, _ = run(["check", d, "--output", "json", "--pretty"])
        data = json.loads(stdout_json)
        check("JSON status ok", data["status"] == "ok")
        check("allConsistent true", data["allConsistent"] is True)
        check("has artifactDir", "artifactDir" in data)


def test_check_staleness():
    print("\n## Check detects staleness")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        run(["embed", d, "--type", "state"])

        # Add a requirement
        req_path = requirements_path(d)
        with open(req_path) as f:
            content = f.read()
        content = content.replace(
            "| FR_3 | Third requirement | P1 |",
            "| FR_3 | Third requirement | P1 |\n| FR_5 | Another new | P0 |",
        )
        with open(req_path, "w") as f:
            f.write(content)

        stdout, _, _ = run(["check", d], expect_exit=1)
        check("text output says STALE", "STALE" in stdout)
        check("mentions FR_5", "FR_5" in stdout)

        stdout_json, _, _ = run(["check", d, "--output", "json"], expect_exit=1)
        data = json.loads(stdout_json)
        check("JSON status stale", data["status"] == "stale")
        check("allConsistent false", data["allConsistent"] is False)
        check("requirements level not consistent",
              data["levels"]["requirements"]["consistent"] is False)


def test_check_level_filter():
    print("\n## Check --level filter")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        run(["embed", d, "--type", "state"])

        # Check only requirements level
        stdout, _, _ = run(["check", d, "--level", "requirements"])
        check("requirements only shows requirements", "requirements" in stdout)

        # Check only iterations level
        stdout, _, _ = run(["check", d, "--level", "iterations"])
        check("iterations only shows iterations", "iterations" in stdout)


def test_check_missing_file():
    print("\n## Check missing file")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        os.remove(state_json_path(d))

        _, stderr, _ = run(["check", d], expect_exit=1)
        check("error mentions state.json", "state.json" in stderr)


def test_determinism():
    print("\n## Determinism — same input, same output")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout1, _, _ = run(["extract", d, "--type", "requirements"])
        stdout2, _, _ = run(["extract", d, "--type", "requirements"])

        fp1 = json.loads(stdout1)
        fp2 = json.loads(stdout2)

        # Compare everything except timestamp (which defaults to now)
        fp1.pop("lastNonTrivialUpdate")
        fp2.pop("lastNonTrivialUpdate")
        check("requirements deterministic", fp1 == fp2)

        stdout3, _, _ = run(["extract", d, "--type", "iterations"])
        stdout4, _, _ = run(["extract", d, "--type", "iterations"])
        fp3 = json.loads(stdout3)
        fp4 = json.loads(stdout4)
        fp3.pop("lastNonTrivialUpdate")
        fp4.pop("lastNonTrivialUpdate")
        check("iterations deterministic", fp3 == fp4)


def test_reserved_prefix_disambiguation():
    print("\n## Reserved prefix disambiguation (MS_, ID_)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "requirements"])
        fp = json.loads(stdout)

        check("MS not in requirements groups", "MS" not in fp["requirements"])
        check("ID not in requirements groups", "ID" not in fp["requirements"])
        check("MS_1 in milestones", "MS_1" in fp["milestones"])
        check("MS_2 in milestones", "MS_2" in fp["milestones"])


def test_lenient_read_strict_write():
    print("\n## Lenient read, strict write (self-healing)")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # Write a malformed fingerprint (unsorted arrays, missing fields)
        req_path = requirements_path(d)
        with open(req_path) as f:
            content = f.read()

        malformed_fp = json.dumps({
            "requirements": {"FR": ["FR_3", "FR_1", "FR_2"]},
            # Missing milestones, lastNonTrivialUpdate
        })
        content += "\n<!-- plet:fingerprint -->\n{}\n<!-- plet:fingerprint -->\n".format(
            malformed_fp
        )
        with open(req_path, "w") as f:
            f.write(content)

        # Embed should succeed (lenient read) and produce correct structure
        stdout, _, _ = run(["embed", d, "--type", "requirements",
                            "--output", "json"])
        data = json.loads(stdout)

        fp = data["fingerprint"]
        check("has milestones after heal", "milestones" in fp)
        check("has lastNonTrivialUpdate after heal", "lastNonTrivialUpdate" in fp)
        check("FR sorted after heal", fp["requirements"]["FR"] == ["FR_1", "FR_2", "FR_3"])


def test_first_embed_creates_block():
    print("\n## First embed creates fingerprint block")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        # Verify no fingerprint block exists
        with open(requirements_path(d)) as f:
            content = f.read()
        check("no block initially", "<!-- plet:fingerprint -->" not in content)

        # Embed
        run(["embed", d, "--type", "requirements"])

        # Verify block was created
        with open(requirements_path(d)) as f:
            content = f.read()
        check("block created", "<!-- plet:fingerprint -->" in content)


def test_error_invalid_type():
    print("\n## Error: invalid --type")
    _, stderr, _ = run(["extract", "/tmp", "--type", "foo"], expect_exit=1)
    check("error mentions invalid type", "invalid" in stderr and "foo" in stderr)


def test_error_dry_run_on_extract():
    print("\n## Error: --dry-run on extract")
    _, stderr, _ = run(["extract", "/tmp", "--type", "requirements", "--dry-run"],
                       expect_exit=1)
    check("error mentions read-only", "read-only" in stderr)


def test_error_bump_on_check():
    print("\n## Error: --bump on check")
    _, stderr, _ = run(["check", "/tmp", "--bump"], expect_exit=1)
    check("error mentions embed only", "embed" in stderr)


def test_error_not_a_directory():
    print("\n## Error: not a directory")
    with tempfile.NamedTemporaryFile() as f:
        _, stderr, _ = run(["extract", f.name, "--type", "requirements"],
                           expect_exit=1)
        check("error mentions not a directory", "not a directory" in stderr)


def test_error_pretty_without_json():
    print("\n## Error: --pretty without --output json")
    _, stderr, _ = run(["extract", "/tmp", "--type", "requirements", "--pretty"],
                       expect_exit=1)
    check("error mentions --output json", "--output json" in stderr)


def test_error_fields_without_json():
    print("\n## Error: --fields without --output json")
    _, stderr, _ = run(["extract", "/tmp", "--type", "requirements",
                        "--fields", "status"], expect_exit=1)
    check("error mentions --output json", "--output json" in stderr)


def test_error_missing_file():
    print("\n## Error: missing artifact file")
    with tempfile.TemporaryDirectory() as d:
        # Empty directory
        _, stderr, _ = run(["extract", d, "--type", "requirements"], expect_exit=1)
        check("error mentions file", "does not exist" in stderr)


def test_withdrawn_section_exclusion():
    print("\n## Withdrawn section exclusion")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "iterations"])
        fp = json.loads(stdout)

        # ID_004 is in the Withdrawn section — should be excluded
        all_ids = []
        for ids in fp["iterations"].values():
            all_ids.extend(ids)
        check("ID_004 excluded", "ID_004" not in all_ids)
        check("ID_001 included", "ID_001" in all_ids)
        check("ID_003 included", "ID_003" in all_ids)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    test_help_all_commands()
    test_version()
    test_extract_requirements()
    test_extract_iterations()
    test_extract_json_output()
    test_extract_fields_filter()
    test_embed_requirements()
    test_embed_chain()
    test_embed_auto_bump()
    test_embed_no_bump_when_unchanged()
    test_embed_dry_run()
    test_check_all_consistent()
    test_check_staleness()
    test_check_level_filter()
    test_check_missing_file()
    test_determinism()
    test_reserved_prefix_disambiguation()
    test_lenient_read_strict_write()
    test_first_embed_creates_block()
    test_error_invalid_type()
    test_error_dry_run_on_extract()
    test_error_bump_on_check()
    test_error_not_a_directory()
    test_error_pretty_without_json()
    test_error_fields_without_json()
    test_error_missing_file()
    test_withdrawn_section_exclusion()

    print("\n{} passed, {} failed".format(passed, failed))
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
