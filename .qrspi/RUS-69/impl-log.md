# Implementation Log — Resolver mis-classifies partially-landed stacks as entry_blocked

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T22:13:04Z
**Tasks completed:** 1, 2, 3, 4, 5, 6, 7, 8, 9
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_resolve_state_test.py` → 41 passed, 0 failed (39 prior + 2 new)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- Plan step 4 (thread the per-phase `merged` field through the `state` builder) required
  no code change: the existing `state(...)` builder already passes the `phases` dict
  through verbatim, so the `merged` field added to `_phase`/`_impl`/`_slice` (steps 1–3)
  is preserved automatically. The intent of step 4 is satisfied; no edit was needed.

**Notes for next session:**

- The merge signal the resolver now consumes is `phases.design.merged` (truthy bool).
  `design_already_landed(state)` in `scripts/qrspi_resolve_state.py` also accepts an
  optional stack-level verdict (`state["stack"]["merged"]` or top-level `state["merged"]`),
  but the per-phase `phases.design.merged` flag is the primary contract. Slice 2's
  `build_state` must set `phases.design.merged = True` on the absent/pruned design head
  for the production path to work — the resolver already reads it.
- The entry-gate diversion is guarded as `if "design" not in existing and not
  (design_already_landed(state) and existing):` — the `and existing` clause ensures the
  fall-through only happens when some other phase (e.g. an open implementation slice) still
  exists to land. If every branch is pruned (`existing` empty), the entry gate still applies.
  Slice 2 should confirm the fully-pruned mid-merge window keeps at least the open slice
  branches in `existing` (it does — slices are still open in that window).
- Signature `resolve(state) -> Decision` is UNCHANGED; no new action vocabulary added
  (reuses `land`), so no `qrspi-batch.js` change is required (structure Unverified
  Assumption confirmed for this slice).

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-11T22:15:57Z
**Tasks completed:** T10, T11, T12, T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_pr_state_test.py` → 83 passed, 0 failed (75 prior + 8 new)
- `python3 scripts/qrspi_resolve_state_test.py` → 41 passed, 0 failed (signal shape unchanged)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. The optional steps (T13 stack-level `started`/`merged` verdict, T15 its
  assertion) were both implemented, not skipped.

**Notes for next session:**

- Production wiring complete: `build_state` (`scripts/qrspi_pr_state.py`) now re-queries
  an absent/pruned PHASE head (design/plan) when the ticket `looks_in_flight` (≥1 live
  slice branch, i.e. `bool(real_snums)`). The re-query uses `_query_pr(owner,repo,head)`
  (GraphQL is by `headRefName`, so a deleted ref still returns nodes) and
  `select_pr(prefer="merged")`; on a MERGED node it sets `phases.<name>.merged=True`
  plus `number`/`state`/`mergedAt`, while `branchExists` stays False.
- The guard bounds `gh` calls exactly as specified: a present branch is queried as
  before; a NOT-in-flight ticket (no live slices) fires NO absent-head re-query (T16b
  asserts the design head is never queried in that case).
- Added an additive stack-level verdict `state["stack"] = {"started": bool, "merged":
  bool}` (Decision 2 Option B). `merged` mirrors `phases.design.merged`; `started` is
  True once any real branch or merge signal exists. `design_already_landed` already
  reads `state["stack"]["merged"]`, and because `stack.merged` is defined as exactly
  `bool(design_phase["merged"])`, there is no false-positive path — it is True only when
  design genuinely merged.
- Verified end-to-end (hermetic stubs): a pruned-design/pruned-plan + live-APPROVED-slice
  state fed through the REAL `resolve` returns `action="land"` (not `entry_blocked`),
  closing the Slice 1 ↔ Slice 2 contract.
- Feature is functionally complete (both slices). Remaining out-of-scope item per
  structure Unverified Assumptions: `doLand`'s tolerance of a partially-landed stack is
  a SEPARATE bug — reaching `land` does not guarantee the partial stack finishes merging.
