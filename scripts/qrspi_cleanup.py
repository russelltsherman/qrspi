#!/usr/bin/env python3
"""One-shot QRSPI cleanup: reap a fully-merged ticket's worktree + branches + remote refs.

Why this exists
---------------
Once a ticket's whole Graphite stack has landed (every slice PR MERGED), the
ticket leaves behind disposable local state: the `.worktrees/<id>` worktree, the
local `<id>/design|plan|slice-*` branches, and now-merged remote head refs. This
script reaps that state for ONE ticket, deterministically, behind a `--dry-run`
gate so a preview can be taken before anything is destroyed.

Design (mirrors qrspi_resolve.py / qrspi_pr_state.py conventions)
-----------------------------------------------------------------
- Self-locating: REPO_ROOT is derived from `__file__` (two levels up), never typed
  by the caller — the same path-mangling defence the rest of the harness uses.
- A PURE classifier `classify_cleanup(stack_merge_state, dirty_porcelain)` decides
  destroy / skip / blocked; it is unit-tested without any subprocess.
    * blocked  — the worktree has uncommitted changes (dirty porcelain). Never
                 destroy a dirty worktree (AC3).
    * destroy  — the stack is fully merged (every real branch's PR MERGED, AC2).
    * skip     — anything else (partial merge, in-flight, no branches).
- `--dry-run` gates ONLY the destructive execution. The decision is computed
  IDENTICALLY with or without it (Decision 4), so a dry run is a faithful preview.
- Idempotent: a missing worktree, a missing local branch, or an already-deleted
  remote ref is a clean no-op success, never an error (Q11, Q12).
- Emits exactly one CleanupEnvelope on stdout, exit 0/1, and reports any infra
  error ONCE as ok:false (never retried), matching the established contract (Q4).

Output: a single JSON envelope on stdout:
    { ok, repoRoot, decision, reason, removed{worktree,branches,remotes}, dryRun, error? }
"""

import argparse
import json
import os
import subprocess
import sys

# The script lives at <repo-root>/scripts/qrspi_cleanup.py, so the repo root is two
# levels up. Deriving it from __file__ (not cwd, not an argument) keeps the only
# path the model could corrupt out of the caller's hands — see qrspi_resolve.py.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

from qrspi_pr_state import (  # noqa: E402
    branch_set,
    is_stack_fully_merged,
    stack_merge_state,
    _query_pr,
)
from qrspi_resolve import parse_name_with_owner  # noqa: E402
from qrspi_restack import worktree_path  # noqa: E402


# --- pure classifier (unit-tested) -----------------------------------------

def classify_cleanup(stack_merge_state, dirty_porcelain):
    """Decide destroy / skip / blocked for one ticket's stack. Pure, so the whole
    decision matrix is unit-testable without touching git/gh.

    `stack_merge_state` is the StackMergeState map from
    qrspi_pr_state.stack_merge_state (branch -> {merged, prNumber, state}).
    `dirty_porcelain` is the raw `git status --porcelain` text for the worktree
    ("" when clean / when there is no worktree).

    - blocked: porcelain is non-empty — the worktree has uncommitted work; never
      destroy it (AC3). This takes precedence over merge state so dirty work is
      never silently discarded.
    - destroy: the stack is fully merged (every real branch's PR MERGED, AC2).
    - skip:    anything else (partial merge, all in-flight, or no branches).

    Returns a CleanupDecision: {decision: "destroy"|"skip"|"blocked", reason: str}.
    """
    if (dirty_porcelain or "").strip():
        return {
            "decision": "blocked",
            "reason": "worktree has uncommitted changes; refusing to destroy",
        }
    if is_stack_fully_merged(stack_merge_state):
        return {
            "decision": "destroy",
            "reason": "stack fully merged",
        }
    return {
        "decision": "skip",
        "reason": "stack not fully merged",
    }


