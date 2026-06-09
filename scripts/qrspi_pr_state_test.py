#!/usr/bin/env python3
"""Unit tests for qrspi_pr_state pure parsers (GraphQL reviewThreads / reviewDecision,
branch parsing). Stdlib-only, assert-based. Run: python3 scripts/qrspi_pr_state_test.py
"""

import sys

import qrspi_pr_state
from qrspi_pr_state import (
    unresolved_thread_count,
    parse_pr_nodes,
    select_pr,
    slice_numbers,
    branch_set,
    real_branches,
    count_plan_slices,
    stack_merge_state,
    is_stack_fully_merged,
    build_state,
    unaddressed_reviewer_comments,
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


def _raises(fn, exc):
    """True iff calling fn() raises an instance of exc."""
    try:
        fn()
    except exc:
        return True
    except Exception:
        return False
    return False


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
       "merged": False, "state": None, "mergedAt": None, "commentTargets": []})

check("approved, all threads resolved",
      parse_pr_nodes([{"number": 52, "reviewDecision": "APPROVED", "state": "OPEN",
                       "reviewThreads": {"nodes": [{"isResolved": True}]}}]),
      {"prExists": True, "number": 52, "reviewDecision": "APPROVED", "unresolvedThreads": 0,
       "merged": False, "state": "OPEN", "mergedAt": None, "commentTargets": []})

check("changes requested with unresolved threads",
      parse_pr_nodes([{"number": 7, "reviewDecision": "CHANGES_REQUESTED", "state": "OPEN",
                       "reviewThreads": {"nodes": [{"isResolved": False},
                                                   {"isResolved": True}]}}]),
      {"prExists": True, "number": 7, "reviewDecision": "CHANGES_REQUESTED", "unresolvedThreads": 1,
       "merged": False, "state": "OPEN", "mergedAt": None, "commentTargets": []})

check("null reviewDecision normalized to None",
      parse_pr_nodes([{"number": 9, "reviewDecision": None, "state": "OPEN",
                       "reviewThreads": {"nodes": []}}]),
      {"prExists": True, "number": 9, "reviewDecision": None, "unresolvedThreads": 0,
       "merged": False, "state": "OPEN", "mergedAt": None, "commentTargets": []})

# --- parse_pr_nodes: additive merge fields (Decision 1, Q2, Q7) -------------
check("merged PR surfaces merged/state/mergedAt",
      parse_pr_nodes([{"number": 60, "reviewDecision": "APPROVED", "state": "MERGED",
                       "merged": True, "mergedAt": "2026-06-08T00:00:00Z",
                       "reviewThreads": {"nodes": []}}]),
      {"prExists": True, "number": 60, "reviewDecision": "APPROVED", "unresolvedThreads": 0,
       "merged": True, "state": "MERGED", "mergedAt": "2026-06-08T00:00:00Z",
       "commentTargets": []})

# --- select_pr (named selection primitive: advancement vs merge/land) -------
_multi = [{"number": 100, "merged": False, "reviewDecision": "APPROVED",
           "reviewThreads": {"nodes": []}},
          {"number": 99, "merged": False, "reviewDecision": "CHANGES_REQUESTED",
           "reviewThreads": {"nodes": [{"isResolved": False}]}}]

check("select_pr empty active -> None", select_pr([], "active"), None)
check("select_pr empty merged -> None", select_pr([], "merged"), None)

# prefer='active' is identity nodes[0] (newest by CREATED_AT DESC).
check("select_pr active picks nodes[0]", select_pr(_multi, "active")["number"], 100)

# Advancement path (parse_pr_nodes) still uses the active selection: newest node.
check("parse_pr_nodes picks active (newest) node when multiple returned",
      parse_pr_nodes(_multi)["number"], 100)

# prefer='merged' wins on ANY MERGED node, order-independent.
_merged_then_closed = [{"number": 200, "merged": True, "state": "MERGED",
                        "reviewThreads": {"nodes": []}},
                       {"number": 201, "merged": False, "state": "CLOSED",
                        "reviewThreads": {"nodes": []}}]
