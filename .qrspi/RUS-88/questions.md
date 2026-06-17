# Questions — Retire the fidelity-only edge critic (qrspi-critic / runCriticLoop)

**Ticket:** RUS-88
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `runPhase` route between the panel loop and the edge-critic loop, and what is the exact conditional (`lenses?.length ? runCriticPanelLoop : runCriticLoop`) currently present in the source after RUS-84's restructuring of that line?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase`)
- Q2: What inputs does `runCriticLoop` receive (upstream artifact, produced artifact, phase identity) and what does it return to its caller, so the removal point and the caller's expected return contract are known?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runCriticLoop` and its callers)
- Q3: Where in `doImplementation` is the per-slice `qrspi-critic` invocation wired into the slice-diff flow, and what data (slice diff, upstream contract) is passed into it?
  **Target:** `.claude/workflows/qrspi-batch.js` (`doImplementation`)

## API Surface

- Q4: What is the full set of call sites of `runCriticLoop` and the `qrspi-critic` agent/skill across the workflow and scripts, so every reference can be accounted for at removal?
  **Target:** `.claude/workflows/qrspi-batch.js`, `.claude/agents/qrspi-critic.md`, the `qrspi-critic` skill directory
- Q5: How is `gateBehindEdge` defined, read, and consumed, and which functions or config keys reference it?
  **Target:** the module(s) responsible for the `gateBehindEdge` cost lever (`qrspi-batch.js`, `scripts/qrspi_critics_config.py`)
- Q6: What does `DEFAULT_CRITIC_PHASES` enumerate in `scripts/qrspi_critics_config.py`, and which entries correspond to the edge critic (questions/research/structure/plan) versus the design panel?
  **Target:** `scripts/qrspi_critics_config.py`

## State Management

- Q7: How does `scripts/qrspi_critics_config.py` resolve per-phase critic configuration (enabled flags, lenses, gateBehindEdge), and which keys in `.qrspi/config.json` / `.qrspi/config.example.json` feed it?
  **Target:** `scripts/qrspi_critics_config.py`, `.qrspi/config.example.json`
- Q8: How is the design critic panel (and its four lenses including `edge-alignment`) configured and resolved separately from the edge critic, so the boundary that must stay byte-for-byte unaffected is identified?
  **Target:** `scripts/qrspi_critics_config.py`, `.claude/workflows/qrspi-batch.js` (`runCriticPanelLoop`)

## Edge Cases

- Q9: When a planning phase has no `lenses` configured, what is the current fallback behavior, and what code path executes if neither a panel nor `runCriticLoop` runs (the "ungated" path)?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase` routing branch)
- Q10: Does any caller of `runCriticLoop` depend on a pass/fail verdict to gate advancement, retry, or block persistence — i.e., does removal leave any phase that previously could fail now always proceeding?
  **Target:** `.claude/workflows/qrspi-batch.js` (`runPhase`, `doImplementation` and their callers)
- Q11: How is the `qrspi-coherence-critic` whole-stack pass invoked at the planning→implementation seam, and is it independent of `runCriticLoop` such that removing the edge critic leaves it intact?
  **Target:** the module responsible for the coherence-seam pass (`qrspi-batch.js`, `qrspi-coherence-critic`)

## Testing

- Q12: Which `scripts/*_test.py` files assert edge-critic / `gateBehindEdge` behavior, and which assert design-panel and coherence config resolution, so the right tests are removed and the right ones are preserved?
  **Target:** `scripts/*_test.py` (notably the critics-config test sibling)
- Q13: How does `scripts/run_tests.py` discover and aggregate the `_test.py` suite, so removed test files and new ungated-routing assertions register correctly in the regression gate?
  **Target:** `scripts/run_tests.py`

## Observability

- Q14: What logging, recorded results, or run-summary output does `runCriticLoop` (and the per-slice critic) currently emit, and what result entries would disappear from a batch run once the edge critic is removed?
  **Target:** `.claude/workflows/qrspi-batch.js` (critic-loop result/logging emission)
