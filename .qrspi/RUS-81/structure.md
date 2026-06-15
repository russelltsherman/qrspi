# Structure Outline — CI-gated revision: resolver reacts to CI check state and auto-revises red frontier PRs

**Design basis:** design.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## New Types

No new struct/class types. The change is carried by additive dict keys on
existing shapes (Python dicts / a JSON envelope) and one new commit-message
trailer. Documented here as logical shapes:

- `CiState` (logical enum, string-valued) — one of `"green" | "red" | "pending" | "none"`.
  Produced by `check_rollup_state(node)`. `none` = no checks / null rollup / a
  committed-but-not-yet-PR'd slice.
- `CI-Revise-Attempt: N` (commit-message trailer, string) — the durable,
  observable-from-GitHub consecutive-red-CI-revise counter (Decision 2 Option C).
  Absent/malformed parses to `0`.

## Modified Types

- `parse_pr_nodes` per-PR shape (`scripts/qrspi_pr_state.py`) — add THREE additive
  keys to BOTH the empty-default and populated return dicts (ref: design.md §Delta):
  - `ciState: str` — normalized rollup (`green|red|pending|none`)
  - `ciFailingChecks: list` — failing check `{name, detailsUrl}` entries (empty unless red)
  - `ciReviseAttempt: int` — *effective* consecutive-red attempt count: the parsed
    trailer value, but forced to `0` whenever `ciState != "red"`
- `build_state` per-phase / per-slice shape (`scripts/qrspi_resolve_state.py`) — carries
  the three new per-PR fields through unchanged (it adds `branchExists` / `n`; the CI
  fields ride along inside the PR shape it wraps).
- `decision()` fixed key set (`scripts/qrspi_resolve_state.py`) — add `ciFailing: bool`
  to the existing `{action, phase, nextPhase, resetToPhase, discardPhases,
  commentTargets, changeRequested, reason}` key set (ref: Decision 1).
- Resolve envelope (`scripts/qrspi_resolve.py` → `wellformed.json`) — add top-level
  re-emit keys `ciFailing` and `ciFailingChecks` (OQ2 RESOLVED), mirroring how
  `commentTargets` is surfaced.
- `.qrspi/config.json` schema — new key `ciReviseCap` (or nested `ci.reviseCap`),
  default `3`, non-positive-integer → `3`.

## Contracts

- `check_rollup_state(node) -> str` — pure normalizer mapping
  `SUCCESS→"green"`, `FAILURE|ERROR→"red"`, `PENDING|EXPECTED→"pending"`,
  `null/absent→"none"`; guarded like `unresolved_thread_count`.
  (`scripts/qrspi_pr_state.py`)
- `ci_revise_attempt(message) -> int` — pure trailer parser reading
  `CI-Revise-Attempt: N` from a head-commit message; absent/malformed → `0`;
  guarded like the other parsers. (`scripts/qrspi_pr_state.py`)
- `ci_state(phases, name) -> str` — pure resolver helper aggregating a phase's
  CI state; for implementation: "any slice red → red; else any pending → pending;
  else green/none". (`scripts/qrspi_resolve_state.py`)
- `resolve(state, ..., ci_revise_cap: int) -> dict` — extended with an explicit
  `ci_revise_cap` argument (cap passed in, never read from disk inside the resolver,
  preserving purity). New CI branch slotted after the unified feedback handler (2b),
  before the active-phase block: frontier red & attempt `< cap` → `revise` with
  `ciFailing=True`; frontier red & attempt `>= cap` → `wait`; frontier pending →
  `wait`; green/none → no-op. For implementation, per-slice attempt counts aggregated
  with `max(...)`. (`scripts/qrspi_resolve_state.py`)
- Config read (`scripts/qrspi_resolve.py`) — resolve `ciReviseCap` via
  `scripts/qrspi_config.py` (default `3`, non-positive-int → `3`), thread into
  `resolve(...)` as the explicit cap argument.
- Envelope re-emit (`scripts/qrspi_resolve.py`) — a helper mirroring
  `comment_targets_of` surfacing `ciFailing` + `ciFailingChecks` at envelope top
  level, plus the new `build_envelope` parameters/keys.
- `doRevise(...)` CI sub-behavior (`.claude/workflows/qrspi-batch.js`) — when
  `decision.ciFailing`, read real failing-check output
  (`gh run view <run-id> --log-failed` / gathered `detailsUrl`), fix code, amend
  via `qrspi_revise_amend.py`, re-push via `gt submit`. Trailer write is
  path-dependent: CI-failure path sets `CI-Revise-Attempt: <prior+1>`; EVERY
  non-CI amend (feedback-only, or any amend where gathered `ciState != "red"`)
  overwrites the trailer to `CI-Revise-Attempt: 0` (writer-side reset). No change
  to `RESOLVE_ACTIONS` (reuses `revise`/`wait`).

