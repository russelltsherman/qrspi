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
import subprocess
import sys

# The script lives at <repo-root>/scripts/qrspi_restack.py, so the repo root is two
# levels up. Deriving it from __file__ (not cwd, not an argument) is the whole point:
# it removes the path a weak worker model keeps corrupting.
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(_SCRIPT_DIR)
sys.path.insert(0, _SCRIPT_DIR)

from qrspi_pr_state import branch_set  # noqa: E402
from qrspi_resolve import pick_tip      # noqa: E402

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


def restack(worktree, tip):
    """Restack the ticket's whole stack onto current trunk from its tip, downstack, then
    push the realigned branches to their PRs.

    Returns (ok, restacked, submitted, error). On a restack conflict (non-zero rc) we
    `gt abort` to restore a clean working tree — a half-applied rebase would otherwise
    wedge the worktree for every later action — then report the conflict verbatim. We do
    NOT try to resolve the conflict: a branch that genuinely conflicts with the new trunk
    needs human attention. When the restack actually moved a branch, we force-push the
    stack so the remote PRs stop pointing at the pre-restack commits; a push failure is
    reported as ok=False (the tree is already clean, so no abort) so the divergence
    surfaces instead of silently persisting."""
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

    tip = pick_tip(existing_branches(args.ticket), args.ticket)
    if tip is None:
        env = build_envelope(args.ticket, worktree, None, ok=True, restacked=False)
        json.dump(env, sys.stdout, indent=2)
        print()
        return 0

    ok, restacked, submitted, error = restack(worktree, tip)
    env = build_envelope(args.ticket, worktree, tip, ok=ok, restacked=restacked,
                         submitted=submitted, error=error)
    json.dump(env, sys.stdout, indent=2)
    print()
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
