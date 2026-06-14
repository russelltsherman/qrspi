# Structure Outline — qrspi-batch trunk-sync hardening: never build a dependent ticket on a stale local main

**Design basis:** design.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## New Types

- `SyncEnvelope { ok: bool, repoRoot: str, updated: bool, from: str|null, to: str|null, error?: str }`
  — the stdout JSON contract emitted by `scripts/qrspi_sync_trunk.py` (ref: design.md §Delta, AC1).
  `from`/`to` are short SHAs of local `main` before/after; `updated` is true only on an actual FF advance,
  false on already-current; on any fail-loud path `ok:false` + verbatim `error`.
- `SyncDecision { token: "updated"|"already-current"|"divergent"|"dirty"|"fetch-failed"|"not-on-main" }`
  — the pure-classifier return value. The five "happy/anomaly" tokens are fixed by OQ2-RESOLVED;
  `"not-on-main"` is the sixth fail-loud token Structure pins here to carry forward the Decision-1 /
  OQ1 HEAD==`main` guard (Risk Register row 1: "fails if HEAD is not on `main` in the main checkout";
  OQ1: "the merge is attempted only when the main checkout's HEAD is on `main` — a non-`main` HEAD
  classifies as fail-loud"). The impure shell maps this token to the envelope fields (see Contracts →
  token→field mapping).

## Modified Types

- `WORKER_SCHEMA` (`.claude/workflows/qrspi-batch.js`) — **no field addition**. `error?` is already
  declared: `{ ok, error?, prUrl?, newStatus?, summary }` (ref: design.md AC4, Decision 3). The change is
  behavioral only: the `doLand` worker prompt fills the existing `error` field, and `finResult` reads it.

## Contracts

### Python helper (cross-slice: consumed by the JS orchestrator)

- `classify_sync(head_branch: str|None, fetch_rc: int, dirty_porcelain: str, local_sha: str|None, origin_sha: str|None, is_ancestor: bool) -> str`
  — **pure**, no I/O. Returns exactly one decision token. `head_branch` is the short branch name the main
  checkout's HEAD currently points at (`"main"` when on trunk; any other branch name, or `None` for a
  detached HEAD, means HEAD is NOT on `main`). Precedence (pins OQ2; **this exact parameter order/list and
  the token→field mapping below are the unit-test contract OQ2 delegated to Structure**):
  1. `head_branch != "main"` (including `None`/detached) → `"not-on-main"`
     (**HEAD-on-`main` guard, checked first so the working-tree-touching FF merge is never attempted off
     `main` — ref: Risk Register row 1, OQ1; this is the Decision-1 fail-loud fallback OQ1 named).
  2. `dirty_porcelain` non-empty (after strip) → `"dirty"` (dirty-tree precedence, ref: Q10 — checked before any fetch/merge so work is never destroyed).
  3. `fetch_rc != 0` → `"fetch-failed"`.
  4. `local_sha == origin_sha` → `"already-current"`.
  5. `not is_ancestor` (local `main` not an ancestor of `origin/main`) → `"divergent"`.
  6. otherwise → `"updated"` (clean FF advance available).
  Rationale for ordering the HEAD guard ahead of `dirty`: both are fail-loud, but the HEAD check needs no
  fetch and no porcelain read to be correct, and surfacing "not on `main`" first gives the operator the
  most actionable reason; either order is safe (no merge runs on any fail-loud token), and this order is
  the pinned contract.
- token → envelope mapping (impure shell, pins OQ2):
  - `"updated"` → `{ ok:true, updated:true, from:local_sha, to:origin_sha }` (after a successful `git merge --ff-only origin/main`).
  - `"already-current"` → `{ ok:true, updated:false, from:local_sha, to:local_sha }`.
  - `"not-on-main"` → `{ ok:false, updated:false, from:null, to:null, error:"<verbatim: main checkout HEAD is not on 'main' (on <head_branch or 'detached HEAD'>); refusing FF-only sync>" }`
    (`from:null` because `local_sha` is `rev-parse main`, which is unrelated to where HEAD points; this token is detected before any fetch).
  - `"dirty"` → `{ ok:false, updated:false, from:local_sha, to:null, error:"<verbatim: main working tree dirty + porcelain lines>" }`.
  - `"fetch-failed"` → `{ ok:false, updated:false, from:local_sha, to:null, error:"<verbatim: git fetch origin failed, rc + stderr>" }`.
  - `"divergent"` → `{ ok:false, updated:false, from:local_sha, to:origin_sha, error:"<verbatim: local main diverged from origin/main; not fast-forwardable>" }`.
