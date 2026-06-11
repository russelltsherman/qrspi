#!/usr/bin/env python3
"""Tests for qrspi_cleanup.

Two layers:
  1. PURE classifier tests for `classify_cleanup` (destroy/skip/blocked) — stdlib-only,
     no subprocess (ref: Q13, Q14). UNCHANGED by RUS-68.
  2. GIT-FIXTURE tests for the remote-ref prune path (RUS-68 Decision 3 Option A): a temp
     git repo + a local BARE repo as "origin" exercise `_prune_remote_refs`/`run` and
     assert against REAL post-run `git ls-remote` state — the only way to catch the
     presence-based false-success bug (AC4). These DEPART from the repo's stdlib-only /
     pure-classifier-only convention deliberately, because the bug lives entirely in the
     impure mechanics. Skip-guarded when `git` is unavailable.

Run: python3 scripts/qrspi_cleanup_test.py
"""

import os
import shutil
import subprocess
import sys
import tempfile

import qrspi_cleanup
from qrspi_cleanup import classify_cleanup
from qrspi_pr_state import stack_merge_state

failures = 0
total = 0


def check(name, got, want):
    global failures, total
    total += 1
    if got != want:
        print("FAIL: %s\n      expected %r\n      got      %r" % (name, want, got))
        failures += 1
    else:
        print("ok: %s" % name)


def check_true(name, cond):
    check(name, bool(cond), True)


def _node(number, state, merged):
    """One branch's GraphQL pullRequests.nodes list (the shape stack_merge_state
    consumes), mirroring the qrspi_pr_state_test fixture helper."""
    return [{"number": number, "state": state, "merged": merged,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}]


# --- Case 1: merged stack, clean worktree -> destroy ------------------------
_merged = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "MERGED", True)})
check("merged + clean -> destroy",
      classify_cleanup(_merged, ""),
      {"decision": "destroy", "reason": "stack fully merged"})


# --- Case 2: partially-merged stack, clean worktree -> skip -----------------
_partial = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("partial + clean -> skip",
      classify_cleanup(_partial, ""),
      {"decision": "skip", "reason": "stack not fully merged"})


# --- Case 3: dirty porcelain -> blocked (takes precedence over merge state) --
check("dirty porcelain -> blocked",
      classify_cleanup(_merged, " M scripts/foo.py\n")["decision"],
      "blocked")

check("dirty porcelain blocks even a fully-merged stack",
      classify_cleanup(_merged, "?? untracked.txt\n")["decision"],
      "blocked")

check("whitespace-only porcelain is NOT dirty (treated clean)",
      classify_cleanup(_merged, "   \n")["decision"],
      "destroy")


# --- Case 4: in-flight stack (all OPEN), clean worktree -> skip -------------
_inflight = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "OPEN", False),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("in-flight + clean -> skip",
      classify_cleanup(_inflight, ""),
      {"decision": "skip", "reason": "stack not fully merged"})


# --- Edge: empty stack, clean worktree -> skip (nothing merged != fully) ----
check("empty stack + clean -> skip",
      classify_cleanup({}, "")["decision"],
      "skip")

# --- Edge: empty stack but dirty -> blocked still wins ----------------------
check("empty stack + dirty -> blocked",
      classify_cleanup({}, " M a\n")["decision"],
      "blocked")


# ===========================================================================
# Git-fixture tests for the remote-ref prune path (RUS-68 Decision 3 Option A)
# ===========================================================================

def _git_available():
    try:
        rc = subprocess.run(["git", "--version"], capture_output=True).returncode
        return rc == 0
    except (OSError, FileNotFoundError):
        return False


def _git(args, cwd):
    """Run git in `cwd`, raising on failure (fixtures must be deterministic)."""
    res = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args),
                                                  res.stderr.strip() or res.stdout.strip()))
    return res.stdout


