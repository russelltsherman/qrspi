# Implementation Plan — qrspi-batch trunk-sync hardening: never build a dependent ticket on a stale local main

**Structure basis:** structure.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total steps:** 19

## Slice 1: FF-only trunk-sync helper + unit tests

### Setup

1. ✨ Create `scripts/qrspi_sync_trunk.py` — new self-locating, stdlib-only helper. Module preamble: derive `ENGINE_ROOT` from `__file__` and resolve the host `REPO_ROOT` via `qrspi_paths.resolve_repo_root` (mirror an existing sibling helper, e.g. `scripts/qrspi_persist.py`/`qrspi_resolve.py`, for the exact import/call signature — Unverified Assumption: `qrspi_paths.resolve_repo_root` import surface). `import json, subprocess, sys`. (ref: structure.md New Types, design.md Delta New files, Q4)

### Core Logic

2. ✨ In `scripts/qrspi_sync_trunk.py`, add the pure classifier with the exact pinned signature: `classify_sync(head_branch: str|None, fetch_rc: int, dirty_porcelain: str, local_sha: str|None, origin_sha: str|None, is_ancestor: bool) -> str`. No I/O. Apply the precedence in this exact order, returning one token: (1) `head_branch != "main"` (incl. `None`/detached) → `"not-on-main"`; (2) `dirty_porcelain.strip()` non-empty → `"dirty"`; (3) `fetch_rc != 0` → `"fetch-failed"`; (4) `local_sha == origin_sha` → `"already-current"`; (5) `not is_ancestor` → `"divergent"`; (6) else → `"updated"`. (ref: structure.md Contracts → classify_sync, OQ2-RESOLVED)

3. ✨ In `scripts/qrspi_sync_trunk.py`, add a token→envelope mapping helper (pure, given the classifier token plus `head_branch`, `local_sha`, `origin_sha`) producing the `SyncEnvelope` dict fields per the pinned mapping:
   - `"updated"` → `{ ok:true, updated:true, from:local_sha, to:origin_sha }`
   - `"already-current"` → `{ ok:true, updated:false, from:local_sha, to:local_sha }`
   - `"not-on-main"` → `{ ok:false, updated:false, from:null, to:null, error:"main checkout HEAD is not on 'main' (on <head_branch or 'detached HEAD'>); refusing FF-only sync" }`
   - `"dirty"` → `{ ok:false, updated:false, from:local_sha, to:null, error:"main working tree dirty + <porcelain lines>" }`
   - `"fetch-failed"` → `{ ok:false, updated:false, from:local_sha, to:null, error:"git fetch origin failed, rc + stderr" }`
   - `"divergent"` → `{ ok:false, updated:false, from:local_sha, to:origin_sha, error:"local main diverged from origin/main; not fast-forwardable" }`
   Include `repoRoot` in every envelope. (ref: structure.md Contracts → token→field mapping)

4. ✨ In `scripts/qrspi_sync_trunk.py`, add the impure shell `_run(argv) -> int`: read the main checkout's HEAD branch via `git symbolic-ref --short -q HEAD` (empty output / non-zero rc ⇒ detached ⇒ pass `None` as `head_branch`) **first**, so a non-`main` HEAD short-circuits to `ok:false` before any fetch/merge (Unverified Assumption: HEAD-branch read primitive — confirm `symbolic-ref` over `rev-parse --abbrev-ref HEAD`). Then run `git status --porcelain`, `git fetch origin` (capture rc+stderr), `git rev-parse main`, `git rev-parse origin/main`, `git merge-base --is-ancestor origin/main main` (rc→`is_ancestor` bool), all with `cwd=REPO_ROOT`. Feed `classify_sync`; only on the `"updated"` token run `git merge --ff-only origin/main` (`cwd=REPO_ROOT`). Build the envelope via step 3, `print(json.dumps(envelope))`, `return 0` when `ok` else `1`. (ref: structure.md Contracts → _run/main, Decision 1 Option A, Risk Register row 1, OQ1)

5. ✨ In `scripts/qrspi_sync_trunk.py`, add `def main(): sys.exit(_run(sys.argv))` and the `if __name__ == "__main__": main()` guard. (ref: structure.md Contracts → _run/main)

