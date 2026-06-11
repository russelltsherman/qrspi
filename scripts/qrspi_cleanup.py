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
    `git branch --list <ticket>/*`. Normalized to bare names via branch_set.

    UNCHANGED contract: still enumerates only locally-tracked `<ticket>/*` branch
    names from the main checkout. It is now one of TWO discovery inputs — the other
    is `_remote_refs`, the origin-driven authority — unioned at the discovery site in
    `run` so worktree-only stranded refs (no local branch) are still found (RUS-68 AC3,
    design Decision 2 Option A)."""
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()


def _remote_refs(ticket):
    """Origin-driven discovery authority: the set of `<ticket>/*` branch names that
    currently exist on origin, from a read-only `git ls-remote --heads origin` snapshot
    (RUS-68 design Decision 2 Option A, RQ1).

    This is the single source of truth for what `<ticket>/*` refs are really on origin —
    independent of whether a matching local branch exists — so a ticket whose branches
    lived only in a now-removed worktree still has its stranded refs discovered (AC3).
    Read-only: never mutates origin. Returns bare branch names (the `refs/heads/` prefix
    stripped), filtered to the `<ticket>/` namespace."""
    rc, out, _ = _run(["git", "ls-remote", "--heads", "origin"], cwd=REPO_ROOT)
    refs = set()
    if rc == 0:
        prefix = "refs/heads/"
        ns = "%s/" % ticket
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 2 and parts[1].startswith(prefix):
                name = parts[1][len(prefix):]
                if name == ticket or name.startswith(ns):
                    refs.add(name)
    return refs


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


class RemotePruneResult:
    """Outcome of a remote-ref prune attempt, separating CONFIRMED-deleted refs from
    attempted-but-still-present ones (RUS-68 §Types).

    This replaces the old presence-list return, whose central bug was reporting a ref as
    "removed" purely because it was present BEFORE the prune — never confirming it was
    actually gone afterward. Here `removed` holds only refs a post-prune `git ls-remote`
    proves absent (AC1/AC2); `failedRemotes` holds survivors (a retriable partial failure,
    not an infra error — RQ2). Both lists are sorted bare branch names."""

    __slots__ = ("removed", "failedRemotes")

    def __init__(self, removed=None, failedRemotes=None):
        self.removed = sorted(removed or [])
        self.failedRemotes = sorted(failedRemotes or [])

    def __eq__(self, other):  # pragma: no cover - convenience for tests
        return (isinstance(other, RemotePruneResult)
                and self.removed == other.removed
                and self.failedRemotes == other.failedRemotes)

    def __repr__(self):  # pragma: no cover - convenience for tests
        return "RemotePruneResult(removed=%r, failedRemotes=%r)" % (
            self.removed, self.failedRemotes)


def _gt_prune_remotes(branches):
    """Perform the `gt`-mediated remote prune for `branches` (RUS-68 RQ3 / Decision 1
    Option D — remote mutation STAYS WITHIN `gt`; the harness never issues
    `git push origin --delete`).

    `gt sync --force` pulls trunk and deletes branches whose PRs have merged, pruning
    their remote refs in one pass. Crucially this is invoked by `_prune_remote_refs`
    BEFORE local-branch deletion (the `run` ordering fix), so the local tracking refs
    `gt` keys off still exist and the mutation actually happens — fixing the original
    no-op trap where `gt sync` ran after the branches it needed were already gone.

    This is the single remote-MUTATING seam: it is the only function in the prune path
    that changes origin, so the fixture test substitutes it to drive a deterministic
    offline outcome while still exercising the real discovery + post-prune confirmation
    + partition logic against a real bare origin. Raises on a genuine `gt` infra failure
    (surfaced once as ok:false by `run`)."""
    rc, out, err = _run(["gt", "sync", "--force"], cwd=REPO_ROOT)
    if rc != 0:
        raise RuntimeError("gt sync --force failed: %s"
                           % (err.strip() or out.strip()))


def _prune_remote_refs(ticket, branches, dry_run):
    """Prune merged `<ticket>/*` remote head refs and report the CONFIRMED outcome.

    Contract (RUS-68 §Contracts, design Decision 1 Option D, AC1/AC2):
      1. Discover the candidate set = `branches` (caller-supplied union of local and
         origin-driven names) intersected with what actually exists on origin now.
      2. Run the `gt`-mediated remote prune (`_gt_prune_remotes`) WHILE the local
         tracking refs still exist (the caller — `run` — guarantees this ordering).
      3. Re-query origin read-only and partition candidates: a ref CONFIRMED absent
         from the post-prune `git ls-remote` lands in `removed`; a ref still present
         lands in `failedRemotes` (a retriable survivor, NOT an infra error — RQ2).

    Idempotency (Q9/Q12): a candidate already absent before the prune is a clean no-op
    success — it is confirmed-absent afterward too, so it lands in `removed`, never
    `failedRemotes`.

    Dry-run (AC4 / Decision 4): reports the candidate refs as `removed` (would-delete)
    and mutates NOTHING — no `gt` call, origin untouched.

    Returns a RemotePruneResult. `branches` is the discovery union; only names that are
    `<ticket>/*` AND present on origin are ever candidates."""
    ns = "%s/" % ticket
    candidates = sorted(
        b for b in branches if (b == ticket or b.startswith(ns)))

    present_before = _remote_refs(ticket)
    candidates = [b for b in candidates if b in present_before]

    if not candidates:
        return RemotePruneResult(removed=[], failedRemotes=[])

    if dry_run:
        # Preview only: report would-delete candidates, mutate nothing (no gt call).
        return RemotePruneResult(removed=candidates, failedRemotes=[])

    # Mutate origin via gt (the only remote-mutating step), then CONFIRM by re-reading.
    _gt_prune_remotes(candidates)

    present_after = _remote_refs(ticket)
    removed = [b for b in candidates if b not in present_after]
    failed = [b for b in candidates if b in present_after]
    return RemotePruneResult(removed=removed, failedRemotes=failed)


# --- envelope -------------------------------------------------------------

def _envelope(ok, decision, reason, removed, dry_run, failed_remotes=None, error=None):
    env = {
        "ok": ok,
        "repoRoot": REPO_ROOT,
        "decision": decision,
        "reason": reason,
        "removed": removed,
        # Additive (RUS-68): refs the run attempted to delete but that are still present
        # on origin. Empty = full success. Non-empty = retriable partial failure (ok stays
        # true — RQ2). `removed.remotes` is NEVER renamed/removed (back-compat).
        "failedRemotes": sorted(failed_remotes or []),
        "dryRun": dry_run,
    }
    if error is not None:
        env["error"] = error
    return env


def run(ticket, dry_run):
    """Compute the decision and (unless dry_run) reap. Returns a CleanupEnvelope.
    Any infra error is caught here and surfaced ONCE as ok:false (never retried).

    Ordering & discovery (RUS-68):
      - The `gt`-driven remote prune runs BEFORE local-branch deletion so the tracking
        refs `gt` keys off still exist (design Decision 1 Option D, RQ3).
      - Discovery is the UNION of `_stack_branches` (local) and `_remote_refs` (origin),
        so worktree-only stranded refs are found (AC3, Decision 2 Option A).
      - When `classify_cleanup` returns `skip` *purely because the local branch set is
        empty* AND origin still carries merged `<ticket>/*` refs, an ADDITIVE stranded-ref
        reaping path prunes those refs — gated on the same fully-merged confirmation the
        documented logic requires. `classify_cleanup` itself is UNCHANGED (RQ1)."""
    removed = {"worktree": False, "branches": [], "remotes": []}
    prune = RemotePruneResult()
    try:
        wt_path = worktree_path(REPO_ROOT, ticket)
        local_branches = _stack_branches(ticket)
        remote_branches = _remote_refs(ticket)
        # Union of the two discovery inputs: local tracking branches + origin-driven refs.
        branches = local_branches | remote_branches
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
            # Remote prune FIRST (while local tracking refs still exist for gt), THEN
            # local-branch deletion (RUS-68 ordering fix).
            prune = _prune_remote_refs(ticket, branches, dry_run)
            removed["remotes"] = list(prune.removed)
            removed["worktree"] = _remove_worktree(wt_path, dry_run)
            removed["branches"] = sorted(
                b for b in local_branches if _delete_local_branch(b, dry_run))
            return _envelope(True, "destroy", decision["reason"], removed, dry_run,
                             failed_remotes=prune.failedRemotes)

        # --- Additive stranded-ref reaping path (RUS-68 RQ1, AC3) ---------------
        # `classify_cleanup` returned `skip`. The ONLY case the additive path covers is
        # a worktree-only ticket: the local branch set is empty so the classifier
        # structurally cannot see the merged refs that still exist on origin. We do NOT
        # retrigger / reorder / re-threshold `classify_cleanup`; we run an INDEPENDENT
        # prune, gated on the same fully-merged confirmation the documented logic uses
        # (a ref is only deleted once its PR is confirmed merged).
        if (decision["decision"] == "skip"
                and not local_branches and remote_branches):
            owner, repo = _gh_owner_repo()
            stranded_state = _gather_merge_state(owner, repo, remote_branches)
            if is_stack_fully_merged(stranded_state):
                prune = _prune_remote_refs(ticket, remote_branches, dry_run)
                removed["remotes"] = list(prune.removed)
                return _envelope(
                    True, "destroy",
                    "stranded origin refs reaped (worktree-only, fully merged)",
                    removed, dry_run, failed_remotes=prune.failedRemotes)

        return _envelope(True, decision["decision"], decision["reason"],
                         removed, dry_run, failed_remotes=prune.failedRemotes)
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
