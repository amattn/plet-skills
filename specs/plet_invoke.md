# plet_invoke.py (INV)

> Status: not started

> Subprocess launch + transcript capture. Assembles prompt (via plet_inject_prompt.py), launches `claude -p --output-format stream-json`, tees streaming JSONL to transcript file, returns exit code. This replaces the vague "orchestrator captures transcript" responsibility with deterministic code.

> **Design notes (from other specs):**
> - Use `claude --enable-auto-mode` for subprocess permissions (not `--dangerously-skip-permissions`). Auto-mode is safer — tracks and logs approvals. See https://claude.com/blog/auto-mode. Replaces FB_22 bypassPermissions approach.
> - Investigate sandboxing for subprocess isolation: https://code.claude.com/docs/en/sandboxing — may provide additional safety guarantees for autonomous execution.
> - Flush after each line write for GUI live-tail (specs/NOTES.md § Transcript capture mechanics).
> - Line-by-line capture from subprocess stdout — synchronous, no data loss.
> - Needs a flag for alternative Claude Code config directories (e.g., `--config-dir`). Users with non-default `CLAUDE_CONFIG_DIR` (such as `~/.claude-work` or `~/.claude-personal`) need the subprocess to use the same config dir for settings, plugins, and skills to resolve correctly.
