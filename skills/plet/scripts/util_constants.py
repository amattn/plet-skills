"""Shared constants for plet scripts.

Single source of truth for version numbers and other values
that multiple scripts need to agree on.
"""

# State file schema version — bump when state file format changes.
# Additive changes = minor bump. Breaking changes = major bump.
# Written into state.json and state/{iter_id}.json by global_state.py and iter_state.py init.
# Human reference: references/state-schema.md, references/formats.md
SCHEMA_VERSION = "0.7.0"

# Plet skill version — matches SKILL.md frontmatter version.
SKILL_VERSION = "0.7.0"
