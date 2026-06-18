# Structure Outline — Bring the /review-* on-demand review family up to manual-review depth

**Design basis:** design.md @ 2026-06-18T01:00:00Z
**Generated:** 2026-06-18T01:30:00Z
**Revised:** 2026-06-18 — plan-review corrections (code-verified, mirrors plan.md): the review panels are NEW ordered `DEFAULT_REVIEW_{DESIGN,PLAN,IMPL}_LENSES` constants — the design one is NOT the batch `DEFAULT_DESIGN_LENSES` (four lenses, excludes node-validity `design-review` per RUS-82); plan/impl lens ids are phase-qualified (`plan-fidelity`/`impl-fidelity`/…) so they compose to real agent names and don't collide in the bare-lens-keyed metrics summary; the regression fixture reuses the existing `design_dropped_criterion_broken.md`. All five Unverified Assumptions are resolved by the plan phase (see that section).
**Status:** draft

## New Types

These are not language types (the codebase is Python stdlib CLIs + Markdown agents/skills);
they are the data-shape contracts that flow between the lens fan-out, reducers, synopsis
helper, and ledger.

- `LensVerdict { lens: str, pass: bool, findings: [str], nonBlockingNotes: [str] }` — one lens's
  output element in the pre-reduction verdict array. `nonBlockingNotes` is the NEW advisory channel
  (Decision 4); reducers pass it through untouched.
- `DecisionReadinessVerdict { lens: "decision-readiness", blockingDecisions: [{question: str, rationale: str}], answerable: [{question: str}] }` —
  the terminal-advisory output (Decision 5); partitioned OUT of the array fed to
  `qrspi_critic_synthesize.py` so it never drives a `revise` round.
- `SynopsisModel { axes: [{lens: str, pass: bool, blockingCount: int}], nonBlocking: [str], decisionReadiness: [{question, rationale}], terminalAction: str }` —
  the honest, axis-enumerated synopsis input (replaces the hand-composed prose keyed only on
  terminal action).
- `RiserInput { PHASE: "design"|"plan"|"impl", OUTPUT_PATH: <scratch-verbatim>, RESIDUAL_FINDINGS: [str], ...named PATH inputs }` —
  the single shared `qrspi-critic-reviser` invocation contract (phase-parameterized).

## Modified Types

- `critic-metrics.jsonl` row — add OPTIONAL additive fields: `nonBlockingNotes: [str]` per round,
  and `axes: [{lens, pass, blockingCount}]` (ref: design.md §Delta, OQ4). Reader
  (`qrspi_critic_summary.summarize`) already accesses fields via `.get()` with defaults, so new
  keys are backward-compatible; the row's `rounds[]` already carries per-lens
  `{lens, pass, findingsCount}`.
- `qrspi_critics_config.py` — add the ordered review panels `DEFAULT_REVIEW_DESIGN_LENSES`
  (`completeness`, `internal-consistency`, `edge-alignment`, `simplicity`, `design-review`),
  `DEFAULT_REVIEW_PLAN_LENSES` (`plan-review`, `plan-fidelity`, `plan-completeness`),
  `DEFAULT_REVIEW_IMPL_LENSES` (`impl-review`, `impl-fidelity`, `impl-completeness`), plus the
  allow-list sets `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES` (mirroring `KNOWN_DESIGN_LENSES`)
  (ref: design.md Decision 2; plan.md Slice 1 step 1). **The review design panel is DISTINCT from
  the batch `DEFAULT_DESIGN_LENSES`** (four lenses; deliberately excludes node-validity
  `design-review` per RUS-82) — it adds `design-review` because that is the only lens
  `/review-design` runs today. Plan/impl lens ids are PHASE-QUALIFIED so `qrspi-<phase>-critic-<id>`
  resolves to a distinct agent and the ids do not collide in the bare-lens-keyed
  `qrspi_critic_summary` per-lens summary.
