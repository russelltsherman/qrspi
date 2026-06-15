# Questions — Critic calibration: anti-pass-bias prompt tuning (data-gated)

**Ticket:** RUS-79
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Data Flow

- Q1: What does a critic verdict object contain end-to-end (pass/fail flag, findings, lens identity, dissent signal), and how does it flow from a single critic agent invocation back through the orchestration into a panel-level decision?
  **Target:** `.claude/agents/qrspi-critic.md` and the module responsible for collecting critic verdicts (`runCriticLoop` in `.claude/workflows/qrspi-batch.js`)
- Q2: How does the RUS-78 instrumentation record the dissent base rate — what fields are captured per verdict, where are they written, and in what format — so this ticket can reuse that path to measure a before/after delta?
  **Target:** the module/script responsible for RUS-78 critic instrumentation (locate where dissent/pass-rate measurements are emitted)

## API Surface

- Q3: What is the exact set of critic agent prompt files in scope (`.claude/agents/qrspi-critic.md`, `qrspi-design-critic-*.md`, the slice and coherence critics), and what shared structure or section ordering do they have in common?
  **Target:** `.claude/agents/` (enumerate the qrspi-critic and qrspi-*-critic-* definition files)
- Q4: What threshold knobs exist in the `critics` config block, what keys and value ranges do they accept, and how are they read and applied at runtime?
  **Target:** `.qrspi/config.json` / `.qrspi/config.example.json` and the config-reading module (`scripts/qrspi_config.py`)

## State Management

- Q5: How is a panel-level pass/fail decision computed from individual lens verdicts — is it a majority, unanimity, or threshold rule — and where is that aggregation logic implemented?
  **Target:** the module responsible for panel verdict aggregation (`runCriticLoop` and any resolver/scoring helper it calls)
- Q6: How does the shared-digest / lens-model / gating cost-reduction shape from RUS-78 currently structure what each lens receives as input, so a prompt-only change can avoid disturbing it?
  **Target:** the module responsible for building the shared critic digest and dispatching per-lens invocations in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q7: How does the critic loop currently behave when a critic returns an ambiguous or malformed verdict (neither a clean pass nor a clearly-structured fail), and is there a defined default — and does that default currently lean pass or fail?
  **Target:** the verdict-parsing logic in `runCriticLoop` (`.claude/workflows/qrspi-batch.js`)
- Q8: What stops an adversarial "default to fail if uncertain" framing from producing a non-terminating revise loop — what bounds the number of critic-driven revise cycles per phase, and where is that bound enforced?
  **Target:** the revise-loop control logic in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve_state.py`
- Q9: How does the teeth eval define which lens "owns" which deliberately-flawed defect, and what majority threshold must each owning lens hit to pass — so a prompt change can be verified not to break that mapping?
  **Target:** the qrspi-teeth-eval workflow and `scripts/qrspi_teeth_assert.py` / `scripts/qrspi_teeth_assert_test.py`

## Testing

- Q10: What existing tests cover critic verdict parsing, panel aggregation, and the teeth-eval majority/marker math, and which of them run in the CI regression gate?
  **Target:** `scripts/*_test.py` (notably `scripts/qrspi_teeth_assert_test.py`) and `.github/workflows/tests.yml`
- Q11: How is a "known-clean artifact" before/after run performed today — is there a fixture of a previously-passed real design the panel can be re-run against, and where would such a fixture live?
  **Target:** the teeth-eval / critic fixtures directory and the qrspi-teeth-eval workflow definition

## Observability

- Q12: Where are critic verdicts and the dissent base rate surfaced for inspection (logs, recorded artifacts, a metrics file), and what is the unit of measurement RUS-78 emits that this ticket's "dissent base rate measurably moves" criterion would be evaluated against?
  **Target:** the RUS-78 instrumentation output sink (log/artifact path where per-verdict dissent data is recorded)
