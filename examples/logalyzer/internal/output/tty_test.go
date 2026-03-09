package output

import (
	"os"
	"testing"
)

// TestOU3_IsTerminalPipe verifies that IsTerminal returns false for a pipe
// (non-TTY file descriptor), ensuring colors are disabled when piped (AC_2, OU_3).
func TestOU3_IsTerminalPipe(t *testing.T) {
	r, w, err := os.Pipe()
	if err != nil {
		t.Fatalf("os.Pipe failed: %v", err)
	}
	defer r.Close()
	defer w.Close()

	if IsTerminal(w) {
		t.Error("IsTerminal should return false for a pipe")
	}
}

// TestOU3_IsTerminalNilFile verifies that IsTerminal returns false for a nil file
// (AC_2, OU_3).
func TestOU3_IsTerminalNilFile(t *testing.T) {
	if IsTerminal(nil) {
		t.Error("IsTerminal should return false for nil")
	}
}
