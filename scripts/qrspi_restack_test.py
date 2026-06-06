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

from qrspi_restack import (
    worktree_path,
    classify_result,
    classify_submit,
    build_envelope,
    REPO_ROOT,
)
from qrspi_resolve import pick_tip

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

print("\n%d passed, %d failed" % (total - failures, failures))
sys.exit(1 if failures else 0)
