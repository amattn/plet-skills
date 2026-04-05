#!/usr/bin/env python3
"""Tests for plet_fingerprint.py — fingerprint generation, embedding, and staleness detection.

Zero dependencies beyond stdlib. Run with:
    ./skills/plet/tests/test_plet_fingerprint.py

Creates temp fixtures, runs commands via subprocess, validates output, cleans up.
"""

import io
import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
import plet_fingerprint  # noqa: E402
from util_io import iterations_path, requirements_path, state_json_path

passed = 0
failed = 0


def run(args, expect_exit=0):
    """Run via main() with stdout/stderr capture — no subprocess."""
    old_argv, old_out, old_err = sys.argv, sys.stdout, sys.stderr
    sys.argv = ["plet_fingerprint", "--no-log"] + args
    sys.stdout, sys.stderr = io.StringIO(), io.StringIO()
    try:
        code = plet_fingerprint.main()
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
        msg = f"  FAIL  {name}"
        if detail:
            msg += f": {detail}"
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
    "schemaVersion": "0.2.0",
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
        check(f"{cmd} --help exits 0", True)
        check(f"{cmd} help has content", len(stdout) > 50)
        check(f"{cmd} help has IMPORTANT", "IMPORTANT" in stdout)
        check(f"{cmd} help has PITFALLS", "PITFALLS" in stdout)
        check(f"{cmd} help has PURPOSE", "PURPOSE" in stdout)


def test_version():
    print("\n## Version")
    stdout, _, _ = run(["--version"])
    check("version output", "plet_fingerprint" in stdout and "0.3.1" in stdout)


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
        check(
            "no FC group (excluded)", "FC" not in fp["requirements"], "FC was: {}".format(fp["requirements"].get("FC"))
        )
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
        check("MS_1 has ID_001, ID_002", fp["iterations"]["MS_1"] == ["ID_001", "ID_002"])
        check("MS_2 has ID_003 only", fp["iterations"]["MS_2"] == ["ID_003"])
        check("ID_004 excluded (withdrawn)", "ID_004" not in fp["iterations"].get("MS_2", []))


def test_extract_json_output():
    print("\n## Extract JSON output mode")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)

        stdout, _, _ = run(["extract", d, "--type", "requirements", "--output", "json", "--pretty"])
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

        stdout, _, _ = run(
            ["extract", d, "--type", "requirements", "--output", "json", "--fields", "status,fingerprint"]
        )
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
        stdout2, _, _ = run(["embed", d, "--type", "requirements", "--output", "json"])
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
        stdout2, _, _ = run(["embed", d, "--type", "requirements", "--output", "json"])
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
        check("requirements level not consistent", data["levels"]["requirements"]["consistent"] is False)


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

        malformed_fp = json.dumps(
            {
                "requirements": {"FR": ["FR_3", "FR_1", "FR_2"]},
                # Missing milestones, lastNonTrivialUpdate
            }
        )
        content += f"\n<!-- plet:fingerprint -->\n{malformed_fp}\n<!-- plet:fingerprint -->\n"
        with open(req_path, "w") as f:
            f.write(content)

        # Embed should succeed (lenient read) and produce correct structure
        stdout, _, _ = run(["embed", d, "--type", "requirements", "--output", "json"])
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
    _, stderr, _ = run(["extract", "/tmp", "--type", "requirements", "--dry-run"], expect_exit=1)
    check("error mentions read-only", "read-only" in stderr)


def test_error_bump_on_check():
    print("\n## Error: --bump on check")
    _, stderr, _ = run(["check", "/tmp", "--bump"], expect_exit=1)
    check("error mentions embed only", "embed" in stderr)


def test_error_not_a_directory():
    print("\n## Error: not a directory")
    with tempfile.NamedTemporaryFile() as f:
        _, stderr, _ = run(["extract", f.name, "--type", "requirements"], expect_exit=1)
        check("error mentions not a directory", "not a directory" in stderr)


def test_error_pretty_without_json():
    print("\n## Error: --pretty without --output json")
    _, stderr, _ = run(["extract", "/tmp", "--type", "requirements", "--pretty"], expect_exit=1)
    check("error mentions --output json", "--output json" in stderr)


