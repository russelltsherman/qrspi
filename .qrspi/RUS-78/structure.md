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
- **Teeth-eval lens→defect ownership map** (the eval's relevance definition, since the harness has no per-artifact routing, Q10):
  - `completeness` → a named omitted acceptance criterion in the flawed fixture.
  - `internal-consistency` → a named internal contradiction in the flawed fixture.
  - `edge-alignment` → a design claim that contradicts a named fact in the companion `research.md` fixture (the only lens whose detection depends on research fidelity — the digest's actual risk surface, design §AC-Teeth-eval review finding #1).
- **Teeth-eval assertion contract** — for each lens, run its assertion over multiple trials (reuse `run_eval.py`'s `--trials`, default 3) and pass iff the lens returns `pass=false` naming its defect in a **majority** (≥2-of-3) of trials; the panel is spawned **digest-ON**. Exact trial count/threshold is pinned in the Plan phase. (design §AC-Teeth-eval review #2 issue #4, Decision 3 Option A, `run_eval.py:38,308`)

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

- ✨ `evals/<teeth>/design.md` (exact path pinned in Plan) — single flawed design fixture with three labelled defects: a named omitted AC (→ completeness), a named internal contradiction (→ internal-consistency), and a claim contradicting a named research fact (→ edge-alignment). Single combined fixture per OQ3 (reviewer: "single design").
- ✨ `evals/<teeth>/research.md` — companion research fixture that explicitly documents the fact the flawed design contradicts (anchors the edge-alignment defect).
- ✨ `scripts/qrspi_teeth_eval.py` (or an `evals/` runner entry; exact form pinned in Plan) — spawns the panel digest-ON, runs each lens/defect assertion over `--trials` (default 3) with a majority (≥2-of-3) threshold, asserts each owning lens returns `pass=false` naming its defect. First real consumer of the `evals/` placeholder seam (design Decision 3 NEW PATTERN). Wired manual/opt-in, NOT into `run_tests.py`/CI.

**Verification:**

- [ ] Manual (opt-in): invoke the runner; confirm completeness, internal-consistency, and edge-alignment each return `pass=false` naming their respective defect in ≥2-of-3 trials, with the digest lever ON.
- [ ] Manual: confirm the runner is NOT picked up by `python3 scripts/run_tests.py` (it must stay off the deterministic CI gate; AC-Teeth-eval, Q11).
- [ ] Inspection: the edge-alignment assertion references a fact present in the `research.md` fixture, so a digest that trims that fact makes edge-alignment pass and the eval fail (the non-vacuity / digest-risk-gating check, review finding #1).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **`runId` source in the orchestrator.** The design defers the exact `runId` source (orchestrator per-invocation id vs. generated uuid) to the structure/plan phase. No concrete orchestrator field is cited that already holds a per-run id, so whether `qrspi-batch.js` exposes a stable per-run identifier at the ledger-append call site is unverified (constraint: no codebase exploration). The Plan phase must confirm this against the actual call site; if none exists, the fallback is a generated id at first append.
- **Exact ledger append call site in `qrspi-batch.js`.** The design asserts the JS builds each `CriticMetricsLedgerLine` and that a `runId` can be threaded there without touching critic-loop control flow. The precise location/shape of that call site is not pinned in the design and is not verifiable here.
- **`run_eval.py --trials` reuse for the teeth eval.** The design cites `run_eval.py:38,308` (`trials: int = 3`, `--trials`) but also calls `evals/`/`run_eval.py` a non-functional placeholder. Whether `--trials` is actually wired to a working trial loop the teeth runner can reuse, or whether the runner must implement its own trial/majority loop, is unverified — the Plan phase must resolve this.
- **`perLens` exact key shape / null-lens rollup.** The design specifies type-from-lens-null derivation but not the precise `perLens` key set or how the single edge critic (`lens:null`) is labelled in output. Proposed here as an `"edge"` key, but this is a structure-phase proposal, not a design-cited contract.
- **Teeth-eval fixture/runner location under `evals/`.** Exact directory layout and whether the runner is a `scripts/qrspi_teeth_eval.py` or an `evals/`-native entry is left to the Plan phase (design states "e.g.").
- **OQ1 (AC-intent gap) is reviewer-pending, not closed.** The design resolves OQ1 to "no global flip" but explicitly flags that whether documenting a default-OFF opt-in satisfies the cost-AC *intent* is the reviewer's explicit call. If the reviewer rules the intent requires the rejected Option A′ (global default flip), Slice 2's scope changes materially. Treated here as the stated resolution, but flagged as the one open acceptance decision.
