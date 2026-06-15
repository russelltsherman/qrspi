# Design — Critic calibration: anti-pass-bias prompt tuning (data-gated)

**Ticket:** RUS-79
**Research basis:** research.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Current State

The atomic critic verdict is `{ pass, findings }`, validated at the runner boundary against a schema; lens identity is attached by the orchestrator at the call site, not emitted by the critic (ref: Q1). The design panel fans out the four lens agents, tags each reply with its lens id, then reduces them to one round verdict via the synthesize worker before feeding the loop decision (ref: Q1). Panel aggregation is **strict unanimity** — one dissenting lens fails the round; there is no majority or quorum knob (ref: Q5). Because aggregation is unanimity, lowering any single lens's pass bar directly raises the panel fail rate, so the aggregation itself needs no change (ref: Q5).

Every one of the six pass/fail critic prompts (`qrspi-critic.md`, the four `qrspi-design-critic-*.md` lenses, and `qrspi-coherence-critic.md`) shares an identical section skeleton: frontmatter, role sentence, Inputs, What to do, the lens-scope section, Verdict schema, and a numbered Rules block (ref: Q3). Each already carries a "**Fail closed on doubt** … that is a finding — do not pass it on benefit of the doubt" rule and an edge-not-node framing — the anti-pass-bias lever RUS-79 targets is the prompt wording, not the loop or aggregation wiring (ref: Q3). The four design lenses also carry a `DIGEST_PATH`-in-place-of-`RESEARCH_PATH` instruction from the RUS-77 cost shape (ref: Q3, Q6).

The loop already fails closed on malformed input: any non-dict, missing, garbled, or unreadable verdict coerces to not-passed and never raises; a null agent reply aborts the step rather than passing (ref: Q7). The per-phase loop is hard-bounded by `maxRounds` (default 2): an always-fail critic costs at most `maxRounds` rounds, then `next_action` returns `cap_reached` (a terminal success) and the phase advances with residual findings spliced into the PR body — it cannot loop forever (ref: Q8). This is distinct from the unrelated `ciReviseCap` that bounds PR-CI-driven revises (ref: Q8).

RUS-78 instrumentation captures `{lens, pass, findingsCount}` per round into an append-only JSONL ledger at `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`, with a `runId` field for scoping (ref: Q2). The dissent base rate is **not stored** — it is computed on read by the summary script, where a round counts as dissent if `pass is False OR findingsCount > 0`, yielding `dissentRate` and `perLens.{lens}.dissentRate` (ref: Q2, Q12). No automated summarization runs in the orchestrator; the summary is produced on demand via `qrspi_critic_summary.py --run-id` (ref: Q12). There is **no committed baseline figure** to diff against (ref: Q12).

The `critics` config block resolves per-phase via a single tested resolver. It exposes `enabled`, `maxRounds`, design-only `lenses`/`candidates`/`digest`/`lensModel`/`gateBehindEdge`, and implementation-only `coherence` — but **no numeric pass-threshold or quorum knob** (ref: Q4). A prompt-only change needs no new config knob if it stays in the prompt files (ref: Q4).

The teeth eval binds three lenses to three unique marker strings (`completeness`→`AC-TEETH-COMPLETENESS`, `internal-consistency`→`TEETH-INCONSISTENCY`, `edge-alignment`→`frobnicate_widget()`); `simplicity` is not exercised (ref: Q9). A trial catches iff `pass is False` AND the lens marker appears as a substring of some finding; a lens passes iff caught ≥ majority threshold (ref: Q9). The CI regression gate runs verdict-parsing, panel-aggregation, metrics, summary, and teeth assert tests via `run_tests.py`; the teeth eval workflow itself is off CI (ref: Q10). There is **no clean/positive design fixture** — the only committed design fixture is the deliberately-flawed teeth one, so an anti-pass-bias change risks pass→fail false positives that no existing test would catch (ref: Q11).

## Desired End State

This ticket is **data-gated**: its first deliverable is a documented decision, not a code change. The end state branches on RUS-78's measured base rate.