class _Fixture:
    """A temp git repo wired to a local BARE repo as `origin` (no network).

    `__enter__` returns self with:
      - .repo  — the working repo (stands in for REPO_ROOT)
      - .origin — the bare origin path
    It points qrspi_cleanup.REPO_ROOT at the working repo for the duration. The
    working repo has `main` plus whatever `<ticket>/*` refs the test seeds via
    `seed_remote_ref`. Cleans up the temp dirs and restores REPO_ROOT on exit."""

    def __init__(self, ticket):
        self.ticket = ticket
        self.tmp = None
        self.repo = None
        self.origin = None
        self._saved_root = None

    def __enter__(self):
        self.tmp = tempfile.mkdtemp(prefix="qrspi_cleanup_fixture_")
        self.origin = os.path.join(self.tmp, "origin.git")
        self.repo = os.path.join(self.tmp, "work")
        _git(["init", "--bare", "-b", "main", self.origin], cwd=self.tmp)
        _git(["init", "-b", "main", self.repo], cwd=self.tmp)
        _git(["config", "user.email", "t@example.com"], cwd=self.repo)
        _git(["config", "user.name", "t"], cwd=self.repo)
        _git(["remote", "add", "origin", self.origin], cwd=self.repo)
        # Seed a main commit and push it so origin has a trunk.
        with open(os.path.join(self.repo, "README"), "w") as fh:
            fh.write("seed\n")
        _git(["add", "README"], cwd=self.repo)
        _git(["commit", "-m", "seed"], cwd=self.repo)
        _git(["push", "origin", "main"], cwd=self.repo)
        # Redirect the module's self-located REPO_ROOT at our working repo.
        self._saved_root = qrspi_cleanup.REPO_ROOT
        qrspi_cleanup.REPO_ROOT = self.repo
        return self

    def __exit__(self, *exc):
        qrspi_cleanup.REPO_ROOT = self._saved_root
        if self.tmp and os.path.isdir(self.tmp):
            shutil.rmtree(self.tmp, ignore_errors=True)
        return False

    def seed_remote_ref(self, branch):
        """Create `branch` locally, push it to origin, then (by default) leave only the
        origin ref — caller decides whether a local branch lingers."""
        _git(["branch", branch, "main"], cwd=self.repo)
        _git(["push", "origin", "%s:%s" % (branch, branch)], cwd=self.repo)

    def remote_branches(self):
        """The set of `<ticket>/*` branch names currently on the bare origin."""
        return set(qrspi_cleanup._remote_refs(self.ticket))


def _make_gt_deleter(fixture, *, only=None, do_nothing=False):
    """Build a stand-in for `_gt_prune_remotes` that drives a DETERMINISTIC offline
    outcome against the bare origin.

    This substitutes ONLY the single remote-MUTATING seam (`_gt_prune_remotes`); the real
    discovery, post-prune `git ls-remote` confirmation, and removed/failedRemotes
    partition in `_prune_remote_refs` still run against the real bare origin. That is
    exactly what makes the test observe TRUE post-run state rather than asserting intent.

      - do_nothing=True  → simulate the ORIGINAL no-op bug (gt ran but deleted nothing),
                           so confirmation must report the refs as survivors (failedRemotes).
      - only=<set>       → delete only those origin refs (the rest survive → failedRemotes).
      - default          → delete every `<ticket>/*` origin ref the fixture knows about.
    """
    def _deleter(branches):
        if do_nothing:
            return
        targets = set(branches) if only is None else (set(branches) & set(only))
        for b in sorted(targets):
            # Delete the ref on the bare origin via a delete-refspec push (the fixture's
            # stand-in for gt's remote prune). gt mutation is NOT exercised here — only
            # the *effect* gt would have, so the confirmation path is what's under test.
            subprocess.run(["git", "push", "origin", "--delete", b],
                           cwd=fixture.repo, capture_output=True, text=True)
    return _deleter


def _with_gt(deleter, fn):
    """Run `fn()` with `_gt_prune_remotes` temporarily replaced by `deleter`."""
    saved = qrspi_cleanup._gt_prune_remotes
    qrspi_cleanup._gt_prune_remotes = deleter
    try:
        return fn()
    finally:
        qrspi_cleanup._gt_prune_remotes = saved


