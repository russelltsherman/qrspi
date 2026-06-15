# PR: RUS-81 CI-gated revision — resolver revises red frontier PRs

**Ticket:** RUS-81
**Design:** design.md @ 2026-06-15T00:00:00Z
**Structure:** structure.md @ 2026-06-15T00:00:00Z

## Summary

Adds CI check state as a third PR-gated advancement signal alongside review approval and
reviewer feedback. The gather (`qrspi_pr_state.py`) now selects each PR head-commit's
`statusCheckRollup` and normalizes it to `green | red | pending | none`; the pure resolver
(`qrspi_resolve_state.py`) gains a CI-gated branch — slotted after the unified-feedback handler
and before the active-phase block — that returns `revise` (with a new `ciFailing` flag) on a red
frontier, `wait` on pending, and is a no-op for green/none. A configurable consecutive-red cap
(`ciReviseCap`, default 3) bounds retries via a `CI-Revise-Attempt` head-commit trailer with two
explicit resets, and `doRevise` learns a CI sub-behavior that reads REAL failing-check output
before fixing all red slices in one pass. Reviewer focus areas: (1) the resolver precedence slot
and the consecutive-red counter's dual-reset correctness (read-side gather reset + writer-side
amend reset), and (2) the byte-pinned contract-seam fixture lockstep in Slice 3. Note: Slice 4's
`doRevise` change is in the harness-coupled `qrspi-batch.js` and has NO automated coverage — its
manual end-to-end (a live ticket with a known-red frontier PR) is the outstanding pre-land gate.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: red frontier → `revise` even with no CR/comments (`ciFailing=true`) | `scripts/qrspi_resolve_state.py` CI branch 2c + `ci_state()` | `scripts/qrspi_resolve_state_test.py` (red-under-cap cases) |
| AC2: pending frontier → `wait` | `scripts/qrspi_resolve_state.py` CI branch 2c (pending) | `scripts/qrspi_resolve_state_test.py` (pending cases) |
| AC3: SUCCESS/no-checks/null behaves as today (no-op) | `scripts/qrspi_pr_state.py:check_rollup_state` (green/none) | `scripts/qrspi_pr_state_test.py` (rollup-state + null cases) |
| AC4: rule applies to all frontier phases; impl via any-slice aggregation; red open slice fixed before advance | `scripts/qrspi_resolve_state.py:ci_state` (`max`/any aggregation), branch slotted before completeness gate | `scripts/qrspi_resolve_state_test.py` (incomplete-implementation case) |
| AC5: worker diagnoses real failing checks, fixes, amends, re-pushes; feedback+CI in one pass | `.claude/workflows/qrspi-batch.js:doRevise` (CI branch, `checksBlock`) | Manual e2e (Slice 4, harness-coupled — see Open Items); `scripts/run_tests.py` regression gate |
| AC6: consecutive-red cap-then-`wait`; configurable default 3; counter dual-reset | `qrspi_resolve_state.py` (cap compare), `qrspi_resolve.py:load_ci_revise_cap`/`coerce_cap`, gather read-side reset, `doRevise` writer-side reset | `scripts/qrspi_resolve_state_test.py` (at/above-cap), `scripts/qrspi_resolve_test.py` (cap config), `scripts/qrspi_pr_state_test.py` (not-red→0 reset) |
| AC7: pure + unit-tested; action vocab unchanged; byte-pinned fixtures in sync | `qrspi_resolve_state.py`/`qrspi_pr_state.py`/`qrspi_resolve.py` (no `RESOLVE_ACTIONS` change), fixtures | `scripts/qrspi_contract_fixtures_producer_test.py`, `scripts/qrspi_contract_fixtures_consumer_test.py` |

## Changes by Slice

### Slice 1: Gather — CI rollup query, normalizers, additive per-PR fields

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_pr_state.py` | ⚠️ modified | +111, -1 |
| `scripts/qrspi_pr_state_test.py` | ⚠️ modified | +107, -6 |

### Slice 2: Resolver — CI-gated `revise`/`wait` branch with cap

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve_state.py` | ⚠️ modified | +82, -2 |
| `scripts/qrspi_resolve_state_test.py` | ⚠️ modified | +161, -8 |

