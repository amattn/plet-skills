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