- `_run(argv) -> int` / `main()` — impure shell: self-locates `REPO_ROOT` via `qrspi_paths.resolve_repo_root`,
  reads the main checkout's HEAD branch via `git symbolic-ref --short -q HEAD` (empty/non-zero rc → detached
  → treated as not-on-`main`), then runs `git status --porcelain`, `git fetch origin`, `git rev-parse main`,
  `git rev-parse origin/main`, `git merge-base --is-ancestor origin/main main`, and (only on the `"updated"`
  token) `git merge --ff-only origin/main`, all with `cwd=REPO_ROOT`; feeds the classifier; prints the
  `SyncEnvelope` JSON; exits `0`/`1`. The HEAD read happens first so a non-`main` HEAD fails loud **before**
  any fetch or merge is attempted (ref: Q4, Decision 1 Option A, Risk Register row 1, OQ1).

### JS orchestrator (cross-slice: depends on the helper's envelope)

- `parseSyncTrunkEnvelope(text: string) -> SyncEnvelope` — mirrors `parseRestackEnvelope`: runs
  `extractJsonObject`, validates `ok` is boolean and (when `ok`) `updated`/`from`/`to` present; throws on malformed (ref: Q5).
- `syncTrunk(phaseLabel: string) -> Promise<SyncEnvelope>` — spawns a **main-checkout** worker told to run exactly
  `engineCmd('scripts/qrspi_sync_trunk.py')` verbatim and echo stdout, then parses via `parseSyncTrunkEnvelope` (ref: Q5, Q7).

## Slice 1: FF-only trunk-sync helper + unit tests

**Goal:** A standalone, self-locating `scripts/qrspi_sync_trunk.py` that fetches `origin` and FF-advances
local `main` to `origin/main`, emitting the `SyncEnvelope` and failing loud on a non-`main` HEAD, divergence,
dirty tree, or fetch failure. Verifiable end-to-end in complete isolation via its own stdlib-only test — no JS, no orchestrator.
**Files touched:**

- ✨ `scripts/qrspi_sync_trunk.py` — pure `classify_sync` + impure `_run`/`main`; self-location, six-token decision space (HEAD-on-`main` guard included), envelope emission (ref: AC1, Decision 1 Option A, Risk Register row 1, OQ1).
- ✨ `scripts/qrspi_sync_trunk_test.py` — stdlib-only: pure-classifier cases (clean FF→`updated`, already-current, divergence, dirty, fetch-failed, **not-on-main for both a non-`main` branch name and a detached `None` HEAD**) and the precedence order (**not-on-main beats dirty**, and dirty beats fetch-failed); plus a `subprocess.run`/`symbolic-ref` fake-handler swap exercising the impure path's token→envelope mapping, including that a non-`main` HEAD short-circuits to `ok:false` with **no `git fetch`/`git merge` ever invoked** (ref: Q12).
**Verification:**
- [ ] `python3 scripts/qrspi_sync_trunk_test.py` passes (covers all six tokens, the HEAD-guard precedence, and impure mapping incl. the no-fetch/no-merge short-circuit on a non-`main` HEAD).
- [ ] Manual: in a checkout where `origin/main` is one commit ahead, running the helper prints `{"ok":true,"updated":true,...}` and local `main` now equals `origin/main`; a divergent local `main` prints `ok:false` with the verbatim divergence reason and exits 1; running it from a checkout whose HEAD is on a non-`main` branch prints `ok:false` with the verbatim "HEAD is not on 'main'" reason and exits 1 without fetching or merging.
**Context cost:** M
**Depends on:** none

## Slice 2: Wire run-start + post-land sync and surface land-conflict reasons (AC2, AC3, AC4)