### Slice 3: Orchestrator wiring — config cap, envelope re-emit, contract fixtures

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_resolve.py` | ⚠️ modified | +80, -3 |
| `.qrspi/config.example.json` | ⚠️ modified | +2, -0 |
| `scripts/fixtures/contract_seam/resolve/wellformed.json` | ⚠️ modified | +3, -0 |
| `scripts/fixtures/contract_seam/resolve/prose_wrapped.json` | ⚠️ modified | +1, -1 |
| `scripts/qrspi_contract_fixtures_producer_test.py` | ⚠️ modified | +8, -3 |
| `scripts/qrspi_contract_fixtures_consumer_test.py` | ⚠️ modified | +4, -0 |
| `scripts/qrspi_resolve_test.py` | ✨ new | +93 |

### Slice 4: Worker — `doRevise` CI-failure path + durable trailer write

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +110, -27 |

### Slice 5: Docs — CI-gated revise behavior

| File | Change | Lines |
|------|--------|-------|
| `.claude/CLAUDE.md` | ⚠️ modified | +23, -2 |
| `docs/qrspi-pr-gated-lifecycle-design.md` | ⚠️ modified | +54, -0 |

### Workflow artifacts (not feature code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-81/design.md` | ✨ new | +102 |
| `.qrspi/RUS-81/structure.md` | ✨ new | +229 |
| `.qrspi/RUS-81/plan.md` | ✨ new | +165 |
| `.qrspi/RUS-81/questions.md` | ✨ new | +53 |
| `.qrspi/RUS-81/research.md` | ✨ new | +315 |
| `.qrspi/RUS-81/worktree.md` | ✨ new | +97 |
| `.qrspi/RUS-81/impl-log.md` | ✨ new | +149 |
| `.qrspi/RUS-81/critic-metrics.jsonl` | ✨ new | +5 |

## Testing Summary

