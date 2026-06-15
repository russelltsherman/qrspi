# Structure Outline — Critic calibration: anti-pass-bias prompt tuning (data-gated)

**Design basis:** design.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

> This ticket is **prompt-and-document only**. No production code (`qrspi-batch.js`,
> synthesize/loop/summary/config Python, `critics` config schema) changes. The "types"
> below are document schemas and the existing assert-harness data shapes the slices reuse,
> not new runtime types. The dominant structural fact is a **hard data gate**: Slice 1
> produces a decision artifact whose conclusion (and human sign-off) determines whether
> Slices 3+ run at all.

## New Types

- `CalibrationDecision` (markdown document, not code) — the gating artifact at
  `.qrspi/RUS-79/calibration-decision.md`. Sections:
  `{ measuredBaseline: { dissentRate: number, perLens: { lens: dissentRate }, sampleSize: int (terminated critic steps) },
     runIdsScoped: string[], leninencyClassification: "wording-addressable" | "structural" | "appropriate",
     outcome: 1 | 2 | 3, humanSampleSufficiencyConfirmation: bool, rationale: text }`
  (ref: design §Desired End State AC-1, §Decision 3).
- `CleanFixtureSet` (fixture files, not code) — ≥3 clean design fixtures under
  `evals/teeth/` the panel must PASS: at least one *plainly-clean* design and at least one
  *clean-but-deferring* design (legitimate scope deferral), each with sibling clean upstream
  files it references (ref: design §Delta, §Decision 1).

## Modified Types

- None. The atomic critic verdict `{ pass, findings }`, the `critics` config schema, and the
  teeth-assert data shapes are all preserved verbatim (ref: design §Delta "No code changes",
  §Decision 2). The prompt edits change *prose inside* the existing prompt skeleton, not any
  type.

## Contracts

These are existing interfaces the slices consume; none are newly authored by this ticket.

- `qrspi_critic_summary.py [--run-id <id>] <ledger.jsonl>` → emits `{ dissentRate, perLens.{lens}.dissentRate }`
  over ONE JSONL ledger — the before/after baseline measurement source (ref: design §Desired End
  State, §Delta procedure). **It reads a single ledger and does NOT aggregate across files**, so a
  representative base rate requires concatenating the committed ledgers (RUS-78/RUS-81/RUS-79) into
  one combined input; measuring only `.qrspi/RUS-79/critic-metrics.jsonl` is a tiny, self-referential
  sample. **Precondition:** before/after runs must carry **distinct** `runId`s (the ledger currently
  emits `run-fallback`; confirm unique runIds or split the ledger by timestamp).
