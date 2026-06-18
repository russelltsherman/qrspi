# Questions — Bring the /review-* on-demand review family up to manual-review depth

**Ticket:** RUS-91
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does each `/review-*` skill currently feed the artifact (design.md / plan.md / slice code) and the ticket text into its single node-validity lens, and at what point (if any) is the ticket made available to the lens prompt?
  **Target:** the `/review-design`, `/review-plan`, `/review-implementation` skill definitions under `.claude/skills/` and their agent definitions under `.claude/agents/`
- Q2: How do `qrspi_critic_synthesize.py` and `qrspi_critic_loop.py` ingest a set of lens verdicts, and what is the exact input/output contract (verdict array shape, AND-reduction) the ticket says these CLIs already implement?
  **Target:** `scripts/qrspi_critic_synthesize.py` and `scripts/qrspi_critic_loop.py`

## API Surface

- Q3: What is the full set of lens prompts in the existing design critic panel (`completeness`, `edge-alignment`, `internal-consistency`, `simplicity`, and the node-validity `qrspi-design-critic-design-review`), and how is each invoked?
  **Target:** the design critic panel lens prompt files under `.claude/agents/` (the `qrspi-design-critic-*` family)
- Q4: What lens prompts exist today for the plan and implementation phases, and which fidelity/completeness lenses are absent (the ticket states plan/impl have no fidelity/completeness lens at all)?
  **Target:** the `qrspi-plan-critic-*` and `qrspi-impl-critic-*` agent/lens definitions under `.claude/agents/`
- Q5: How does the whole-stack `/review` skill enumerate and compose the three per-phase lenses, and where would an upgraded multi-lens panel plug into that composition?
  **Target:** the `/review` skill definition under `.claude/skills/`

## State Management

- Q6: How does each `/review-*` skill enforce the propose-only invariant today (scratch-copy creation, PR head SHA unchanged, comment-only write), and where is the scratch copy created and torn down?
  **Target:** the module responsible for the scratch-copy review loop in the `/review-*` skills/agents
- Q7: How is the agreement-extended ledger row computed and written per review run, and what fields does a row record that an upgraded multi-lens/multi-phase synopsis would need to populate?
  **Target:** the module responsible for appending the review ledger row referenced by the `/review-*` skills

## Edge Cases

- Q8: On `revise`, where does each skill re-spawn the producing agent (`qrspi-design` / `qrspi-plan` / `qrspi-implement`), and what is the spawn interface a non-producer/adversarial reviser would have to satisfy to replace it?
  **Target:** the revise/reviser spawn path in the `/review-*` skills and agent definitions
- Q9: Where in `/review-design` is the open-question pass that spawns `qrspi-design` to answer the design's own open questions, and what determines whether an open question is reported as resolved versus blocking?
  **Target:** the open-question handling section of the `/review-design` skill/agent
- Q10: How does the current synopsis derive its verdict text (e.g. "Converged round 0, zero findings, pass"), and where is the blocking-only bar applied that dropped the real `critics_config` inaccuracy as non-blocking?
  **Target:** the synopsis-rendering / verdict-reduction logic invoked by the `/review-*` skills (and `qrspi_critic_synthesize.py`)
- Q11: For `/review-implementation`, how is the slice stack discovered and aggregated into a single rolled-up synopsis, and what happens when slices are partially landed or a slice is missing?
  **Target:** the slice-stack discovery logic in the `/review-implementation` skill/agent

## Testing

- Q12: What stdlib `_test.py` siblings currently cover `qrspi_critic_synthesize.py` / `qrspi_critic_loop.py`, and what verdict-array / AND-reduction cases do they assert that new lens wiring must keep passing?
  **Target:** `scripts/qrspi_critic_synthesize_test.py`, `scripts/qrspi_critic_loop_test.py`, and `scripts/run_tests.py`
- Q13: What artifacts exist for the RUS-86 / PR #347 regression case (the `design.md` with the retry-events and shared-log descoping), and where would a regression fixture for re-running the upgraded `/review-design` against it live?
  **Target:** the module responsible for review test fixtures / the RUS-86 design artifact referenced by the acceptance criteria

## Observability

- Q14: What does a `/review-*` run currently emit to the PR comment and to the ledger that records which quality axes were checked, so an "honest verdict" can state what was reviewed versus what remains open?
  **Target:** the synopsis comment writer and ledger-append module used by the `/review-*` skills
- Q15: How can a reviewer or operator confirm after a run that the propose-only invariant held — i.e. where is the before/after PR head SHA observable and which write operations are logged?
  **Target:** the propose-only verification / logging path in the `/review-*` skills
