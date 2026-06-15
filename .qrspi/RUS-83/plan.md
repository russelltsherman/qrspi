# Implementation Plan — CI-revise loop cap must count failed revise attempts (close AC6 hole from RUS-81)

**Structure basis:** structure.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total steps:** 28

## Slice 1: Deterministic increment helper `qrspi_ci_revise_bump.py` + pure-core tests

### Setup

1. ✨ Create `scripts/qrspi_ci_revise_bump.py` — self-locating helper script, mirroring `scripts/qrspi_revise_amend.py`. Add the standard self-locating repo-root preamble (resolve repo root from the script's own `__file__` path), a `--ticket <id>` and `--branch <branch>` argparse interface, and a `--stack` flag (present for implementation slices, absent for design/plan). No logic yet — establishes the module skeleton.

### Core Logic

2. ✨ Add pure function `bump_ci_revise_trailer(message: str) -> str` to `scripts/qrspi_ci_revise_bump.py` — parse the existing `CI-Revise-Attempt: N` trailer with the SAME regex/semantics as the gather's `ci_revise_attempt` (absent ⇒ `prior=0`, last-occurrence wins), then return a new full message containing **exactly one** `CI-Revise-Attempt: <prior+1>` trailer with the subject line and every other trailer byte-preserved (ref: structure.md Contracts, design.md §Delta bullet 1 step 3, AC5). Strip any/all existing `CI-Revise-Attempt:` lines and append the single new one.
3. ✨ Add imperative shell to `scripts/qrspi_ci_revise_bump.py` — orchestrate: (a) checkout `<branch>` via `gt checkout --no-interactive`; (b) read head-commit full message via `git log -1 --format=%B`; (c) apply `bump_ci_revise_trailer`; (d) write message-only via `gt modify --no-interactive -m`; (e) re-publish via `gt submit --publish --no-edit --no-interactive` (append `--stack` when `--stack` flag was passed); (f) VERIFY the pushed head has exactly one `CI-Revise-Attempt: <prior+1>` trailer; (g) print JSON `{ ok, branch, prior, new, error? }` and exit **non-zero** on any failure (ref: structure.md Contracts, design.md §Delta bullet 1, Decision 1 Option A′).
   - **Note:** Confirm the exact `gt submit` publish flags against `scripts/qrspi_revise_amend.py`'s working invocation before finalizing (ref: structure.md Unverified Assumption "gt submit --publish --no-edit flag exactness"). Use whatever non-interactive publish form `qrspi_revise_amend.py` uses.

### Tests

4. ✨ Create `scripts/qrspi_ci_revise_bump_test.py` — stdlib-only `_test.py` exercising the pure `bump_ci_revise_trailer` core (ref: structure.md Slice 1 Files touched, design.md §Delta "New/modified tests"). Cases:
   - absent trailer ⇒ result has `CI-Revise-Attempt: 1`
   - `CI-Revise-Attempt: 2` ⇒ result has `CI-Revise-Attempt: 3`
   - exactly one trailer in result (no duplicate appended when one already present)
   - subject line preserved byte-for-byte
   - other trailers (e.g. `Co-Authored-By:`) preserved byte-for-byte
   - last-occurrence-wins parse when message has two `CI-Revise-Attempt:` lines
5. Run: `python3 scripts/qrspi_ci_revise_bump_test.py`
   - **Expected:** all cases pass, exit 0
6. Run: `python3 scripts/run_tests.py bump`
   - **Expected:** the runner discovers and runs the new test green

### Verify Slice 1

7. **Checkpoint:** `python3 scripts/qrspi_ci_revise_bump_test.py && python3 scripts/run_tests.py bump`
   - [ ] Pure-core test passes standalone
   - [ ] `run_tests.py bump` discovers and runs it green
   - [ ] Manual: run the script against a throwaway branch with no trailer → publishes `CI-Revise-Attempt: 1`; run again → `2` (exactly one trailer, subject intact); simulate a `gt` failure → non-zero exit + `ok:false` JSON

---

## Slice 2: Resolver `ciGaveUp` terminal-state field + tests

### Core Logic

8. ⚠️ Modify `scripts/qrspi_resolve_state.py` — add `ciGaveUp` to the decision builder, defaulting `False` on every decision path (mirroring the existing `ciFailing` boolean) (ref: structure.md Modified Types, design.md Decision 2 Option A).
   - **Current:** the `wait`/`revise` decision dict carries `action`, `phase`, `ciFailing` (bool), and a free-text `reason`; no `ciGaveUp` field.
   - **After:** every decision dict additionally carries `ciGaveUp: bool` (default `False`).
9. ⚠️ Modify `scripts/qrspi_resolve_state.py` — on the cap-reached red→`wait` branch (where `attempt < ci_revise_cap` is False on a red frontier), set `ciGaveUp = True` and emit a distinct reason string (e.g. "CI red and revise cap reached — needs manual diagnosis"). Do NOT change the `attempt < cap` comparison itself (ref: structure.md Slice 2 Files touched, design.md §Delta resolver bullet, OQ2 — raise on every cap-reached red→wait per Decision 3 Option A).
   - **Current:** cap-reached red frontier returns `wait` with `ciFailing` true and prose reason only.
   - **After:** same `wait`/`ciFailing`, additionally `ciGaveUp = True` and a distinct reason.

### Tests

10. ⚠️ Modify `scripts/qrspi_resolve_state_test.py` — add cases (ref: structure.md Slice 2 Files touched, AC4/AC5):
    - cap-reached red (`ciReviseAttempt >= cap`) → `wait` with `ciGaveUp == True` and the distinct reason
    - under-cap red (`ciReviseAttempt < cap`) → `revise` with `ciGaveUp == False`
    - a non-CI `wait` path (e.g. pending CI, thread-only) carries `ciGaveUp == False` (default unchanged)
11. Run: `python3 scripts/qrspi_resolve_state_test.py`
    - **Expected:** new + all existing cases pass
12. Run: `python3 scripts/run_tests.py resolve`
    - **Expected:** green
13. Run: `python3 scripts/run_tests.py`
    - **Expected:** full suite green — confirms no existing decision consumer regresses on the additive defaulted field

### Verify Slice 2

14. **Checkpoint:** `python3 scripts/run_tests.py resolve && python3 scripts/run_tests.py`
    - [ ] `qrspi_resolve_state_test.py` passes (new + existing cases)
    - [ ] `run_tests.py resolve` green
    - [ ] Full suite green — additive defaulted field tolerated by all consumers

---

## Slice 3: Wire `doRevise` to the helper + surface `ciGaveUp` in JS + end-to-end verify

### Core Logic

15. ⚠️ Modify `scripts/qrspi_resolve.py` — add a pure `red_branches_of(decision, phases, ticket)` and emit it as the top-level envelope field `ciRedBranches`, mirroring `ci_failing_checks_of` (ref: design.md Risk row 5 / OQ3; structure.md Contracts). Returns the ascending list of branches the helper must bump this pass:
    - non-CI decision (`ciFailing` False) ⇒ `[]`
    - implementation ⇒ each `phases["implementation"]["slices"][*]` with `ciState == "red"`, as `"<ticket>/slice-<n>"`, ascending (per-slice `ciState` is attached by the gather, `scripts/qrspi_pr_state.py`)
    - design/plan ⇒ `["<ticket>/<phase>"]` when the frontier phase `ciState == "red"`, else `[]`
    Thread `ticket` into `build_envelope` (or compute in the caller and pass like `slices=`).
    - **Current:** the envelope carries aggregated `ciFailing` + flat `ciFailingChecks` + slice branch *names* (`slices`), with **no per-slice red/green map** — so `doRevise` cannot deterministically tell which slice branches are red (today only the spawned worker discovers that via `gh pr checks`).
    - **After:** `ciRedBranches` hands `doRevise` the exact deterministic list, so the JS never re-derives per-slice CI nor delegates "which slices are red" to an LLM worker (which would reintroduce the non-determinism Option A′ exists to remove).
16. ⚠️ Modify `scripts/qrspi_resolve_test.py` — cases for `red_branches_of` / `ciRedBranches`: implementation slices `[red, green, red]` ⇒ `["<t>/slice-1", "<t>/slice-3"]`; red design frontier ⇒ `["<t>/design"]`; any non-CI decision ⇒ `[]`.
    - Run: `python3 scripts/run_tests.py resolve` — **Expected:** green (new + existing).
17. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`doRevise`, step-2b worker prompt) — DELETE the **ENTIRE** step-6 `CI-Revise-Attempt` block (not just its CI branch). The worker now only diagnoses, fixes, amends content, and re-requests review; it never touches the counter. Renumber the prompt's remaining steps (old step-7 re-request → new step-6, old step-8 → 7) (ref: structure.md Slice 3 Files touched (a), design.md §Delta JS bullet (a), Decision 1 Option A′).
    - **Current:** step-6 is a shared template — its `${ciFailing ? '<prior+1>' : 'overwrite to 0'}` else-branch is the SOLE reset-to-0 on the `changeRequested && !ciFailing` (green-CI change-request) path through 2b.
    - **After:** no trailer logic in the worker at all; the CI +1 moves to the helper (step 18) and the green-CI-change-request reset is re-homed (step 19).
18. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`doRevise`) — after the step-2b content worker returns, when `ciFailing` is true run `qrspi_ci_revise_bump.py` **UNCONDITIONALLY** (regardless of worker `ok`) once per branch in `r.ciRedBranches`, lowest-first. Invoke via a thin worker that types the one verbatim `python3 <engineCmdFor(r,'scripts/qrspi_ci_revise_bump.py')> --ticket <id> --branch <BRANCH>` command (append ` --stack` when `d.phase === 'implementation'`) — using `engineCmdFor`/`r.repoRoot` for the path, NOT `engineCmd`'s `.` (ref: structure.md Slice 3 Files touched (b), design.md §Delta JS bullet (b); MEMORY: batch-worker-cwd-engine-path). The bump fires whenever `ciFailing` is true **regardless of `changeRequested`** — i.e. for both the combined 2b (`changeRequested && ciFailing`) and the pure-CI 2c decisions; do NOT gate it to the `!changeRequested` branch.
    - **Current:** the CI-path counter advance was bundled into the worker's step-6 and only fired when the worker successfully amended.
    - **After:** the deterministic helper is the sole increment authority, invoked unconditionally per still-red branch after the content worker returns.
19. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`doRevise`) — **re-home the non-CI reset** (closes the step-17 caution): on the step-2b exit where `changeRequested && !ciFailing` (green-CI change request), call `resetCiReviseTrailer(t, r, d, answered)` **unconditionally** after the worker returns. It is idempotent (no-ops when the trailer is absent or already 0), so no "did the worker amend?" detection is needed (ref: structure.md Slice 3 Files touched (c)).
    - **Current:** the `changeRequested && !ciFailing` reset-to-0 lived in worker step-6's else branch (deleted in step 17).
    - **After:** it is an explicit `resetCiReviseTrailer` call in `doRevise`, preserving the CLAUDE.md invariant "every non-CI amend overwrites the trailer to 0" for the one path that loses its writer when step-6 is deleted. Net: bump on the CI path, reset on the non-CI path, worker never writes the counter — one writer per path.
20. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`doRevise`, step-2a) — confirm step-2a's `resetCiReviseTrailer` call is **UNCHANGED** (still gated on `answered.some(a => a.applied)`); only step-2b gains a new reset call (step 19). Non-CI reset now fires on 2a (comment-only, on apply) AND 2b (`changeRequested && !ciFailing`, unconditional) (ref: structure.md Slice 3 Files touched (d)).
21. ⚠️ Modify `.claude/workflows/qrspi-batch.js` (`wait`-branch result/skip record + per-ticket log; `doRevise` result record) — surface `ciGaveUp` from the resolver decision into the recorded result object and the per-ticket log line, and treat a **non-zero** `qrspi_ci_revise_bump.py` exit as a recorded **hard failure** on the revise result so a count that could not advance is never silent (ref: structure.md Slice 3 Files touched, design.md Risk Register row 4, OQ1 recommended resolution, Q10/Q14).
    - **Current:** the `wait` record / log surfaces `ciFailing` and the prose reason only; no helper exists to record a counter-advance failure.
    - **After:** the record / log additionally surfaces `ciGaveUp`, and a non-zero helper exit is recorded as a hard failure on the revise result.

### Tests

22. `.claude/workflows/qrspi-batch.js` is harness-coupled and not unit-testable per CLAUDE.md — the JS wiring (steps 17–21) is verified by manual end-to-end run plus the full Python suite. NOTE: unlike the prior draft, Slice 3 now also carries real Python unit coverage — the `ciRedBranches` aggregation (step 16) under `python3 scripts/run_tests.py resolve`.