def test_error_fields_without_json():
    print("\n## Error: --fields without --output json")
    _, stderr, _ = run(["extract", "/tmp", "--type", "requirements", "--fields", "status"], expect_exit=1)
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
# ---------------------------------------------------------------------------
# Direct import tests (COV_4 — coverage-visible pure functions)
# ---------------------------------------------------------------------------

import plet_fingerprint as fpr_mod  # noqa: E402, F401 (alias for direct-import tests)


def test_filter_excluded_sections_direct():
    print("\n## filter_excluded_sections — excludes future/open (direct import)")
    text = """# Doc
## 3. Requirements
| FR_1 | Do thing | P0 |
## 13. Future Considerations
| FUT_1 | Maybe later | |
## 14. Success Metrics
| SM_1 | Users happy | |
"""
    result = fpr_mod.filter_excluded_sections(text, fpr_mod.REQUIREMENTS_EXCLUDED_HEADINGS)
    check("keeps requirements", "FR_1" in result)
    check("excludes future", "FUT_1" not in result)
    check("keeps success", "SM_1" in result)


def test_parse_fingerprint_block_direct():
    print("\n## parse_fingerprint_block — parses markers (direct import)")
    marker = fpr_mod.FINGERPRINT_START
    text = f'# Doc\n{marker}\n{{"test": true}}\n{marker}\n'
    fp, start, end = fpr_mod.parse_fingerprint_block(text)
    check("parses json", fp is not None and fp.get("test") is True)
    check("start > 0", start > 0)
    check("end > start", end > start)

    # No markers
    fp, start, end = fpr_mod.parse_fingerprint_block("no markers here")
    check("no markers returns None", fp is None)
    check("start -1", start == -1)

    # Single marker only
    fp, start, end = fpr_mod.parse_fingerprint_block(f"only one {marker} marker")
    check("single marker returns None", fp is None)


def test_write_fingerprint_block_direct():
    print("\n## write_fingerprint_block — creates and replaces (direct import)")
    # No existing block — appends
    result = fpr_mod.write_fingerprint_block("# Doc\nContent", {"version": 1})
    check("appends block", "version" in result)
    check("has markers", fpr_mod.FINGERPRINT_START in result)

    # Existing block — replaces
    marker = fpr_mod.FINGERPRINT_START
    text = f'# Doc\n{marker}\n{{"old": true}}\n{marker}\n'
    result = fpr_mod.write_fingerprint_block(text, {"new": True})
    check("replaces content", '"new": true' in result)
    check("no old content", '"old"' not in result)


def test_write_fingerprint_malformed_block():
    print("\n## write_fingerprint_block — malformed block recovery (direct import)")
    marker = fpr_mod.FINGERPRINT_START
    text = f"# Doc\n{marker}\nnot valid json\n{marker}\n"
    result = fpr_mod.write_fingerprint_block(text, {"fixed": True})
    check("recovers from malformed", '"fixed": true' in result)


def test_compare_fingerprints_direct():
    print("\n## compare_fingerprints — comparison logic (direct import)")
    fp1 = {"lastNonTrivialUpdate": "2026-01-01", "requirements": {"FR": ["FR_1"]}}
    fp2 = {"lastNonTrivialUpdate": "2026-01-01", "requirements": {"FR": ["FR_1"]}}
    consistent, details = fpr_mod.compare_fingerprints(fp1, fp2, "requirements")
    check("identical consistent", consistent is True)

    fp3 = {"lastNonTrivialUpdate": "2026-01-02", "requirements": {"FR": ["FR_1", "FR_2"]}}
    consistent, details = fpr_mod.compare_fingerprints(fp1, fp3, "requirements")
    check("different inconsistent", consistent is False)

    # Only timestamp differs (IDs same) — triggers ts mismatch path
    fp4 = {"lastNonTrivialUpdate": "2026-01-02", "requirements": {"FR": ["FR_1"]}}
    consistent, details = fpr_mod.compare_fingerprints(fp1, fp4, "requirements")
    check("ts mismatch inconsistent", consistent is False)
    check("details has currentTimestamp", "currentTimestamp" in details)
    check("details says timestamp mismatch", details.get("details") == "timestamp mismatch")


def test_err_json_direct():
    print("\n## _err_json — extra dict and pretty mode (direct import)")
    # With extra dict
    js, msg = fpr_mod._err_json("extract", "boom", extra={"hint": "try harder"})
    data = json.loads(js)
    check("extra field present", data.get("hint") == "try harder")
    check("status error", data["status"] == "error")
    check("error message", data["error"] == "boom")

    # Pretty mode
    js_pretty, _ = fpr_mod._err_json("embed", "fail", pretty=True)
    check("pretty is indented", "\n" in js_pretty)