_closed_then_merged = [{"number": 211, "merged": False, "state": "CLOSED",
                        "reviewThreads": {"nodes": []}},
                       {"number": 210, "merged": True, "state": "MERGED",
                        "reviewThreads": {"nodes": []}}]
check("select_pr merged wins (merged is nodes[0])",
      select_pr(_merged_then_closed, "merged")["number"], 200)
check("select_pr merged wins (merged is nodes[1], order-independent)",
      select_pr(_closed_then_merged, "merged")["number"], 210)

# No MERGED node -> prefer='merged' falls back to the active (nodes[0]) selection.
check("select_pr merged falls back to active when no node merged",
      select_pr(_multi, "merged")["number"], 100)

# Single-PR identity: select_pr returns the SAME object (AC3, AC4, Q10, OQ3).
_single = {"number": 52, "merged": False, "reviewDecision": "APPROVED", "state": "OPEN",
           "reviewThreads": {"nodes": [{"isResolved": True}]}}
check("select_pr active single-PR identity (same object)",
      select_pr([_single], "active") is _single, True)
check("parse_pr_nodes single-PR shape unchanged (commentTargets [] without bot_login)",
      parse_pr_nodes([_single]),
      {"prExists": True, "number": 52, "reviewDecision": "APPROVED", "unresolvedThreads": 0,
       "merged": False, "state": "OPEN", "mergedAt": None, "commentTargets": []})

check("select_pr unknown prefer raises ValueError",
      _raises(lambda: select_pr(_multi, "bogus"), ValueError), True)

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
      {"RUS-1/slice-1": {"merged": True, "prNumber": 10, "state": "MERGED",
                         "mergedByPr": 10},
       "RUS-1/slice-2": {"merged": True, "prNumber": 11, "state": "MERGED",
                         "mergedByPr": 11}})
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
      {"merged": False, "prNumber": None, "state": None, "mergedByPr": None})
check("deleted head ref makes stack not fully merged",
      is_stack_fully_merged(_deleted), False)

# Edge: empty stack -> predicate False (nothing merged is not 'fully merged').
check("empty stack: predicate False",
      is_stack_fully_merged({}), False)


# --- merge-aware selection: a branch with MULTIPLE PRs on one head ref -------
# (RUS-53 root fix: a NEWER non-merged PR must NOT mask an earlier MERGED one.)
def _nodes(*specs):
    """Build a pullRequests.nodes list. Each spec is (number, state, merged)."""
    return [{"number": n, "state": s, "merged": m,
             "reviewDecision": "APPROVED", "reviewThreads": {"nodes": []}}
            for (n, s, m) in specs]


# Step 6 — merged + newer-closed (RUS-30 shape): nodes CREATED_AT DESC put the
# newer non-merged PR at index 0, the earlier MERGED PR after it. Expect merged.
_merged_newer_closed = stack_merge_state(
    ["RUS-1/slice-1"],
    {"RUS-1/slice-1": _nodes((301, "CLOSED", False), (300, "MERGED", True))})
check("merged + newer-closed: branch reads merged True (RUS-30 reaped)",
      _merged_newer_closed["RUS-1/slice-1"],
      {"merged": True, "prNumber": 300, "state": "MERGED", "mergedByPr": 300})
check("merged + newer-closed: single-branch stack is fully merged -> destroy",
      is_stack_fully_merged(_merged_newer_closed), True)

# Step 7 — inverse order: closed first, newer MERGED second. Still merged
# (selection is order-independent).
_closed_newer_merged = stack_merge_state(
    ["RUS-1/slice-1"],
    {"RUS-1/slice-1": _nodes((310, "MERGED", True), (311, "CLOSED", False))})
check("closed + newer-merged: branch reads merged True (order-independent)",
      _closed_newer_merged["RUS-1/slice-1"],
      {"merged": True, "prNumber": 310, "state": "MERGED", "mergedByPr": 310})

