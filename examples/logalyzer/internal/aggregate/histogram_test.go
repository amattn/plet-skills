package aggregate

import (
	"testing"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// makeHistogramEntries returns log entries spread across multiple hours for histogram testing.
func makeHistogramEntries() []parser.LogEntry {
	return []parser.LogEntry{
		{Level: "info", Message: "a", Timestamp: time.Date(2025, 1, 1, 10, 5, 0, 0, time.UTC)},
		{Level: "info", Message: "b", Timestamp: time.Date(2025, 1, 1, 10, 15, 0, 0, time.UTC)},
		{Level: "warn", Message: "c", Timestamp: time.Date(2025, 1, 1, 10, 45, 0, 0, time.UTC)},
		{Level: "error", Message: "d", Timestamp: time.Date(2025, 1, 1, 11, 10, 0, 0, time.UTC)},
		{Level: "info", Message: "e", Timestamp: time.Date(2025, 1, 1, 12, 30, 0, 0, time.UTC)},
	}
}

// TestAG5_HistogramHourBuckets verifies that Histogram produces correct hourly buckets (AC_1, AC_2).
func TestAG5_HistogramHourBuckets(t *testing.T) {
	entries := makeHistogramEntries()
	buckets := Histogram(entries, time.Hour)

	if len(buckets) != 3 {
		t.Fatalf("expected 3 hourly buckets, got %d", len(buckets))
	}

	// Bucket 0: 10:00-11:00 (3 entries)
	if buckets[0].Count != 3 {
		t.Errorf("bucket[0] count: expected 3, got %d", buckets[0].Count)
	}
	expectedStart := time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC)
	if !buckets[0].Start.Equal(expectedStart) {
		t.Errorf("bucket[0] start: expected %v, got %v", expectedStart, buckets[0].Start)
	}

	// Bucket 1: 11:00-12:00 (1 entry)
	if buckets[1].Count != 1 {
		t.Errorf("bucket[1] count: expected 1, got %d", buckets[1].Count)
	}

	// Bucket 2: 12:00-13:00 (1 entry)
	if buckets[2].Count != 1 {
		t.Errorf("bucket[2] count: expected 1, got %d", buckets[2].Count)
	}
}

// TestAG5_HistogramMinuteBuckets verifies that Histogram produces correct minute-level buckets (AC_1, AC_2).
func TestAG5_HistogramMinuteBuckets(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "a", Timestamp: time.Date(2025, 1, 1, 10, 0, 15, 0, time.UTC)},
		{Level: "info", Message: "b", Timestamp: time.Date(2025, 1, 1, 10, 0, 45, 0, time.UTC)},
		{Level: "info", Message: "c", Timestamp: time.Date(2025, 1, 1, 10, 1, 30, 0, time.UTC)},
		{Level: "info", Message: "d", Timestamp: time.Date(2025, 1, 1, 10, 3, 0, 0, time.UTC)},
	}
	buckets := Histogram(entries, time.Minute)

	if len(buckets) != 4 {
		t.Fatalf("expected 4 minute buckets (10:00, 10:01, 10:02, 10:03), got %d", len(buckets))
	}

	if buckets[0].Count != 2 {
		t.Errorf("bucket 10:00 count: expected 2, got %d", buckets[0].Count)
	}
	if buckets[1].Count != 1 {
		t.Errorf("bucket 10:01 count: expected 1, got %d", buckets[1].Count)
	}
	if buckets[2].Count != 0 {
		t.Errorf("bucket 10:02 count: expected 0, got %d", buckets[2].Count)
	}
	if buckets[3].Count != 1 {
		t.Errorf("bucket 10:03 count: expected 1, got %d", buckets[3].Count)
	}
}

// TestAG5_HistogramFiveMinuteBuckets verifies that custom durations like 5m work (AC_2).
func TestAG5_HistogramFiveMinuteBuckets(t *testing.T) {
	entries := makeHistogramEntries()
	buckets := Histogram(entries, 5*time.Minute)

	if len(buckets) < 3 {
		t.Errorf("expected at least 3 five-minute buckets, got %d", len(buckets))
	}
}

