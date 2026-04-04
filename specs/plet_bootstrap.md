# plet_bootstrap.py (BST)

> Status: not started

## 1. Purpose (BST_PUR)

Project setup script — configures a target project for plet operation. Sets up git config (merge driver, .gitattributes), creates .gitignore, merges plet allow entries into .claude/settings.json, creates CLAUDE.md stub.

The LOGA Run 4 script discovery problem (subagents couldn't find scripts) is solved separately via `plet_prompt.py` including the absolute script path in the subagent prompt. Bootstrap handles everything else — the project infrastructure that needs to exist before plet can operate.

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_PUR_1 | Configure a target project for plet operation. Single entry point for all project setup: git config, .gitignore, .claude/settings.json, CLAUDE.md. | P0 |
| BST_PUR_2 | Configure git merge driver for runtime artifacts (progress.md, learnings.md, emergent.md). | P0 |
| BST_PUR_3 | Create `.gitignore` entries for `.plet/` (worktrees, infrastructure), `.claude/settings.local.json`, `CLAUDE.local.md`. `plet/` is NOT gitignored — it's committed project state. | P0 |
| BST_PUR_4 | Create CLAUDE.md stub if missing — project-level instructions for subagents. | P1 |
| BST_PUR_5 | Idempotent — safe to run multiple times. Updates scripts if version changed, skips files that already exist unless `--force`. | P0 |
| BST_PUR_6 | Merge plet script `allow` entries into `.claude/settings.json`. Create the file if missing. Never overwrite existing entries — only add missing plet patterns. Never set `defaultMode` or `bypassPermissions` — that's a user security decision. Warn if permissions look insufficient for autonomous subagent operation. | P0 |

## 2. Agent Personas (BST_AGT)

| ID | Caller | Context | Commands used |
|----|--------|---------|---------------|
| BST_AGT_1 | plan session agent | Step 1: project setup, before state initialization | `setup` |
| BST_AGT_2 | SKILL.md agent | When preflight warns about missing bootstrap artifacts | `setup` |
| BST_AGT_3 | human | Manual project setup or repair | `setup`, `check` |

## 3. Commands

**Command summary:**

- **`setup`** (SET) — Run the full bootstrap. Copies scripts, configures git, creates missing files. Idempotent.
- **`check`** (CHK) — Verify bootstrap state without modifying anything. Reports what's missing or outdated. Read-only.

All commands take `<project_dir>` as required first positional arg (the project root, NOT plet_dir — bootstrap creates `.plet/` at the project root level).

### Universal Flags

| Flag | Applies to | Description |
|------|-----------|-------------|
| `--output json` | both | Structured JSON output |
| `--pretty` | both | Indent JSON (requires `--output json`) |
| `--fields f1,f2` | both | Limit JSON fields (requires `--output json`) |
| `--force` | `setup` only | Overwrite existing files (scripts, CLAUDE.md). Default: skip existing. |
| `--usage` | top-level only | Compact invocation syntax with examples for all commands (UNV_CMD_30) |

---

### 3.1 setup (SET)

#### Justification (BST_SET_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_JUS_1 | Why: multiple project-level configurations must exist before plet can operate — git merge driver, .gitignore, .claude/settings.json allow entries, CLAUDE.md with script discovery instructions. Without bootstrap, these are missing or wrong, causing failures and 15+ minute stalls (LOGA Run 4). | P0 |
| BST_SET_JUS_2 | When: plan phase (once per project), or when preflight detects missing bootstrap artifacts. | P0 |

#### Definition (BST_SET_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_CMD_1 | Usage: `plet_bootstrap.py setup <project_dir> [--force] [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** mutating, idempotent (safe to re-run)

#### Inputs (BST_SET_INP)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_INP_1 | `project_dir` — required first positional. The project root directory (where `.git/` lives). NOT `plet_dir`. | P0 |
| BST_SET_INP_2 | `--force` — overwrite existing git config. Default: skip items that already exist. Never overwrites CLAUDE.md or .claude/settings.json user fields. | P1 |

#### Outputs (BST_SET_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_OUT_1 | Text mode: per-action lines (`created: .gitignore`, `configured: merge driver`, `skipped: CLAUDE.md (exists)`), then summary. | P0 |
| BST_SET_OUT_2 | JSON mode: `{"status":"ok", "command":"setup", "actions":[...], "summary":{"created":N, "configured":N, "skipped":N}}` | P0 |

#### Preconditions (BST_SET_PRE)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_PRE_1 | `project_dir` exists and is a directory | P0 |
| BST_SET_PRE_2 | `project_dir` should be inside a git repository. If no `.git/` found: `setup` errors, `check` warns. The SKILL.md agent handles the interactive fix (asks user, runs `git init`). | P0 |
| BST_SET_PRE_3 | Script derives its own location from `__file__` (bootstrap is in the scripts dir). Used for CLAUDE.md stub content (script path for subagent discovery). | P0 |

#### Postconditions (BST_SET_PST)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_PST_1 | `.plet/` directory exists | P0 |
| BST_SET_PST_2 | `.gitignore` includes `.plet/`, `.claude/settings.local.json`, and `CLAUDE.local.md` entries | P0 |
| BST_SET_PST_3 | `.gitattributes` includes merge driver config for `plet/*.md` | P0 |
| BST_SET_PST_4 | Git merge driver configured in local git config | P0 |
| BST_SET_PST_5 | CLAUDE.md exists with plet project stub (if not already present) | P1 |
| BST_SET_PST_6 | `.claude/settings.json` has plet script allow entries. Existing entries preserved — only missing plet patterns added. | P0 |

#### Behaviors (BST_SET_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_SET_BHV_1 | **Git merge driver:** Configure `plet-append` merge driver in `.git/config` (local) and add `.gitattributes` entries for `plet/progress.md`, `plet/learnings.md`, `plet/emergent.md`. | P0 |
| BST_SET_BHV_2 | **.gitignore:** Append entries to `.gitignore` if not already present: `.plet/` (infrastructure), `.claude/settings.local.json` (user-local overrides), `CLAUDE.local.md` (user-local instructions). Do NOT add `plet/` — that's committed project state. Create `.gitignore` if it doesn't exist. Each entry checked independently — only missing ones added. | P0 |
| BST_SET_BHV_3 | **CLAUDE.md:** Create a stub CLAUDE.md with plet project instructions if not present. Must include: how to find plet scripts (`CLAUDE_SKILL_DIR` env var or derive from `CLAUDE_CONFIG_DIR`), key plet conventions, pointer to `plet/` directory for state files. Skip if exists (don't overwrite user's CLAUDE.md). `--force` does NOT overwrite CLAUDE.md — it's user content. | P1 |
| BST_SET_BHV_4 | **Idempotent:** Running setup twice produces the same result. Second run reports "skipped" for already-configured items. | P0 |
| BST_SET_BHV_5 | **Claude settings:** Read `.claude/settings.json` (create `.claude/` dir + file if missing). Parse existing `permissions.allow` array. Add plet script allow entries if not already present. Never modify `defaultMode`, `bypassPermissions`, or `sandbox` — those are user security decisions. If permissions look insufficient for autonomous subagents (no auto mode, no bypassPermissions), print a WARN with the recommended config to add manually. | P0 |
| BST_SET_BHV_6 | **Create .plet/ directory** if it doesn't exist. Infrastructure dir for worktrees and future use. | P0 |

---

### 3.2 check (CHK)

#### Justification (BST_CHK_JUS)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_CHK_JUS_1 | Why: preflight needs to detect missing bootstrap artifacts. `check` reports what's missing or outdated without modifying anything. | P0 |
| BST_CHK_JUS_2 | When: `plet_gate_session.py preflight` can call this to verify bootstrap state. Human debugging. | P0 |

#### Definition (BST_CHK_CMD)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_CHK_CMD_1 | Usage: `plet_bootstrap.py check <project_dir> [--output json [--pretty] [--fields f1,f2]]` | P0 |

**Properties:** read-only, idempotent

#### Outputs (BST_CHK_OUT)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_CHK_OUT_1 | Text mode: per-check lines (`pass: merge driver configured`, `warn: permissions — bypassPermissions not set`), then summary. | P0 |
| BST_CHK_OUT_2 | JSON mode: `{"status":"ok/warn/fail", "command":"check", "checks":[...], "summary":{"passed":N, "failed":N, "warnings":N}}` | P0 |
| BST_CHK_OUT_3 | Exit codes: 0 (all pass), 1 (any fail), 2 (warn only). | P0 |

#### Behaviors (BST_CHK_BHV)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_CHK_BHV_1 | **plet-dir:** Check `.plet/` directory exists. WARN if missing. | P0 |
| BST_CHK_BHV_2 | **gitignore:** Check `.gitignore` includes `.plet/`. WARN if missing. | P0 |
| BST_CHK_BHV_3 | **merge-driver:** Check git config has plet-append merge driver. WARN if missing. | P0 |
| BST_CHK_BHV_4 | **gitattributes:** Check `.gitattributes` has merge driver entries. WARN if missing. | P0 |
| BST_CHK_BHV_5 | **claude-md:** Check CLAUDE.md exists. WARN if missing. | P1 |
| BST_CHK_BHV_6 | **claude-settings:** Check `.claude/settings.json` has plet script allow entries. WARN if missing. | P0 |
| BST_CHK_BHV_7 | **permissions:** Check `.claude/settings.json` for `defaultMode: "auto"` or `bypassPermissions` config. Also empirically detect runtime mode: sandbox mode (`TMPDIR=/tmp/claude` or write to `/tmp` blocked), auto mode (check env vars or settings). WARN if subagents likely can't operate autonomously. Include suggested config in the warning message. | P0 |
| BST_CHK_BHV_8 | **git-config:** Check `git config user.email` and `git config user.name` are set. WARN if missing — git commits will fail. The SKILL.md agent handles the interactive fix (asks user, runs git config). | P0 |
| BST_CHK_BHV_9 | **git-repo:** Check `.git/` exists. WARN if missing — SKILL.md agent offers to run `git init`. | P0 |

---

## 4. Edge Cases (BST_EDG)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_EDG_1 | Not inside a git repo → error before any setup actions | P0 |
| BST_EDG_2 | `.gitignore` already has `.plet/` entry → skip (don't duplicate) | P0 |
| BST_EDG_4 | CLAUDE.md exists → skip (never overwrite user content) | P0 |
| BST_EDG_5 | `.gitattributes` already has merge driver entries → skip | P0 |
| BST_EDG_6 | `--force` overwrites git config but NOT CLAUDE.md or `.claude/settings.json` user settings (defaultMode, bypassPermissions) | P0 |
| BST_EDG_7 | `.claude/settings.json` exists with non-plet allow entries → preserved. Only plet patterns added. | P0 |
| BST_EDG_8 | `.claude/settings.json` has malformed JSON → error, don't corrupt it | P0 |

## 5. Error Handling (BST_ERR)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_ERR_1 | Missing `project_dir` → error + help | P0 |
| BST_ERR_2 | Not a git repo → `Error: not inside a git repository` | P0 |
| BST_ERR_3 | `.claude/settings.json` malformed JSON → `Error: invalid JSON in .claude/settings.json` | P0 |
| BST_ERR_4 | Unknown flags → error (UNV_CMD_29) | P0 |

## 6. Formats (BST_FMT)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_FMT_1 | Reads: `.gitignore`, `.gitattributes`, `.git/config`, `.claude/settings.json`, `CLAUDE.md` — checks for existing content before modifying. | P0 |
| BST_FMT_2 | Writes: `.plet/` (dir), `.gitignore`, `.gitattributes`, `.git/config` (merge driver), `.claude/settings.json`, `CLAUDE.md` | P0 |

## 7. Agent Flows (BST_AFL)

| ID | Flow | Steps |
|----|------|-------|
| BST_AFL_1 | Plan phase setup | 1. User runs `/plet` or `/plet plan`. 2. SKILL.md agent calls `plet_bootstrap.py setup .` 3. Bootstrap copies scripts, configures git. 4. Agent proceeds to plan session. |
| BST_AFL_2 | Preflight triggers setup | 1. User runs `/plet loop`. 2. Preflight calls `plet_bootstrap.py check .` → FAIL (missing config). 3. SKILL.md agent calls `plet_bootstrap.py setup .` 4. Re-runs preflight → pass. 5. Proceeds to loop. |

## 8. Examples (BST_EXM)

```bash
# Full project bootstrap
plet_bootstrap.py setup .
# created: .plet/ directory
# created: .gitignore (3 entries: .plet/, .claude/settings.local.json, CLAUDE.local.md)
# configured: merge driver (plet-append)
# configured: .gitattributes (3 entries)
# created: CLAUDE.md (plet stub with script discovery)
# configured: .claude/settings.json (added plet allow entries)
# warn: permissions — bypassPermissions not set (subagents need autonomous access)
#
# Bootstrap complete: 3 created, 2 configured, 1 warning

# Check bootstrap state
plet_bootstrap.py check .
# pass: .plet/ directory exists
# pass: .gitignore (3 entries present)
# pass: merge driver configured
# pass: .gitattributes configured
# pass: CLAUDE.md exists
# pass: .claude/settings.json has plet allow entries
# warn: permissions — bypassPermissions not set
# pass: git user.email configured
# pass: git user.name configured
# pass: git repo exists
# 9 passed, 0 failed, 1 warning

# Re-run (idempotent)
plet_bootstrap.py setup .
# skipped: .plet/ (exists)
# skipped: .gitignore (entries present)
# skipped: merge driver (configured)
# skipped: .gitattributes (configured)
# skipped: CLAUDE.md (exists)
# skipped: .claude/settings.json (plet entries present)
#
# Bootstrap complete: 0 created, 0 configured, 6 skipped
```

## 9. Dependencies (BST_DEP)

| ID | Dependency | Direction | Description |
|----|------------|-----------|-------------|
| BST_DEP_1 | Own `__file__` path | reads | Derives scripts dir location for CLAUDE.md stub content |
| BST_DEP_2 | `util_cli.py` | imports | Argument parsing, dispatch, output formatting |
| BST_DEP_3 | `plet_gate_session.py` | called by | Preflight can call `check` to verify bootstrap state |
| BST_DEP_4 | SKILL.md | called by | Plan phase and preflight-triggered setup |

## 10. Non-Functional Requirements (BST_NFR)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_NFR_1 | Zero external dependencies — Python stdlib only | P0 |
| BST_NFR_2 | Python 3.8+ compatible | P0 |
| BST_NFR_3 | Executable with shebang, `chmod +x` | P0 |
| BST_NFR_4 | Fast — git config + file creates, should complete in < 2 seconds | P0 |

## 11. Developer Experience (BST_DXP)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_DXP_1 | `--help` on every command with examples | P0 |
| BST_DXP_2 | `--version` | P0 |
| BST_DXP_3 | Clear per-action output so user sees what happened | P0 |

## 12. Critical Test Areas (BST_CRT)

| ID | Test Area | Why |
|----|-----------|-----|
| BST_CRT_1 | Idempotent — second run no-ops | Must be safe to re-run |
| BST_CRT_2 | .gitignore doesn't ignore plet/ | Would break state tracking |
| BST_CRT_3 | CLAUDE.md not overwritten | Would destroy user content |
| BST_CRT_4 | Permissions check detects sandbox-only | Would let user start loop that will fail |
| BST_CRT_5 | .claude/settings.json merges, not overwrites | Would destroy user's existing allow entries |
| BST_CRT_6 | CLAUDE.md includes script discovery path | Subagents waste 8+ minutes without it |

## 13. Testing & Verification (BST_TST)

| ID | Requirement | Priority |
|----|-------------|----------|
| BST_TST_1 | Test file: `skills/plet/tests/test_plet_bootstrap.py` | P0 |
| BST_TST_2 | Tests call script via subprocess | P0 |
| BST_TST_3 | Temp git repos per test | P0 |
| BST_TST_4 | Test both setup and check commands | P0 |

## 14. Resolved Questions

| # | Question | Resolution |
|---|----------|------------|
| 1 | Where to put scripts? | Don't copy — subagents discover via prompt (seq 44). Bootstrap focuses on project infrastructure. Script copying is BST_FUT_2 (offline backup). |
| 2 | When does bootstrap run? | Plan phase (once per project), or when preflight detects missing artifacts. |
| 3 | New script or existing command? | New script `plet_bootstrap.py` — clear purpose, discoverable. |
| 4 | `--force` overwrite CLAUDE.md? | No — CLAUDE.md is user content, never overwritten even with `--force`. |

## 15. Future Considerations (BST_FUT)

| ID | Consideration |
|----|---------------|
| BST_FUT_1 | `start-session` could call `plet_bootstrap.py check` and auto-run `setup` if needed. Ensures every loop starts with correct bootstrap state. |
| BST_FUT_2 | Copy scripts to `.plet/scripts/` as offline backup. Not needed for discovery (prompt includes path), but useful if user runs on a machine without the plet plugin installed. Would need to handle .gitignore and worktree visibility. |
| BST_FUT_3 | Copy reference files (implement.md, verify.md, state-schema.md) into `.plet/references/` for subagent access. |

## 16. Open Questions

| # | Question | Context |
|---|----------|---------|
| 1 | What goes in the CLAUDE.md stub? | Must include script discovery instructions with fallback chain: (1) `CLAUDE_SKILL_DIR` env var (most direct), (2) `CLAUDE_CONFIG_DIR` + plugin cache path, (3) `~/.claude` + plugin cache path (default). Plet conventions, pointer to plet/ state. Template TBD. |
| 2 | Should bootstrap check Python version? | Scripts require 3.8+. If the target project's Python is older, scripts will fail with syntax errors. A quick `python3 --version` check could prevent confusing failures. |
| 3 | What allow patterns for .claude/settings.json? | Need to figure out the right pattern. `Bash(${CLAUDE_SKILL_DIR}/scripts/plet_*.py *)` uses the env var. But if scripts are called by absolute path from the prompt, the pattern may differ. |