# Step 10 — deleted head ref WITH a MERGED fetched node still reads merged True.
# (The ref is gone but the GraphQL query by headRefName still returns the node.)
_deleted_ref_with_merged = stack_merge_state(
    ["RUS-1/slice-1"],
    {"RUS-1/slice-1": _nodes((320, "MERGED", True))})
check("deleted head ref with MERGED fetched node reads merged True (AC5)",
      _deleted_ref_with_merged["RUS-1/slice-1"],
      {"merged": True, "prNumber": 320, "state": "MERGED", "mergedByPr": 320})

# Step 11 — no MERGED node (all-open / all-closed): falls back to active (nodes[0])
# and reads merged False, so non-landed branches behave exactly as today.
_all_open = stack_merge_state(
    ["RUS-1/slice-1"],
    {"RUS-1/slice-1": _nodes((330, "OPEN", False), (329, "OPEN", False))})
check("all-open (no MERGED node): merged False, active fallback to nodes[0]",
      _all_open["RUS-1/slice-1"],
      {"merged": False, "prNumber": 330, "state": "OPEN", "mergedByPr": None})
_all_closed = stack_merge_state(
    ["RUS-1/slice-1"],
    {"RUS-1/slice-1": _nodes((340, "CLOSED", False), (339, "CLOSED", False))})
check("all-closed (no MERGED node): merged False, active fallback to nodes[0]",
      _all_closed["RUS-1/slice-1"],
      {"merged": False, "prNumber": 340, "state": "CLOSED", "mergedByPr": None})


# --- build_state: additive blocker keys (RUS-50) ----------------------------
# build_state shells out to git/gh; stub the subprocess-backed helpers so the test
# is hermetic and exercises only the new blocked_open/blocked_by plumbing. A
# branch-less ticket means no PR queries fire, so only _git_branches is needed.
def _build_state_blocker_case():
    saved = (qrspi_pr_state._git_branches,
             qrspi_pr_state._git_show,
             qrspi_pr_state._file_in_tree)
    qrspi_pr_state._git_branches = lambda ticket: []
    qrspi_pr_state._git_show = lambda ref_path: ""
    qrspi_pr_state._file_in_tree = lambda ref, path: False
    try:
        blocked = build_state("o", "r", "RUS-1", True, "Selected",
                              blocked_open=True, blocked_by=["RUS-99"])
        default = build_state("o", "r", "RUS-1", True, "Selected")
    finally:
        (qrspi_pr_state._git_branches,
         qrspi_pr_state._git_show,
         qrspi_pr_state._file_in_tree) = saved
    return blocked, default


_blocked, _default = _build_state_blocker_case()
check("build_state(blocked_open=True) -> blockedOpen True",
      _blocked["blockedOpen"], True)
check("build_state(blocked_by=['RUS-99']) -> blockedBy ['RUS-99']",
      _blocked["blockedBy"], ["RUS-99"])
# Defaults keep existing callers green: blocker keys default falsy/empty.
check("build_state default -> blockedOpen False",
      _default["blockedOpen"], False)
check("build_state default -> blockedBy []",
      _default["blockedBy"], [])


# --- unaddressed_reviewer_comments (RUS-54: comment gather, AC5/AC6) --------
BOT = "qrspi-bot"


def _inline_thread(thread_id, *comments):
    """A reviewThreads node. Each comment is (databaseId, login, createdAt[, body])."""
    nodes = []
    for c in comments:
        cid, login, created = c[0], c[1], c[2]
        body = c[3] if len(c) > 3 else "b%s" % cid
        nodes.append({"databaseId": cid, "body": body, "createdAt": created,
                      "author": {"login": login}})
    return {"id": thread_id, "isResolved": False, "comments": {"nodes": nodes}}


def _pr(threads=None, top=None):
    return {"reviewThreads": {"nodes": threads or []},
            "comments": {"nodes": top or []}}


def _top(cid, login, created, body=None):
    return {"databaseId": cid, "body": body or "t%s" % cid, "createdAt": created,
            "author": {"login": login}}