- `TICKET_CONTENT_PATH` — already-declared optional lens input on the design/impl node-validity
  lenses; now ACTUALLY passed by the skills, and newly declared on the fidelity/completeness/
  decision-readiness lenses (ref: Decision 6). Node-validity lens stays research+code-only.

## Contracts

- `DEFAULT_REVIEW_{DESIGN,PLAN,IMPL}_LENSES: tuple[str]` (in `qrspi_critics_config.py`) — the
  ordered per-phase review panels the `/review-*` skills fan out; `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES`
  are the matching allow-list `set`s. Lens id → agent is `qrspi-<phase>-critic-<lens-id>`; ids are
  phase-qualified for plan/impl (`plan-fidelity`, `plan-completeness`, `impl-fidelity`,
  `impl-completeness`), bare for the design edge lenses (only design emits them).
- `render_synopsis(verdictArray: [LensVerdict], decisionReadiness: DecisionReadinessVerdict, terminalAction: str) -> str` —
  NEW synopsis helper; renders axis enumeration + per-lens pass + advisory non-blocking section +
  decision-readiness section. Source is the PRE-reduction per-lens verdict array (the reduced
  `{pass, findings}` alone is insufficient — ref: design.md §Delta "Axis-enumeration source").
- `ledger_row_fields(verdictArray: [LensVerdict]) -> dict` — NEW helper deriving the optional
  additive `critic-metrics.jsonl` fields from the same verdict array.
- `partition_decision_readiness(verdictArray) -> (panelArray, decisionReadinessVerdict)` —
  splits the decision-readiness lens output out of the array fed to synthesize (Decision 5).
- `qrspi-critic-reviser` agent contract — accepts `PHASE` input; writes ONLY to `OUTPUT_PATH`
  (scratch-verbatim); propose-only (no tracked path / branch write); receives `RESIDUAL_FINDINGS`
  (node-validity/fidelity findings ONLY — decision-readiness excluded).
- Each new lens agent — emits `LensVerdict`; fidelity/completeness lenses must produce a *named
  descoping/deviation counter-example* OR an affirmative "no AC narrowed, checked: <list>"
  (Risk Register adversarial contract); default `pass:false` under uncertainty (fail-closed).

## Slice 1: Per-phase lens config + synopsis/ledger helpers (the tested pure core)

**Goal:** All NEW pure-Python machinery the skills will call lands with passing unit tests,
independently verifiable via `run_tests.py` before any agent or skill is touched. Delivers:
plan/impl lens allow-lists, the decision-readiness partition, the axis-enumerated synopsis
renderer, and the additive ledger fields — each `_test.py`-covered.
**Files touched:**

- ⚠️ `scripts/qrspi_critics_config.py` — add `DEFAULT_REVIEW_{DESIGN,PLAN,IMPL}_LENSES` ordered panels + `KNOWN_PLAN_LENSES`/`KNOWN_IMPL_LENSES` allow-list sets (design panel ≠ batch `DEFAULT_DESIGN_LENSES`)
- ⚠️ `scripts/qrspi_critics_config_test.py` — cover the new constants/defaults
- ✨ `scripts/qrspi_review_synopsis.py` — `render_synopsis()` + `partition_decision_readiness()` + `ledger_row_fields()`
- ✨ `scripts/qrspi_review_synopsis_test.py` — axis enumeration, non-blocking passthrough, decision-readiness partition, ledger fields
- ⚠️ `scripts/qrspi_critic_summary.py` — confirm `.get()`-lenient read of new optional fields (only if a gap exists; else no change)
- ⚠️ `scripts/qrspi_critic_summary_test.py` — assert old rows (without new keys) still parse + new fields surface

**Verification:**
- [ ] `python3 scripts/run_tests.py` is green (new + existing tests)
- [ ] `python3 scripts/run_tests.py critic` and `... synopsis` pass in isolation
- [ ] A fixture old-style metrics row (no `nonBlockingNotes`/`axes`) still parses (backward-compat assertion)
**Context cost:** M
**Depends on:** none

