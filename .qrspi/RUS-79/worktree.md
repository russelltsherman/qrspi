# Work Tree — Critic calibration: anti-pass-bias prompt tuning (data-gated)

**Plan basis:** plan.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 (Slice 1, the data gate) → [gate: outcome=2] → T16 → T17 → T18 → T19 → T20 → T21 → T22 → T23 → T24 → T25 → T26 → T27 (Slice 3)

> **Gate note:** Slice 3 (Session 3) runs **only if** `calibration-decision.md` records
> `outcome: 2` AND the Slice 1 human gate (T7) is signed off. On outcome 1 or 3 the ticket
> closes after Session 1 and Session 3 is skipped entirely. Session 2 (Slice 2) is buildable
> independently of Slice 1's outcome but is only *consumed* by Session 3 (T25).

## Session 1 — Slice 1: Calibration decision artifact (the data gate)

**Load:** structure.md §Contracts (`CalibrationDecision`, Precondition), structure.md §New Types,
        plan.md §Slice 1, design.md §Desired End State, design.md §Delta procedure, design.md §Decision 3,
        critic-metrics.jsonl (the scoped ledger)
**Estimated context:** ~22%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Run `qrspi_critic_summary.py --run-id <id>` against the ledger; capture verbatim `dissentRate`/`perLens` baseline | — | §1.1 | S | pending |
| T2 | Confirm scoped `runId`s are distinct (not two `run-fallback`); record before/after separability mechanism | T1 | §1.2 | S | pending |
| T3 | Count sample size = number of terminated critic steps the dissentRate is computed over | T1 | §1.3 | S | pending |
| T4 | Classify observed leniency: `wording-addressable` \| `structural` \| `appropriate`, with rationale tied to ledger | T2, T3 | §1.4 | M | pending |
| T5 | Map classification → exactly one `outcome` (appropriate→1, wording→2, structural→3) | T4 | §1.5 | S | pending |
| T6 | ✨ Create `calibration-decision.md` populating all `CalibrationDecision` schema sections from T1–T5 | T5 | §1.6 | M | pending |
| T7 | **Verify Slice 1** — checkpoint: numbers match CLI verbatim, sampleSize/runIds stated, single outcome w/ rationale, **human gate** signs off sample sufficiency (OQ1) + outcome | T6 | §1.7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (the data gate) complete and human-signed-off. Fresh context for Slice 2,
which builds the independent noise-guard fixtures/asserts and shares no working set with the
decision artifact. Also marks the gate decision point: Session 3 proceeds only on outcome=2.

## Session 2 — Slice 2: Clean-design fixtures + panel-PASSES assertion (the noise guard)

**Load:** structure.md §Slice 2 Files, structure.md §Contracts (`qrspi_teeth_assert.py` math),
        structure.md §Verify, plan.md §Slice 2, design.md §Delta (new test/fixtures), design.md §Decision 1,
        evals/fixtures/design_rest_endpoint.md, scripts/qrspi_teeth_assert.py (+ its `_test.py`)
**Estimated context:** ~26%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Decide promote `design_rest_endpoint.md` into teeth set vs author from scratch; record decision + rationale | — | §2.8 | S | pending |
| T9 | ✨ Create `evals/teeth/<plainly-clean-design>.md` + sibling clean upstream files (baseline PASS fixture) | T8 | §2.9 | M | pending |
| T10 | ✨ Create `evals/teeth/<clean-but-deferring-design>.md` + siblings (defensible-deferral, highest false-positive-risk case) | T8 | §2.10 | M | pending |
| T11 | ✨ Create `evals/teeth/<third-clean-fixture>.md` + siblings (distributional coverage of the noise bound) | T8 | §2.11 | M | pending |
| T12 | ✨ Create `scripts/qrspi_clean_assert.py` — inverse-of-teeth: panel converges (no fail, no fabricated findings) on majority of trials | T9, T10, T11 | §2.12 | M | pending |
| T13 | ✨ Create `scripts/qrspi_clean_assert_test.py` — stdlib-only unit test of inverse majority/noise math; runs under `run_tests.py` | T12 | §2.13 | S | pending |
| T14 | Run `python3 scripts/run_tests.py clean`; expect the new assert-math test passes | T13 | §2.14 | S | pending |
| T15 | **Verify Slice 2** — checkpoint: assert-math test passes, promote/author decision recorded, un-tuned panel converges w/ zero fabricated findings on majority (pre-tune noise baseline) | T14 | §2.15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete. Fresh context for Slice 3 (the prompt edits), which loads a
different working set (the six critic agent files + tuned-prompt invariant) and is large enough
to warrant isolation. **Conditional boundary:** Session 3 runs ONLY IF Slice 1 outcome = 2 AND
the T7 human gate is signed off; otherwise the ticket closes here (outcome 1/3).

