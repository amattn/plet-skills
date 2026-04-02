#!/usr/bin/env python3
"""plet bootstrap — project setup for plet operation.

Configures git (merge driver, .gitattributes), creates .gitignore,
merges allow entries into .claude/settings.json, creates CLAUDE.md stub.
Idempotent — safe to run multiple times.

Usage:
    plet_bootstrap.py <command> <project_dir>

Commands:
    setup     Configure the project for plet (mutating, idempotent)
    check     Verify bootstrap state (read-only)

Global flags:
    --help, -h    Show this help or command-specific help
    --version     Show version info

All commands support: --output json [--pretty] [--fields f1,f2]
setup supports: --force (overwrite git config, not CLAUDE.md or user settings)
"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import (
    dispatch,
    emit_json,
    extract_output_flags,
    parse_kwargs,
    validate_known_flags,
)
from util_constants import SKILL_VERSION

SCRIPT_NAME = "plet_bootstrap"
SCRIPT_VERSION = "0.1.0"

UNIVERSAL_FLAGS_READ = {"output", "pretty", "fields"}
UNIVERSAL_FLAGS_WRITE = UNIVERSAL_FLAGS_READ | {"dry_run", "force"}

GITIGNORE_ENTRIES = [
    ".plet/",
    ".claude/settings.local.json",
    "CLAUDE.local.md",
]

GITATTR_PATTERNS = [
    "plet/state.json merge=ours",
    "plet/progress.md merge=plet-append",
    "plet/learnings.md merge=plet-append",
    "plet/emergent.md merge=plet-append",
    "plet/trace/*.ndjson merge=plet-append",
]

# Allow patterns for .claude/settings.json
PLET_ALLOW_ENTRIES = [
    "Bash(plet_*.py *)",
]

CLAUDE_MD_STUB = """# CLAUDE.md

This project uses **plet** for spec-driven autonomous development.

## Plet Scripts

Plet scripts are available via environment variables. Check:
```bash
env | grep -E 'PLET|CLAUDE'
```

Key variables:
- `PLET_SCRIPTS_DIR` — absolute path to plet scripts
- `PLET_DIR` — path to the plet directory
- `CLAUDE_SKILL_DIR` — skill directory (if available)
- `CLAUDE_CONFIG_DIR` — Claude config directory (fallback: `~/.claude`)

Call scripts as: `$PLET_SCRIPTS_DIR/plet_iter_state.py ...`

## Project State

