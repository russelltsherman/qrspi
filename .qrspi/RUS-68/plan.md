# Implementation Plan — qrspi_cleanup.py falsely reports remote branch deletion that never happened

**Structure basis:** structure.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total steps:** 24

## Slice 1: Real remote-ref deletion with confirmed-outcome reporting + origin-driven discovery + git-fixture test

### Setup

1. ⚠️ Modify `scripts/qrspi_cleanup.py` — introduce the `RemotePruneResult` shape as a small return container near the existing helpers (use a `dict` literal or a stdlib `dataclass`/`NamedTuple`, matching the file's current style).
   - **Current:** `_prune_remote_refs` returns a presence-derived `list[str]`.
   - **After:** a `RemotePruneResult { removed: list[str], failedRemotes: list[str] }` is the declared return container, separating confirmed-deleted refs from attempted-but-still-present refs.

2. ⚠️ Modify `scripts/qrspi_cleanup.py` — extract origin discovery into a dedicated read-only helper `_remote_refs(ticket) -> list[str]`.
   - **Current:** `git ls-remote --heads origin` filtering lives inline inside `_prune_remote_refs`.
   - **After:** `_remote_refs(ticket) -> list[str]` returns the `<ticket>/*`-filtered `git ls-remote --heads origin` snapshot; it is the single origin-driven discovery authority (ref: structure Contracts, design Decision 2 Option A, RQ1).

### Core Logic

3. ⚠️ Modify `scripts/qrspi_cleanup.py` — confirm `_stack_branches(ticket) -> list[str]` stays UNCHANGED (still enumerates locally-tracked `<ticket>/*` from the main checkout) and is consumed as one of two discovery inputs alongside `_remote_refs` (ref: structure Contracts).
   - **Current:** `_stack_branches(ticket) -> list[str]` — local-branch enumeration.
   - **After:** identical signature/behavior; now unioned with `_remote_refs` output at the discovery site.

4. ⚠️ Modify `scripts/qrspi_cleanup.py` — rewrite `_prune_remote_refs` to perform the `gt`-mediated remote prune **while the local tracking ref still exists**, per-ref where `gt` allows; remote mutation stays within `gt` (no `git push origin --delete`) (ref: design Decision 1 Option D, RQ3).
   - **Current:** `_prune_remote_refs(ticket, branches, dry_run)` runs the prune after local branches are already gone and returns the pre-deletion presence list.
   - **After:** `_prune_remote_refs(ticket, branches, dry_run) -> RemotePruneResult` runs the `gt`-driven prune with a live tracking ref.

5. ⚠️ Modify `scripts/qrspi_cleanup.py` — add post-prune confirmation inside `_prune_remote_refs`: re-query origin via read-only `git ls-remote` and partition candidates into confirmed-absent (`removed`) vs. still-present (`failedRemotes`) (ref: design §Delta bullet 2, AC1, AC2).
   - **Current:** no re-check of origin; presence list returned regardless of deletion outcome.
   - **After:** `_prune_remote_refs` returns `RemotePruneResult{removed=<confirmed-absent>, failedRemotes=<still-present>}`.

6. ⚠️ Modify `scripts/qrspi_cleanup.py` — keep dry-run non-mutating in `_prune_remote_refs`: when `dry_run` is set, report candidate refs as `removed` (would-delete) without invoking any mutating `gt` command and without altering origin (ref: structure Contracts, AC4 dry-run constraint).
   - **Current:** dry-run reports the presence list.
   - **After:** dry-run reports candidates, mutates nothing, performs no destructive `gt` call.

7. ⚠️ Modify `scripts/qrspi_cleanup.py` — keep already-absent refs a clean no-op success: a candidate already absent from the post-prune `git ls-remote` is treated as deleted (lands in `removed`, never `failedRemotes`) (ref: design Risk Register row 5, AC1 idempotency).
   - **Current:** already-absent refs silently excluded by the `if b in present` filter.
   - **After:** already-absent refs counted as confirmed-removed no-op.

8. ⚠️ Modify `scripts/qrspi_cleanup.py` — reorder the destroy path in `run(...)` so the `gt`-driven remote prune runs **before** local-branch deletion (or re-establishes the tracking ref `gt` needs) (ref: design Decision 1 Option D, RQ3, structure `run` contract).
   - **Current:** destroy order is remove worktree → delete local branches → prune remote (so `gt` keys off already-deleted branches).
   - **After:** remote prune (or tracking-ref re-establishment) precedes local-branch deletion.

9. ⚠️ Modify `scripts/qrspi_cleanup.py` — add the additive stranded-ref reaping path in `run(...)`: when `classify_cleanup` returns `skip` *because the local branch set is empty* AND `_remote_refs` shows merged `<ticket>/*` refs on origin, run `_prune_remote_refs` over those origin-discovered refs; `classify_cleanup` is NOT retriggered, reordered, or re-thresholded (ref: design RQ1, Risk Register rows 1–2).
   - **Current:** empty local branch set → `skip` → orphaned refs never discovered/deleted.
   - **After:** alternate reaping route deletes worktree-only stranded refs, gated on the same fully-merged confirmation; `classify_cleanup` untouched.

10. ⚠️ Modify `scripts/qrspi_cleanup.py` — gate the stranded-ref reaping path on the same fully-merged confirmation the documented logic requires (a ref is only deleted once its PR is confirmed merged), so the destroy decision is never overridden (ref: design RQ1, Risk Register row 1).
    - **Current:** no merged-state gate on origin-only refs.
    - **After:** stranded-ref deletion only proceeds when the `<ticket>/*` refs are confirmed fully merged.

11. ⚠️ Modify `scripts/qrspi_cleanup.py` — fold `_prune_remote_refs` output into the envelope in `run(...)`: populate `removed.remotes` from `RemotePruneResult.removed` (confirmed-absent only) and add a top-level `failedRemotes` list from `RemotePruneResult.failedRemotes` (ref: structure `run` contract, design §Delta bullet 4).
    - **Current:** `removed.remotes` populated from the presence list; no `failedRemotes` field.
    - **After:** `removed.remotes` = confirmed-absent refs; `failedRemotes` = survivors, added additively (no rename/removal of any `removed.*` field).

12. ⚠️ Modify `scripts/qrspi_cleanup.py` — set envelope `ok` semantics: `ok:true` even when `failedRemotes` is non-empty (retriable partial failure); reserve `ok:false` for genuine infra errors (`gt`/git unreachable) (ref: design RQ2, structure `run` contract).
    - **Current:** zero-exit run reports `ok:true` with presence list as "deleted"; non-zero `gt` exit raises → `ok:false`.
    - **After:** partial failure → `ok:true` + non-empty `failedRemotes`; `ok:false` only on infra error.

### Tests

13. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — add a fixture helper that builds a temp git repo + a local bare repo as "origin", with a `git`-absent skip-guard (ref: structure Files touched, design Decision 3 Option A, Risk Register row 3).
    - **Current:** stdlib-only, exercises only pure `classify_cleanup`; no temp repo/fake remote/subprocess.
    - **After:** a reusable fixture stands up a temp repo + bare origin and skip-guards when `git` is unavailable.

14. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — add the core deletion test: create merged `<ticket>/*` refs on the bare origin, run `_prune_remote_refs`/`run`, assert post-run `git ls-remote` shows the refs gone and `removed.remotes` matches reality (ref: structure Verification bullet 1, AC1, AC4).
    - **Current:** no test observes post-run remote state.
    - **After:** test asserts actual origin absence equals `removed.remotes`.

15. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — assert the test FAILS when only the reporting change is reverted (proves it catches presence-based false success) (ref: structure Verification bullet 1, AC4).
    - **Current:** no regression guard for the false-success bug.
    - **After:** test documented/structured to fail against today's presence-based reporting.

16. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — add the worktree-only case: empty local branch set + merged `<ticket>/*` refs on the bare origin; assert post-run `git ls-remote` shows the refs gone and they appear in `removed.remotes` (ref: structure Verification bullet 2, AC3).
    - **Current:** worktree-only scenario untested.
    - **After:** test proves stranded refs are discovered and deleted via the additive path.

17. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — add the survivor case: a ref that remains present after the prune lands in `failedRemotes`, is absent from `removed.remotes`, and the envelope is `ok:true` (ref: structure Verification bullet 3, AC2, RQ2).
    - **Current:** no test distinguishes deleted from survived refs.
    - **After:** test asserts survivor → `failedRemotes`, not `removed.remotes`, `ok:true`.

18. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — add the dry-run case: envelope reports candidate refs but post-run `git ls-remote` shows origin unchanged (ref: structure Verification bullet 4, idempotency/dry-run constraint).
    - **Current:** no dry-run mutation guard.
    - **After:** test asserts dry-run mutates nothing.

19. ⚠️ Modify `scripts/qrspi_cleanup_test.py` — confirm the existing pure `classify_cleanup` tests remain intact and unchanged alongside the new fixture tests (ref: structure Verification bullet 5, design Risk Register row 3).
    - **Current:** pure `classify_cleanup` tests are the only tests.
    - **After:** they pass unchanged next to the new fixture-backed tests.

20. Run: `python3 scripts/qrspi_cleanup_test.py`
    - **Expected:** all tests pass (or skip cleanly when `git` is absent); pure `classify_cleanup` tests unchanged.

### Verify Slice 1

21. **Checkpoint:** `python3 scripts/qrspi_cleanup_test.py`
    - [ ] New fixture test passes; it FAILS when reverting just the reporting change (catches presence-based false success, AC4).
    - [ ] Worktree-only case: empty local branch set + merged origin refs → post-run `git ls-remote` shows refs gone and they appear in `removed.remotes` (AC3).
    - [ ] Survivor case: a still-present ref appears in `failedRemotes`, is absent from `removed.remotes`, envelope is `ok:true` (AC2, RQ2).
    - [ ] Dry-run: envelope reports candidate refs but `git ls-remote` shows origin unchanged.
    - [ ] Existing pure `classify_cleanup` tests still pass unchanged.

---

## Slice 2: Batch consumer surfaces failedRemotes and schedules Reconcile retry

### Core Logic

22. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — surface `failedRemotes` in the cleanup log line at ~`:816-817` so stranded refs are visible to the operator; do not break parsing of existing `removed.*` fields (ref: structure Files touched, design §Delta bullet 5).
    - **Current:** cleanup log line at ~`:816-817` logs `removed.*` only; `failedRemotes` not read.
    - **After:** the log line includes `failedRemotes` (stranded refs) alongside the existing fields; `parseCleanupEnvelope` reads the additive field, tolerating its absence (back-compat).

23. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — on `ok:true` + non-empty `failedRemotes`, schedule the ticket for a Reconcile retry instead of halting; keep `ok:false` as the only halt condition (ref: structure Files touched, design RQ2, Risk Register row 4).
    - **Current:** partial-failure handling halts (or treats non-empty result as terminal); only `ok:false` distinguished.
    - **After:** `ok:true` + non-empty `failedRemotes` → retriable Reconcile-retry schedule; empty `failedRemotes` → unchanged existing behavior; `ok:false` → still halts (HARD-STOP preserved); an envelope lacking `failedRemotes` parses without error.

### Verify Slice 2

24. **Checkpoint:** manually feed the cleanup consumer in `.claude/workflows/qrspi-batch.js` representative envelopes (end-to-end, per project convention — the eval harness is a placeholder).
    - [ ] Envelope with non-empty `failedRemotes` (ok:true): log line includes the stranded refs and the ticket is scheduled for a Reconcile retry, not halted.
    - [ ] Envelope with empty `failedRemotes`: no retry scheduled, existing behavior unchanged.
    - [ ] Envelope with `ok:false`: still halts (HARD-STOP semantics preserved).
    - [ ] Envelope lacking `failedRemotes` (back-compat): parsed without error.

---

## Rollback Notes

- **Steps 4–12 (destructive remote mutation in `qrspi_cleanup.py`):** these change real `gt`-mediated origin-ref deletion and its ordering. If a regression strands or wrongly deletes refs, revert `scripts/qrspi_cleanup.py` to the prior commit; the change is self-contained to that one file. Validate any rollback with `python3 scripts/qrspi_cleanup_test.py`. The fixture test uses a local bare repo (no network), so reverting the test (Steps 13–19) leaves no external state behind — simply delete the temp fixtures.
- **Steps 11–12 (envelope shape — additive `failedRemotes`):** the field is additive and `removed.*` is never renamed/removed, so the batch consumer (Slice 2) tolerates its absence; if Slice 2 must be rolled back independently, revert `.claude/workflows/qrspi-batch.js` alone — the producer remains back-compatible.
- **Steps 22–23 (`.claude/workflows/qrspi-batch.js`):** consumer-only logic change (logging + Reconcile-retry scheduling). Revert the single file to restore prior halt behavior; no persisted state or migration involved.
