# PR: RUS-68 Fix false-success remote-ref cleanup reporting in qrspi_cleanup

**Ticket:** RUS-68
**Design:** design.md @ 2026-06-11T00:00:00Z
**Structure:** structure.md @ 2026-06-11T00:00:00Z

## Summary

`qrspi_cleanup.py` reported origin refs as deleted based on pre-deletion
*presence*, not on any confirmed deletion — and its only remote-mutating call
(`gt sync --force`) ran *after* the local branches it keys off were already
gone, so it frequently deleted nothing while still reporting success. This PR
makes the remote prune run while the local tracking ref still exists, confirms
each ref's absence with a read-only `git ls-remote` before reporting it, and
splits the outcome into `removed.remotes` (confirmed-absent only) and a new
additive `failedRemotes` list (attempted-but-still-present, retriable). It also
adds an origin-driven discovery path so worktree-only stranded refs (the RUS-40
case) are found and reaped without changing `classify_cleanup`, and surfaces
`failedRemotes` to the batch orchestrator, which now schedules a Reconcile
retry instead of halting. Reviewer focus: (1) the prune→confirm ordering and
the `gt`-only mutation seam (`_gt_prune_remotes`) in `qrspi_cleanup.py`, and
(2) the `ok:true` + non-empty-`failedRemotes` retriable contract in the batch
consumer (`ok:false` stays reserved for genuine infra errors).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: a ref reported in `removed.remotes` is genuinely gone from origin (deleted, then confirmed absent) | `scripts/qrspi_cleanup.py:_prune_remote_refs` (post-prune `git ls-remote` confirm) + `_gt_prune_remotes` | `scripts/qrspi_cleanup_test.py` worktree-only/merged-ref fixture case (post-run `git ls-remote` shows ref gone, appears in `removed.remotes`) |
| AC2: `removed.remotes` lists only deleted refs; a failed-to-delete ref is excluded and surfaced as failure | `scripts/qrspi_cleanup.py:_prune_remote_refs` (removed/failedRemotes partition) | `scripts/qrspi_cleanup_test.py` survivor case (survivor in `failedRemotes`, absent from `removed.remotes`, `ok:true`) |
| AC3: worktree-only merged refs are discovered and deleted (origin-driven discovery) | `scripts/qrspi_cleanup.py:_remote_refs` + additive stranded-ref reaping path in `run` | `scripts/qrspi_cleanup_test.py` empty-local-branch + merged-origin-refs case |
| AC4: a test exercises real deletion and fails against presence-based reporting | `scripts/qrspi_cleanup_test.py` (temp repo + bare-origin fixture) | `python3 scripts/qrspi_cleanup_test.py` — proven to FAIL when reporting is reverted to presence-based |

## Changes by Slice

