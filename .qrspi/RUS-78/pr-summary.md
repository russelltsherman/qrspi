# PR: RUS-78 Critic effectiveness: instrumentation, cost-reduction, teeth eval

**Ticket:** RUS-78
**Design:** design.md @ 2026-06-15T00:00:00Z
**Structure:** structure.md @ 2026-06-15T00:00:00Z

## Summary

Makes the QRSPI critic layer measurable, opt-in cheaper, and self-testing across three
independent slices. Slice 1 stamps a required `runId` on every appended
`CriticMetricsLedgerLine` and adds a pure summarizer (`qrspi_critic_summary.py`) that
harvests the existing per-ticket ledger into a base-rate report (dissent rate, a named
revise-attempted proxy, terminal-action distribution, per-lens stats) scopable to exactly
one run via `--run-id` — the number Ticket B will calibrate against. Slice 2 is config/docs
only: it documents how to opt into the already-shipped RUS-77 digest cost lever (no default
flip) and adds a manual digest-OFF/ON token A/B runbook, citing rather than re-creating the
shipped RUS-77 tests. Slice 3 adds an on-demand, off-CI teeth eval — flawed-design fixtures
with three lens-owned defect markers, a pure CI-tested majority/marker decision core, and a
workflow runner that spawns the real panel digest-ON over trials. Reviewer focus: (1) the
`runId` change to the tested append seam and its single JS call-site edit (does it avoid the
critic-loop control flow?); (2) the non-vacuity of the teeth eval's edge-alignment assertion
(the only lens whose detection depends on the trimmed research); and (3) OQ1 — whether a
documented default-OFF opt-in satisfies the cost-AC intent.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC-Instrumentation: per-run capture of {lens/type, phase, ticket, round, pass/fail, findings-count} + dissent-rate + dissent→change proxy, scopable to one run | `scripts/qrspi_critic_summary.py:load_ledger/summarize/main`; `scripts/qrspi_metrics_append.py:wrap_envelope` (adds `runId`); `.claude/workflows/qrspi-batch.js:recordCriticMetrics` (threads `runId`) | `scripts/qrspi_critic_summary_test.py` (dissent-via-fail/findings, `dissentRevisedRate`, partial-line/aborted-record, `--run-id`/`--since`/`--ticket` scoping, `timestampSpan`); `scripts/qrspi_metrics_append_test.py` (`runId` presence + round-trip) |
| AC-Cost-reduction: design panel consumes fewer tokens, configurable via `critics` block | `.qrspi/config.example.json` (`critics.design.digest.$comment_optin` opt-in doc, default stays OFF); `docs/critic-cost-ab.md` (manual external-token A/B runbook) | Cited (not re-created): `scripts/qrspi_research_digest_test.py:test_digest_strictly_shorter`; `scripts/qrspi_critics_config_test.py:test_digest_default_off`/`test_digest_enabled_true_parses` (RUS-77 `c6fa275`) |
| AC-Teeth-eval: on-demand check feeds a flawed design, asserts each relevant lens returns pass=false naming its defect, digest-ON | `evals/teeth/{design,research,ticket,questions}.md` (3 lens-owned markers); `scripts/qrspi_teeth_assert.py:evaluate` (pure majority/marker core); `.claude/workflows/qrspi-teeth-eval.js` (opt-in runner, spawns real panel digest-ON × trials) | `scripts/qrspi_teeth_assert_test.py` (catch-via-marker, majority threshold, no-catch) — pure core in CI; agent-spawning runner is off-CI manual |
| AC-No-regression: `run_tests.py` and CI stay green | All-additive Python + one additive ledger field; no edits to existing tested module contracts | `python3 scripts/run_tests.py` → 39 passed, 0 failed (was 38; +`qrspi_teeth_assert_test.py`) |

## Changes by Slice

### Slice 1: Instrumentation — runId field + critic summarizer

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critic_summary.py` | ✨ new | +209 |
| `scripts/qrspi_critic_summary_test.py` | ✨ new | +224 |
| `scripts/qrspi_metrics_append.py` | ⚠️ modified | +13, -3 |
| `scripts/qrspi_metrics_append_test.py` | ⚠️ modified | +~40, -~6 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +13, -1 |

### Slice 2: Cost-reduction — document the existing digest lever

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/config.example.json` | ⚠️ modified | +1 |
| `docs/critic-cost-ab.md` | ✨ new | +87 |

