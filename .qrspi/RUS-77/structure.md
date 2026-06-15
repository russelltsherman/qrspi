# Structure Outline — Critic effectiveness: instrumentation, cost reduction, teeth eval

**Design basis:** design.md @ 2026-06-14T18:00:00Z
**Generated:** 2026-06-14T18:30:00Z
**Status:** draft

> Maps the design's three acceptance criteria to vertical slices:
> AC-INSTR (instrumentation) → Slices 1–2; AC-COST (cost reduction) → Slices 3–4;
> AC-TEETH (teeth eval) → Slice 5. Each slice has a real testability boundary:
> a tested Python core can be verified before the JS wiring that consumes it.

## New Types

> These are JSON-shaped records (this is a CLI/orchestrator codebase; "types" are
> the canonical dict shapes the pure-Python reducers emit/consume, mirroring the
> existing `qrspi_critic_synthesize.py` record shape).

- `CriticRoundRecord { lens: str, pass: bool, findingsCount: int }`
- `CriticStepMetrics { phase: str, rounds: CriticRoundRecord[], terminalAction: str ("converged"|"cap_reached"|"exhausted"|"aborted"), tokensIn?: int, tokensOut?: int }`
  — canonical machine-readable record for one critic step (one edge-critic loop OR one panel loop). `tokensIn`/`tokensOut` are optional/absent in the live path (OQ2 RESOLVED: harness exposes no per-lens token usage). The `terminalAction` enum is the four **actual loop terminations** in `runCriticLoop` (`qrspi-batch.js:710-773`): `converged` (decision.action=='converged', `:743`), `cap_reached` (`:747`), `exhausted` (the defensive `ok:true` tail at `:773`), and `aborted` (any `ok:false` early return — verdict/decision/reviser failure, `:728`/`:739`/`:766`). `revise` is **not** included: it is a mid-loop continuation (`:749`) after which the loop re-critiques, never a terminal state. (Note: `design.md:76` is stale — it names only `converged/cap_reached`; the four-value enum above is the faithful set and supersedes it.)
- `CriticMetricsLedgerLine` — one JSON-line in `.qrspi/<id>/critic-metrics.jsonl`; serialization of a `CriticStepMetrics` plus `{ticketId, timestamp}` envelope fields.
- `DesignDigest` — deterministic extraction/trim of research.md sections written to a digest file path; content shape is a trimmed markdown subset (not a structured record).

## Modified Types

- `DesignCriticConfig` (output of `qrspi_critics_config.resolve_design`) — currently `{enabled, maxRounds, lenses, candidates}`; add nested keys `digest: {enabled: bool}`, `lensModel?: str`, `gateBehindEdge: {enabled: bool}`, all defaulting OFF / absent (ref: design.md §Delta, Decision 3; OQ3 RESOLVED keeps `gateBehindEdge` default OFF).
- `TicketResult` — currently `{ticketId, action, newStatus?, summary, prUrl?}`; add `criticMetrics: CriticStepMetrics[]` folded in `doDesign` alongside existing summary splices (ref: design.md §Delta, Decision 2).
- `DEFAULT_CRITIC_PHASES` (JS mirror in `qrspi-batch.js`) — kept in lockstep with the new `resolve_design` nested defaults (ref: design.md §Delta).

## Contracts

- `qrspi_critic_metrics.build_record(verdicts, terminalAction, usage?) -> CriticStepMetrics` — pure reducer; takes per-lens/per-round verdicts (and optional usage numbers) for one critic step, emits the canonical record. Mirrors `qrspi_critic_synthesize.py` (ref: Decision 1, Option A).
- `qrspi_metrics_append` CLI: `python3 scripts/qrspi_metrics_append.py --ticket <id> --record <json>` (self-locating) — appends one JSON-line to `.qrspi/<id>/critic-metrics.jsonl`, verifying the write (non-empty) like `qrspi_persist.py`. Exit non-zero on failure (fail-closed).
- `qrspi_research_digest` CLI: `python3 scripts/qrspi_research_digest.py --research <path> --out <path>` — deterministic digest generation; writes the digest file. Call site adds a `test -s <digestPath>` non-empty guard before fan-out, failing the phase fail-closed (ref: Q1, Q8).
- `resolve_design(config) -> DesignCriticConfig` (modified) — returns the extended config with the three new nested gates defaulting OFF.
- Lens agent input contract (`.claude/agents/qrspi-design-critic-*.md`): accepts an optional `DIGEST_PATH`; when present the lens Reads it in place of (or in addition to) `RESEARCH_PATH` (ref: Q1, Q8).
- Teeth assertion contract (`scripts/<teeth>_test.py`): given the flawed fixture `evals/fixtures/design_dropped_criterion_broken.md` and its golden, asserts the lens prompt/agent contract would surface the injected dropped-criterion flaw deterministically (ref: Decision 4 Option B).