- **AC — documented decision citing the measured base rate AND its sample size.** A decision document under `.qrspi/RUS-79/` records the RUS-78 `dissentRate` (overall and per-lens) **and the number of terminated critic steps it is computed over** (the sample size), then concludes among **three** outcomes, not two:
  1. **Dissent is appropriate** → close with that evidence, no prompt change (the data-driven null result) (ref: Q12).
  2. **Critics are measurably lenient in a way prompt wording can move** → tune the prompts (the AC below).
  3. **Critics are measurably lenient but the cause is structural, not wording** — the lenses faithfully confirm upstream *fidelity/traceability* and have no doubt to act on (no codebase access, edge-not-node framing) — → prompt-tuning is the wrong instrument; close RUS-79 as "not the right lever" and defer to **RUS-82** (the sibling node-lens + code-access theory in the RUS-77 family). See Decision 3.
  Because no committed baseline exists, this requires first running the summary CLI over the existing ledger; and because the sample is currently tiny (only the RUS-78 / RUS-81 / RUS-79 ledgers exist), the decision is **not binding until a human confirms the sample is large enough** (OQ1).
- **AC — if warranted, prompts tuned toward "default to fail if uncertain."** Edits land only in the six `.claude/agents/*critic*.md` files. Each tuned prompt sharpens the existing "fail closed on doubt" rule into explicit adversarial framing and adds an instruction that any `pass:false` MUST carry a concrete finding (ref: Q3, addresses the latent schema/prompt gap in Inconsistencies). No config knob is added — the ticket also permitted "threshold knobs in the `critics` config", but this design **deliberately declines** that allowance: under strict-unanimity aggregation a per-lens prompt change already moves the panel fail rate, so a quorum/threshold knob would be redundant scope (ref: Q4, Q5).
- **AC — teeth eval still passes.** Each owning lens still fails the flawed fixture AND still cites its exact marker substring; wording changes must preserve marker citation (ref: Q9).
- **AC — no regression toward noise.** A known-clean design fixture (new, since none exists) is run through the panel before and after; the panel still converges without fabricated findings (ref: Q11).
- **AC — dissent base rate measurably moves.** Two `runId`-scoped summaries (before/after) over the same real ticket show `dissentRate` moving in the intended direction (ref: Q2, Q12).
- **Constraint — prompt-only + reuse RUS-78 path.** No critic-loop restructuring, no new measurement path, and the RUS-77 cost shape (digest / lensModel / gating) is preserved; the `DIGEST_PATH` instruction stays verbatim in every design lens (ref: Q6).

## Delta

- **New file — `.qrspi/RUS-79/calibration-decision.md`** (committed in the design/plan phase as the gating artifact): records the before-baseline `dissentRate` from the summary CLI and the warranted/not-warranted call.
- **Modified files (only if warranted) — the six critic prompts** `.claude/agents/qrspi-critic.md`, `qrspi-design-critic-completeness.md`, `qrspi-design-critic-internal-consistency.md`, `qrspi-design-critic-edge-alignment.md`, `qrspi-design-critic-simplicity.md`, `qrspi-coherence-critic.md`: tune the Rules block toward adversarial framing and add the "fail MUST carry a finding" rule. Preserve frontmatter, the Verdict schema contract, the lens-scope sentence, the input-path enumeration, and the `DIGEST_PATH` instruction verbatim (ref: Q3, Q6).
- **New fixtures — a clean-design set under `evals/teeth/`** (≥3: a plainly-clean design plus at least one *clean-but-deferring* design that legitimately defers scope), each with any sibling clean upstream files it needs, that the panel should PASS. Before authoring from scratch, evaluate **promoting the existing clean `evals/fixtures/design_rest_endpoint.md`** (today bound to the non-functional placeholder harness, not the teeth assert) into the teeth set, to cut the "must be crafted genuinely clean" risk (ref: Q11).
- **New test/assert — a clean-fixture catch-inverse assertion** reusing the teeth harness math: assert the panel converges (no fail, no fabricated findings) on the clean fixture (ref: Q9, Q11).
- **No code changes** to `qrspi-batch.js`, the synthesize/loop/summary/config Python, or any `critics` config schema (ref: Q4, Q5, Q6).
- **New procedure (no code)** — run `qrspi_critic_summary.py --run-id` before and after against the same real ticket to capture the delta (ref: Q12). **Precondition:** the before/after runs must land **distinct** `runId`s. The ledger currently shows runs writing `runId: "run-fallback"` (the `Date.now`/`randomUUID` fallback, project memory `qrspi-batch-runid-datenow-bug`); two `run-fallback` lines share a scope key and cannot be separated by `--run-id`. Confirm unique runIds are being emitted before trusting the delta, or scope the two summaries another way (e.g. split the ledger by timestamp).

