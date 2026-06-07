#!/usr/bin/env python3
"""Unit tests for qrspi_pr_body pure helpers (worktree path, slice branch name,
subject/trailer split, PR-body composition, gt-modify result classification, and
envelope assembly). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_pr_body_test.py

The subprocess-backed parts (gt checkout/modify, git log) are intentionally NOT tested
here — same convention as qrspi_restack_test.py / qrspi_resolve_test.py / qrspi_persist
— and are verified by a manual end-to-end run on a real slice stack.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_pr_body import (  # noqa: E402
    worktree_path,
    slice_branch,
    split_subject_trailers,
    compose_message,
    classify_modify,
    build_envelope,
    REPO_ROOT,
)

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

# --- slice_branch -----------------------------------------------------------
check("slice branch name", slice_branch("RUS-21", 1), "RUS-21/slice-1")
check("slice branch name n>1", slice_branch("RUS-9", 2), "RUS-9/slice-2")
check("slice branch coerces str slice", slice_branch("RUS-9", "3"), "RUS-9/slice-3")

# --- split_subject_trailers -------------------------------------------------
check("subject + single trailer split",
      split_subject_trailers("RUS-1 [I] 1/2: goal\n\nCo-Authored-By: X <a@b>"),
      ("RUS-1 [I] 1/2: goal", ["Co-Authored-By: X <a@b>"]))

check("subject only (no trailer)",
      split_subject_trailers("RUS-1 [I] 1/1: only"),
      ("RUS-1 [I] 1/1: only", []))

check("body between subject and trailer is dropped; trailer kept",
      split_subject_trailers(
          "RUS-1 [SP]: Plan\n\nsome old body line\n\nCo-Authored-By: X <a@b>"),
      ("RUS-1 [SP]: Plan", ["Co-Authored-By: X <a@b>"]))

check("multiple trailing trailers preserved in order",
      split_subject_trailers(
          "subj\n\nbody\n\nSigned-off-by: A <a@a>\nCo-Authored-By: B <b@b>"),
      ("subj", ["Signed-off-by: A <a@a>", "Co-Authored-By: B <b@b>"]))

check("empty message", split_subject_trailers(""), ("", []))

check("a trailing non-trailer line means no trailer block",
      split_subject_trailers("subj\n\njust a body, no trailer."),
      ("subj", []))

# --- compose_message --------------------------------------------------------
check("compose splices body between subject and trailer",
      compose_message("RUS-1 [I] 1/2: goal\n\nCo-Authored-By: X <a@b>",
                      "## Summary\n\nDid the thing."),
      "RUS-1 [I] 1/2: goal\n\n## Summary\n\nDid the thing.\n\nCo-Authored-By: X <a@b>\n")

check("compose with no existing trailer",
      compose_message("RUS-1 [I] 1/1: x", "Body only."),
      "RUS-1 [I] 1/1: x\n\nBody only.\n")

check("compose strips surrounding whitespace on body",
      compose_message("subj\n\nCo-Authored-By: X <a@b>", "\n\n  padded body  \n\n"),
      "subj\n\npadded body\n\nCo-Authored-By: X <a@b>\n")

check("compose replaces a prior body, keeps subject+trailer",
      compose_message("subj\n\nOLD BODY\n\nCo-Authored-By: X <a@b>", "NEW BODY"),
      "subj\n\nNEW BODY\n\nCo-Authored-By: X <a@b>\n")

# A realistic multi-paragraph pr-summary keeps its internal blank lines intact.
_summary = "## What\n\n- did A\n- did B\n\n## Why\n\nBecause reasons."
check("compose preserves internal blank lines of the body",
      compose_message("RUS-9 [I] 1/2: thing\n\nCo-Authored-By: X <a@b>", _summary),
      "RUS-9 [I] 1/2: thing\n\n" + _summary + "\n\nCo-Authored-By: X <a@b>\n")

# --- classify_modify --------------------------------------------------------
check("rc=0 -> ok, no error", classify_modify(0, "amended", ""), (True, None))
check("rc!=0 -> not ok, stderr error",
      classify_modify(1, "", "fatal: nothing to amend"),
      (False, "fatal: nothing to amend"))
check("rc!=0 falls back to stdout then generic",
      classify_modify(2, "", ""), (False, "gt modify failed (rc=2)"))

# --- build_envelope ---------------------------------------------------------
check("envelope ok shape",
      build_envelope("RUS-1", 1, "RUS-1/slice-1", "/repo/.worktrees/RUS-1",
                     ok=True, subject="RUS-1 [I] 1/1: x", bytes_=42),
      {"ok": True, "repoRoot": REPO_ROOT, "ticket": "RUS-1", "slice": 1,
       "branch": "RUS-1/slice-1", "worktreeDir": "/repo/.worktrees/RUS-1",
       "subject": "RUS-1 [I] 1/1: x", "bytes": 42})

check("envelope error shape includes error, coerces slice/bytes",
      build_envelope("RUS-1", "2", "RUS-1/slice-2", "/wt", ok=False,
                     error="boom"),
      {"ok": False, "repoRoot": REPO_ROOT, "ticket": "RUS-1", "slice": 2,
       "branch": "RUS-1/slice-2", "worktreeDir": "/wt", "subject": None,
       "bytes": 0, "error": "boom"})

check("envelope honors explicit repo_root (git-common-dir root from a worktree)",
      build_envelope("RUS-1", 1, "RUS-1/slice-1", "/main/.worktrees/RUS-1",
                     ok=True, subject="s", bytes_=1, repo_root="/main")["repoRoot"],
      "/main")


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
