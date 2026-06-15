# Structure Outline — Critic effectiveness: instrumentation, cost reduction, and teeth eval

**Design basis:** design.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## New Types

- `CriticSummary { stepCount: int, timestampSpan: {start: str|null, end: str|null}, dissentRate: float, dissentRevisedRate: float, terminalActionCounts: {action: count}, perLens: {lensKey: {steps: int, dissentRate: float}}, abortedRecords: int }`
  — the JSON object returned by `summarize(...)` and printed by the summarizer CLI. `lensKey` is the lens string, with `null`-lens rolled under an `"edge"` key (single edge critic) per the `lens:null ⇒ edge` derivation (design §Current State, Q1/Q8).
- (No new persisted store.) The teeth-eval fixtures are data files (a flawed `design.md`, a companion `research.md`), not types.

## Modified Types

- `CriticMetricsLedgerLine` — add field `runId: str` (ref: design.md §Delta, Decision 1 Option B / OQ2). Every appended ledger line gains one explicit run identifier; the per-ticket file path is unchanged. No rename, no new store. Existing fields (`phase`, `rounds[]`, `terminalAction`, `ticketId`, `timestamp`, schema-present-but-unpopulated `tokensIn`/`tokensOut`) are untouched.

## Contracts

- `load_ledger(path: str) -> list[dict]` — read `critic-metrics.jsonl` line by line; on `JSONDecodeError` per line, skip it and increment an aborted-record count; tolerate a trailing partial line. Pure; no aggregation. (design §Delta, Risk Register row 1, Q9)
- `summarize(lines: list[dict], since: str|None = None, ticket: str|None = None, run_id: str|None = None) -> CriticSummary` — pure aggregator. Scopes by exact `run_id` (the clean per-run filter) and/or the `since`/`ticket` window, then computes: `dissentRate` (a round counts as dissent if `pass is False` OR `findingsCount > 0`), `dissentRevisedRate` (**named revise-attempted proxy**: a `pass:false` round followed by a later round in the same step — docstring must state it measures "a revise round was attempted after dissent," NOT "the artifact changed", design §AC-Instrumentation, Q8), `terminalActionCounts`, `perLens`, `stepCount`, and `timestampSpan`. Round is derived from `rounds[]` array position; critic type is derived from `lens` null-ness. (design §Delta, Decision 1)
- `main(argv)` / CLI for `qrspi_critic_summary.py` — accepts `--run-id`, `--since`, `--ticket`, and a ledger path; prints the `CriticSummary` as JSON. Follows the functional-core / imperative-shell idiom (thin CLI over pure functions). (design §Delta)
- **Appender contract change** — the `runId` source is pinned here: the appender (`scripts/qrspi_metrics_append.py`) accepts a `run_id` argument (and the JS call site that builds each `CriticMetricsLedgerLine` in `qrspi-batch.js` passes the orchestrator's per-invocation run id, falling back to a generated id if absent). The exact orchestrator id source vs. generated-uuid choice is finalized in the Plan phase; the contract here is: the field is always present and a string on every appended line. (design §Delta, OQ2)
- **Teeth-eval lens→defect ownership map** (the eval's relevance definition, since the harness has no per-artifact routing, Q10). Each defect embeds a **unique, quotable marker** the owning lens must cite in its `findings` when it catches the defect — this turns "names its defect" into a deterministic substring test against the verdict (`CRITIC_VERDICT_SCHEMA = {pass: bool, findings: string[]}`):
  - `completeness` → a named omitted acceptance criterion (marker e.g. `AC-TEETH-COMPLETENESS`), present in the **`ticket.md`** fixture (the completeness lens anchors on ticket ACs + answered questions — it Reads `TICKET_CONTENT_PATH`/`QUESTIONS_PATH`, so the omitted AC must live in the ticket fixture, not only the design).
  - `internal-consistency` → a named internal contradiction in the flawed design (marker = a specific contradictory token, e.g. two stated values for the same constant).
  - `edge-alignment` → a design claim that contradicts a named fact in the companion `research.md` fixture (marker e.g. a fake symbol `frobnicate_widget()`) — the only lens whose detection depends on research fidelity, i.e. the digest's actual risk surface (design §AC-Teeth-eval review finding #1). The contradicted fact must be one a *correct* digest **retains**, so digest-ON the lens must still catch it; a digest that trimmed it makes edge-alignment pass and the eval **fail** (non-vacuity).
- **Teeth-eval spawning mechanism (pinned — corrects the design's `run_eval.py` reuse).** A lens is a registered `agentType` (`qrspi-design-critic-<lens>`) spawnable **only from a Workflow runner** (qrspi-batch.js:20–24), and it **Reads its inputs as files** (`tools: Read`). `run_eval.py`'s `call_model` is a single-turn, **tool-less** Messages API call (files/tool_calls empty) and therefore **cannot drive a real lens** — it is NOT reusable for this eval, regardless of `--trials`. The runner is therefore a **workflow**, `.claude/workflows/qrspi-teeth-eval.js`, NOT `scripts/qrspi_teeth_eval.py`. It spawns the real lenses exactly as `runCriticPanelLoop` does (4 input paths + threaded `DIGEST_PATH`), builds the digest via the real `scripts/qrspi_research_digest.py` CLI (the `buildResearchDigest` worker pattern, qrspi-batch.js:999–1004), and runs python-via-worker for the digest build and the assertion core (the `synthesizeVerdicts` pattern, qrspi-batch.js:972–986). A `.claude/workflows/*.js` file is inherently off the deterministic CI gate (`run_tests.py` globs `scripts/*_test.py`) and runs only on explicit `Workflow({name:"qrspi-teeth-eval"})` invocation.
- **Teeth-eval assertion contract** — the majority/marker decision is a **pure, CI-tested core**, `scripts/qrspi_teeth_assert.py`: given per-lens trial verdicts + expected markers + threshold, a trial "catches" iff `pass is False AND marker ∈ some finding`, and a lens passes iff `caught ≥ threshold`. `--trials` default 3, threshold ≥2-of-3 (the workflow runs the trial loop; the *math* lives in the tested core — this is Slice 3's deterministic test contribution, since the agent spawning itself stays off CI). The panel is spawned **digest-ON**. (design §AC-Teeth-eval review #2 issue #4, Decision 3 Option A)

## Slice 1: Instrumentation — runId field + critic summarizer

**Goal:** From a `critic-metrics.jsonl` ledger (whose lines now carry an explicit `runId`), produce a base-rate report (`dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens`, `stepCount`, `timestampSpan`) scopable to exactly one run via `--run-id`. End-to-end path: ledger lines → `load_ledger` → `summarize` → CLI JSON output. This is the one deliverable that gates Ticket B, so the `runId` field and the summarizer that consumes it are mutually dependent and verified together.
**Files touched:**

- ✨ `scripts/qrspi_critic_summary.py` — pure `load_ledger` + `summarize` + CLI (the summarizer).
- ✨ `scripts/qrspi_critic_summary_test.py` — in-memory ledger-line fixtures (mirroring `qrspi_metrics_append_test.py:SAMPLE_RECORD`, now including `runId`): dissent-via-fail, dissent-via-non-empty-findings, `dissentRevisedRate` (pass:false-then-later-round) inference, trailing-partial-line tolerance, aborted-record counting, `--run-id` exact scoping, `--since`/`--ticket` scoping, `timestampSpan` reporting.
- ⚠️ `scripts/qrspi_metrics_append.py` — add `run_id` parameter; stamp every appended `CriticMetricsLedgerLine` with `runId` (one additive field, no rename, no new store, no critic-loop control-flow edit).
- ⚠️ `scripts/qrspi_metrics_append_test.py` — add a case asserting the `runId` field is present and round-trips through the appender.
- ⚠️ `.claude/workflows/qrspi-batch.js` — the JS call site that builds each ledger line passes a `runId` (orchestrator per-invocation id, fallback generated). This is the single place instrumentation reaches into existing JS; it touches the append call site, NOT the critic-loop control flow (design §Slicing-premise note).

**Verification:**

- [ ] `python3 scripts/run_tests.py critic_summary` passes (new summarizer tests, including `--run-id` exact scoping and partial-line tolerance).
- [ ] `python3 scripts/run_tests.py metrics_append` passes (new `runId` presence/round-trip case).
- [ ] `python3 scripts/run_tests.py` stays fully green (no regression; AC-No-regression).
- [ ] Manual: run `qrspi_critic_summary.py --run-id <id>` against a sample ledger and confirm the JSON carries `stepCount`, `timestampSpan`, `dissentRate`, `dissentRevisedRate`, `terminalActionCounts`, `perLens`.

**Context cost:** M
**Depends on:** none

## Slice 2: Cost-reduction — document the existing digest lever

**Goal:** An operator can discover and opt into the already-shipped (RUS-77 `c6fa275`) digest cost lever via the example config, with no code or default-behavior change. The structural cost claim (`len(digest) < len(research)`) and config-resolution are **already** covered by shipped RUS-77 tests (`qrspi_research_digest_test.py:test_digest_strictly_shorter`, `qrspi_critics_config_test.py:test_digest_default_off`/`_enabled_true_parses`) — those are **cited, not re-created** (design §Delta "NOT re-created", Decision 2). The literal token dimension is substantiated by an optional run-level external-token A/B documented here.
**Files touched:**

- ⚠️ `.qrspi/config.example.json` — add a commented/example `critics.design.digest.enabled: true` entry documenting how to opt into the existing lever. **No default flip** (default stays OFF; preserves RUS-77 posture, design OQ1 / Decision 2 A′ rejected).
- ✨ (runbook, exact home decided in Plan) a documented manual procedure for the run-level digest-OFF vs digest-ON external-token A/B (the literal "measurably fewer tokens" measurement, externally observed like the ~749K figure). Structure phase note: this is a documented runbook step, not a deterministic test; the Plan phase decides whether it is a markdown runbook section or a thin script. (design §Delta "New (optional, manual) run-level token A/B", OQ4)

**Verification:**

- [ ] `python3 scripts/run_tests.py` stays green — confirms the already-shipped digest-size proxy + config-resolution tests still pass and nothing in this slice broke them (the structural cost claim is cited via these existing tests).
- [ ] Manual: parse `.qrspi/config.example.json` (valid JSON) and confirm the digest-enable example is present and discoverable.
- [ ] Manual (opt-in): the documented external-token A/B runbook is followed once if a reviewer wants the literal token figure; not part of CI.

**Context cost:** S
**Depends on:** none

## Slice 3: Teeth eval — flawed-design fixture + opt-in panel runner

**Goal:** An on-demand, opt-in check feeds the real design panel a single flawed `design.md` fixture (carrying three labelled defects) plus a companion `research.md` fixture, runs the panel **digest-ON** over multiple trials, and asserts each owning lens returns `pass=false` naming its defect by a majority threshold — proving the cost-reduced panel still has teeth, non-vacuously (the edge-alignment/research defect gates the digest's actual risk). Lives off the deterministic CI gate (agent-spawning, non-deterministic).
**Files touched:**

- ✨ `evals/teeth/design.md` — single flawed design fixture with three labelled defects, each carrying its unique marker: a named omitted AC (→ completeness), a named internal contradiction (→ internal-consistency), and a claim contradicting a named research fact (→ edge-alignment). Single combined fixture per OQ3 (reviewer: "single design").
- ✨ `evals/teeth/research.md` — companion research fixture that explicitly documents the fact the flawed design contradicts (anchors the edge-alignment defect); the fact must survive a correct digest.
- ✨ `evals/teeth/ticket.md` — **new** ticket fixture carrying the acceptance criterion the design omits (the completeness lens anchors on ticket ACs; without this the omitted-AC defect is undetectable).
- ✨ `evals/teeth/questions.md` — **new** minimal answered-questions fixture (the completeness lens Reads `QUESTIONS_PATH`; must exist).
- ✨ `scripts/qrspi_teeth_assert.py` — pure majority/marker decision core (`evaluate(trial_verdicts, markers, threshold) -> per-lens {caught, total, pass}`). Deterministic, no agents — runs in `run_tests.py`/CI.
- ✨ `scripts/qrspi_teeth_assert_test.py` — stdlib `unittest` over synthetic verdicts (catch-via-marker, majority threshold, no-catch). Auto-discovered by `run_tests.py` (Slice 3's CI test contribution).
- ✨ `.claude/workflows/qrspi-teeth-eval.js` — the opt-in workflow runner (REPLACES the design's `scripts/qrspi_teeth_eval.py`, which is infeasible — see the spawning-mechanism contract). Builds the digest via the real `qrspi_research_digest.py` CLI (digest-ON), fans out the real `qrspi-design-critic-<lens>` agentTypes × `--trials` against the fixtures, then calls `qrspi_teeth_assert.py` via a worker and `return`s a `{digestOn, trials, perLens, overallPass}` report. First real consumer of the `evals/` seam (design Decision 3 NEW PATTERN). Inherently off CI; runs only on explicit `Workflow(...)` invocation.

**Verification:**

- [ ] `python3 scripts/run_tests.py teeth_assert` passes (the pure majority/marker core — deterministic, in CI).
- [ ] Manual (opt-in): `Workflow({name:"qrspi-teeth-eval", args:{trials:3}})`; confirm the report shows completeness, internal-consistency, and edge-alignment each `pass=false` naming their respective defect in ≥2-of-3 trials, with the digest lever ON.
- [ ] Manual: confirm the workflow is NOT picked up by `python3 scripts/run_tests.py --list` (it must stay off the deterministic CI gate; AC-Teeth-eval, Q11).
- [ ] Inspection: the edge-alignment marker references a fact present in `evals/teeth/research.md` that a correct digest retains, so a digest that trims it makes edge-alignment pass and the eval fail (the non-vacuity / digest-risk-gating check, review finding #1).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **`runId` source in the orchestrator.** The design defers the exact `runId` source (orchestrator per-invocation id vs. generated uuid) to the structure/plan phase. No concrete orchestrator field is cited that already holds a per-run id, so whether `qrspi-batch.js` exposes a stable per-run identifier at the ledger-append call site is unverified (constraint: no codebase exploration). The Plan phase must confirm this against the actual call site; if none exists, the fallback is a generated id at first append.
- **Exact ledger append call site in `qrspi-batch.js`.** The design asserts the JS builds each `CriticMetricsLedgerLine` and that a `runId` can be threaded there without touching critic-loop control flow. The precise location/shape of that call site is not pinned in the design and is not verifiable here.
- **`run_eval.py --trials` reuse for the teeth eval — RESOLVED: not reusable.** `run_eval.py`'s `--trials` IS a working loop (`for trial in range(config.trials)`, `run_eval.py:242`), but its execution seam `call_model` (`run_eval.py:100–148`) is a single-turn, **tool-less** Anthropic Messages API call (files/tool_calls empty), so it **cannot drive a real design-critic lens**, which must Read its fixture inputs from disk. The teeth runner therefore does NOT call into `run_eval.py`; the trial loop lives in the workflow runner and the majority/marker math lives in the pure `qrspi_teeth_assert.py` core.
- **`perLens` exact key shape / null-lens rollup.** The design specifies type-from-lens-null derivation but not the precise `perLens` key set or how the single edge critic (`lens:null`) is labelled in output. Proposed here as an `"edge"` key, but this is a structure-phase proposal, not a design-cited contract.
- **Teeth-eval fixture/runner location — RESOLVED.** Fixtures live under `evals/teeth/` (`design.md`, `research.md`, `ticket.md`, `questions.md`); the runner is the workflow `.claude/workflows/qrspi-teeth-eval.js` (a `scripts/qrspi_teeth_eval.py` is infeasible — `agent()` is a Workflow-runner-only primitive), with the testable decision extracted to the pure `scripts/qrspi_teeth_assert.py` (+ `_test.py`).
- **OQ1 (AC-intent gap) is reviewer-pending, not closed.** The design resolves OQ1 to "no global flip" but explicitly flags that whether documenting a default-OFF opt-in satisfies the cost-AC *intent* is the reviewer's explicit call. If the reviewer rules the intent requires the rejected Option A′ (global default flip), Slice 2's scope changes materially. Treated here as the stated resolution, but flagged as the one open acceptance decision.
