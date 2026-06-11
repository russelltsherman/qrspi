# Implementation Plan — qrspi-batch restack aborts submit on a partially-landed stack (merged ancestors)

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 22

## Slice 1: Merged-ancestor-aware restack/submit in `qrspi_restack.py`

### Setup

1. ⚠️ Modify `scripts/qrspi_restack.py` — add the merge-state imports at module top so the existing tested classifiers become consumers here.
   - **Current:** imports only `branch_set` and `pick_tip` from `qrspi_pr_state` (ref: design.md Current State, Q2).
   - **After:** also import `stack_merge_state` and `is_stack_fully_merged` from `qrspi_pr_state` (ref: structure.md Contracts; Decision 2A).

### Core Logic

2. ✨ Add pure helper `merged_ancestors(branches, merged_flags) -> set[str]` to `scripts/qrspi_restack.py` — given the ticket's branch set and a per-branch merged boolean map, return the subset that are merged ancestors (merged AND below the lowest open slice). Stdlib-only, tuple-in/tuple-out, matching the existing classifier style (ref: structure.md "New pure helpers"; design.md Delta).

3. ✨ Add pure helper `submit_scope(branches, merged_flags, ticket) -> {scope: list[str], lowestOpen: branch|None, reparentParent: branch}` to `scripts/qrspi_restack.py` — pure computation of (a) the lowest still-open slice, (b) whether its tracked parent is a merged ancestor (→ re-parent onto trunk), and (c) the open-branch set to submit; returns an empty/sentinel scope when the stack is fully merged. Derives tracked parent from `<ticket>/slice-N` ordering + merged flags (ref: structure.md Unverified Assumption "Tracked parent" read; design.md Decision 1A).
   - Note: if implementation reveals a real `gt`-metadata tracked-parent read is required (not derivable from ordering), add a thin impure shell wrapper and keep `submit_scope` pure over its result (ref: structure.md Unverified Assumptions).

4. ✨ Add impure shell function `read_merge_state(ticket, branches) -> merge_state` to `scripts/qrspi_restack.py` — thin wrapper around a `gh` GraphQL read feeding `stack_merge_state(branches, graphql_nodes)` (Decision 2A). Intentionally untested per the pure-core/impure-shell split (ref: structure.md "New impure shell boundary"; Q11). Reuse the gather shape from `qrspi_pr_state.py` where practical (ref: structure.md Unverified Assumption "gh GraphQL read shape").

5. ✨ Add impure shell function `reparent_lowest_open(branch) -> (rc, out, err)` to `scripts/qrspi_restack.py` — wraps the single `gt move --onto main` / `gt track --parent main` call confined to this ticket's lowest open slice (Decision 1, Option A). Confirm the exact `gt` invocation/flags against the installed `gt` version during implementation (ref: structure.md Unverified Assumption "Targeted re-parent command"; RUS-40 procedure).

6. ⚠️ Modify `restack()` in `scripts/qrspi_restack.py` — add the fully-landed short-circuit before any `gt` work.
   - **Current:** `restack()` immediately runs `gt checkout <tip>` → `gt restack --downstack` → conditional `gt submit --stack`, with no merge awareness (ref: design.md Current State).
   - **After:** call `read_merge_state(ticket, branches)`, then `is_stack_fully_merged(merge_state)`; when true, return `ok:true, restacked:false, submitted:false` immediately — no `gt checkout`/`restack`/`submit` runs (ref: structure.md Slice 1 (1); design.md OQ3 / AC fully-landed short-circuit).

7. ⚠️ Modify `restack()` in `scripts/qrspi_restack.py` — add the partial-land re-parent + scoped submit path.
   - **Current:** computes tip via `pick_tip(existing_branches(...))` and submits `--stack` from the tip with no merged-ancestor handling, so `gt` aborts when it walks into merged downstack branches (ref: design.md Current State, Q9/Q10).
   - **After:** when not fully landed, compute `submit_scope(branches, merged_flags, ticket)`; if `reparentParent` indicates the lowest open slice's tracked parent is a merged ancestor, call `reparent_lowest_open(lowestOpen)` then run the existing `--stack` submit scoped to the open branches; preserve the no-op→skip-push path (`restacked == False` skips submit) (ref: structure.md Slice 1 (2); design.md Delta, Decision 1A).

### Tests

8. ⚠️ Modify `scripts/qrspi_restack_test.py` — add a stdlib-only case for fully-open input: no merged ancestors → `submit_scope` returns the full-stack scope and `reparentParent` unset (ref: structure.md Slice 1 verification; design.md Delta test cases).

9. ⚠️ Modify `scripts/qrspi_restack_test.py` — add a stdlib-only case for partial-land input: lower slices merged → `merged_ancestors` returns the merged lower slices and `submit_scope.scope` = open slices only with the lowest-open re-parent flagged (ref: structure.md Slice 1 verification).

10. ⚠️ Modify `scripts/qrspi_restack_test.py` — add a stdlib-only case for fully-landed input: all slices merged → `submit_scope` returns an empty/short-circuit scope (ref: structure.md Slice 1 verification; design.md OQ3).

11. Run: `python3 scripts/qrspi_restack_test.py`
    - **Expected:** all tests pass, including the three new helper cases (fully-open, partial-land, fully-landed).

