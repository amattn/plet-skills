"""Shared constants for plet scripts.

Single source of truth for version numbers and other values
that multiple scripts need to agree on.
"""

# State file schema version — bump when state file format changes.
# Additive changes = minor bump. Breaking changes = major bump.
SCHEMA_VERSION = "0.2.0"

# Plet skill version — matches SKILL.md frontmatter version.
SKILL_VERSION = "0.3.0"
