# Work Tree — qrspi_cleanup.py falsely reports remote branch deletion that never happened

**Plan basis:** plan.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T4 → T5 → T8 → T11 → T12 → T13 → T14 → T15 → T22 → T23 → T24

## Session 1 — Slice 1 producer: real remote-ref deletion + confirmed-outcome reporting

**Load:** structure.md §Contracts, structure.md §Types (`RemotePruneResult`), plan.md §Slice 1 (steps 1–12), design.md Decision 1 Option D, design.md Decision 2 Option A, design.md §Delta bullets 2 & 4
**Estimated context:** ~28% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Introduce `RemotePruneResult{removed, failedRemotes}` return container in `qrspi_cleanup.py` | — | §1.1 | S | pending |
| T2 | Extract origin discovery into read-only `_remote_refs(ticket) -> list[str]` | T1 | §1.2 | S | pending |
| T3 | Confirm `_stack_branches` stays UNCHANGED; union it with `_remote_refs` at discovery site | T2 | §1.3 | S | pending |
| T4 | Rewrite `_prune_remote_refs` to prune via `gt` while local tracking ref still exists | T1 | §1.4 | M | pending |
| T5 | Add post-prune confirmation: re-query origin via `git ls-remote`, partition into `removed` vs `failedRemotes` | T4 | §1.5 | M | pending |
| T6 | Keep dry-run non-mutating: report candidates as `removed`, invoke no mutating `gt` | T4 | §1.6 | S | pending |
| T7 | Keep already-absent refs a clean no-op success (land in `removed`, never `failedRemotes`) | T5 | §1.7 | S | pending |
| T8 | Reorder destroy path in `run(...)` so remote prune precedes local-branch deletion | T4 | §1.8 | M | pending |
| T9 | Add additive stranded-ref reaping path in `run(...)` for empty-local-set + merged origin refs; `classify_cleanup` untouched | T2, T8 | §1.9 | M | pending |
| T10 | Gate stranded-ref reaping on the same fully-merged confirmation | T9 | §1.10 | S | pending |
| T11 | Fold `RemotePruneResult` into envelope: `removed.remotes`=confirmed-absent, add top-level `failedRemotes` | T5, T8 | §1.11 | M | pending |
| T12 | Set envelope `ok` semantics: `ok:true` on non-empty `failedRemotes`; `ok:false` only on infra error | T11 | §1.12 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Producer logic complete and self-consistent. The test suite (Slice 1 Tests) loads a different concern — git-fixture/bare-origin scaffolding and verification — and only depends on the now-stable producer contract, so a fresh context keeps the test session focused and under budget.

## Session 2 — Slice 1 tests: git-fixture suite + verification checkpoint

**Load:** structure.md §Files touched, structure.md §Verification (bullets 1–5), plan.md §Slice 1 Tests (steps 13–21), design.md Decision 3 Option A, design.md Risk Register rows 3 & 5, impl-log.md §Slice 1 producer (notes only — final `_prune_remote_refs`/`run`/`RemotePruneResult` signatures)
**Estimated context:** ~26% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Add fixture helper: temp git repo + local bare "origin" with `git`-absent skip-guard | T12 | §1.13 | M | pending |
| T14 | Core deletion test: merged origin refs → post-run `git ls-remote` shows gone, `removed.remotes` matches | T13 | §1.14 | M | pending |
| T15 | Assert test FAILS when only the reporting change is reverted (catches presence-based false success) | T14 | §1.15 | S | pending |
| T16 | Worktree-only test: empty local set + merged origin refs → refs gone, in `removed.remotes` | T13 | §1.16 | M | pending |
| T17 | Survivor test: still-present ref lands in `failedRemotes`, absent from `removed.remotes`, `ok:true` | T13 | §1.17 | M | pending |
| T18 | Dry-run test: envelope reports candidates but origin unchanged | T13 | §1.18 | S | pending |
| T19 | Confirm existing pure `classify_cleanup` tests remain intact and unchanged | T13 | §1.19 | S | pending |
| T20 | Run `python3 scripts/qrspi_cleanup_test.py` — all pass or skip cleanly when `git` absent | T14, T15, T16, T17, T18, T19 | §1.20 | S | pending |
| T21 | **Verify Slice 1** checkpoint (all AC1–AC4 boxes + classify regression) | T20 | §1.21 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (producer + tests) complete and verified. Slice 2 is a separate file (`qrspi-batch.js` consumer) gated only on Slice 1's now-stable additive envelope shape. Fresh context drops the Python-side detail and loads the JS consumer concern.

## Session 3 — Slice 2: batch consumer surfaces failedRemotes + Reconcile retry

**Load:** structure.md §Files touched (`qrspi-batch.js`), structure.md §Verification, plan.md §Slice 2 (steps 22–24), design.md §Delta bullet 5, design.md RQ2, design.md Risk Register row 4, impl-log.md §Slice 1 (notes only — final `failedRemotes` envelope field + `ok` semantics)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T22 | Surface `failedRemotes` in cleanup log line (~`:816-817`); `parseCleanupEnvelope` tolerates its absence | T12 | §2.22 | S | pending |
| T23 | On `ok:true` + non-empty `failedRemotes`, schedule Reconcile retry; keep `ok:false` as sole halt | T22 | §2.23 | M | pending |
| T24 | **Verify Slice 2** checkpoint (non-empty/empty/`ok:false`/back-compat envelopes, end-to-end) | T23 | §2.24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. All slices implemented and verified; stack ready for PR preparation.
