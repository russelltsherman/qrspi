# Questions — qrspi-batch restack step aborts submit on a partially-landed stack (merged ancestors)

**Ticket:** RUS-67
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does `restack()` determine the stack tip, and what data does `pick_tip` consume to select the highest slice it checks out before running `gt restack --downstack`?
  **Target:** `scripts/qrspi_restack.py` (`restack()`, `pick_tip`, lines ~155-188)
- Q2: What information about each branch's tracked parent and merge status is currently available to the restack script (e.g. from `gt` metadata, `gh`, or git), and where does that data enter the script?
  **Target:** `scripts/qrspi_restack.py` and any `gt`/`gh` invocations it makes

## API Surface

- Q3: What is the exact set of `gt` subcommands and flags `qrspi_restack.py` invokes today (restack, submit), and which functions wrap each invocation?
  **Target:** `scripts/qrspi_restack.py` (`restack()`, `submit_stack()`)
- Q4: What signature and return contract does `classify_submit()` expose, and how is its `ok:false` result consumed by the caller?
  **Target:** `scripts/qrspi_restack.py` (`classify_submit()`)
- Q5: How does the `qrspi-batch` workflow invoke `qrspi_restack.py`, and how does it map the script's output to the `restack_conflict` outcome that strands the ticket?
  **Target:** `.claude/workflows/qrspi-batch.js`

## State Management

- Q6: Where does the script document or enforce the "never `gt sync` a held stack" rule, and what is recorded in the header comment about why merged-ancestor pruning is currently absent?
  **Target:** `scripts/qrspi_restack.py` (header comment)
- Q7: How does the resolver (`qrspi_resolve_state.py`) currently detect a "design branch" and decide entry state, such that a partially-landed stack causes it to misreport `entry_blocked "No design branch"`?
  **Target:** `scripts/qrspi_resolve_state.py`

## Edge Cases

- Q8: What does the script do when `gt restack` reports that no branch moved versus when a branch moved — does the submit path run only conditionally, and what triggers it?
  **Target:** `scripts/qrspi_restack.py` (`restack()`)
- Q9: How does the script behave when the lowest open slice's tracked parent is a merged branch (e.g. `slice-1` merged, `slice-2` open) — is there any branch in the codebase that classifies a branch as merged-into-trunk?
  **Target:** `scripts/qrspi_restack.py` and the module responsible for branch/merge classification
- Q10: What happens when ALL slices have merged (fully landed) versus when none have merged (fully open) — how does the restack/submit path distinguish these from the partial-land case?
  **Target:** `scripts/qrspi_restack.py` (`restack()`, `pick_tip`)

## Testing

- Q11: What pure-logic units in `qrspi_restack.py` are already covered by its `_test.py` sibling, and how do those tests stub or fake the `gt`/`gh` calls?
  **Target:** `scripts/qrspi_restack_test.py`
- Q12: What test fixtures or helpers exist in the resolver test for representing a partially-landed stack (merged ancestors + open slices)?
  **Target:** `scripts/qrspi_resolve_state_test.py`

## Observability

- Q13: How does `qrspi_restack.py` surface the abort to the batch — what fields does it emit (e.g. `ok`, error text, classification) and where is the verbatim `gt` WARNING/ERROR output captured or logged?
  **Target:** `scripts/qrspi_restack.py` (`classify_submit()`, `submit_stack()`)
