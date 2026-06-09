# Questions — Backfill 17 missing eval fixtures

**Ticket:** RUS-36
**Generated:** 2026-06-09T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the eval harness resolve a fixture filename referenced by a case in `evals/suite.json` into a path under `evals/fixtures/`, and what exact load step errors when the file is absent?
  **Target:** `scripts/run_eval.py` and the module responsible for fixture loading
- Q2: For the generate-then-curate path, what is the on-disk relationship between a source ticket (e.g. `ticket_rest_endpoint.md`) and the artifact a phase agent produces, and where does a phase agent write its output before persistence?
  **Target:** `scripts/qrspi_persist.py` and the `stg()` staging-path helper in `.claude/workflows/qrspi-batch.js`
- Q3: Which existing 4 ticket fixtures are already present in `evals/fixtures/`, and what naming and content conventions do they establish for the 17 missing files?
  **Target:** the existing files in `evals/fixtures/`

## API Surface

- Q4: What is the full list of fixture filenames each eval case in `evals/suite.json` references, and does that list match the 17 names enumerated in the ticket exactly?
  **Target:** `evals/suite.json`
- Q5: What format and required sections does each phase's artifact template define, so a curated fixture matches the gold-standard shape its consuming case expects?
  **Target:** the per-phase templates in `.qrspi/templates/` (questions, research, design, structure, plan, worktree)

## State Management

- Q6: How is the mapping between an eval case and its phase under test recorded, so the 11 currently-erroring cases can be tied back to the specific missing fixture each requires?
  **Target:** `evals/suite.json` and `scripts/run_eval.py`
- Q7: Where does the harness expect the `.txt` diff fixture (`git_diff_rest_endpoint.txt`) versus the `.md` artifact fixtures, and is the load path branch by extension?
  **Target:** the module responsible for loading fixtures in `scripts/run_eval.py`

## Edge Cases

- Q8: What does "loads cleanly" mean concretely for a fixture — does the harness validate only file existence/non-emptiness, or does it parse/schema-check the content?
  **Target:** `scripts/run_eval.py`
- Q9: How are the "broken" fixtures (`structure_broken_contract.md`, `plan_broken_contract_slice1.md`, `worktree_session_broken_contract.md`) expected to differ from their passing counterparts, and does any case assert a failure rather than a success against them?
  **Target:** `evals/suite.json` and `docs/eval-system.md` lines 78-89
- Q10: For multi-slice plan fixtures (`plan_rest_endpoint.md` plus `plan_rest_endpoint_slice1.md`), what distinguishes the whole-plan fixture from the per-slice fixture, and which case consumes each?
  **Target:** `evals/suite.json`
- Q11: Does any fixture name in the ticket NOT have a corresponding referencing case in `evals/suite.json` (or vice versa), which would leave an orphaned or unmet reference?
  **Target:** `evals/suite.json` cross-referenced with `docs/eval-system.md`

## Testing

- Q12: How is the eval harness currently exercised given it is documented as a "non-functional placeholder," and what command or test would demonstrate a fixture loads cleanly?
  **Target:** `scripts/run_eval.py` and its `_test.py` sibling if present
- Q13: Are there existing stdlib-only unit tests covering fixture presence or the suite-to-fixture reference integrity?
  **Target:** `scripts/*_test.py`

## Observability

- Q14: When a fixture fails to load today, what does the harness emit (exception, log line, exit code), and how would an operator identify which of the 11 cases errored on which missing file?
  **Target:** the error-reporting path in `scripts/run_eval.py`
