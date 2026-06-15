# PR: RUS-77 Critic effectiveness — metrics, cost levers, teeth eval

**Ticket:** RUS-77
**Design:** design.md @ 2026-06-14T18:00:00Z
**Structure:** structure.md @ 2026-06-14T18:30:00Z

## Summary

RUS-77 ("Ticket A" of the critic-effectiveness feature) adds three capabilities to
the design-phase critic layer: (1) **instrumentation** — every critic step now emits
a machine-readable `CriticStepMetrics` record (per-lens pass/fail + findings counts +
terminal action) that folds into the ticket result and persists to a per-ticket
append-only ledger (`.qrspi/<id>/critic-metrics.jsonl`); (2) **cost reduction** — three
independent, default-OFF config levers (a shared research digest passed by path to all
lenses, an optional per-lens model, and a panel-behind-edge gate); and (3) a **teeth
eval** — a deliberately-flawed design fixture plus golden plus a deterministic
contract-style assertion. All new deterministic logic lands as stdlib-only Python cores
with `_test.py` siblings; `qrspi-batch.js` only shells out. **Reviewer focus:** the
disabled-path invariant (all levers default OFF ⇒ byte-for-byte-unchanged lens inputs,
dispatch, and result object — verified by inspection in Slice 2/4), and two deliberate
scope-honesty decisions (`gateBehindEdge` ships as an honest no-op pending an upstream
edge outcome; `lensModel` is a speculative seam the harness may not honor — neither
blocks the ticket; digest is the primary lever).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC-INSTR: each critic step emits a machine-readable record (per-lens pass/findings, terminal action; tokens optional/absent per OQ2) | `scripts/qrspi_critic_metrics.py:build_record` | `scripts/qrspi_critic_metrics_test.py` |
| AC-INSTR: records persist to a durable per-ticket ledger (append, not overwrite; fail-closed) | `scripts/qrspi_metrics_append.py:main` | `scripts/qrspi_metrics_append_test.py` |
| AC-INSTR: records fold into the ticket result via the critic loops, disabled path unchanged | `.claude/workflows/qrspi-batch.js:recordCriticMetrics` (+ `runCriticLoop`/`runCriticPanelLoop`/`doDesign` wiring) | `scripts/qrspi_critic_metrics_test.py` + `scripts/qrspi_metrics_append_test.py` (integration smoke, impl-log Session 2); JS seam by inspection (harness-coupled) |
| AC-COST: three cost levers exist as independent default-OFF config gates | `scripts/qrspi_critics_config.py:resolve_design` (+ `DEFAULT_CRITIC_PHASES` JS mirror, `.qrspi/config.example.json`) | `scripts/qrspi_critics_config_test.py` (incl. `JsMirrorParityTests`) |
| AC-COST (a): shared research digest produced once, passed by path, non-empty fail-closed guard | `scripts/qrspi_research_digest.py:build_digest` + `.claude/workflows/qrspi-batch.js:buildResearchDigest` + lens `DIGEST_PATH` input | `scripts/qrspi_research_digest_test.py` |
| AC-COST (b): per-lens model threaded via `criticConfig` (speculative seam, default OFF) | `.claude/workflows/qrspi-batch.js` (`runCriticPanelLoop` lens `agentOpts.model`) | covered by config default-OFF test; live seam not verifiable in sandbox (Risk Register) |
| AC-COST (c): panel-behind-edge gate (default OFF, honest no-op) | `.claude/workflows/qrspi-batch.js:runPhase` (panel-vs-edge dispatch gate) | covered by config default-OFF test; gate-ON e2e not runnable in sandbox |
| AC-TEETH: flawed-design fixture + golden + deterministic assertion that surfaces the dropped criterion | `evals/fixtures/design_dropped_criterion_broken.md`, `evals/golden/design_dropped_criterion_broken.json`, `scripts/qrspi_teeth_test.py:dropped_criteria` | `scripts/qrspi_teeth_test.py` (`FixtureWellFormedTest` + `TeethOfTheTeethTest`) |

## Changes by Slice

### Slice 1: Metrics reducer + ledger appender (tested Python core)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critic_metrics.py` | ✨ new (pure reducer `build_record`) | +103 |
| `scripts/qrspi_critic_metrics_test.py` | ✨ new | +93 |
| `scripts/qrspi_metrics_append.py` | ✨ new (self-locating appender + write-verify) | +147 |
| `scripts/qrspi_metrics_append_test.py` | ✨ new | +136 |

### Slice 2: Wire metrics into the critic loops + result object (JS shell)

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified (`recordCriticMetrics` helper; loop + `runPhase` + `doDesign` wiring) | +130, -13 |
| `scripts/qrspi_critic_metrics.py` | ⚠️ modified (added stdin→stdout CLI shim over `build_record`) | +53 |

