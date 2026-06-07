# Implementation Plan — Deterministic worktree & branch cleanup for fully-merged QRSPI stacks

**Structure basis:** structure.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft
**Total steps:** 24

## Slice 1: Merge-state gatherer in qrspi_pr_state.py

### Setup

1. ⚠️ Modify `scripts/qrspi_pr_state.py` — extend the GitHub GraphQL query string to surface merge state for each branch's PR.
   - **Current:** PR query requests `states:OPEN` and selects `number`, `reviewDecision`, and review-thread fields only.
   - **After:** query also accepts/returns MERGED PRs and selects `state`, `merged`, and `mergedAt` per PR head ref, so merged PRs are no longer invisible (ref: Decision 1, Q2, Q7).

### Core Logic

2. ⚠️ Modify `scripts/qrspi_pr_state.py` — extend the per-branch PR-state record additively.
   - **Current:** record = `{ prExists, number, reviewDecision, unresolvedThreads }`.
   - **After:** record = `{ prExists, number, reviewDecision, unresolvedThreads, merged: bool, state: str, mergedAt: str|None }` — existing keys untouched so OPEN-path resolver/restack callers are unaffected (ref: Modified Types, Decision 1).
3. ✨ Add pure helper `stack_merge_state(branches, graphql_nodes) -> StackMergeState` in `scripts/qrspi_pr_state.py` — maps each real branch to `{ merged, prNumber, state }` from MERGED-aware GraphQL nodes; absent head ref (GitHub already deleted) maps to a documented sentinel (ref: Contracts, OQ3).
4. ✨ Add pure predicate `is_stack_fully_merged(stack_merge_state) -> bool` in `scripts/qrspi_pr_state.py` — returns true only when every real branch's PR is merged; empty stack and any unmerged branch return false (all-or-nothing, AC2).

### Tests

5. ⚠️ Modify `scripts/qrspi_pr_state_test.py` — add stdlib-only fixtures and assertions for `stack_merge_state` and `is_stack_fully_merged`: fully-merged → all true + predicate true; partially-merged → predicate false; in-flight (all OPEN) → predicate false; GitHub-already-deleted-ref → sentinel handled without crash (ref: Q13, Q14, OQ3).

### Verify Slice 1

6. **Checkpoint:** `python3 scripts/qrspi_pr_state_test.py`
   - [ ] All existing assertions plus the four new merge-state cases pass.
7. **Checkpoint:** `python3 scripts/qrspi_resolve_state_test.py`
   - [ ] OPEN-path resolver tests still pass, proving the additive fields broke no existing caller.

---

## Slice 2: qrspi_cleanup.py script (pure classifier + impure reap behind --dry-run)

### Setup

8. ✨ Create `scripts/qrspi_cleanup.py` — self-locating one-shot CLI; derive `REPO_ROOT` from `__file__` (two levels up), `argparse` with `--ticket <id>` and `--dry-run`, matching the established script contract (ref: Q4, Decision 4).
9. ⚠️ Modify `scripts/qrspi_cleanup.py` — import/reuse `worktree_path`, `branch_set`, `slice_numbers`, `pick_tip`, `real_branches`, `stack_merge_state`, `is_stack_fully_merged` from `qrspi_pr_state.py` rather than re-deriving (ref: Contracts "Reused as-is", Decision 1).
   - **Current:** file does not exist.
   - **After:** cleanup consumes the single authoritative gatherer for stack enumeration + merge state.

### Core Logic

10. ✨ Add pure `classify_cleanup(stack_merge_state, dirty_porcelain) -> CleanupDecision` in `scripts/qrspi_cleanup.py` — returns `{decision: "blocked", reason}` if `dirty_porcelain` non-empty (AC3); else `{decision: "destroy"}` if `is_stack_fully_merged` else `{decision: "skip"}` (AC2). Mirrors the `classify_result(rc, stdout, stderr)` pure shape (ref: Q14).
11. ✨ Add impure gather layer in `scripts/qrspi_cleanup.py` — for `--ticket`, gather stack merge state (Slice 1 helpers) and run `git status --porcelain` against the worktree to produce `dirty_porcelain` (ref: Q9, AC3).
12. ✨ Add impure reap layer in `scripts/qrspi_cleanup.py` — on `destroy` and NOT `--dry-run`, execute `git worktree remove`, delete local stack branches, and prune merged remote refs via `gt sync --force`; `--dry-run` gates ONLY execution, decision computed identically (ref: Decision 2/3/4, Q5).
13. ✨ Add idempotency handling in `scripts/qrspi_cleanup.py` — treat missing worktree, missing local branch, and already-deleted remote ref as clean no-op success (ref: Q11, Q12).
14. ✨ Add envelope emission + main in `scripts/qrspi_cleanup.py` — emit exactly one `CleanupEnvelope` `{ ok, repoRoot, decision, reason, removed{worktree,branches,remotes}, dryRun, error? }` to stdout, exit 0/1, report any infra error ONCE as `ok:false` (ref: CleanupEnvelope type, Q4).

