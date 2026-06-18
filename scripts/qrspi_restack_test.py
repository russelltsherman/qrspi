#!/usr/bin/env python3
"""Unit tests for qrspi_restack pure helpers (worktree path, gt-result classification,
envelope assembly, and the tip-branch selection it relies on). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_restack_test.py

The subprocess-backed parts (gt checkout/restack/abort, git branch) are intentionally
NOT tested here — same convention as qrspi_resolve_test.py / qrspi_persist_test.py — and
are verified by a manual end-to-end run against a deliberately-stale branch.
"""

import os
import sys

import shutil
import subprocess
import tempfile

from qrspi_restack import (
    worktree_path,
    classify_result,
    classify_submit,
    build_envelope,
    merged_ancestors,
    submit_scope,
    provision_worktree,
    REPO_ROOT,
)
from qrspi_resolve import pick_tip, worktree_is_healthy

failures = 0
total = 0


def check(label, got, want):
    global failures, total
    total += 1
    if got == want:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))


# --- worktree_path ----------------------------------------------------------
check("worktree path is <repo>/.worktrees/<ticket>",
      worktree_path("/repo", "RUS-1"), "/repo/.worktrees/RUS-1")

# --- classify_result --------------------------------------------------------
check("rc=0 with restack output -> ok, restacked",
      classify_result(0, "Restacking RUS-1/design on main.", ""), (True, True, None))
check("rc=0 no-op (real gt phrasing) -> ok, not restacked",
      classify_result(0, "RUS-1/design does not need to be restacked on main.", ""),
      (True, False, None))
check("rc=0 all-branches no-op (multiline) -> ok, not restacked",
      classify_result(0,
                      "RUS-1/design does not need to be restacked on main.\n"
                      "RUS-1/plan does not need to be restacked on RUS-1/design.", ""),
      (True, False, None))
check("rc=0 mixed (one moved, one no-op) -> ok, restacked",
      classify_result(0,
                      "RUS-1/design does not need to be restacked on main.\n"
                      "Restacking RUS-1/plan on RUS-1/design.", ""),
      (True, True, None))
check("rc=0 with no output at all -> ok, not restacked",
      classify_result(0, "", ""), (True, False, None))
check("rc!=0 conflict -> not ok, error is stderr verbatim",
      classify_result(1, "", "CONFLICT: merge conflict in foo.py"),
      (False, False, "CONFLICT: merge conflict in foo.py"))
check("rc!=0 falls back to stdout when stderr empty",
      classify_result(1, "could not apply", ""),
      (False, False, "could not apply"))
check("rc!=0 with neither stream -> synthesized message",
      classify_result(2, "", ""), (False, False, "gt restack failed (rc=2)"))
check("rc!=0 trims surrounding whitespace",
      classify_result(1, "", "  boom  \n"), (False, False, "boom"))

# --- classify_submit --------------------------------------------------------
check("submit rc=0 -> ok, no error",
      classify_submit(0, "Submitting 2 PRs...", ""), (True, None))
check("submit rc=0 no output -> ok, no error",
      classify_submit(0, "", ""), (True, None))
check("submit rc!=0 -> not ok, prefixed stderr",
      classify_submit(1, "", "failed to push to origin"),
      (False, "restack succeeded but gt submit --stack failed: failed to push to origin"))
check("submit rc!=0 falls back to stdout when stderr empty",
      classify_submit(1, "remote rejected", ""),
      (False, "restack succeeded but gt submit --stack failed: remote rejected"))
check("submit rc!=0 with neither stream -> synthesized detail",
      classify_submit(2, "", ""),
      (False, "restack succeeded but gt submit --stack failed: gt submit failed (rc=2)"))

# --- build_envelope ---------------------------------------------------------
ok_env = build_envelope("RUS-1", "/wt/RUS-1", "RUS-1/design", ok=True, restacked=True,
                        submitted=True)