### Tests

6. ✨ Create `scripts/qrspi_sync_trunk_test.py` — stdlib-only (`unittest`). Pure-classifier cases: clean FF→`"updated"`, already-current→`"already-current"`, divergence→`"divergent"`, dirty→`"dirty"`, fetch-failed→`"fetch-failed"`, not-on-main for **both** a non-`main` branch name **and** a detached `None` HEAD→`"not-on-main"`. (ref: structure.md Slice 1 Files touched, Q12)

7. ⚠️ Add to `scripts/qrspi_sync_trunk_test.py` the precedence-order assertions: not-on-main beats dirty (set `head_branch != "main"` **and** non-empty `dirty_porcelain` → expect `"not-on-main"`), and dirty beats fetch-failed (non-empty `dirty_porcelain` **and** `fetch_rc != 0` → expect `"dirty"`).
   - **Current:** `scripts/qrspi_sync_trunk_test.py` covers only the single-condition classifier cases (step 6).
   - **After:** it additionally asserts the two precedence orderings.

8. ⚠️ Add to `scripts/qrspi_sync_trunk_test.py` an impure-path test via a `subprocess.run`/`symbolic-ref` fake-handler swap (monkeypatch), exercising the token→envelope mapping. Include a case where a non-`main` HEAD short-circuits to `ok:false` and asserts **no `git fetch` and no `git merge` were ever invoked** by the fake handler.
   - **Current:** `scripts/qrspi_sync_trunk_test.py` exercises only the pure classifier (steps 6–7).
   - **After:** it also exercises `_run`'s impure mapping and the no-fetch/no-merge short-circuit on a non-`main` HEAD.

9. Run: `python3 scripts/qrspi_sync_trunk_test.py`
   - **Expected:** all tests pass — six tokens, the HEAD-guard precedence orderings, and the impure mapping incl. the no-fetch/no-merge short-circuit.

### Verify Slice 1

10. **Checkpoint:** `python3 scripts/qrspi_sync_trunk_test.py`
    - [ ] Test suite passes (all six tokens covered: updated, already-current, divergent, dirty, fetch-failed, not-on-main).
    - [ ] not-on-main beats dirty; dirty beats fetch-failed (precedence assertions pass).
    - [ ] Impure mapping test passes, including that a non-`main` HEAD short-circuits to `ok:false` with no `git fetch`/`git merge` invoked.

---

## Slice 2: Wire run-start + post-land sync and surface land-conflict reasons (AC2, AC3, AC4)

### Setup

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `parseSyncTrunkEnvelope(text)`, mirroring `parseRestackEnvelope`: run `extractJsonObject`, validate `ok` is boolean and (when `ok`) `updated`/`from`/`to` are present; throw on malformed (Unverified Assumption: mirror the sibling `parseRestackEnvelope` shape verbatim).
    - **Current:** no `parseSyncTrunkEnvelope` exists.
    - **After:** `parseSyncTrunkEnvelope(text: string) -> SyncEnvelope` is defined alongside `parseRestackEnvelope`. (ref: structure.md Contracts → JS orchestrator, Q5)

12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `syncTrunk(phaseLabel)`, mirroring the existing restack worker invocation: spawn a **main-checkout** worker told to run exactly `engineCmd('scripts/qrspi_sync_trunk.py')` verbatim and echo stdout, then parse via `parseSyncTrunkEnvelope` (Unverified Assumption: `engineCmd` / main-checkout worker spawn boilerplate taken from the restack-worker precedent).
    - **Current:** no `syncTrunk` helper exists.
    - **After:** `syncTrunk(phaseLabel: string) -> Promise<SyncEnvelope>` is defined. (ref: structure.md Contracts → JS orchestrator, Q5, Q7)

