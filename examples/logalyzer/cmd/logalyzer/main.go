// Package main is the entry point for the logalyzer CLI tool.
package main

import (
	"fmt"
	"os"

	"github.com/amattn/logalyzer/internal/aggregate"
	"github.com/amattn/logalyzer/internal/parser"
)

// Version is the current version of logalyzer.
// This is set at build time or defaults to the dev version below.
var Version = "v0.1.0-dev"

func main() {
	exitCode := run(os.Args[1:])
	os.Exit(exitCode)
}

// run contains the main application logic and returns an exit code.
// Separating this from main() enables testing.
func run(args []string) int {
	for _, arg := range args {
		if arg == "--version" || arg == "-v" {
			fmt.Printf("logalyzer %s\n", Version)
			return 0
		}
	}

	if len(args) < 1 {
		fmt.Fprintln(os.Stderr, "logalyzer — structured log analysis tool")
		fmt.Fprintln(os.Stderr, "Run with --version for version info.")
		return 0
	}

	switch args[0] {
	case "summary":
		return runSummary(args[1:])
	case "search":
		return runSearch(args[1:])
	default:
		// 384729156032 — unknown subcommand
		fmt.Fprintf(os.Stderr, "error [384729156032]: unknown command %q\n", args[0])
		return 1
	}
}

// runSummary implements the 'summary' subcommand, which parses an NDJSON file
// and prints a human-readable summary to stdout.
func runSummary(args []string) int {
	if len(args) < 1 {
		// 927461538204 — missing file argument for summary
		fmt.Fprintln(os.Stderr, "error [927461538204]: summary requires a file argument")
		fmt.Fprintln(os.Stderr, "usage: logalyzer summary <file>")
		return 1
	}

	filePath := args[0]
	f, err := os.Open(filePath)
	if err != nil {
		// 615283947120 — could not open file for summary
		fmt.Fprintf(os.Stderr, "error [615283947120]: could not open file %q: %v\n", filePath, err)
		return 1
	}
	defer f.Close()

	result, err := parser.ParseNDJSONResult(f)
	if err != nil {
		// 843172906534 — parse error during summary
		fmt.Fprintf(os.Stderr, "error [843172906534]: failed to parse %q: %v\n", filePath, err)
		return 1
	}

	summary := aggregate.Summarize(result.Entries, result.ParseErrors)
	fmt.Print(summary.Format())
	return 0
}
