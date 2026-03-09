package output

import "os"

// IsTerminal reports whether f is connected to a terminal (TTY).
// Returns false if f is nil, if Stat fails, or if the file is not a
// character device (e.g., a pipe or regular file).
// 629481073512 — TTY detection for automatic color toggle (OU_3)
func IsTerminal(f *os.File) bool {
	if f == nil {
		return false
	}
	fi, err := f.Stat()
	if err != nil {
		return false
	}
	return fi.Mode()&os.ModeCharDevice != 0
}