## Slice 2: The shared non-producer reviser + the five new lens agents

**Goal:** All NEW `.claude/agents/` markdown agents exist, authored via skill-creator, with
triggering validated. Delivers the single phase-parameterized `qrspi-critic-reviser` and the
five new lenses (plan fidelity+completeness, impl fidelity+completeness, design
decision-readiness). Each fidelity/completeness lens enforces the adversarial counter-example
contract and fail-closed default.
**Files touched:**

- ✨ `.claude/agents/qrspi-critic-reviser.md` — shared non-producer adversarial reviser (PHASE-parameterized; OUTPUT_PATH=scratch-verbatim; propose-only)
- ✨ `.claude/agents/qrspi-plan-critic-plan-fidelity.md` — ticket-grounded plan fidelity lens (id `plan-fidelity`)
- ✨ `.claude/agents/qrspi-plan-critic-plan-completeness.md` — plan completeness lens (id `plan-completeness`; every AC + answered question covered)
- ✨ `.claude/agents/qrspi-impl-critic-impl-fidelity.md` — ticket-grounded impl fidelity lens (id `impl-fidelity`)
- ✨ `.claude/agents/qrspi-impl-critic-impl-completeness.md` — impl completeness lens (id `impl-completeness`)
- ✨ `.claude/agents/qrspi-design-critic-decision-readiness.md` — non-producer decision-readiness lens (replaces self-grading open-question pass)

**Verification:**
- [ ] skill-creator eval/authoring loop run per agent (per MEMORY directive — never ship a SKILL/agent ad-hoc)
- [ ] Triggering validated with direct `claude -p` routing probes in the real repo (sandbox run_eval invalid — ref: design.md Risk Register / MEMORY)
- [ ] Each lens emits a `LensVerdict`-shaped result; fidelity/completeness lenses produce a named counter-example OR an affirmative per-AC checklist (manual probe over a deliberately-descoped sample)
- [ ] Reviser writes ONLY to OUTPUT_PATH and leaves no tracked-path/branch mutation (manual probe)
**Context cost:** L
**Depends on:** none (parallelizable with Slice 1; both are inputs to Slice 3)

## Slice 3: Upgrade /review-design end-to-end (the reference wiring)

**Goal:** `/review-design` runs the FULL design panel (`design-review` + `edge-alignment` +
`completeness` + `internal-consistency` + `simplicity`), passes `TICKET_CONTENT_PATH` to the
fidelity/completeness/decision-readiness lenses, partitions decision-readiness out of the
synthesize array, swaps the reviser to `qrspi-critic-reviser`, and renders the honest
axis-enumerated synopsis with a non-blocking section. This is the first fully-wired phase and
the template the other two skills follow.
**Files touched:**

- ⚠️ `.claude/skills/review-design/SKILL.md` — full-panel fan-out; `TICKET_CONTENT_PATH` plumbing (fetch/stage ticket text); Step 4a verdict array → `qrspi_critic_synthesize.py`; replace Step 5 with decision-readiness lens; `qrspi-critic-reviser` swap; widened synopsis via `qrspi_review_synopsis.py`
- ⚠️ (read-only ref) `.claude/agents/qrspi-critic-reviser.md` — consumed, not modified

**Verification:**
- [ ] End-to-end `/review-design` run over an existing ticket's design PR posts an axis-enumerated synopsis listing all five lenses + per-lens pass + non-blocking section
- [ ] PR head SHA identical before/after (propose-only invariant — ref: design.md Q6/Q15)
- [ ] Decision-readiness blocking items appear in the synopsis but trigger NO reviser round
- [ ] `TICKET_CONTENT_PATH` is passed to fidelity/completeness/decision-readiness lenses ONLY (node-validity lens unchanged)
**Context cost:** L
**Depends on:** Slice 1, Slice 2

## Slice 4: Upgrade /review-plan and /review-implementation

