# Work Tree — Resolver mis-classifies partially-landed stacks as entry_blocked

**Plan basis:** plan.md @ 2026-06-11T16:10:00Z
**Generated:** 2026-06-11T16:30:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T4 → T5 → T6 → T9 → T10 → T11 → T12 → T16 → T18

## Session 1 — Slice 1: Resolver diverts merged-and-pruned design from the entry gate

**Load:** structure.md §Modified Types, structure.md §Contracts (`resolve`, `design_already_landed`), plan.md §Slice 1
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Extend `_phase` builder in `qrspi_resolve_state_test.py` with `merged=False` keyword writing `"merged"` onto the phase dict | — | §1.1 | S | pending |
| T2 | Extend `_slice` builder with the same `merged=False` keyword on the per-slice dict | — | §1.2 | S | pending |
| T3 | Extend `_impl` builder with `merged=False` keyword carrying the merge signal | — | §1.3 | S | pending |
| T4 | Extend `state` builder to thread per-phase `merged` signals into the assembled `phases` map | T1, T2, T3 | §1.4 | S | pending |
| T5 | Add internal predicate `design_already_landed(state) -> bool` in `qrspi_resolve_state.py` (reads merge fields only; True only on genuine merge signal) | — | §1.5 | M | pending |
| T6 | In `resolve(state)`, consult `design_already_landed` before the `entry_blocked`/`run_design` short-circuit; fall through to active-phase/`land` logic when True | T5 | §1.6 | M | pending |
| T7 | Add test: merged-lower / open-upper case (design+plan `merged=True`, slices open+APPROVED) asserts `resolve(...).action == "land"` | T4, T6 | §1.7 | S | pending |
| T8 | Add regression test: un-started ticket (no merges, no live branches) still resolves to `entry_blocked` | T4, T6 | §1.8 | S | pending |
| T9 | **Verify Slice 1:** `python3 scripts/qrspi_resolve_state_test.py` — suite passes, `land` case green, `entry_blocked` regression green | T7, T8 | §1.9 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (resolver logic + tests pass). Fresh context for Slice 2, which touches a different file (`qrspi_pr_state.py`) — drop Slice 1 implementation detail, retain only the per-phase `merged` signal shape as a contract.

## Session 2 — Slice 2: build_state populates the merge signal for pruned design heads

**Load:** structure.md §Contracts (`build_state`), plan.md §Slice 2, impl-log.md §Slice 1 (the `phases.<name>.merged` signal shape only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | In `build_state` (`qrspi_pr_state.py`), add a guard firing the merge re-query only when a phase branch is absent AND the ticket looks in-flight | T9 | §2.10 | M | pending |
| T11 | Within the guard, re-query the absent phase head for merge state via the existing single-head machinery, selecting with `select_pr(prefer="merged")` | T10 | §2.11 | M | pending |
| T12 | Set `phases.<name>.merged=True` on the absent phase head when the re-query finds a MERGED PR (mirroring `qrspi_cleanup.py`) | T11 | §2.12 | S | pending |
| T13 | (Optional) Surface a stack-level `started`/`merged` verdict in `state`, aggregating per-phase `merged` | T12 | §2.13 | S | pending |
| T14 | Add gather-layer test: absent design head with a MERGED PR (stubbed nodes) yields `phases.design.merged=True` | T12 | §2.14 | S | pending |
| T15 | (Optional) If T13 done, assert stack-level verdict matches per-phase `merged` fields | T13 | §2.15 | S | pending |
| T16 | Add guard test: re-query does NOT fire for a present-branch or not-in-flight fixture (bounds `gh` calls) | T12 | §2.16 | S | pending |
| T17 | Cross-check: `python3 scripts/qrspi_resolve_state_test.py` still passes (signal shape unchanged) | T12 | §2.17 | S | pending |
| T18 | **Verify Slice 2:** `python3 scripts/qrspi_pr_state_test.py && python3 scripts/qrspi_resolve_state_test.py` — absent-head-MERGED case green, guard test green, resolver suite still green | T14, T16, T17 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Feature complete — both slices implemented and verified. No further session; remaining work (PR summary) is handled by the `/qrspi-pr` phase.