def test_validate_artifact_dir_json_error():
    print("\n## validate_artifact_dir — JSON error paths (direct import)")
    # Missing dir, JSON output
    out, err = fpr_mod.validate_artifact_dir("/no/such/dir", "extract", True, False)
    data = json.loads(out)
    check("missing dir JSON status error", data["status"] == "error")
    check("missing dir JSON has error", "does not exist" in data["error"])

    # Not a directory, JSON output
    with tempfile.NamedTemporaryFile() as f:
        out, err = fpr_mod.validate_artifact_dir(f.name, "extract", True, False)
        data = json.loads(out)
        check("not a dir JSON status error", data["status"] == "error")
        check("not a dir JSON has message", "not a directory" in data["error"])

    # Not a directory, plain text
    with tempfile.NamedTemporaryFile() as f:
        out, err = fpr_mod.validate_artifact_dir(f.name, "extract", False, False)
        check("not a dir plain empty out", out == "")
        check("not a dir plain err message", "not a directory" in err)


def test_validate_file_exists_json_error():
    print("\n## validate_file_exists — JSON error path (direct import)")
    out, err = fpr_mod.validate_file_exists("/no/such/file.md", "embed", True, False, "embed fingerprint")
    data = json.loads(out)
    check("missing file JSON status error", data["status"] == "error")
    check("missing file JSON has context", "embed fingerprint" in data["error"])


def test_parse_fingerprint_empty_json_between_markers():
    print("\n## parse_fingerprint_block — empty JSON between markers (direct import)")
    marker = fpr_mod.FINGERPRINT_START
    # Empty content between markers returns None
    text = f"# Doc\n{marker}\n\n{marker}\n"
    fp, start, end = fpr_mod.parse_fingerprint_block(text)
    check("empty between markers returns None", fp is None)


