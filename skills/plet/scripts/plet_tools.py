#!/usr/bin/env python3
"""plet tools — plan/refine utilities and diagnostics.

Commands for project setup, state initialization, fingerprint management,
validation, and session detection. Used by plan/refine agents and humans.

Usage:
    plet_tools.py bootstrap <plet_dir> [--dry-run]
    plet_tools.py init <plet_dir> --iterations '[...]' [--output json]
    plet_tools.py validate <plet_dir> [--output json]
    plet_tools.py detect <plet_dir> [--output json]
    plet_tools.py status <plet_dir> [--output json]
    plet_tools.py fingerprint-extract <plet_dir> [--output json]
    plet_tools.py fingerprint-embed <plet_dir> [--output json]
    plet_tools.py fingerprint-check <plet_dir> --level all|iterations|requirements [--output json]

Commands:
    bootstrap             Project setup (CLAUDE.md, .gitignore, plet/ dir)
    init                  Create state.json + per-iteration state files
    validate              Schema validation of state files
    detect                Detect current phase (plan, loop, refine)
    status                Session summary, iteration states, blockers
    fingerprint-extract   Extract fingerprints from spec artifacts
    fingerprint-embed     Embed fingerprints into state.json
    fingerprint-check     Check fingerprint staleness
"""

import os
import sys

# Add scripts dir to path for sibling imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from util_cli import dispatch  # noqa: E402

SCRIPT_VERSION = "0.1.0"
# Import command functions from modules
from bootstrap import cmd_setup as cmd_bootstrap  # noqa: E402
from fingerprint import cmd_check as cmd_fingerprint_check  # noqa: E402
from fingerprint import cmd_embed as cmd_fingerprint_embed  # noqa: E402
from fingerprint import cmd_extract as cmd_fingerprint_extract  # noqa: E402
from gate_session import cmd_detect, cmd_status  # noqa: E402
from global_state import cmd_init, cmd_validate  # noqa: E402
from util_constants import SKILL_VERSION  # noqa: E402


def main():
    commands = {
        "bootstrap": cmd_bootstrap,
        "init": cmd_init,
        "validate": cmd_validate,
        "detect": cmd_detect,
        "status": cmd_status,
        "fingerprint-extract": cmd_fingerprint_extract,
        "fingerprint-embed": cmd_fingerprint_embed,
        "fingerprint-check": cmd_fingerprint_check,
    }
    return dispatch(commands, "plet_tools", SCRIPT_VERSION, SKILL_VERSION, __doc__)


if __name__ == "__main__":
    sys.exit(main())
