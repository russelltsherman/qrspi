# Structure Outline — Deterministic worktree & branch cleanup for fully-merged QRSPI stacks

**Design basis:** design.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft

## New Types

(All Python; "types" are documented dict/JSON shapes, no class machinery.)

- `StackMergeState = { branch: str -> { merged: bool, prNumber: int | None, state: "MERGED"|"OPEN"|"CLOSED"|None } }`
  — per-real-branch merge status for one ticket's stack (output of the extended gatherer).
- `CleanupDecision = { decision: "destroy"|"skip"|"blocked", reason: str }`
  — return of the pure classifier.
- `CleanupEnvelope = { ok: bool, repoRoot: str, decision: "destroy"|"skip"|"blocked", reason: str, removed: { worktree: bool, branches: [str], remotes: [str] }, dryRun: bool, error?: str }`
  — the single stdout JSON envelope from `qrspi_cleanup.py`, matching the established `ok`/`repoRoot`/`error?` contract (ref: Q4).

## Modified Types

- `qrspi_pr_state.py` PR-state record — add fields `merged: bool`, `state: str`, `mergedAt: str|None` **additively** alongside existing `prExists`/`number`/`reviewDecision`/`unresolvedThreads` so OPEN-path resolver/restack callers are unaffected (ref: design.md §Delta, Decision 1, Q2, Q7).

## Contracts

- `stack_merge_state(branches, graphql_nodes): StackMergeState` — pure helper in `qrspi_pr_state.py`; maps each real branch to its merged boolean from a MERGED-aware GraphQL result (ref: Decision 1).
- `is_stack_fully_merged(stack_merge_state): bool` — pure predicate; true only when every real branch's PR is merged (all-or-nothing, AC2).
- `classify_cleanup(stack_merge_state, dirty_porcelain): CleanupDecision` — pure classifier in `qrspi_cleanup.py`. `blocked` if `dirty_porcelain` non-empty (AC3); else `destroy` if `is_stack_fully_merged` else `skip` (AC2). Mirrors the `classify_result(rc, stdout, stderr)` shape (ref: Q14).
- `qrspi_cleanup.py --ticket <id> [--dry-run]` — one-shot CLI; self-locates `REPO_ROOT` from `__file__`, emits exactly one `CleanupEnvelope`, exit 0/1, reports infra error once as `ok:false` (ref: Q4). `--dry-run` gates ONLY the destructive execution; decision is computed identically (Decision 4).
- Reused as-is from existing scripts: `worktree_path`, `branch_set`, `slice_numbers`, `pick_tip`, `real_branches` (ref: Q3).
- Batch invocation contract: `qrspi-batch.js` calls `qrspi_cleanup.py` as a single verbatim command and folds the parsed envelope into its `results` array via `log(...)`/`summary` (ref: Q15).

## Slice 1: Merge-state gatherer in qrspi_pr_state.py

**Goal:** `qrspi_pr_state.py` can authoritatively answer "is this stack fully merged?" via a MERGED-aware GraphQL query and pure predicates, with existing OPEN-path callers unchanged. Testable end-to-end: feed GraphQL fixture nodes + branch list → get per-branch merged booleans and a stack-merged verdict.
**Files touched:**

- ⚠️ `scripts/qrspi_pr_state.py` — extend GraphQL query to surface MERGED state; add additive `merged`/`state`/`mergedAt` fields; add pure helpers `stack_merge_state(...)` and `is_stack_fully_merged(...)` (ref: Decision 1, Q2, Q7).
- ⚠️ `scripts/qrspi_pr_state_test.py` — add stdlib-only fixtures for the merge parser: fully-merged, partially-merged, in-flight (OPEN), and GitHub-already-deleted-ref cases (ref: Q13, Q14, OQ3).
**Verification:**
- [ ] `python3 scripts/qrspi_pr_state_test.py` passes, including new merge-state cases.
- [ ] Re-run existing resolver/restack tests to prove the additive fields broke no OPEN-path caller (`python3 scripts/qrspi_resolve_state_test.py` and siblings).
**Context cost:** M
**Depends on:** none

## Slice 2: qrspi_cleanup.py script (pure classifier + impure reap behind --dry-run)

**Goal:** A self-locating `qrspi_cleanup.py` that, for one ticket, classifies destroy/skip/blocked and (unless `--dry-run`) reaps worktree + local branches + merged remote refs, emitting one envelope. Testable end-to-end: unit tests drive the pure classifier across merged/partial/dirty/in-flight; manual `--dry-run` against a real stranded ticket previews the reap (AC5 preview).
**Files touched:**

