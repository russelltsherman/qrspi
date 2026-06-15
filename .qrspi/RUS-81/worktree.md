# Work Tree — CI-gated revision: resolver reacts to CI check state and auto-revises red frontier PRs

**Plan basis:** plan.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T1 → T6 → T7 → T12 → T13 → T15 → T16 → T20 → T21 → T23 → T30 → T31 → T32 → T33 → T34 → T36

> The critical path runs through the data plumbing of each slice: Slice 1 adds the gathered CI fields (T1/T6/T7), Slice 2 consumes them in the resolver decision (T13/T15/T16), Slice 3 threads the cap + re-emits the envelope (T21/T23), Slice 4 wires the worker `doRevise` CI path + trailer (T31/T32), and Slice 5 documents the shipped behavior (T34). Each slice's verify gate (T12, T20, T30, T33, T36) is the session-closing checkpoint. Slices are strictly bottom-up dependent (Slice 3 envelope re-emit needs Slice 2's `ciFailing` key; see Rollback Notes), so sessions cannot overlap.

## Session 1 — Slice 1: Gather (CI rollup query, normalizers, additive per-PR fields)

**Load:** structure.md §Contracts (`check_rollup_state`, `ci_revise_attempt` signatures), plan.md §Slice 1
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Extend `PR_QUERY` GraphQL with `statusCheckRollup{state}` under per-PR head commit | — | §1.1 | S | pending |
| T2 | Extend `PR_QUERY` with per-check `contexts` detail (CheckRun/StatusContext fragments, N=100) | T1 | §1.2 | S | pending |
| T3 | Extend `PR_QUERY` with head-commit `message` (carries attempt trailer) | T1 | §1.3 | S | pending |
| T4 | Add pure `check_rollup_state(node) -> str` normalizer (SUCCESS/FAILURE/ERROR/PENDING/EXPECTED/null → green/red/pending/none) | — | §1.4 | S | pending |
| T5 | Add pure `ci_revise_attempt(message) -> int` trailer parser (absent/malformed → 0) | T3 | §1.5 | S | pending |
| T6 | Add 3 additive keys (`ciState`,`ciFailingChecks`,`ciReviseAttempt`) to `parse_pr_nodes` EMPTY-DEFAULT dict | — | §1.6 | S | pending |
| T7 | Add 3 additive keys with computed values to `parse_pr_nodes` POPULATED dict (incl. not-red→0 reset) | T2, T4, T5, T6 | §1.7 | M | pending |
| T8 | Add `check_rollup_state` table-driven test cases (5 states + null/absent) | T4 | §1.8 | S | pending |
| T9 | Add `ci_revise_attempt` test cases (present/absent/malformed → 2/0/0) | T5 | §1.9 | S | pending |
| T10 | Add counter-reset test (stale trailer + non-red → effective 0) | T7 | §1.10 | S | pending |
| T11 | Add additive-shape guard test (both dicts carry the 3 keys) | T6, T7 | §1.11 | S | pending |
| T12 | **Verify Slice 1** — `python3 scripts/run_tests.py pr_state` (+ resolve still green) | T8, T9, T10, T11 | §1.12 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. The resolver work in Slice 2 consumes the new gathered fields but edits a different module (`qrspi_resolve_state.py`); fresh context drops the `qrspi_pr_state.py` GraphQL/parser details and loads the resolver contract instead.

## Session 2 — Slice 2: Resolver (CI-gated `revise`/`wait` branch with cap)

**Load:** structure.md §Contracts (`ci_state` signature, `resolve(...)` decision-key set, precedence-slot rule), plan.md §Slice 2, plan.md §Slice 1 (gathered field names `ciState`/`ciFailingChecks`/`ciReviseAttempt` only)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T13 | Add `ciFailing: bool` (default False) to `decision()` fixed key set | T12 | §2.13 | S | pending |
| T14 | Add explicit `ci_revise_cap: int` parameter to `resolve(...)` signature | T13 | §2.14 | S | pending |
| T15 | Add pure `ci_state(phases, name) -> str` helper (red>pending>green/none aggregation) | T12 | §2.15 | S | pending |
| T16 | Add CI-gated branch to `resolve(...)` (after 2b, before active-phase): red<cap→revise+ciFailing; red≥cap→wait; pending→wait; green/none→no-op; per-slice `max(...)` attempt | T14, T15 | §2.16 | L | pending |
| T17 | Add resolver test matrix (red/pending/green/none × frontier/non-frontier × cap) | T16 | §2.17 | M | pending |
| T18 | Add precedence tests (non-frontier CR resets; frontier CR+CI one pass; incomplete-impl red slice revises) | T16 | §2.18 | M | pending |
| T19 | Update every existing `resolve(...)` test call site to pass `ci_revise_cap` | T14 | §2.19 | M | pending |
| T20 | **Verify Slice 2** — `python3 scripts/run_tests.py resolve_state` (cap-then-wait AC6; green/none no-op) | T17, T18, T19 | §2.20 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and verified. Slice 3 moves to the orchestrator/envelope layer (`qrspi_resolve.py`, config, byte-pinned fixtures) — a different concern from the pure decision logic; fresh context loads the envelope shape and fixture-lockstep rule.

