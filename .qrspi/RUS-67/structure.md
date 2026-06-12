# Structure Outline — qrspi-batch restack aborts submit on a partially-landed stack (merged ancestors)

**Design basis:** design.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

None. All new surface is pure functions returning tuples/dicts in the existing classifier style; no new record/struct types are introduced.

## Modified Types

- JSON envelope emitted by `qrspi_restack.py` — **no structural change.** Contract is preserved: `{ ok, repoRoot, ticket, worktreeDir, tip, restacked, submitted, error? }`. The fully-landed short-circuit reuses existing fields (`ok:true, restacked:false, submitted:false`) (ref: design.md §Delta, "No changes to qrspi-batch.js control flow").

## Contracts

Cross-slice / cross-module interfaces consumed by the new code (all pre-existing, tested, gaining their first production consumer in the affected paths):

- `qrspi_pr_state.stack_merge_state(branches, graphql_nodes) -> {branch: {merged, prNumber, state, mergedByPr}}` — authoritative per-branch PR-merged map; the merged-ancestor source of truth (Decision 2A). Consumed by Slice 1.
- `qrspi_pr_state.is_stack_fully_merged(merge_state) -> bool` — all-or-nothing predicate; drives the fully-landed short-circuit (OQ3). Consumed by Slice 1.
- `qrspi_restack.branch_set(...)` / `qrspi_restack.pick_tip(branches) -> branch` — existing imports, unchanged.

New pure helpers introduced in Slice 1 (intra-`qrspi_restack.py`, stdlib-only, tuple-in/tuple-out):

- `merged_ancestors(branches, merged_flags) -> set[str]` — given the ticket's branch set and a per-branch merged boolean map, return the subset that are merged ancestors (merged AND below the lowest open slice).
- `submit_scope(branches, merged_flags, ticket) -> {scope: list[str], lowestOpen: branch|None, reparentParent: branch}` — pure computation of (a) the lowest still-open slice, (b) whether its tracked parent is a merged ancestor (→ re-parent onto trunk), and (c) the open-branch set to submit. Returns an empty/sentinel scope when the stack is fully merged.

New impure shell boundary in Slice 1 (thin wrapper, intentionally untested per the pure-core/impure-shell split, ref: Q11):

- `read_merge_state(ticket, branches) -> merge_state` — wraps a `gh` GraphQL read feeding `stack_merge_state` (Decision 2A); the only new network/`gt`-metadata read.
- `reparent_lowest_open(branch) -> (rc, out, err)` — wraps the single `gt move --onto main` / `gt track --parent main` call confined to this ticket's lowest open slice (Decision 1, Option A).

## Slice 1: Merged-ancestor-aware restack/submit in `qrspi_restack.py`

**Goal:** A partially-landed stack restacks and re-submits only its open slices (no `restack_conflict`), and a fully-landed stack short-circuits with no `gt` work — verified end-to-end against a reproduced partial-land condition.
**Files touched:**

- ⚠️ `scripts/qrspi_restack.py` — add `read_merge_state` (impure shell read feeding `stack_merge_state`); add pure helpers `merged_ancestors(branches, merged_flags)` and `submit_scope(branches, merged_flags, ticket)`; add the impure `reparent_lowest_open` `gt move`/`gt track` wrapper; in `restack()`/`main()`: (1) short-circuit via `is_stack_fully_merged(merge_state)` returning `ok:true, restacked:false, submitted:false` before any `gt checkout`/`restack`/`submit`; (2) when partially landed, re-parent the lowest open slice onto trunk then run the existing `--stack` submit scoped to open branches; preserve the no-op→skip-push path (ref: design.md §Delta, Decisions 1 & 2, OQ3).
- ⚠️ `scripts/qrspi_restack_test.py` — new stdlib-only cases for the pure helpers: fully-open input (no merged ancestors → full-stack scope), partial-land input (lower slices merged → scope = open slices only, lowest-open re-parent flagged), fully-landed input (all merged → empty/short-circuit scope) (ref: design.md §Delta, AC "stdlib-only unit tests").
**Verification:**
- [ ] `python3 scripts/qrspi_restack_test.py` passes, including the three new helper cases.
- [ ] Manual e2e: reproduce the partial-land condition (lower slices merged, top slice open) and run the batch; confirm `restack()` returns `ok:true` and the ticket dispatches `advance`/`land` instead of `restack_conflict` (ref: design.md AC "manual e2e", RUS-40 procedure).
- [ ] Dry-run check during e2e: `gt submit --stack --dry-run` lists only this ticket's open `<ticket>/slice-*` branches — no merged ancestors, no other tickets' branches (Risk Register blast-radius mitigation).
**Context cost:** M
**Depends on:** none

