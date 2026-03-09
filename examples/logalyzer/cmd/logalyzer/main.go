// Package main is the entry point for the logalyzer CLI tool.
package main

import (
	"fmt"
	"os"
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

	fmt.Fprintln(os.Stderr, "logalyzer — structured log analysis tool")
	fmt.Fprintln(os.Stderr, "Run with --version for version info.")
	return 0
}
