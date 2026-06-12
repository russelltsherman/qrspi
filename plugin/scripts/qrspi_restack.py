#!/usr/bin/env python3
"""Deterministically restack a QRSPI ticket's stack onto the current trunk.

Why this exists
---------------
Each QRSPI ticket is a Graphite stack rooted at trunk: `main <- design <- plan
<- slice-1..N`. Whenever trunk advances (a sibling stack lands, or `main` is
updated), every branch in the stack drifts out of alignment and Graphite marks it
`(needs restack)`. A branch parented on a stale trunk tip can fail `gt submit`,
which is what compounded the trunk-divergence failures in the first full qrspi-batch
run. The batch must therefore ensure a ticket's stack is current BEFORE it builds or
submits new work — and it must do so deterministically, not via a weak worker model
hand-running `gt` (the failure class `qrspi_resolve.py`/`qrspi_persist.py` already
neutralised by folding path-sensitive multi-step shell into one self-locating
command).

This script self-locates the repo root from its own `__file__`, finds the ticket's
worktree + stack tip, and runs `gt restack --downstack` from the tip so the whole
chain (tip -> ... -> design) rebases onto the current trunk. It restacks onto the
LOCAL trunk only — it NEVER `gt sync`s (the SKILL forbids syncing a held stack
mid-feature) and never rewrites trunk. `gt restack` is idempotent: an already-aligned
stack is a no-op. A restack conflict is treated as a HARD STOP — the script runs
`gt abort` to restore a clean tree and reports `ok:false` with the verbatim conflict,
so the caller skips+surfaces the ticket and the batch keeps moving.

Pushing the realigned stack
---------------------------
A `gt restack` rewrites branch commits LOCALLY only — the open phase PRs still point at
the pre-restack commits. Leaving it there gives us restacked branches with no update on
the remote, so the later `gt submit`/`gt merge` still sees the stale parent the restack
was meant to fix. So when (and only when) the restack actually moved a branch, this
script follows it with `gt submit --publish --stack --force --no-edit --no-interactive`
from the tip, force-pushing the rewritten history to every existing phase PR in the
stack (the rebase makes the remote diverge, so the push must force). The submit is the
codebase idiom for "ensure the stack's remotes are current" (same call the land step
runs first). A submit failure is surfaced as `ok:false` — a stack realigned locally but
not pushed is exactly the divergence this gate exists to prevent — and needs no abort
(the restack already left a clean tree).

Output: a single JSON envelope on stdout:
    { ok, repoRoot, ticket, worktreeDir, tip, restacked, submitted, error? }
"""

import argparse
import json
import os
import re
import subprocess
import sys

# ENGINE_ROOT: the dir holding this engine's scripts/ (from __file__) — used ONLY for
# sibling imports. REPO_ROOT: the HOST checkout root all host paths key off, resolved via
# the shared qrspi_paths.resolve_repo_root() (git-common-dir first — the MAIN checkout even
# from a worktree; __file__ parent last resort). validate=False keeps gh off the import
# path. Decoupling the two is the RUS-60 core change (ref: design.md Decision 2).
ENGINE_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ENGINE_ROOT)

import qrspi_paths  # noqa: E402
from qrspi_pr_state import (             # noqa: E402
    branch_set,
    stack_merge_state,
    is_stack_fully_merged,
    PR_QUERY,
)
from qrspi_resolve import (               # noqa: E402
    pick_tip,
    parse_name_with_owner,
    _gh_name_with_owner,
)

REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)

# gt prints exactly one line per branch on a no-op restack:
#   "<branch> does not need to be restacked on <trunk>."
# Used ONLY to report whether any branch actually moved (restacked True/False) — never
# to decide ok/not-ok. A stack where every line carries this phrase did nothing.
_NOOP_PHRASE = "does not need to be restacked"


# --- pure helpers (unit-tested) --------------------------------------------

def worktree_path(repo_root, ticket):
    """Canonical worktree path for a ticket. Pure; the path is computed here, never
    typed by the model."""
    return os.path.join(repo_root, ".worktrees", ticket)