## Slice 1: Metrics reducer + ledger appender (tested Python core)

**Goal:** A flawed/synthetic set of per-lens verdicts can be reduced to a canonical `CriticStepMetrics` record and appended as one JSON-line to a per-ticket ledger — verifiable end-to-end with `python3` before any JS touches it.
**Files touched:**

- ✨ `scripts/qrspi_critic_metrics.py` — pure reducer `build_record(...)`
- ✨ `scripts/qrspi_critic_metrics_test.py` — unit tests for the reducer (pass/fail mixes, findings counts, optional/absent token fields per OQ2, terminalAction values)
- ✨ `scripts/qrspi_metrics_append.py` — self-locating JSON-line appender with write-verify
- ✨ `scripts/qrspi_metrics_append_test.py` — unit tests for append (creates file, appends, verifies non-empty, fail-closed on bad input)

**Verification:**
- [ ] `python3 scripts/run_tests.py metrics` passes (both new `_test.py` modules)
- [ ] Manual: run the appender with a sample record; confirm a valid JSON-line lands in a temp ledger and a second call appends rather than overwrites
- [ ] Ledger schema preserves BOTH pass/fail tally AND findings count per step (OQ4 RESOLVED — no collapsing into a single rate)

**Context cost:** S
**Depends on:** none

## Slice 2: Wire metrics into the critic loops + result object (JS shell)

**Goal:** A real (critics-enabled) design run emits one ledger line per critic step and folds a `criticMetrics` array into the ticket result — while the critics-DISABLED path stays byte-for-byte unchanged.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — in `runCriticLoop` and `runCriticPanelLoop`, after each step shell out to the Slice-1 reducer + appender; fold `criticMetrics` into the result object in `doDesign`. All new calls live inside the existing `if (criticConfig)` guard.

**Verification:**
- [ ] Manual end-to-end: a critics-enabled design run produces `.qrspi/<id>/critic-metrics.jsonl` with one line per edge-critic loop and per panel loop
- [ ] Manual: the ticket result object carries a non-empty `criticMetrics`
- [ ] Manual: a critics-DISABLED run produces NO ledger and an unchanged result object (guard verified)
- [ ] `.qrspi/<id>/critic-metrics.jsonl` is gitignored (no untracked-file leak; ref: Risk Register)

**Context cost:** M
**Depends on:** Slice 1

## Slice 3: Config gates for the three cost levers (tested Python core + mirror)

**Goal:** `resolve_design` returns the three new default-OFF gates (`digest`, `lensModel`, `gateBehindEdge`), the JS default mirror matches, and the example config documents them — verifiable via unit tests before any cost-lever wiring depends on them.
**Files touched:**

- ⚠️ `scripts/qrspi_critics_config.py` — extend `resolve_design` with the three nested keys, defaulting OFF/absent
- ⚠️ `scripts/qrspi_critics_config_test.py` — assert defaults are OFF, nested keys parse, JS-mirror parity
- ⚠️ `.claude/workflows/qrspi-batch.js` — update `DEFAULT_CRITIC_PHASES` mirror to match new defaults
- ⚠️ `.qrspi/config.example.json` — document `digest.enabled`, `lensModel`, `gateBehindEdge.enabled`

**Verification:**
- [ ] `python3 scripts/run_tests.py critics_config` passes
- [ ] Test asserts all three gates default OFF / absent (preserves current behavior)
- [ ] Test asserts the Python defaults and the JS `DEFAULT_CRITIC_PHASES` mirror agree (lockstep)

**Context cost:** S
**Depends on:** none

