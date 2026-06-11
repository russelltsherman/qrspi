# Questions — Land excludes the tip slice on multi-slice stacks, producing half-landed stacks

**Ticket:** RUS-70
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the land action determine which branch to check out before invoking the Graphite stack merge, and where is the hard-coded slice-1 reference set?
  **Target:** the module/prompt responsible for the `land` action (likely `.claude/workflows/qrspi-batch.js` and/or its finalize prompts)
- Q2: How is the set of slice branches for a ticket enumerated, and is the actual stack tip (top slice) computed anywhere or only the bottom slice-1?
  **Target:** the module responsible for resolving slice branch names (`scripts/qrspi_resolve.py` / `scripts/qrspi_resolve_state.py`)
- Q3: What exact Graphite command and flags are issued to perform the stack merge, and what is its documented behavior regarding which branches in the upstack get merged relative to the checked-out branch?
  **Target:** the land invocation in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What inputs (ticket id, branch names, slice count) does the land step receive from the resolver envelope, and does that envelope already expose the slice count or tip branch?
  **Target:** the envelope produced by `scripts/qrspi_resolve.py`
- Q5: Does the codebase have a dedicated land helper script (analogous to `qrspi_persist.py` / `qrspi_pr_body.py`), or is land expressed entirely as inline shell in the workflow/prompt?
  **Target:** `scripts/` directory and `.claude/workflows/qrspi-batch.js`

## State Management

- Q6: How does the workflow "square up local state" before the merge, and which commands are used so that already-approved remote PR heads are not force-pushed or overwritten?
  **Target:** the pre-merge local-state reconciliation step in `.claude/workflows/qrspi-batch.js`
- Q7: After a land completes, what condition does the workflow use to mark the ticket Done, and does it confirm every slice PR reached MERGED rather than assuming success from the merge command's exit code?
  **Target:** the land/Done transition in `.claude/workflows/qrspi-batch.js` and `scripts/qrspi_resolve_state.py`

## Edge Cases

- Q8: For a single-slice stack (slice-1 is also the tip), what branch does land check out, and does the current bottom-up-from-slice-1 logic still land the full stack correctly in that case?
  **Target:** the land branch-selection logic in `.claude/workflows/qrspi-batch.js`
- Q9: How does the land action behave when slice branches are non-contiguous or partially merged already (e.g., lower PRs MERGED, tip open) — does it re-attempt the full upstack or skip merged branches?
  **Target:** the land action in `.claude/workflows/qrspi-batch.js`
- Q10: Is there any enforcement that the bottom-up merge order is preserved, and what happens to that ordering when the merge is initiated from the tip rather than slice-1?
  **Target:** the Graphite merge invocation and any ordering logic in `.claude/workflows/qrspi-batch.js`

## Testing

- Q11: What existing tests cover the land action or the resolver's land decision, and do any assert that all N slice PRs reach MERGED?
  **Target:** `scripts/qrspi_resolve_state_test.py` and any `*_test.py` sibling covering land
- Q12: How are multi-slice stacks represented in the existing test fixtures, and is there a fixture with N>1 slices that a land test could exercise?
  **Target:** the test fixtures under `scripts/` (`qrspi_*_test.py`)

## Observability

- Q13: What does the land step log or report on completion, and would a partially-landed outcome (tip slice left open) currently surface as an error or pass silently?
  **Target:** the land step's logging/result reporting in `.claude/workflows/qrspi-batch.js`
- Q14: Does any post-land verification query PR states (e.g., via `scripts/qrspi_pr_state.py` / gh GraphQL) to confirm MERGED status, and where would such a check be wired in?
  **Target:** `scripts/qrspi_pr_state.py` and the land completion path in `.claude/workflows/qrspi-batch.js`
