# Questions — Holistic design critic: adversarial node-validity lens with codebase access

**Ticket:** RUS-82
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What inputs does `runCriticPanelLoop` currently assemble and thread into each design-critic lens spawn prompt (design.md, ticket, research.md, questions.md, and any shared digest), and at what point would a `CODEBASE_PATH` (worktree/repo root) value be available to splice in?
  **Target:** `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`
- Q2: How is the shared "digest" (from RUS-78) constructed and passed to the lenses today, and what is the mechanism by which an individual lens could opt out of the digest in favor of full research + source?
  **Target:** the digest-construction logic in `.claude/workflows/qrspi-batch.js` and the RUS-78 cost-lever code paths

## API Surface

- Q3: What is the exact `CRITIC_VERDICT_SCHEMA` shape (`{pass, findings}`) that every design-critic lens must emit, and where is it defined and consumed?
  **Target:** the module defining `CRITIC_VERDICT_SCHEMA` (referenced from `.claude/workflows/qrspi-batch.js` / `scripts/qrspi_critic_synthesize.py`)
- Q4: What frontmatter fields (notably `tools` and any model/seam key like `lensModel`) do the existing four design-critic agents declare, and what is the exact format for granting `Read` + `Grep` and a per-lens model override?
  **Target:** the existing lens agent files under `.claude/agents/` (`qrspi-design-critic-{completeness,internal-consistency,edge-alignment,simplicity}`)

## State Management

- Q5: Where is the default design lens set (`DEFAULT_DESIGN_LENSES`) defined, and how does the config resolver's whitelist (`KNOWN_DESIGN_LENSES`) gate which lenses `critics.design.lenses` may activate?
  **Target:** `scripts/qrspi_critics_config.py` and the `DEFAULT_DESIGN_LENSES` definition in `.claude/workflows/qrspi-batch.js`
- Q6: How does `scripts/qrspi_critic_synthesize.py` AND-reduce per-lens verdicts, and how does it currently determine the set of expected lenses for a round (so an added lens is counted in unanimity)?
  **Target:** `scripts/qrspi_critic_synthesize.py`

## Edge Cases

- Q7: How does the panel loop behave when unanimity is never reached — what does `maxRounds` / `cap_reached` do, and how does a perpetually-dissenting lens currently surface (ship via `cap_reached` vs block)?
  **Target:** the round-loop / `maxRounds` / `cap_reached` handling in `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`
- Q8: How does `runCriticPanelLoop` handle a lens that returns a malformed verdict, times out, or emits no `{pass, findings}` — does a missing verdict count as fail, pass, or abort?
  **Target:** the verdict-collection / error-handling path in `runCriticPanelLoop` and `scripts/qrspi_critic_synthesize.py`
- Q9: What distinguishes the design-keyed plumbing (agentType prefix `qrspi-design-critic-`, design input paths, "design-phase" prompt text) from anything reusable, given the ticket requires the lens prompt be authored phase-generically for a future plan-phase reuse?
  **Target:** the agentType-prefix and prompt-construction code in `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`

## Testing

- Q10: What pattern do the existing `scripts/*_test.py` tests use to assert lens-set membership, config-resolver whitelist acceptance, and synthesize behavior, so new wiring tests match the `python3 scripts/run_tests.py` gate?
  **Target:** `scripts/qrspi_critics_config_test.py`, `scripts/qrspi_critic_synthesize_test.py`, and `scripts/run_tests.py`
- Q11: How is a deliberately-flawed design fixture (e.g. under `evals/teeth/`) currently structured for the teeth eval, and what marker/assertion mechanism does `scripts/qrspi_teeth_assert.py` use to verify a lens caught its defect?
  **Target:** `scripts/qrspi_teeth_assert.py`, `scripts/qrspi_teeth_assert_test.py`, and the fixtures under `evals/teeth/`

## Observability

- Q12: What does `runCriticPanelLoop` record or emit per-lens per-round (verdicts, findings, instrumentation from RUS-78), and where would a new lens's blocking-vs-non-blocking-note distinction be visible in that output?
  **Target:** the per-lens logging / instrumentation emitted by `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`