// TestAG5_HistogramChronologicalOrder verifies buckets are sorted chronologically (AC_3).
func TestAG5_HistogramChronologicalOrder(t *testing.T) {
	// Provide entries out of chronological order
	entries := []parser.LogEntry{
		{Level: "info", Message: "late", Timestamp: time.Date(2025, 1, 1, 14, 0, 0, 0, time.UTC)},
		{Level: "info", Message: "early", Timestamp: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC)},
		{Level: "info", Message: "mid", Timestamp: time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC)},
	}
	buckets := Histogram(entries, time.Hour)

	for i := 1; i < len(buckets); i++ {
		if !buckets[i].Start.After(buckets[i-1].Start) {
			t.Errorf("buckets not chronological: bucket[%d].Start=%v >= bucket[%d].Start=%v",
				i-1, buckets[i-1].Start, i, buckets[i].Start)
		}
	}
}

// TestAG5_HistogramEmpty verifies Histogram handles empty input gracefully (AC_1).
func TestAG5_HistogramEmpty(t *testing.T) {
	buckets := Histogram(nil, time.Hour)
	if len(buckets) != 0 {
		t.Errorf("expected 0 buckets for nil input, got %d", len(buckets))
	}
}

// TestAG5_HistogramSkipsZeroTimestamp verifies entries without timestamps are excluded (AC_1).
func TestAG5_HistogramSkipsZeroTimestamp(t *testing.T) {
	entries := []parser.LogEntry{
		{Level: "info", Message: "has ts", Timestamp: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC)},
		{Level: "info", Message: "no ts"},
	}
	buckets := Histogram(entries, time.Hour)

	if len(buckets) != 1 {
		t.Fatalf("expected 1 bucket, got %d", len(buckets))
	}
	if buckets[0].Count != 1 {
		t.Errorf("expected count 1, got %d", buckets[0].Count)
	}
}

// TestAG5_HistogramBucketEndTime verifies each bucket's End equals Start + duration (AC_1).
func TestAG5_HistogramBucketEndTime(t *testing.T) {
	entries := makeHistogramEntries()
	dur := time.Hour
	buckets := Histogram(entries, dur)

	for i, b := range buckets {
		expectedEnd := b.Start.Add(dur)
		if !b.End.Equal(expectedEnd) {
			t.Errorf("bucket[%d]: expected End=%v, got %v", i, expectedEnd, b.End)
		}
	}
}

// TestAG5_HistogramFormat verifies FormatHistogram produces one line per bucket (AC_1).
func TestAG5_HistogramFormat(t *testing.T) {
	buckets := []Bucket{
		{Start: time.Date(2025, 1, 1, 10, 0, 0, 0, time.UTC), End: time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC), Count: 3},
		{Start: time.Date(2025, 1, 1, 11, 0, 0, 0, time.UTC), End: time.Date(2025, 1, 1, 12, 0, 0, 0, time.UTC), Count: 1},
	}
	out := FormatHistogram(buckets)
	lines := splitNonEmpty(out)
	if len(lines) != 2 {
		t.Errorf("expected 2 lines, got %d: %q", len(lines), out)
	}
}

// splitNonEmpty splits a string by newlines and filters out empty lines.
func splitNonEmpty(s string) []string {
	var result []string
	for _, line := range splitLines(s) {
		if line != "" {
			result = append(result, line)
		}
	}
	return result
}

// splitLines splits a string into lines.
func splitLines(s string) []string {
	var lines []string
	start := 0
	for i := 0; i < len(s); i++ {
		if s[i] == '\n' {
			lines = append(lines, s[start:i])
			start = i + 1
		}
	}
	if start < len(s) {
		lines = append(lines, s[start:])
	}
	return lines
}