check("ok envelope ok flag", ok_env["ok"], True)
check("ok envelope restacked flag", ok_env["restacked"], True)
check("ok envelope submitted flag", ok_env["submitted"], True)
check("ok envelope ticket", ok_env["ticket"], "RUS-1")
check("ok envelope worktreeDir", ok_env["worktreeDir"], "/wt/RUS-1")
check("ok envelope tip", ok_env["tip"], "RUS-1/design")
check("ok envelope repoRoot is derived REPO_ROOT", ok_env["repoRoot"], REPO_ROOT)
check("ok envelope has no error key", "error" in ok_env, False)

noop_env = build_envelope("RUS-1", "/wt/RUS-1", None, ok=True, restacked=False)
check("no-op envelope ok with null tip", (noop_env["ok"], noop_env["tip"]), (True, None))
check("no-op envelope not restacked", noop_env["restacked"], False)
check("no-op envelope not submitted (default)", noop_env["submitted"], False)

err_env = build_envelope("RUS-1", "/wt/RUS-1", "RUS-1/slice-2", ok=False, restacked=False,
                         error="CONFLICT in bar.py")
check("err envelope ok flag", err_env["ok"], False)
check("err envelope error message", err_env["error"], "CONFLICT in bar.py")
check("err envelope not submitted", err_env["submitted"], False)

# --- pick_tip (the tip-branch selection restack relies on) ------------------
check("tip picks design when only design exists",
      pick_tip({"RUS-1/design"}, "RUS-1"), "RUS-1/design")
check("tip picks plan over design",
      pick_tip({"RUS-1/design", "RUS-1/plan"}, "RUS-1"), "RUS-1/plan")
check("tip picks highest slice over plan/design",
      pick_tip({"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1", "RUS-1/slice-3"}, "RUS-1"),
      "RUS-1/slice-3")
check("tip is None when ticket has no branch",
      pick_tip(set(), "RUS-1"), None)

# --- merged_ancestors / submit_scope (merged-ancestor-aware restack) --------
# A ticket's stack ordering is design < plan < slice-1 < slice-2 < ...; branches is the
# set from branch_set(), merged_flags maps branch -> bool (its PR merged).

# Fully-open input: no branch merged. No merged ancestors; submit_scope covers the whole
# stack in order and flags no re-parent.
_open_branches = {"RUS-1/slice-1", "RUS-1/slice-2"}
check("fully-open: no merged ancestors",
      merged_ancestors(_open_branches, {}), set())
check("fully-open: scope is the full open stack in order",
      submit_scope(_open_branches, {}, "RUS-1")["scope"],
      ["RUS-1/slice-1", "RUS-1/slice-2"])
check("fully-open: lowestOpen is the bottom slice",
      submit_scope(_open_branches, {}, "RUS-1")["lowestOpen"], "RUS-1/slice-1")
check("fully-open: reparentParent unset",
      submit_scope(_open_branches, {}, "RUS-1")["reparentParent"], None)

# Partial-land input: lower slices merged, top slice open. merged_ancestors returns the
# merged lower slices; submit_scope.scope is the open slices only and the lowest open
# slice is flagged for re-parent onto trunk (its tracked parent is a merged ancestor).
_partial_branches = {"RUS-1/slice-1", "RUS-1/slice-2", "RUS-1/slice-3"}
_partial_flags = {"RUS-1/slice-1": True, "RUS-1/slice-2": True}
check("partial-land: merged lower slices are the ancestors",
      merged_ancestors(_partial_branches, _partial_flags),
      {"RUS-1/slice-1", "RUS-1/slice-2"})
check("partial-land: scope is open slices only",
      submit_scope(_partial_branches, _partial_flags, "RUS-1")["scope"],
      ["RUS-1/slice-3"])
check("partial-land: lowest open slice flagged for re-parent",
      submit_scope(_partial_branches, _partial_flags, "RUS-1")["lowestOpen"],
      "RUS-1/slice-3")
check("partial-land: reparentParent is the merged ancestor immediately below",
      submit_scope(_partial_branches, _partial_flags, "RUS-1")["reparentParent"],
      "RUS-1/slice-2")