### Core Logic

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (AC2) — insert a run-start `await syncTrunk(...)` after Query scope resolution and **before** the per-ticket loop (near `:2443`; Unverified Assumption: locate the actual post-Query-scope / pre-loop boundary, do not trust the literal offset). On a non-ok envelope, `throw` to abort the whole run (run-start hard-abort idiom).
    - **Current:** the first git mutation in the main checkout is the worktree cut inside `resolveTicket`; nothing fetches/FF-advances local `main` at run start.
    - **After:** a run-start `syncTrunk` runs before any worktree is cut; a non-ok result `throw`s to abort the run. (ref: structure.md Slice 2 AC2, design.md Decision 2 Option A, Q11)

14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (AC3) — in `doLand`, add a post-land `await syncTrunk(...)` gated on `verdict.status === 'landed'`, placed beside the existing `runCleanup` call. On a non-ok envelope, `throw` to abort the run (fatal — same disposition as the run-start sync).
    - **Current:** after a successful land, `doLand` runs `runCleanup` (gated on `verdict.status === 'landed'`) but nothing reconciles local `main` to `origin/main`.
    - **After:** a post-land `syncTrunk` runs in the same `landed` branch beside `runCleanup`; a non-ok result `throw`s to abort the run. (ref: structure.md Slice 2 AC3, OQ3-RESOLVED, Q8, Q11)

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (AC4) — update the `doLand` land-worker **prompt** to instruct the worker to return its verbatim conflict reason in the already-present `error` field (today it returns the reason in `summary` and leaves `error` empty). No `WORKER_SCHEMA` change — `error?` is already declared.
    - **Current:** the `doLand` prompt has the land worker put its reason in `summary` with an empty `error`.
    - **After:** the prompt instructs the worker to fill `error` with the verbatim conflict reason. (ref: structure.md Modified Types, design.md Decision 3 Option A, Q6, Q13)

16. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (AC4) — change `finResult`'s failure summary to `fin?.error ?? fin?.summary ?? 'unknown'` (Unverified Assumption: confirm `finResult`'s precise current expression in `doLand` before editing).
    - **Current:** `finResult`'s failure path surfaces only `fin?.error`, so a real conflict surfaces `... finalize failed: unknown`.
    - **After:** `finResult` reads `fin?.error ?? fin?.summary ?? 'unknown'`, surfacing the verbatim reason. (ref: structure.md Modified Types, Q6, Q13)

### Tests

17. Run: `node --check .claude/workflows/qrspi-batch.js`
    - **Expected:** passes — no syntax regression from the four edits. (ref: structure.md Slice 2 Verification)

### Verify Slice 2

18. **Checkpoint:** `node --check .claude/workflows/qrspi-batch.js`
    - [ ] `node --check` passes (no syntax regression).
    - [ ] Code inspection: both `syncTrunk` call sites `throw` on non-ok (run-start before the per-ticket loop; post-land inside the `verdict.status === 'landed'` branch beside `runCleanup`).
    - [ ] `finResult` reads `fin?.error ?? fin?.summary ?? 'unknown'`; the `doLand` prompt instructs the worker to fill `error`.

19. **Checkpoint (manual e2e, AC5 — verification only, per the eval-placeholder note):** run the batch in a checkout where `origin/main` is one commit ahead of local `main`.
    - [ ] Local `main` is FF-advanced to `origin/main` before Resolve cuts any worktree.
    - [ ] A divergent local `main` aborts the run loud with the verbatim divergence reason.

---

## Rollback Notes

- Step 1–9 (Slice 1): `scripts/qrspi_sync_trunk.py` and `scripts/qrspi_sync_trunk_test.py` are new files with no callers until Slice 2 wires them; delete both files to fully revert Slice 1 — no migration, no shared state.
- Step 13 (AC2 run-start sync): purely additive call site; remove the inserted `syncTrunk` block to revert. No data is mutated beyond a local `main` FF-advance, which is itself reversible via `git reset --hard <prior-sha>` on the main checkout if needed.
- Step 14 (AC3 post-land sync): additive within the `landed` branch; remove the block to revert. Same FF-advance reversibility note as step 13.
- Step 15–16 (AC4): no schema change (`error?` already declared), so reverting is a straight edit-back of the `doLand` prompt and the `finResult` expression — backward-compatible with workers that set only `summary`.
- No DB migrations, no config-file changes, no destructive ops in this plan.
