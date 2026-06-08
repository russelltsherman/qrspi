#!/usr/bin/env python3
"""Unit tests for qrspi_cleanup.classify_cleanup (the pure destroy/skip/blocked
decision). Stdlib-only, assert/check() style, NO subprocess mocks — only the pure
classifier is exercised (ref: Q13, Q14). Run: python3 scripts/qrspi_cleanup_test.py
"""

import sys

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


def report():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(report())
