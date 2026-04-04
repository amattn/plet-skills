# plet CLI Cheat Sheet

Compact reference for all plet script commands. Escalation: this file → `--usage` → `--help`.

Scripts are at `${CLAUDE_SKILL_DIR}/scripts/` or `$PLET_SCRIPTS_DIR` (env var injected by orchestrator).

---

## Subagent Commands (implement + verify)

### Phase end (replaces 6 separate calls)

```
plet_phase.py end <plet_dir> --iter-id ID_xxx --phase implement --verdict completed --progress-content "..."
plet_phase.py end <plet_dir> --iter-id ID_xxx --phase verify --verdict passed --progress-content "..." --report-file /tmp/report.json
```

Implement verdicts: `completed`, `blocked`
Verify verdicts: `passed`, `rejected`, `blocked`

### State updates

```
plet_iter_state.py update-activity <plet_dir> --iter-id ID_xxx --phase-activity VALUE --activity-detail "..." --agent-id ID
plet_iter_state.py update-criterion <plet_dir> --iter-id ID_xxx --criterion AC_N --phase implementation|verification --status pass|fail --evidence "..." --agent-id ID
# verification fail: --red-test TEST_NAME|none  required; if --red-test none also requires --no-test-rationale "..."
# optional: --one-liner "..."  (short summary stored on criterion)
plet_iter_state.py set-verdict <plet_dir> --iter-id ID_xxx --phase implement|verify --verdict VALUE --agent-id ID
plet_iter_state.py heartbeat <plet_dir> --iter-id ID_xxx --agent-id ID
plet_iter_state.py add-report <plet_dir> --iter-id ID_xxx --verdict VALUE --summary "..." --criteria-results '[...]' --findings '[...]' --related-entries '[...]' --agent-id ID
plet_iter_state.py validate <plet_dir> --iter-id ID_xxx
```

### Runtime artifacts

```
plet_entries.py add-progress <plet_dir> --iter-id ID_xxx --iter-title "..." --phase implement --attempt N --status STATUS --content "..."
plet_entries.py add-learning <plet_dir> --iter-id ID_xxx --iter-title "..." --category CATEGORY --title "..." --content "..." --phase implement --attempt N
plet_entries.py add-emergent <plet_dir> --iter-id ID_xxx --iter-title "..." --title "..." --phase implement --category "CATEGORY" --content "..." --attempt N
plet_entries.py check <plet_dir> --iter-id ID_xxx
```

Status values: `IN_PROGRESS`, `COMPLETE`, `BLOCKED`, `FAILED`, `SKIPPED`, `MIGRATED`
Category values (learning): `pattern`, `gotcha`, `technique`, `tool`, `debug`, `context`
Category values (emergent): `design decision`, `spec gap`, `requirement change`, `process issue`, `tech debt`

### Trace events

```
plet_trace.py append-event <plet_dir> --iter-id ID_xxx --phase implement --attempt N --event-type TYPE --data '{...}'
plet_trace.py validate <plet_dir> --iter-id ID_xxx --phase implement --attempt N
plet_trace.py query <plet_dir> --iter-id ID_xxx --phase implement --attempt N [--event-type TYPE]
```

Event types: `decision`, `criterion_update`, `lifecycle_change`, `activity_change`, `error`, `invocation`

### Gate checks

```
plet_gate_phase.py pre <plet_dir> --iter-id ID_xxx --phase implement
plet_gate_phase.py post <plet_dir> --iter-id ID_xxx --phase implement --output json
```

### Git operations

```
plet_git_ops.py audit-tag <plet_dir> --iter-id ID_xxx --phase implement
plet_git_ops.py merge-squash <plet_dir> --iter-id ID_xxx
plet_git_check.py check-iteration <plet_dir> --iter-id ID_xxx --phase implement
```

---

## Orchestrator / SKILL.md Commands

These are called by the orchestrator or SKILL.md agent, not by implement/verify subagents.

### Session lifecycle

```
plet_session.py start-session <plet_dir> --type loop|refine
plet_session.py end-session <plet_dir>
plet_gate_session.py detect <plet_dir>
plet_gate_session.py status <plet_dir>
plet_gate_session.py preflight <plet_dir> --session-type loop
plet_gate_session.py postflight <plet_dir> --session-type loop
```

### Scheduling

```
plet_schedule.py eligible <plet_dir>
plet_schedule.py check-breakpoints <plet_dir> --iter-id ID_xxx --position before|after
plet_schedule.py check-retry <plet_dir> --iter-id ID_xxx
```

### Orchestrator loop

```
plet_orchestrator.py run <plet_dir> [--allow-stale] [--sequential] [--output ndjson]
```

### State management

```
plet_global_state.py init <plet_dir> --project-id PROJ --project-name "..." --dependency-map '{...}' --milestones '{...}' --iterations-fingerprint '{...}'
plet_global_state.py update-lifecycle <plet_dir> --iter-id ID_xxx --lifecycle VALUE
plet_global_state.py get-lifecycle <plet_dir> [--iter-id ID_xxx]
plet_global_state.py validate <plet_dir>
plet_iter_state.py init <plet_dir> --iter-id ID_xxx --title "..." --dependencies '[]' --criteria '[...]'
plet_iter_state.py start-phase <plet_dir> --iter-id ID_xxx --phase implement
```

Lifecycle values: `queued`, `implementing`, `verifying`, `complete`, `blocked`, `withdrawn`, `ineligible`

### Worktrees

```
plet_git_iteration.py branch-name <plet_dir> --iter-id ID_xxx
plet_git_iteration.py worktree-create <plet_dir> --iter-id ID_xxx
plet_git_iteration.py worktree-remove <plet_dir> --iter-id ID_xxx
plet_git_check.py check-session <plet_dir>
```

### Fingerprints

```
plet_fingerprint.py extract <plet_dir> --type requirements|iterations
plet_fingerprint.py embed <plet_dir> --type requirements|iterations|state
plet_fingerprint.py check <plet_dir>
```

### Prompt assembly

```
plet_prompt.py assemble <plet_dir> --iter-id ID_xxx --phase implement|verify
```

### Bootstrap

```
plet_bootstrap.py setup <project_dir>
plet_bootstrap.py check <project_dir>
```

---

## Universal Flags

All scripts support: `--help`, `--version`, `--usage`
Most commands support: `--output json [--pretty] [--fields f1,f2]`
Mutating commands support: `--dry-run`