### Slice 3: Teeth eval — flawed-design fixtures + pure core + opt-in runner

| File | Change | Lines |
|------|--------|-------|
| `evals/teeth/design.md` | ✨ new | +78 |
| `evals/teeth/research.md` | ✨ new | +47 |
| `evals/teeth/ticket.md` | ✨ new | +29 |
| `evals/teeth/questions.md` | ✨ new | +23 |
| `scripts/qrspi_teeth_assert.py` | ✨ new | +173 |
| `scripts/qrspi_teeth_assert_test.py` | ✨ new | +178 |
| `.claude/workflows/qrspi-teeth-eval.js` | ✨ new | +185 |

### QRSPI workflow artifacts (not feature code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-78/{questions,research,design,structure,plan,worktree,impl-log}.md` | ✨ phase artifacts | +1551 |
| `.qrspi/RUS-78/critic-metrics.jsonl` | ✨ ledger samples | +2 |

## Testing Summary

- [x] Slice 1: summarizer unit tests — `python3 scripts/run_tests.py critic_summary` — 1 file passed
- [x] Slice 1: appender `runId` round-trip — `python3 scripts/run_tests.py metrics_append` — 1 file passed
- [x] Slice 1: manual — `python3 scripts/qrspi_critic_summary.py --run-id run-A <ledger>` printed JSON with `stepCount`, `timestampSpan`, `dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens`, `abortedRecords`; `--run-id` correctly excluded the other run's lines
- [x] Slice 2: regression — `python3 scripts/run_tests.py` — 38 passed, 0 failed (confirms cited RUS-77 digest + config tests still green)
- [x] Slice 2: manual — `.qrspi/config.example.json` parses; `digest.enabled` still `false`; `$comment_optin` present/discoverable; `docs/critic-cost-ab.md` non-empty
- [x] Slice 3: pure decision core — `python3 scripts/run_tests.py teeth_assert` — 1 file passed
- [x] Slice 3: full suite — `python3 scripts/run_tests.py` — 39 passed, 0 failed (+1 new, no regression)
- [x] Slice 3: workflow compile — `node scripts/check_workflows.js .claude/workflows/*.js` — 2 ok, 0 failed
- [x] Slice 3: off-CI guard — `python3 scripts/run_tests.py --list | grep -i teeth` lists only `qrspi_teeth_assert_test.py`; no `.js` runner on the deterministic gate
- [x] Slice 3: non-vacuity inspection — built the digest from `evals/teeth/research.md`; the `frobnicate_widget()` "synchronous and idempotent" fact survives the digest (prose, not a fenced block), so edge-alignment still catches defect #3 digest-ON
- [ ] Slice 3: manual opt-in end-to-end — `Workflow({name:"qrspi-teeth-eval", args:{trials:3}})` — NOT run (agent-spawning, off-CI, non-deterministic); deterministic decision math fully covered by `qrspi_teeth_assert_test.py`

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `config.example.json` opt-in (Slice 2) | "add a commented/example `critics.design.digest.enabled: true` entry" | Added a `$comment_optin` sibling **inside** the existing `digest` block; left live `enabled: false` | The file already shipped a `digest` block mirroring the runtime default; setting the live value to `true` would flip the default-mirror, violating the hard "No default flip" constraint. The `$comment_*` doc-key fallback (plan step 23) keeps valid JSON and preserves OFF. Discoverability + no-flip both hold |
| `runId` source (Slice 1) | structure/plan pins the source; "always present and a string on every appended line" | `process.env.QRSPI_RUN_ID` → `crypto.randomUUID()` → `run-<ts>-<rand>` fallback (webcrypto-absent sandbox) | Implemented with the project's defensive `typeof`-guard style; the timestamp+random fallback preserves the "always a string" contract without changing env-var-first / generated-id semantics |
| `qrspi_metrics_append.py --run-id` (Slice 1) | add `run_id` parameter | Made `--run-id` a **required** CLI argument (no default) | Stronger enforcement of the "always present" contract; the sole call site (`qrspi-batch.js recordCriticMetrics`) was updated to thread the module-level `runId` |
| Teeth runner location (Slice 3) | worktree.md Session-3 table named `scripts/qrspi_teeth_eval.py` | `.claude/workflows/qrspi-teeth-eval.js` + pure `scripts/qrspi_teeth_assert.py` | Followed the AUTHORITATIVE corrected layout in structure §Contracts / plan §Plan-phase pins; `agent()` is a Workflow-runner-only primitive, so a `scripts/*.py` runner is infeasible. The stale worktree table was explicitly superseded |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Summarizer breaks on a trailing partial ledger line | Mitigated — `load_ledger` parses line-by-line, skips `JSONDecodeError`, counts aborted records; covered by a corrupt-trailing-line test | Revert `qrspi_critic_summary.py` (pure, no callers but the new CLI) |
| Digest-ON panel drops enough context that a lens misses a real defect | Mitigated (non-vacuous) — teeth eval's edge-alignment assertion fails iff the digest trims the research fact behind defect #3; inspection confirmed the fact survives a correct digest | Disable the digest lever (default already OFF); tune the digest, not the prompts (calibration is Ticket B) |
| Run-scoping cannot separate two close runs of the same ticket | Resolved — explicit `runId` per line + `--run-id` exact filter; `--since`/`--ticket` retained as secondary window | Revert the `runId` field (Slice 1); summarizer falls back to the `--since`/`--ticket` window |
| Adding `runId` touches the tested append seam | Accepted (low) — additive field, no rename/new-store, no critic-loop control-flow edit; appender test gains presence/round-trip case | Revert `qrspi_metrics_append.py` + the single `qrspi-batch.js` call-site line |
| Literal per-critic token count not measurable in-harness (`tokensIn/Out` never populated) | Accepted — deterministic byte-size proxy (shipped RUS-77 test) + optional external-token A/B runbook (`docs/critic-cost-ab.md`); per-critic attribution deferred to a future telemetry ticket | N/A (documentation only) |
| Teeth eval is itself flaky (real LLM agents miss a defect on a single run) | Mitigated — multi-trial majority threshold (default 3, ≥2-of-3) in `qrspi_teeth_assert.py:evaluate`, with fail-closed catch rule and guarded non-positive-threshold fallback; kept off CI | Do not run the opt-in eval; the deterministic core test stays in CI regardless |
| Cost slice's "new" deliverables duplicate already-shipped RUS-77 work | Closed — verified the digest builder + byte-proxy test + config-resolution test landed in RUS-77 `c6fa275`; they are cited, not re-created; only new code artifact is the `config.example.json` doc line | N/A |

