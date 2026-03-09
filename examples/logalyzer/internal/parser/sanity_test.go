package parser

import "testing"

// TestSanity is a basic sanity check that the test infrastructure works.
// Changing the assertion to false should cause the test to fail (AC_3).
func TestSanity(t *testing.T) {
	want := true
	got := true
	if got != want {
		t.Errorf("sanity check failed: got %v, want %v", got, want)
	}
}
