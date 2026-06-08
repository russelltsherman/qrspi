# Implementation Plan — Wrong PR chosen when a branch has multiple PRs, stranding merged worktrees

**Structure basis:** structure.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft
**Total steps:** 14

## Slice 1: Merge-aware PR selection at the single chokepoint

**Goal:** A branch whose work has merged reports `merged: True` even when a newer
non-merged PR exists on the same head ref, so a fully-landed stack (RUS-30) is reaped
by both cleanup and reconcile — while the advancement path stays byte-for-byte
unchanged. Selector + fetch-cap + tests, all in one module and its test sibling.

**Depends on:** none

### Setup

1. ⚠️ Modify `scripts/qrspi_pr_state.py` — Raise the per-branch PR connection cap in the
   `PR_QUERY` GraphQL string (ref: structure.md Modified Types `PR_QUERY`; AC6).
   - **Current:** the per-branch `pullRequests(...)` connection uses `first:5`
   - **After:** the same connection uses `first:25`; no fields added (`state`/`merged`
     already per-node)

### Core Logic

2. ⚠️ Modify `scripts/qrspi_pr_state.py` — Add the named selection primitive
   `select_pr(nodes: list[dict], prefer: str) -> dict | None` (ref: structure.md Contracts
   `select_pr`; Design Decision 1 Option C, Decision 2 Option A).
   - **Current:** no such function; node selection is an inline `nodes[0]` inside
     `parse_pr_nodes`
   - **After:** new pure function. `prefer="active"` returns `nodes[0]` (identity), i.e.
     `None` when `nodes` is empty else `nodes[0]` — byte-for-byte the current selection.
     `prefer="merged"` returns the first node where `node.get("merged") is True` if any
     ("any MERGED node wins", order-independent), else falls back to the `prefer="active"`
     result. Any other `prefer` value raises `ValueError`.

3. ⚠️ Modify `scripts/qrspi_pr_state.py` — Re-express `parse_pr_nodes` over the new
   primitive (ref: structure.md Contracts `parse_pr_nodes`; AC3, Q10, OQ3).
   - **Current:** `parse_pr_nodes(nodes)` selects the PR inline via `nodes[0]` (newest-created)
   - **After:** `parse_pr_nodes(nodes)` selects via `select_pr(nodes, prefer="active")`;
     the returned normalized advancement shape (`prExists`, `number`, `reviewDecision`,
     `unresolvedThreads`, `merged`, `state`, `mergedAt`) is unchanged — a rename, not a
     behavior change

4. ⚠️ Modify `scripts/qrspi_pr_state.py` — Source the per-branch `merged` value in
   `stack_merge_state` from the merged-preferring scan (ref: structure.md Contracts
   `stack_merge_state`; AC1, AC2, AC5).
   - **Current:** per-branch `merged` is read from `nodes[0]["merged"]` (via the
     `parse_pr_nodes` collapse), so a newer non-merged PR masks an earlier MERGED one
   - **After:** per-branch `merged` is derived from `select_pr(nodes, prefer="merged")`
     (i.e. `True` if any fetched node is MERGED), which also folds in the deleted-head-ref
     case (a branch whose head ref is gone but has a MERGED fetched node reads
     `merged: True`). Downstream `is_stack_fully_merged` / `classify_cleanup` are unchanged.

5. ⚠️ Modify `scripts/qrspi_pr_state.py` — (Optional, observability only) record the PR
   number that drove the `merged: True` verdict on the cleanup/merge projection dict, e.g.
   `mergedByPr: int | None` (ref: structure.md New Types note; Design Delta §1; Q13).
   - **Current:** the projection dict carries no field naming the driving PR
   - **After:** purely additive key `mergedByPr` (the `number` of the selected merged node,
     else `None`); no consumer is made to depend on it. Skip this step if it would expand
     blast radius beyond the additive guarantee.

### Tests

6. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — Add fixture + assertion: merged + newer-closed
   branch (RUS-30 shape: nodes `[{closed, merged:False}, {merged:True}]` per CREATED_AT DESC),
   expect the merge projection `merged == True` (ref: structure.md Files touched; AC1, AC4, Q8).

7. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — Add fixture + assertion: closed + newer-merged
   branch (inverse: nodes `[{merged:True}, {closed, merged:False}]`), expect merge projection
   `merged == True` (ref: AC4, Q9).

8. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — Add fixture + assertion: single-PR identity
   case — `select_pr([node], prefer="active") is node` and `parse_pr_nodes([node])` produces
   the same normalized shape as before (ref: AC3, AC4, Q10, OQ3).

9. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — Revise/replace the existing
   `"picks first node when multiple returned"` assertion so it reflects merged-preferring
   selection rather than pinning the index-0 bug (ref: structure.md Files touched; AC4, Q12,
   Risk Register row 1).

10. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — Add fixture + assertion: deleted-head-ref
    branch with a MERGED fetched node reads `merged == True` (ref: structure.md Verification;
    AC5, Q11).

11. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — Add fixture + assertion: all-open / all-closed
    (no MERGED node) branch — `select_pr(nodes, prefer="merged")` falls back to the active
    selection and the projection reads `merged == False`, confirming non-landed branches behave
    exactly as today (ref: structure.md Unverified Assumption 3).

12. Run: `python3 scripts/qrspi_pr_state_test.py`
    - **Expected:** all tests pass, including the five new multi-PR fixtures and the revised
      `"picks first node"` assertion

13. Run: `python3 scripts/qrspi_resolve_state_test.py`
    - **Expected:** all 24 cases pass unchanged (byte-for-byte advancement baseline — confirms
      no regression from the `parse_pr_nodes` rename, AC3, Q10). This file is the regression
      oracle and is expected to stay untouched.

### Verify Slice 1

14. **Checkpoint:** `python3 scripts/qrspi_pr_state_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - [ ] `qrspi_pr_state_test.py` passes with the new multi-PR fixtures and revised assertion
    - [ ] `qrspi_resolve_state_test.py` passes unchanged (24-case baseline, AC3)
    - [ ] A constructed merged+newer-closed branch yields `is_stack_fully_merged == True` →
          `classify_cleanup` returns `destroy`, not `skip` (RUS-30 reaped — AC2).
          NOTE: confirm the literal `destroy`/`skip` return tokens against
          `scripts/qrspi_cleanup.py` before asserting (structure.md Unverified Assumption 1)
    - [ ] A constructed deleted-head-ref branch with a MERGED fetched node reads
          `merged: True` (AC5)

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations. All changes are confined to
  `scripts/qrspi_pr_state.py` and its `_test.py` sibling.
- Step 1 (`first:5` → `first:25`): revert by restoring `first:5` in `PR_QUERY`. Pure query
  page-size change; no schema or state impact.
- Steps 2–5 (selector + projection): revert by restoring the inline `nodes[0]` selection in
  `parse_pr_nodes` and the `nodes[0]["merged"]` read in `stack_merge_state`, and removing
  `select_pr` (and the optional `mergedByPr` key). The 24-case `qrspi_resolve_state_test.py`
  baseline (step 13) is the guard that the rename did not alter advancement behavior.
- No PR-write operations are introduced anywhere (Design constraint).
