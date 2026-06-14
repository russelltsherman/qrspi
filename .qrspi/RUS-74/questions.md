# Questions — qrspi-batch trunk-sync hardening: never build a dependent ticket on a stale local main

**Ticket:** RUS-74
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Data Flow

- Q1: In the Resolve phase, where does the base ref that a new worktree is cut from get determined, and does any step fetch or move local `main` before that cut?
  **Target:** `.claude/workflows/qrspi-batch.js` (Resolve phase) and `scripts/qrspi_resolve.py`
- Q2: How does the Restack phase select its restack base, and at what point does it read local `main` relative to the start-of-run sequence?
  **Target:** `.claude/workflows/qrspi-batch.js` (Restack phase)
- Q3: What is the ordering of phases at run start (Query → Resolve → Restack → … → land), and what is the earliest orchestration point that executes in the main checkout before any worktree is cut?
  **Target:** `.claude/workflows/qrspi-batch.js` (top-level run sequence)

## API Surface

- Q4: What is the established JSON-envelope convention and self-locating repo-root pattern used by sibling helpers, so a new `scripts/qrspi_sync_trunk.py` matches it?
  **Target:** `scripts/qrspi_persist.py` and `scripts/qrspi_resolve.py`
- Q5: How does the workflow shell out to these Python helpers and parse their JSON output, including how a non-`ok` envelope is surfaced as a hard stop?
  **Target:** `.claude/workflows/qrspi-batch.js` (helper invocation/parse sites)
- Q6: What fields does the land worker's output schema currently expose, and where does `finResult` read from it (`fin.error` vs `fin.summary`)?
  **Target:** `.claude/workflows/qrspi-batch.js` (land worker schema and `finResult`)

## State Management

- Q7: Which checkout (main repo vs `.worktrees/<id>/`) does each orchestration site run in, and how is "the main checkout" identified for a sync that must not run inside a worktree?
  **Target:** `.claude/workflows/qrspi-batch.js` and the worktree-setup logic in `scripts/qrspi_resolve.py`
- Q8: How is the post-land call site distinguished from the land worker's own worktree context, so AC3's hygiene sync runs in the orchestrator/main-checkout context only?
  **Target:** `.claude/workflows/qrspi-batch.js` (land call site)

## Edge Cases

- Q9: How is a divergent local `main` (not an ancestor of `origin/main`) currently detected anywhere in the harness, and what FF-ancestor check primitives are available to fail loud on it?
  **Target:** the module responsible for trunk/branch operations in `.claude/workflows/qrspi-batch.js`
- Q10: How does the existing code detect a dirty working tree before mutating refs, so the sync can guard on a clean main working tree?
  **Target:** `scripts/qrspi_resolve.py` and `.claude/workflows/qrspi-batch.js`
- Q11: What happens at run start if `git fetch origin` fails or local `main` is already current, and how do other run-start helpers signal a no-op versus an abort?
  **Target:** `.claude/workflows/qrspi-batch.js` (run-start error handling)

## Testing

- Q12: What stdlib-only test pattern do the existing `scripts/qrspi_*_test.py` siblings use to exercise git interactions (e.g., temp repos, fakes, or subprocess stubs) for the clean-FF / already-current / divergence / dirty-tree cases?
  **Target:** `scripts/qrspi_resolve_state_test.py` and `scripts/qrspi_persist_test.py`

## Observability

- Q13: How are hard-stop failures currently propagated into the batch run result, and where would a verbatim land-conflict reason ("land finalize failed: ...") be assembled and surfaced?
  **Target:** `.claude/workflows/qrspi-batch.js` (`finResult` and run-result reporting)