**Goal:** The plan and impl single-phase skills spawn their new multi-lens panels (sourced from
`DEFAULT_REVIEW_PLAN_LENSES` / `DEFAULT_REVIEW_IMPL_LENSES`), pass the ticket, swap to the shared reviser, and
render the honest synopsis — following the Slice 3 template. Also aligns
`/review-implementation` frontier resolution with `/review`'s `gh pr list --state all` guard
(Risk Register: partially-landed-stack misfire).
**Files touched:**

- ⚠️ `.claude/skills/review-plan/SKILL.md` — multi-lens panel; ticket plumbing; reviser swap; widened synopsis
- ⚠️ `.claude/skills/review-implementation/SKILL.md` — multi-lens panel; ticket plumbing; reviser swap; widened synopsis; `--state all` frontier guard

**Verification:**
- [ ] `/review-plan` run posts an axis-enumerated synopsis with the plan panel lenses + per-lens pass
- [ ] `/review-implementation` run posts the rolled-up synopsis to the top slice PR; frontier resolved via `--state all` (no partially-landed misfire)
- [ ] Both: PR head SHA unchanged before/after (propose-only)
- [ ] Both: ticket passed to fidelity/completeness lenses only
**Context cost:** M
**Depends on:** Slice 1, Slice 2, Slice 3

## Slice 5: Upgrade whole-stack /review + author the regression fixture

**Goal:** `/review` composes the upgraded per-phase panels in its binding table and renders the
honest per-phase synopsis sub-sections. The regression anchor REUSES the existing
`evals/fixtures/design_dropped_criterion_broken.md` (an independently-authored design that
silently drops the "403 unless admin" AC), and running the upgraded design panel lenses over it
(a lens-level probe — a static fixture is not a live PR) surfaces the dropped AC as a blocking
finding (no clean pass) — closing the regression AC (OQ5).
**Files touched:**

- ⚠️ `.claude/skills/review/SKILL.md` — bind upgraded per-phase panels; honest per-phase synopsis sub-sections; one ledger row per phase
- ✨ REUSE `evals/fixtures/design_dropped_criterion_broken.md` (DASH-417; independently authored, drops "403 unless admin") as the regression anchor — NOT a new fixture (avoids duplication; non-circular per OQ5). Add a minimal `ticket_dropped_criterion.md` only if no ticket fixture states the four ACs.
- ⚠️ `evals/fixtures/README.md` — provenance-table row documenting the reused fixture (+ any added ticket fixture)

**Verification:**
- [ ] `/review <id>` over a ticket with a frontier PR posts ONE rolled-up synopsis with per-phase sub-sections, each axis-enumerated; one ledger row per phase
- [ ] PR head SHA unchanged (propose-only across the whole stack)
- [ ] Running the upgraded design panel lenses over `evals/fixtures/design_dropped_criterion_broken.md` (+ ticket fixture) surfaces the dropped "403 unless admin" AC as a blocking finding (lens-level probe)
- [ ] `python3 scripts/run_tests.py` still green
**Context cost:** M
**Depends on:** Slice 1, Slice 2, Slice 3, Slice 4

---

## Unverified Assumptions

These were claims from design.md that the Structure phase could not map to a concrete,
named file/symbol from the cited research. **All five are now RESOLVED by the plan phase**
(plan.md read the cited code/skills directly); the resolutions are recorded inline below.

1. **Exact name and current signature of the synthesize/loop CLIs and the `critic-metrics.jsonl`
   reader.** The design names `qrspi_critic_synthesize.py`, `qrspi_critic_loop.py`, and
   `qrspi_critic_summary.summarize` (ref: Q2, OQ4), but the structure phase cannot read the
   codebase to confirm exact file paths, the `summarize` function signature, or that the row
   `rounds[]` literally carries `{lens, pass, findingsCount}`. Slice 1's `qrspi_critic_summary.py`
   edit may be a no-op if the reader is already lenient — confirm in the plan phase.
   **RESOLVED:** verified — `qrspi_critic_synthesize.synthesize`, `qrspi_critic_loop.next_action`,
   and `qrspi_critic_summary.summarize` exist as named; `summarize` reads every field via `.get()`
   (lenient) and buckets per-lens on the bare `rnd["lens"]`, so the Slice 1 reader edit is a no-op
   and additive `axes`/`nonBlockingNotes` fields are backward-compatible (plan.md Slice 1 steps 8, 34).