## Session 3 — Slice 3: Tune the six critic prompts (ONLY IF Slice 1 outcome = 2)

**Load:** structure.md §Slice 3 Files, structure.md §Tuned-prompt invariant,
        structure.md §Contracts (verbatim-preserve regions), plan.md §Slice 3,
        design.md §Decision 2 Option A, design.md §Risk Register (rows 1–4, 6, 8),
        calibration-decision.md §outcome (gate re-read), impl-log §Slice 1 outcome + §Slice 2 clean-assert (notes only),
        the six `.claude/agents/qrspi-*critic*.md` files
**Estimated context:** ~34%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Confirm gate: re-read `calibration-decision.md` `outcome` == 2 + human confirmation present; STOP if not (no prompt edit) | T7, T15 | §3.16 | S | pending |
| T17 | ⚠️ Modify `qrspi-critic.md` — adversarial "default to fail if uncertain" + "every `pass:false` MUST carry a finding"; preserve frontmatter/role/inputs/lens-scope/Verdict schema verbatim | T16 | §3.17 | M | pending |
| T18 | ⚠️ Modify `qrspi-design-critic-completeness.md` — same Rules edit; preserve verbatim regions incl. `DIGEST_PATH` line | T16 | §3.18 | S | pending |
| T19 | ⚠️ Modify `qrspi-design-critic-internal-consistency.md` — same edit; preserve `DIGEST_PATH` + all verbatim regions | T16 | §3.19 | S | pending |
| T20 | ⚠️ Modify `qrspi-design-critic-edge-alignment.md` — same edit; preserve `DIGEST_PATH` + all verbatim regions | T16 | §3.20 | S | pending |
| T21 | ⚠️ Modify `qrspi-design-critic-simplicity.md` — same edit; preserve `DIGEST_PATH` + all verbatim regions | T16 | §3.21 | S | pending |
| T22 | ⚠️ Modify `qrspi-coherence-critic.md` — same edit (impl-phase critic, no `DIGEST_PATH`); preserve verbatim regions | T16 | §3.22 | S | pending |
| T23 | Diff-review all six files: only Rules-block prose changed; every verbatim-preserve region byte-identical | T17, T18, T19, T20, T21, T22 | §3.23 | M | pending |
| T24 | Run teeth eval `Workflow({name:"qrspi-teeth-eval"})`; each owning lens still fails fixture + cites exact marker substring | T23 | §3.24 | M | pending |
| T25 | Run `python3 scripts/qrspi_clean_assert.py` over `evals/teeth/` clean set; panel still converges, zero fabricated findings post-tune | T23, T15 | §3.25 | S | pending |
| T26 | Capture before/after `dissentRate` delta with distinct `runId`s (or timestamp split); moves in intended direction by human-set magnitude | T23 | §3.26 | M | pending |
| T27 | **Verify Slice 3** — checkpoint: diff-review verbatim-preserve confirmed, teeth eval passes w/ markers, clean-assert converges, before/after delta confirmed (runIds distinct) | T24, T25, T26 | §3.27 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Feature complete (all runnable slices implemented per the gate). Fresh context for
the PR phase. Note: the six edited files (T17–T22) must serialize with RUS-82, which edits the
same files (OQ5) — coordinate revert/rebase ordering before submitting.