- [x] Slice 1: gather unit tests — `python3 scripts/run_tests.py pr_state` — 1 file passed (normalizer, trailer-parser, not-red→0 reset cases)
- [x] Slice 2: resolver unit tests — `python3 scripts/run_tests.py resolve_state` — 1 file passed (60 cases; +19 new CI cases)
- [x] Slice 3: full suite incl. byte-pinned contract fixtures — `python3 scripts/run_tests.py` — 37 files passed, 0 failed; `python3 scripts/qrspi_resolve_test.py` — 119 cases passed
- [x] Slice 4: syntax + regression gate — `node --check .claude/workflows/qrspi-batch.js` (OK) + `python3 scripts/run_tests.py` — 37 passed, 0 failed
- [x] Slice 5: docs-only regression gate — `python3 scripts/run_tests.py` — 37 passed, 0 failed
- [ ] Manual verification (OUTSTANDING): drive a live ticket with a known-red frontier PR through one batch step; confirm `doRevise` reads real `--log-failed` output, amends, re-pushes, and the head commit carries the incremented `CI-Revise-Attempt` trailer; confirm a subsequent feedback-only/on-green amend overwrites the trailer to `0`

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `resolve(state, ..., ci_revise_cap)` | explicit `ci_revise_cap` argument | `resolve(state, ci_revise_cap=3)` with default 3 | Default does not read disk and does not break purity; keeps the untouched `qrspi_resolve.py` call site and `qrspi_resolve_test.py` valid mid-feature. Slice 3 makes the caller pass the explicit config-resolved cap. |
| Envelope re-emit helper "mirroring `comment_targets_of`" | one helper | two helpers: `ci_failing_of(decision)` + `ci_failing_checks_of(decision, phases)` | The fixed-key `decision` dict carries `ciFailing` but cannot carry `ciFailingChecks` (failing-check entries live on the per-PR/phase shape, not the decision), so the list is re-aggregated from `phases`. Added optional `phases=None` to `build_envelope`; default keeps old callers byte-for-byte unaffected. |
| `ci_state(phases, name)` only | named contract helper | added internal `ci_revise_attempt_of(phases, name)` | Needed to read the gathered per-phase attempt count for the cap compare; pure and unit-covered. |
| Config key `ciReviseCap` / nested `ci.reviseCap` | either/or | flat `ciReviseCap` only | `qrspi_config.py`'s reader handles a single top-level key (no dot-path) per project memory; flat key resolved via `read_config` + pure `coerce_cap` (rejects bool). |
| `doRevise` trailer write within the `qrspi_revise_amend.py` amend | trailer manipulation rides on the content amend | trailer written by a SEPARATE message-only `gt modify -m` after the content amend; plus a best-effort `resetCiReviseTrailer` on the comment-only APPLY path | `qrspi_revise_amend.py` preserves the commit message verbatim and cannot write the trailer, so a distinct message-only amend is required. The extra comment-only-apply reset is durability/observability hygiene; cap correctness is already guaranteed by the gather read-side reset. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Normalizer misclassifies PENDING as FAILURE (or vice-versa) | mitigated — pure `check_rollup_state` with explicit enum mapping incl. null/absent→none, EXPECTED→pending; table-driven over five states + null | Revert Slice 1 commit (`b513d4b`); fields are additive/inert to consumers |
| CI branch slotted at wrong precedence masks reset/feedback | mitigated — branch 2c slotted strictly after 2b, before active-phase; resolver cases assert non-frontier CR still resets and frontier CR+CI handled in one pass | Revert Slice 2 commit (`5da7c72`); resolver returns to pre-CI behavior |
| Attempt counter falsely inflates a fresh red episode with a stale count | mitigated — two explicit resets: gather read-side (not-red→0) and `doRevise` writer-side (non-CI amend → 0); both unit-/path-covered | Revert Slices 1+4; resolver no longer compares any attempt count |
| Shared-file overlap with RUS-76 on the JS↔Python contract-fixture seam | accepted — `blockedBy RUS-76` entry-gate edge; fixtures edited as a single synchronized producer+consumer+fixture change | Revert Slice 3 commit (`2abfd3d`) to restore prior byte-pinned envelope |
| Envelope byte-pin breaks if top-level CI re-emit added without updating pinned fixtures | mitigated — synchronized 3-file (+ producer/consumer) lockstep edit; full suite + 119-case resolve test green | Revert Slice 3 commit (`2abfd3d`) |
| Worker fabricates a CI fix without reading real check output (honesty-bound) | mitigated by design, UNVERIFIED at runtime — `doRevise` prompt mandates reading real `gh pr checks`/`gh run view --log-failed` output before any fix; not exercised by automated tests (harness-coupled JS) | Revert Slice 4 commit (`f892702`); `doRevise` returns to feedback-only behavior |

## Open Items

- **Manual end-to-end gate (blocking land):** Slice 4's `doRevise` CI path in `.claude/workflows/qrspi-batch.js` is harness-coupled and has NO automated coverage per project convention. It must be exercised against a live ticket with a known-red frontier PR before landing — confirming real `--log-failed` read, amend, re-push, the incremented `CI-Revise-Attempt: <prior+1>` trailer, and the on-green/feedback-only overwrite to `0`. Not yet run (no live red-CI ticket available in-session).
- **Unverified GraphQL `statusCheckRollup` shape:** the `statusCheckRollup{state contexts(first:100){...}}` fragment (N=100) was implemented as planned but NOT verified against the live GitHub GraphQL schema — the parsers are pure/unit-tested and the query string is only exercised by the (non-unit-tested) subprocess path. The manual e2e is the first point this query shape hits the live API.
- **Unverified check-name → run-id mapping for `gh run view`:** the worker's exact diagnosis command turning a gathered `detailsUrl`/check name into a `gh run view <run-id> --log-failed` invocation is asserted in the prompt, not verified; first validated by the manual e2e.
- **Unverified Graphite stale-approval dismissal on amend re-push (OQ4):** the design's assertion that amend + `gt submit` re-pushes the branch head so GitHub auto-dismisses a stale APPROVED review depends on this repo's branch-protection settings; not verified here.
- **Design-doc §4 resolve-loop pseudocode not rewritten:** the new CI gate is documented declaratively in §5 (Predicates); the older §4 pseudocode predates even the RUS-54 unified-feedback handler and was left out of scope.
