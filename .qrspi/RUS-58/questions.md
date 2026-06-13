# Questions — qrspi critics 4/5 — Stage 3 (Implementation): per-slice code critics + whole-stack coherence pass

**Ticket:** RUS-58
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Data Flow

- Q1: At the planning→implementation seam, how are the slice's planned steps located and read so they can be handed to the per-slice edge critic as its rubric?
  **Target:** the module responsible for reading per-slice plan steps (plan artifact reader / `.qrspi/<id>/` plan output)
- Q2: How does the whole-stack coherence critic obtain the six upstream artifacts (ticket, questions, research, design, structure, plan) together for a single pass?
  **Target:** the artifact-loading path in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_persist.py`

## API Surface

- Q3: What is the contract (inputs and return envelope) of the existing foundation critic loop that the per-slice edge critic is said to reuse?
  **Target:** `runCriticLoop` and the `qrspi-critic` agent in `.claude/workflows/qrspi-batch.js`
- Q4: How is the implementation phase currently sequenced in `runPhase` so that a critic can be inserted after tests pass and before `gt submit`?
  **Target:** the implementation-phase branch of `runPhase` in `.claude/workflows/qrspi-batch.js`
- Q5: What is the existing mechanism for surfacing critic findings into a PR body, and what API does it use?
  **Target:** the module responsible for PR body composition (`scripts/qrspi_pr_body.py` and the `gh api ... pulls/N -X PATCH` path)

## State Management

- Q6: How is per-slice critic cardinality (single critic, no panel) currently expressed for other phases, and where is the panel-vs-single configuration read from?
  **Target:** the critic configuration reader (`critics.*` keys) and `scripts/qrspi_config.py`
- Q7: Where does the revise path for an implementation slice live, so the edge critic's "revise = fix the slice" outcome can be wired to it?
  **Target:** the revise/amend module (`scripts/qrspi_revise_amend.py` and the revise branch in `qrspi-batch.js`)

## Edge Cases

- Q8: What happens in the implementation phase flow when tests pass but the per-slice edge critic fails after the maximum revise attempts — is submission blocked, and where is that terminal state handled?
  **Target:** the critic-loop termination handling in `runCriticLoop` / `runPhase`
- Q9: When the coherence pass flags intent drift in an upstream artifact, what is the existing mechanism (if any) for triggering a targeted upstream revise from the implementation seam, and how is downstream work affected?
  **Target:** the reset/revise resolution logic in `scripts/qrspi_resolve_state.py`
- Q10: For a single-slice ticket, does the per-slice critic loop still execute, and how is the slice count derived to bound the N critic runs?
  **Target:** the slice-enumeration logic in `.claude/workflows/qrspi-batch.js`
- Q11: How is the slice diff computed and scoped (which commit range or branch comparison) so that the edge critic sees only that slice's code and not the whole stack?
  **Target:** the slice diff-gathering logic in the implementation phase of `qrspi-batch.js`

## Testing

- Q12: How are existing critic-wiring unit tests structured to stub inputs (e.g., diff and steps), so the slice-critic and coherence-pass triggering tests can follow the same pattern?
  **Target:** the `scripts/qrspi_*_test.py` stdlib-only test siblings and any existing critic-loop test

## Observability

- Q13: How is the implementation-phase eval score currently computed and reported, so a before/after comparison can be emitted?
  **Target:** `scripts/run_eval.py` and the `evals/` harness
- Q14: Where are critic findings and revise outcomes logged or emitted during a batch run so the coherence-pass findings are observable to an operator?
  **Target:** the logging/output path in `.claude/workflows/qrspi-batch.js` (`runPhase` / `runCriticLoop`)
