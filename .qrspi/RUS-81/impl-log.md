# Implementation Log — CI-gated revision: resolver reacts to CI check state and auto-revises red frontier PRs

## Session 1 — Slice 1: Gather (CI rollup query, normalizers, additive per-PR fields)

**Timestamp:** 2026-06-15T16:28:25Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10, T11, T12
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py pr_state` → 1 file passed, 0 failed (all new check_rollup_state / ci_revise_attempt / not-red→0 reset / additive-shape cases pass)
- `python3 scripts/run_tests.py resolve` → 2 files passed (resolve_state, resolve), 0 failed (additive fields inert to existing consumers)
- `python3 scripts/run_tests.py contract` → 2 files passed (producer, consumer), 0 failed (byte-pinned seam fixtures still hold)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. Note on the Unverified Assumption flagged in structure §UA and plan §1.2: the `statusCheckRollup{state contexts(first:100){nodes{__typename ... on CheckRun{name conclusion detailsUrl} ... on StatusContext{context state targetUrl}}}}` fragment was implemented as planned with N=100. It was NOT verified against the live GitHub GraphQL schema (no `gh` network call made in this slice — the parsers are pure/unit-tested and the GraphQL string is exercised only by the subprocess path, which is not unit-tested per project convention). Slice 4's manual e2e is the first point this query shape hits the live API.

**Notes for next session:**

- Slice 1 adds these gathered per-PR fields (both the empty-default and populated `parse_pr_nodes` dicts now carry all three):
  - `ciState: str` — one of `"green" | "red" | "pending" | "none"` (from `check_rollup_state`).
  - `ciFailingChecks: list[{name, detailsUrl}]` — populated ONLY when `ciState == "red"`; `[]` otherwise.
  - `ciReviseAttempt: int` — the EFFECTIVE consecutive-red counter: the parsed `CI-Revise-Attempt: N` trailer value, but forced to `0` whenever `ciState != "red"` (the not-red→0 reset is already applied at gather time, so Slice 2's resolver reads it directly — no need to re-zero).
- New pure functions in `scripts/qrspi_pr_state.py` (importable): `check_rollup_state(pr_node) -> str`, `ci_revise_attempt(message) -> int`. Two private helpers added: `_head_commit(pr_node)` (the commits(last:1) head commit dict, guarded to `{}`) and `_failing_checks(pr_node)` (the `{name, detailsUrl}` list, treating CheckRun conclusions FAILURE/ERROR/TIMED_OUT/CANCELLED/STARTUP_FAILURE/ACTION_REQUIRED and StatusContext state FAILURE/ERROR as failing).
- `check_rollup_state` takes the PARSED PR NODE (reads `node.commits.nodes[-1].commit.statusCheckRollup.state`), NOT a bare rollup dict. Structure's contract names it `check_rollup_state(node)`; "node" = the PR node. Slice 2's `ci_state(phases, name)` should aggregate the already-gathered `ciState` strings off the per-PR shapes, not re-call `check_rollup_state`.
- `PR_QUERY` now selects `commits(last:1){nodes{commit{message statusCheckRollup{state contexts(...)}}}}`. The head-commit `message` is what carries the `CI-Revise-Attempt` trailer (Slice 4 writes it).
- The slice loop in `build_state` (lines ~488-493) parses each slice PR through `parse_pr_nodes`, so each slice in `phases.implementation.slices` already carries the three CI fields. The two `phase_pr` synthetic-merge branches (pruned/landed) build from `parse_pr_nodes([])`, so they get the empty-default CI defaults (`none`/`[]`/`0`) — correct, since a pruned/merged head has no live red CI.
- Existing test expectations for `parse_pr_nodes` were updated to include the three additive keys via a `_CI_DEFAULTS` spread constant in the test file (in-slice test maintenance, not a structure deviation).

---

## Session 2 — Slice 2: Resolver (CI-gated `revise`/`wait` branch with cap)

**Timestamp:** 2026-06-15T16:35:06Z
**Tasks completed:** T13, T14, T15, T16, T17, T18, T19, T20
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py resolve_state` → 1 file passed, 0 failed (Slice 2 verification gate, plan §2.20). Direct run reports 60 cases passed (was 41; 19 new CI cases).
- `python3 scripts/run_tests.py resolve_test` → 1 file passed (the `qrspi_resolve.py` consumer still constructs a valid `resolve(state)` call via the default cap).
- `python3 scripts/run_tests.py pr_state` → 1 file passed (Slice 1 gather unaffected).
- `python3 scripts/run_tests.py` (full suite) → 36 passed, 1 FAILED: `qrspi_contract_fixtures_producer_test.py::test_resolve` (and the consumer pin would fail identically). See note below — this is the expected Slice 3 lockstep repair, NOT a regression in this slice's scope.

