# Questions — Self-verifying design & plan producers: codebase-grounded claim checks + pre-persist verification gate

**Ticket:** RUS-94
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `runPhase` currently sequence the producer agent spawn, the staged-artifact write, and the `qrspi_persist.py` move, and at what point in that sequence could a pre-persist gate intercept the staged artifact before it is moved to the canonical `.qrspi/<id>/` path?
  **Target:** `.claude/workflows/qrspi-batch.js` (the `runPhase` function and the `stg()` staging helper)
- Q2: What inputs (ticket text, answered questions, research artifact, REPO_ROOT) are spliced into the `qrspi-design` and `qrspi-plan` spawn prompts today, and how are those inputs passed (inline vs file path)?
  **Target:** `.claude/workflows/qrspi-batch.js` (the design/plan spawn-prompt seam)

## API Surface

- Q3: What is the exact invocation contract of `scripts/qrspi_persist.py` (arguments, exit codes, stdout/stderr shape) that the new pre-persist gate would need to run before, and how is its result consumed in `runPhase`?
  **Target:** `scripts/qrspi_persist.py` and its caller in `.claude/workflows/qrspi-batch.js`
- Q4: What is the established CLI/envelope convention for the tested pure-Python helpers (e.g. argument parsing, JSON-on-stdout, self-locating repo root) that a new verification-core helper should follow to match `qrspi_resolve.py` / `qrspi_persist.py`?
  **Target:** `scripts/qrspi_resolve.py` and `scripts/qrspi_persist.py`
- Q5: How do the `qrspi-design.md` and `qrspi-plan.md` agent definitions declare their `tools:` field today, and how is the read-only scoped-to-REPO_ROOT posture (RUS-82) expressed where it already exists in the repo?
  **Target:** `.claude/agents/qrspi-design.md`, `.claude/agents/qrspi-plan.md`, and the RUS-82 agent that already has scoped Read/Grep/Glob access

## State Management

- Q6: How does `runPhase` currently represent and propagate a phase failure into the existing revise pass, and what state/flag would a "verification failed → enter revise" outcome reuse versus add?
  **Target:** `.claude/workflows/qrspi-batch.js` (the `runPhase` failure/revise path and `doRevise`)
- Q7: What is the canonical structure of the design artifact's `## Open Questions` section (where AC2/AC5 convert unverifiable claims and contradicted premises into Open Questions), and where is that section defined in the design template?
  **Target:** `.qrspi/templates/design.md` and `.claude/agents/qrspi-design.md`

## Edge Cases

- Q8: How is a ticket's set of acceptance criteria currently surfaced to the design/plan producers (AC3 completeness mapping), and what happens to the AC-coverage check when the ticket has zero or malformed acceptance criteria?
  **Target:** the module/agent responsible for assembling the design/plan spawn input from the ticket (`.claude/workflows/qrspi-batch.js` spawn seam and `.claude/agents/qrspi-design.md`)
- Q9: What does the existing persist/revise path do when the staged artifact is missing or empty, and how would a verification gate that runs before persist distinguish "no verification signal present" (AC: behave exactly as today) from "verification ran and failed"?
  **Target:** `scripts/qrspi_persist.py` and the planned verification-core helper invocation in `runPhase`
- Q10: How is the revise loop bounded today (e.g. attempt counters/caps like the `CI-Revise-Attempt` trailer), so a verification gate that repeatedly fails does not loop indefinitely?
  **Target:** `.claude/workflows/qrspi-batch.js` (revise attempt accounting) and `scripts/qrspi_resolve_state.py`

## Testing

- Q11: What is the structure and convention of the existing stdlib-only `_test.py` siblings and the aggregating runner that a new `scripts/<verification-core>_test.py` must conform to (test discovery, subprocess isolation, naming)?
  **Target:** `scripts/run_tests.py` and a representative `scripts/*_test.py` sibling (e.g. `scripts/qrspi_resolve_state_test.py`)
- Q12: How is the JS↔Python contract between `qrspi-batch.js` and the pure-Python helpers currently exercised (given `qrspi-batch.js` is documented as not unit-testable in isolation), so the new gate's JS-to-core seam is covered?
  **Target:** `docs/testing-dynamic-workflows.md` and the JS↔Python contract fixtures referenced there

## Observability

- Q13: How does `runPhase` currently surface a phase outcome (logs, recorded result codes, the batch run summary) so that a verification-gate failure and the resulting revise pass are visible in the run output?
  **Target:** `.claude/workflows/qrspi-batch.js` (the per-phase result recording and run-summary emission)
