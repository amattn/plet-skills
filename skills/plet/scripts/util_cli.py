"""Shared CLI utilities for plet scripts.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Provides argument parsing, validation, timestamp generation, and the
standard main() dispatch pattern. Every plet script imports from here
rather than reimplementing these patterns, eliminating drift across
the 10-script inventory.

Functions:
    parse_kwargs(args)
        Parse --key value pairs from an args list. Bare --flag without
        a value is treated as boolean True. Returns a dict. Keys have
        leading -- stripped and hyphens converted to underscores
        (e.g., --iteration-id becomes iteration_id).

    require_kwargs(kwargs, required, command_help="")
        Check that all required keys exist in a kwargs dict. On first
        missing key, prints "Error: --{key} is required" to stderr.
        If command_help is provided, prints it to stderr after the error.
        Returns True if all present, False if any missing.

    validate_enum(value, valid_values, field_name)
        Check that value is in valid_values. On failure, prints
        "Error: invalid {field_name} '{value}' (valid: ...)" to stderr.
        Returns True if valid, False if not.

    validate_int(value, field_name)
        Parse a string as an integer. On failure, prints
        "Error: {field_name} must be an integer, got '{value}'" to stderr.
        Returns (parsed_int, True) on success, (None, False) on failure.

    now_iso()
        Returns the current UTC time as an ISO 8601 string with second
        resolution: "YYYY-MM-DDTHH:MM:SSZ". Uses datetime.datetime.utcnow().

    dispatch(commands, script_name, script_version, skill_version, doc, argv=None)
        Standard main() entry point. Parses argv (defaults to sys.argv)
        to extract the command name, then:
        - --help / -h: prints doc (the module docstring) to stdout, returns 0
        - --version: prints "{script_name} {script_version} (built against
          plet skill {skill_version})" to stdout, returns 0
        - unknown command: prints error + valid commands to stderr, returns 1
        - valid command: calls commands[cmd](remaining_args), returns its
          exit code

        The commands dict maps command names (str) to callables that accept
        a list of string args and return an int exit code.

    filter_fields(data, fields)
        Filter a dict to only requested fields. If fields is None, returns
        data unchanged. When filtering, adds two metadata keys:
        - "fieldsIncluded": list of fields that were requested and present
        - "fieldsOmitted": list of fields that were available but filtered out
        Used with --fields flag (UNV_CMD_19) to limit JSON output size for
        agent context window protection.

Dependencies: Python stdlib only (sys, datetime).
"""