# --- subprocess-backed mechanics (not unit-tested) -------------------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def _gh_owner_repo():
    """(owner, repo) for the current repo via gh. Raises on failure (reported once
    as an infra error by main)."""
    rc, out, err = _run(["gh", "repo", "view", "--json", "nameWithOwner",
                         "-q", ".nameWithOwner"], cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("gh repo view failed: %s" % (err.strip() or out.strip()))
    return parse_name_with_owner(out.strip())


def _stack_branches(ticket):
    """The set of this ticket's local stack branches (design/plan/slice-*), from
    `git branch --list <ticket>/*`. Normalized to bare names via branch_set."""
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()


def _dirty_porcelain(wt_path):
    """`git status --porcelain` for the ticket's worktree, or "" when the worktree
    does not exist (a missing worktree cannot be dirty — Q11). Read-only."""
    if not os.path.isdir(wt_path):
        return ""
    rc, out, _ = _run(["git", "status", "--porcelain"], cwd=wt_path)
    return out if rc == 0 else ""


def _gather_merge_state(owner, repo, branches):
    """Build the StackMergeState for `branches` by querying each branch's PR nodes.
    Assembles the {branch -> graphql_nodes} dict stack_merge_state consumes (the
    wiring PREVIOUS_NOTES flagged as not-yet-done for the gather)."""
    graphql_nodes = {b: _query_pr(owner, repo, b) for b in branches}
    return stack_merge_state(list(branches), graphql_nodes)


def _remove_worktree(wt_path, dry_run):
    """Remove the ticket worktree. Missing worktree -> clean no-op success (Q11).
    Returns True iff a worktree existed (and, when not dry-run, was removed)."""
    if not os.path.isdir(wt_path):
        return False
    if dry_run:
        return True
    rc, out, err = _run(["git", "worktree", "remove", "--force", wt_path],
                        cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("git worktree remove failed: %s"
                           % (err.strip() or out.strip()))
    return True


def _delete_local_branch(branch, dry_run):
    """Delete one local branch. Already-absent branch -> clean no-op (Q12).
    Returns True iff the branch existed (and, when not dry-run, was deleted)."""
    rc, _, _ = _run(["git", "rev-parse", "--verify", "--quiet", "refs/heads/%s" % branch],
                    cwd=REPO_ROOT)
    if rc != 0:
        return False  # already gone — clean no-op
    if dry_run:
        return True
    drc, out, err = _run(["git", "branch", "-D", branch], cwd=REPO_ROOT)
    if drc != 0:
        raise RuntimeError("git branch -D %s failed: %s"
                           % (branch, err.strip() or out.strip()))
    return True


def _prune_remote_refs(branches, dry_run):
    """Prune merged remote head refs for `branches`. A remote ref that is already
    gone is a clean no-op (Q12). Returns the list of branches whose remote ref was
    present (and, when not dry-run, deleted)."""
    rc, out, _ = _run(["git", "ls-remote", "--heads", "origin"], cwd=REPO_ROOT)
    present = set()
    if rc == 0:
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith("refs/heads/"):
                present.add(parts[1][len("refs/heads/"):])
    remotes = [b for b in branches if b in present]
    if dry_run or not remotes:
        return remotes
    # gt sync --force prunes local branches whose PRs have merged and their remote
    # refs in one pass (Decision 2/3). We invoke it once for the whole stack.
    src, out2, err2 = _run(["gt", "sync", "--force"], cwd=REPO_ROOT)
    if src != 0:
        raise RuntimeError("gt sync --force failed: %s"
                           % (err2.strip() or out2.strip()))
    return remotes


# --- envelope -------------------------------------------------------------

def _envelope(ok, decision, reason, removed, dry_run, error=None):
    env = {
        "ok": ok,
        "repoRoot": REPO_ROOT,
        "decision": decision,
        "reason": reason,
        "removed": removed,
        "dryRun": dry_run,
    }
    if error is not None:
        env["error"] = error
    return env


def run(ticket, dry_run):
    """Compute the decision and (unless dry_run) reap. Returns a CleanupEnvelope.
    Any infra error is caught here and surfaced ONCE as ok:false (never retried)."""
    removed = {"worktree": False, "branches": [], "remotes": []}
    try:
        wt_path = worktree_path(REPO_ROOT, ticket)
        branches = _stack_branches(ticket)
        dirty = _dirty_porcelain(wt_path)

        # Decision is computed identically with or without --dry-run (Decision 4).
        # Merge state is only needed when the worktree is clean (a dirty worktree
        # short-circuits to blocked before we spend gh queries).
        merge_state = {}
        if not (dirty or "").strip():
            owner, repo = _gh_owner_repo()
            merge_state = _gather_merge_state(owner, repo, branches)

        decision = classify_cleanup(merge_state, dirty)

        if decision["decision"] == "blocked":
            reason = decision["reason"]
            if dirty.strip():
                reason = "%s: %s" % (reason, dirty.strip())
            return _envelope(True, "blocked", reason, removed, dry_run,
                             error=dirty.strip() or None)

        if decision["decision"] == "destroy":
            removed["worktree"] = _remove_worktree(wt_path, dry_run)
            removed["branches"] = sorted(
                b for b in branches if _delete_local_branch(b, dry_run))
            removed["remotes"] = sorted(_prune_remote_refs(branches, dry_run))

        return _envelope(True, decision["decision"], decision["reason"],
                         removed, dry_run)
    except Exception as exc:  # noqa: BLE001 — report any infra error once as ok:false
        return _envelope(False, "skip", "infrastructure error", removed, dry_run,
                         error=str(exc))


def main():
    parser = argparse.ArgumentParser(
        description="Reap a fully-merged QRSPI ticket's worktree, branches, and remote refs")
    parser.add_argument("--ticket", required=True, help="Linear ticket id, e.g. RUS-52")
    parser.add_argument("--dry-run", action="store_true",
                        help="Compute the decision and preview the reap WITHOUT destroying anything")
    args = parser.parse_args()

    env = run(args.ticket, args.dry_run)
    json.dump(env, sys.stdout, indent=2)
    print()
    sys.exit(0 if env["ok"] else 1)


if __name__ == "__main__":
    main()
