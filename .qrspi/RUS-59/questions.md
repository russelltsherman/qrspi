# Questions — Generation-side N-select for Design: N candidate designs → judge → synthesize

**Ticket:** RUS-59
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the Design phase currently flow from inputs (ticket, questions, research) to a single produced `design.md`, and at what point would an N-candidate generation step splice in before the existing critic panel?
  **Target:** `doDesign` and `runPhase` in `.claude/workflows/qrspi-batch.js`
- Q2: How are the per-candidate framing prompts (e.g. MVP-first / risk-first / simplest-thing) materialized and passed to each parallel design-agent run, and where would diverse framing variants be defined?
  **Target:** the Design agent prompt under `.claude/agents/` and the design-phase dispatch in `.claude/workflows/qrspi-batch.js`
- Q3: How does the synthesized winning `design.md` reach the staging path consumed by the critic panel, and how is staging handled today for the single-design path?
  **Target:** the `stg()` helper in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_persist.py`

## API Surface

- Q4: What is the existing critic-panel entry contract (`runCriticPanelLoop` / `runCriticLoop`) that an N-select stage must produce a single `design.md` for, and what shape does it expect?
  **Target:** `runCriticPanelLoop` and `runCriticLoop` in `.claude/workflows/qrspi-batch.js`
- Q5: What verdict/score schema do existing critic and lens agents emit (e.g. `CRITIC_VERDICT_SCHEMA`, `parse_critic_verdict`), and what schema would a judge agent scoring N candidates on a rubric reuse or extend?
  **Target:** the critic verdict schema definitions in `.claude/workflows/qrspi-batch.js` and the lens agents under `.claude/agents/`

## State Management

- Q6: How is the N×-cost gate configured today for the existing Design panel (`critics.design`), and where is the single enabling flag for N-select generation read and parsed?
  **Target:** `parseCriticConfig` / config parsing in `.claude/workflows/qrspi-batch.js` and `.qrspi/config.example.json`
- Q7: How are parallel agent fan-out runs (multiple candidates) currently coordinated and collected, including how the per-round results are accumulated?
  **Target:** the parallel lens fan-out logic in `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q8: What happens when the N candidate design runs disagree such that the judge produces a tie or no clear winner — where would tie-breaking in judge scoring/synthesis selection be handled?
  **Target:** the module responsible for judge scoring and synthesis selection (new logic alongside `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`)
- Q9: How are partial failures of parallel runs handled — e.g. if one of the N design-agent runs errors or produces an empty/unparseable artifact, does the phase abort or proceed with the surviving candidates?
  **Target:** the parallel fan-out and per-phase success gate in `runPhase` / `.claude/workflows/qrspi-batch.js`
- Q10: When the N-select flag is OFF (the default), what guarantees the Design phase behaves exactly as the panel-only path does today with no extra spend?
  **Target:** the design-phase dispatch on config in `runPhase` / `doDesign` in `.claude/workflows/qrspi-batch.js`

## Testing

- Q11: How are existing parse/scoring helpers unit-tested with stubbed inputs (the `scripts/qrspi_*_test.py` pattern), and where would unit tests for judge scoring + synthesis selection with stubbed candidates live?
  **Target:** the `scripts/qrspi_*_test.py` suite and the helper(s) the judge/synthesis logic would expose
- Q12: How does the eval harness compare configurations today, given it is a non-functional placeholder, and what is the mechanism for an eval comparison of panel-only vs. N-select + panel?
  **Target:** `evals/` and `scripts/run_eval.py`

## Observability

- Q13: How is per-round critic-panel activity logged today, and where would per-candidate judge scores AND token cost be reported so the N× spend can be justified against the panel alone?
  **Target:** the per-round logging in `runCriticPanelLoop` in `.claude/workflows/qrspi-batch.js`
