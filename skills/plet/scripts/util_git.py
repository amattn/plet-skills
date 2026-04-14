"""Pure functions for git naming conventions.

Branch names, tag names, and other git-related string derivation.
No git operations — no subprocess calls, no imports beyond stdlib.

Extracted from plet_git_iteration.py so multiple scripts can share
the same naming logic without duplicating it.
"""


def active_session_branch(state):
    """Get the branch name from the current active session in sessionHistory.

    Returns the branch string, or None if no active session.
    More robust than deriving from loopSessionCount — uses the actual
    branch name that was created, not a re-derivation that can mismatch
    after failed/recovered sessions.
    """
    history = state.get("sessionHistory", [])
    for entry in reversed(history):
        if entry.get("endedAt") is None:
            return entry.get("branch")
    # No active session — fall back to last session if any
    if history:
        return history[-1].get("branch")
    return None


def active_loop_number(state):
    """Get the loop number from the current active session.

    Returns the integer loop number, or loopSessionCount as fallback.
    Parses from the branch name (e.g., "plet/PROJ/loop3/workstream" → 3).
    """
    branch = active_session_branch(state)
    if branch:
        # Parse loop number from branch: plet/{proj}/loop{N}/...
        parts = branch.split("/")
        for p in parts:
            if p.startswith("loop"):
                try:
                    return int(p[4:])
                except (ValueError, IndexError):
                    pass
    return state.get("loopSessionCount", 0)


def derive_branch_name(state, branch_type, iter_id=None):
    """Derive the branch name from state and type.

    Args:
        state: dict with projectId, loopSessionCount, refineSessionCount
        branch_type: one of "iteration", "workstream", "plan", "refine"
        iter_id: required when branch_type is "iteration"

    Returns the branch name string.
    """
    project_id = state["projectId"]

    if branch_type == "iteration":
        n = state["loopSessionCount"]
        return f"plet/{project_id}/loop{n}/{iter_id}"
    elif branch_type == "workstream":
        n = state["loopSessionCount"]
        return f"plet/{project_id}/loop{n}/workstream"
    elif branch_type == "plan":
        n = state.get("planSessionCount", 1)
        return f"plet/{project_id}/plan{n}/workstream"
    elif branch_type == "refine":
        n = state["refineSessionCount"]
        return f"plet/{project_id}/refine{n}/workstream"
