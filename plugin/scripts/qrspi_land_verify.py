#!/usr/bin/env python3
"""Deterministic land verifier: did the WHOLE stack actually land?

Given a ticket id, gather each slice branch's MERGED state and return a verdict:

    LandVerdict { status: "landed" | "incomplete", openBranches: list[str] }

`landed` requires every real slice branch to be MERGED (reusing the tested
`is_stack_fully_merged` predicate from qrspi_pr_state). `incomplete` names every
non-MERGED slice branch, so a half-landed stack — the exact RUS-70 failure where
the tip slice was left OPEN — is surfaced by name instead of silently reported as
Done.

The verdict function (`verify_landed`) is pure and unit-tested against the
existing N=2 stack fixtures. The CLI (`main`) does the subprocess-backed gather
(git branches + gh GraphQL) and is self-locating like its siblings
(qrspi_resolve.py / qrspi_persist.py) — it derives the repo root from its own
__file__, so the only thing a caller types is `qrspi_land_verify.py <ticket>`.

Exit code: 0 on `landed`, non-zero on `incomplete`, so the orchestrator can gate
the Done projection on the process status as well as the JSON.
"""

import json
import os
import subprocess
import sys

# Self-locating, like qrspi_resolve.py: <repo>/scripts/qrspi_land_verify.py, so the
# repo root is one level up from this file's dir. Deriving it from __file__ (not cwd,
# not an argument) is what keeps the path-sensitive gather token-free for the caller.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

from qrspi_pr_state import (  # noqa: E402
    PR_QUERY,
    branch_set,
    slice_numbers,
    stack_merge_state,
    is_stack_fully_merged,
)


# --- pure verdict (unit-tested) --------------------------------------------

def verify_landed(stack_state):
    """Reduce a StackMergeState to a LandVerdict.

    `stack_state` is the dict stack_merge_state() returns:
        { branch: { merged: bool, prNumber: int|None, state: str|None,
                    mergedByPr: int|None } }

    Returns the LandVerdict dict:
        { "status": "landed" | "incomplete", "openBranches": list[str] }

    `landed` (empty openBranches) iff is_stack_fully_merged(stack_state) — every
    real branch MERGED (all-or-nothing). Otherwise `incomplete`, naming every
    non-MERGED branch in stack_state's iteration order. Reuses is_stack_fully_merged
    rather than duplicating the all-merged predicate (ref: structure.md Contracts;
    design.md §Decision 2)."""
    if is_stack_fully_merged(stack_state):
        return {"status": "landed", "openBranches": []}
    open_branches = [
        branch for branch, entry in (stack_state or {}).items()
        if not entry.get("merged")
    ]
    return {"status": "incomplete", "openBranches": open_branches}


# --- subprocess-backed gather (not unit-tested) ----------------------------

def _run(cmd, cwd=None):
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def _gh_name_with_owner():
    rc, out, err = _run(["gh", "repo", "view", "--json", "nameWithOwner",
                         "-q", ".nameWithOwner"], cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("gh repo view failed: %s" % (err.strip() or out.strip()))
    return out.strip()


def _slice_branches(ticket):
    """The ticket's real slice branch head-refs in ascending slice order, derived
    from `git branch --list <ticket>/*`. Reuses slice_numbers() so the ordering and
    parsing match the resolver's view of the stack."""
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    if rc != 0:
        return []
    lines = out.splitlines()
    return ["%s/slice-%d" % (ticket, n) for n in slice_numbers(lines)]


def _query_pr(owner, repo, head):
    rc, out, err = _run(
        ["gh", "api", "graphql",
         "-f", "query=%s" % PR_QUERY,
         "-F", "owner=%s" % owner, "-F", "repo=%s" % repo, "-F", "head=%s" % head],
        cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("gh graphql failed for %s: %s" % (head, err.strip()))
    data = json.loads(out)
    return data["data"]["repository"]["pullRequests"]["nodes"]


def main(ticket_id):
    """Gather per-branch merge state for `ticket_id` and emit the LandVerdict JSON.

    Returns the process exit code: 0 on `landed`, 1 on `incomplete` (ref:
    structure.md Contracts; design.md §Delta)."""
    owner_repo = _gh_name_with_owner()
    owner, repo = owner_repo.split("/", 1)
    branches = _slice_branches(ticket_id)
    graphql_nodes = {b: _query_pr(owner, repo, b) for b in branches}
    stack_state = stack_merge_state(branches, graphql_nodes)
    verdict = verify_landed(stack_state)
    print(json.dumps(verdict))
    return 0 if verdict["status"] == "landed" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