2. **How `/review-design` Step 4a / `/review` Step 3b currently fan out lenses.** The design calls
   these "the documented plug points" (Decision 1, ref: Q5) but the precise SKILL.md step
   structure (how the Agent tool is invoked, how the verdict array is currently assembled and
   piped) is not reproduced in design.md — the plan phase must read the four SKILL.md files to
   author exact edits.
   **RESOLVED:** verified — each skill's Step 4a hardcodes one `subagent_type` and SEPARATELY
   assembles a one-element verdict array `[{"lens":"<id>","pass":...,"findings":...}]` piped to
   `qrspi_critic_synthesize.py`; the fan-out derives `subagent_type` as `qrspi-<phase>-critic-<lens-id>`
   (lens `"design-review"` → `qrspi-design-critic-design-review`). The plan authors per-step edits
   against this structure (plan.md Slice 3 step 28, Slices 4–5).

3. **The mechanism to fetch/stage ticket text to `TICKET_CONTENT_PATH`.** The design says "the
   skills must fetch/stage the ticket text" (§Delta) but does not specify whether this reuses an
   existing Linear-fetch/stage helper or needs a new one. Per MEMORY (linear fetch is via
   `mcp__linear__get_issue`), but the staging path convention for review (`/tmp/phase-stage/<id>/review/`)
   and who writes the ticket file is unspecified — resolve in the plan phase.
   **RESOLVED:** the skill fetches via `mcp__linear__get_issue` and stages the ticket text to
   `TICKET_CONTENT_PATH` = `/tmp/phase-stage/<id>/review/ticket.md`, passed to the
   fidelity/completeness/decision-readiness lenses ONLY (plan.md Slice 3 step 30; Slice 4 steps 40, 45).

4. **Whether the impl panel's per-slice CI/stack aggregation interacts with the new impl lenses.**
   The design upgrades `/review-implementation` to a multi-lens panel and adds the `--state all`
   guard, but does not state whether the impl fidelity/completeness lenses run per-slice or over
   the aggregated stack. The plan phase must decide the impl lens input granularity.
   **RESOLVED:** the impl fidelity/completeness lenses run over the AGGREGATED slice stack (one
   panel pass), consistent with the existing single rolled-up synopsis to the top slice PR
   (plan.md Slice 4 step 44).

5. **`DEFAULT_DESIGN_LENSES` exact contents/location.** OQ1 resolution requires the
   `/review-design` panel to "match the batch `DEFAULT_DESIGN_LENSES`," but the structure phase
   cannot confirm that constant's name/location or that it equals the five named lenses. The plan
   phase must verify the batch default to avoid panel drift.
   **RESOLVED — and the design's premise was WRONG.** Verified: `DEFAULT_DESIGN_LENSES =
   ["completeness", "internal-consistency", "edge-alignment", "simplicity"]` is FOUR lenses and
   DELIBERATELY excludes node-validity `design-review` (RUS-82 decoupling; "Do NOT re-couple"
   comment in the file). So the `/review-design` panel does NOT "match the batch
   `DEFAULT_DESIGN_LENSES`": it must be a NEW ordered `DEFAULT_REVIEW_DESIGN_LENSES` adding
   `design-review` (the only lens `/review-design` runs today). Plan/impl lens ids are
   phase-qualified to compose to real agents and avoid the bare-lens-keyed metrics collision
   (plan.md Slice 1 step 1; this corrected the original panel-source contradiction).