**Deviations from structure.md:**

- none on contracts. One bounded implementation choice: `resolve(state, ci_revise_cap=3)` was given a DEFAULT of `3` rather than a bare required positional. Structure says the cap is "passed in by the caller … never read from disk inside the resolver, preserving purity" — the default does not read disk and does not break purity; it only keeps the resolver additive so the untouched `qrspi_resolve.py` call site (`resolve(state)`, updated to pass the explicit cap in Slice 3 / T21) stays valid and `qrspi_resolve_test.py` does not regress mid-feature. The default mirrors the documented config default (3) and the additive `changeRequested` flag pattern. Slice 3 makes the caller explicit.

**Deviations from plan.md:**

- none. Note on plan §2.18b (frontier CR + CI-fail in one pass): this is implemented in the EXISTING unified feedback handler (block "2b"), not the new CI branch ("2c"). Block 2b now also computes `ciFailing = (ci_state(phases, f) == "red")` for the feedback phase it selects and folds it into the single `revise` decision, so a frontier carrying a change request and/or reviewer comments AND red CI returns one `revise` with both `changeRequested` and `ciFailing` set. The standalone CI branch (2c) handles the no-feedback red/pending/green/none cases on the frontier (highest existing phase), slotted after 2b and before the active-phase block, exactly per the precedence rule.

**Notes for next session:**

