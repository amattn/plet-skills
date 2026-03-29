"""Pure functions for git naming conventions.

Branch names, tag names, and other git-related string derivation.
No git operations — no subprocess calls, no imports beyond stdlib.

Extracted from plet_git_iteration.py so multiple scripts can share
the same naming logic without duplicating it.
"""


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
        return "plet/{}/loop{}/{}".format(project_id, n, iter_id)
    elif branch_type == "workstream":
        n = state["loopSessionCount"]
        return "plet/{}/loop{}/workstream".format(project_id, n)
    elif branch_type == "plan":
        return "plet/{}/plan1/workstream".format(project_id)
    elif branch_type == "refine":
        n = state["refineSessionCount"]
        return "plet/{}/refine{}/workstream".format(project_id, n)
