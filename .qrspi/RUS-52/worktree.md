# Work Tree — Deterministic worktree & branch cleanup for fully-merged QRSPI stacks

**Plan basis:** plan.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T8 → T10 → T11 → T12 → T13 → T14 → T15 → T19 → T20 → T22 → T23 (16 tasks)

## Session 1

**Load:** structure.md §Modified Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Extend `qrspi_pr_state.py` GraphQL query to accept MERGED PRs and select `state`, `merged`, `mergedAt` per head ref | — | §1.1 | M | pending |
| T2 | Extend per-branch PR-state record additively with `merged`, `state`, `mergedAt` (existing keys untouched) | T1 | §1.2 | S | pending |
| T3 | Add pure helper `stack_merge_state(branches, graphql_nodes) -> StackMergeState`; absent head ref maps to documented sentinel | T2 | §1.3 | M | pending |
| T4 | Add pure predicate `is_stack_fully_merged(stack_merge_state) -> bool`; empty/any-unmerged → false | T3 | §1.4 | S | pending |
| T5 | Add stdlib-only fixtures/assertions in `qrspi_pr_state_test.py` for the two new helpers (4 cases) | T4 | §1.5 | M | pending |
| T6 | **Verify Slice 1** — `python3 scripts/qrspi_pr_state_test.py` (new + existing pass) | T5 | §1.6 | S | pending |
| T7 | **Verify Slice 1** — `python3 scripts/qrspi_resolve_state_test.py` (OPEN-path callers unaffected) | T6 | §1.7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. Slice 2 depends only on the now-stable `stack_merge_state` / `is_stack_fully_merged` contracts, not on Slice 1's implementation internals. Fresh context for Slice 2.

## Session 2

**Load:** structure.md §Contracts (CleanupDecision, CleanupEnvelope, "Reused as-is"), plan.md §Slice 2, impl-log.md §Slice 1 (helper signatures only)
**Estimated context:** ~24% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Create self-locating `qrspi_cleanup.py` CLI — `REPO_ROOT` from `__file__`, argparse `--ticket`/`--dry-run` | T7 | §2.8 | S | pending |
| T9 | Import/reuse `worktree_path`, `branch_set`, `slice_numbers`, `pick_tip`, `real_branches`, `stack_merge_state`, `is_stack_fully_merged` from `qrspi_pr_state.py` | T8 | §2.9 | S | pending |
| T10 | Add pure `classify_cleanup(stack_merge_state, dirty_porcelain) -> CleanupDecision` — blocked/destroy/skip | T9 | §2.10 | M | pending |
| T11 | Add impure gather layer — stack merge state + `git status --porcelain` → `dirty_porcelain` | T10 | §2.11 | M | pending |
| T12 | Add impure reap layer — `git worktree remove`, delete local branches, `gt sync --force`; `--dry-run` gates execution only | T11 | §2.12 | L | pending |
| T13 | Add idempotency handling — missing worktree/branch/remote ref = clean no-op success | T12 | §2.13 | M | pending |
| T14 | Add `CleanupEnvelope` emission + main; single envelope to stdout, exit 0/1, infra error once as `ok:false` | T13 | §2.14 | M | pending |
| T15 | Create `qrspi_cleanup_test.py` — stdlib-only classifier fixtures (merged/partial/dirty/in-flight), no subprocess mocks | T14 | §2.15 | M | pending |
| T16 | **Verify Slice 2** — `python3 scripts/qrspi_cleanup_test.py` (4 classifier cases) | T15 | §2.16 | S | pending |
| T17 | **Verify Slice 2** — `qrspi_cleanup.py --ticket <merged-id> --dry-run` prints `destroy` envelope, touches nothing | T16 | §2.17 | S | pending |
| T18 | **Verify Slice 2** — `qrspi_cleanup.py --ticket <dirty-id> --dry-run` yields `blocked` envelope | T17 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 ships a complete, tested CLI. Slice 3 only wires existing callers to its frozen invocation contract (`qrspi_cleanup.py --ticket <id>`), so its implementation detail is no longer needed. Fresh context for Slice 3 orchestration.

## Session 3

**Load:** structure.md §Contracts (CleanupEnvelope), plan.md §Slice 3, plan.md §Rollback Notes, impl-log.md §Slice 2 (cleanup CLI invocation + envelope shape only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Modify `qrspi-batch.js` `doLand` — replace prose cleanup with verbatim `qrspi_cleanup.py --ticket <id>`, fold envelope into `results` | T18 | §3.19 | M | pending |
| T20 | Modify `qrspi-batch.js` — add reconciliation pass (git/GitHub candidates, not Linear sweep) running cleanup per ticket; `blocked` logged and skipped | T19 | §3.20 | L | pending |
| T21 | Modify `qrspi-work/SKILL.md` — replace `gt sync --force` / `git worktree remove --force` land-cleanup prose with script invocation | T19 | §3.21 | S | pending |
| T22 | **Verify Slice 3** — manual e2e land: `doLand` invokes cleanup, worktree/branches gone, envelope folded into `results` | T20, T21 | §3.22 | M | pending |
| T23 | **Verify Slice 3** — manual e2e reconciliation: `--dry-run` lists stranded backlog, real run clears them, `blocked` skipped | T22 | §3.23 | M | pending |
| T24 | **Verify Slice 3** — `grep -nE 'git worktree remove --force\|gt sync --force' .claude/skills/qrspi-work/SKILL.md` returns no land-cleanup matches | T21 | §3.24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. No fresh context required after Slice 3 verification — feature complete and ready for the qrspi-pr phase.
