# Implementation Log — qrspi_cleanup.py falsely reports remote branch deletion that never happened

## Session 1 — Slice 1

**Timestamp:** 2026-06-11T20:55:03Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_cleanup_test.py` → 25 passed, 0 failed (8 pure classifier + 17 fixture; run after Session 2 added the fixture suite)

**Deviations from structure.md:**

- `RemotePruneResult` is a small `__slots__` class (with `__eq__`/`__repr__` for tests) rather than a `dict`/`NamedTuple`/`dataclass`. The plan permitted "a `dict` literal or a stdlib `dataclass`/`NamedTuple`, matching the file's current style"; the file has no existing dataclass/NamedTuple usage, so a lightweight class keeps the `.removed` / `.failedRemotes` attribute access the contract names. Public shape (`removed: list[str]`, `failedRemotes: list[str]`) matches the structure §Types exactly.

**Deviations from plan.md:**

- none in producer behavior. One design-level resolution of structure §Unverified-Assumption-1 (gt granularity): the actual remote MUTATION is isolated in a new `_gt_prune_remotes(branches)` seam that calls `gt sync --force` (RQ3-compliant, no `git push origin --delete` in the real path). `_prune_remote_refs` keeps the full discovery → gt-mutate → read-only `git ls-remote` confirm → removed/failedRemotes partition logic around it. `gt sync` remains coarse-grained (whole-repo merged-branch prune, not per-ref); per design Decision D the post-prune `git ls-remote` confirmation compensates for that coarseness — a ref still present after the prune lands in `failedRemotes`, never `removed`. The seam exists so the offline fixture test (binding AC4 / Decision 3 Option A) can drive a deterministic origin mutation without a live Graphite/GitHub PR state, while still exercising the real confirmation/partition path against a real bare origin.

**Notes for next session:**

- Final signatures (for Slice 2 / qrspi-batch.js consumer):
  - Envelope now carries a top-level `failedRemotes: list[str]` (sorted, always present, `[]` when full success). `removed.remotes` is UNCHANGED in name and now holds ONLY confirmed-absent refs. No other `removed.*` field renamed/removed (back-compat preserved).
  - `ok` semantics: `ok:true` even when `failedRemotes` is non-empty (retriable partial failure, RQ2). `ok:false` is reserved for genuine infra errors (gt/git/gh unreachable) and the exception path leaves `failedRemotes` empty.
  - `_prune_remote_refs(ticket, branches, dry_run) -> RemotePruneResult` — NOTE the signature gained a leading `ticket` arg (was `(branches, dry_run)`).
  - `_remote_refs(ticket) -> set[str]` — new read-only origin discovery authority (bare `<ticket>/*` names).
  - `_gt_prune_remotes(branches)` — the ONLY remote-mutating seam (calls `gt sync --force`); test substitutes it.
  - Discovery in `run` is the UNION of `_stack_branches` (local) and `_remote_refs` (origin). Remote prune runs BEFORE local-branch deletion.
  - Additive stranded-ref reaping path in `run`: fires only when `classify_cleanup` returns `skip` AND local branch set is empty AND origin carries `<ticket>/*` refs AND `is_stack_fully_merged` confirms the origin refs merged; reports `decision: "destroy"` with reason "stranded origin refs reaped (worktree-only, fully merged)". `classify_cleanup` is untouched.

---

## Session 2 — Slice 1

**Timestamp:** 2026-06-11T20:55:03Z
**Tasks completed:** T13, T14, T15, T16, T17, T18, T19, T20, T21
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_cleanup_test.py` → 25 passed, 0 failed

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. The fixture uses a `git push origin --delete` ONLY inside the test's `_gt_prune_remotes` stand-in (`_make_gt_deleter`) to drive a deterministic offline origin mutation — this is test scaffolding, NOT the production path (production stays within `gt`). The seam-substitution keeps the real discovery + post-prune `git ls-remote` confirmation + removed/failedRemotes partition under test against a real bare origin.

**Verification (T21 checkpoint — all boxes met):**

- New fixture test passes; PROVEN to FAIL when only the reporting change is reverted to presence-based — ran a buggy presence-based `_prune_remote_refs` in-memory and the false-success guard failed (expected survivor in `failedRemotes`, buggy code reported it `removed`) (AC4).
- Worktree-only case: empty local set + merged origin refs → post-run `git ls-remote` shows the ref gone and it appears in `removed.remotes`; envelope `decision: destroy`, `ok:true`, `failedRemotes: []` (AC3).
- Survivor case: a still-present ref lands in `failedRemotes`, is absent from `removed.remotes`, envelope `ok:true` (AC2, RQ2) — verified both at `_prune_remote_refs` level and end-to-end via `run`.
- Dry-run: candidate reported in `removed`, origin `git ls-remote` unchanged (no gt seam call).
- Existing pure `classify_cleanup` tests (8) pass unchanged alongside the fixture suite.

**Notes for next session:**

- Slice 1 producer + tests complete and green. The additive `failedRemotes` envelope field and the `ok:true`-on-partial-failure semantics are the only contract surface Slice 2 (`qrspi-batch.js` consumer) needs.
- The fixture suite skip-guards via `_git_available()` — prints `SKIP` and runs only the pure tests when `git` is absent.

---

## Session 3 — Slice 2

**Timestamp:** 2026-06-11T21:10:00Z
**Tasks completed:** T22, T23, T24
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX OK
- Standalone end-to-end envelope harness (4 required cases + 2 defensive cases) → 15 passed, 0 failed. Harness copied the verbatim `extractJsonObject`/`parseCleanupEnvelope`/`cleanupFailedRemotes` functions and the distilled land/processed-exclusion logic, asserted: (1) non-empty `failedRemotes`+`ok:true` → log surfaces stranded refs, `reconcileRetry` set, NOT halted, ticket left OUT of `processed` (eligible for Reconcile retry); (2) empty `failedRemotes` → no retry, added to `processed` (unchanged); (3) `ok:false` → halts, no retry; (4) envelope LACKING `failedRemotes` → parses with no error, no retry. (Harness lived in /tmp, removed after running — eval harness is a project placeholder, so logic verified directly per convention.)

**Deviations from structure.md:**

- none. Implemented the consumer in `.claude/workflows/qrspi-batch.js` only.

**Deviations from plan.md:**

- Resolved structure §Unverified-Assumption-3 (no pre-existing explicit "Reconcile retry scheduler"). The retry mechanism IS the existing opt-in Reconcile pass (`runReconciliation`), which re-enumerates `.worktrees/` candidates and excludes the run's `processed` set. "Schedule a Reconcile retry" is therefore implemented as: a land whose cleanup returns `ok:true` + non-empty `failedRemotes` sets `res.reconcileRetry = true`, and the main loop skips `processed.add(t.id)` for such a ticket — so this run's Reconcile pass (when enabled) re-attempts the prune, and the still-present origin refs keep it in the backlog for a later run's pass regardless. No new scheduler/queue was invented (that would be out-of-slice scope and would duplicate the existing reconcile path).

**Verification (T24 checkpoint — all boxes met):**

- Non-empty `failedRemotes` (ok:true): the Finalize/Reconcile log lines append `STRANDED remotes [...]`, and the land result sets `reconcileRetry`, leaving the ticket OUT of `processed` so the Reconcile pass re-attempts it — NOT halted.
- Empty `failedRemotes`: no `reconcileRetry`, ticket added to `processed`, existing behavior unchanged.
- `ok:false`: still the sole hard-stop — logged "cleanup failed", no retry (HARD-STOP preserved).
- Envelope lacking `failedRemotes` (back-compat): `parseCleanupEnvelope` does not validate/require the field; `cleanupFailedRemotes` returns `[]` (also coerces non-array junk) — parses without error, no retry.

**Notes for next session:**

- Slice 2 (final slice) complete. Both files implemented and verified; stack ready for `/qrspi-pr`.
- New consumer surface in `qrspi-batch.js`: helper `cleanupFailedRemotes(cl)` (reads `cl.failedRemotes` defensively → `[]`); land/reconcile log lines surface `STRANDED remotes [...]`; land result carries `failedRemotes` + a `reconcileRetry` boolean; the main loop's `processed.add` is now conditional on `!res.reconcileRetry`.
