# logalyzer

A CLI tool for searching, filtering, and summarizing structured log files in NDJSON format.

## Overview

logalyzer reads NDJSON log files, parses them into a uniform internal representation, and supports searching, filtering, and aggregation. Output is human-readable text or JSON.

Designed for developers and operators who need to quickly find relevant log entries, spot patterns, and summarize log data without a full log management stack.

## Setup

Requires Go 1.26+.

```bash
go build ./cmd/logalyzer
```

## Usage

```bash
# Search for errors
logalyzer search --level error app.log

# Keyword search with time range
logalyzer search --search "timeout" --from 2026-03-08T00:00:00Z app.log

# Summary of a log file
logalyzer summary app.log

# JSON output for piping
logalyzer search --level warn,error --json app.log | jq '.message'

# Version
logalyzer --version
```

## Running Tests

```bash
go test ./...
```

## Project Structure

```
logalyzer/
├── cmd/logalyzer/       # CLI entry point
├── internal/
│   ├── parser/          # NDJSON parser, format normalization
│   ├── filter/          # Filter and search logic
│   ├── aggregate/       # Aggregation and summary
│   └── output/          # Text and JSON formatters
├── go.mod
├── CLAUDE.md
├── PLET.md
└── README.md
```
