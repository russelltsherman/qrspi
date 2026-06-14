# Design — qrspi-batch trunk-sync hardening: never build a dependent ticket on a stale local main

**Ticket:** RUS-74
**Research basis:** research.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## Current State

The `qrspi-batch` run cuts and restacks worktrees onto **local** `main` and never fetches or fast-forwards it first. In the Resolve phase, a brand-new ticket's design branch is cut with `git worktree add -b <id>/design <worktree> trunk` where `trunk` defaults to `"main"`; no step fetches or advances local `main` before that cut, and there is no `git fetch`, `gt sync`, or `origin/main` reference anywhere in the resolve path (ref: Q1). The Restack phase realigns onto the **local** trunk only — `gt restack --downstack` from the stack tip, and `gt move --onto main` for a partial-land re-parent — and the restack module is explicit that it "restacks onto the LOCAL trunk only ... NEVER `gt sync`s" (ref: Q2). At run start the script runs Query once in the main checkout, then iterates tickets sequentially, and per ticket runs Resolve → Restack → dispatch; the first git mutation in the main checkout is the worktree cut inside `resolveTicket`, and there is no run-start step that touches trunk before the first worktree is cut (ref: Q3).

No divergence detection exists: a repo-wide search for `merge-base`, `--is-ancestor`, `origin/main`, `git fetch`, and `ff-only` found zero occurrences in executable code; the harness never compares local `main` to `origin/main` and never runs a fast-forward/ancestor check, so the only available git primitives are `rev-parse`, `ls-remote`, and `branch --list` (ref: Q9). The harness implicitly trusts local `main` is a faithful trunk tip (ref: Discovered Patterns). The "drift gate" restack framing only surfaces divergence between the held stack and *local* trunk, never local-vs-origin, so a stale local `main` passes it cleanly while still being the wrong base (ref: Q2, ref: Inconsistencies).

Sibling helpers establish a fixed shape: self-locating root (`ENGINE_ROOT` from `__file__`, host root via `qrspi_paths.resolve_repo_root`), a single `{ ok, repoRoot, ..., error? }` JSON envelope on stdout, exit `0/1`, a pure-core/impure-`_run` split, and fail-once-never-retry on infra error (ref: Q4). The workflow invokes each helper by spawning a worker agent told to run exactly one verbatim command and echo stdout, then parses it with `extractJsonObject` + a `parse*Envelope` validator; a run-start non-ok envelope `throw`s to abort the whole run (Query config scope), while a per-ticket non-ok envelope is logged and `continue`d (ref: Q5, ref: Q11). Dirty-tree guarding has a canonical precedent: `git status --porcelain` read impurely, classified by a pure function that returns "blocked" when non-empty, with dirty-tree precedence so work is never destroyed (ref: Q10). The land worker uses `WORKER_SCHEMA` = `{ ok, error?, prUrl?, newStatus?, summary }` — note `error?` is **already a declared (optional) field**, not absent (ref: Q6). The foot-gun is purely a mismatch in *which* field gets filled vs read: `finResult`'s failure path surfaces **only** `fin?.error` and ignores `fin.summary`, while the `doLand` prompt has the land worker return its reason in `summary` (the required field) with an empty `error`, so a real conflict surfaces `... finalize failed: unknown` (ref: Q6, ref: Q13, ref: Inconsistencies). Because `error?` already exists in the schema, closing this needs no schema change — only the prompt (fill `error`) and `finResult` (read it, fall back to `summary`). Tests are stdlib-only: pure classifiers over crafted inputs, plus a `subprocess.run` fake-handler swap for impure git/gh mechanics, plus optional skip-guarded real-git fixtures (ref: Q12).

## Desired End State