- ✨ `scripts/qrspi_cleanup.py` — pure `classify_cleanup(stack_merge_state, dirty_porcelain)`; impure layer gathers merge state (via Slice 1 helpers), runs `git status --porcelain` (AC3, Q9), and on `destroy` executes `git worktree remove` + branch deletion + `gt sync --force` remote prune behind the `--dry-run` gate (Decision 2/3/4, Q5). Reuses `worktree_path`/`branch_set`/`slice_numbers`/`pick_tip`. Treats missing worktree/branch/remote ref as clean no-op success (Q11, Q12).
- ✨ `scripts/qrspi_cleanup_test.py` — stdlib-only, assert/`check()` style, dict/text fixtures for merged → destroy, partial → skip, dirty porcelain → blocked, in-flight → skip; NO subprocess mocks (ref: Q13, Q14).
**Verification:**
- [ ] `python3 scripts/qrspi_cleanup_test.py` passes all four classifier cases.
- [ ] Manual e2e: `python3 scripts/qrspi_cleanup.py --ticket <merged-id> --dry-run` prints a `destroy` envelope listing the worktree/branches/remotes it WOULD remove, touching nothing on disk.
- [ ] Manual e2e: dirty worktree yields a `blocked` envelope with the dirty state in `error`/`reason`.
**Context cost:** M
**Depends on:** Slice 1

## Slice 3: Orchestration wiring (batch land + reconciliation, work SKILL prose)

**Goal:** Cleanup runs automatically on land and a reconciliation pass reaps already-merged-but-uncleaned tickets, replacing the unsafe `--force 2>/dev/null` prose. Testable end-to-end: a land run invokes the script after merge; a reconciliation run enumerates stranded tickets and (dry-run first) reaps the backlog.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — (a) in `doLand`, replace prose worktree/branch removal with a verbatim single-command `qrspi_cleanup.py --ticket <id>` invocation after the bottom-up merge (AC1, ref: Q1, Q15); (b) add a reconciliation pass that enumerates candidate finished tickets (driven from git/GitHub, not Linear `Done` sweep — ref: Q8, OQ1) and runs cleanup per ticket, folding outcomes into `results` (AC4).
- ⚠️ `.claude/skills/qrspi-work/SKILL.md` — replace the `gt sync --force` / `git worktree remove --force` land-cleanup prose with the script invocation (ref: Q1, Q5).
**Verification:**
- [ ] Manual e2e land run: after `gt merge` succeeds, `doLand` invokes `qrspi_cleanup.py` and the ticket's worktree + branches are gone; envelope folded into `results`.
- [ ] Manual e2e reconciliation: run the new pass with dry-run, confirm it lists the stranded backlog (the ~27 worktrees / 20+ merged stacks, AC5), then a real run clears them.
- [ ] `qrspi-work/SKILL.md` no longer contains `git worktree remove --force` or `gt sync --force` cleanup prose.
**Context cost:** M
**Depends on:** Slice 2

---

## Unverified Assumptions

- **OQ1 — reconciliation candidate source.** Whether the batch reconciliation enumerates finished tickets from `.worktrees/*` dirs, from merged PRs on GitHub, or their intersection is unresolved in the design. Slice 3 assumes a git/GitHub-driven enumeration (not the Linear `Done` sweep), but the exact source needs a decision before planning.
- **OQ2 — blocked behavior during batch reconciliation.** Whether a `blocked` (dirty) ticket halts the reconciliation run or is logged-and-skipped while others proceed is open. Slice 3 leans toward log-and-continue (matching existing actions) but this is unverified.
- **OQ3 — query shape for deleted refs.** Whether matching `headRefName` with `states:MERGED` is sufficient, or branches GitHub has already deleted (no OPEN/MERGED PR returned by head ref) must also be reconciled, affects the Slice 1 GraphQL design. The "deleted-ref" test fixture is included defensively, but the canonical handling is unconfirmed.
- **OQ4 — default of `--dry-run` for the standalone CLI.** Whether `--dry-run` should be the default (opt-in to destroy) for safety vs. `doLand` always passing an explicit destroy flag is undecided. Slice 2 implements the flag but does not fix the default polarity.
- **AC5 backlog magnitude.** "27 worktrees / 20+ merged stacks" is a stated count from the design that cannot be verified from code; the actual stranded set is whatever the reconciliation enumerates at run time.