### Slice 1: Real remote-ref deletion with confirmed-outcome reporting + origin-driven discovery + git-fixture test

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_cleanup.py` | ⚠️ modified | +~170, -~25 |
| `scripts/qrspi_cleanup_test.py` | ⚠️ modified | +~265, -~5 |

Adds `RemotePruneResult`, `_remote_refs` (read-only origin discovery), the
`_gt_prune_remotes` mutation seam (`gt sync --force`, the only remote-mutating
call), the reorder-before-local-delete + post-prune `git ls-remote`
confirmation in `_prune_remote_refs` (signature gained a leading `ticket`
arg), the additive stranded-ref reaping path in `run`, and the additive
top-level `failedRemotes` envelope field. Test file adds the git-fixture suite
(temp repo + local bare origin), skip-guarded on `git` availability.

### Slice 2: Batch consumer surfaces failedRemotes and schedules Reconcile retry

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +~45, -~6 |

Adds `cleanupFailedRemotes(cl)` (defensive read → `[]`), surfaces `STRANDED
remotes [...]` in the Finalize/Reconcile log lines, carries `failedRemotes` +
a `reconcileRetry` boolean on the land result, and makes `processed.add(t.id)`
conditional on `!res.reconcileRetry` so a partial-failure ticket stays
eligible for the Reconcile pass. `ok:false` remains the only hard stop.

## Testing Summary

- [x] Slice 1: unit + git-fixture — `python3 scripts/qrspi_cleanup_test.py` — 25 passed, 0 failed (8 pure `classify_cleanup` + 17 fixture)
- [x] Slice 1: AC4 negative control — buggy presence-based `_prune_remote_refs` run in-memory → fixture FAILS (survivor expected in `failedRemotes`, buggy code reported it `removed`)
- [x] Slice 2: syntax — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] Slice 2: end-to-end envelope harness (4 required + 2 defensive cases) — 15 passed, 0 failed (verbatim `extractJsonObject`/`parseCleanupEnvelope`/`cleanupFailedRemotes` + distilled land/processed-exclusion logic; harness in `/tmp`, removed after run per eval-placeholder convention)
- [x] Manual verification: dry-run reports candidate in `removed` while origin `git ls-remote` is unchanged (no gt seam call); back-compat — an envelope lacking `failedRemotes` parses without error and triggers no retry

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `RemotePruneResult` | `dict` / stdlib `dataclass` / `NamedTuple` | small `__slots__` class with `__eq__`/`__repr__` | Plan permitted matching file style; file has no existing dataclass/NamedTuple. Public shape (`removed: list[str]`, `failedRemotes: list[str]`) matches structure §Types exactly. |
| `_prune_remote_refs` granularity (Unverified-Assumption-1) | per-ref `gt` prune | coarse `gt sync --force` isolated in `_gt_prune_remotes` seam, compensated by post-prune `git ls-remote` confirm | `gt sync` is whole-repo merged-branch prune; per design Decision D the read-only confirmation partitions survivors into `failedRemotes`, so coarseness never yields a false `removed`. Seam exists so the offline fixture can drive a deterministic origin mutation. |
| Reconcile retry scheduler (Unverified-Assumption-3) | a dedicated retry scheduler to hook into | reuse existing opt-in Reconcile pass (`runReconciliation`) via `reconcileRetry` flag + conditional `processed.add` | No standalone scheduler exists; inventing one would duplicate the existing reconcile path and exceed slice scope. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Origin-driven discovery deletes refs it shouldn't (e.g. still-open `<ticket>/*` PR ref) | mitigated — stranded-ref path gated on same fully-merged confirmation; `classify_cleanup` untouched | Revert `scripts/qrspi_cleanup.py` to remove the additive `run` reaping path |
| `skip` on empty local-branch set means destroy never runs / AC3 unreached | mitigated — additive alternate trigger (empty local set + merged origin refs) deletes without retriggering `classify_cleanup` | Remove the additive reaping branch in `run`; classifier behavior unchanged |
| Git-fixture test flaky/unavailable in CI/sandbox | mitigated — local bare origin (no network); `_git_available()` skip-guard prints `SKIP` and runs only pure tests | None needed; pure-classifier tests remain green standalone |
| Envelope `failedRemotes` semantics break the batch consumer parser | mitigated — additive field, no rename/removal of `removed.*`; consumer `cleanupFailedRemotes` coerces missing/non-array to `[]`; partial failure is `ok:true` not `ok:false` | Revert `.claude/workflows/qrspi-batch.js`; producer field is additive and ignored by older consumers |
| Already-absent ref races idempotency | mitigated — already-absent treated as clean no-op success; outcome confirmed via `git ls-remote`, not push rc | n/a |

No new risks discovered during implementation.

## Open Items

- Per-ref `gt` remote pruning is not available; the implementation uses
  coarse `gt sync --force` + read-only confirmation (Unverified-Assumption-1
  resolved as a coarse-mutate-then-confirm seam). If a future `gt` gains
  per-ref prune, `_gt_prune_remotes` is the single seam to upgrade.
- The fully-merged confirmation source for worktree-only refs
  (Unverified-Assumption-2) is satisfied via `is_stack_fully_merged` on the
  origin snapshot; no follow-up required, noted for traceability.
- The Reconcile retry relies on the existing opt-in Reconcile pass being
  enabled in a given batch run; a still-present ref otherwise persists in the
  backlog until a run with the pass enabled re-attempts it. No dedicated
  retry queue was introduced (out of slice scope).
