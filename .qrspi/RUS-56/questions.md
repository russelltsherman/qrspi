# Questions — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Ticket:** RUS-56
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the design phase currently move from producing `design.md` to submitting the design PR, and at what point would a critic panel + synthesize + revise stage be inserted into that sequence?
  **Target:** the design phase agent definition in `.claude/agents/` and its wrapper in `.claude/skills/qrspi-design/`

- Q2: How are the upstream artifacts (ticket, `research.md`, `questions.md`) and `design.md` located and read during the design phase, so each lens can be handed them as its rubric?
  **Target:** the design phase agent and `scripts/qrspi_persist.py` / staging-path conventions

## API Surface

- Q3: What interface does the "foundation loop (1/5)" expose for running M lenses in parallel, and what arguments does it accept (lens definitions, inputs, maxRounds)?
  **Target:** the foundation critic-loop module introduced by ticket 1/5 (the module responsible for running critic lenses)

- Q4: What is the exact findings schema each lens must emit, and where is the schema validation performed for lens output?
  **Target:** the module responsible for critic findings schema validation

- Q5: How is `maxRounds` (default 2) configured and passed into a phase's critic loop, and is it overridable per-phase or per-run?
  **Target:** the foundation loop configuration surface and `.qrspi/config.json` / `config.example.json`

## State Management

- Q6: How is the synthesized revise instruction passed back to the design agent for revision, and how is round count tracked across panel → synthesize → revise iterations?
  **Target:** the design phase agent and the foundation loop state handling

- Q7: How is the revised `design.md` re-persisted between rounds, and does re-paneling re-read the staged artifact or an in-memory copy?
  **Target:** `scripts/qrspi_persist.py` and the design phase staging flow

## Edge Cases

- Q8: What happens when the panel passes on round 1 — what mechanism short-circuits the revise step so no revision occurs?
  **Target:** the foundation loop / design phase agent termination logic

- Q9: After `maxRounds` is exhausted with unresolved findings, how are those findings surfaced into the design PR body, given that PR bodies are seeded only from the branch commit message at `gt submit` creation time?
  **Target:** the design PR finalize/commit-message assembly path and `scripts/qrspi_pr_body.py`

- Q10: How are conflicting or duplicate findings across lenses handled during synthesis (merge/dedupe), and what determines precedence when two lenses disagree?
  **Target:** the synthesis module responsible for merging/deduping panel findings

- Q11: What is the failure behavior if a single lens errors or returns schema-invalid output mid-panel — does the panel abort, drop that lens, or block design submission?
  **Target:** the foundation loop error-handling path and findings schema validation

## Testing

- Q12: How do existing `scripts/qrspi_*_test.py` unit tests stub critic lenses, and what pattern would the synthesis merge/dedupe and panel-wiring tests follow?
  **Target:** `scripts/qrspi_*_test.py` siblings and any existing foundation-loop test from ticket 1/5

- Q13: How does the eval suite run against the design phase to produce the before/after design-phase score (post-RUS-37 checks) required by the acceptance criteria?
  **Target:** `scripts/run_eval.py`, the `evals/` directory, and the RUS-37 design-phase eval checks

## Observability

- Q14: How are panel findings, synthesis output, and per-round revise decisions logged or reported so a human can audit why a design was (or was not) revised before review?
  **Target:** the design phase agent logging and the foundation loop run output