## Open Items

- **OQ1 (reviewer decision):** With the digest lever default-OFF, the out-of-the-box panel is cheaper for nobody — "cost reduction" as scoped is "document a pre-existing opt-in." If the cost-AC *intent* requires the default run to be cheaper, that needs the rejected Option A′ (global default flip) and is a separate decision. Reviewer must ratify whether documented-but-default-OFF satisfies the AC.
- **OQ4 (reviewer ratification):** Which is "the cost AC's verifiable form" — the already-shipped byte-size proxy alone, or the byte proxy + the optional run-level external-token A/B (`docs/critic-cost-ab.md`).
- **Deferred — literal dissent→artifact-change metric:** the summarizer reports `dissentRevisedRate`, a named revise-*attempted* proxy (an LLM reviser can no-op and still trigger a later round). Capturing the literal artifact-changed edge needs a new ledger event — Ticket B's to add if it needs the exact figure.
- **Deferred — per-critic token attribution:** blocked on the harness exposing per-subagent usage (`tokensIn`/`tokensOut` schema-present but unpopulated). Future telemetry ticket.
- **Not run — teeth eval end-to-end:** the opt-in `Workflow({name:"qrspi-teeth-eval"})` agent-spawning run has not been executed (off-CI, non-deterministic); only its deterministic decision core is CI-covered.
- **Lens→marker map maintenance:** the ownership map lives in two places kept in sync (the workflow's `LENS_MARKERS` and the test's `MARKERS`); changing a fixture marker requires updating both the fixture text and the map.
- **Stale worktree.md:** the worktree.md Session-3 table still names the old `scripts/qrspi_teeth_eval.py` layout; the authoritative layout is structure.md/plan.md. Follow-up cleanup of the stale task descriptions.