### Slice 3: Config gates for the three cost levers (tested Python core + mirror)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critics_config.py` | ⚠️ modified (`resolve_design` + 3 nested default-OFF gates) | +40, -5 |
| `scripts/qrspi_critics_config_test.py` | ⚠️ modified (defaults-OFF, per-lever parse, JS-mirror parity) | +107 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified (`DEFAULT_CRITIC_PHASES` mirror) | +4, -1 |
| `.qrspi/config.example.json` | ⚠️ modified (document the 3 knobs) | +7 |

### Slice 4: Cost levers — shared digest, per-lens model, edge gate

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_research_digest.py` | ✨ new (deterministic fence-strip digest generator) | +122 |
| `scripts/qrspi_research_digest_test.py` | ✨ new | +168 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified (`buildResearchDigest`; digest/model threading; edge gate) | +83, -3 |
| `.claude/agents/qrspi-design-critic-completeness.md` | ⚠️ modified (optional `DIGEST_PATH` input) | +4, -1 |
| `.claude/agents/qrspi-design-critic-edge-alignment.md` | ⚠️ modified (optional `DIGEST_PATH` input) | +4, -1 |
| `.claude/agents/qrspi-design-critic-internal-consistency.md` | ⚠️ modified (optional `DIGEST_PATH` input) | +4, -1 |
| `.claude/agents/qrspi-design-critic-simplicity.md` | ⚠️ modified (optional `DIGEST_PATH` input) | +4, -1 |

### Slice 5: Teeth eval — flawed-design fixture + golden + contract assertion

| File | Change | Lines |
|------|--------|-------|
| `evals/fixtures/design_dropped_criterion_broken.md` | ✨ new (flawed fixture — DO NOT "fix") | +84 |
| `evals/golden/design_dropped_criterion_broken.json` | ✨ new (golden expectation) | +12 |
| `scripts/qrspi_teeth_test.py` | ✨ new (deterministic coverage check + teeth-of-the-teeth) | +228 |

### Phase artifacts (not slice code)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-77/questions.md` | ✨ new | +47 |
| `.qrspi/RUS-77/research.md` | ✨ new | +480 |
| `.qrspi/RUS-77/design.md` | ✨ new | +246 |
| `.qrspi/RUS-77/structure.md` | ✨ new | +134 |
| `.qrspi/RUS-77/plan.md` | ✨ new | +253 |
| `.qrspi/RUS-77/worktree.md` | ✨ new | +137 |
| `.qrspi/RUS-77/impl-log.md` | ✨ new | +167 |

## Testing Summary

