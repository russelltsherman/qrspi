# Structure Outline — CI-revise loop cap must count failed revise attempts (close AC6 hole from RUS-81)

**Design basis:** design.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## New Types

- No new data types. The durable state remains the existing `CI-Revise-Attempt: N` head-commit trailer (a string trailer parsed to int). New code is two functions plus one new boolean decision field.

## Modified Types

- `decision` dict (built in `scripts/qrspi_resolve_state.py`) — add field `ciGaveUp: bool` (default `False`), set `True` only on the cap-reached red→`wait` branch (ref: design.md §Delta, Decision 2 Option A, AC4). Mirrors the existing `ciFailing` boolean.

## Contracts

These are the cross-slice interfaces. The trailer string format `CI-Revise-Attempt: N` is the shared serialization contract between the bump helper (writer) and `qrspi_pr_state.py` (reader) — unchanged, identical regex/format on both sides (ref: design.md §Delta "Modified `scripts/qrspi_pr_state.py`: no functional change").

- `bump_ci_revise_trailer(message: str) -> str` — PURE core of the new helper. Given a full commit message, parse the existing `CI-Revise-Attempt: N` trailer (absent ⇒ `prior=0`, last-occurrence wins to mirror the gather's parse), return a new message with **exactly one** `CI-Revise-Attempt: <prior+1>` trailer, subject line and every other trailer byte-preserved (ref: design.md §Delta bullet 1 step 3, AC5). Unit-tested.
- `python3 scripts/qrspi_ci_revise_bump.py --ticket <id> --branch <branch>` — IMPERATIVE shell of the new helper. Checks out `<branch>`, reads head message (`git log -1 --format=%B`), applies `bump_ci_revise_trailer`, writes message-only (`gt modify --no-interactive -m`), re-publishes (`gt submit --publish --no-edit [--stack for implementation] --no-interactive`), VERIFIES exactly one trailer at `<prior+1>`, prints JSON `{ ok, branch, prior, new, error? }`, exits **non-zero** (fail-closed) on any failure (ref: design.md §Delta bullet 1, Decision 1 Option A′, mirrors `qrspi_revise_amend.py`).
- `doRevise` (in `.claude/workflows/qrspi-batch.js`) → invokes the helper once per still-red branch (design/plan: the one phase branch; implementation: each still-red slice branch, lowest first) **unconditionally** after the content worker returns on a red pass, regardless of worker `ok` (ref: design.md §Delta bullet 2, Decision 1 Option A′).
- `ciRedBranches` (top-level envelope field, emitted by `scripts/qrspi_resolve.py`'s pure `red_branches_of(decision, phases, ticket)`) — the deterministic, ascending list of branches the helper must bump this pass (red slice branches for implementation; the one phase branch for a red design/plan frontier; `[]` for non-CI). `doRevise` iterates it directly, mirroring how `ciFailingChecks` / `commentTargets` are pre-aggregated for the JS, so the orchestrator never re-derives per-slice CI state and never delegates "which slices are red" to an LLM worker.

## Slice 1: Deterministic increment helper `qrspi_ci_revise_bump.py` + pure-core tests

**Goal:** A standalone, fail-closed Python helper that is the sole authority for advancing `CI-Revise-Attempt`. Delivers the AC1/AC5 guarantee end-to-end and is fully verifiable in isolation (its pure rewrite core via unit tests, its `gt`/publish shell via the same trust model as `qrspi_revise_amend.py`) before any JS touches it. This is a single cohesive unit: the script and its sibling test are mutually dependent and there is no testability boundary between them.

**Files touched:**

- ✨ `scripts/qrspi_ci_revise_bump.py` — self-locating helper; pure `bump_ci_revise_trailer(message)` core + the `gt` imperative shell (checkout → read → rewrite → `gt modify -m` → `gt submit --publish` → verify → JSON/exit-code), mirroring `scripts/qrspi_revise_amend.py`
- ✨ `scripts/qrspi_ci_revise_bump_test.py` — stdlib-only `_test.py` for the pure core: absent⇒1, `N`⇒`N+1`, exactly-one-trailer (no duplicate appended), subject preserved, other trailers preserved, last-occurrence-wins parse

**Verification:**

- [ ] `python3 scripts/qrspi_ci_revise_bump_test.py` passes
- [ ] `python3 scripts/run_tests.py bump` discovers and runs the new test green
- [ ] Manual: run the script against a throwaway branch with no trailer and confirm it publishes `CI-Revise-Attempt: 1`; run again, confirm `2` (exactly one trailer, subject intact); simulate a `gt` failure and confirm non-zero exit + `ok:false` JSON

**Context cost:** M
**Depends on:** none

## Slice 2: Resolver `ciGaveUp` terminal-state field + tests

**Goal:** The pure resolver carries a structured, machine-readable terminal signal distinguishing a cap-reached red park from a normal `wait`. Independently unit-testable against synthetic `ciReviseAttempt` inputs — no dependency on Slice 1 (the resolver reads the gathered count, it does not write the trailer). AC4 + AC5.

**Files touched:**

- ⚠️ `scripts/qrspi_resolve_state.py` — add `ciGaveUp` to the decision builder (default `False`); set `True` and emit a distinct reason on the cap-reached red→`wait` branch. No change to the `attempt < cap` comparison itself.
- ⚠️ `scripts/qrspi_resolve_state_test.py` — new cases: cap-reached red → `wait` with `ciGaveUp == True` and distinct reason; under-cap red → `revise` with `ciGaveUp == False`; non-CI `wait` paths carry `ciGaveUp == False` (default unchanged)

**Verification:**

- [ ] `python3 scripts/qrspi_resolve_state_test.py` passes (new + existing cases)
- [ ] `python3 scripts/run_tests.py resolve` green
- [ ] Confirm existing decision consumers tolerate the additive defaulted field (no existing test regresses)

**Context cost:** S
**Depends on:** none

## Slice 3: Wire `doRevise` to the helper + surface `ciGaveUp` in JS + end-to-end verify

**Goal:** Close the loop in the orchestrator: delete the worker's step-6 CI-path trailer write, invoke the helper unconditionally per still-red branch after the content worker returns on a red pass, and surface `ciGaveUp` in the JS dispatch/result record + per-ticket log. This is the integrating slice; it depends on both prior slices existing (the helper to call, the resolver field to surface). Verified by manual end-to-end run since `qrspi-batch.js` is harness-coupled and not unit-testable (per CLAUDE.md).

**Files touched:**

- ⚠️ `scripts/qrspi_resolve.py` — add pure `red_branches_of(decision, phases, ticket)` and emit it as the top-level envelope field `ciRedBranches` (ascending red slice branches for implementation; the single phase branch for a red design/plan frontier; `[]` for non-CI), mirroring `ci_failing_checks_of`. Gives `doRevise` a deterministic red-branch list to bump (resolves OQ3: the JS otherwise has only aggregated `ciFailing` + flat `ciFailingChecks` + slice *names*, no per-slice red/green)
- ⚠️ `scripts/qrspi_resolve_test.py` — cases for `ciRedBranches`: `[red,green,red]` ⇒ slice-1 + slice-3; red design ⇒ the design branch; non-CI ⇒ `[]`
- ⚠️ `.claude/workflows/qrspi-batch.js` (`doRevise`) — (a) DELETE the **ENTIRE** worker step-6 `CI-Revise-Attempt` block (a shared template serving BOTH the CI +1 and the green-CI-change-request reset-to-0); the worker never touches the counter; (b) after the content worker returns on a red pass, run `qrspi_ci_revise_bump.py` **unconditionally** (regardless of worker `ok`) once per branch in `r.ciRedBranches`, lowest-first, via a thin worker typing the one verbatim `python3 … qrspi_ci_revise_bump.py … [--stack]` command (fires whenever `ciFailing`, regardless of `changeRequested`; the resolver's `max(...)` over slices still governs the cap); (c) **re-home the non-CI reset**: on the `changeRequested && !ciFailing` 2b exit call `resetCiReviseTrailer` unconditionally (idempotent), preserving the "every non-CI amend overwrites the trailer to 0" invariant the deleted step-6 else-branch used to hold; (d) step-2a's `resetCiReviseTrailer` is UNCHANGED
- ⚠️ `.claude/workflows/qrspi-batch.js` (`wait`-branch result/skip record + per-ticket log) — surface `ciGaveUp` from the resolver decision into the recorded result and log line (ref: Risk Register row 4), and treat a non-zero helper exit as a recorded hard failure on the result record (OQ1 recommended resolution)

**Verification:**

- [ ] Manual end-to-end on a deliberately-unfixable red PR: worker reports failure / pushes no content amend → helper still advances the trailer by 1 each pass (confirm on the pushed PR head via `gh`/`git log`)
- [ ] Repeated passes reach `ciReviseCap` (default 3) → resolver returns `wait` with `ciGaveUp == True` and the JS result record/log surfaces it
- [ ] A pass that turns CI green → gather's read-side not-red→0 reset zeroes the count (AC3 unchanged)
- [ ] `python3 scripts/run_tests.py` full suite still green (no Python regressions)

**Context cost:** M
**Depends on:** Slice 1, Slice 2

---

## Unverified Assumptions

- **OQ1 (helper non-zero exit handling):** The design recommends `doRevise` record a helper non-zero exit as a hard failure the operator sees (Slice 3 adopts this), but the design lists it as an open question. If the intended behavior is best-effort absorption (like `resetCiReviseTrailer`), Slice 3's result-recording logic changes. Needs confirmation before planning.
- **OQ2 (`ciGaveUp` raise condition):** Slice 2 raises `ciGaveUp` on *every* cap-reached red→`wait` (Decision 3 Option A). The design flags whether AC4 instead intends it only when at least one failed-no-change attempt occurred. Confirm operator-facing semantics; affects the resolver condition.
- **OQ3 (multi-slice consecutive-red semantics) — RESOLVED in plan:** the plan surfaces the still-red slice branches deterministically as the new `ciRedBranches` envelope field (a pure `red_branches_of` over the gather's per-slice `ciState`), so `doRevise` bumps exactly the red slices lowest-first and the resolver's existing `max(...)` aggregation tracks the longest consecutive-red streak; a slice that goes green is zeroed by the gather's read-side not-red→0 reset. The remaining product-semantics open items (OQ2 `ciGaveUp` raise condition; the in-scope reading of surfacing per-slice `ciState`) are carried to the plan reviewer in plan.md.
- **`gt submit --publish --no-edit` flag exactness:** The helper's publish step flags (`--publish --no-edit`, plus `--stack` for implementation) are taken from the design's prose. The precise non-interactive `gt submit` flag set that publishes a message-only amend without re-prompting is not verified against the installed `gt` here (cf. MEMORY: `gt merge --confirm` contradicted its skill doc). The Plan/Implement phase must confirm the exact flags against `qrspi_revise_amend.py`'s working invocation.
