# Structure Outline — qrspi_cleanup.py falsely reports remote branch deletion that never happened

**Design basis:** design.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## New Types

- `RemotePruneResult { removed: list[str], failedRemotes: list[str] }` — internal return of `_prune_remote_refs`, separating confirmed-deleted refs from attempted-but-still-present ones (replaces today's presence-list return).
- Envelope additive field: `failedRemotes: list[str]` — top-level (or alongside `removed.*`) list of `<ticket>/*` refs the run attempted to delete but that are still present on origin. Empty list = full success. Non-empty = retriable partial failure (`ok` stays `true`).

## Modified Types

- Cleanup result envelope (the JSON dict emitted by `run`) — add field `failedRemotes: list[str]` additively; do NOT rename or remove `removed.remotes` or any existing `removed.*` field (ref: design.md §Delta, §Risk Register row 4). `removed.remotes` now contains only confirmed-absent refs.

## Contracts

- `_stack_branches(ticket) -> list[str]` — UNCHANGED. Still enumerates locally-tracked `<ticket>/*` branch names from the main checkout. Remains one of two discovery inputs.
- `_remote_refs(ticket) -> list[str]` — read-only `git ls-remote --heads origin` snapshot, filtered to `<ticket>/*`. Origin-driven discovery authority (new or extracted; today this lives inline in `_prune_remote_refs`) (ref: design.md §Delta, Decision 2 Option A, RQ1).
- `_prune_remote_refs(ticket, branches, dry_run) -> RemotePruneResult` — performs the `gt`-mediated remote prune **while the local tracking ref still exists**, then confirms each candidate ref's absence via a post-prune read-only `git ls-remote`. Returns confirmed-absent refs in `removed`, still-present refs in `failedRemotes`. Dry-run mutates nothing and reports what would be deleted (ref: design.md §Delta, Decision 1 Option D, RQ3).
- `classify_cleanup(...) -> decision` — UNCHANGED (destroy/skip/blocked logic stays intact, out of scope; ref: RQ1).
- Stranded-ref reaping path (additive trigger) — when `classify_cleanup` returns `skip` *because the local branch set is empty* AND `_remote_refs` shows merged `<ticket>/*` refs on origin, an alternate reaping route runs `_prune_remote_refs` gated on the same fully-merged confirmation. `classify_cleanup` is not retriggered or re-thresholded (ref: design.md RQ1, Decision 2).
- `run(...) -> envelope dict` — ordering contract: the `gt`-driven remote prune runs **before** local-branch deletion (or re-establishes the tracking ref `gt` needs). Folds `_prune_remote_refs` output into `removed.remotes` (confirmed) and `failedRemotes` (survivors). `ok:true` even with non-empty `failedRemotes`; `ok:false` reserved for genuine infra errors (`gt`/git unreachable) (ref: design.md RQ2, RQ3).

## Slice 1: Real remote-ref deletion with confirmed-outcome reporting + origin-driven discovery + git-fixture test

**Goal:** `qrspi_cleanup.py` actually deletes a ticket's merged origin refs via `gt` (with correct ordering so `gt` has a live tracking ref), confirms absence by re-querying origin, reports only confirmed-absent refs in `removed.remotes`, lists survivors in `failedRemotes`, and discovers worktree-only stranded refs from the origin snapshot — all proven by a temp-repo + bare-origin fixture test that fails against today's presence-based reporting. This is the end-to-end correctness path (AC1–AC4).
**Files touched:**

- ⚠️ `scripts/qrspi_cleanup.py` — reorder the `gt`-driven remote prune before local-branch deletion (or re-establish the tracking ref); add post-prune read-only `git ls-remote` confirmation; populate `removed.remotes` from confirmed-absent refs only and `failedRemotes` from survivors; add origin-driven `<ticket>/*` discovery from the `git ls-remote` snapshot; add the additive stranded-ref reaping path for the empty-local-branch + merged-origin-refs case (gated on the same fully-merged confirmation; `classify_cleanup` untouched); add `failedRemotes` to the envelope additively; keep already-absent refs a clean no-op success; keep dry-run non-mutating (ref: design.md §Delta bullets 1–4, Decisions 1/2, RQ1/RQ2/RQ3).
- ⚠️ `scripts/qrspi_cleanup_test.py` — add fixture-backed test: temp git repo + local bare repo as "origin", create merged `<ticket>/*` refs, run `_prune_remote_refs`/`run`, assert post-run `git ls-remote` shows the refs gone and `removed.remotes` matches reality; add a worktree-only / empty-local-branch case asserting stranded refs are discovered and deleted (AC3); add a survivor case asserting a still-present ref lands in `failedRemotes` and not `removed.remotes` (AC2). Skip-guard if `git` is absent; keep existing pure `classify_cleanup` tests intact (ref: design.md Decision 3 Option A, AC4, §Risk Register row 3 — NEW PATTERN: a git-fixture test departing from the stdlib-only/pure-classifier convention).
**Verification:**
- [ ] `python3 scripts/qrspi_cleanup_test.py` — the new fixture test passes; confirm it FAILS when reverting just the reporting change (proves it catches presence-based false success, AC4).
- [ ] Worktree-only case: with an empty local branch set and merged `<ticket>/*` refs on the bare origin, post-run `git ls-remote` shows the refs gone and they appear in `removed.remotes` (AC3).
- [ ] Survivor case: a ref that remains present after the prune appears in `failedRemotes`, is absent from `removed.remotes`, and the envelope is `ok:true` (AC2, RQ2).
- [ ] Dry-run: envelope reports candidate refs but `git ls-remote` shows origin unchanged (idempotency/dry-run constraint).
- [ ] Existing pure `classify_cleanup` tests still pass unchanged.
**Context cost:** M
**Depends on:** none

## Slice 2: Batch consumer surfaces failedRemotes and schedules Reconcile retry

**Goal:** The batch orchestrator reads the new `failedRemotes` field, logs stranded refs so the operator sees them, and on a non-empty `failedRemotes` schedules the ticket for a Reconcile retry rather than halting — verified end-to-end against a cleanup envelope carrying `failedRemotes`.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — surface `failedRemotes` in the cleanup log line at ~`:816-817`; on non-empty `failedRemotes` schedule a Reconcile retry instead of a halt; treat `ok:true` + non-empty `failedRemotes` as retriable (not a hard stop), and keep `ok:false` as the only halt condition; do not break parsing of existing `removed.*` fields (`parseCleanupEnvelope` / the Reconcile-retry trigger updated in lockstep) (ref: design.md §Delta bullet 5, RQ2, §Risk Register row 4).
**Verification:**
- [ ] Feed the consumer a cleanup envelope with non-empty `failedRemotes` (ok:true): the log line includes the stranded refs and the ticket is scheduled for a Reconcile retry, not halted.
- [ ] Envelope with empty `failedRemotes`: no retry scheduled, existing behavior unchanged.
- [ ] Envelope with `ok:false`: still halts (HARD-STOP semantics preserved).
- [ ] An envelope lacking `failedRemotes` (back-compat) is parsed without error.
**Context cost:** S
**Depends on:** Slice 1 (envelope shape — the `failedRemotes` field — must exist first)

---

## Unverified Assumptions

- **`gt` can prune a single remote ref while the local tracking branch exists, with observable per-ref outcome.** Decision 1 Option D / RQ3 require staying within `gt` and assume that reordering the `gt`-driven prune before local-branch deletion (or re-establishing the tracking ref) makes `gt` actually mutate origin per-ref. The design does not name the exact `gt` subcommand/flags that achieve a per-ref (vs. all-at-once `gt sync --force`) remote prune. The implementer must confirm which `gt` invocation deletes the intended ref(s) without deleting unrelated branches — and whether per-ref granularity is achievable at all under `gt`, or whether confirmation must compensate for coarser-grained mutation.
- **The fully-merged confirmation gate for the additive stranded-ref path is concretely derivable for worktree-only refs.** RQ1 / Risk Register row 1 require that a stranded ref is only deleted "once its PR is confirmed merged," but with no local branch and a removed worktree, the design does not specify the concrete source of merged-state truth (e.g. a `gh` PR-state query keyed on the ref name vs. an existing helper). The implementer must identify how merged-state is established for a ref that exists only on origin.
- **The exact location and current shape of the batch consumer's cleanup-envelope parsing.** The design cites `.claude/workflows/qrspi-batch.js:816-817` and a `parseCleanupEnvelope`/log line, but the precise function names and the Reconcile-retry scheduling mechanism are not pinned in the Delta; Slice 2 assumes a Reconcile-retry path already exists to hook into. The implementer must confirm the consumer's current parse/retry structure before wiring the additive field in.
