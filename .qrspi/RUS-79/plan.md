# Implementation Plan — Critic calibration: anti-pass-bias prompt tuning (data-gated)

**Structure basis:** structure.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total steps:** 29

> **Gating note (from structure.md):** This ticket is prompt-and-document only — no
> production code changes to the critic loop/synthesize/summary/config Python or the `critics`
> config schema. (Slice 2 DOES add a NEW off-CI eval Workflow + a pure-math assert module — the
> noise guard — mirroring the existing teeth-eval split; this is additive, not a loop change.)
> Slice 1 produces a decision artifact whose `outcome` (1/2/3) plus human sign-off determines
> whether Slice 3 runs at all. Slice 3 executes **only if outcome = 2**; on outcome 1 or 3 the
> ticket closes on Slice 1 and Slice 3 is skipped entirely. Slice 2 is buildable independently of
> Slice 1's outcome but is only *consumed* by Slice 3.

## Slice 1: Calibration decision artifact (the data gate)

### Setup

1. Discover the measurement scope FIRST (before any scoped summary). List the committed ledgers —
   `.qrspi/RUS-78/critic-metrics.jsonl`, `.qrspi/RUS-81/critic-metrics.jsonl`,
   `.qrspi/RUS-79/critic-metrics.jsonl` — and inspect their `runId`s.
   - **Expected:** a recorded inventory of available ledgers + the `runId`s present, and a
     determination of before/after separability: **distinct `runId`s** vs all-`run-fallback` (project
     memory `qrspi-batch-runid-datenow-bug`) → in which case the before/after must be split by
     **timestamp** instead. (ref: structure Contracts Precondition; design §Delta, Risk Register row 8)

2. Build the baseline. `qrspi_critic_summary.py` reads **ONE** ledger and does **not** aggregate across
   files, so concatenate the committed ledgers into one combined input and summarize that — measuring
   **only** the RUS-79 ledger is a tiny, self-referential sample (it contains this very ticket's own
   4/4-pass design run). Run `python3 scripts/qrspi_critic_summary.py [--run-id <id> | --since <ts>] <combined-ledger.jsonl>`.
   - **Expected:** emits `{ dissentRate, perLens.{lens}.dissentRate }` over the combined ledger; capture
     the verbatim numbers as the baseline. If the data is genuinely RUS-79-only, record the baseline as
     **non-binding** and defer to the OQ1 human gate. (ref: structure Contracts; design §Desired End State AC-1, §Delta procedure)

3. Count the **sample size** = number of terminated critic steps the `dissentRate` is computed over,
   across the combined scoped ledger(s).
   - **Expected:** an integer recorded for the decision doc's `sampleSize` field. (ref: design AC-1, OQ1)

### Core Logic

4. Classify the observed leniency against the three categories from `CalibrationDecision`:
   `wording-addressable` | `structural` | `appropriate` — examine the missed dissents and judge whether
   sharper wording could plausibly have caught them, or whether the misses are validity/correctness gaps
   the fidelity-only lens structurally cannot see. **Record the classification per-lens** (which lenses
   the evidence implicates) — this scopes Slice 3 (see its Verification-coverage note).
   - **Expected:** exactly one overall classification + a per-lens breakdown, with rationale tying the
     call to the ledger evidence. (ref: structure Contracts; design §Decision 3 Option B)

5. Map the classification to exactly one `outcome` (1 | 2 | 3): appropriate→1 (close, null result),
   wording-addressable→2 (tune in Slice 3), structural→3 (defer to RUS-82).
   - **Expected:** a single outcome value derived from step 4's classification. (ref: design §Desired End State AC-1, §Decision 3)

### Tests

6. ✨ Create `.worktrees/RUS-79/.qrspi/RUS-79/calibration-decision.md` — the `CalibrationDecision`
   gating document. Populate all schema sections from steps 1–5: `measuredBaseline`
   (`dissentRate`, `perLens`, `sampleSize`, **ledgersScoped**), `runIdsScoped` (or the timestamp-split
   note), `leninencyClassification` (overall **+ per-lens**), `outcome`,
   `humanSampleSufficiencyConfirmation` (the OQ1 field), and `rationale`.
   (ref: structure New Types `CalibrationDecision`; design §Delta new file)

### Verify Slice 1

7. **Checkpoint:** re-run the summary over the combined ledger and compare to the doc.
   - [ ] The cited `dissentRate`/`perLens` numbers in `calibration-decision.md` match the CLI output verbatim.
   - [ ] The doc names the **ledgers** scoped (not just RUS-79), states `sampleSize`, and records the
         scoped `runId`s as distinct (not all `run-fallback`) or that a timestamp split is used.
   - [ ] The doc concludes exactly one of outcomes 1/2/3 with rationale tying the per-lens classification
         to the evidence.
   - [ ] **Human gate:** a human confirms sample sufficiency (OQ1) and the outcome before any prompt edit.
         Slice 3 does not begin until this is signed off.