**Goal:** The batch fetches/FF-advances local `main` before any worktree is cut (run start) and after every
successful land, aborting the run loud on any sync failure; and a real land conflict surfaces its verbatim
reason instead of `unknown`. All three edits live in one file, share the run's git-trunk-correctness concern,
and can only be verified together against the helper from Slice 1 — they are one developer sitting.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js`:
  - add `parseSyncTrunkEnvelope` (mirror `parseRestackEnvelope`) and `syncTrunk(phaseLabel)` (built with `engineCmd('scripts/qrspi_sync_trunk.py')`, main-checkout worker).
  - **AC2:** insert a run-start `syncTrunk` after Query scope resolution and before the per-ticket loop (≈`:2443`); on non-ok, `throw` to abort the run (run-start abort idiom, ref: Q11).
  - **AC3:** add a post-land `syncTrunk` in `doLand`, gated on `verdict.status === 'landed'`, beside `runCleanup`; on non-ok, `throw` to abort the run — fatal per OQ3-RESOLVED (ref: Q8, Q11).
  - **AC4:** point the `doLand` land-worker prompt at the already-present `error` field (verbatim conflict reason), and change `finResult`'s failure summary to `fin?.error ?? fin?.summary ?? 'unknown'` (no `WORKER_SCHEMA` change, ref: Q6, Q13, Decision 3 Option A).
**Verification:**
- [ ] `node --check .claude/workflows/qrspi-batch.js` passes (no syntax regression).
- [ ] Code inspection: both `syncTrunk` call sites `throw` on non-ok (run-start and post-land); the AC3 site is inside the `verdict.status === 'landed'` branch beside `runCleanup`; `finResult` reads `error ?? summary ?? 'unknown'`; the `doLand` prompt instructs the worker to fill `error`.
- [ ] Manual e2e (AC5): a run whose `origin/main` is ahead advances local `main` before Resolve; a divergent local `main` aborts the run loud with the verbatim reason. (Verification only, per the eval-placeholder note.)
**Context cost:** M
**Depends on:** Slice 1 (the `syncTrunk` worker invokes `scripts/qrspi_sync_trunk.py`; run-start/post-land wiring cannot be exercised without the helper).

---

## Unverified Assumptions

- **Exact insertion line `:2443` for the AC2 run-start sync** — the design cites this line as "after Query
  scope resolution and before the per-ticket loop," but line numbers drift; the implementer must locate the
  actual boundary (post-Query-scope, pre-loop) rather than trust the literal offset. (ref: design.md §Delta AC2 call site)
- **`finResult`'s precise current shape** — the design states `finResult`'s failure path surfaces only
  `fin?.error` today and must become `fin?.error ?? fin?.summary ?? 'unknown'`; the exact surrounding
  expression in `doLand` is not quoted in the design and must be confirmed in-file before editing. (ref: design.md AC4, Q13)
- **`qrspi_paths.resolve_repo_root` import surface** — the design asserts the sibling-helper self-location
  convention (`ENGINE_ROOT` from `__file__`, host root via `qrspi_paths.resolve_repo_root`) but does not show
  its exact import/call signature; the implementer mirrors an existing sibling helper rather than inventing it. (ref: Q4)
- **`engineCmd` / main-checkout worker invocation shape** — `syncTrunk` is specified to mirror the existing
  restack worker pattern (`engineCmd('scripts/...')`, `extractJsonObject` + validator), but the precise worker-
  spawn boilerplate is taken on faith from the sibling `parseRestackEnvelope`/restack-worker precedent, not
  re-derived here. (ref: Q5, Q7)
- **HEAD-branch read primitive** — the structure pins `git symbolic-ref --short -q HEAD` as the impure
  HEAD-on-`main` probe (empty output / non-zero rc ⇒ detached ⇒ not-on-`main`); the design names the guard
  (Risk Register row 1, OQ1) but not the exact git command, so the implementer confirms `symbolic-ref` (vs
  `rev-parse --abbrev-ref HEAD`, which prints `HEAD` for a detached state) is the chosen probe. (ref: Risk Register row 1, OQ1)