Runtime state lives in `plet/` (committed to git):
- `plet/state.json` — global state (lifecycles, dependencies)
- `plet/state/*.json` — per-iteration state
- `plet/progress.md` — append-only progress log
- `plet/learnings.md` — cross-iteration knowledge base
- `plet/emergent.md` — items for human review
- `plet/requirements.md` — project requirements
- `plet/iterations.md` — iteration definitions
"""


def _help_hint(cmd):
    return f"Run: plet_bootstrap.py {cmd} --help"


def _get_project_dir(args):
    """Extract project_dir from args. Returns (project_dir, remaining) or (None, [])."""
    if not args:
        print("Error: project_dir is required", file=sys.stderr)
        return None, []
    return args[0], args[1:]


def _is_git_repo(project_dir):
    """Check if project_dir is inside a git repository."""
    result = subprocess.run(
        ["git", "-C", project_dir, "rev-parse", "--git-dir"],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _git_config_get(project_dir, key):
    """Read a git config value. Returns value or None."""
    result = subprocess.run(
        ["git", "-C", project_dir, "config", "--get", key],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def _ensure_gitignore(project_dir):
    """Add missing entries to .gitignore. Returns list of actions."""
    actions = []
    path = os.path.join(project_dir, ".gitignore")

    existing = ""
    if os.path.isfile(path):
        with open(path) as f:
            existing = f.read()

    missing = [e for e in GITIGNORE_ENTRIES if e not in existing]
    if not missing:
        actions.append({"action": "skipped", "target": ".gitignore", "detail": "all entries present"})
        return actions

    with open(path, "a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        f.write("# plet infrastructure\n")
        for entry in missing:
            f.write(entry + "\n")

    if not os.path.isfile(path):
        actions.append({"action": "created", "target": ".gitignore", "detail": f"{len(missing)} entries"})
    else:
        actions.append(
            {
                "action": "configured",
                "target": ".gitignore",
                "detail": f"added {len(missing)} entries",
            }
        )
    return actions


def _ensure_gitattributes(project_dir):
    """Add merge driver entries to .gitattributes. Returns list of actions."""
    actions = []
    path = os.path.join(project_dir, ".gitattributes")

    existing = ""
    if os.path.isfile(path):
        with open(path) as f:
            existing = f.read()

    missing = [p for p in GITATTR_PATTERNS if p not in existing]
    if not missing:
        actions.append({"action": "skipped", "target": ".gitattributes", "detail": "all entries present"})
        return actions

    with open(path, "a") as f:
        if existing and not existing.endswith("\n"):
            f.write("\n")
        for p in missing:
            f.write(p + "\n")

    actions.append({"action": "configured", "target": ".gitattributes", "detail": f"{len(missing)} entries"})
    return actions


def _ensure_merge_driver(project_dir):
    """Configure plet-append merge driver in git config. Returns list of actions."""
    actions = []

    existing = _git_config_get(project_dir, "merge.plet-append.driver")
    if existing:
        actions.append({"action": "skipped", "target": "merge driver", "detail": "already configured"})
        return actions

    scripts_dir = os.path.dirname(os.path.abspath(__file__))
    driver_path = os.path.join(scripts_dir, "plet_merge_driver.py")

    if not os.path.isfile(driver_path):
        actions.append(
            {
                "action": "skipped",
                "target": "merge driver",
                "detail": f"plet_merge_driver.py not found at {driver_path}",
            }
        )
        return actions

    driver_cmd = f"{sys.executable} {driver_path} %O %A %B"
    subprocess.run(
        ["git", "-C", project_dir, "config", "merge.plet-append.driver", driver_cmd],
        capture_output=True,
    )
    subprocess.run(
        ["git", "-C", project_dir, "config", "merge.plet-append.name", "plet append-only merge"],
        capture_output=True,
    )

    actions.append({"action": "configured", "target": "merge driver", "detail": "plet-append"})
    return actions


def _ensure_plet_dir(project_dir):
    """Create .plet/ directory. Returns list of actions."""
    plet_infra = os.path.join(project_dir, ".plet")
    if os.path.isdir(plet_infra):
        return [{"action": "skipped", "target": ".plet/", "detail": "exists"}]

    os.makedirs(plet_infra, exist_ok=True)
    return [{"action": "created", "target": ".plet/", "detail": "infrastructure directory"}]


def _ensure_claude_md(project_dir):
    """Create CLAUDE.md stub if missing. Never overwrites. Returns list of actions."""
    path = os.path.join(project_dir, "CLAUDE.md")
    if os.path.isfile(path):
        return [{"action": "skipped", "target": "CLAUDE.md", "detail": "exists (not overwritten)"}]

    with open(path, "w") as f:
        f.write(CLAUDE_MD_STUB)

    return [{"action": "created", "target": "CLAUDE.md", "detail": "plet stub with script discovery"}]


def _ensure_claude_settings(project_dir):
    """Merge plet allow entries into .claude/settings.json. Returns list of actions."""
    actions = []
    claude_dir = os.path.join(project_dir, ".claude")
    settings_path = os.path.join(claude_dir, "settings.json")

    # Load or create
    if os.path.isfile(settings_path):
        try:
            with open(settings_path) as f:
                settings = json.load(f)
        except json.JSONDecodeError as e:
            return [{"action": "error", "target": ".claude/settings.json", "detail": f"invalid JSON: {e}"}]
    else:
        os.makedirs(claude_dir, exist_ok=True)
        settings = {}

    # Ensure permissions.allow exists
    if "permissions" not in settings:
        settings["permissions"] = {}
    if "allow" not in settings["permissions"]:
        settings["permissions"]["allow"] = []

    allow = settings["permissions"]["allow"]
    missing = [e for e in PLET_ALLOW_ENTRIES if e not in allow]

    if not missing:
        actions.append({"action": "skipped", "target": ".claude/settings.json", "detail": "plet allow entries present"})
    else:
        allow.extend(missing)
        with open(settings_path, "w") as f:
            json.dump(settings, f, indent=4)
            f.write("\n")
        actions.append(
            {
                "action": "configured",
                "target": ".claude/settings.json",
                "detail": f"added {len(missing)} allow entries",
            }
        )

    # Check permissions (warn only, never modify)
    default_mode = settings.get("permissions", {}).get("defaultMode")
    has_bypass = "bypassPermissions" in settings.get("permissions", {})
    sandbox = settings.get("sandbox", {})
    sandbox_enabled = sandbox.get("enabled", False) if isinstance(sandbox, dict) else False

    if default_mode == "auto" or has_bypass:
        pass  # sufficient
    elif sandbox_enabled:
        actions.append(
            {
                "action": "warn",
                "target": "permissions",
                "detail": "sandbox mode enabled but no bypassPermissions — "
                "subagents may not have autonomous tool access. "
                'Consider adding: "permissions": {"defaultMode": "auto"}',
            }
        )
    else:
        # Detect sandbox empirically
        tmpdir = os.environ.get("TMPDIR", "")
        if tmpdir.startswith("/tmp/claude"):
            actions.append(
                {
                    "action": "warn",
                    "target": "permissions",
                    "detail": f"sandbox mode detected (TMPDIR={tmpdir}) but no auto/bypass — "
                    "subagents may not have autonomous tool access",
                }
            )

    return actions


# ---------------------------------------------------------------------------
# setup
# ---------------------------------------------------------------------------


def cmd_setup(args):
    """Configure the project for plet operation."""
    HELP = """Usage: plet_bootstrap.py setup <project_dir> [--force]
  [--output json [--pretty] [--fields f1,f2]]

