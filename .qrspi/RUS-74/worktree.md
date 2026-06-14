# Work Tree — qrspi-batch trunk-sync hardening: never build a dependent ticket on a stale local main

**Plan basis:** plan.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T9 → T10 (Slice 1) → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T18 (Slice 2)

## Session 1

**Load:** structure.md §New Types, structure.md §Contracts (classify_sync, token→field mapping, _run/main), plan.md §Slice 1, design.md §Decision 1
**Estimated context:** ~22% of window

Slice 1 is self-contained: it creates two new files (`scripts/qrspi_sync_trunk.py` and its test sibling) with no callers until Slice 2. The classifier and envelope mapping (T2, T3) are pure and gate everything downstream.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_sync_trunk.py` with self-locating module preamble (ENGINE_ROOT, REPO_ROOT via qrspi_paths.resolve_repo_root, stdlib imports) | — | §1.1 | S | pending |
| T2 | Add pure `classify_sync(...)` with the six-token precedence chain (not-on-main → dirty → fetch-failed → already-current → divergent → updated) | T1 | §1.2 | M | pending |
| T3 | Add pure token→envelope mapping helper producing SyncEnvelope dicts (incl. repoRoot in every envelope) | T2 | §1.3 | M | pending |
| T4 | Add impure shell `_run(argv)`: HEAD-branch read first (short-circuit), porcelain/fetch/rev-parse/merge-base, feed classify_sync, ff-only merge only on "updated", print envelope, return rc | T3 | §1.4 | M | pending |
| T5 | Add `main()` + `if __name__ == "__main__"` guard | T4 | §1.5 | S | pending |
| T6 | Create `scripts/qrspi_sync_trunk_test.py` — pure-classifier cases for all six tokens (incl. non-main branch and detached None HEAD) | T2 | §1.6 | M | pending |
| T7 | Add precedence-order assertions: not-on-main beats dirty; dirty beats fetch-failed | T6 | §1.7 | S | pending |
| T8 | Add impure-path test via subprocess/symbolic-ref fake-handler swap: token→envelope mapping + non-main HEAD short-circuits with no fetch/merge invoked | T4, T6 | §1.8 | M | pending |
| T9 | Run `python3 scripts/qrspi_sync_trunk_test.py` | T5, T7, T8 | §1.9 | S | pending |
| T10 | **Verify Slice 1** — all six tokens, precedence orderings, impure mapping + no-fetch/no-merge short-circuit pass | T9 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (new helper + tests, no callers). Fresh context for Slice 2, which wires the helper into the JS orchestrator — a different file and concern, so the Slice 1 Python detail is no longer needed (only its envelope contract).

## Session 2

**Load:** structure.md §Contracts (JS orchestrator, Modified Types), plan.md §Slice 2, design.md §Decision 2, §Decision 3, impl-log.md §Slice 1 (SyncEnvelope shape only)
**Estimated context:** ~25% of window

Slice 2 wires `scripts/qrspi_sync_trunk.py` into `.claude/workflows/qrspi-batch.js` at run-start (AC2) and post-land (AC3), and surfaces verbatim land-conflict reasons (AC4). All edits are in one file; the two parse/helper additions (T11, T12) gate the three call-site edits.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Add `parseSyncTrunkEnvelope(text)` to qrspi-batch.js, mirroring `parseRestackEnvelope` (validate ok bool; on ok, updated/from/to present; throw on malformed) | T10 | §2.11 | S | pending |
| T12 | Add `syncTrunk(phaseLabel)` to qrspi-batch.js — spawn main-checkout worker running `engineCmd('scripts/qrspi_sync_trunk.py')`, parse via parseSyncTrunkEnvelope | T11 | §2.12 | M | pending |
| T13 | (AC2) Insert run-start `await syncTrunk(...)` after Query scope resolution, before the per-ticket loop; throw on non-ok to abort the run | T12 | §2.13 | M | pending |
| T14 | (AC3) In `doLand`, add post-land `await syncTrunk(...)` gated on `verdict.status === 'landed'` beside runCleanup; throw on non-ok | T12 | §2.14 | M | pending |
| T15 | (AC4) Update `doLand` land-worker prompt to return verbatim conflict reason in the already-declared `error` field | — | §2.15 | S | pending |
| T16 | (AC4) Change `finResult` failure summary to `fin?.error ?? fin?.summary ?? 'unknown'` | T15 | §2.16 | S | pending |
| T17 | Run `node --check .claude/workflows/qrspi-batch.js` | T13, T14, T16 | §2.17 | S | pending |
| T18 | **Verify Slice 2** — node --check passes; both syncTrunk call sites throw on non-ok; finResult/prompt edits in place | T17 | §2.18 | S | pending |
| T19 | **Verify Slice 2 (manual e2e, AC5)** — run batch where origin/main is ahead: local main FF-advances before any worktree cut; divergent main aborts loud with verbatim reason | T18 | §2.19 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** End of plan. All slices implemented and verified; no further session.
