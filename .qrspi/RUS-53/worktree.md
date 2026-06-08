# Work Tree — Wrong PR chosen when a branch has multiple PRs, stranding merged worktrees

**Plan basis:** plan.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T9 → T11 → T12 → T13 → T14

## Session 1

**Load:** structure.md §Contracts (`select_pr`, `parse_pr_nodes`, `stack_merge_state`),
        structure.md §Modified Types (`PR_QUERY`), structure.md §New Types note,
        plan.md §Slice 1
**Estimated context:** ~18% of window (single module `scripts/qrspi_pr_state.py` + its
        `_test.py` sibling; no broader codebase load)

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Raise per-branch PR connection cap `first:5` → `first:25` in `PR_QUERY` (no fields added) | — | §1.1 | S | pending |
| T2 | Add pure primitive `select_pr(nodes, prefer)` — `active`=`nodes[0]` identity, `merged`=first MERGED node else active fallback, else `ValueError` | — | §1.2 | M | pending |
| T3 | Re-express `parse_pr_nodes` over `select_pr(nodes, prefer="active")` (rename, no behavior change) | T2 | §1.3 | S | pending |
| T4 | Source per-branch `merged` in `stack_merge_state` from `select_pr(nodes, prefer="merged")` (folds in deleted-head-ref case) | T2, T3 | §1.4 | M | pending |
| T5 | (Optional, additive) record `mergedByPr: int \| None` on the cleanup/merge projection dict; skip if it widens blast radius | T4 | §1.5 | S | pending |
| T6 | Test: merged + newer-closed branch (RUS-30 shape) → projection `merged == True` | T4 | §1.6 | S | pending |
| T7 | Test: closed + newer-merged branch (inverse) → projection `merged == True` | T4 | §1.7 | S | pending |
| T8 | Test: single-PR identity — `select_pr([node], prefer="active") is node` and `parse_pr_nodes([node])` shape unchanged | T2, T3 | §1.8 | S | pending |
| T9 | Test: revise/replace existing `"picks first node when multiple returned"` assertion to reflect merged-preferring selection | T4 | §1.9 | S | pending |
| T10 | Test: deleted-head-ref branch with a MERGED fetched node reads `merged == True` | T4 | §1.10 | S | pending |
| T11 | Test: all-open/all-closed (no MERGED node) falls back to active and reads `merged == False` | T4 | §1.11 | S | pending |
| T12 | Run `python3 scripts/qrspi_pr_state_test.py` — all pass incl. five new fixtures + revised assertion | T6, T7, T8, T9, T10, T11 | §1.12 | S | pending |
| T13 | Run `python3 scripts/qrspi_resolve_state_test.py` — 24-case advancement baseline passes unchanged (regression oracle) | T3, T4 | §1.13 | S | pending |
| T14 | **Verify Slice 1** — both test files pass; constructed merged+newer-closed branch → `is_stack_fully_merged == True` → `classify_cleanup` returns `destroy` (confirm tokens vs `qrspi_cleanup.py`); deleted-head-ref + MERGED node reads `merged: True` | T12, T13 | §1.14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Single-slice feature — no further sessions. Slice 1 complete and verified.
