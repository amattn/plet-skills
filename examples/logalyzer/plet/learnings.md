# Learnings

plet v1.0.0

<div id="plet-eln_01JD9X1001_id001_i1"></div>

---

### [gotcha] GOROOT needs explicit setting
**PletId:** `eln_01JD9X1001_id001_i1`
**Iteration:** [ID_001]
**Timestamp:** 2026-03-09T09:05:00Z

The system has a stale GOROOT env var pointing to `/Users/kai/BTSync/gostuff/go/` which causes `go build` to fail with "package fmt is not in std". Fix: prefix commands with `GOROOT=/usr/local/go` or ensure the environment is clean. This affects all Go commands (build, test, vet, etc.).

<div id="END-plet-eln_01JD9X1001_id001_i1"></div>

<div id="plet-eln_01JD9X2002_id001_v1"></div>

---

### [practice] Testable main pattern works well for CLI verification
**PletId:** `eln_01JD9X2002_id001_v1`
**Iteration:** [ID_001]
**Timestamp:** 2026-03-09T08:00:19Z

The `run(args []string) int` pattern separating logic from `main()` is effective but the test (TestVersionFlag) still builds a binary and uses exec.Command. For simple flag tests, testing the `run` function directly would be faster and avoid build overhead. Consider this approach for future iterations.

<div id="END-plet-eln_01JD9X2002_id001_v1"></div>

## ID_002 Learnings
- **Testability pattern:** Wrapping `ParseNDJSON(r)` around `ParseNDJSONWithWarnings(r, warnWriter)` cleanly separates stderr coupling from test assertions. Good pattern for any function that writes warnings.
- **Non-string well-known fields:** Implementation gracefully handles cases where e.g. `"level"` is a number instead of string by putting it in Extra. This is defensive and spec-compatible.