# Partial-land across phases: design+plan merged, slice-1 open. The lowest open slice's
# tracked parent (plan) is a merged ancestor, so it must re-parent onto trunk.
_phase_branches = {"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1"}
_phase_flags = {"RUS-1/design": True, "RUS-1/plan": True}
check("phase partial-land: design+plan are merged ancestors",
      merged_ancestors(_phase_branches, _phase_flags),
      {"RUS-1/design", "RUS-1/plan"})
check("phase partial-land: reparentParent is the merged plan branch",
      submit_scope(_phase_branches, _phase_flags, "RUS-1")["reparentParent"],
      "RUS-1/plan")

# Fully-landed input: every slice merged. There is no open branch, so merged_ancestors is
# empty and submit_scope returns the empty/short-circuit scope (the caller short-circuits
# via is_stack_fully_merged before any gt work).
_landed_branches = {"RUS-1/slice-1", "RUS-1/slice-2"}
_landed_flags = {"RUS-1/slice-1": True, "RUS-1/slice-2": True}
check("fully-landed: no merged ancestors (no open branch to sit below)",
      merged_ancestors(_landed_branches, _landed_flags), set())
check("fully-landed: empty short-circuit scope",
      submit_scope(_landed_branches, _landed_flags, "RUS-1"),
      {"scope": [], "lowestOpen": None, "reparentParent": None})

# --- restack re-provisions / self-heals the worktree in-process (hermetic real-git) ---
# Regression for the orphaned-worktree restack failure (RUS-85/RUS-87 restack_conflict):
# resolve provisions the worktree in an EARLIER agent, but the `.git/worktrees/<id>` admin
# metadata can vanish across the agent/process boundary in the sandbox (the `.worktrees/<id>`
# working dir survives, its admin dir is pruned/lost), re-orphaning the worktree. restack
# runs as its OWN agent, so it must (re)provision a healthy worktree IN ITS OWN PROCESS
# before `gt checkout` — else the checkout dies with "fatal: not a git repository". These
# pin that in-process self-heal against a throwaway real-git repo (no gt/gh needed).

def _git2(args, cwd):
    res = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("git %s failed: %s" % (" ".join(args), res.stderr.strip()))
    return res


def _run_restack_provision_tests():
    with tempfile.TemporaryDirectory() as root:
        _git2(["init", "-b", "main"], root)
        _git2(["config", "user.email", "t@t.t"], root)
        _git2(["config", "user.name", "t"], root)
        with open(os.path.join(root, "f.txt"), "w") as fh:
            fh.write("seed\n")
        _git2(["add", "."], root)
        _git2(["commit", "-m", "seed"], root)
        _git2(["branch", "RUS-1/design"], root)
        wt = os.path.join(root, ".worktrees", "RUS-1")

        # 1. First provision creates a healthy worktree at the canonical path.
        got = provision_worktree("RUS-1", repo_root=root)
        check("provision_worktree returns the canonical worktree path", got, wt)
        check("provisioned worktree is healthy", worktree_is_healthy(wt), True)

        # 2. Orphan it (admin metadata gone, working dir survives) — the cross-agent
        #    vanish — then re-provision: it must SELF-HEAL, not reuse the dead dir.
        shutil.rmtree(os.path.join(root, ".git", "worktrees", "RUS-1"))
        check("orphaned worktree dir survives on disk", os.path.isdir(wt), True)
        check("orphaned worktree detected unhealthy", worktree_is_healthy(wt), False)
        healed = provision_worktree("RUS-1", repo_root=root)
        check("re-provision self-heals to a healthy worktree",
              worktree_is_healthy(healed), True)
        head = subprocess.run(["git", "-C", wt, "rev-parse", "--abbrev-ref", "HEAD"],
                              capture_output=True, text=True).stdout.strip()
        check("self-healed worktree is on the branch tip", head, "RUS-1/design")


_run_restack_provision_tests()

print("\n%d passed, %d failed" % (total - failures, failures))
sys.exit(1 if failures else 0)
