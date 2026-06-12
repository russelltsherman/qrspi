# Work Tree — qrspi-batch restack aborts submit on a partially-landed stack (merged ancestors)

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T7 → T12 → T13 → T14 → T18 → T19 → T20

## Session 1

**Load:** structure.md §Contracts, structure.md §"New pure helpers", structure.md §"New impure shell boundary", structure.md §Slice 1, plan.md §Slice 1
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add merge-state imports (`stack_merge_state`, `is_stack_fully_merged`) at top of `qrspi_restack.py` | — | §1.1 | S | pending |
| T2 | Add pure helper `merged_ancestors(branches, merged_flags) -> set[str]` | T1 | §1.2 | S | pending |
| T3 | Add pure helper `submit_scope(branches, merged_flags, ticket)` (scope / lowestOpen / reparentParent) | T2 | §1.3 | M | pending |
| T4 | Add impure shell `read_merge_state(ticket, branches)` (gh GraphQL → `stack_merge_state`) | T1 | §1.4 | M | pending |
| T5 | Add impure shell `reparent_lowest_open(branch)` (`gt move --onto main` / `gt track --parent main`) | T1 | §1.5 | M | pending |
| T6 | Modify `restack()` — fully-landed short-circuit before any `gt` work | T3, T4 | §1.6 | S | pending |
| T7 | Modify `restack()` — partial-land re-parent + scoped submit path | T3, T4, T5, T6 | §1.7 | M | pending |
| T8 | Add `qrspi_restack_test.py` case: fully-open input (full scope, reparentParent unset) | T3 | §1.8 | S | pending |
| T9 | Add `qrspi_restack_test.py` case: partial-land input (merged lower slices, lowest-open re-parent flagged) | T3 | §1.9 | S | pending |
| T10 | Add `qrspi_restack_test.py` case: fully-landed input (empty/short-circuit scope) | T3 | §1.10 | S | pending |
| T11 | Run `python3 scripts/qrspi_restack_test.py` — all cases pass | T7, T8, T9, T10 | §1.11 | S | pending |
| T12 | **Verify Slice 1** — unit tests pass; manual e2e partial-land returns `ok:true`; dry-run lists only this ticket's open slices | T11 | §1.12 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (qrspi_restack.py) complete. Slice 2 touches a different module (qrspi_pr_state.py) and the resolver entry gate; fresh context avoids carrying Slice 1's gt/restack details into the resolver work.

## Session 2

**Load:** structure.md §Contracts, structure.md §Slice 2, plan.md §Slice 2, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Factor "0-ahead empty vs. 0-ahead merged" into pure helper (e.g. `branch_present(...)`) in `qrspi_pr_state.py` | T12 | §2.13 | M | pending |
| T14 | Modify `build_state()` — `real_branches`/`branchExists` use the distinction (landed-ancestor present; empty placeholder still rejected) | T13 | §2.14 | M | pending |
| T15 | Add `qrspi_pr_state_test.py` regression: populated landed-ancestor design branch (0 ahead, merged PR) → `branchExists: true` | T14 | §2.15 | S | pending |
| T16 | Add `qrspi_pr_state_test.py` coverage: empty-placeholder branch (0 ahead, no merged PR) still `branchExists: false` | T14 | §2.16 | S | pending |
| T17 | Run `python3 scripts/qrspi_pr_state_test.py` — all cases pass | T14, T15, T16 | §2.17 | S | pending |
| T18 | Run `python3 scripts/qrspi_resolve_state_test.py` — no entry-gate regression | T14 | §2.18 | S | pending |
| T19 | **Verify Slice 2** — pr_state tests (landed-ancestor + retained placeholder rejection) and resolve_state tests pass | T17, T18 | §2.19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Both slices are individually implemented and verified. The cross-slice checkpoints require both slices merged/sequenced together and a combined manual e2e; isolate them in a fresh context to assert the integrated behavior without per-slice implementation detail.

## Session 3

**Load:** plan.md §"Cross-slice Verify", plan.md §"Rollback Notes", impl-log.md §Slice 1 (notes only), impl-log.md §Slice 2 (notes only)
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T20 | **Cross-slice e2e** — reproduce partial-land; batch advances with no `restack_conflict` and no `entry_blocked "No design branch"` | T12, T19 | §3.20 | M | pending |
| T21 | **Envelope contract check** — confirm no `qrspi-batch.js` change needed (fully-landed `ok:true` dispatches to `land`); surface gap if it fails | T20 | §3.21 | S | pending |
| T22 | **Full suite** — `qrspi_restack_test.py && qrspi_pr_state_test.py && qrspi_resolve_state_test.py` all pass | T11, T17, T18 | §3.22 | S | pending |
