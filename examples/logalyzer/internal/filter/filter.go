// Package filter provides search and filter operations for parsed log entries.
package filter

import (
	"strings"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// Filter is the interface implemented by all log entry filters.
type Filter interface {
	// Match returns true if the entry passes this filter.
	Match(entry parser.LogEntry) bool
}

// Apply filters entries through a set of filters, returning only entries
// that match all filters (AND semantics).
func Apply(entries []parser.LogEntry, filters ...Filter) []parser.LogEntry {
	var result []parser.LogEntry
	for _, e := range entries {
		pass := true
		for _, f := range filters {
			if !f.Match(e) {
				pass = false
				break
			}
		}
		if pass {
			result = append(result, e)
		}
	}
	return result
}

// LevelFilter matches entries whose level is one of the specified levels.
// Matching is case-insensitive.
type LevelFilter struct {
	levels map[string]bool
}

// NewLevelFilter creates a LevelFilter that matches any of the given levels.
// Levels are compared case-insensitively.
func NewLevelFilter(levels []string) *LevelFilter {
	m := make(map[string]bool, len(levels))
	for _, l := range levels {
		m[strings.ToLower(l)] = true
	}
	return &LevelFilter{levels: m}
}

// Match returns true if the entry's level matches one of the filter's levels.
func (f *LevelFilter) Match(entry parser.LogEntry) bool {
	return f.levels[strings.ToLower(entry.Level)]
}

// TimeRangeFilter matches entries whose timestamp falls within the specified range.
// Zero values for From or To indicate an open-ended range.
type TimeRangeFilter struct {
	From time.Time
	To   time.Time
}

// NewTimeRangeFilter creates a TimeRangeFilter with the given bounds.
// Pass zero time for either bound to leave that side open.
func NewTimeRangeFilter(from, to time.Time) *TimeRangeFilter {
	return &TimeRangeFilter{From: from, To: to}
}

// Match returns true if the entry's timestamp is within the filter's range.
func (f *TimeRangeFilter) Match(entry parser.LogEntry) bool {
	if !f.From.IsZero() && entry.Timestamp.Before(f.From) {
		return false
	}
	if !f.To.IsZero() && entry.Timestamp.After(f.To) {
		return false
	}
	return true
}

// KeywordFilter matches entries that contain the keyword in any string field.
// Matching is case-insensitive.
type KeywordFilter struct {
	keyword string
}

// NewKeywordFilter creates a KeywordFilter for the given keyword.
// Matching is case-insensitive.
func NewKeywordFilter(keyword string) *KeywordFilter {
	return &KeywordFilter{keyword: strings.ToLower(keyword)}
}

// Match returns true if the keyword appears in any string field of the entry.
func (f *KeywordFilter) Match(entry parser.LogEntry) bool {
	lower := strings.ToLower
	kw := f.keyword

	if strings.Contains(lower(entry.Level), kw) {
		return true
	}
	if strings.Contains(lower(entry.Message), kw) {
		return true
	}
	for _, v := range entry.Extra {
		if s, ok := v.(string); ok {
			if strings.Contains(lower(s), kw) {
				return true
			}
		}
	}
	return false
}