- Slice 2 edits ONLY `scripts/qrspi_resolve_state.py` + `scripts/qrspi_resolve_state_test.py`. Changes:
  - `decision()` fixed key set gained `ciFailing: bool` (default `False`), placed between `changeRequested` and `reason`. Because the resolve envelope embeds the full decision dict, this new key now appears in the producer dump — which is WHY `scripts/fixtures/contract_seam/resolve/wellformed.json` + `prose_wrapped.json` + the producer/consumer pins are now byte-stale. **Slice 3 (T25-T28) repairs these four files in byte-for-byte lockstep** (plan Rollback Notes: "Slice 3's envelope re-emit depends on Slice 2's `ciFailing` decision key"). I deliberately did NOT touch them — they are Slice 3 scope. The producer dump now emits the decision block with `"ciFailing": false` inserted directly before `"reason"`; the consumer fixture must match byte-for-byte.
  - `resolve(state, ci_revise_cap=3)` — new keyword param (default 3). Slice 3 T21 must thread the config-resolved cap in as the explicit argument.
  - Two new pure helpers: `ci_state(phases, name) -> str` (implementation aggregation: any slice red→red, else any pending→pending, else any green→green, else none) and `ci_revise_attempt_of(phases, name) -> int` (reads the gathered `ciReviseAttempt`, already not-red→0 normalized at gather time; implementation aggregates per-slice attempts via `max(...)`). `ci_revise_attempt_of` is an internal addition beyond the structure's named `ci_state` contract — needed to read the gathered per-phase attempt count for the cap comparison; it is pure and unit-covered.
  - New resolver block "2c" (after the unified feedback handler 2b, before `active = max(...)`): frontier red & attempt `< cap` → `revise` + `ciFailing=True`; frontier red & attempt `>= cap` → `wait` + `ciFailing=True`; frontier pending → `wait`; green/none → fall through (no-op). "Frontier" = the highest existing phase (`max(existing, key=_order)`).
  - The CI branch runs BEFORE the implementation completeness gate, so a red OPEN slice with unbuilt later slices (later slices contribute `ciState="none"`, aggregate stays red) revises before `advance` builds the next slice (review finding #2 / plan §2.18c).
  - Test infra: `_phase()`/`_slice()` gained additive `ci_state="none"`/`ci_attempt=0` kwargs; `case()` gained a `cap=3` kwarg threaded into `resolve(..., ci_revise_cap=cap)` in the runner; the runner tuple is now `(name, st, expect, cap)`. Existing 41 cases were not semantically changed (they pass no `ci_state`, so `ci_state` defaults to "none" → CI no-op).

---

## Session 3 — Slice 3: Orchestrator wiring (config cap, envelope re-emit, contract fixtures)

**Timestamp:** 2026-06-15T16:45:18Z
**Tasks completed:** T21, T22, T23, T24, T25, T26, T27, T28, T29, T30
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` (full suite, Slice 3 verification gate / plan §3.30) → 37 files passed, 0 failed
- `python3 scripts/qrspi_resolve_test.py` (direct) → 119 cases passed, 0 failed (was ~75; +44 new: coerce_cap, load_ci_revise_cap, ci_failing_of, ci_failing_checks_of, build_envelope CI re-emit)
- `python3 scripts/run_tests.py contract` → 2 files passed (producer + consumer byte-pins hold across the new envelope shape; consumer ran 22 tests, NOT skipped — node present)

**Deviations from structure.md:**

- none on the named contracts. Two bounded, additive implementation choices, both pure/unit-covered:
  - The structure's "Envelope re-emit … a helper mirroring `comment_targets_of`" is implemented as TWO helpers, not one: `ci_failing_of(decision)` (the bool, sourced from `decision["ciFailing"]` exactly like `comment_targets_of` reads the decision) and `ci_failing_checks_of(decision, phases)` (the list). They are split because the fixed-key `decision` dict carries `ciFailing` but CANNOT carry `ciFailingChecks` (per Slice 1, the failing-check entries live on the per-PR/phase shape, not the decision). So `ci_failing_checks_of` re-aggregates the decision phase's gathered `ciFailingChecks` from `phases` (implementation: concatenate per-slice lists, mirroring how `qrspi_resolve_state.ci_state` aggregates across slices). This required adding an optional `phases=None` param to `build_envelope` and threading `state.get("phases", {})` into the `main()` call site. Default `phases=None` → `ci_failing_checks_of` returns `[]`, so old callers (incl. the producer test, which passes no `phases`) are byte-for-byte unaffected.
  - `coerce_cap` rejects `bool` explicitly (bool is an `int` subclass) so a config `true`/`false` never reads as `1`/`0`; both fall back to the default 3, consistent with "non-positive-integer → 3".

**Deviations from plan.md:**

- none. T21 uses the flat top-level `ciReviseCap` key (NOT nested `ci.reviseCap`) per the plan's explicit note and project memory that `qrspi_config.py`'s reader handles a single top-level key only. The cap is resolved via `qrspi_config.read_config(repo_root)` + the pure `coerce_cap`, NOT the `qrspi_config.py` CLI/`select_value` (which is string-default-oriented and would not give the positive-int/non-positive→3 semantics); this stays within the contract ("resolve `ciReviseCap` via `scripts/qrspi_config.py`") by importing and reusing its `read_config`.

**Notes for next session:**

- Slice 3 edits exactly the 7 files in scope (`scripts/qrspi_resolve.py`, `.qrspi/config.example.json`, `scripts/fixtures/contract_seam/resolve/wellformed.json`, `.../prose_wrapped.json`, `scripts/qrspi_contract_fixtures_producer_test.py`, `scripts/qrspi_contract_fixtures_consumer_test.py`, `scripts/qrspi_resolve_test.py`). No resolver (`qrspi_resolve_state.py`) or gather (`qrspi_pr_state.py`) changes.
- The resolve envelope now carries TWO additive top-level keys, inserted directly after `commentTargets`: `ciFailing` (bool) and `ciFailingChecks` (list of `{name, detailsUrl}`). For a non-CI decision they default to `False`/`[]`. Slice 4's `doRevise` reads them as `r.ciFailing` / `r.ciFailingChecks` (the consumer contract), NOT from `r.decision`.
- PREVIOUS_NOTES was correct: `wellformed.json` already had the in-decision `"ciFailing": false` (Slice 2 repair) and was NOT re-edited for that. Slice 3 ADDED the top-level `ciFailing`/`ciFailingChecks` to it (regenerated byte-for-byte from the live `build_envelope` producer dump, `json.dumps(env, indent=2)+"\n"`). `prose_wrapped.json` also gained the in-decision `"ciFailing": false` AND the two top-level keys to mirror wellformed (the consumer extractor only needs a balanced object, but mirroring keeps the two resolve fixtures shape-consistent).
- `build_envelope(...)` signature gained a trailing `phases=None` kwarg. Any future caller wanting populated top-level `ciFailingChecks` MUST pass `phases=state["phases"]`; omitting it yields `[]` (safe default).
- Cap wiring: `main()` now calls `resolve(state, ci_revise_cap=load_ci_revise_cap(repo_root))`. `load_ci_revise_cap` reads the flat `ciReviseCap` config key (default 3, non-positive/non-int/bool → 3 via `coerce_cap`).

---

## Session 4 — Slice 4: Worker (`doRevise` CI-failure path + durable trailer write)

**Timestamp:** 2026-06-15T16:54:12Z
**Tasks completed:** T31, T32
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → syntax OK
- `python3 scripts/run_tests.py` → 37 passed, 0 failed (regression gate; `qrspi-batch.js` is harness-coupled and not unit-testable per project convention, so slice-4's own verification is manual e2e — plan step 33)

**Deviations from structure.md:**

- none (Contracts honored: `doRevise` reads `r.ciFailing` / `r.ciFailingChecks` at the envelope top level, not from `decision`; no `RESOLVE_ACTIONS` change — reuses `revise`/`wait`; trailer write is path-dependent: CI path increments `<prior+1>`, every non-CI amend overwrites to `0`).

**Deviations from plan.md:**

- none in substance. One scope addition the plan step 32 implies but does not name a site for: the writer-side reset on a NON-CI amend also applies to the **comment-only APPLY** path (not just the CR/CI 2b prompt). Added a dedicated best-effort `resetCiReviseTrailer(...)` worker invoked from step 2a when `answered.some(a => a.applied)`, since `qrspi_revise_amend.py` preserves the message verbatim and would otherwise leave a stale trailer. This is durability/observability hygiene only — the gather's read-side reset (`ciReviseAttempt = ... if ciState=="red" else 0`) already forces the EFFECTIVE cap count to 0 whenever CI is not red, so the cap is correct regardless.

**Notes for next session:**

- Slice 4 edits exactly ONE in-scope file: `.claude/workflows/qrspi-batch.js`. No Python/script/fixture changes.
- `doRevise` now reads `const ciFailing = !!(r.ciFailing || (d && d.ciFailing))` and `const ciFailingChecks = Array.isArray(r.ciFailingChecks) ? r.ciFailingChecks : []`. The early-return guard now also admits a CI-only revise (`!changeRequested && targets.length === 0 && !ciFailing` is the new skip condition). The comment-only short-circuit (step 2a) is now `!changeRequested && !ciFailing` so a red-CI/no-CR PR falls through to the fix+re-request path (2b).
- Step 2b prompt is path-aware: a `trigger` line states whether it is CR-only, CI-only, or both; a `checksBlock` renders `r.ciFailingChecks` (name + detailsUrl). The worker is instructed to read REAL failing-check output (`gh pr checks <PR>` → `gh run view <run-id> --log-failed` / open detailsUrl) BEFORE any fix (honesty-bound), fix ALL red slices in one pass (implementation), amend content via `qrspi_revise_amend.py`, then do a SEPARATE message-only `gt modify -m` to set the trailer, then `gt submit --rerequest-review`.
- TRAILER MECHANISM (important for Slice 5 docs / any future worker change): `qrspi_revise_amend.py` preserves the commit message **verbatim** — it does NOT and cannot write the trailer. So the trailer is written by a DISTINCT message-only amend the worker performs after the content amend: read `git log -1 --format=%B`, replace/append exactly one `CI-Revise-Attempt: N` line, `gt modify --no-interactive -m "<full message>"` (no staged files — the one place a bare `gt modify` is correct), then `gt submit`. CI path: `N = prior+1` (prior read off the head commit's existing trailer, absent ⇒ 0). Non-CI path: `N = 0`.
- The `resetCiReviseTrailer(...)` helper (new, after `respondToComments`) is best-effort: a failure logs a WARN and does NOT fail the revise, because the read-side reset already protects cap correctness.
- Slice 5 (Docs) is next: document the CI-gated revise trigger + the consecutive-red counter with its TWO resets (writer-side here in `doRevise`, AND the gather's read-side not-red→0). Manual e2e of this slice (plan step 33) was NOT run in this session — the harness needs a live ticket with a known-red frontier PR; flag for the human-driven e2e gate.

---

## Session 5 — Slice 5: Docs (CI-gated revise behavior)

**Timestamp:** 2026-06-15T17:05:00Z
**Tasks completed:** T34, T35, T36
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` (full suite, Slice 5 verification gate / plan §5.36) → 37 passed, 0 failed (docs-only change does not regress code)

**Deviations from structure.md:**

- none (Slice 5 is docs-only; no new types/contracts).

**Deviations from plan.md:**

- none in substance. Plan T34 says "Modify `CLAUDE.md`" — the Lifecycle section it names lives in the project `.claude/CLAUDE.md` (the repo-root `CLAUDE.md` is a 0-line `@~/.agents/AGENTS.md` import with no Lifecycle section), so the edit was made in `.claude/CLAUDE.md`. Plan T35 also says "Remove any stale 'CI is ignored entirely today' claim" — a full grep of `docs/qrspi-pr-gated-lifecycle-design.md` found NO such claim (the doc is the original RUS-50 design, which never asserted CI was consulted at all), so the removal is vacuous; nothing stale was deleted.

**Notes for next session:**

- Slice 5 edits exactly TWO in-scope files: `.claude/CLAUDE.md` (Lifecycle section — added a CI-gated revise bullet + updated the qrspi-batch actions bullet to name red-CI/pending/at-cap) and `docs/qrspi-pr-gated-lifecycle-design.md` (added a `### CI gate (RUS-81)` subsection to §5 Predicates covering the green/red/pending/none normalization, the revise/wait predicate table, the after-2b/before-active precedence slot, the configurable `ciReviseCap` cap default 3 from `.qrspi/config.json`, and the dual reset). No code/script/fixture/workflow changes.
- The §4 resolve-loop pseudocode in the design doc was NOT rewritten — it is the original RUS-50 manual-revise loop and does not reflect the shipped RUS-54 unified-feedback handler either; rewriting it is out of this slice's scope. The new CI gate is documented declaratively in §5 (Predicates), which is the doc's home for advancement signals (READY/RESET live there too).
- Manual e2e (plan step 33 for Slice 4, and the manual doc read in step 36) is the only remaining gate: a live ticket with a known-red frontier PR is needed to exercise `doRevise`'s CI path end-to-end. Flag for the human-driven e2e gate before landing — no automated coverage exists for `qrspi-batch.js` per project convention.