def run_fixture_tests():
    if not _git_available():
        print("SKIP: git unavailable — fixture tests skipped (pure tests still ran)")
        return

    ticket = "RUS-1"
    nsref = "%s/slice-1" % ticket

    # --- T14/T15: core deletion test — removed.remotes reflects REAL post-run absence,
    #     and the SAME path catches the presence-based false-success bug ---------------
    with _Fixture(ticket) as fx:
        fx.seed_remote_ref(nsref)
        check_true("fixture: ref present on origin before prune",
                   nsref in fx.remote_branches())

        # Real deletion: gt-seam deletes the ref; confirmation must report it removed.
        res = _with_gt(
            _make_gt_deleter(fx),
            lambda: qrspi_cleanup._prune_remote_refs(ticket, {nsref}, dry_run=False))
        check("core: confirmed-deleted ref lands in removed",
              (res.removed, res.failedRemotes), ([nsref], []))
        check_true("core: ref ACTUALLY gone from origin (real ls-remote)",
                   nsref not in fx.remote_branches())

    # T15 — the regression guard: if the gt mutation is a NO-OP (the original bug), the
    # presence-based code would still have reported the ref "removed". The confirmed-
    # outcome code instead reports it as a SURVIVOR (failedRemotes), never removed.
    with _Fixture(ticket) as fx:
        fx.seed_remote_ref(nsref)
        res = _with_gt(
            _make_gt_deleter(fx, do_nothing=True),
            lambda: qrspi_cleanup._prune_remote_refs(ticket, {nsref}, dry_run=False))
        check("false-success guard: no-op prune → survivor, NOT removed",
              (res.removed, res.failedRemotes), ([], [nsref]))
        check_true("false-success guard: ref still present on origin",
                   nsref in fx.remote_branches())

    # --- T17: survivor case — one ref deleted, one survives → failedRemotes ----------
    with _Fixture(ticket) as fx:
        a, b = "%s/slice-1" % ticket, "%s/slice-2" % ticket
        fx.seed_remote_ref(a)
        fx.seed_remote_ref(b)
        res = _with_gt(
            _make_gt_deleter(fx, only={a}),
            lambda: qrspi_cleanup._prune_remote_refs(ticket, {a, b}, dry_run=False))
        check("survivor: deleted ref in removed, survivor in failedRemotes",
              (res.removed, res.failedRemotes), ([a], [b]))
        check_true("survivor: survivor still on origin", b in fx.remote_branches())
        check_true("survivor: deleted ref gone from origin", a not in fx.remote_branches())

    # --- T18: dry-run mutates NOTHING -------------------------------------------------
    with _Fixture(ticket) as fx:
        fx.seed_remote_ref(nsref)
        # If dry-run ever calls the gt seam, this deleter would mutate origin; assert it
        # does NOT by also wiring a deleter that WOULD delete.
        res = _with_gt(
            _make_gt_deleter(fx),
            lambda: qrspi_cleanup._prune_remote_refs(ticket, {nsref}, dry_run=True))
        check("dry-run: candidate reported in removed (would-delete)",
              (res.removed, res.failedRemotes), ([nsref], []))
        check_true("dry-run: origin UNCHANGED (ref still present)",
                   nsref in fx.remote_branches())

    # --- T16: worktree-only stranded-ref reaping via run() ----------------------------
    # Empty local branch set + merged <ticket>/* refs on origin → additive path deletes
    # them and reports them in removed.remotes (AC3). We stub the merge-state gather to
    # report the origin refs fully merged (the gate), and the worktree path / gh owner
    # lookups so run() exercises only the stranded path against the real bare origin.
    with _Fixture(ticket) as fx:
        fx.seed_remote_ref(nsref)
        # The fixture repo has the local branch from seed_remote_ref; delete it so the
        # local set is EMPTY (the worktree-only condition) while origin keeps the ref.
        _git(["branch", "-D", nsref], cwd=fx.repo)
        check_true("stranded: local branch set is empty",
                   not qrspi_cleanup._stack_branches(ticket))
        check_true("stranded: origin still carries the ref",
                   nsref in fx.remote_branches())

        saved = {
            "_gh_owner_repo": qrspi_cleanup._gh_owner_repo,
            "_gather_merge_state": qrspi_cleanup._gather_merge_state,
            "worktree_path": qrspi_cleanup.worktree_path,
            "_gt_prune_remotes": qrspi_cleanup._gt_prune_remotes,
        }
        qrspi_cleanup._gh_owner_repo = lambda: ("o", "r")
        qrspi_cleanup.worktree_path = lambda root, t: os.path.join(fx.tmp, "no-wt")
        qrspi_cleanup._gather_merge_state = lambda owner, repo, branches: {
            b: {"merged": True, "prNumber": 1, "state": "MERGED"} for b in branches}
        qrspi_cleanup._gt_prune_remotes = _make_gt_deleter(fx)
        try:
            env = qrspi_cleanup.run(ticket, dry_run=False)
        finally:
            for k, v in saved.items():
                setattr(qrspi_cleanup, k, v)

        check("stranded: envelope decision is destroy", env["decision"], "destroy")
        check("stranded: ref reported in removed.remotes",
              env["removed"]["remotes"], [nsref])
        check("stranded: failedRemotes empty, ok true",
              (env["failedRemotes"], env["ok"]), ([], True))
        check_true("stranded: ref ACTUALLY gone from origin",
                   nsref not in fx.remote_branches())

    # --- Survivor via run(): ok stays TRUE on non-empty failedRemotes (RQ2) -----------
    with _Fixture(ticket) as fx:
        a, b = "%s/slice-1" % ticket, "%s/slice-2" % ticket
        fx.seed_remote_ref(a)
        fx.seed_remote_ref(b)
        _git(["branch", "-D", a], cwd=fx.repo)
        _git(["branch", "-D", b], cwd=fx.repo)
        saved = {
            "_gh_owner_repo": qrspi_cleanup._gh_owner_repo,
            "_gather_merge_state": qrspi_cleanup._gather_merge_state,
            "worktree_path": qrspi_cleanup.worktree_path,
            "_gt_prune_remotes": qrspi_cleanup._gt_prune_remotes,
        }
        qrspi_cleanup._gh_owner_repo = lambda: ("o", "r")
        qrspi_cleanup.worktree_path = lambda root, t: os.path.join(fx.tmp, "no-wt")
        qrspi_cleanup._gather_merge_state = lambda owner, repo, branches: {
            x: {"merged": True, "prNumber": 1, "state": "MERGED"} for x in branches}
        qrspi_cleanup._gt_prune_remotes = _make_gt_deleter(fx, only={a})
        try:
            env = qrspi_cleanup.run(ticket, dry_run=False)
        finally:
            for k, v in saved.items():
                setattr(qrspi_cleanup, k, v)
        check("run-survivor: ok:true with non-empty failedRemotes (RQ2)",
              (env["ok"], env["removed"]["remotes"], env["failedRemotes"]),
              (True, [a], [b]))


def report():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    run_fixture_tests()
    sys.exit(report())
