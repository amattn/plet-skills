"""util_subprocess — shared subprocess execution utilities.

Wraps subprocess.run with consistent defaults: capture_output, text mode,
no shell=True. Provides run_git convenience for the common case.

Internal module — imported by plet_*.py scripts, never called directly.
"""

import subprocess


def run(args, cwd=None, timeout=None):
    """Run a subprocess with safe defaults.

    Args:
        args: command and arguments as a list
        cwd: working directory (optional)
        timeout: timeout in seconds (optional, raises TimeoutExpired)

    Returns:
        subprocess.CompletedProcess with stdout/stderr as strings.
        On non-zero exit, returns normally — caller decides how to handle.
    """
    return subprocess.run(
        args,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )


def run_git(*args, cwd=None, timeout=None):
    """Run a git command. Prepends 'git' to args, strips stdout/stderr.

    Args:
        *args: git subcommand and arguments (e.g., "status", "--porcelain")
        cwd: working directory (optional)
        timeout: timeout in seconds (optional)

    Returns:
        subprocess.CompletedProcess with stdout/stderr stripped.
    """
    result = run(["git"] + list(args), cwd=cwd, timeout=timeout)
    result.stdout = result.stdout.strip()
    result.stderr = result.stderr.strip()
    return result
