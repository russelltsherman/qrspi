# Questions — Critic-layer effectiveness (instrumentation, cost, teeth, calibration)

**Ticket:** RUS-77
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the design-step input (research.md and the upstream artifact) reach each of the 4 design-panel lenses today — is the full ~36KB research.md passed verbatim to every lens, or is there any shared/derived digest already produced before fan-out?
  **Target:** the module responsible for the design panel fan-out (runCriticLoop and the design-step orchestration in `.claude/workflows/qrspi-batch.js`)
- Q2: What is the ordering and data hand-off between the 2 edge critics, the 4 panel lenses, and the 3 synthesize/decide steps (which step's output feeds which) within a single design step?
  **Target:** the critic-layer sequencing logic in `.claude/workflows/qrspi-batch.js` and the `qrspi-critic` skill definition

## API Surface

- Q3: What is the current input/output contract of the edge critic — what does it return on a passing critique, and is the `{pass, findings}` verdict shape consumed anywhere that would need to change to gate the panel behind the edge critic?
  **Target:** the `qrspi-critic` skill (`.claude/skills/qrspi-critic/`) and its caller in `.claude/workflows/qrspi-batch.js`
- Q4: How is the model selected for each critic lens currently — is the lens model a single hard-coded value, or is it already parameterized in a way that would allow a cheaper lens model per the cost-reduction goal?
  **Target:** the critic-spawn / model-selection logic in `.claude/workflows/qrspi-batch.js` and any `.qrspi/config.json` keys it reads

## State Management

- Q5: Where, if anywhere, are per-step critic outcomes (pass/fail, findings count, artifact changes, token usage) currently recorded or persisted after a design step completes?
  **Target:** the artifact-persistence path (`scripts/qrspi_persist.py`) and any run-level logging in `.claude/workflows/qrspi-batch.js`
- Q6: What configuration mechanism controls whether the critic layer (or individual lenses) runs, and does it support the nested keys an `implCriticCfg.enabled`-style gate would need?
  **Target:** the config reader (`scripts/qrspi_config.py`) and `parseConfigEnvelope` in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q7: What happens to the design step when a critic lens returns findings (a non-passing verdict) — is there an existing skip-on-failure / re-run / accumulate-residual path, and how is a failed Linear or persistence write during that path handled?
  **Target:** the critic-loop failure handling in `.claude/workflows/qrspi-batch.js` (the doImplementation slice-critic precedent for skip-on-failure)
- Q8: How does the layer behave if the shared digest (once introduced) is empty, truncated, or fails to generate — does any current code assume each lens always receives the full research.md?
  **Target:** the design-panel fan-out input assembly in `.claude/workflows/qrspi-batch.js`
- Q9: What is the current behavior when subagent token consumption is large (the ~749K-token first attempt) — is there any budget cap, timeout, or abort threshold on a critic step, or does it run unbounded?
  **Target:** the critic-step spawning and any limit/timeout handling in `.claude/workflows/qrspi-batch.js`

## Testing

- Q10: What is the existing pattern for a "teeth" / behavioral eval that asserts a critic fails on a flawed input, and where would a fixture of a deliberately-flawed design live relative to the current test harness?
  **Target:** `scripts/run_tests.py`, the `scripts/*_test.py` suite, and the `evals/` + `scripts/run_eval.py` placeholder
- Q11: How are critic-layer behaviors currently tested given that `qrspi-batch.js` is documented as harness-coupled and not unit-testable in isolation — what is the JS↔Python contract-fixture seam that a critic change would be verified against?
  **Target:** the JS↔Python contract fixtures referenced in `docs/testing-dynamic-workflows.md` and `scripts/`

## Observability

- Q12: What logging, counters, or run-summary output exists today that could carry critic base-rate metrics (pass/fail counts, findings counts, per-lens token usage), and what format does the batch run currently emit per ticket?
  **Target:** the run-result accumulation and reporting in `.claude/workflows/qrspi-batch.js` and any structured output it writes