## Slice 1: Gather — CI rollup query, normalizers, and additive per-PR fields

**Goal:** The PR-state gather selects `statusCheckRollup` + per-check detail +
head-commit message, and exposes the three additive CI fields (`ciState`,
`ciFailingChecks`, `ciReviseAttempt`) on the per-PR shape — with the
not-red→0 effective-count reset — fully unit-testable in isolation against the
existing resolver (which ignores the new fields until Slice 2).
**Files touched:**

- ⚠️ `scripts/qrspi_pr_state.py` — add `statusCheckRollup{state}`, per-check
  `contexts(...)` detail, and `commits(last:1){nodes{commit{message}}}` to
  `PR_QUERY`; add pure `check_rollup_state(node)` and `ci_revise_attempt(message)`;
  add the three additive keys to both return dicts of `parse_pr_nodes`, computing
  `ciReviseAttempt = ci_revise_attempt(message) if ciState=="red" else 0`
- ⚠️ `scripts/qrspi_pr_state_test.py` — table-driven cases: `check_rollup_state`
  over the five rollup states + null/absent; `ci_revise_attempt` incl.
  absent/malformed→0; the counter-reset case asserting effective `ciReviseAttempt`
  is `0` when `ciState != "red"` despite a stale `CI-Revise-Attempt: 2` trailer

**Verification:**
- [ ] `python3 scripts/run_tests.py pr_state` passes, including the new normalizer,
      trailer-parser, and not-red→0 reset cases
