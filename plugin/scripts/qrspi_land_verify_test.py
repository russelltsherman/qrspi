#!/usr/bin/env python3
"""Unit tests for qrspi_land_verify.verify_landed (the pure land verdict).

Stdlib-only, assert-based, run: python3 scripts/qrspi_land_verify_test.py

Reuses the N=2 stack shape and the `_node` GraphQL stub from the qrspi_pr_state
tests, building real StackMergeState dicts through stack_merge_state() so the
verdict is exercised against the same fixtures the merge-state predicate is.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qrspi_pr_state import stack_merge_state  # noqa: E402
from qrspi_land_verify import verify_landed  # noqa: E402

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
    """A single-node pullRequests.nodes list, matching qrspi_pr_state_test._node."""
    return [{"number": number, "state": state, "merged": merged,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}]


_BRANCHES = ["RUS-1/slice-1", "RUS-1/slice-2"]


# --- Case 1: fully-merged stack -> landed, empty openBranches ----------------
_fully_merged = stack_merge_state(
    _BRANCHES,
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "MERGED", True)})
check("fully-merged: verdict landed",
      verify_landed(_fully_merged),
      {"status": "landed", "openBranches": []})


# --- Case 2: partial (slice-2 OPEN) -> incomplete naming the OPEN tip --------
_partial = stack_merge_state(
    _BRANCHES,
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("partial (slice-2 OPEN): verdict incomplete naming slice-2",
      verify_landed(_partial),
      {"status": "incomplete", "openBranches": ["RUS-1/slice-2"]})


# --- Case 3: all-OPEN -> incomplete naming both branches --------------------
_all_open = stack_merge_state(
    _BRANCHES,
    {"RUS-1/slice-1": _node(10, "OPEN", False),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("all-OPEN: verdict incomplete naming both branches",
      verify_landed(_all_open),
      {"status": "incomplete", "openBranches": ["RUS-1/slice-1", "RUS-1/slice-2"]})


# --- Edge: empty stack -> incomplete (nothing merged is not landed) ----------
check("empty stack: verdict incomplete with no branches",
      verify_landed({}),
      {"status": "incomplete", "openBranches": []})


print("\n%d/%d checks passed" % (total - failures, total))
sys.exit(1 if failures else 0)
