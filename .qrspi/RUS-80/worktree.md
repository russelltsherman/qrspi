# Work Tree — Test + document the existing phase/slice resume guarantee

**Plan basis:** plan.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1,
        design.md §Decision 1 / §Decision 2 / §Decision 3, design.md §Probe Evidence
**Estimated context:** ~22% of window

The entire plan is one tests-and-docs slice touching only
`scripts/qrspi_resolve_test.py` and `docs/testing-dynamic-workflows.md` (no runtime
change), so all 8 steps fit in a single session well under the 40% ceiling. Tasks are a
linear chain: the two new assertions (T1, T2) and the framing comments (T3) edit the same
test file, the two doc edits (T4, T5) edit the same doc file, and the three checkpoints
(T6, T7, T8) verify the work in order.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add net-new non-contiguous `slice_branches` assertion (AC2) in `qrspi_resolve_test.py`, beside existing block, no new imports | — | §1 | S | pending |
| T2 | Add net-new AC3 `build_envelope` `existing`-passthrough block (tempdir + seeded artifact + `detect_existing`) in `qrspi_resolve_test.py` | T1 | §2 | S | pending |
| T3 | Add resume-framing comments on existing `detect_existing` / `pick_tip` / `slice_branches` blocks (no new assertions/imports) | T2 | §3 | S | pending |
| T4 | Add "Resume guarantee" section to `docs/testing-dynamic-workflows.md` (phase/slice-boundary by design; non-empty-present caveat; inspection-only skips) (AC4) | T3 | §4 | S | pending |
| T5 | Embed probe result verbatim + classifier-withdrawal rationale into the "Resume guarantee" section (AC4/AC5) | T4 | §5 | S | pending |
| T6 | **Verify Slice 1 — checkpoint:** `python3 scripts/run_tests.py resolve` exercises new AC2 + AC3 assertions | T5 | §6 | S | pending |
| T7 | **Verify Slice 1 — checkpoint:** `python3 scripts/run_tests.py` full suite green (AC6) | T6 | §7 | S | pending |
| T8 | **Verify Slice 1 — manual read:** `docs/testing-dynamic-workflows.md` has "Resume guarantee" section with probe result, rationale, non-empty caveat, inspection-only note | T7 | §8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** End of work. Single-slice plan; all 8 tasks complete in Session 1 and no
further slice exists.
