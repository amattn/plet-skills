# CLAUDE.md

## Project

logalyzer — CLI tool for searching, filtering, and summarizing NDJSON log files.

## Language & Build

- Go 1.26+
- Build: `go build ./cmd/logalyzer`
- Test: `go test ./...`
- No external dependencies — stdlib only

## Key Commands

| Command | Purpose |
|---------|---------|
| `go build ./...` | Verify compilation |
| `go test ./...` | Run full test suite |
| `gofmt -l .` | Check formatting |
| `gofmt -w .` | Fix formatting |
| `go vet ./...` | Static analysis |

## Project Structure

- `cmd/logalyzer/` — CLI entry point, flag parsing, subcommand routing
- `internal/parser/` — NDJSON parser, field alias resolution, timestamp normalization
- `internal/filter/` — Filter and search logic
- `internal/aggregate/` — Aggregation and summary
- `internal/output/` — Text and JSON formatters

## Conventions

- Follow Go conventions (effective Go, standard project layout)
- All exported functions and types include Go doc comments
- Every error string includes a unique random 12-digit debug number, never reused
- No external runtime dependencies — prefer the Go standard library
- Test names include the requirement ID they verify (e.g., `TestLP1_ParseValidNDJSON`)

## plet

This project is managed by the plet development loop. See `PLET.md` for plet-specific context.
