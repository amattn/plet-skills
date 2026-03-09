# PLET.md — plet-specific context for logalyzer

## Verification Commands

| Command | Purpose |
|---------|---------|
| `go build ./...` | Verify compilation |
| `go test ./...` | Run full test suite |
| `gofmt -l .` | Check formatting (should output nothing) |
| `go vet ./...` | Static analysis |

## Iteration Conventions

- Branch per iteration: `plet/loop/{iteration_id}`
- Commit convention: `plet: [ID_xxx] {phase}-{attempt} - {title}`
- State files: `plet/state/{iteration_id}.json`
- Runtime artifacts: `plet/progress.md`, `plet/learnings.md`, `plet/emergent.md`

## Key Files

- `plet/requirements.md` — full requirements (PRD)
- `plet/iterations.md` — iteration definitions with acceptance criteria
- `plet/state.json` — global state and dependency map

## Environment Notes

- Go 1.26+ required
- GOROOT may need explicit setting: `GOROOT=/usr/local/go`
- No external dependencies — stdlib only
