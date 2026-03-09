package main

import (
	"flag"
	"fmt"
	"os"
	"sort"
	"strings"
	"time"

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
	jsonOut := fs.Bool("json", false, "output each matching entry as a JSON object, one per line")
	caseSensitive := fs.Bool("case-sensitive", false, "make --keyword match case-sensitive (default is case-insensitive)")
	regex := fs.String("regex", "", "filter entries matching a regex across string fields")
	invert := fs.Bool("invert", false, "show entries that do NOT match the other filters")
	histogramFlag := fs.Bool("histogram", false, "produce a time-bucketed histogram of entry counts")
	bucketFlag := fs.String("bucket", "1h", "bucket duration for histogram (e.g., 1m, 5m, 1h)")

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
		if *caseSensitive {
			filters = append(filters, filter.NewCaseSensitiveKeywordFilter(*keyword))
		} else {
			filters = append(filters, filter.NewKeywordFilter(*keyword))
		}
	}
	if *regex != "" {
		rf, regexErr := filter.NewRegexFilter(*regex)
		if regexErr != nil {
			// 849271365042 — invalid regex pattern in search command
			fmt.Fprintf(os.Stderr, "error [849271365042]: %v\n", regexErr)
			return 1
		}
		filters = append(filters, rf)
	}
	// --invert: wrap all collected filters in an InvertFilter
	if *invert && len(filters) > 0 {
		combined := &compositeFilter{filters: filters}
		filters = []filter.Filter{filter.NewInvertFilter(combined)}
	}
	if len(filters) > 0 {
		entries = filter.Apply(entries, filters...)
	}

	// --histogram: produce time-bucketed histogram
	if *histogramFlag {
		bucketDuration, parseErr := time.ParseDuration(*bucketFlag)
		if parseErr != nil {
			// 572918340625 — invalid bucket duration for histogram
			fmt.Fprintf(os.Stderr, "error [572918340625]: invalid bucket duration %q: %v\n", *bucketFlag, parseErr)
			return 1
		}
		buckets := aggregate.Histogram(entries, bucketDuration)
		fmt.Print(aggregate.FormatHistogram(buckets))
		return 0
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

	// Detect TTY for color output (OU_3)
	colorEnabled := output.IsTerminal(os.Stdout)

	// Output entries: JSON when --json or --fields, text otherwise
	for _, e := range entries {
		if *jsonOut || len(fieldList) > 0 {
			fmt.Println(output.FormatEntryJSON(e, fieldList))
		} else {
			if err := output.StreamEntry(os.Stdout, e, colorEnabled); err != nil {
				// 285917463021 — write error during search output
				fmt.Fprintf(os.Stderr, "error [285917463021]: write failed: %v\n", err)
				return 1
			}
		}
	}

	return 0
}

// compositeFilter combines multiple filters with AND semantics into a single Filter.
// Used internally to wrap filters before inverting with --invert.
type compositeFilter struct {
	filters []filter.Filter
}

// Match returns true if all inner filters match the entry.
func (c *compositeFilter) Match(entry parser.LogEntry) bool {
	for _, f := range c.filters {
		if !f.Match(entry) {
			return false
		}
	}
	return true
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
