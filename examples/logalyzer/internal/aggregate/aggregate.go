// Package aggregate provides summary and aggregation functions for parsed log entries.
package aggregate

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// Summary holds aggregated statistics about a set of log entries.
type Summary struct {
	// TotalCount is the number of successfully parsed log entries.
	TotalCount int
	// LevelCounts maps each severity level to the number of entries with that level.
	LevelCounts map[string]int
	// Earliest is the earliest timestamp found in the entries (zero if no timestamps).
	Earliest time.Time
	// Latest is the latest timestamp found in the entries (zero if no timestamps).
	Latest time.Time
	// ParseErrorCount is the number of malformed lines that could not be parsed.
	ParseErrorCount int
}

// Summarize computes aggregate statistics over a set of log entries.
// parseErrors is the number of malformed lines that were skipped during parsing.
func Summarize(entries []parser.LogEntry, parseErrors int) *Summary {
	s := &Summary{
		TotalCount:      len(entries),
		LevelCounts:     make(map[string]int),
		ParseErrorCount: parseErrors,
	}

	for _, e := range entries {
		s.LevelCounts[e.Level]++

		if !e.Timestamp.IsZero() {
			if s.Earliest.IsZero() || e.Timestamp.Before(s.Earliest) {
				s.Earliest = e.Timestamp
			}
			if s.Latest.IsZero() || e.Timestamp.After(s.Latest) {
				s.Latest = e.Timestamp
			}
		}
	}

	return s
}

// Format returns a human-readable text representation of the summary.
func (s *Summary) Format() string {
	var b strings.Builder

	// 491827364051 — summary format header
	fmt.Fprintf(&b, "=== Log Summary ===\n")
	fmt.Fprintf(&b, "Total entries: %d\n", s.TotalCount)
	fmt.Fprintf(&b, "Parse errors:  %d\n", s.ParseErrorCount)

	if !s.Earliest.IsZero() && !s.Latest.IsZero() {
		fmt.Fprintf(&b, "Time range:    %s to %s\n", s.Earliest.Format(time.RFC3339), s.Latest.Format(time.RFC3339))
	} else {
		fmt.Fprintf(&b, "Time range:    (no timestamps)\n")
	}

	fmt.Fprintf(&b, "\nCounts by level:\n")
	if len(s.LevelCounts) == 0 {
		fmt.Fprintf(&b, "  (none)\n")
	} else {
		// Sort levels for deterministic output
		levels := make([]string, 0, len(s.LevelCounts))
		for lvl := range s.LevelCounts {
			levels = append(levels, lvl)
		}
		sort.Strings(levels)
		for _, lvl := range levels {
			displayLvl := lvl
			if displayLvl == "" {
				displayLvl = "(unknown)"
			}
			fmt.Fprintf(&b, "  %-12s %d\n", displayLvl, s.LevelCounts[lvl])
		}
	}

	return b.String()
}