### Tests

15. ✨ Create `scripts/qrspi_cleanup_test.py` — stdlib-only, assert/`check()` style; dict/text fixtures driving `classify_cleanup` for merged → destroy, partial → skip, dirty porcelain → blocked, in-flight → skip; NO subprocess mocks (ref: Q13, Q14).

### Verify Slice 2

16. **Checkpoint:** `python3 scripts/qrspi_cleanup_test.py`
    - [ ] All four classifier cases pass.
17. **Checkpoint:** `python3 scripts/qrspi_cleanup.py --ticket <merged-id> --dry-run`
    - [ ] Prints a `destroy` envelope listing the worktree/branches/remotes it WOULD remove, `dryRun:true`, touching nothing on disk.
18. **Checkpoint:** `python3 scripts/qrspi_cleanup.py --ticket <dirty-id> --dry-run`
    - [ ] Yields a `blocked` envelope with the dirty state surfaced in `reason`/`error`.

---

## Slice 3: Orchestration wiring (batch land + reconciliation, work SKILL prose)

### Core Logic

19. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`doLand`) — replace the prose worktree/branch removal with a verbatim single-command `qrspi_cleanup.py --ticket <id>` invocation after the bottom-up merge succeeds; fold the parsed envelope into `results` via `log(...)`/`summary` (ref: AC1, Q1, Q15).
   - **Current:** `doLand` emits prose running `gt sync --force` + `git worktree remove --force 2>/dev/null` + `git worktree prune`.
   - **After:** `doLand` runs the deterministic cleanup script and records its envelope outcome.
20. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a reconciliation pass that enumerates candidate finished tickets from git/GitHub (worktree dirs + merged PRs, NOT a Linear `Done` sweep) and runs `qrspi_cleanup.py --ticket <id>` per ticket, folding each outcome into `results`; a `blocked` ticket is logged and skipped while others proceed (ref: AC4, Q8, OQ1, OQ2).
21. ⚠️ Modify `.claude/skills/qrspi-work/SKILL.md` — replace the `gt sync --force` / `git worktree remove --force` land-cleanup prose with the `qrspi_cleanup.py` script invocation (ref: Q1, Q5).
    - **Current:** land-cleanup section instructs running `gt sync --force` and `git worktree remove --force`.
    - **After:** land-cleanup section invokes `qrspi_cleanup.py --ticket <id>`.

### Verify Slice 3

22. **Checkpoint (manual e2e land):** run a land via the batch workflow against a fully-merged stack.
    - [ ] After `gt merge` succeeds, `doLand` invokes `qrspi_cleanup.py`; the ticket's worktree + local branches are gone and the envelope is folded into `results`.
23. **Checkpoint (manual e2e reconciliation):** run the reconciliation pass with `--dry-run` first, then for real.
    - [ ] Dry-run lists the stranded backlog (the ~27 worktrees / 20+ merged stacks, AC5) touching nothing; the real run clears them; `blocked` tickets are logged and skipped, not halting the pass.
24. **Checkpoint:** `grep -nE 'git worktree remove --force|gt sync --force' .claude/skills/qrspi-work/SKILL.md`
    - [ ] Returns no land-cleanup matches — the prose is fully replaced by the script invocation.

---

## Rollback Notes

- **Step 1–4 (qrspi_pr_state.py):** changes are additive (new query fields, new pure helpers). Rollback = `git checkout scripts/qrspi_pr_state.py`; no data migration, no persisted state. Re-run `qrspi_pr_state_test.py` + `qrspi_resolve_state_test.py` to confirm restored behavior.
- **Step 12 (destructive reap in qrspi_cleanup.py):** this is the only destructive op — it removes worktrees, deletes local branches, and prunes remote refs. There is NO undo for a removed worktree or pruned remote ref. Mitigations are built into the design: `--dry-run` previews without touching disk; AC3 `blocked` guard refuses dirty worktrees; AC2 all-or-nothing destroys only when every stack PR is merged (merged PR content is preserved on trunk). Always run with `--dry-run` first against any new ticket set.
- **Step 19–21 (orchestration wiring):** behavioral/config changes in a workflow script and a SKILL.md. Rollback = `git checkout .claude/workflows/qrspi-batch.js .claude/skills/qrspi-work/SKILL.md` to restore the prior prose cleanup path. No persisted state involved.
- **Step 20/23 (reconciliation backlog sweep):** the AC5 sweep is the highest-blast-radius action (clears ~20+ stacks at once). Mandatory `--dry-run` preview before the real run; if the dry-run lists an unexpected ticket, abort and inspect rather than proceeding.
