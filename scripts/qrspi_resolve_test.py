#!/usr/bin/env python3
"""Unit tests for qrspi_resolve pure helpers (name/owner split, artifact detection,
tip-branch picking, envelope assembly). Stdlib-only, assert-based.
Run: python3 scripts/qrspi_resolve_test.py

The subprocess-backed parts (gh/git/gt, build_state) are intentionally NOT tested
here — same convention as qrspi_pr_state_test.py — and are verified by a manual
end-to-end run against a real ticket.
"""

import os
import sys
import tempfile

from qrspi_resolve import (
    parse_name_with_owner,
    detect_existing,
    pick_tip,
    build_envelope,
    ARTIFACTS,
    REPO_ROOT,
)

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


def check_raises(name, fn):
    global failures, total
    total += 1
    try:
        fn()
    except Exception:
        print("ok: %s" % name)
        return
    print("FAIL: %s\n      expected an exception, none raised" % name)
    failures += 1


# --- parse_name_with_owner --------------------------------------------------
check("splits owner/repo", parse_name_with_owner("russelltsherman/qrspi"),
      ("russelltsherman", "qrspi"))
check("tolerates trailing newline", parse_name_with_owner("a/b\n"), ("a", "b"))
check_raises("rejects missing slash", lambda: parse_name_with_owner("noslash"))
check_raises("rejects empty owner", lambda: parse_name_with_owner("/repo"))
check_raises("rejects empty repo", lambda: parse_name_with_owner("owner/"))
check_raises("rejects too many slashes", lambda: parse_name_with_owner("a/b/c"))
check_raises("rejects None", lambda: parse_name_with_owner(None))

# --- detect_existing --------------------------------------------------------
check("missing dir -> all False", detect_existing("/no/such/dir/anywhere"),
      {name: False for name in ARTIFACTS})

with tempfile.TemporaryDirectory() as d:
    # non-empty design + plan; empty research (0 bytes) must read as absent
    with open(os.path.join(d, "design.md"), "w") as fh:
        fh.write("content")
    with open(os.path.join(d, "plan.md"), "w") as fh:
        fh.write("more")
    open(os.path.join(d, "research.md"), "w").close()  # empty
    got = detect_existing(d)
    check("non-empty design detected", got["design"], True)
    check("non-empty plan detected", got["plan"], True)
    check("empty research not counted", got["research"], False)
    check("absent questions -> False", got["questions"], False)
    check("all six keys present", sorted(got.keys()), sorted(ARTIFACTS))

# --- pick_tip ---------------------------------------------------------------
check("no branches -> None", pick_tip(set(), "RUS-1"), None)
check("design only", pick_tip({"RUS-1/design"}, "RUS-1"), "RUS-1/design")
check("plan beats design", pick_tip({"RUS-1/design", "RUS-1/plan"}, "RUS-1"),
      "RUS-1/plan")
check("highest slice wins",
      pick_tip({"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1", "RUS-1/slice-2"}, "RUS-1"),
      "RUS-1/slice-2")
check("slice beats plan even out of order",
      pick_tip({"RUS-1/plan", "RUS-1/slice-3", "RUS-1/slice-1"}, "RUS-1"),
      "RUS-1/slice-3")

# --- build_envelope ---------------------------------------------------------
_dec = {"action": "run_design", "reason": "x"}
_ex = {name: False for name in ARTIFACTS}
ok_env = build_envelope("/wt/RUS-1", _dec, _ex, ok=True)
check("ok envelope ok flag", ok_env["ok"], True)
check("ok envelope carries decision", ok_env["decision"], _dec)
check("ok envelope repoRoot is derived REPO_ROOT", ok_env["repoRoot"], REPO_ROOT)
check("ok envelope has no error key", "error" in ok_env, False)
check("ok envelope worktreeDir", ok_env["worktreeDir"], "/wt/RUS-1")

err_env = build_envelope("/wt/RUS-1", None, _ex, ok=False, error="boom")
check("err envelope ok flag", err_env["ok"], False)
check("err envelope error message", err_env["error"], "boom")


def run():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(run())