## Slice 2: Resolver entry-gate fix for populated landed-ancestor branches in `qrspi_pr_state.py`

**Goal:** A populated phase branch whose commits have landed in trunk (0 ahead because merged, not because empty) still reports `branchExists: true`, so the resolver stops emitting the spurious `entry_blocked "No design branch"` on a partially-landed stack.
**Files touched:**

- ⚠️ `scripts/qrspi_pr_state.py` — adjust the `real_branches` / `branchExists` derivation in `build_state()` so a branch that is 0-ahead of trunk is treated as present when it has a positive merged-PR signal (or still exists locally), distinguishing "0 ahead because empty placeholder" (still rejected) from "0 ahead because the work landed" (now present); factor the distinction into a pure helper if it clarifies the gate (ref: design.md §Delta, Decision 3 Option A, OQ2 — gate on merged-PR signal, not bare git existence).
- ⚠️ `scripts/qrspi_pr_state_test.py` — new regression case: a *populated landed-ancestor* design branch (0 ahead, merged PR) asserts `branchExists: true`; retain coverage that an empty-placeholder branch is still rejected (ref: design.md §Delta, Q12 gap, Risk "re-admits the empty-placeholder design branch").
**Verification:**
- [ ] `python3 scripts/qrspi_pr_state_test.py` passes, including the populated-landed-ancestor case asserting `branchExists: true` and the retained empty-placeholder rejection.
- [ ] `python3 scripts/qrspi_resolve_state_test.py` still passes (resolver consumes `branchExists`; confirm no regression in the entry-gate path).
**Context cost:** S
**Depends on:** none (independent module/code path; can be developed in parallel with Slice 1 — see Unverified Assumptions on shared e2e)

---

## Unverified Assumptions

- **Targeted re-parent command (Decision 1A).** The design names `gt move --onto main` / `gt track --parent main` as the re-parent mechanism but does not pin which one (or its exact flags) is correct for dropping a merged ancestor from this ticket's stack metadata without disturbing other tickets. The exact `gt` invocation must be confirmed against the installed `gt` version during implementation; the RUS-40 manual procedure is the reference but was not transcribed into the design.
- **`gh` GraphQL read shape in restack.** `qrspi_restack.py` makes zero `gh` calls today (ref: Q2). The design specifies feeding `stack_merge_state(branches, graphql_nodes)`, but the concrete query / how `graphql_nodes` is fetched and shaped inside `read_merge_state` is not specified — likely reuses the gather in `qrspi_pr_state.py`, but that reuse path (import vs. re-query) is unverified.
- **"Tracked parent" read.** `submit_scope` needs each open slice's *tracked parent* to decide if it is a merged ancestor, but the design states restack performs "no `gt`-metadata reads of tracked parents" today (ref: Current State). Whether the parent is inferred purely from the `<ticket>/slice-N` ordering + merged flags (pure) or requires a new `gt`-metadata read (impure) is not nailed down; the helper signatures above assume the former (order + merged flags suffice). If a real tracked-parent read is needed, an additional thin shell wrapper is required.
- **Shared manual e2e covers both slices.** The single manual e2e in Slice 1 exercises a full batch advance, which in practice also depends on the Slice 2 resolver fix to avoid `entry_blocked`. The slices are independently *unit*-testable (own `_test.py`), but the end-to-end "clean batch advance" AC realistically needs both merged. Sequencing both before the manual e2e is advisable even though there is no code-level dependency.
- **No `qrspi-batch.js` change.** The design asserts no batch control-flow change is needed if the envelope contract is unchanged. This holds only if the fully-landed short-circuit's `ok:true` envelope is dispatched to `land` by the existing batch logic without a new branch — unverified against the actual `ensureRestacked`/dispatch code, which this phase did not read.
