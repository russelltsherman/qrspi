# Work Tree — Wire the RUS-58 per-slice edge critic into the doImplementation slice loop

**Plan basis:** plan.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

> Single-slice plan (Slice 1, 12 steps). All five code edits modify the one file
> `.claude/workflows/qrspi-batch.js` and are mutually dependent, so they form one
> serial chain in a single implementation session. The verification checkpoints
> (plan §9–12) are manual end-to-end inspections that follow the code + automated
> checks; they are grouped as the closing Verify task of the session.

## Session 1

**Load:** structure.md §New Types, structure.md §Contracts, structure.md §Slice 1,
        plan.md §Slice 1, design.md §Delta 1-6 (referenced anchors only)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add `SLICE_DECIDE_SCHEMA` constant after `LOOP_DECISION_SCHEMA` (validates the `decide()` envelope) | — | §1 | S | pending |
| T2 | Add `sliceCriticDecide(t, setup, n)` worker helper modeled on `criticDecision`; injects `t.id`, validates against `SLICE_DECIDE_SCHEMA` | T1 | §2 | M | pending |
| T3 | Declare cross-iteration accumulator `const perSliceFindings = {}` beside `coherenceFindings` / `previousNotes` | — | §3 | S | pending |
| T4 | Insert the gated in-loop critic block (decide → skip-on-null → critic-skip log or `runSliceCritic` → store `residualFindings`) after the per-slice commit | T2, T3 | §4 | L | pending |
| T5 | Extend finalize worker prompt to splice coherence + per-slice findings into the matching slice commits (skip-on-empty), lowest-N-first, before the single `gt submit --stack` | T4 | §5 | L | pending |
| T6 | Run reducer regression suites: `python3 scripts/qrspi_slice_critic_test.py && python3 scripts/qrspi_critic_body_test.py` | T5 | §7 | S | pending |
| T7 | Run `node --check .claude/workflows/qrspi-batch.js` (syntax gate) | T5 | §8 | S | pending |
| T8 | **Verify Slice 1** — manual end-to-end checkpoints: enabled-path decide+critic+splice with exactly one `gt submit --stack`; disabled-path byte-identical transcript; failure-path `skip()` on null-decide / critic-spawn-fail; empty-bucket no-op (no `qrspi_critic_body.py`/restack) | T6, T7 | §9–12 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** End of the single implementation slice. No further sessions — the plan
defines exactly one vertical slice, so the stack is ready for finalize/submit.
