# Structure Outline — Resolver mis-classifies partially-landed stacks as entry_blocked

**Design basis:** design.md @ 2026-06-11T15:00:00Z
**Generated:** 2026-06-11T15:40:00Z
**Status:** draft

## New Types

None. The work threads a merge signal through existing dict shapes; no new
record/class is introduced.

## Modified Types

- `state` dict (built by `qrspi_pr_state.build_state`, consumed by
  `qrspi_resolve_state.resolve`) — per-phase entries under `phases` gain a
  reliable `merged: bool` even when `branchExists` is False (a pruned/absent
  head), and optionally a stack-level `started`/`merged` verdict read by the
  entry gate (ref: design.md §Delta, Decision 2 Option A/B).
- Resolver test builders `_phase` / `_slice` / `_impl` / `state` in
  `qrspi_resolve_state_test.py` — add a `merged` (merge-signal) keyword so a
  fixture can model a merged-and-pruned phase (ref: design.md §Delta, AC3).

## Contracts

- `resolve(state) -> Decision` — UNCHANGED signature; the batch keeps calling
  `resolve(state)` verbatim (ref: design.md Constraint "logic stays in
  resolver"). New behavior: before declaring `entry_blocked`/`run_design` for a
  missing design branch, consult a merge signal; if design is "started but
  already landed", fall through to the active-phase/implementation `land` branch
  (Decision 1 Option A — reuses the existing `land` action, no new vocabulary).
- `design_already_landed(state) -> bool` (pseudo, internal to
  `qrspi_resolve_state.py`) — predicate: True when the design phase has a merge
  signal (`phases.design.merged` or stack-level `started`/`merged` verdict),
  even though `branchExists` is False. Strictly additive: returns True only when
  a real merge signal is present (ref: design.md Risk row 1, AC2 constraint).
- `build_state(...) -> state` — UNCHANGED signature; internally re-queries an
  absent/pruned phase head for merge state using the existing
  `stack_merge_state` / `select_pr(prefer="merged")` machinery and sets
  `phases.<name>.merged=True` when a MERGED PR exists for that head — mirroring
  `qrspi_cleanup.py` (ref: design.md Decision 2 Option A, Risk row 5). Re-query
  fires only when a phase branch is absent AND the ticket otherwise looks
  in-flight (ref: design.md Risk row 3).

## Slice 1: Resolver diverts merged-and-pruned design from the entry gate

**Goal:** The pure `resolve(state)` no longer returns `entry_blocked`
"No design branch" for a stack whose design PR has merged (branch pruned) while
upper slice PRs remain open + APPROVED; it reaches the `land` branch instead.
End-to-end testable with hand-built state dicts — the resolver is pure over a
dict, so no gather/I-O is needed to prove all three ACs.

**Files touched:**

- ⚠️ `scripts/qrspi_resolve_state.py` — add a `design_already_landed`-style
  predicate consulted before/inside the entry gate; on a present merge signal,
  fall through to the active-phase/implementation `land` logic rather than
  `entry_blocked`/`run_design`. No new action; no `run_design` merge guard
  (RQ3 — that path is unreachable) (ref: design.md §Delta, Decision 1 Option A).
- ⚠️ `scripts/qrspi_resolve_state_test.py` — extend `_phase`/`_slice`/`_impl`/
  `state` builders with a `merged` dimension; add (a) the merged-lower/open-upper
  case (design+plan merged-and-gone, slices open+APPROVED) asserting `land`
  (AC3), and (b) a regression case proving a genuinely un-started ticket (not
  assigned/Selected, zero merged PRs, no live branches) still yields
  `entry_blocked` (AC3 constraint / Risk row 1).

**Verification:**

- [ ] `python3 scripts/qrspi_resolve_state_test.py` passes, including the new
      merged-lower/open-upper case asserting `land` and the un-started
      `entry_blocked` regression case.

**Context cost:** M
**Depends on:** none

## Slice 2: build_state populates the merge signal for pruned design heads

**Goal:** In production, `build_state` supplies the merge signal Slice 1's
resolver relies on, by re-querying an absent/pruned phase head for merge state
(reusing `stack_merge_state` / `select_pr(prefer="merged")`) so
`phases.design.merged=True` survives even when every lower branch is pruned
(RQ2 — the fully-pruned mid-merge window is in scope).

**Files touched:**

- ⚠️ `scripts/qrspi_pr_state.py` — `build_state` re-queries an absent phase head
  for merge state (Decision 2 Option A), reusing the single-head query already
  used by `phase_pr` and `select_pr(prefer="merged")`; gated to fire only when a
  branch is absent AND the ticket looks in-flight (ref: design.md Decision 2,
  Risk rows 3 & 5). Optionally surface a stack-level `started`/`merged` verdict
  (Decision 2 Option B) for a clean resolver read.
- ⚠️ `scripts/qrspi_pr_state_test.py` — cover the pruned-head-returns-merged
  case at the gather layer (ref: design.md §Delta "Possibly modified").

**Verification:**

- [ ] `python3 scripts/qrspi_pr_state_test.py` passes, including a case where an
      absent design head with a MERGED PR yields `phases.design.merged=True`
      (and, if added, the stack-level `started`/`merged` verdict).
- [ ] `python3 scripts/qrspi_resolve_state_test.py` still passes (signal shape
      the resolver reads is unchanged).

**Context cost:** M
**Depends on:** Slice 1 (resolver must already consume the merge field that
this slice populates, so the field's shape is fixed before it is filled).

---

## Unverified Assumptions

- **No `qrspi-batch.js` change is required.** Decision 1 Option A reuses the
  existing `land` action, so per design.md §Delta the JS `RESOLVE_ACTIONS` /
  dispatch switch is untouched. If, during implementation, the resolver is found
  to need a new action after all, a matched `RESOLVE_ACTIONS` + switch update
  (and a vocabulary-parity test) becomes a third slice (ref: design.md
  Decision 1 Option B, Risk row 4).
- **`doLand` tolerates a partially-landed stack** (some lower slice PRs already
  merged) once the resolver reaches `land`. The design explicitly declares the
  land-worker tolerance fix OUT OF SCOPE (the multi-slice tip-exclusion bug,
  tracked separately; ref: design.md RQ1, Risk row 2). This slice plan only
  gets `resolve` to REACH `land`; it does not verify or fix `doLand` end-to-end
  landing of a partial stack. Flagged for human attention — reaching `land` may
  not actually finish the merge until that separate bug is fixed.
- **The merge re-query path is I/O and not unit-tested at the GraphQL boundary.**
  design.md Decision 2 Option A notes the absent-head re-query lives in the
  labeled I/O section of `qrspi_pr_state.py`; the unit test in Slice 2 exercises
  `build_state`'s logic with stubbed PR nodes, not a live `gh` call. Real-batch
  latency / rate-limit behavior (Risk row 3) is verifiable only by manual
  end-to-end run, not by the unit suite.
