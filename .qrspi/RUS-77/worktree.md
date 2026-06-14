# Work Tree — Critic effectiveness: instrumentation, cost reduction, teeth eval

**Plan basis:** plan.md @ 2026-06-14T19:00:00Z
**Generated:** 2026-06-14T19:30:00Z
**Status:** draft
**Total sessions:** 6
**Critical path:** T1 → T2 → T4 → T5 → T7 (Slice 1) → T15 (Slice 3 wiring) → T22 → T26 → T30 (Slice 4 levers) → T41 (final gate)

> Slice dependency note (from plan): Slices 1, 3, 5 are tested Python cores
> with no JS dependency (parallelizable in principle). Slice 2 depends on
> Slice 1; Slice 4 depends on Slice 3. Sessions are sequenced by slice so each
> session loads only its slice's plan section. The critical path runs through
> the Python core → its JS wiring for the two dependent slice pairs (1→2, 3→4),
> with the final full-suite gate (Session 6) gating on everything.

## Session 1 — Slice 1: Metrics reducer + ledger appender (tested Python core)

**Load:** plan.md §Slice 1, structure.md §New Types (CriticStepMetrics,
        CriticRoundRecord, CriticMetricsLedgerLine), structure.md §Contracts
        (build_record, qrspi_metrics_append)
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_critic_metrics.py` — pure reducer module skeleton with canonical record shape docstring | — | §1 | S | pending |
| T2 | Implement `build_record(verdicts, terminalAction, usage=None, phase=...)` per Contract; validate terminalAction; emit tokensIn/Out only when usage supplies them | T1 | §2 | M | pending |
| T3 | Create `scripts/qrspi_critic_metrics_test.py` — unit tests for build_record (all-pass, mixed, usage absent/present, valid/invalid terminalAction) | T2 | §3 | S | pending |
| T4 | Create `scripts/qrspi_metrics_append.py` — self-locating CLI skeleton; argparse --ticket/--record; resolve ledger path; parse JSON fail-closed | T1 | §4 | M | pending |
| T5 | Implement envelope-wrap + append-and-verify in appender: inject ticketId + UTC timestamp, append-mode write, non-empty verify, fail-closed | T4 | §5 | M | pending |
| T6 | Create `scripts/qrspi_metrics_append_test.py` — create/append/no-overwrite, envelope-shape, fail-closed-on-bad-JSON tests | T5 | §6 | S | pending |
| T7 | **Verify Slice 1** — `python3 scripts/run_tests.py metrics` (both modules pass; OQ2/OQ4 envelope + append checks) | T3, T6 | §7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (tested Python core landed). Fresh context for the
JS-shell wiring of Slice 2, which loads the batch orchestrator instead of the
Python core internals.

## Session 2 — Slice 2: Wire metrics into the critic loops + result object (JS shell)

**Load:** plan.md §Slice 2, structure.md §Modified Types (TicketResult),
        impl-log.md §Slice 1 (notes only — appender/reducer CLI contract)
**Estimated context:** ~22%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Modify `.gitignore` — add `**/.qrspi/*/critic-metrics.jsonl` so the ledger is never committed | T7 | §8 | S | pending |
| T9 | Modify `qrspi-batch.js` `runCriticLoop` — build verdicts, shell to reducer + appender (engineCmdFor/r.repoRoot), return record for doDesign | T7 | §9 | M | pending |
| T10 | Modify `qrspi-batch.js` `runCriticPanelLoop` — build per-lens verdicts, call reducer + appender, accumulate record | T9 | §10 | M | pending |
| T11 | Modify `qrspi-batch.js` `doDesign` — collect edge + panel records into `criticMetrics` array, fold into ticket result object | T10 | §11 | S | pending |
| T12 | Modify `qrspi-batch.js` — confirm all new calls + fold sit strictly inside `if (criticConfig)` guard (disabled path byte-unchanged) | T11 | §12 | S | pending |
| T13 | **Verify Slice 2** — manual e2e: critics ON writes envelope ledger lines + non-empty criticMetrics; critics OFF writes nothing, unchanged result; ledger gitignored | T8, T12 | §13 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (metrics fully wired). Fresh context for Slice 3,
an independent tested Python config core + JS mirror — no Slice 2 internals
needed beyond knowing the ledger lever exists.

## Session 3 — Slice 3: Config gates for the three cost levers (tested Python core + mirror)

**Load:** plan.md §Slice 3, structure.md §Modified Types (DesignCriticConfig,
        DEFAULT_CRITIC_PHASES)
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T14 | Modify `scripts/qrspi_critics_config.py` `resolve_design` — add nested gates digest.enabled, lensModel, gateBehindEdge.enabled (all default OFF/absent) | T13 | §14 | M | pending |
| T15 | Modify `scripts/qrspi_critics_config_test.py` — defaults-OFF, each gate parses through, Python↔JS parity assertion | T14 | §15 | M | pending |
| T16 | Modify `qrspi-batch.js` `DEFAULT_CRITIC_PHASES` mirror — add the three new default-OFF gates in lockstep with resolve_design | T14 | §16 | S | pending |
| T17 | Modify `.qrspi/config.example.json` — document the three default-OFF design-critic knobs | T14 | §17 | S | pending |
| T18 | **Verify Slice 3** — `python3 scripts/run_tests.py critics_config` (gates default OFF; parity test green) | T15, T16, T17 | §18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 complete (config gates + mirror in lockstep). Fresh context
for Slice 4, which consumes the gates to implement the three cost levers across
the digest CLI, the JS fan-out, and the lens agent files.

## Session 4 — Slice 4: Cost levers — shared digest (primary), per-lens model, edge gate

**Load:** plan.md §Slice 4, structure.md §Contracts (qrspi_research_digest,
        Lens agent input contract), impl-log.md §Slice 3 (config gate names only)
**Estimated context:** ~30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Create `scripts/qrspi_research_digest.py` — self-locating CLI skeleton; argparse --research/--out; header-anchored extraction policy docstring | T18 | §19 | M | pending |
| T20 | Implement digest extraction — whitelist Current State / Desired End State / Delta in order; fail-closed on empty / no-match | T19 | §20 | M | pending |
| T21 | Create `scripts/qrspi_research_digest_test.py` — whitelist, determinism, fail-closed-on-empty / no-match tests | T20 | §21 | S | pending |
| T22 | Modify `qrspi-batch.js` — when digest.enabled, build digest once before fan-out + `test -s` guard (fail-closed) | T20 | §22 | M | pending |
| T23 | Modify `qrspi-batch.js` — thread `DIGEST_PATH` into each lens agent input when digest.enabled; else omit | T22 | §23 | S | pending |
| T24 | Modify `qrspi-batch.js` — pass `model: criticConfig.lensModel` on each lens agent call when lever ON; else omit | T18 | §24 | S | pending |
| T25 | Modify `qrspi-batch.js` — when gateBehindEdge.enabled, run panel only if edge critics passed; else always run | T18 | §25 | S | pending |
| T26 | Modify `qrspi-design-critic-completeness.md` — accept optional DIGEST_PATH; prefer it over RESEARCH_PATH when present | T23 | §26 | S | pending |
| T27 | Modify remaining three `qrspi-design-critic-*.md` lens agents — same optional-DIGEST_PATH contract (one atomic edit per file) | T26 | §27 | M | pending |
| T28 | **Verify Slice 4** — `python3 scripts/run_tests.py research_digest` (all cases pass) | T21 | §28 | S | pending |
| T29 | **Verify Slice 4** — manual e2e digest.enabled ON: digest built once, all lenses receive DIGEST_PATH, empty digest aborts fail-closed | T22, T23, T27 | §29 | M | pending |
| T30 | **Verify Slice 4** — manual e2e all levers OFF: full RESEARCH_PATH, no digest, behavior unchanged | T22, T23, T24, T25 | §30 | S | pending |
| T31 | **Verify Slice 4** — manual single spawn with lensModel set; record model-option observation (do not block if harness ignores) | T24 | §31 | S | pending |
| T32 | **Verify Slice 4** — manual e2e gateBehindEdge ON (panel skipped on edge pass) vs OFF (panel always runs) | T25 | §32 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 complete (all cost levers + lens contracts). Fresh context
for Slice 5, an independent eval-fixture/teeth-test core that loads no batch.js
or config internals.

## Session 5 — Slice 5: Teeth eval — flawed-design fixture + golden + contract-style assertion

**Load:** plan.md §Slice 5, structure.md §Contracts (teeth test mechanism),
        design.md §Decision 4 (Option B)
**Estimated context:** ~15%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T33 | Create `evals/fixtures/design_dropped_criterion_broken.md` — flawed design that silently drops one stated AC from its Delta/Decisions | T32 | §33 | S | pending |
| T34 | Create `evals/golden/design_dropped_criterion_broken.json` — golden: dropped criterion id + mustSurface expectation | T33 | §34 | S | pending |
| T35 | Create `scripts/qrspi_teeth_test.py` — contract-style unittest: assert droppedCriterion ∈ (stated − covered) via criterion-coverage check | T34 | §35 | M | pending |
| T36 | Modify `scripts/qrspi_teeth_test.py` — add repaired-fixture negative case (re-add criterion → no detection; proves teeth) | T35 | §36 | S | pending |
| T37 | **Verify Slice 5** — `python3 scripts/run_tests.py teeth` (passes; enumerated by --list) | T36 | §37 | S | pending |
| T38 | **Verify Slice 5** — confirm teeth: repaired-fixture case shows assertion would fail if flaw removed | T36 | §38 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All five slices complete. Fresh context for the final full-suite
regression + disabled-path gate, which spans every slice's artifacts and must
run with no slice-specific bias loaded.

## Session 6 — Final full-suite gate

**Load:** plan.md §Final full-suite gate, impl-log.md §Slices 1–5 (notes only)
**Estimated context:** ~12%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T39 | **Checkpoint:** `python3 scripts/run_tests.py` — entire suite green (CI regression gate) | T7, T18, T28, T37 | §39 | S | pending |
| T40 | **Checkpoint:** `python3 scripts/run_tests.py --list` — all five new `_test.py` modules enumerated | T39 | §40 | S | pending |
| T41 | **Checkpoint:** Re-confirm critics-DISABLED path byte-for-byte unchanged (no ledger, no digest, unchanged result, identical lens inputs) | T13, T30, T39 | §41 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Work tree complete. Next phase is implementation, starting at Session 1.
