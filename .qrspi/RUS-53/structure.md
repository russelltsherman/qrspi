# Structure Outline — Wrong PR chosen when a branch has multiple PRs, stranding merged worktrees

**Design basis:** design.md @ 2026-06-08T00:00:00Z
**Generated:** 2026-06-08T00:00:00Z
**Status:** draft

## New Types

None. The change operates on the existing per-branch PR-node dicts and the existing
normalized merge-state dict; no new structured type is introduced.

(Optional, observability only — design Delta §1) The cleanup/merge projection dict MAY
gain one additional key, e.g. `mergedByPr: int | None` — the PR number that drove the
`merged: True` verdict. Additive; no consumer is required to read it.

## Modified Types

- **Per-branch merge projection** (the dict `stack_merge_state` builds per branch in
  `scripts/qrspi_pr_state.py`) — `merged: bool` is now derived by an "any MERGED node
  wins" scan over all fetched nodes rather than `nodes[0]["merged"]`. Same key, same
  type; only the value's derivation changes (ref: design.md §Delta, AC1/AC5).
- **`PR_QUERY`** (the GraphQL query string in `scripts/qrspi_pr_state.py`) — the
  per-branch PR connection cap changes from `first:5` to `first:25`. No new fields
  added (`state`/`merged` already per-node) (ref: design.md §Delta, AC6).

## Contracts

- `select_pr(nodes: list[dict], prefer: str) -> dict | None` — single named selection
  primitive over the fetched PR nodes for one branch.
  - `prefer="active"` — returns the advancement-facing PR. MUST reduce to identity
    (`nodes[0]`) for the common/single-PR case so the 24 pinned resolver tests and
    the `parse_pr_nodes` consumers are unchanged byte-for-byte (ref: AC3, Q10, OQ3).
  - `prefer="merged"` — returns a MERGED node if any fetched node is MERGED, else the
    active fallback. Drives the merge/land question; order-independent (ref: AC1, Q8/Q9).
- `parse_pr_nodes(nodes)` — UNCHANGED public behavior; internally expressed via
  `select_pr(nodes, prefer="active")`. Returns the same normalized advancement shape
  (`prExists`, `number`, `reviewDecision`, `unresolvedThreads`, `merged`, `state`,
  `mergedAt`) consumed by `qrspi_resolve_state.resolve` (ref: AC3, Q4, Q10).
- `stack_merge_state(...)` — per-branch `merged` now sourced from the merged-preferring
  selection (`select_pr(..., prefer="merged")` or equivalent scan), feeding
  `is_stack_fully_merged` and `classify_cleanup` unchanged downstream (ref: AC2, Q6/Q7).
- `is_stack_fully_merged(merge_state) -> bool` — UNCHANGED. Still all-or-nothing across
  real branch entries; only the per-branch `merged` input becomes correct (ref: Q6).

## Slice 1: Merge-aware PR selection at the single chokepoint

**Goal:** A branch whose work has merged reports `merged: True` even when a newer
non-merged PR exists on the same head ref, so a fully-landed stack (RUS-30) is reaped by
both cleanup and reconcile — while the advancement path stays byte-for-byte unchanged.
This is the complete end-to-end fix: selector + fetch-cap + tests, all in one module and
its test sibling, verified by one test run.

**Files touched:**

- ⚠️ `scripts/qrspi_pr_state.py` — Add the named selection primitive
  `select_pr(nodes, prefer=...)`. Re-express `parse_pr_nodes` as the `prefer="active"`
  path (identity for `len(nodes) == 1`, no behavior change — AC3/Q10/OQ3). Source the
  `stack_merge_state` per-branch `merged` from an "any MERGED node wins" scan
  (`prefer="merged"`), which also folds in the deleted-head-ref sentinel (AC5). Raise
  `PR_QUERY`'s per-branch cap from `first:5` to `first:25` (AC6). Optionally record the
  driving PR number for observability (design Delta §1).
- ⚠️ `scripts/qrspi_pr_state_test.py` — Add fixtures: merged + newer-closed (RUS-30,
  expect `merged: True`), closed + newer-merged (inverse, expect `merged: True`),
  single-PR identity (expect unchanged). Revise/replace the
  `"picks first node when multiple returned"` assertion to reflect merged-preferring
  selection (AC4/Q12). Add a deleted-head-ref-with-MERGED-node case (AC5).
- ⚠️ `scripts/qrspi_resolve_state_test.py` — ONLY if the advancement selection's
  observable output changes. Per OQ3/Q10 it must NOT; this file is expected to stay
  untouched. Listed because it is the oracle to re-run as a regression guard.

**Verification:**

- [ ] `python3 scripts/qrspi_pr_state_test.py` passes, including the new multi-PR
      fixtures and the revised `"picks first node"` assertion.
- [ ] `python3 scripts/qrspi_resolve_state_test.py` passes unchanged (24-case
      byte-for-byte baseline confirms no advancement regression — AC3).
- [ ] A constructed merged+newer-closed branch yields `is_stack_fully_merged == True`
      → `classify_cleanup` returns `destroy`, not `skip` (RUS-30 reaped — AC2).
- [ ] A constructed deleted-head-ref branch with a MERGED fetched node reads
      `merged: True` (AC5).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **`classify_cleanup` returns the literal `destroy` vs `skip` for the reapable/stranded
  cases.** The design says cleanup reads `skip` today and should reach `destroy`
  (§Current State, AC2), but the exact return tokens of `classify_cleanup` were not
  quoted in the design. The implementer must confirm the actual sentinel values against
  `scripts/qrspi_cleanup.py` before asserting on them in the verification step.
- **The optional `mergedByPr` observability field has no required consumer.** Design §Delta
  marks it "optional"; whether `qrspi_cleanup.py` / the cleanup envelope or any log line
  should surface it (ref: Q13) is left to the implementer. If added it must remain purely
  additive (no consumer made to depend on it).
- **`select_pr`'s `prefer="active"` fallback for `prefer="merged"` (when no node is MERGED)
  is assumed to equal the current active selection.** The design states the merge scan is
  "any MERGED wins" but does not spell out the no-MERGED branch's return; the safe reading
  is that it falls back to the active/`nodes[0]` PR so non-landed branches behave exactly
  as today. Confirm this preserves current `merged: False` behavior for all-open/all-closed
  branches.
