package main

import (
	"flag"
	"fmt"
	"os"
	"sort"
	"strings"

	"github.com/amattn/logalyzer/internal/aggregate"
	"github.com/amattn/logalyzer/internal/filter"
	"github.com/amattn/logalyzer/internal/output"
	"github.com/amattn/logalyzer/internal/parser"
)

// runSearch implements the 'search' subcommand, which parses an NDJSON file,
// applies optional filters, and outputs results with optional grouping,
// field selection, limiting, or counting.
func runSearch(args []string) int {
	fs := flag.NewFlagSet("search", flag.ContinueOnError)

	groupBy := fs.String("group-by", "", "group and count entries by field value")
	fields := fs.String("fields", "", "comma-separated list of fields to display")
	limit := fs.Int("limit", 0, "maximum number of entries to output (0 = no limit)")
	count := fs.Bool("count", false, "output only the count of matching entries")
	level := fs.String("level", "", "filter by log level (comma-separated)")
	keyword := fs.String("keyword", "", "filter by keyword in any string field")

	if err := fs.Parse(args); err != nil {
		// 529174836201 — flag parse error in search
		fmt.Fprintf(os.Stderr, "error [529174836201]: %v\n", err)
		return 1
	}

	if fs.NArg() < 1 {
		// 641829375064 — missing file argument for search
		fmt.Fprintln(os.Stderr, "error [641829375064]: search requires a file argument")
		fmt.Fprintln(os.Stderr, "usage: logalyzer search [flags] <file>")
		return 2
	}

	filePath := fs.Arg(0)
	f, err := os.Open(filePath)
	if err != nil {
		// 718293465120 — could not open file for search
		fmt.Fprintf(os.Stderr, "error [718293465120]: could not open file %q: %v\n", filePath, err)
		return 1
	}
	defer f.Close()

	entries, err := parser.ParseNDJSONWithWarnings(f, os.Stderr)
	if err != nil {
		// 394817256031 — parse error during search
		fmt.Fprintf(os.Stderr, "error [394817256031]: failed to parse %q: %v\n", filePath, err)
		return 1
	}

	// Apply filters
	var filters []filter.Filter
	if *level != "" {
		levels := strings.Split(*level, ",")
		filters = append(filters, filter.NewLevelFilter(levels))
	}
	if *keyword != "" {
		filters = append(filters, filter.NewKeywordFilter(*keyword))
	}
	if len(filters) > 0 {
		entries = filter.Apply(entries, filters...)
	}

	// --count: output just the count
	if *count {
		fmt.Println(output.CountEntries(entries))
		return 0
	}

	// --group-by: group and count by field
	if *groupBy != "" {
		counts := aggregate.GroupBy(entries, *groupBy)
		printGroupByCounts(counts)
		return 0
	}

	// --limit: cap the number of entries
	entries = output.LimitEntries(entries, *limit)

	// Parse field list
	var fieldList []string
	if *fields != "" {
		fieldList = strings.Split(*fields, ",")
	}

	// Output entries
	for _, e := range entries {
		fmt.Println(output.FormatEntryJSON(e, fieldList))
	}

	return 0
}

// printGroupByCounts prints group-by results sorted by key.
func printGroupByCounts(counts map[string]int) {
	keys := make([]string, 0, len(counts))
	for k := range counts {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	for _, k := range keys {
		displayKey := k
		if displayKey == "" {
			displayKey = "(empty)"
		}
		fmt.Printf("%s: %d\n", displayKey, counts[k])
	}
}