Configures a project for plet: git merge driver, .gitignore,
.claude/settings.json, CLAUDE.md stub. Idempotent.

Examples:
  plet_bootstrap.py setup .
  plet_bootstrap.py setup /path/to/project --force
  plet_bootstrap.py setup . --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    project_dir, remaining = _get_project_dir(args)
    if project_dir is None:
        return 1

    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, {"force"} | UNIVERSAL_FLAGS_WRITE, _help_hint("setup")):
        return 1

    output_json, pretty, fields, dry_run, ok = extract_output_flags(kwargs, allow_dry_run=True)
    if not ok:
        return 1

    # Preconditions
    if not os.path.isdir(project_dir):
        print(f"Error: directory does not exist: {project_dir}", file=sys.stderr)
        return 1

    if not _is_git_repo(project_dir):
        print(f"Error: not inside a git repository: {project_dir}", file=sys.stderr)
        print("Run 'git init' first.", file=sys.stderr)
        return 1

    if dry_run:
        if output_json:
            emit_json(
                {"status": "ok", "command": "setup", "dryRun": True, "actions": [], "summary": {}},
                SCRIPT_VERSION,
                pretty,
                fields,
            )
        else:
            print(f"DRY RUN — would configure project at {project_dir}")
        return 0

    # Run all setup actions
    all_actions = []
    all_actions.extend(_ensure_plet_dir(project_dir))
    all_actions.extend(_ensure_gitignore(project_dir))
    all_actions.extend(_ensure_gitattributes(project_dir))
    all_actions.extend(_ensure_merge_driver(project_dir))
    all_actions.extend(_ensure_claude_md(project_dir))
    all_actions.extend(_ensure_claude_settings(project_dir))

    # Summarize
    created = sum(1 for a in all_actions if a["action"] == "created")
    configured = sum(1 for a in all_actions if a["action"] == "configured")
    skipped = sum(1 for a in all_actions if a["action"] == "skipped")
    warnings = sum(1 for a in all_actions if a["action"] == "warn")
    errors = sum(1 for a in all_actions if a["action"] == "error")

    if output_json:
        emit_json(
            {
                "status": "error" if errors else ("warn" if warnings else "ok"),
                "command": "setup",
                "actions": all_actions,
                "summary": {
                    "created": created,
                    "configured": configured,
                    "skipped": skipped,
                    "warnings": warnings,
                    "errors": errors,
                },
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        for a in all_actions:
            print("{}: {} — {}".format(a["action"], a["target"], a["detail"]))
        print(f"\nBootstrap complete: {created} created, {configured} configured, {skipped} skipped")
        if warnings:
            print(f"{warnings} warning(s)")

    return 1 if errors else 0


# ---------------------------------------------------------------------------
# check
# ---------------------------------------------------------------------------


def cmd_check(args):
    """Verify bootstrap state without modifying anything."""
    HELP = """Usage: plet_bootstrap.py check <project_dir>
  [--output json [--pretty] [--fields f1,f2]]

Checks if the project is properly configured for plet.
Reports what's missing or needs attention. Read-only.

Examples:
  plet_bootstrap.py check .
  plet_bootstrap.py check /path/to/project --output json --pretty
"""
    if "-h" in args or "--help" in args:
        print(HELP)
        return 0

    project_dir, remaining = _get_project_dir(args)
    if project_dir is None:
        return 1

    kwargs = parse_kwargs(remaining)
    if not validate_known_flags(kwargs, UNIVERSAL_FLAGS_READ, _help_hint("check")):
        return 1

    output_json, pretty, fields, _, ok = extract_output_flags(kwargs)
    if not ok:
        return 1

    if not os.path.isdir(project_dir):
        print(f"Error: directory does not exist: {project_dir}", file=sys.stderr)
        return 1

    checks = []

    # git-repo
    if _is_git_repo(project_dir):
        checks.append({"name": "git-repo", "status": "pass", "detail": "git repository found"})
    else:
        checks.append({"name": "git-repo", "status": "warn", "detail": "not a git repository — run git init"})

    # plet-dir
    if os.path.isdir(os.path.join(project_dir, ".plet")):
        checks.append({"name": "plet-dir", "status": "pass", "detail": ".plet/ exists"})
    else:
        checks.append({"name": "plet-dir", "status": "warn", "detail": ".plet/ missing — run setup"})

    # gitignore
    gitignore_path = os.path.join(project_dir, ".gitignore")
    if os.path.isfile(gitignore_path):
        with open(gitignore_path) as f:
            content = f.read()
        if ".plet/" in content:
            checks.append({"name": "gitignore", "status": "pass", "detail": ".plet/ entry present"})
        else:
            checks.append({"name": "gitignore", "status": "warn", "detail": ".plet/ entry missing"})
    else:
        checks.append({"name": "gitignore", "status": "warn", "detail": ".gitignore missing"})

    # merge-driver
    if _is_git_repo(project_dir):
        driver = _git_config_get(project_dir, "merge.plet-append.driver")
        if driver:
            checks.append({"name": "merge-driver", "status": "pass", "detail": "plet-append configured"})
        else:
            checks.append({"name": "merge-driver", "status": "warn", "detail": "plet-append not configured"})

    # gitattributes
    gitattr_path = os.path.join(project_dir, ".gitattributes")
    if os.path.isfile(gitattr_path):
        with open(gitattr_path) as f:
            content = f.read()
        if "plet-append" in content:
            checks.append({"name": "gitattributes", "status": "pass", "detail": "merge driver entries present"})
        else:
            checks.append({"name": "gitattributes", "status": "warn", "detail": "merge driver entries missing"})
    else:
        checks.append({"name": "gitattributes", "status": "warn", "detail": ".gitattributes missing"})

    # claude-md
    if os.path.isfile(os.path.join(project_dir, "CLAUDE.md")):
        checks.append({"name": "claude-md", "status": "pass", "detail": "CLAUDE.md exists"})
    else:
        checks.append({"name": "claude-md", "status": "warn", "detail": "CLAUDE.md missing"})

    # claude-settings
    settings_path = os.path.join(project_dir, ".claude", "settings.json")
    if os.path.isfile(settings_path):
        try:
            with open(settings_path) as f:
                settings = json.load(f)
            allow = settings.get("permissions", {}).get("allow", [])
            has_plet = any(e in allow for e in PLET_ALLOW_ENTRIES)
            if has_plet:
                checks.append({"name": "claude-settings", "status": "pass", "detail": "plet allow entries present"})
            else:
                checks.append({"name": "claude-settings", "status": "warn", "detail": "plet allow entries missing"})

            # permissions check
            default_mode = settings.get("permissions", {}).get("defaultMode")
            has_bypass = "bypassPermissions" in settings.get("permissions", {})
            if default_mode == "auto" or has_bypass:
                checks.append({"name": "permissions", "status": "pass", "detail": "autonomous mode configured"})
            else:
                sandbox = settings.get("sandbox", {})
                sandbox_on = sandbox.get("enabled", False) if isinstance(sandbox, dict) else False
                tmpdir = os.environ.get("TMPDIR", "")
                if sandbox_on or tmpdir.startswith("/tmp/claude"):
                    checks.append(
                        {
                            "name": "permissions",
                            "status": "warn",
                            "detail": "sandbox mode but no auto/bypass — subagents need autonomous access. "
                            'Add: "defaultMode": "auto" to permissions',
                        }
                    )
                else:
                    checks.append(
                        {
                            "name": "permissions",
                            "status": "warn",
                            "detail": "no defaultMode or bypassPermissions set"
                            " — subagents may need approval for every tool call",
                        }
                    )
        except json.JSONDecodeError:
            checks.append(
                {"name": "claude-settings", "status": "warn", "detail": "invalid JSON in .claude/settings.json"}
            )
    else:
        checks.append({"name": "claude-settings", "status": "warn", "detail": ".claude/settings.json missing"})

    # git-config (user.email + user.name)
    if _is_git_repo(project_dir):
        email = _git_config_get(project_dir, "user.email")
        name = _git_config_get(project_dir, "user.name")
        if email and name:
            checks.append({"name": "git-config", "status": "pass", "detail": "user.email and user.name configured"})
        else:
            missing = []
            if not email:
                missing.append("user.email")
            if not name:
                missing.append("user.name")
            checks.append(
                {
                    "name": "git-config",
                    "status": "warn",
                    "detail": "{} not configured — git commits will fail".format(" and ".join(missing)),
                }
            )

    # Summarize
    passed = sum(1 for c in checks if c["status"] == "pass")
    failed = sum(1 for c in checks if c["status"] == "fail")
    warnings = sum(1 for c in checks if c["status"] == "warn")

    if output_json:
        status = "fail" if failed else ("warn" if warnings else "ok")
        emit_json(
            {
                "status": status,
                "command": "check",
                "checks": checks,
                "summary": {"passed": passed, "failed": failed, "warnings": warnings},
            },
            SCRIPT_VERSION,
            pretty,
            fields,
        )
    else:
        for c in checks:
            print("{}: {} — {}".format(c["status"], c["name"], c["detail"]))
        print(f"\n{passed} passed, {failed} failed, {warnings} warnings")

    if failed:
        return 1
    elif warnings:
        return 2
    return 0


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    commands = {
        "setup": cmd_setup,
        "check": cmd_check,
    }
    return dispatch(
        commands,
        SCRIPT_NAME,
        SCRIPT_VERSION,
        SKILL_VERSION,
        __doc__,
    )


if __name__ == "__main__":
    sys.exit(main())