---

## Slice 2: Clean-design fixtures + panel-PASSES guard (the noise guard)

> **Architecture (mirrors the teeth eval).** The design panel can be driven **only from a Workflow** —
> a lens is a registered agentType (`qrspi-design-critic-<lens>`) spawnable only inside the agent
> harness; a plain python script cannot spawn it (see `.claude/workflows/qrspi-teeth-eval.js` header,
> which records that the design's originally-named `scripts/qrspi_teeth_eval.py` was replaced by a
> Workflow for exactly this reason). So the clean guard is a **two-part split**, the inverse of teeth:
> a **Workflow** runs the panel over the clean fixtures, and a **pure-math python module** scores the
> collected verdicts (and is the only unit-testable part).

### Setup

8. Decide whether to promote the existing clean `evals/fixtures/design_rest_endpoint.md` into the teeth
   set vs author fixtures from scratch; record the decision and its rationale.
   - **Expected:** a recorded promote/author decision. (ref: structure Verify; design §Delta, §Decision 1)

### Core Logic

9. ✨ Create `evals/teeth/<plainly-clean-design>.md` — a design the panel should PASS, plus the sibling
   clean upstream files it references.
   - **Purpose:** the baseline plainly-clean fixture. (ref: structure Slice 2 Files; design §Delta)

10. ✨ Create `evals/teeth/<clean-but-deferring-design>.md` — a design that legitimately defers scope
    ("defensible deferral", the case most at risk of false-positive noise), plus its sibling clean
    upstream files.
    - **Purpose:** the highest-risk clean case the noise guard must protect. (ref: structure Slice 2 Files; design §Decision 1)

11. ✨ Create `evals/teeth/<third-clean-fixture>.md` — a third clean design (plus siblings) so the set
    spans distributional noise rather than a single point.
    - **Purpose:** distributional coverage of the noise bound. (ref: structure Slice 2 Files; design §Decision 1)

12. ✨ Create `scripts/qrspi_clean_assert.py` — the **pure deterministic inverse-math module ONLY** (no
    panel spawning, no LLM): given grouped per-fixture/per-trial verdicts, a trial **converges** iff
    `pass is True` AND it carries no fabricated findings; a fixture passes iff converged ≥ majority
    threshold; the set passes iff every fixture passes. Stdlib + argparse, mirroring the SHAPE of
    `scripts/qrspi_teeth_assert.py` (which is itself pure math, agent-spawning lives in the Workflow).
    - **Purpose:** the unit-testable inverse-of-teeth scorer. (ref: structure Contracts `qrspi_teeth_assert.py` math; design §Decision 1, §Delta new test)

13. ✨ Create `.claude/workflows/qrspi-clean-eval.js` — the Workflow that fans out the REAL design panel
    (`qrspi-design-critic-<lens>` agents) over the clean fixture set × N trials, groups the per-lens
    verdicts, and hands them to `qrspi_clean_assert.py` (via a worker, exactly as `qrspi-teeth-eval.js`
    calls `qrspi_teeth_assert.py`), returning `{ trials, perFixture, overallPass }`. This is the
    panel-running half the python module cannot do.
    - **Purpose:** the off-CI clean-guard eval (the inverse peer of `qrspi-teeth-eval.js`). (ref: design §Decision 1; structure Slice 2 Files)

### Tests