def _branch_rank(branch, ticket):
    """Stack-order rank for a ticket branch: design < plan < slice-1 < slice-2 < ...

    Returns an int sort key (lower = closer to trunk). A branch that does not match
    the ticket's `<ticket>/{design,plan,slice-N}` shape sorts last (a large sentinel)
    so foreign branches never get treated as an ancestor. Pure, so the stack ordering
    is unit-testable without git/gt."""
    prefix = "%s/" % ticket
    if not branch.startswith(prefix):
        return 10 ** 9
    rest = branch[len(prefix):]
    if rest == "design":
        return 0
    if rest == "plan":
        return 1
    m = re.match(r"^slice-(\d+)$", rest)
    if m:
        # +2 keeps slice-1 above plan; the slice number preserves slice ordering.
        return 2 + int(m.group(1))
    return 10 ** 9


def merged_ancestors(branches, merged_flags):
    """The subset of `branches` that are merged ancestors: merged AND below the lowest
    still-open slice in stack order (design < plan < slice-1 < ...).

    `branches` is the ticket's branch set (from branch_set()); `merged_flags` maps a
    branch name -> bool (its PR is merged). A branch absent from the map is treated as
    not-merged. The lowest open branch is the bottom-most (lowest-rank) branch whose
    PR is NOT merged; every merged branch ranked strictly below it is a merged ancestor.
    When every branch is merged there is no open branch, so no branch is "below" an open
    one and the merged-ancestor set is empty (the fully-landed case is the short-circuit's
    job, not this helper's). Pure, tuple-in/tuple-out. Needs the ticket to rank branches,
    inferred from the shared `<ticket>/` prefix of `branches`."""
    if not branches:
        return set()
    ticket = _infer_ticket(branches)
    open_branches = [b for b in branches if not merged_flags.get(b, False)]
    if not open_branches:
        return set()
    lowest_open = min(open_branches, key=lambda b: _branch_rank(b, ticket))
    lo_rank = _branch_rank(lowest_open, ticket)
    return {b for b in branches
            if merged_flags.get(b, False) and _branch_rank(b, ticket) < lo_rank}


def submit_scope(branches, merged_flags, ticket):
    """Pure computation of the merged-ancestor-aware submit scope.

    Returns a dict:
        { "scope": [open branch names, stack order],
          "lowestOpen": <lowest open branch name> | None,
          "reparentParent": <merged-ancestor branch that is lowestOpen's tracked
                             parent> | None }

    - `scope` is the open (not-merged) branches, sorted in stack order, that the
      `--stack` submit should cover. Empty when the stack is fully merged.
    - `lowestOpen` is the bottom-most open branch (the one whose tracked parent may be
      a merged ancestor that must be dropped). None when fully merged.
    - `reparentParent` is set to the merged-ancestor branch immediately below
      `lowestOpen` in stack order when that parent is merged (so the lowest open slice
      must be re-parented onto trunk); None when the lowest open branch's tracked parent
      is NOT a merged ancestor (fully-open stack, or its parent is still open).

    The tracked parent is inferred from `<ticket>/slice-N` ordering + merged flags
    (ref: structure.md Unverified Assumption "Tracked parent" read): the parent of the
    lowest open branch is the highest-ranked branch strictly below it; if that parent is
    merged, it is a merged ancestor to drop. Pure, tuple-in/tuple-out."""
    ancestors = merged_ancestors(branches, merged_flags)
    open_branches = [b for b in branches if not merged_flags.get(b, False)]
    scope = sorted(open_branches, key=lambda b: _branch_rank(b, ticket))
    if not scope:
        return {"scope": [], "lowestOpen": None, "reparentParent": None}
    lowest_open = scope[0]
    lo_rank = _branch_rank(lowest_open, ticket)
    # The tracked parent is the highest-ranked branch strictly below the lowest open
    # branch. If that parent is a merged ancestor, the lowest open slice must be
    # re-parented onto trunk.
    below = [b for b in branches if _branch_rank(b, ticket) < lo_rank]
    reparent_parent = None
    if below:
        parent = max(below, key=lambda b: _branch_rank(b, ticket))
        if parent in ancestors:
            reparent_parent = parent
    return {"scope": scope, "lowestOpen": lowest_open, "reparentParent": reparent_parent}


