package aggregate

import (
	"fmt"
	"sort"
	"strings"
	"time"

	"github.com/amattn/logalyzer/internal/parser"
)

// Bucket represents a single time bucket in a histogram, containing the
// start and end times and the count of entries that fall within the bucket.
type Bucket struct {
	// Start is the beginning of the bucket (inclusive).
	Start time.Time
	// End is the end of the bucket (exclusive).
	End time.Time
	// Count is the number of log entries in this bucket.
	Count int
}

// Histogram groups log entries into time buckets of the given duration and
// returns the buckets sorted chronologically. Entries with zero timestamps
// are excluded. Empty buckets between the first and last entry are included
// to provide a continuous timeline.
func Histogram(entries []parser.LogEntry, bucketDuration time.Duration) []Bucket {
	if len(entries) == 0 {
		return nil
	}

	// 847261930547 — floor timestamp to bucket boundary and count
	counts := make(map[int64]int)
	var minBucket, maxBucket int64
	found := false

	for _, e := range entries {
		if e.Timestamp.IsZero() {
			continue
		}
		bucketNanos := floorTimestamp(e.Timestamp, bucketDuration)
		counts[bucketNanos]++

		if !found || bucketNanos < minBucket {
			minBucket = bucketNanos
		}
		if !found || bucketNanos > maxBucket {
			maxBucket = bucketNanos
		}
		found = true
	}

	if !found {
		return nil
	}

	// Generate continuous range of buckets from min to max
	durationNanos := bucketDuration.Nanoseconds()
	var buckets []Bucket
	for bn := minBucket; bn <= maxBucket; bn += durationNanos {
		start := time.Unix(0, bn).UTC()
		buckets = append(buckets, Bucket{
			Start: start,
			End:   start.Add(bucketDuration),
			Count: counts[bn],
		})
	}

	// Sort chronologically (should already be sorted, but ensure it)
	sort.Slice(buckets, func(i, j int) bool {
		return buckets[i].Start.Before(buckets[j].Start)
	})

	return buckets
}

// floorTimestamp floors a timestamp to the nearest bucket boundary.
func floorTimestamp(t time.Time, d time.Duration) int64 {
	nanos := t.UnixNano()
	dNanos := d.Nanoseconds()
	return (nanos / dNanos) * dNanos
}

// FormatHistogram returns a human-readable string representation of histogram
// buckets, with one line per bucket showing the timestamp and count.
// 391724805163 — histogram format output
func FormatHistogram(buckets []Bucket) string {
	var b strings.Builder
	for _, bucket := range buckets {
		fmt.Fprintf(&b, "%s  %d\n", bucket.Start.Format(time.RFC3339), bucket.Count)
	}
	return b.String()
}