- **Clean-guard architecture (two-part split, the inverse of teeth).** The design panel is spawnable
  **only from a Workflow** (a lens is a registered agentType `qrspi-design-critic-<lens>`; a plain
  python script cannot drive it — see `.claude/workflows/qrspi-teeth-eval.js`, which records that the
  design's originally-named `scripts/qrspi_teeth_eval.py` was replaced by a Workflow for this reason).
  So the noise guard is: (1) `scripts/qrspi_clean_assert.py` — a PURE deterministic scorer (a trial
  converges iff `pass is True` AND no fabricated findings; a fixture passes iff converged ≥ majority;
  unit-tested), mirroring the SHAPE of `qrspi_teeth_assert.py`; and (2) `.claude/workflows/qrspi-clean-eval.js`
  — a Workflow that fans out the real panel over the clean set × N trials and hands grouped verdicts to
  the scorer, the inverse peer of `qrspi-teeth-eval.js` (ref: design §Decision 1, §Delta new test).
- Design-critic prompt contract (verbatim-preserve regions in all six prompt files):
  frontmatter, role sentence, Inputs / input-path enumeration, lens-scope sentence, the
  `{ pass, findings }` Verdict schema, and the `DIGEST_PATH`-in-place-of-`RESEARCH_PATH`
  instruction (ref: design §Delta, §Decision 2, Risk Register row 4).
- Tuned-prompt invariant (added by Slice 3): every `pass:false` verdict MUST carry at least
  one concrete finding (ref: design §Decision 2, Risk Register row 6).

## Slice 1: Calibration decision artifact (the data gate)

**Goal:** Produce the committed gating document recording the measured RUS-78 base rate, its
sample size, the lens-classification of observed leniency, and the three-way outcome call —
the artifact every downstream slice is gated on. This is the ticket's *first deliverable* and
delivers a complete, reviewable end-to-end result on its own (the design's primary AC).
**Files touched:**

- ✨ `.qrspi/RUS-79/calibration-decision.md` — records `dissentRate` (overall + per-lens) and
  **sample size** (count of terminated critic steps) from `qrspi_critic_summary.py`; classifies
  the misses as wording-addressable vs structural vs appropriate (Decision 3); states outcome
  1/2/3; carries an explicit field for the human sample-sufficiency confirmation (OQ1).
**Verification:**
- [ ] Run `python3 scripts/qrspi_critic_summary.py --run-id <id>` against the existing ledger;
      the cited `dissentRate`/`perLens` numbers in the doc match its output verbatim.
- [ ] Document states sample size (number of terminated critic steps) and names the scoped
      runIds; confirms they are distinct (not two `run-fallback` lines).
- [ ] Document concludes exactly one of outcomes 1/2/3 with rationale tying the classification
      to the evidence (Decision 3 Option B).
- [ ] Human confirms sample sufficiency (OQ1) and the outcome before any prompt edit.
**Context cost:** S
**Depends on:** none

## Slice 2: Clean-design fixtures + panel-PASSES assertion (the noise guard)

**Goal:** Add the regression guard the repo currently lacks: clean-design fixtures the panel
must PASS plus an inverse-of-teeth assertion that the panel converges with no fabricated
findings. Independently testable — it runs and proves the *current* (un-tuned) panel passes
the clean set, establishing the pre-tune baseline the noise AC needs. Buildable regardless of
Slice 1's outcome, but only *consumed* by Slice 3.
**Files touched:**

- ✨ `evals/teeth/<plainly-clean-design>.md` (+ sibling clean upstream files it references) —
  a design the panel should PASS.
- ✨ `evals/teeth/<clean-but-deferring-design>.md` (+ siblings) — a design that legitimately
  defers scope (the "defensible deferral" case most at risk of false-positive noise).
- ✨ `evals/teeth/<third-clean-fixture>.md` (+ siblings) — third fixture so the set spans
  distributional noise, not a single point.
- ✨ `scripts/qrspi_clean_assert.py` — the PURE deterministic inverse-of-teeth scorer (no panel
  spawning): converged iff `pass is True` AND no fabricated findings, majority-thresholded; mirrors
  the SHAPE of `qrspi_teeth_assert.py`.
- ✨ `.claude/workflows/qrspi-clean-eval.js` — the Workflow that runs the real design panel over the
  clean set × N trials and feeds grouped verdicts to `qrspi_clean_assert.py` (the panel-running half a
  python script cannot do); the inverse peer of `qrspi-teeth-eval.js`.
- ✨ `scripts/qrspi_clean_assert_test.py` — stdlib-only unit test of the inverse majority/noise
  math (mirrors `qrspi_teeth_assert_test.py`); runs under `run_tests.py`.
**Verification:**
- [ ] `python3 scripts/run_tests.py clean` passes (the new deterministic assert-math test).
- [ ] Before authoring from scratch, evaluate promoting the existing clean
      `evals/fixtures/design_rest_endpoint.md` into the teeth set (Delta) — record the decision.
- [ ] The un-tuned panel run over the clean set converges with zero fabricated findings on a
      majority of trials (captures the pre-tune noise baseline).
**Context cost:** M
**Depends on:** none (orderable before or alongside Slice 1; precedes Slice 3)

## Slice 3: Tune the six critic prompts (ONLY IF Slice 1 outcome = 2)

**Goal:** If and only if the calibration decision warrants it (outcome 2: leniency is
wording-addressable), sharpen the existing "fail closed on doubt" rule into explicit
adversarial framing in each of the six pass/fail critic prompts and add the "every `pass:false`
MUST carry a concrete finding" rule — verifying via teeth eval (markers still cited), the
clean-fixture assert (no new noise), and a before/after dissent-rate delta. If outcome is 1 or
3, this slice is **skipped** and the ticket closes on Slice 1.
**Files touched:**

- ⚠️ `.claude/agents/qrspi-critic.md` — sharpen Rules block; add fail-must-carry-finding rule;
  preserve frontmatter / Verdict schema / input paths verbatim.
- ⚠️ `.claude/agents/qrspi-design-critic-completeness.md` — same; preserve `DIGEST_PATH` line.
- ⚠️ `.claude/agents/qrspi-design-critic-internal-consistency.md` — same; preserve `DIGEST_PATH`.
- ⚠️ `.claude/agents/qrspi-design-critic-edge-alignment.md` — same; preserve `DIGEST_PATH`.
- ⚠️ `.claude/agents/qrspi-design-critic-simplicity.md` — same; preserve `DIGEST_PATH`.
- ⚠️ `.claude/agents/qrspi-coherence-critic.md` — same.
**Verification:**
- [ ] Diff-review each file confirms verbatim preservation of frontmatter, role sentence,
      input-path enumeration, Verdict `{ pass, findings }` schema, lens-scope sentence, and the
      `DIGEST_PATH`-in-place-of-`RESEARCH_PATH` instruction (Risk Register row 4).
- [ ] Teeth eval still passes: each owning lens fails the flawed fixture AND cites its exact
      marker substring (Workflow `qrspi-teeth-eval`; AC-3, Risk Register row 3).
- [ ] Clean-fixture assert from Slice 2 still converges with zero fabricated findings post-tune
      (no regression toward noise; AC-4).
- [ ] Before/after `runId`-scoped `qrspi_critic_summary.py` over the same real ticket shows
      `dissentRate` moving in the intended direction by the human-set magnitude (AC-5, OQ2);
      runIds confirmed distinct (not `run-fallback`).
**Context cost:** M
**Depends on:** Slice 1 (gate: only runs if outcome 2), Slice 2 (consumes the clean-fixture
assert as a verification step)

---

## Unverified Assumptions

- **Sample-size sufficiency is unresolved (OQ1, binding).** The design states only three
  ledgers exist (RUS-78/RUS-81/RUS-79) and the sample is "too small to bind the calibration
  decision." Whether enough data will exist at structure/plan time is a human gate, not a
  mappable code path — Slice 1 records the number but cannot itself decide sufficiency.
- **Outcome is unknown until Slice 1 runs.** Slice 3 may not execute at all (outcomes 1/3 close
  the ticket with no prompt edits). The slice ordering encodes this conditionality, but the
  branch cannot be pre-resolved here.
- **"Measurably moves" magnitude (OQ2) is undefined.** The AC is directional only; the concrete
  minimum `dissentRate` delta must be set by a human against the observed baseline before
  Slice 3's delta check has a pass/fail bar.
- **before/after `runId` collision risk (Delta precondition, Risk Register row 8).** The ledger
  currently writes `runId: "run-fallback"` (project memory `qrspi-batch-runid-datenow-bug`).
  Whether unique runIds are emitted at measurement time — or whether the ledger must be split by
  timestamp instead — is unverified and must be confirmed before any delta is trusted.
- **Which real ticket is the before/after subject (OQ3)** and whether re-running it twice
  through the design panel is acceptable is unspecified — a human-chosen input to Slice 3's
  measurement, not derivable from the design.
- **Fixture-assert placement (OQ4)** — whether the clean fixtures + PASS-assert wire into the
  opt-in teeth-eval workflow or live as a separate off-CI assertion is a human call; Slice 2
  builds the assert either way but the wiring target is unverified.
- **RUS-82 serialization (OQ5) — RESOLVED.** RUS-82 is now `blockedBy` RUS-79, so RUS-79 lands
  FIRST and RUS-82 rebases on the tuned prompt files afterward. No longer an open "which first".
- **Verification-coverage gap (Slice 3).** The automated guards exercise only the design panel:
  the teeth eval covers `{completeness, internal-consistency, edge-alignment}` (`simplicity`
  excluded) and the clean-eval covers the 4-lens design panel. `qrspi-critic.md` (generic edge
  critic) and `qrspi-coherence-critic.md` (implementation seam) have NO automated coverage, and
  `simplicity`'s catch-side is unproven. The plan turns this into a reviewer decision: tune only
  harness-covered lenses the evidence implicates, or back the unharnessed prompts with a manual
  `claude -p` probe + diff-review. Not resolvable in the structure; it depends on Slice 1's per-lens
  evidence.
- **Promotion of `evals/fixtures/design_rest_endpoint.md`** into the teeth set (Delta) is
  recommended-to-evaluate, not decided; whether it is genuinely clean enough to reuse is a
  judgment Slice 2 must make, not a settled fact.