def _infer_ticket(branches):
    """Infer the ticket id from a branch set sharing a common `<ticket>/...` prefix.

    Branch names are `<ticket>/<phase>` (e.g. RUS-1/design, RUS-1/slice-2). Returns the
    portion before the first '/' of any branch (they all share it for one ticket's
    stack). Returns "" for an empty set. Pure."""
    for b in sorted(branches):
        if "/" in b:
            return b.split("/", 1)[0]
    return ""


def classify_result(rc, stdout, stderr):
    """Map a `gt restack` (rc, stdout, stderr) to (ok, restacked, error). Pure, so the
    success/failure/no-op decision is unit-testable without running gt.

    - rc == 0  -> ok=True; restacked=False only when output clearly says nothing was
      done, else True.
    - rc != 0  -> ok=False; error is the trimmed stderr (falling back to stdout), which
      for a conflict carries gt's verbatim message.
    """
    if rc == 0:
        lines = [ln.strip() for ln in
                 ("%s\n%s" % (stdout or "", stderr or "")).splitlines() if ln.strip()]
        # Nothing moved iff there is no output, or every line is a "does not need to be
        # restacked" no-op line. Any other line (e.g. an actual "Restacking ..." line)
        # means at least one branch was rebased.
        restacked = any(_NOOP_PHRASE not in ln for ln in lines) if lines else False
        return True, restacked, None
    msg = (stderr or "").strip() or (stdout or "").strip() or "gt restack failed (rc=%d)" % rc
    return False, False, msg


def classify_submit(rc, stdout, stderr):
    """Map a `gt submit` (rc, stdout, stderr) to (ok, error). Pure, so the push
    success/failure decision is unit-testable without running gt.

    - rc == 0  -> ok=True, no error.
    - rc != 0  -> ok=False; error is the trimmed stderr (falling back to stdout), prefixed
      so the caller's log makes clear the restack succeeded but the push did not.
    """
    if rc == 0:
        return True, None
    detail = (stderr or "").strip() or (stdout or "").strip() or "gt submit failed (rc=%d)" % rc
    return False, "restack succeeded but gt submit --stack failed: %s" % detail


def build_envelope(ticket, worktree_dir, tip, ok=True, restacked=False, submitted=False,
                   error=None):
    """Assemble the JSON envelope the qrspi-batch ensureRestacked() step consumes.
    Pure; `repoRoot` is always the module-level REPO_ROOT this script derived."""
    env = {
        "ok": ok,
        "repoRoot": REPO_ROOT,
        "ticket": ticket,
        "worktreeDir": worktree_dir,
        "tip": tip,
        "restacked": restacked,
        "submitted": submitted,
    }
    if error is not None:
        env["error"] = error
    return env


# --- subprocess-backed mechanics (not unit-tested; manual e2e) -------------

def _run(cmd, cwd=None):
    """Run a command, returning (returncode, stdout, stderr) with text output."""
    res = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    return res.returncode, res.stdout, res.stderr


def existing_branches(ticket):
    """Normalised set of the ticket's branches (`<ticket>/*`) as Graphite sees them."""
    rc, out, _ = _run(["git", "branch", "--list", "%s/*" % ticket], cwd=REPO_ROOT)
    return branch_set(out.splitlines()) if rc == 0 else set()