## Slice 4: Cost levers — shared digest (primary), per-lens model, edge gate (JS wiring + digest core + agent input)

**Goal:** With each lever opted in via config, a design run (a) builds a research digest once and passes it by path to all lenses with a non-empty fail-closed guard, (b) threads a per-lens model, and (c) gates the panel behind edge-critic pass — each independently, all default OFF so the default run is unchanged.
**Files touched:**

- ✨ `scripts/qrspi_research_digest.py` — deterministic digest generator
- ✨ `scripts/qrspi_research_digest_test.py` — unit tests (deterministic output, section extraction/trim, empty-input handling)
- ⚠️ `.claude/workflows/qrspi-batch.js` — pre-fan-out digest step + `test -s` non-empty guard (fail-closed); thread `digestPath` and per-lens `model` from `criticConfig`; add the panel-behind-edge-critic gate
- ⚠️ `.claude/agents/qrspi-design-critic-*.md` — accept optional `DIGEST_PATH`; Read it in place of/in addition to `RESEARCH_PATH` when present

**Verification:**
- [ ] `python3 scripts/run_tests.py research_digest` passes
- [ ] Manual end-to-end (digest ON): digest file generated once, all lenses read it, fewer full-research re-reads; empty/missing digest aborts the phase fail-closed
- [ ] Manual (digest OFF, default): lenses read full RESEARCH_PATH; behavior unchanged
- [ ] Manual (lensModel set): verify the `agent()` model option is honored by a single spawn (Risk Register — unverified harness seam; do NOT block ticket on it)
- [ ] Manual (gateBehindEdge ON): panel is skipped when edge critics pass; (default OFF): panel always runs

**Context cost:** L
**Depends on:** Slice 3

## Slice 5: Teeth eval — flawed-design fixture + golden + contract-style assertion

**Goal:** A deliberately-flawed design fixture (silently drops a stated acceptance criterion) plus its golden, with a runnable `scripts/*_test.py` asserting the lens prompt/agent contract would surface the injected flaw — running in the existing CI gate today (Decision 4 Option B; does NOT revive `run_eval.py`).
**Files touched:**

- ✨ `evals/fixtures/design_dropped_criterion_broken.md` — flawed-design fixture
- ✨ `evals/golden/design_dropped_criterion_broken.<ext>` — golden expectation for the fixture
- ✨ `scripts/qrspi_teeth_test.py` — contract-style assertion that the lens contract surfaces the dropped-criterion flaw deterministically

**Verification:**
- [ ] `python3 scripts/run_tests.py teeth` passes and is picked up by the aggregating CI runner
- [ ] The assertion fails if the fixture's injected flaw is removed (the test actually has teeth)

**Context cost:** M
**Depends on:** none (fixture/contract test is independent; does not require the live JS wiring)

---

## Unverified Assumptions

- **Per-lens model option (`agent()` `model`):** The design flags this as an unverified harness seam (Risk Register; Q4). Slice 4 ships it default-OFF and verifies with a single manual spawn; if the harness ignores the option, the lever is inert but does not block the ticket (digest is the primary lever). This cannot be mapped to a guaranteed-working interface until manually confirmed.
- **Teeth-test mechanism specifics:** Decision 4 Option B specifies a "contract-style `scripts/*_test.py` asserting the lens prompt/agent contract would surface the flaw." The exact deterministic mechanism for asserting a *prompt/agent contract* (vs. a live LLM verdict) is not fully pinned down in the design — the test asserts the contract, not a live LLM call. The concrete assertion form needs to be settled in the Plan phase. Golden file extension/format is also unspecified.
- **Digest extraction algorithm:** The design names a "deterministic extraction/trim of research.md sections" but does not specify which sections are kept or the trim rule. The Plan phase must define the concrete extraction logic; the risk that the digest drops signal a lens needed (false PASS) is mitigated by default-OFF + the teeth fixture, but the specific section-selection policy is not yet mapped to code.
- **Token-usage fields:** OQ2 RESOLVED that the live path exposes no per-lens token usage, so `tokensIn?`/`tokensOut?` stay absent in practice. AC-INSTR's token-cost dimension is therefore unmeasured from the live path; the fields exist in the schema only for future/external population. No code path populates them in this ticket.