## Session 3 — Slice 3: Orchestrator wiring (config cap, envelope re-emit, contract fixtures)

**Load:** structure.md §Contracts (envelope top-level shape, `build_envelope` params), plan.md §Slice 3, plan.md §Rollback Notes (fixtures-as-atomic-unit), plan.md §Slice 2 (`ciFailing` decision key only); project memory: `qrspi_config.py` reads a SINGLE flat top-level key (no dot-path) → use flat `ciReviseCap`
**Estimated context:** ~24% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T21 | Read configurable cap in `qrspi_resolve.py` via `qrspi_config.py` (flat `ciReviseCap`, default 3, non-positive→3); thread into `resolve(...)` | T20 | §3.21 | S | pending |
| T22 | Add envelope re-emit helper (mirrors `comment_targets_of`) surfacing `ciFailing`/`ciFailingChecks` | T20 | §3.22 | S | pending |
| T23 | Extend `build_envelope(...)` with top-level `ciFailing`/`ciFailingChecks` from the step-22 helper | T22 | §3.23 | S | pending |
| T24 | Document flat `ciReviseCap` key (default 3, non-positive→3) in `.qrspi/config.example.json` | T21 | §3.24 | S | pending |
| T25 | Add CI keys to `fixtures/contract_seam/resolve/wellformed.json` (byte-for-byte producer dump) | T23 | §3.25 | S | pending |
| T26 | Add same CI keys to `fixtures/contract_seam/resolve/prose_wrapped.json` (byte-for-byte) | T25 | §3.26 | S | pending |
| T27 | Update resolve producer pin in `qrspi_contract_fixtures_producer_test.py` to new shape | T25 | §3.27 | S | pending |
| T28 | Update resolve consumer pin in `qrspi_contract_fixtures_consumer_test.py` to new shape | T26 | §3.28 | S | pending |
| T29 | Add `qrspi_resolve_test.py` assertions (cap read from config; envelope re-emits CI keys) | T21, T23 | §3.29 | M | pending |
| T30 | **Verify Slice 3** — `python3 scripts/run_tests.py` (full suite; byte-pin holds; absent/non-positive cap → 3) | T24, T27, T28, T29 | §3.30 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete and verified — the Python data path (gather → resolve → envelope) is fully wired and byte-pinned. Slice 4 moves to the JS worker (`qrspi-batch.js`, harness-coupled, manual-verify only); fresh context loads the `doRevise` contract and trailer-write rule, dropping the Python fixture details.

## Session 4 — Slice 4: Worker (`doRevise` CI-failure path + durable trailer write)

**Load:** structure.md §Contracts (`doRevise` CI branch behavior, `CI-Revise-Attempt` trailer semantics), plan.md §Slice 4, plan.md §Rollback Notes (trailer-write / revert-Slice-2+4-together); project memory: honesty-bound — read REAL `gh run view --log-failed` output before any fix; `qrspi-batch.js` is harness-coupled (no unit test)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T31 | Teach `doRevise` the `ciFailing` branch: consume `ciFailingChecks`, read real failing-check log BEFORE fix, fix code, amend via `qrspi_revise_amend.py`, re-push via `gt submit`; fix ALL red slices in one pass; combined feedback+CI in one pass; no `RESOLVE_ACTIONS` change | T30 | §4.31 | L | pending |
| T32 | Implement path-dependent `CI-Revise-Attempt` trailer write in `doRevise`: CI-path → prior+1; every non-CI/on-green amend → overwrite to 0; preserve subject + other trailers | T31 | §4.32 | M | pending |
| T33 | **Verify Slice 4** — manual e2e: drive a known-red frontier PR through one batch step; confirm real log read + incremented trailer; on-green amend resets trailer to 0 | T32 | §4.33 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 complete and verified end-to-end — the full CI-gated revise loop is functional. Slice 5 is docs-only against `CLAUDE.md` and the lifecycle design doc; fresh context loads the now-shipped behavior to document it accurately and strip stale claims.

## Session 5 — Slice 5: Docs

**Load:** plan.md §Slice 5, plan.md §Slice 2 (resolver precedence slot: after 2b, before active-phase), plan.md §Slice 3 (config cap default 3); shipped behavior summary from Slices 1–4
**Estimated context:** ~15% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T34 | Extend `CLAUDE.md` Lifecycle section: CI-gated revise trigger (red→revise, pending→wait, configurable cap-then-wait, `CI-Revise-Attempt` counter + two resets) | T33 | §5.34 | S | pending |
| T35 | Update `docs/qrspi-pr-gated-lifecycle-design.md`: CI signal, precedence slot (after 2b/before active-phase), config cap (default 3), counter/dual-reset; remove stale "CI is ignored" claim | T33 | §5.35 | S | pending |
| T36 | **Verify Slice 5** — `python3 scripts/run_tests.py` (regression) + manual doc read (accuracy; no stale "CI is ignored" claim) | T34, T35 | §5.36 | S | pending |