# T9 — inline reviewer comment, no bot reply -> one CommentTarget; ids from
# .databaseId (NOT a nested user.id), author from author.login, threadType inline.
_t9 = unaddressed_reviewer_comments(
    _pr(threads=[_inline_thread("THRD1",
                                (501, "reviewer-r", "2026-06-09T01:00:00Z", "please fix"))]),
    BOT)
check("inline reviewer comment, no bot reply -> one target", len(_t9), 1)
check("inline target commentId from .databaseId (not user.id)", _t9[0]["commentId"], 501)
check("inline target author from author.login", _t9[0]["author"], "reviewer-r")
check("inline target threadType inline", _t9[0]["threadType"], "inline")
check("inline target threadId is the thread id", _t9[0]["threadId"], "THRD1")
check("inline target body surfaced", _t9[0]["body"], "please fix")

# T10 — bot reply LATER in the same inline thread -> not returned (idempotency/AC5).
_t10 = unaddressed_reviewer_comments(
    _pr(threads=[_inline_thread("THRD2",
                                (510, "reviewer-r", "2026-06-09T01:00:00Z"),
                                (511, BOT, "2026-06-09T02:00:00Z"))]),
    BOT)
check("inline reviewer comment with later bot reply -> not unaddressed", _t10, [])

# T10b — bot reply EARLIER, reviewer follows up after -> still unaddressed (later wins).
_t10b = unaddressed_reviewer_comments(
    _pr(threads=[_inline_thread("THRD3",
                                (520, "reviewer-r", "2026-06-09T01:00:00Z"),
                                (521, BOT, "2026-06-09T02:00:00Z"),
                                (522, "reviewer-r", "2026-06-09T03:00:00Z"))]),
    BOT)
check("reviewer follow-up after bot reply -> unaddressed again", len(_t10b), 1)
check("reviewer follow-up target is the latest reviewer comment", _t10b[0]["commentId"], 522)
check("inline lastReplyAuthor is the thread's last comment author",
      _t10b[0]["lastReplyAuthor"], "reviewer-r")

# T11 — top-level reviewer comment with a LATER bot top-level -> not returned;
# without one -> returned with threadType toplevel.
_t11_addressed = unaddressed_reviewer_comments(
    _pr(top=[_top(530, "reviewer-r", "2026-06-09T01:00:00Z"),
             _top(531, BOT, "2026-06-09T02:00:00Z")]),
    BOT)
check("top-level reviewer comment with later bot comment -> addressed", _t11_addressed, [])

_t11_open = unaddressed_reviewer_comments(
    _pr(top=[_top(540, "reviewer-r", "2026-06-09T01:00:00Z")]),
    BOT)
check("top-level reviewer comment, no later bot comment -> one target", len(_t11_open), 1)
check("top-level target threadType toplevel", _t11_open[0]["threadType"], "toplevel")
check("top-level target threadId None", _t11_open[0]["threadId"], None)
check("top-level target commentId from .databaseId", _t11_open[0]["commentId"], 540)

# T11b — bot top-level is EARLIER than the reviewer comment -> still unaddressed
# (ordering by createdAt, not array order).
_t11_earlier_bot = unaddressed_reviewer_comments(
    _pr(top=[_top(550, BOT, "2026-06-09T01:00:00Z"),
             _top(551, "reviewer-r", "2026-06-09T02:00:00Z")]),
    BOT)
check("top-level reviewer comment newer than bot's -> unaddressed", len(_t11_earlier_bot), 1)
check("top-level newer-than-bot target id", _t11_earlier_bot[0]["commentId"], 551)

# T12 — a comment authored by bot_login is ALWAYS filtered out (author attribution),
# inline and top-level alike.
_t12 = unaddressed_reviewer_comments(
    _pr(threads=[_inline_thread("THRD9", (560, BOT, "2026-06-09T01:00:00Z"))],
        top=[_top(561, BOT, "2026-06-09T01:00:00Z")]),
    BOT)
check("only bot-authored comments -> empty (filtered out)", _t12, [])


def run():
    print("\n%d passed, %d failed" % (total - failures, failures))
    return 1 if failures else 0


if __name__ == "__main__":
    # checks run at import-time above; report and exit
    sys.exit(run())