- [x] Slice 1: reducer + appender units — `python3 scripts/run_tests.py metrics` — 2 test files passed, 0 failed
- [x] Slice 1: manual append idempotency — appender run twice → 1-line then 2-line ledger (append, no overwrite); no `.worktrees/<id>/.worktrees/<id>/…` double-nesting
- [x] Slice 2: full regression — `python3 scripts/run_tests.py` — 33 passed, 0 failed
- [x] Slice 2: JS syntax — `node --check .claude/workflows/qrspi-batch.js` — JS-SYNTAX-OK
- [x] Slice 2: integration smoke — chained reducer→appender worker command → 2 envelope-wrapped ledger lines (Python-derived `findingsCount`)
- [x] Slice 2: ledger gitignored — `git check-ignore -v` matches `.gitignore:3:.worktrees/`
- [x] Slice 3: config units — `python3 scripts/run_tests.py critics_config` — 1 test file passed
- [x] Slice 3: JS-mirror parity non-vacuous — `python3 -m unittest scripts.qrspi_critics_config_test.JsMirrorParityTests -v` — 2 passed
- [x] Slice 3: example config valid JSON — `python3 -c "import json; json.load(open('.qrspi/config.example.json'))"` — VALID
- [x] Slice 4: digest units — `python3 scripts/run_tests.py research_digest` — 1 test file passed
- [x] Slice 4: digest on a REAL research.md — `qrspi_research_digest.py --research .qrspi/RUS-77/research.md` — 40497B → 32490B, 0 fences remaining
- [x] Slice 4: workflow meta/syntax gate — `node scripts/check_workflows.js .claude/workflows/qrspi-batch.js` — OK
- [x] Slice 5: teeth units — `python3 scripts/run_tests.py teeth` — 1 test file passed (5 tests; repaired fixture yields empty dropped set ⇒ assertion is load-bearing)
- [x] Full suite (final) — `python3 scripts/run_tests.py` — 35 passed, 0 failed
- [ ] Live-agent e2e (T13, T29–T32): critics-enabled vs disabled design run; digest ON/OFF; lensModel single-spawn; gateBehindEdge ON/OFF — **NOT runnable in the implement-agent sandbox** (require live agents/Linear); verified by code inspection of the disabled-path invariant instead

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `qrspi_critic_metrics.py` (Slice 1) | reducer `build_record` only (no CLI) | Added a pure stdin→stdout CLI shim in Slice 2 | Slice 1 shipped no callable CLI, so JS had no way to invoke the reducer; the shim is a pure addition (mirrors `qrspi_critic_synthesize.py`), satisfies both "reduce via the reducer" and "count derived in Python", and changes no `build_record` signature |
| `TicketResult.criticMetrics` | Modified Types lists `criticMetrics` as an added field (could read as always-present) | Key OMITTED on the fully-disabled path; present only when ≥1 record surfaced | Follows plan §12's more-specific disabled-path guarantee (byte-for-byte-unchanged result object) |
| `DesignCriticConfig.lensModel?: str` | "defaulting OFF / absent" | Key OMITTED (not `None`) when config supplies no/empty/non-string value | Resolved "absent" literally; keeps default design block byte-identical and the JS mirror lockstep-equal (the `?` denotes optional/absent) |
| Golden file extension (Slice 5) | `evals/golden/...broken.<ext>` (unverified) | `.json` | Pinned by plan step 34 |
| `gateBehindEdge` lever (Slice 4) | a working panel-skip optimization | Honest conditional no-op: skips panel only when `gateBehindEdge.enabled && criticConfig.edgePassed === true`, but nothing plumbs `edgePassed` for design today, so it logs the gap and runs the panel | Per plan §25 scope note: no in-scope upstream edge outcome exists for the design panel to gate behind; records the gap rather than fabricating a sequence |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Token usage not exposed to the workflow → per-lens token metrics unobtainable | accepted (OQ2) — `tokensIn`/`tokensOut` ship absent; core base-rate signal is pass/fail + findings count (always available) | n/a — cost dimension shipped unmeasured by design |
| Shared digest drops content a lens needed → false PASS | mitigated — digest default OFF; non-empty fail-closed guard; full-research path preserved as default; teeth fixture is the validation substrate | Set `critics.design.digest.enabled` false (the default) to disable |
| `agent()` may not honor a `model` option (unverified seam) | accepted/unverified — `lensModel` ships default-absent; inert if the harness ignores it; not blocking (digest is primary) | Omit `lensModel` from config (the default) |
| `run_eval.py` is a non-functional placeholder → teeth eval may not be executable in-scope | mitigated — delivered Decision 4 Option B (deterministic contract-style `scripts/qrspi_teeth_test.py` in the existing CI gate); does NOT revive `run_eval.py` | Tests run in CI today; a true behavioral lens eval is deferred (see Open Items) |
| JS changes to `qrspi-batch.js` not unit-testable (harness-coupled) | accepted — all logic in tested Python cores; JS seam verified by `node --check` + `check_workflows.js` + integration smoke + inspection | Revert the slice commit(s) touching `qrspi-batch.js` |
| New `critic-metrics.jsonl` ledger left untracked / collides across tickets | mitigated — written per-ticket under `.worktrees/<id>/.qrspi/<id>/`, already gitignored by `.gitignore:3:.worktrees/` (verified via `git check-ignore`); no extra rule needed | Delete the ledger file; it is gitignored and per-ticket isolated |

## Open Items

- **Live behavioral teeth eval is deferred** (OQ1 / Decision 4 Option B): `scripts/qrspi_teeth_test.py` is a deterministic STRUCTURAL check over the fixture, not a live exercise of any lens. It does not run/mock the completeness lens, so it does not verify AC-TEETH's "a flawed design makes each lens fail" *behaviorally*. Reviving `evals/run_eval.py` to a real behavioral runner is a separate follow-up ticket; the fixture + golden are the durable substrate it would consume.
- **`gateBehindEdge` lever does no real work yet**: to activate it, a future ticket must plumb a passing upstream edge-critic outcome onto the design `criticConfig.edgePassed` in `doDesign` (where `r` is in scope). Until then it is an honest no-op.
- **`lensModel` is a speculative seam**: no evidence the harness honors `agent()` `model`; verify with a single live spawn (T31) before relying on it. Inert if ignored.
- **Token-cost dimension unmeasured** (OQ2): `tokensIn`/`tokensOut` exist in the schema only for future/external population; no code path fills them in the live path.
- **Calibration (Ticket B)** is explicitly out of scope and data-gated on this ticket's instrumentation; it composes its judgment from the raw pass/fail + findings counts this ledger records (OQ4).
- **Live-agent e2e checkpoints (T13, T29–T32)** could not run in the implement-agent sandbox; they should be exercised in a real critics-enabled run before trusting the cost levers ON.