def read_merge_state(ticket, branches):
    """Read each branch's PR-merged status via gh GraphQL and fold it through the
    tested `stack_merge_state` classifier. Returns the StackMergeState shape
    `{ branch: {merged, prNumber, state, mergedByPr} }`.

    Impure shell boundary (the only new network read): resolves owner/repo from the
    gh-authenticated repo (same `gh repo view`/`parse_name_with_owner` path the
    resolver uses), runs the shared PR_QUERY once per branch head ref, and builds the
    `{branch: nodes}` map `stack_merge_state` consumes. A branch whose gh query fails
    (e.g. its head ref was deleted after merge) degrades to no nodes -> the documented
    not-merged sentinel inside stack_merge_state, never a crash (ref: structure.md
    "New impure shell boundary"; Decision 2A). Intentionally untested per the
    pure-core/impure-shell split (Q11); the merge logic it feeds is tested in
    qrspi_pr_state_test.py."""
    branches = list(branches)
    if not branches:
        return {}
    owner, repo = parse_name_with_owner(_gh_name_with_owner(REPO_ROOT))
    graphql_nodes = {}
    for head in branches:
        rc, out, _ = _run(
            ["gh", "api", "graphql",
             "-f", "query=%s" % PR_QUERY,
             "-F", "owner=%s" % owner, "-F", "repo=%s" % repo, "-F", "head=%s" % head],
            cwd=REPO_ROOT)
        if rc != 0:
            # A failed read (commonly a head ref GitHub already deleted post-merge)
            # -> no nodes -> stack_merge_state maps it to the not-merged sentinel.
            graphql_nodes[head] = []
            continue
        try:
            data = json.loads(out)
            graphql_nodes[head] = data["data"]["repository"]["pullRequests"]["nodes"]
        except (ValueError, KeyError, TypeError):
            graphql_nodes[head] = []
    return stack_merge_state(branches, graphql_nodes)


def reparent_lowest_open(branch, worktree):
    """Re-parent the ticket's lowest still-open slice onto trunk, dropping a merged
    ancestor as its tracked parent (Decision 1, Option A). Returns (rc, out, err).

    Runs `gt move --onto main --source <branch>` from the worktree, scoped to exactly
    this one branch (the lowest open slice the caller already isolated). In gt 1.8.6
    `gt move` rebases the source branch onto the target AND restacks its descendants, so
    the one call both fixes the tracked-parent metadata (now trunk, not the merged
    ancestor) and re-aligns the open slices above it — never touching the whole stack's
    trunk and never another ticket's branches. After this the subsequent `--stack`
    submit walks from the open tip down to trunk without ever stepping into a merged
    ancestor (which is what aborted the submit). `--no-interactive` is required so it
    never opens a selector in the batch. Impure shell boundary, intentionally untested
    per the pure-core/impure-shell split (Q11); the `gt move --onto/--source` flags were
    confirmed against the installed gt 1.8.6."""
    return _run(["gt", "move", "--onto", "main", "--source", branch, "--no-interactive"],
                cwd=worktree)


def submit_stack(worktree):
    """Force-push the realigned stack to its existing phase PRs. Returns (ok, error).

    Runs from the tip (already checked out by restack()); `--stack` covers the whole
    chain, `--force` is required because the restack rewrote history so the remote has
    diverged. `--publish` keeps the phase PRs published (the lifecycle never holds a
    phase PR as a draft) and matches the land step's "ensure remotes current" call."""
    rc, out, err = _run(
        ["gt", "submit", "--publish", "--stack", "--force", "--no-edit", "--no-interactive"],
        cwd=worktree)
    return classify_submit(rc, out, err)