### Verify Slice 3

23. **Checkpoint (e2e, unfixable red):** On a deliberately-unfixable red PR, run the batch revise pass; the worker reports failure / pushes no content amend.
    - [ ] The helper still advances the trailer by 1 each pass — confirm on the pushed PR head via `gh pr view` / `git log -1 --format=%B`
24. **Checkpoint (multi-slice selectivity — Gap 2):** On an implementation frontier with slices `[red, green, red]`, run one revise pass.
    - [ ] Only `slice-1` and `slice-3` heads carry a bumped trailer; `slice-2` is untouched (no needless re-push) — proves `ciRedBranches` drives the helper, not a bump-all
25. **Checkpoint (non-CI reset — Gap 1):** A `changeRequested && green-CI` revise pass.
    - [ ] The amended head trailer reads `CI-Revise-Attempt: 0` (or absent) — confirms step 19's reset fired and step-17's deletion didn't strand the path
26. **Checkpoint (cap):** Repeat the revise pass until `ciReviseCap` (default 3) is reached.
    - [ ] The resolver returns `wait` with `ciGaveUp == True`, and the JS result record / per-ticket log surfaces it
27. **Checkpoint (green reset):** Make a pass that turns CI green.
    - [ ] The gather's read-side not-red→0 reset zeroes the count (AC3 unchanged)
28. **Checkpoint (no regression):** `python3 scripts/run_tests.py`
    - [ ] Full suite green — no Python regressions

### Open decisions for the plan reviewer (not silently resolved)

- **OQ2 (AC4 semantics):** the plan raises `ciGaveUp` on **every** cap-reached red→`wait` (Decision 3 Option A, step 9). Confirm AC4 does not instead intend it only when ≥1 failed-no-change attempt occurred. The plan's choice is the simpler default (the operator action — manual diagnosis — is identical either way), but it is a genuine product-semantics call AC4 leaves open.
- **Scope check (step 15):** surfacing already-gathered per-slice `ciState` into the envelope as `ciRedBranches` is **re-emission, not re-gathering** — but the ticket lists "the CI normalization / gather of `statusCheckRollup`" as out of scope. Confirm this reading before implementing step 15. (Fallback if disallowed: bump every branch in `r.slices` + the phase branch — numerically safe because the gather's not-red→0 read-side reset zeroes any green/pending slice's trailer — at the cost of needless re-push / CI churn on passing slices.)

---

## Rollback Notes

- Step 1–6 (Slice 1, new files): rollback by deleting `scripts/qrspi_ci_revise_bump.py` and `scripts/qrspi_ci_revise_bump_test.py`. No persistent state written; no migration. Safe additive create.
- Step 3 (helper publishes via `gt submit`): this MUTATES a live PR head commit (writes the trailer and pushes). A wrong increment on a real branch is reversible by re-running the non-CI `resetCiReviseTrailer` path (or a manual `gt modify -m` restoring the prior trailer value) — the trailer is the only durable state and is idempotently rewritable. Validate against a throwaway branch first (Step 7 manual check).
- Step 8–9 (resolver `ciGaveUp`): additive defaulted field; rollback by removing the field and the cap-branch assignment. Pure function, no state, no migration.
- Step 15–16 (`ciRedBranches` envelope field): additive top-level field + pure `red_branches_of` function; rollback by removing the function, the `build_envelope` emit, and the test. Inert to old consumers (they ignore the field). No state, no migration.
- Step 17–21 (qrspi-batch.js): rollback by restoring the deleted worker step-6 block and removing the helper-invocation (18), the re-homed non-CI reset (19), and the `ciGaveUp` / non-zero-exit surfacing (21). The single-writer invariant is now a **three-way matched set** — step-6 deletion (17), bump invocation (18), and the re-homed reset (19) must roll back together: dropping 18 while keeping 17 **zero-counts** the CI path; dropping 19 while keeping 17 **strands** the green-CI-change-request reset; restoring step-6 while keeping 18 **double-counts**. No persistent state in the JS itself; the only durable artifact is the trailer, governed by the helper (CI +1) and `resetCiReviseTrailer` (non-CI 0).
