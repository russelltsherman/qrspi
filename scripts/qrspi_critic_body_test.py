#!/usr/bin/env python3
"""Unit tests for qrspi_critic_body pure helpers (worktree path, phase branch name,
subject/body/trailer split, residual-findings section render, commit-message composition,
gt-modify result classification, and envelope assembly). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_critic_body_test.py

The subprocess-backed parts (gt checkout/modify, git log) are intentionally NOT tested here
— same convention as qrspi_pr_body_test.py / qrspi_restack_test.py — and are verified by a
manual end-to-end run on a real design/plan stack.
"""

import os
import sys

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)

from qrspi_critic_body import (  # noqa: E402
    worktree_path,
    phase_branch,
    split_subject_trailers,
    render_findings_section,
    compose_message,
    classify_modify,
    build_envelope,
    REPO_ROOT,
    _PHASE_BRANCH,
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


def check_true(label, cond):
    check(label, bool(cond), True)


def check_raises(label, fn, exc):
    global failures, total
    total += 1
    try:
        fn()
    except exc:
        print("ok: %s" % label)
        return
    except Exception as e:  # noqa: BLE001
        failures += 1
        print("FAIL: %s raised %r, wanted %s" % (label, e, exc.__name__))
        return
    failures += 1
    print("FAIL: %s did not raise %s" % (label, exc.__name__))


# --- worktree_path / phase_branch ------------------------------------------

check("worktree_path", worktree_path("/repo", "RUS-9"), "/repo/.worktrees/RUS-9")
check("phase_branch design", phase_branch("RUS-9", "design"), "RUS-9/design")
check("phase_branch plan", phase_branch("RUS-9", "plan"), "RUS-9/plan")
check_raises("phase_branch rejects unsupported phase",
             lambda: phase_branch("RUS-9", "implementation"), ValueError)

# --- phase_branch: slice branch (RUS-58 Slice 2) ---------------------------
# Regression guard: design/plan ignore a passed slice_index and keep their fixed suffix.
check("phase_branch design ignores slice_index",
      phase_branch("RUS-9", "design", 3), "RUS-9/design")
check("phase_branch plan ignores slice_index",
      phase_branch("RUS-9", "plan", 3), "RUS-9/plan")
# slice resolves to <ticket>/slice-N for N=1 and N>1.
check("phase_branch slice N=1", phase_branch("RUS-9", "slice", 1), "RUS-9/slice-1")
check("phase_branch slice N>1", phase_branch("RUS-9", "slice", 7), "RUS-9/slice-7")
# String index is coerced (the CLI parses --slice as int, but the helper guards too).
check("phase_branch slice coerces str index",
      phase_branch("RUS-9", "slice", "2"), "RUS-9/slice-2")
# A missing or non-positive slice index for the slice phase is a ValueError.
check_raises("phase_branch slice requires index",
             lambda: phase_branch("RUS-9", "slice", None), ValueError)
check_raises("phase_branch slice rejects 0",
             lambda: phase_branch("RUS-9", "slice", 0), ValueError)
check_raises("phase_branch slice rejects non-int",
             lambda: phase_branch("RUS-9", "slice", "x"), ValueError)
# The `slice` phase is registered in the CLI choice set (sorted(_PHASE_BRANCH)).
check_true("slice is a registered phase choice", "slice" in _PHASE_BRANCH)

# --- split_subject_trailers (preserves existing body, unlike qrspi_pr_body) -

check("split: subject only",
      split_subject_trailers("RUS-1 [QR]: Design — Foo"),
      ("RUS-1 [QR]: Design — Foo", [], []))

check("split: subject + trailer",
      split_subject_trailers("Subj\n\nCo-Authored-By: X <y@z>"),
      ("Subj", [], ["Co-Authored-By: X <y@z>"]))

check("split: subject + body + trailer (body preserved)",
      split_subject_trailers("Subj\n\nbody line 1\nbody line 2\n\nCo-Authored-By: X <y@z>"),
      ("Subj", ["body line 1", "body line 2"], ["Co-Authored-By: X <y@z>"]))

check("split: empty message", split_subject_trailers(""), ("", [], []))
check("split: None message", split_subject_trailers(None), ("", [], []))

# --- render_findings_section -----------------------------------------------

check("render: empty list -> ''", render_findings_section([]), "")
check("render: non-list -> ''", render_findings_section(None), "")
check("render: blanks-only list -> ''", render_findings_section(["  ", ""]), "")

_sec = render_findings_section(["Dropped AC4 (no-op fast path)", "Distorted Q9 default"])
check_true("render: header present", _sec.startswith("## Residual critic findings"))
check_true("render: finding 1 as bullet", "- Dropped AC4 (no-op fast path)" in _sec)
check_true("render: finding 2 as bullet", "- Distorted Q9 default" in _sec)
check_true("render: drops blank entries",
           "- " not in render_findings_section(["only one", "  "]).split("only one", 1)[1])

# --- compose_message --------------------------------------------------------

# No findings -> message unchanged (idempotent no-op), subject + trailer preserved.
check("compose: no findings keeps subject+trailer",
      compose_message("Subj\n\nCo-Authored-By: X <y@z>", []),
      "Subj\n\nCo-Authored-By: X <y@z>\n")

# Findings spliced ABOVE the trailer, subject preserved.
_msg = compose_message("Subj\n\nCo-Authored-By: X <y@z>", ["Dropped AC4"])
_lines = _msg.splitlines()
check("compose: subject first", _lines[0], "Subj")
check_true("compose: section present", "## Residual critic findings" in _msg)
check_true("compose: finding bullet present", "- Dropped AC4" in _msg)
check_true("compose: trailer last", _lines[-1] == "Co-Authored-By: X <y@z>")
check_true("compose: section sits above trailer",
           _msg.index("## Residual critic findings") < _msg.index("Co-Authored-By"))
check_true("compose: newline-terminated", _msg.endswith("\n"))

# Existing body is preserved AND the findings section appended after it.
_msg2 = compose_message("Subj\n\nexisting body\n\nCo-Authored-By: X <y@z>", ["F1"])
check_true("compose: existing body preserved", "existing body" in _msg2)
check_true("compose: body precedes findings section",
           _msg2.index("existing body") < _msg2.index("## Residual critic findings"))

# --- classify_modify --------------------------------------------------------

check("classify: rc 0 -> ok", classify_modify(0, "", ""), (True, None))
check("classify: rc!=0 uses stderr", classify_modify(1, "", "boom"), (False, "boom"))
check("classify: rc!=0 falls back to stdout",
      classify_modify(1, "out msg", ""), (False, "out msg"))
check("classify: rc!=0 generic fallback",
      classify_modify(3, "", ""), (False, "gt modify failed (rc=3)"))

# --- build_envelope ---------------------------------------------------------

check("envelope ok shape",
      build_envelope("RUS-1", "design", "RUS-1/design", "/wt", ok=True, subject="s",
                     bytes_=10, repo_root="/main"),
      {"ok": True, "repoRoot": "/main", "ticket": "RUS-1", "phase": "design",
       "branch": "RUS-1/design", "worktreeDir": "/wt", "subject": "s", "bytes": 10})

check("envelope error shape carries error",
      build_envelope("RUS-1", "plan", "RUS-1/plan", "/wt", ok=False, error="boom",
                     repo_root="/main"),
      {"ok": False, "repoRoot": "/main", "ticket": "RUS-1", "phase": "plan",
       "branch": "RUS-1/plan", "worktreeDir": "/wt", "subject": None, "bytes": 0,
       "error": "boom"})

check("envelope repoRoot default IS the module REPO_ROOT",
      build_envelope("RUS-1", "design", "RUS-1/design", "/wt", ok=True)["repoRoot"],
      REPO_ROOT)


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
