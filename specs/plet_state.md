# plet_state.py

> Status: in progress — retroactive spec. Script exists, spec documenting current behavior + known issues.

## Audit Findings (2026-03-15)

Audited against `specs/conventions.md`. 28 PASS, 2 FAIL, 2 N/A.

### Failures

| ID | Issue | Fix |
|----|-------|-----|
| UNV_NFR_2 | `cmd_init` doesn't check if file exists — silently overwrites | Add `os.path.exists(path)` check, error if file exists |
| UNV_TST_7 | `--help` not tested for `update-criterion` or `update-field`; `--version` not tested | Add missing test cases |

### Cross-Script Inconsistencies

1. **No shared `parse_kwargs` function** — `cmd_init` duplicates the logic inline. Should extract and reuse the `parse_kwargs` pattern from `plet_entries.py`.
2. **`update-criterion` uses 5 positional args** — all `plet_entries.py` commands use 1 positional + named args. Should migrate to `--criterion-id AC_1 --phase implementation --status pass --evidence "..."`.
3. **`update-field` uses alternating positional pairs without `--`** — a third parsing pattern. Should migrate to `--field lifecycle --value implementing` or keep the current ergonomic pattern but document it as an intentional exception.
4. **Inline kwarg parser doesn't support boolean flags** — `plet_entries.py`'s `parse_kwargs` does.
