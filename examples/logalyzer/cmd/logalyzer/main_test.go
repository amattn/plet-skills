package main

import (
	"os/exec"
	"strings"
	"testing"
)

// TestVersionFlag verifies that --version and -v print the version string (AC_4).
func TestVersionFlag(t *testing.T) {
	// Build the binary first
	buildCmd := exec.Command("go", "build", "-o", "logalyzer_test_bin", ".")
	buildCmd.Dir = "."
	if out, err := buildCmd.CombinedOutput(); err != nil {
		t.Fatalf("failed to build binary: %v\n%s", err, out)
	}
	defer func() {
		_ = exec.Command("rm", "-f", "logalyzer_test_bin").Run()
	}()

	tests := []struct {
		name string
		flag string
	}{
		{"long flag", "--version"},
		{"short flag", "-v"},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			cmd := exec.Command("./logalyzer_test_bin", tt.flag)
			out, err := cmd.CombinedOutput()
			if err != nil {
				t.Fatalf("command failed with %v: %s", err, out)
			}

			output := strings.TrimSpace(string(out))
			if !strings.HasPrefix(output, "logalyzer v") {
				t.Errorf("expected version output starting with 'logalyzer v', got: %q", output)
			}
		})
	}
}