### Verify Slice 1

12. **Checkpoint:** `python3 scripts/qrspi_restack_test.py`
    - [ ] `python3 scripts/qrspi_restack_test.py` passes, including the three new helper cases.
    - [ ] Manual e2e: reproduce the partial-land condition (lower slices merged, top slice open) and run the batch; confirm `restack()` returns `ok:true` and the ticket dispatches `advance`/`land` instead of `restack_conflict` (ref: design.md AC "manual e2e", RUS-40 procedure).
    - [ ] Dry-run check during e2e: `gt submit --stack --dry-run` lists only this ticket's open `<ticket>/slice-*` branches — no merged ancestors, no other tickets' branches (Risk Register blast-radius mitigation).

---

## Slice 2: Resolver entry-gate fix for populated landed-ancestor branches in `qrspi_pr_state.py`

### Core Logic

13. ⚠️ Modify `scripts/qrspi_pr_state.py` — factor the "0 ahead because empty vs. 0 ahead because merged" distinction into a pure helper (e.g. `branch_present(branch, ahead, merged_pr, exists_locally) -> bool`) if it clarifies the gate.
    - **Current:** `branchExists = head in real`; `real_branches` keeps a branch only when `git rev-list --count main..<branch> > 0`, so a landed-ancestor branch (0 ahead) is dropped (ref: design.md Current State, Q7).
    - **After:** a 0-ahead branch is treated as present when it has a positive merged-PR signal (or still exists locally), distinguishing landed work from an empty placeholder (ref: structure.md Slice 2; design.md Decision 3A, OQ2).

14. ⚠️ Modify `build_state()` in `scripts/qrspi_pr_state.py` — adjust the `real_branches` / `branchExists` derivation to use the distinction from step 13.
    - **Current:** `branchExists = head in real`, where `real` excludes any 0-ahead branch (ref: design.md Current State).
    - **After:** a populated branch whose commits landed in trunk (0 ahead, merged PR) reports `branchExists: true`; an empty-placeholder branch (0 ahead, no merged-PR signal) is still rejected (ref: structure.md Slice 2; design.md Decision 3A; Risk "re-admits the empty-placeholder design branch").

### Tests

15. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a regression case: a *populated landed-ancestor* design branch (0 ahead, merged PR) asserts `branchExists: true` (ref: structure.md Slice 2 verification; design.md Q12 gap).

16. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — retain/add coverage that an empty-placeholder branch (0 ahead, no merged PR) is still rejected (`branchExists: false`) (ref: structure.md Slice 2 verification; Risk Register).

17. Run: `python3 scripts/qrspi_pr_state_test.py`
    - **Expected:** all tests pass, including the populated-landed-ancestor case and the retained empty-placeholder rejection.

18. Run: `python3 scripts/qrspi_resolve_state_test.py`
    - **Expected:** still passes; the resolver consumes `branchExists` and the entry-gate path shows no regression.

### Verify Slice 2

19. **Checkpoint:** `python3 scripts/qrspi_pr_state_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - [ ] `python3 scripts/qrspi_pr_state_test.py` passes, including the populated-landed-ancestor case asserting `branchExists: true` and the retained empty-placeholder rejection.
    - [ ] `python3 scripts/qrspi_resolve_state_test.py` still passes (no regression in the entry-gate path).

---

## Cross-slice Verify

20. **Checkpoint (shared manual e2e — sequence both slices first):** reproduce the partial-land condition and run the full batch advance.
    - [ ] With Slice 1 and Slice 2 both merged, the batch advances cleanly: no `restack_conflict` and no `entry_blocked "No design branch"` (ref: structure.md Unverified Assumption "Shared manual e2e covers both slices"; design.md AC + OQ4).

21. **Checkpoint (envelope contract preserved):** confirm no `qrspi-batch.js` change is needed.
    - [ ] The fully-landed short-circuit's `ok:true` envelope is dispatched to `land` by the existing batch logic with no new branch (ref: structure.md Unverified Assumption "No qrspi-batch.js change"; design.md Delta "No changes to qrspi-batch.js control flow"). If verification fails, surface the gap rather than editing batch control flow without scope.

22. **Checkpoint (full suite):** `python3 scripts/qrspi_restack_test.py && python3 scripts/qrspi_pr_state_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - [ ] All three stdlib-only test files pass.

---

## Rollback Notes

- **Step 5 / Step 7 (`gt move --onto main` / `gt track --parent main` re-parent):** this mutates `gt` stack metadata for the lowest open slice. Before the real submit, verify with `gt submit --stack --dry-run` that only this ticket's open `<ticket>/slice-*` branches are listed (blast-radius mitigation, Risk Register). To reverse a wrong re-parent, restore the original tracked parent with `gt track --parent <original-parent>` for the affected slice; no other tickets' branches should have been touched. Confirm the exact `gt` reverse invocation against the installed `gt` version.
- **Step 6 (fully-landed short-circuit):** pure control-flow addition; revert by removing the `is_stack_fully_merged` early-return block. No persistent state changed.
- **Steps 13–14 (resolver gate change):** pure-logic change to `branchExists` derivation; revert by restoring `branchExists = head in real`. No persistent state changed. If the change re-admits empty-placeholder branches, the empty-placeholder regression test (step 16) catches it before merge.
