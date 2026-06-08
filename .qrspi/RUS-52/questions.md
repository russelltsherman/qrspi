# Questions — Deterministic worktree & branch cleanup for fully-merged QRSPI stacks

**Ticket:** RUS-52
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the land step currently determine that a ticket's stack is complete, and where does the prose cleanup instruction to the worker live within it?
  **Target:** the land action in `.claude/workflows/qrspi-batch.js`
- Q2: How does `scripts/qrspi_pr_state.py` enumerate the PRs that belong to a single ticket's stack, and what fields does it report for each PR's merge state?
  **Target:** `scripts/qrspi_pr_state.py`
- Q3: How are a ticket's worktree path and its stack branch names (`<id>/design`, `<id>/plan`, `<id>/slice-N`) derived from the ticket ID elsewhere in the harness?
  **Target:** `scripts/qrspi_resolve.py` and the branch-naming logic in `.claude/workflows/qrspi-batch.js`

## API Surface

- Q4: What is the established invocation contract (arguments, stdout envelope, exit codes, self-location from `__file__`) shared by `qrspi_resolve.py`, `qrspi_persist.py`, and the restack script that a new cleanup script must match?
  **Target:** `scripts/qrspi_resolve.py` and the restack script under `scripts/`
- Q5: What Graphite commands does the harness already shell out to for remote-affecting operations, and which one performs remote ref pruning?
  **Target:** the restack/submit logic in `.claude/workflows/qrspi-batch.js` and the `using-graphite-cli` skill references in `scripts/`
- Q6: How do the existing scripts expose a preview/dry-run mode or report intended actions without performing them?
  **Target:** the module responsible for resolve/persist CLI flag parsing in `scripts/`

## State Management

- Q7: What is treated as the authoritative source of PR merge state in the resolver, and how is "merged" distinguished from "in-review" and "closed-unmerged"?
  **Target:** `scripts/qrspi_resolve_state.py` and `scripts/qrspi_pr_state.py`
- Q8: How does the harness currently track which git worktrees and branches exist for in-flight tickets versus finished ones?
  **Target:** the worktree-setup logic in `scripts/qrspi_resolve.py` and `.worktrees/` handling in `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q9: How does existing harness code detect uncommitted changes in a worktree, and where is `git worktree remove` (or any force-removal flag) currently invoked?
  **Target:** the worktree teardown path in `.claude/workflows/qrspi-batch.js`
- Q10: How does the current reset/discard path remove downstream phase branches and worktrees, and what does it do when a stack is only partially merged?
  **Target:** the automatic reset action in `.claude/workflows/qrspi-batch.js`
- Q11: How does the harness handle remote refs that have already been deleted (e.g., GitHub auto-deletes the head branch on merge) so a pruning step does not error on missing refs?
  **Target:** the Graphite remote-pruning invocation in `.claude/workflows/qrspi-batch.js`
- Q12: What guarantees idempotency in the existing self-locating scripts when they are re-run against already-processed tickets?
  **Target:** `scripts/qrspi_persist.py` and `scripts/qrspi_resolve.py`

## Testing

- Q13: What is the stdlib-only unit-test structure and fixture/mocking convention used by `scripts/qrspi_*_test.py` for simulating PR merge states (merged / partial / dirty / in-flight)?
  **Target:** `scripts/qrspi_resolve_state_test.py` and sibling `scripts/qrspi_*_test.py` files
- Q14: How do existing tests stub out git and Graphite subprocess calls so cleanup decision logic can be verified without touching a real repository?
  **Target:** the test doubles in `scripts/qrspi_*_test.py`

## Observability

- Q15: How do the existing land and reset actions surface their decisions and outcomes (logging, stdout envelope fields, batch run summary), so a cleanup pass and its skip/destroy/blocked-by-dirty decisions are visible to an operator?
  **Target:** the run-summary/logging path in `.claude/workflows/qrspi-batch.js` and the envelope emitted by `scripts/qrspi_resolve.py`