## Pattern Decisions

### Decision 1: How to detect over-correction (pass→fail false positives)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Add a positive clean-design fixture + a panel-PASSES assertion mirroring the teeth harness | Reuses the existing teeth/assert pattern (ref: Q9); gives an automated guard the repo currently lacks (ref: Q11); off-CI like teeth, so no flaky-LLM CI risk | New fixture must be crafted genuinely clean; lens-LLM nondeterminism means it is a majority assert, not a hard gate |
| B | Rely solely on the manual before/after dissent-rate delta on a real ticket | Zero new fixtures; uses the RUS-78 ledger path directly (ref: Q12) | No reusable regression guard; dissent rate moving up cannot distinguish "caught real defects" from "fabricated noise" — exactly the noise the AC forbids |

**Recommendation:** Option A (with Option B's delta run kept as the AC-mandated measurement). Use **multiple** clean fixtures (≥3, spanning a plainly-clean design plus at least one *clean-but-deferring* design that legitimately says "defensible deferral" — the case most at risk of becoming false-positive noise), not one, and define a **noise bound** the post-tune panel must stay under (e.g. zero fabricated findings across the clean set on a majority of trials). A single fixture cannot characterize distributional noise, which is this change's predicted failure mode (see Decision 3 Option A cons).
**Rationale:** The AC explicitly demands "no regression toward noise … verified via a before/after run" on a known-clean artifact, and research confirms no such fixture exists (ref: Q11). Extending the teeth harness — the established off-CI lens-behavior guard (ref: Q9, Q10) — is the in-pattern way to add it. Dissent rate alone (B) is necessary for the "measurably moves" AC but insufficient for the "no noise" AC, since a higher rate is ambiguous (ref: Q12, Inconsistencies).
**NEW PATTERN?** No — it is the inverse of the existing teeth catch-rule (assert PASS instead of CATCH), built on the same `qrspi_teeth_assert.py` math and fixture directory (ref: Q9, Q11).

### Decision 2: Where the adversarial framing lives and how uniformly to apply it

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Sharpen the existing "fail closed on doubt" rule in-place in each prompt's Rules block + add "fail MUST carry a finding" | Minimal, surgical; preserves the shared skeleton and all input-path/digest contracts (ref: Q3, Q6); honors the prompt-only constraint | Six files edited; risk of per-file drift if not applied uniformly |
| B | Add a new standalone "Adversarial stance" section to each prompt | More visible/explicit | Diverges from the shared section skeleton (ref: Q3); larger prompts may interact with cost shape (ref: Q6) and add maintenance surface |

**Recommendation:** Option A.
**Rationale:** Every critic already carries the fail-closed rule and a uniform skeleton (ref: Q3); the lever is wording, not structure (ref: Discovered Patterns). Tightening the existing rule keeps the byte-level contracts (Verdict schema, input paths, `DIGEST_PATH`) intact, which Q6 flags as mandatory. The added "fail MUST carry a finding" rule directly closes the latent schema/prompt gap where a fail can ship zero actionable findings (ref: Q7, Inconsistencies).
**NEW PATTERN?** No — it edits prose inside the established prompt skeleton (ref: Q3).

### Decision 3: Whether prompt wording is the correct lever at all (wording vs structural leniency)

The ticket assumes leniency is a *wording* problem fixable by an adversarial "default to fail if uncertain" framing. A competing hypothesis in the same RUS-77 family (RUS-82) holds that the lenses rubber-stamp because they judge **fidelity/traceability** (does the artifact derive from its upstream?) rather than **validity/correctness** (is the upstream itself any good?) — a structural limit (no codebase access, edge-not-node framing), not a tone one. The two are not distinguishable from a pass-rate alone: this ticket's own ledger shows the design panel passing 4/4 lenses with 0 findings on *this very design*, which fits both stories.

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Treat leniency as purely a wording problem; tune unconditionally when the base rate is high | Simplest; matches the ticket's literal framing | A fidelity-critic has **no uncertainty to trip** — "fail if uncertain" then either no-ops or manufactures fidelity objections on clean-but-deferring artifacts (the "defensible deferral" pass-bias the ticket cites becomes noise), the exact regression the noise AC forbids |
| B (recommended) | Gate the tune behind a *qualitative* read of the base-rate evidence: tune only when the missed dissents are ones sharper wording could plausibly have caught; if the misses are validity/correctness gaps the lens structurally cannot see, take outcome 3 (defer to RUS-82) | Keeps RUS-79 from spending its one prompt-tuning shot on a cause it cannot fix; makes the null-for-the-right-reason outcome explicit | Requires human judgment on the evidence, not just a threshold; couples the decision to RUS-82's existence |

**Recommendation:** Option B. The before-baseline analysis must **classify** the observed leniency, not just measure its rate — wording-addressable misses justify the tune; structural misses are RUS-82's domain.
**Rationale:** Closing a pass-bias bug with a wording change that cannot create doubt where the critic has none is circular; the design must first establish that the leniency is of a kind wording can move (ref: Q3, Inconsistencies; sibling RUS-82).
**NEW PATTERN?** No — it is a decision-gating step on the existing calibration-decision artifact, not new machinery.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Acting before RUS-78 data confirms leniency — fixing an unconfirmed problem | med | high | Gate hard on the calibration-decision artifact; do not edit prompts until the summary CLI shows measurable leniency; close as null if not (ticket Why-Now; ref: Q12) |
| Anti-pass-bias over-corrects into noise (clean artifacts now fail) | med | high | Add clean-design fixture + panel-PASSES assert (Decision 1); run the before/after on a real ticket; reject if clean fixture starts failing (ref: Q11) |
| Wording change breaks teeth eval (lens stops citing its marker) | med | high | Preserve each lens's ability to fail AND cite its exact marker substring; re-run the teeth eval after editing (ref: Q9) |
| Editing prompts disturbs the RUS-77 cost shape (drops `DIGEST_PATH` / input-path lines) | low | med | Treat input-path enumeration and the `DIGEST_PATH`-in-place-of-`RESEARCH_PATH` instruction as verbatim-preserve regions; diff-review each file (ref: Q6) |
| "Measurably moves" is unfalsifiable without a baseline number | high | med | Capture and commit the before-baseline `dissentRate` in the decision artifact before any edit; scope both runs by `runId` (ref: Q2, Q12) |
| A stricter fail yields fails with no actionable findings (schema permits empty findings on fail) | med | med | Add the explicit "every `pass:false` MUST carry a concrete finding" prompt rule (Decision 2; ref: Q7, Inconsistencies) |
| Leniency's cause is **structural** (fidelity-not-validity), so prompt-tuning is a no-op or a noise source | med | high | Decision 3 Option B: classify the missed dissents in the base-rate analysis; if they are validity gaps the lens cannot structurally see, take outcome 3 (defer to RUS-82), do not tune |
| before/after runs collide on `runId: "run-fallback"` so the delta cannot be computed | high | med | Confirm unique runIds are emitted (project memory `qrspi-batch-runid-datenow-bug`) before measuring, or split the ledger by timestamp (Delta measurement precondition) |
| RUS-82 edits the SAME six panel prompt files concurrently → merge collision / contradictory tuning of the shared fail-closed rule | med | med | Coordinate ordering with RUS-82 (project memory: the two must serialize); land one before the other touches the lens prompts (OQ5) |

## Open Questions

- OQ1 **(binding gate):** Has RUS-78's instrumentation run across enough real phases to produce a meaningful base rate yet? Only **three** committed ledgers exist today (RUS-78, RUS-81, RUS-79), so the sample is currently **too small to bind the calibration decision**. The ticket forbids entering on unconfirmed data; record the actual `dissentRate` and sample size in `calibration-decision.md` and have a human confirm sufficiency **before** any prompt edit (ref: Q12).
- OQ2: What is the concrete "intended direction and magnitude" threshold for "dissent base rate measurably moves" — e.g. a minimum absolute delta in `dissentRate`? The AC is directional only; a human should set the bar against the observed baseline (ref: Q12).
- OQ3: Which real ticket is the agreed-upon before/after subject, and is re-running the same ticket through the design panel twice acceptable (it appends two `runId`-scoped ledger lines)? (ref: Q2, Q11).
- OQ4: Should the clean-design fixtures and their PASS-assertion be wired into the opt-in teeth-eval workflow run, or live as a separate off-CI assertion? Both are off-CI by the lens-nondeterminism convention; the human owns this placement call (ref: Q10, Q11).
- OQ5: RUS-79 and RUS-82 both edit the six panel prompt files; project history says they must serialize. Which lands first, and how is the other rebased to avoid contradictory tuning of the same `fail-closed` rule? (sibling RUS-82; RUS-77 family).
