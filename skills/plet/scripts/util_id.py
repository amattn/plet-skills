"""Shared plet ID generation utilities.

Internal module — imported by plet_*.py scripts, never called directly.
Not listed in allowed-tools. Not executable.

Provides Crockford Base32 encoding, timestamp generation, and the
plet ID scheme used across all runtime artifact entries and trace
events. Every script that generates plet IDs imports from here rather
than reimplementing, eliminating drift.

Plet ID format:
    {prefix}_{crockford_timestamp}_{iteration_segment}_{phase_segment}

    prefix:    type-specific (epr, eln, eem, tev, vrp)
    timestamp: 10-char Crockford Base32 (milliseconds since epoch)
    iteration: ITR_001 -> itr001, proj -> proj
    phase:     implement -> i, verify -> v, refine -> r, plan -> p + attempt

Example: epr_01JD8X3K7M_itr001_i1

Functions:
    crockford_encode(n)
        Encode a non-negative integer as a Crockford Base32 string.
        Crockford alphabet excludes I, L, O, U to avoid ambiguity.

    crockford_timestamp()
        Generate a 10-char Crockford Base32 timestamp from current
        time in milliseconds. Zero-padded to 10 characters.

    normalize_iteration(iteration_id)
        Normalize iteration ID for plet ID context segment:
        ITR_001 -> itr001, proj -> proj. Lowercased, underscores removed.

    phase_attempt_segment(phase, attempt)
        Encode phase and attempt number: implement-1 -> i1, verify-2 -> v2,
        refine-1 -> r1, plan-1 -> p1.

    generate_plet_id(prefix, iteration_id, phase, attempt)
        Generate a complete plet ID with the given type prefix.
        Combines: prefix + crockford_timestamp + iteration + phase.

Dependencies: Python stdlib only (time).
"""

import time

# Crockford Base32 alphabet (excludes I, L, O, U)
CROCKFORD_ALPHABET = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"

# Phase prefix mapping
PHASE_PREFIXES = {
    "implement": "i",
    "verify": "v",
    "refine": "r",
    "plan": "p",
}


def crockford_encode(n):
    """Encode a non-negative integer as a Crockford Base32 string."""
    if n == 0:
        return "0"
    result = []
    while n > 0:
        result.append(CROCKFORD_ALPHABET[n % 32])
        n //= 32
    return "".join(reversed(result))


def crockford_timestamp():
    """Generate a 10-char Crockford Base32 timestamp from current time in ms."""
    ms = int(time.time() * 1000)
    encoded = crockford_encode(ms)
    return encoded.zfill(10)


def normalize_iteration(iteration_id):
    """Normalize iteration ID for plet ID: ITR_001 -> itr001, proj -> proj."""
    if iteration_id.lower() == "proj":
        return "proj"
    return iteration_id.lower().replace("_", "")


def phase_attempt_segment(phase, attempt):
    """Encode phase and attempt: implement-1 -> i1, verify-2 -> v2, plan-1 -> p1."""
    prefix = PHASE_PREFIXES.get(phase, phase[0])
    return f"{prefix}{attempt}"


def generate_plet_id(prefix, iteration_id, phase, attempt):
    """Generate a complete plet ID.

    Args:
        prefix: type prefix (epr, eln, eem, tev, vrp)
        iteration_id: iteration ID (e.g., ITR_001) or "proj"
        phase: implement, verify, refine, or plan
        attempt: attempt number (integer)

    Returns: plet ID string (e.g., epr_01JD8X3K7M_itr001_i1)
    """
    ts = crockford_timestamp()
    iter_seg = normalize_iteration(iteration_id)
    phase_seg = phase_attempt_segment(phase, attempt)
    return f"{prefix}_{ts}_{iter_seg}_{phase_seg}"
