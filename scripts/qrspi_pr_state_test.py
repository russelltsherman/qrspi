#!/usr/bin/env python3
"""Unit tests for qrspi_pr_state pure parsers (GraphQL reviewThreads / reviewDecision,
branch parsing). Stdlib-only, assert-based. Run: python3 scripts/qrspi_pr_state_test.py
"""

import sys

from qrspi_pr_state import (
    unresolved_thread_count,
    parse_pr_nodes,
    slice_numbers,
    branch_set,
    real_branches,
    count_plan_slices,
    stack_merge_state,
    is_stack_fully_merged,
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


# --- unresolved_thread_count -----------------------------------------------
check("no threads -> 0", unresolved_thread_count([]), 0)
check("all resolved -> 0",
      unresolved_thread_count([{"isResolved": True}, {"isResolved": True}]), 0)
check("mixed -> count unresolved",
      unresolved_thread_count([{"isResolved": True}, {"isResolved": False},
                               {"isResolved": False}]), 2)
check("missing isResolved treated as unresolved",
      unresolved_thread_count([{}, {"isResolved": True}]), 1)

# --- parse_pr_nodes ---------------------------------------------------------
check("no PR nodes -> prExists False",
      parse_pr_nodes([]),
      {"prExists": False, "number": None, "reviewDecision": None, "unresolvedThreads": 0,
       "merged": False, "state": None, "mergedAt": None})

check("approved, all threads resolved",
      parse_pr_nodes([{"number": 52, "reviewDecision": "APPROVED", "state": "OPEN",
                       "reviewThreads": {"nodes": [{"isResolved": True}]}}]),
      {"prExists": True, "number": 52, "reviewDecision": "APPROVED", "unresolvedThreads": 0,
       "merged": False, "state": "OPEN", "mergedAt": None})

check("changes requested with unresolved threads",
      parse_pr_nodes([{"number": 7, "reviewDecision": "CHANGES_REQUESTED", "state": "OPEN",
                       "reviewThreads": {"nodes": [{"isResolved": False},
                                                   {"isResolved": True}]}}]),
      {"prExists": True, "number": 7, "reviewDecision": "CHANGES_REQUESTED", "unresolvedThreads": 1,
       "merged": False, "state": "OPEN", "mergedAt": None})

check("null reviewDecision normalized to None",
      parse_pr_nodes([{"number": 9, "reviewDecision": None, "state": "OPEN",
                       "reviewThreads": {"nodes": []}}]),
      {"prExists": True, "number": 9, "reviewDecision": None, "unresolvedThreads": 0,
       "merged": False, "state": "OPEN", "mergedAt": None})

# --- parse_pr_nodes: additive merge fields (Decision 1, Q2, Q7) -------------
check("merged PR surfaces merged/state/mergedAt",
      parse_pr_nodes([{"number": 60, "reviewDecision": "APPROVED", "state": "MERGED",
                       "merged": True, "mergedAt": "2026-06-08T00:00:00Z",
                       "reviewThreads": {"nodes": []}}]),
      {"prExists": True, "number": 60, "reviewDecision": "APPROVED", "unresolvedThreads": 0,
       "merged": True, "state": "MERGED", "mergedAt": "2026-06-08T00:00:00Z"})

check("picks first node when multiple returned",
      parse_pr_nodes([{"number": 100, "reviewDecision": "APPROVED",
                       "reviewThreads": {"nodes": []}},
                      {"number": 99, "reviewDecision": "CHANGES_REQUESTED",
                       "reviewThreads": {"nodes": [{"isResolved": False}]}}])["number"],
      100)

# --- slice_numbers ----------------------------------------------------------
check("extracts and sorts slice numbers",
      slice_numbers(["  RUS-1/slice-2", "* RUS-1/slice-1", "  RUS-1/design",
                     "  RUS-1/plan", "  RUS-1/slice-10"]),
      [1, 2, 10])

check("no slice branches -> empty",
      slice_numbers(["  RUS-1/design", "  RUS-1/plan"]),
      [])

# --- branch_set -------------------------------------------------------------
check("normalizes branch lines (strips current marker)",
      branch_set(["* RUS-1/design", "  RUS-1/plan", ""]),
      {"RUS-1/design", "RUS-1/plan"})

check("strips '+' worktree marker (regression: ticket branches live in worktrees)",
      branch_set(["+ RUS-1/design", "* RUS-1/plan", "  RUS-1/slice-1"]),
      {"RUS-1/design", "RUS-1/plan", "RUS-1/slice-1"})

# --- real_branches (regression: empty placeholder branch must not read as a phase) --
check("empty placeholder branch (0 commits ahead of trunk) is not real",
      real_branches({"RUS-1/design"}, {"RUS-1/design": 0}),
      set())

check("branch ahead of trunk is real",
      real_branches({"RUS-1/design"}, {"RUS-1/design": 3}),
      {"RUS-1/design"})

check("mixed: real design, empty plan placeholder",
      real_branches({"RUS-1/design", "RUS-1/plan"},
                    {"RUS-1/design": 1, "RUS-1/plan": 0}),
      {"RUS-1/design"})

check("branch missing from ahead map is not real (defensive)",
      real_branches({"RUS-1/design"}, {}),
      set())


# --- count_plan_slices (mandatory-slice gate; optionality NOT honored) ------
check("counts two slice headings",
      count_plan_slices("# Plan\n## Slice 1: do x\n### Setup\n"
                        "## Slice 2: do y (optional, pending OQ4)\n### Verify Slice 2\n"),
      2)

check("optionality/gating annotations do NOT reduce the count",
      count_plan_slices("## Slice 1: a\n## Slice 2: b (optional)\n"
                        "## Slice 3: c (gated on OQ5)\n"),
      3)

check("no slice headings -> 0",
      count_plan_slices("# Plan\n## Overview\n## Rollback Notes\n"),
      0)

check("ignores '### Verify Slice N' subheadings (not top-level ## Slice)",
      count_plan_slices("## Slice 1: a\n### Verify Slice 1\n"),
      1)

check("dedupes a repeated slice number",
      count_plan_slices("## Slice 1: a\n## Slice 1: a (restated)\n"),
      1)

check("empty / None plan text -> 0",
      count_plan_slices(""),
      0)


# --- stack_merge_state / is_stack_fully_merged (Decision 1, AC2, OQ3) -------
def _node(number, state, merged):
    return [{"number": number, "state": state, "merged": merged,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}]


# Case 1: fully-merged stack -> every branch merged True + predicate True.
_fully_merged = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "MERGED", True)})
check("fully-merged: all branches merged",
      _fully_merged,
      {"RUS-1/slice-1": {"merged": True, "prNumber": 10, "state": "MERGED"},
       "RUS-1/slice-2": {"merged": True, "prNumber": 11, "state": "MERGED"}})
check("fully-merged: predicate True",
      is_stack_fully_merged(_fully_merged), True)

# Case 2: partially-merged -> predicate False.
_partial = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("partially-merged: predicate False",
      is_stack_fully_merged(_partial), False)

# Case 3: in-flight (all OPEN) -> predicate False.
_inflight = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "OPEN", False),
     "RUS-1/slice-2": _node(11, "OPEN", False)})
check("in-flight (all OPEN): predicate False",
      is_stack_fully_merged(_inflight), False)

# Case 4: GitHub already deleted the head ref -> sentinel, no crash.
_deleted = stack_merge_state(
    ["RUS-1/slice-1", "RUS-1/slice-2"],
    {"RUS-1/slice-1": _node(10, "MERGED", True)})  # slice-2 head ref absent
check("deleted head ref -> documented sentinel",
      _deleted["RUS-1/slice-2"],
      {"merged": False, "prNumber": None, "state": None})
check("deleted head ref makes stack not fully merged",
      is_stack_fully_merged(_deleted), False)

# Edge: empty stack -> predicate False (nothing merged is not 'fully merged').
check("empty stack: predicate False",
      is_stack_fully_merged({}), False)


def run():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    # checks run at import-time above; report and exit
    sys.exit(run())