- **AC1** — A self-locating, stdlib-only `scripts/qrspi_sync_trunk.py` runs `git fetch origin` then an FF-only update of local `main` to `origin/main`, returns `{ ok, updated, from, to, error? }`, and fails loud (`ok:false`, verbatim reason) on divergence (local `main` not an ancestor of `origin/main`) or a dirty main working tree. `scripts/qrspi_sync_trunk_test.py` covers clean FF, already-current no-op, divergence, and dirty-tree — matching the envelope/self-location convention (ref: Q4) and the test patterns (ref: Q12).
- **AC2** — The batch invokes the helper once at run start, **before the Resolve phase cuts any worktree**, in the main checkout. This is the primary preventer and also makes Restack correct, since Restack realigns onto local `main` (ref: Q2, ref: Q3). A divergence/fetch failure here `throw`s to abort the whole run, mirroring the run-start config-scope abort idiom (ref: Q11).
- **AC3** — The batch invokes the helper **after each successful land, in the main checkout**, in the orchestrator context (never the land worker's worktree) — alongside the post-land `runCleanup` call, gated on `verdict.status === 'landed'` (ref: Q8). This keeps local `main` current between lands within a run. **A post-land sync failure is fatal: it `throw`s to abort the run** (same disposition as the AC2 run-start sync), mirroring the run-start hard-abort idiom (ref: Q11). Rationale: once a land has occurred, local `main` is now *behind* `origin/main` by at least that landed commit; if the reconciling sync fails, every subsequent ticket in the run would cut/restack onto a now-stale local `main` — exactly the stale-base failure this ticket exists to prevent. Failing loud here is strictly safer than continuing on a known-stale trunk.
- **AC4** — The land worker's output schema **already** carries an (optional) `error` field — `WORKER_SCHEMA = { ok, error?, prUrl?, newStatus?, summary }` (ref: Q6) — so no schema-field addition is required. The fix is two edits: (a) the `doLand` land-worker prompt must populate that already-present `error` field with the verbatim conflict reason (today it returns the reason in `summary` while leaving `error` empty), and (b) `finResult`'s failure path falls back `error ?? summary ?? 'unknown'`, so a land conflict surfaces verbatim instead of `unknown` (ref: Q6, ref: Q13). This satisfies the ticket's AC4 ("the land worker's output schema carries an `error` field") — the field is present; what was missing is the prompt populating it and `finResult` honoring it.
- **AC5** — Manual e2e: a run whose `origin/main` is ahead of local `main` advances local `main` before Resolve; a divergent local `main` aborts the run loud. (Verification only — no eval-harness assertion, per the placeholder note.)

## Delta

**New files**
- `scripts/qrspi_sync_trunk.py` — the FF-only sync helper. Module-level self-location and `REPO_ROOT` per Q4. A **pure classifier** `classify_sync(fetch_rc, dirty_porcelain, local_sha, origin_sha, is_ancestor)` (exact signature open — see OQ2) returns the decision (`updated`/`already-current`/`divergent`/`dirty`/`fetch-failed`) so it is unit-testable in isolation; an impure shell runs `git status --porcelain`, `git fetch origin`, `git rev-parse main` / `origin/main`, `git merge-base --is-ancestor origin/main main`, and the FF `git update-ref`/`git merge --ff-only` and feeds the classifier. Emits `{ ok, repoRoot, updated, from, to, error? }`.
- `scripts/qrspi_sync_trunk_test.py` — stdlib-only: pure-classifier cases (clean FF, already-current, divergence, dirty) plus a `subprocess.run` fake-handler swap for the impure path (ref: Q12).

**Modified files**
- `.claude/workflows/qrspi-batch.js`:
  - A `parseSyncTrunkEnvelope(text)` validator (mirrors `parseRestackEnvelope`) and a `syncTrunk(phaseLabel)` worker invocation built with `engineCmd('scripts/qrspi_sync_trunk.py')`, run as a main-checkout worker (ref: Q5, Q7).
  - **AC2 call site:** insert a run-start sync after Query scope resolution and **before** the per-ticket loop (`:2443`); on non-ok, `throw` to abort the run (ref: Q3, Q11).
  - **AC3 call site:** add a post-land sync in `doLand`, gated on `verdict.status === 'landed'`, beside `runCleanup` (ref: Q8); on non-ok, `throw` to abort the run (fatal — same disposition as the AC2 run-start sync, ref: Q11), because a failed reconcile leaves local `main` stale for every subsequent ticket in the run.
  - **AC4:** **no `WORKER_SCHEMA` field addition** — `error?` is already declared in `WORKER_SCHEMA = { ok, error?, prUrl?, newStatus?, summary }` (ref: Q6). Two edits only: update the `doLand` land-worker prompt to return its verbatim reason in the already-present `error` field (today it returns the reason in `summary`), and change `finResult`'s failure summary to `fin?.error ?? fin?.summary ?? 'unknown'` (ref: Q6, Q13).

No DB/middleware changes; this is orchestration + a deterministic helper.

## Pattern Decisions

### Decision 1: How to perform the FF-only update of local `main` while `main` is checked out in the main worktree

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `git merge --ff-only origin/main` run with `cwd=repo_root` (main checkout, on `main`) | Native FF-only semantics; refuses non-FF automatically; honors the checked-out branch | Requires HEAD on `main`; touches the working tree (mitigated by the dirty-tree guard) |
| B | `git fetch` + explicit `git merge-base --is-ancestor origin/main main` check, then `git update-ref refs/heads/main origin/main` | Decision is explicit and classifier-testable; no working-tree touch | `update-ref` on the checked-out branch desyncs index/worktree — unsafe while `main` is checked out |

**Recommendation:** Option A for the ref move, with the **explicit `--is-ancestor` check from Option B used only to classify divergence and produce the verbatim fail-loud reason** before attempting the merge. The constraint notes `git branch -f main` fails for a worktree-checked-out branch (ticket Constraints); `merge --ff-only` is the safe primitive when HEAD is on `main`.
**Rationale:** Reuses the dirty-tree precedence guard exactly (`git status --porcelain` + pure classifier, ref: Q10) and the pure-core/impure-shell split (ref: Q4). The explicit ancestor check gives a clean classifier input and a precise reason, satisfying "fail loud, verbatim."
**NEW PATTERN?** Yes — `git merge-base --is-ancestor` and `git fetch origin` are introduced for the first time (ref: Q9); justified because no existing primitive compares local-vs-origin, and the ticket explicitly requires it. The *envelope, self-location, test, and pure/impure shape* are NOT new — they clone the sibling-helper convention.

### Decision 2: Run-start placement and failure disposition (AC2)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Single run-start sync before the loop; non-ok `throw`s (whole-run abort) | Matches the strict run-start config-scope idiom (ref: Q11); one guaranteed sync before any cut | A transient `git fetch` failure aborts the whole run |
| B | Sync inside `resolveTicket`/Restack per ticket; non-ok logs + `continue`s | Degrades per-ticket | Re-fetches every ticket; a stale base could still slip if ordering is wrong; contradicts AC2's "once at run start, before Resolve" |

**Recommendation:** Option A.
**Rationale:** AC2 mandates "once at run start, before the Resolve phase cuts any worktree." The run-start hard-abort-via-`throw` idiom is the established disposition for run-start invariants (config scope, ref: Q11); a stale/divergent trunk is exactly that class of run-wide invariant. Divergence is a real anomaly to surface, not paper over (ticket Constraints).
**NEW PATTERN?** No — reuses the run-start `throw`-to-abort idiom (ref: Q11).

### Decision 3: AC4 surfacing — schema vs `finResult` fallback

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Populate the already-present `error` field via the `doLand` prompt + `finResult` falls back `error ?? summary ?? 'unknown'` (no schema change — `error?` is already in `WORKER_SCHEMA`, ref: Q6) | Minimal; preserves both fields; backward-compatible with workers that only set `summary` | Two small edits (`doLand` prompt + `finResult`) |
| B | Repurpose `summary` only in `finResult`'s failure path | One edit | Loses the verbatim/structured `error` channel; `summary` is human prose, not the conflict reason |

**Recommendation:** Option A (exactly as AC4 specifies).
**Rationale:** The current foot-gun is **not** a missing schema field — `error?` is already declared in `WORKER_SCHEMA` (ref: Q6); it is that `finResult` reads only `fin.error` while the `doLand` prompt has the land worker fill `summary` and leave `error` empty (ref: Q6, ref: Inconsistencies). Pointing the prompt at the existing `error` field plus the `error ?? summary ?? 'unknown'` fallback closes the gap without any schema edit and without removing the structured error channel other callers rely on.
**NEW PATTERN?** No.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `merge --ff-only` touches the working tree / fails if HEAD is not on `main` in the main checkout | med | high | Guard on clean working tree first (ref: Q10) and on HEAD==`main`; classify and fail loud (`ok:false`) rather than force, never `--force` (ticket Constraints) |
| Run-start `throw` on a transient `git fetch` network blip aborts an otherwise-healthy run | med | med | Acceptable per AC2/Constraints (fail loud over silent stale base); operator re-runs once connectivity returns; keep the verbatim reason so the cause is obvious (ref: Q11) |
| AC4 fallback still surfaces `unknown` if the land worker sets neither `error` nor a meaningful `summary` | low | med | `error ?? summary ?? 'unknown'` covers both channels; update the `doLand` prompt to put the verbatim reason in `error` (ref: Q6) |
| Out-of-scope mid-run external advance of `origin/main` (concurrent lander) still produces a stale base | low | med | Explicitly out of scope (ticket Out of Scope); AC2 covers run-start, AC3 covers the orchestrator's own lands |
| Landing concurrently with RUS-58/RUS-73 re-creates the shared-file conflict in `qrspi-batch.js` | high | high | Entry gate holds RUS-74 (blockedBy RUS-58, RUS-73) until both land (ticket Dependencies) — not weakened by this change |

## Open Questions

- OQ1: **RESOLVED — `git merge --ff-only origin/main` (Decision 1 Option A) is acceptable.** The reviewer confirmed the working-tree touch is fine because the design already guards it: the dirty-tree precedence guard (`git status --porcelain` + the pure classifier, ref Q10) classifies a non-empty tree as `dirty` / fail-loud *before* the merge, so the FF never touches uncommitted work (Risk Register row 1); the merge is attempted only when the main checkout's HEAD is on `main` (a non-`main` HEAD classifies as fail-loud — the exact fallback this question named); and the explicit `git merge-base --is-ancestor origin/main main` check classifies divergence and produces the verbatim fail-loud reason before any merge. No design change needed — the text already reflects Option A.
- OQ2: **RESOLVED — deferred to the Structure phase, by reviewer direction.** The exact `classify_sync` parameter list/order and the decision-token→`{ updated, from, to }` mapping are the unit-test contract and are left for Structure to pin precisely. The design's commitments remain the concrete anchor Structure builds on: the classifier is pure and unit-testable (pure-core/impure-`_run` split, ref Q4); its decision space is the five tokens `updated` / `already-current` / `divergent` / `dirty` / `fetch-failed`; its inputs are those sketched in `classify_sync(fetch_rc, dirty_porcelain, local_sha, origin_sha, is_ancestor)`; and it feeds the `{ ok, repoRoot, updated, from, to, error? }` envelope. Only the precise signature/order and token-to-field filling are intentionally left open for Structure.
- OQ3: **RESOLVED — fatal.** AC3's post-land sync failure `throw`s to abort the run (same disposition as the AC2 run-start sync). After a land, local `main` is behind `origin/main`; a failed reconcile would leave every subsequent ticket cutting/restacking onto a known-stale trunk — the exact failure this ticket prevents — so failing loud is strictly safer than continuing. (The earlier "non-fatal — next run's AC2 sync reconciles" suggestion is rejected: it leaves *this* run's remaining tickets on a stale base.)
