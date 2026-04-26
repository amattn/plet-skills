"""Shared constants for plet scripts.

Single source of truth for version numbers and other values
that multiple scripts need to agree on.
"""

import re

# State file schema version — bump when state file format changes.
# Additive changes = minor bump. Breaking changes = major bump.
# Written into state.json and state/{iter_id}.json by global_state.py and iter_state.py init.
# Human reference: references/state-schema.md, references/formats.md
SCHEMA_VERSION = "0.7.1"

# Plet skill version — matches SKILL.md frontmatter version.
SKILL_VERSION = "0.7.2"

# Iteration ID pattern — accepts ITR_NNN (normal) and ITR_RFT_N (refactor).
# Used by all validators. Import this instead of defining local regexes.
ITER_ID_RE = re.compile(r"^ITR_(?:RFT_)?\d+$")
ITER_ID_OR_PROJ_RE = re.compile(r"^(ITR_(?:RFT_)?\d+|proj)$")