def restack(worktree, tip, ticket, branches):
    """Restack the ticket's open slices onto current trunk from its tip, downstack, then
    push the realigned branches to their PRs — merged-ancestor-aware.

    Returns (ok, restacked, submitted, error). Two new merge-aware paths gate the
    existing restack/submit (ref: structure.md Slice 1; design.md Delta, Decisions 1 & 2,
    OQ3):

    1. Fully-landed short-circuit: read the stack's per-branch merge state and, when
       EVERY branch's PR is merged (is_stack_fully_merged), return immediately with
       ok=True, restacked=False, submitted=False — no `gt checkout`/`restack`/`submit`
       runs at all. Re-restacking/submitting an already-landed stack is the work that
       aborted; skipping it is the whole point (OQ3).

    2. Partial-land re-parent: when some lower slices are merged but the top is still
       open, the lowest open slice's tracked parent is a merged ancestor that `gt` would
       walk into and abort on. Compute submit_scope(); if its reparentParent is set,
       `gt move --onto main` that lowest open slice onto trunk FIRST, dropping the merged
       ancestor, then run the existing checkout/restack/submit over the now-trunk-rooted
       open chain (Decision 1A).

    On a restack conflict (non-zero rc) we `gt abort` to restore a clean working tree — a
    half-applied rebase would otherwise wedge the worktree for every later action — then
    report the conflict verbatim. We do NOT try to resolve the conflict: a branch that
    genuinely conflicts with the new trunk needs human attention. When the restack
    actually moved a branch, we force-push the stack so the remote PRs stop pointing at
    the pre-restack commits; a push failure is reported as ok=False (the tree is already
    clean, so no abort) so the divergence surfaces instead of silently persisting."""
    # --- merge-state gate (before any gt work) -----------------------------
    merge_state = read_merge_state(ticket, branches)
    if is_stack_fully_merged(merge_state):
        # Every PR is merged: the stack is fully landed. Re-restacking/submitting it is
        # exactly the work that aborted, so short-circuit with a clean no-op success and
        # let the caller dispatch land/done instead of restack_conflict (OQ3).
        return True, False, False, None

    merged_flags = {b: merge_state.get(b, {}).get("merged", False) for b in branches}
    scope = submit_scope(branches, merged_flags, ticket)

    # Partial land: the lowest open slice sits on a merged ancestor. Re-parent it onto
    # trunk FIRST so the upcoming downstack restack/submit never walks into the merged
    # ancestor that aborts gt (Decision 1A). reparentParent is None for a fully-open
    # stack, so this is a no-op there and the behaviour is unchanged.
    if scope.get("reparentParent") and scope.get("lowestOpen"):
        rc, out, err = reparent_lowest_open(scope["lowestOpen"], worktree)
        if rc != 0:
            return False, False, False, (
                "gt move %s --onto main failed: %s"
                % (scope["lowestOpen"], (err or out).strip()))

    # gt checkout the tip so `--downstack` covers the entire ticket chain
    # (tip -> ... -> design -> trunk), rebasing the bottom onto the current trunk tip.
    rc, out, err = _run(["gt", "checkout", tip, "--no-interactive"], cwd=worktree)
    if rc != 0:
        return False, False, False, ("gt checkout %s failed: %s" % (tip, (err or out).strip()))

    rc, out, err = _run(["gt", "restack", "--downstack", "--no-interactive"], cwd=worktree)
    ok, restacked, error = classify_result(rc, out, err)
    if not ok:
        # Leave no half-restacked state behind; abort is best-effort and its own failure
        # must not mask the original conflict message.
        _run(["gt", "abort", "--force", "--no-interactive"], cwd=worktree)
        return ok, restacked, False, error

    # Nothing moved -> remote already matches local; skip the push entirely.
    if not restacked:
        return ok, restacked, False, None

    submit_ok, submit_err = submit_stack(worktree)
    if not submit_ok:
        return False, restacked, False, submit_err
    return True, restacked, True, None


def main():
    parser = argparse.ArgumentParser(
        description="Restack a QRSPI ticket's stack onto current trunk (self-locating)")
    parser.add_argument("--ticket", required=True, help="Ticket id, e.g. RUS-21")
    args = parser.parse_args()

    worktree = worktree_path(REPO_ROOT, args.ticket)

    # Nothing to restack if the ticket has no worktree or no branch yet (e.g. a fresh
    # run_design before its design branch exists). That is a clean no-op success.
    if not os.path.isdir(worktree):
        env = build_envelope(args.ticket, worktree, None, ok=True, restacked=False)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 0

    branches = existing_branches(args.ticket)
    tip = pick_tip(branches, args.ticket)
    if tip is None:
        env = build_envelope(args.ticket, worktree, None, ok=True, restacked=False)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 0

    ok, restacked, submitted, error = restack(worktree, tip, args.ticket, branches)
    env = build_envelope(args.ticket, worktree, tip, ok=ok, restacked=restacked,
                         submitted=submitted, error=error)
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