- [ ] The existing resolver/envelope tests still pass (the additive fields are inert
      to consumers that don't read them)
**Context cost:** M
**Depends on:** none

## Slice 2: Resolver — CI-gated `revise`/`wait` branch with cap

**Goal:** The pure resolver consumes the gathered `ciState` / `ciReviseAttempt`
(from Slice 1) and decides: a red frontier under the cap → `revise` (`ciFailing=True`),
red frontier at/above the cap → `wait`, pending frontier → `wait`, green/none →
unchanged; correct precedence (after 2b, before active-phase incl. the
implementation completeness gate); table-driven tests prove every cell.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve_state.py` — add `ci_state(phases, name)` helper (any-red
  → red / any-pending → pending aggregation for implementation); add the CI branch
  after the unified feedback handler (2b), before the active-phase block; add
  `ciFailing` to the `decision()` fixed key set; add explicit `ci_revise_cap`
  argument to `resolve(...)` (per-slice attempts aggregated via `max(...)`)
- ⚠️ `scripts/qrspi_resolve_state_test.py` — table-driven cases: red/pending/green/none
  × frontier/non-frontier × under/at cap; non-frontier CR still resets at step 2;
  frontier CR + CI-fail both handled in one pass; incomplete-implementation case (a
  red open slice with unbuilt later slices revises before advancing, review finding #2);
  update any existing `resolve(...)` call sites in tests to pass the new cap argument

**Verification:**
- [ ] `python3 scripts/run_tests.py resolve_state` passes, including non-frontier-CR-still-resets,
      frontier-CR+CI in one pass, and incomplete-implementation cases
- [ ] A red frontier at cap resolves to `wait` (cap-then-wait, AC6); green/none is a no-op
**Context cost:** M
**Depends on:** Slice 1

## Slice 3: Orchestrator wiring — config cap, envelope re-emit, contract fixtures

**Goal:** `qrspi_resolve.py` resolves the configurable cap from `.qrspi/config.json`,
threads it into `resolve(...)`, and re-emits `ciFailing` + `ciFailingChecks` at the
envelope top level; the byte-pinned contract-seam fixtures and producer/consumer
tests are updated in byte-for-byte lockstep; the example config documents the new key.
**Files touched:**

- ⚠️ `scripts/qrspi_resolve.py` — read `ciReviseCap` via `qrspi_config.py` (default 3,
  non-positive-int → 3), pass into `resolve(...)`; add the `comment_targets_of`-style
  re-emit helper + new `build_envelope` params/keys for `ciFailing`/`ciFailingChecks`
- ⚠️ `.qrspi/config.example.json` — document `ciReviseCap` / nested `ci.reviseCap`
  with `default 3` semantics, per the `$comment` convention
- ⚠️ `scripts/fixtures/contract_seam/resolve/wellformed.json` — add the top-level CI
  keys (byte-for-byte with the producer dump)
- ⚠️ `scripts/fixtures/contract_seam/resolve/prose_wrapped.json` — same keys, byte-for-byte
- ⚠️ `scripts/qrspi_contract_fixtures_producer_test.py` — update the resolve producer
  pin to the new envelope shape
- ⚠️ `scripts/qrspi_contract_fixtures_consumer_test.py` — update the resolve consumer
  pin to the new envelope shape
- ⚠️ `scripts/qrspi_resolve_test.py` — assert the cap is read from config (default 3 /
  non-positive-int fallback) and threaded into `resolve(...)`; assert top-level re-emit
  of `ciFailing`/`ciFailingChecks`

**Verification:**
- [ ] `python3 scripts/run_tests.py` passes whole suite (resolve, contract fixtures,
      pr_state, resolve_state) — envelope byte-pin holds
- [ ] An absent / non-positive `ciReviseCap` falls back to `3`
**Context cost:** M
**Depends on:** Slice 2

## Slice 4: Worker — `doRevise` CI-failure path + durable trailer write

**Goal:** `doRevise` gains the CI sub-behavior: when `ciFailing`, it reads REAL
failing-check output before any fix (honesty-bound), fixes code, amends via
`qrspi_revise_amend.py`, re-pushes via `gt submit`, and writes the path-dependent
`CI-Revise-Attempt` trailer (increment on the CI path; reset to `0` on every non-CI
amend). Combined reviewer-feedback + CI failure handled in one pass; all red slices
fixed in one pass for implementation (OQ3).
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — teach `doRevise` the `ciFailing` branch:
  consume the gathered `ciFailingChecks` (names/URLs), read failing-check logs
  (`gh run view --log-failed` / `detailsUrl`), fix, amend, re-push; manipulate the
  `CI-Revise-Attempt` trailer in the commit message before/within the
  `qrspi_revise_amend.py` amend (increment on CI path, overwrite to `0` on every
  non-CI amend); fix all red slice PRs in one invocation for implementation

**Verification:**
- [ ] Manual end-to-end (per project convention: `qrspi-batch.js` is harness-coupled,
      not unit-testable): drive a ticket with a known-red frontier PR through one batch
      step; confirm `doRevise` reads real `--log-failed` output, amends, re-pushes, and
      the head commit carries the incremented `CI-Revise-Attempt` trailer
- [ ] Confirm a subsequent feedback-only / on-green amend overwrites the trailer to `0`
**Context cost:** L
**Depends on:** Slice 3

## Slice 5: Docs

**Goal:** The PR-gated lifecycle docs describe CI-gated revision (red frontier →
`revise`, pending → `wait`, the configurable cap-then-`wait`, the
`CI-Revise-Attempt` consecutive-red counter and its two resets).
**Files touched:**

- ⚠️ `CLAUDE.md` — extend the Lifecycle section with the CI-gated revise trigger
- ⚠️ `docs/qrspi-pr-gated-lifecycle-design.md` — document the CI signal, the resolver
  precedence slot, the cap, and the counter/reset semantics

**Verification:**
- [ ] Docs accurately describe the shipped behavior from Slices 1–4 (red→revise,
      pending→wait, cap N default 3 from config, consecutive-red counter + dual reset)
- [ ] No stale claims (e.g. "CI is ignored entirely today") remain
**Context cost:** S
**Depends on:** Slice 4

---

## Unverified Assumptions

- **GraphQL `statusCheckRollup` shape.** The design specifies the `commits(last:1)
  {nodes{commit{statusCheckRollup{state} ...}}}` selection and the five-state enum
  (`ERROR, EXPECTED, FAILURE, PENDING, SUCCESS`). The exact `contexts(first:N)`
  fragment fields (`CheckRun.name/conclusion/detailsUrl` vs `StatusContext.context/
  state/targetUrl`) and the value of `N` are not pinned by a concrete schema probe in
  the design — needs confirmation against the live GitHub GraphQL schema during Plan/
  Implement.
- **`gh run view --log-failed` ↔ check identity mapping.** AC5/Slice 4 assume the
  gathered `ciFailingChecks` `detailsUrl`/name can be turned into a `gh run view
  <run-id>` invocation. The design does not specify how a check name/URL maps to a
  run-id for `gh run view`; the worker's exact diagnosis command is unverified.
- **Config nesting choice (`ciReviseCap` vs `ci.reviseCap`).** The design leaves the
  flat-vs-nested key as an either/or. Project memory notes `qrspi_config.py` reads a
  single top-level key only (no dot-path), so a nested `ci.reviseCap` may not be
  readable by the existing reader without extension — the flat `ciReviseCap` is the
  safer default but the choice is not finalized in the design.
- **Graphite stale-approval dismissal on amend re-push (OQ4).** The design asserts
  that amending + `gt submit` re-pushes the branch head so GitHub auto-dismisses a
  stale APPROVED review and re-enters review with green checks. This GitHub/Graphite
  behavior is asserted, not verified against this repo's branch-protection settings.
- **RUS-76 dependency.** The Risk Register notes a `blockedBy RUS-76` entry-gate edge
  on the contract-fixture seam; Slice 3 edits those fixtures and assumes RUS-76 has
  landed a stable harness. If RUS-76 is not yet landed, Slice 3 must wait.