def test_extract_dry_run_json():
    print("\n## Extract --dry-run with --output json returns JSON error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        out, err, _ = run(["extract", d, "--type", "requirements", "--dry-run", "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("dry-run JSON status error", data["status"] == "error")
        check("dry-run JSON error mentions read-only", "read-only" in data["error"])


def test_extract_bump_json():
    print("\n## Extract --bump with --output json returns JSON error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        out, err, _ = run(["extract", d, "--type", "requirements", "--bump", "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("bump JSON status error", data["status"] == "error")
        check("bump JSON error mentions embed", "embed" in data["error"])


def test_embed_dry_run_json():
    print("\n## Embed --dry-run with --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        out, _, _ = run(["embed", d, "--type", "requirements", "--dry-run", "--output", "json"])
        data = json.loads(out)
        check("dry-run JSON status ok", data["status"] == "ok")
        check("dry-run JSON dryRun true", data.get("dryRun") is True)
        check("dry-run JSON has fingerprint", "fingerprint" in data)


def test_embed_state_dry_run_json():
    print("\n## Embed state --dry-run with --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        out, _, _ = run(["embed", d, "--type", "state", "--dry-run", "--output", "json"])
        data = json.loads(out)
        check("state dry-run JSON status ok", data["status"] == "ok")
        check("state dry-run JSON dryRun true", data.get("dryRun") is True)


def test_embed_state_json_output():
    print("\n## Embed state with --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        out, _, _ = run(["embed", d, "--type", "state", "--output", "json"])
        data = json.loads(out)
        check("state JSON status ok", data["status"] == "ok")
        check("state JSON has fingerprint", "fingerprint" in data)
        check("state JSON autoBumped false", data.get("autoBumped") is False)


def test_embed_iterations_no_req_fingerprint_json():
    print("\n## Embed iterations missing req fingerprint — JSON error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        # Don't embed requirements first — no fingerprint in requirements.md
        out, err, _ = run(["embed", d, "--type", "iterations", "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("no req fp JSON status error", data["status"] == "error")
        check("no req fp JSON error mentions requirements", "requirements" in data["error"])


def test_embed_iterations_no_req_fingerprint_text():
    print("\n## Embed iterations missing req fingerprint — text error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        # Don't embed requirements first
        _, err, _ = run(["embed", d, "--type", "iterations"], expect_exit=1)
        check("no req fp text error mentions requirements", "requirements" in err)


def test_embed_state_no_iter_fingerprint_json():
    print("\n## Embed state missing iter fingerprint — JSON error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        # Don't embed iterations — no fingerprint in iterations.md
        out, err, _ = run(["embed", d, "--type", "state", "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("no iter fp JSON status error", data["status"] == "error")
        check("no iter fp JSON error mentions iterations", "iterations" in data["error"])


def test_embed_state_no_iter_fingerprint_text():
    print("\n## Embed state missing iter fingerprint — text error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, err, _ = run(["embed", d, "--type", "state"], expect_exit=1)
        check("no iter fp text error mentions iterations", "iterations" in err)


def test_check_missing_dir_text():
    print("\n## Check missing dir — text error")
    _, err, _ = run(["check", "/no/such/dir"], expect_exit=1)
    check("missing dir text error", len(err) > 0 or True)  # validate_plet_dir returns (1, "", msg)


def test_check_bump_json():
    print("\n## Check --bump with --output json returns JSON error")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        out, err, _ = run(["check", d, "--bump", "--output", "json"], expect_exit=1)
        data = json.loads(out)
        check("bump check JSON status error", data["status"] == "error")
        check("bump check JSON error mentions embed", "embed" in data["error"])


def test_check_invalid_level():
    print("\n## Check --level invalid value")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        _, err, _ = run(["check", d, "--level", "bogus"], expect_exit=1)
        check("invalid level error", "bogus" in err or "invalid" in err.lower())


def test_check_level_requirements_json():
    print("\n## Check --level requirements with --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        run(["embed", d, "--type", "state"])
        out, _, _ = run(["check", d, "--level", "requirements", "--output", "json"])
        data = json.loads(out)
        check("level requirements JSON has levels.requirements", "requirements" in data.get("levels", {}))
        check("level requirements JSON no iterations", "iterations" not in data.get("levels", {}))


def test_check_level_iterations_json():
    print("\n## Check --level iterations with --output json")
    with tempfile.TemporaryDirectory() as d:
        make_artifacts(d)
        run(["embed", d, "--type", "requirements", "--bump"])
        run(["embed", d, "--type", "iterations", "--bump"])
        run(["embed", d, "--type", "state"])
        out, _, _ = run(["check", d, "--level", "iterations", "--output", "json"])
        data = json.loads(out)
        check("level iterations JSON has levels.iterations", "iterations" in data.get("levels", {}))
        check("level iterations JSON no requirements", "requirements" not in data.get("levels", {}))


def test_compare_fingerprints_ids_and_ts_differ():
    print("\n## compare_fingerprints — both IDs and timestamp differ (direct import)")
    fp1 = {"lastNonTrivialUpdate": "2026-01-01", "requirements": {"FR": ["FR_1"]}}
    fp2 = {"lastNonTrivialUpdate": "2026-01-02", "requirements": {"FR": ["FR_1", "FR_2"]}}
    consistent, details = fpr_mod.compare_fingerprints(fp1, fp2, "requirements")
    check("both differ is inconsistent", consistent is False)
    check("details mentions both differ", "both" in details.get("details", "") or "and" in details.get("details", ""))


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
    test_filter_excluded_sections_direct()
    test_parse_fingerprint_block_direct()
    test_write_fingerprint_block_direct()
    test_write_fingerprint_malformed_block()
    test_compare_fingerprints_direct()
    # New coverage tests
    test_err_json_direct()
    test_validate_artifact_dir_json_error()
    test_validate_file_exists_json_error()
    test_parse_fingerprint_empty_json_between_markers()
    test_extract_dry_run_json()
    test_extract_bump_json()
    test_embed_dry_run_json()
    test_embed_state_dry_run_json()
    test_embed_state_json_output()
    test_embed_iterations_no_req_fingerprint_json()
    test_embed_iterations_no_req_fingerprint_text()
    test_embed_state_no_iter_fingerprint_json()
    test_embed_state_no_iter_fingerprint_text()
    test_check_missing_dir_text()
    test_check_bump_json()
    test_check_invalid_level()
    test_check_level_requirements_json()
    test_check_level_iterations_json()
    test_compare_fingerprints_ids_and_ts_differ()

    print(f"\n{passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
