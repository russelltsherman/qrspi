# Questions — qrspi critics 1/5: edge-critic loop primitive wired into runPhase

**Ticket:** RUS-55
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does a phase agent currently pass its produced staged artifact from `produce` through to finalize/submit inside `runPhase` in `qrspi-batch.js`, and at which point would a pre-finalize step be inserted?
  **Target:** `runPhase` in `.claude/workflows/qrspi-batch.js`
- Q2: How are upstream artifact(s) for a given phase located and read today (staging paths via the `stg()` helper vs the persisted `.worktrees/<id>/.qrspi/<id>/` paths), so the critic can be handed the upstream artifact as the rubric anchor?
  **Target:** the `stg()` helper and artifact-path resolution in `.claude/workflows/qrspi-batch.js`
- Q3: How is a produced artifact's persistence verified and the result surfaced back into `runPhase` (the Fix A staging + move), and does that verification gate run before or after where the critic loop would sit?
  **Target:** `scripts/qrspi_persist.py` and its call site in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What is the existing signature and call convention for spawning a typed phase agent (e.g. the `agent()`/`parallel()`/`pipeline()` primitives) that `runCriticLoop` would reuse to invoke critic and revise agents?
  **Target:** the agent-spawning primitives in `.claude/workflows/qrspi-batch.js`
- Q5: How are agent-type contracts currently defined and registered (where phase agent definitions live), so a new `critic` agent-type with a StructuredOutput schema can be added consistently?
  **Target:** `.claude/agents/` and the agent-type registration in `.claude/workflows/qrspi-batch.js`
- Q6: How are StructuredOutput schemas currently declared and validated for existing agents, and what mechanism would validate the `{ pass: bool, findings: [...] }` findings contract?
  **Target:** the StructuredOutput schema definitions used by existing phase agents

## State Management

- Q7: How is per-phase configuration (which phase maps to which agent/template/artifact) represented in `qrspi-batch.js`, so an OPTIONAL per-phase critic configuration can be attached without affecting phases that have none?
  **Target:** the phase configuration table/map in `.claude/workflows/qrspi-batch.js`
- Q8: How is the human-review PR body composed today for design/plan phases (the heredoc commit message), so remaining non-converged critic findings can be appended to it?
  **Target:** PR body / commit-message authoring in `.claude/workflows/qrspi-batch.js` (and `scripts/qrspi_pr_body.py`)

## Edge Cases

- Q9: When a phase has no critic configured, what is the exact current control path through `runPhase` that must remain byte-for-byte unchanged, and what branch would guard the new step?
  **Target:** `runPhase` in `.claude/workflows/qrspi-batch.js`
- Q10: How are round counters / loop caps expressed in existing deterministic JS control flow in `qrspi-batch.js`, and how does the codebase currently guard against non-terminating loops in orchestration?
  **Target:** deterministic control-flow sections of `.claude/workflows/qrspi-batch.js`
- Q11: What happens today if a critic-equivalent agentic call returns malformed or schema-invalid output — is there existing handling for agent output that fails schema validation that the findings contract would inherit?
  **Target:** the agent-output validation path in `.claude/workflows/qrspi-batch.js`

## Testing

- Q12: How are the existing stdlib-only `_test.py` unit tests structured for pure orchestration logic, and is the JS loop control flow in `qrspi-batch.js` currently unit-tested anywhere, or is JS logic verified only by manual e2e?
  **Target:** `scripts/qrspi_*_test.py` and any test harness for `.claude/workflows/qrspi-batch.js`
- Q13: How does the existing test setup stub or fake agentic calls so the produce→critique→revise control flow can be tested with stubbed critic/revise functions?
  **Target:** the test stubbing approach used in `scripts/qrspi_*_test.py`

## Observability

- Q14: How does `runPhase` currently report progress, per-phase outcomes, and failures (logging / return envelope) so critic rounds, pass/fail per round, and cap-reached surfacing can be observed?
  **Target:** the logging / result-envelope reporting in `runPhase` in `.claude/workflows/qrspi-batch.js`
