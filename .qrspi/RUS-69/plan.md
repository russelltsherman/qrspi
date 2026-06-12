# Implementation Plan — Resolver mis-classifies partially-landed stacks as entry_blocked

**Structure basis:** structure.md @ 2026-06-11T15:40:00Z
**Generated:** 2026-06-11T16:10:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: Resolver diverts merged-and-pruned design from the entry gate

**Goal:** The pure `resolve(state)` no longer returns `entry_blocked` ("No
design branch") for a stack whose design PR has merged (branch pruned) while
upper slice PRs remain open + APPROVED; it reaches the `land` branch instead.
Signature `resolve(state) -> Decision` is UNCHANGED (ref: structure.md
Contracts).

### Setup

1. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — extend the `_phase`
   builder to accept a `merged` keyword (default `False`) and write it onto the
   phase dict alongside the existing branch/PR/decision/thread/comment fields,
   so a fixture can model a merged-and-pruned phase (ref: structure.md Modified
   Types; design.md AC3).
   - **Current:** `_phase(...)` produces a phase dict with no `merged` field.
   - **After:** `_phase(..., merged=False)` sets `"merged": merged` on the
     returned phase dict.

2. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — extend the `_slice`
   builder with the same `merged=False` keyword, threaded onto the per-slice
   dict (ref: structure.md Modified Types).
   - **Current:** `_slice(...)` has no `merged` parameter.
   - **After:** `_slice(..., merged=False)` carries `"merged": merged`.

3. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — extend the `_impl`
   builder with a `merged=False` keyword so the implementation phase entry can
   carry a merge signal (ref: structure.md Modified Types).
   - **Current:** `_impl(...)` has no `merged` parameter.
   - **After:** `_impl(..., merged=False)` carries `"merged": merged`.

4. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — extend the `state`
   builder so it threads any `merged` signal set on the phase fixtures through
   into the assembled `phases` map (ref: structure.md Modified Types).
   - **Current:** `state(...)` assembles `phases` without preserving a
     per-phase `merged` field.
   - **After:** `state(...)` preserves each phase's `merged` field in the
     assembled `phases` map.

### Core Logic

5. ⚠️ Modify `scripts/qrspi_resolve_state.py` — add an internal predicate
   `design_already_landed(state) -> bool` that returns True only when a real
   merge signal is present for the design phase (`phases.design.merged` truthy,
   or the stack-level `started`/`merged` verdict if present), and False
   otherwise — strictly additive (ref: structure.md Contracts
   `design_already_landed`; design.md Decision 1 Option A, AC2 constraint).
   - **Current:** no such predicate exists.
   - **After:** `design_already_landed(state) -> bool` defined, reading only
     merge fields, returning True only on a genuine merge signal.

6. ⚠️ Modify `scripts/qrspi_resolve_state.py` — in `resolve(state)`, before
   the entry gate declares `entry_blocked`/`run_design` for a missing design
   branch (`if "design" not in existing`), consult `design_already_landed`; if
   True, fall through to the active-phase/implementation `land` logic instead
   of returning `entry_blocked`/`run_design`. No new action is added; the
   `run_design` branch gets no merge guard (RQ3 — unreachable) (ref:
   structure.md Contracts `resolve`; design.md Decision 1 Option A, §Delta).
   - **Current:** `if "design" not in existing:` short-circuits to
     `entry_blocked`/`run_design` regardless of merge state.
   - **After:** the same branch first checks `design_already_landed(state)` and,
     when True, falls through to the existing active-phase/`land` logic.

### Tests

7. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add a test for the
   merged-lower / open-upper case: design + plan merged-and-gone
   (`branchExists=False`, `merged=True`), implementation slices open + APPROVED,
   asserting `resolve(...).action == "land"` (ref: structure.md Verification;
   design.md AC3).
   - **Expected:** the new test asserts `land` for the merged-lower /
     open-upper stack.

8. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add a regression test
   proving a genuinely un-started ticket (not assigned/Selected, zero merged
   PRs, no live branches) still resolves to `entry_blocked` (ref: structure.md
   Verification; design.md AC3 constraint, Risk row 1).
   - **Expected:** the un-started fixture still asserts `entry_blocked`.

### Verify Slice 1

9. **Checkpoint:** `python3 scripts/qrspi_resolve_state_test.py`
   - [ ] Suite passes.
   - [ ] The new merged-lower / open-upper case asserts `land`.
   - [ ] The un-started regression case asserts `entry_blocked`.

---

## Slice 2: build_state populates the merge signal for pruned design heads

**Goal:** In production, `build_state` supplies the merge signal Slice 1's
resolver relies on, re-querying an absent/pruned phase head for merge state
(reusing `stack_merge_state` / `select_pr(prefer="merged")`) so
`phases.design.merged=True` survives even when every lower branch is pruned.
Signature `build_state(...) -> state` is UNCHANGED (ref: structure.md
Contracts).

### Setup

10. ⚠️ Modify `scripts/qrspi_pr_state.py` — in `build_state`, add a guard
    condition that fires the merge re-query only when a phase branch is absent
    (`branchExists=False`) AND the ticket otherwise looks in-flight (live
    slices or a known prior PR), not on every gather (ref: structure.md
    Contracts `build_state`; design.md Decision 2, Risk row 3).
    - **Current:** `build_state` does not re-query absent/pruned phase heads.
    - **After:** a guarded branch computes whether a re-query is warranted for
      each absent phase head.

### Core Logic

11. ⚠️ Modify `scripts/qrspi_pr_state.py` — within the guarded branch,
    re-query the absent phase head for merge state using the existing
    single-head query machinery already used by `phase_pr`, selecting with
    `select_pr(prefer="merged")` ("any MERGED node wins") to avoid the
    index-0 masking class (ref: structure.md Contracts `build_state`; design.md
    Risk row 5, Decision 2 Option A).
    - **Current:** an absent head yields the empty `parse_pr_nodes([])` shape
      with `merged=False`.
    - **After:** an absent head with a MERGED PR is re-queried and yields a
      MERGED node via `select_pr(prefer="merged")`.

12. ⚠️ Modify `scripts/qrspi_pr_state.py` — set `phases.<name>.merged=True`
    on the absent phase head when the re-query finds a MERGED PR, mirroring
    `qrspi_cleanup.py` (ref: structure.md Contracts `build_state`; design.md
    Decision 2 Option A, Risk row 5).
    - **Current:** `phases.<name>.merged` stays `False` for a pruned head.
    - **After:** `phases.<name>.merged=True` when a MERGED PR exists for that
      absent head.

13. ⚠️ Modify `scripts/qrspi_pr_state.py` — optionally surface a stack-level
    `started`/`merged` verdict in the returned `state` for a clean resolver
    read (Decision 2 Option B), aggregating per-phase `merged` (ref:
    structure.md Contracts `build_state`; design.md Decision 2 Option B).
    - **Current:** `state` carries no stack-level `started`/`merged` verdict.
    - **After:** `state` optionally carries an aggregated `started`/`merged`
      verdict consistent with the per-phase `merged` fields.

### Tests

14. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a case at the gather
    layer where an absent design head with a MERGED PR (stubbed PR nodes)
    yields `phases.design.merged=True` (ref: structure.md Verification;
    design.md §Delta "Possibly modified").
    - **Expected:** absent-head-with-MERGED-PR fixture yields
      `phases.design.merged=True`.

15. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — if the stack-level
    `started`/`merged` verdict was added in step 13, assert it is populated
    consistently with the per-phase `merged` fields (ref: structure.md
    Verification).
    - **Expected:** stack-level verdict matches the per-phase merge signals
      (skip if step 13 was not implemented).

16. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add a guard test proving the
    re-query does NOT fire when a branch is present, or when the ticket does
    not look in-flight, keeping `gh` calls bounded (ref: structure.md Contracts
    `build_state`; design.md Risk row 3).
    - **Expected:** no re-query (and no spurious `merged=True`) for a
      present-branch or not-in-flight fixture.

### Tests (cross-check)

17. Run: `python3 scripts/qrspi_resolve_state_test.py`
    - **Expected:** still passes — the per-phase `merged` signal shape the
      resolver reads is unchanged by Slice 2 (ref: structure.md Verification;
      Depends on: Slice 1).

### Verify Slice 2

18. **Checkpoint:** `python3 scripts/qrspi_pr_state_test.py && python3 scripts/qrspi_resolve_state_test.py`
    - [ ] `qrspi_pr_state_test.py` passes, including the absent-head-MERGED case
          yielding `phases.design.merged=True`.
    - [ ] The re-query guard test confirms no re-query for present-branch /
          not-in-flight fixtures.
    - [ ] `qrspi_resolve_state_test.py` still passes (signal shape unchanged).

---

## Rollback Notes

- No DB migrations, config changes, or destructive operations are involved —
  all steps are additive edits to four Python files
  (`scripts/qrspi_resolve_state.py`, `scripts/qrspi_resolve_state_test.py`,
  `scripts/qrspi_pr_state.py`, `scripts/qrspi_pr_state_test.py`).
- Rollback for any step: revert the edit to the named file; the changes are
  strictly additive (new predicate, new keyword args, new test cases, a guarded
  re-query branch) and reverting restores prior behavior with no residual state.
- Step 11/12 (the `gh` GraphQL re-query) performs reads only — no mutation —
  so reverting needs no cleanup of remote state.