14. ✨ Create `scripts/qrspi_clean_assert_test.py` — stdlib-only unit test of the inverse majority/noise
    math (mirrors `qrspi_teeth_assert_test.py`); must run under `run_tests.py`. Tests the deterministic
    convergence/majority math only (does NOT invoke the LLM panel — that is the Workflow's job).
    - (ref: structure Slice 2 Files)

15. Run: `python3 scripts/run_tests.py clean`
    - **Expected:** the new deterministic assert-math test passes.

### Verify Slice 2

16. **Checkpoint:** `python3 scripts/run_tests.py clean` and one `Workflow({ name: "qrspi-clean-eval" })`.
    - [ ] The new deterministic assert-math test passes.
    - [ ] The promote-vs-author decision for `evals/fixtures/design_rest_endpoint.md` is recorded (step 8).
    - [ ] The **un-tuned** panel, run via `Workflow({ name: "qrspi-clean-eval" })`, converges with zero
          fabricated findings on a majority of trials over the clean set (captures the pre-tune noise baseline).

---

## Slice 3: Tune the critic prompts (ONLY IF Slice 1 outcome = 2)

> **Conditional slice.** Execute only if `calibration-decision.md` records `outcome: 2` (leniency is
> wording-addressable) AND the human gate in step 7 is signed off. If outcome is 1 or 3, **skip this
> entire slice** — the ticket closes on Slice 1. Slice 3 also depends on Slice 2 (consumes the clean-eval
> as a verification step). **RUS-82 ordering is RESOLVED:** RUS-82 is now `blockedBy` RUS-79, so RUS-79
> lands FIRST; RUS-82 rebases on these six files afterward (OQ5 — no longer "which first").

> **Verification-coverage decision (reviewer call — addresses the harness gap).** The automated guards
> only exercise the **design panel**: the teeth eval covers exactly `{completeness, internal-consistency,
> edge-alignment}` (`qrspi-teeth-eval.js` — `simplicity` is excluded), and the clean-eval covers the
> 4-lens design panel. So `qrspi-critic.md` (the generic edge critic for questions/research/structure/plan)
> and `qrspi-coherence-critic.md` (implementation seam) would be tuned with **no automated verification**,
> and `simplicity` gets only the no-noise side, not a teeth proof. Choose per the step-4 per-lens evidence:
> **(a)** tune only the lenses that (i) the base rate shows lenient AND (ii) a harness covers — deferring
> the unharnessed prompts to a follow-up; or **(b)** tune the unharnessed prompts too, backed by a manual
> single-shot `claude -p` behavior probe (project memory `skill-creator-run-eval-invalid-in-sandbox`:
> direct probes, not the bogus run_eval harness) + manual diff-review as the only guard (step 27). Default
> to (a) unless the evidence specifically implicates the generic edge / coherence critics.

### Setup

17. Confirm the gate: re-read `calibration-decision.md` `outcome` field == 2 and the human sufficiency
    confirmation is present; confirm the Verification-coverage choice (a/b) and which files are in scope.
    If not outcome 2, stop — do not edit any prompt.
    - **Expected:** explicit go/no-go + the in-scope file list recorded; proceed only on confirmed outcome 2. (ref: structure Slice 3 Depends on; design §Decision 3, Risk Register row 1)

### Core Logic

18. ⚠️ Modify `.claude/agents/qrspi-critic.md` (**only if in scope per the coverage decision**) — sharpen
    the Rules block "fail closed on doubt" rule into explicit adversarial framing and add the "every
    `pass:false` MUST carry a concrete finding" rule.
    - **Current:** Rules block carries "Fail closed on doubt … do not pass on benefit of the doubt"; no
      "every `pass:false` MUST carry a concrete finding" rule.
    - **After:** explicit adversarial "default to fail if uncertain" framing PLUS the new finding rule.
      Frontmatter, role sentence, Inputs / input-path enumeration, lens-scope sentence, and the
      `{ pass, findings }` Verdict schema preserved **verbatim**. (ref: structure Tuned-prompt invariant; design §Decision 2 Option A, Risk Register rows 4, 6)

19. ⚠️ Modify `.claude/agents/qrspi-design-critic-completeness.md` — same Rules-block edit as step 18.
    - **Current:** shared skeleton with "fail closed on doubt"; carries the `DIGEST_PATH`-in-place-of-`RESEARCH_PATH` instruction.
    - **After:** adversarial framing + fail-must-carry-finding rule; frontmatter, Verdict schema, input-path
      enumeration, lens-scope sentence, and the `DIGEST_PATH` line preserved verbatim. (ref: structure Contracts verbatim-preserve regions; design §Delta, Risk Register row 4)

20. ⚠️ Modify `.claude/agents/qrspi-design-critic-internal-consistency.md` — same edit, preserving `DIGEST_PATH`.
    - **After:** adversarial framing + fail-must-carry-finding rule; all verbatim-preserve regions intact. (ref: design §Delta, Risk Register row 4)

21. ⚠️ Modify `.claude/agents/qrspi-design-critic-edge-alignment.md` — same edit, preserving `DIGEST_PATH`.
    - **After:** adversarial framing + fail-must-carry-finding rule; all verbatim-preserve regions intact. (ref: design §Delta, Risk Register row 4)

22. ⚠️ Modify `.claude/agents/qrspi-design-critic-simplicity.md` — same edit, preserving `DIGEST_PATH`.
    Note: `simplicity` has clean-eval (no-noise) coverage but NO teeth coverage — its catch-side is
    unverified; rely on diff-review + (if chosen) a manual probe.
    - **After:** adversarial framing + fail-must-carry-finding rule; all verbatim-preserve regions intact. (ref: design §Delta, Risk Register row 4)

23. ⚠️ Modify `.claude/agents/qrspi-coherence-critic.md` (**only if in scope per the coverage decision**) —
    same Rules-block edit (implementation-phase coherence critic; no `DIGEST_PATH` line).
    - **After:** adversarial framing + fail-must-carry-finding rule; frontmatter, Verdict schema, input-path
      enumeration, and lens-scope sentence preserved verbatim. (ref: structure Slice 3 Files; design §Delta)

### Tests

24. Diff-review each edited file for verbatim preservation of frontmatter, role sentence, input-path
    enumeration, Verdict `{ pass, findings }` schema, lens-scope sentence, and (the four design lenses)
    the `DIGEST_PATH`-in-place-of-`RESEARCH_PATH` instruction.
    - **Expected:** only the Rules-block prose changed; every verbatim-preserve region byte-identical. (ref: structure Verify; design Risk Register row 4)

25. Run the teeth eval: `Workflow({ name: "qrspi-teeth-eval" })`
    - **Expected:** each owning lens still fails the flawed fixture AND still cites its exact marker substring
      (`completeness`→`AC-TEETH-COMPLETENESS`, `internal-consistency`→`TEETH-INCONSISTENCY`,
      `edge-alignment`→`frobnicate_widget()`). (ref: design AC-3, Risk Register row 3)

26. Run the clean-eval from Slice 2: `Workflow({ name: "qrspi-clean-eval" })` over the `evals/teeth/` clean set.
    - **Expected:** the panel still converges with zero fabricated findings on a majority of trials post-tune
      (no regression toward noise). (ref: design AC-4, Risk Register row 2)

27. If coverage option (b) was chosen — manual behavior probe for the **unharnessed** tuned prompts
    (`qrspi-critic.md`, `qrspi-coherence-critic.md`, and `simplicity`'s catch-side): run a single-shot
    `claude -p` check that the tuned prompt still passes a clean artifact and dissents (with a concrete
    finding) on a seeded defect.
    - **Expected:** recorded pass/dissent behavior for each unharnessed prompt; no fabricated finding on the
      clean input. (ref: Verification-coverage decision; project memory `skill-creator-run-eval-invalid-in-sandbox`)

28. Capture the **before/after** delta: run `python3 scripts/qrspi_critic_summary.py` over the same combined
    ledger / real ticket before and after the edits, with **distinct** `runId`s (or a timestamp-split ledger
    per step 1).
    - **Expected:** `dissentRate` moves in the intended direction by the human-set magnitude (OQ2); the
      runIds are confirmed distinct, not `run-fallback`. (ref: design AC-5, OQ2, Risk Register row 8)

### Verify Slice 3

29. **Checkpoint:** `Workflow({ name: "qrspi-teeth-eval" })` && `Workflow({ name: "qrspi-clean-eval" })`.
    - [ ] Diff-review confirms verbatim preservation in all edited files (step 24).
    - [ ] Teeth eval passes: each owning lens fails the flawed fixture AND cites its exact marker (step 25).
    - [ ] Clean-eval still converges with zero fabricated findings post-tune (step 26).
    - [ ] Any unharnessed tuned prompt passed its manual probe (step 27, if option b).
    - [ ] Before/after `dissentRate` delta moves in the intended direction by the human-set magnitude;
          runIds confirmed distinct (step 28).

---

## Rollback Notes

- **Step 6 (`calibration-decision.md`):** safe to revert — delete the file; a new, non-executing document
  with no downstream code dependency. No data migration.
- **Steps 9–14 (Slice 2 fixtures + assert module + clean-eval Workflow + test):** safe to revert — all new
  files under `evals/teeth/`, `scripts/`, and `.claude/workflows/`; deleting them removes the new off-CI
  guard with no effect on existing behavior. `scripts/qrspi_clean_assert_test.py` is picked up by
  `run_tests.py` by glob, so its removal cleanly drops it from the suite. The new `qrspi-clean-eval.js`
  Workflow is opt-in (invoked only by name), so its presence is inert until called.
- **Steps 18–23 (the prompt edits):** the only edits to **existing, behavior-bearing** files. Each is a
  single-file prose change with no schema/contract change. Roll back per-file by restoring the
  verbatim-preserve regions and reverting the Rules-block wording to the prior "fail closed on doubt" text.
  **Gate risk:** if outcome is later reclassified to 1 or 3, every edited prompt must be reverted wholesale
  (the tune was unwarranted). **RUS-82 ordering is resolved** (RUS-82 `blockedBy` RUS-79 → RUS-79 lands
  first); RUS-82 rebases on the tuned files afterward, so no contradictory concurrent tuning of the shared
  fail-closed rule (OQ5).
