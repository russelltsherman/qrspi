# PR: RUS-56 Stage-1 design multi-lens critic panel + edge critic

**Ticket:** RUS-56
**Design:** design.md @ 2026-06-13T00:00:00Z
**Structure:** structure.md @ 2026-06-13T00:00:00Z

## Summary

This change adds an opt-in, four-lens critic panel to the QRSPI design phase. Inside the design produce→persist window, `doDesign` now fans out four parallel lens agents (completeness, internal-consistency, edge-alignment, simplicity) against the staged `design.md`, reduces their `{pass, findings}` verdicts to one authoritative verdict via a new pure `synthesize`, and delegates the converge/revise/cap decision to the already-landed `next_action` — re-spawning the design agent to rewrite the staged design in place on `revise`, capped at `maxRounds` (default 2). The whole panel is gated behind a new optional `criticConfig`/`criticCtx` on `runPhase`: when the `critics.design` config block is absent, `runPhase` reproduces today's single-persist behavior byte-for-byte. Reviewers should focus on (1) the `runPhase` produce→persist seam and its `if (criticConfig && criticCtx)` guard, (2) the fail-closed lens/synthesis path (a null or garbled lens can never falsely converge), and (3) the residual-findings PR-body splice that rides into the design finalize commit on `cap_reached`. Note AC5 is a documentation deliverable (see Open Items / Risks) — the eval harness is a non-functional placeholder, so no measured score is produced.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Design runs M-lens panel → synthesize → revise ≤ maxRounds before submit | `.claude/workflows/qrspi-batch.js:runCriticPanelLoop` + `runPhase` (criticConfig guard); `scripts/qrspi_critic_synthesize.py:decide_round` | `scripts/qrspi_critic_synthesize_test.py` (decide_round checks); `node --check qrspi-batch.js`; extracted `parseCriticConfig`/`buildDesignCriticConfig` helper probe (12 fixtures) |
| AC2: Each lens receives upstream (ticket/research/questions) + design.md; findings schema-validated | `.claude/agents/qrspi-design-critic-{completeness,internal-consistency,edge-alignment,simplicity}.md`; `CRITIC_VERDICT_SCHEMA` in qrspi-batch.js; ingest via `scripts/qrspi_critic_loop.py:parse_critic_verdict` | input-wiring grep (each lens references `TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH`/`DESIGN_PATH`/`CRITIC_VERDICT_SCHEMA`); `parse_critic_verdict` ingest probe |
| AC3: Panel-pass on round 1 ⇒ no revise | `scripts/qrspi_critic_synthesize.py:decide_round` (synthesize → next_action `converged`) | `scripts/qrspi_critic_synthesize_test.py` (all-pass → converged, no revise) |
| AC4: Unresolved findings after cap surfaced into design PR body | `scripts/qrspi_critic_body.py:splice`; cap-reached splice step in `doDesign` finalize via `qrspi_critic_body.py --findings-file` | `scripts/qrspi_critic_body_test.py`; e2e residual-splice probe (`[{text,lens},"bare"]` → "Residual critic findings" block; `[]` → no-op) |
| AC5: Measured design-phase eval score reported before/after | Documentation-only (per OQ4) — procedure recorded below, no code slice | N/A — eval harness is a non-functional placeholder (see Open Items) |

## Changes by Slice

### Slice 1: Pure synthesis + body helpers (Python firewall)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critic_synthesize.py` | ✨ new | +213 |
| `scripts/qrspi_critic_synthesize_test.py` | ✨ new | +176 |
| `scripts/qrspi_critic_body.py` | ✨ new | +163 |
| `scripts/qrspi_critic_body_test.py` | ✨ new | +139 |

(Note: `decide_round` + its CLI `__main__` were added to `qrspi_critic_synthesize.py` during Slice 3 — see Deviations.)

### Slice 2: Lens agent prompts + verdict schema

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-design-critic-completeness.md` | ✨ new | +53 |
| `.claude/agents/qrspi-design-critic-internal-consistency.md` | ✨ new | +53 |
| `.claude/agents/qrspi-design-critic-edge-alignment.md` | ✨ new | +54 |
| `.claude/agents/qrspi-design-critic-simplicity.md` | ✨ new | +54 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | (`CRITIC_VERDICT_SCHEMA` constant only) |

### Slice 3: Panel loop + doDesign wiring + config + PR-body splice

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +292, -5 (cumulative across slices 2+3) |
| `.qrspi/config.example.json` | ⚠️ modified | +7 |

### Workflow artifacts (not a code slice)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-56/questions.md` | ✨ new | +59 |
| `.qrspi/RUS-56/research.md` | ✨ new | +445 |
| `.qrspi/RUS-56/design.md` | ✨ new | +113 |
| `.qrspi/RUS-56/structure.md` | ✨ new | +81 |
| `.qrspi/RUS-56/plan.md` | ✨ new | +132 |
| `.qrspi/RUS-56/worktree.md` | ✨ new | +68 |
| `.qrspi/RUS-56/impl-log.md` | ✨ new | +120 |

## Testing Summary

- [x] Slice 1: `python3 scripts/qrspi_critic_synthesize_test.py` — 18 passed (Slice 1), 23 passed after Slice 3 added 5 `decide_round` checks
- [x] Slice 1: `python3 scripts/qrspi_critic_body_test.py` — 20 passed
- [x] Slice 2: `node --check .claude/workflows/qrspi-batch.js` — SYNTAX_OK
- [x] Slice 2: `parse_critic_verdict` ingest probes (valid lens reply not coerced; prose-wrapped embedded-JSON ingested) — pass
- [x] Slice 2: input-wiring grep — each of four lens prompts references the required path vars + `CRITIC_VERDICT_SCHEMA`
- [x] Slice 3: `node --check .claude/workflows/qrspi-batch.js` — SYNTAX_OK
- [x] Slice 3: extracted `parseCriticConfig` + `buildDesignCriticConfig` helper probe over 12 fixtures — ALL PASS
- [x] Slice 3: config round-trip — `qrspi_config.py --key critics` returns nested object when present, `value:""` when absent (panel off)
- [x] Slice 3: e2e residual splice — `qrspi_critic_body.py` with `[{text,lens},"bare"]` → "Residual critic findings" block; `[]` → message unchanged
- [x] Regression (Slice 3): `python3 scripts/qrspi_critic_loop_test.py` — 33 passed (RUS-55)
- [x] Regression (Slice 3): `python3 scripts/qrspi_pr_body_test.py` — 23 passed (RUS-55)
- [ ] Manual verification: full end-to-end batch design run (live Linear ticket + Graphite stack + reviewer) — NOT executed; JS fan-out wiring is syntax-checked and helper logic probed, but the live produce→persist→submit path is unverified (per Q12: JS glue is manual-e2e only). Deferred — see Open Items.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `runPhase` signature | optional trailing `criticConfig` param (single) | `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig, criticCtx)` — 7th `criticConfig` AND 8th `criticCtx` param | The mutable `criticCtx {wd, r, residualFindings, panelSummary}` is the side-channel the panel needs for `art()`/`stg()` paths and to hand residuals back to the finalize splice; both optional, guarded by `if (criticConfig && criticCtx)`; no other caller passes them — absent ⇒ byte-for-byte today's behavior |
| `scripts/qrspi_critic_synthesize.py` | pure library only (synthesize) | added `decide_round(verdicts, round, max_rounds)` + a stdin/stdout `__main__` CLI | Plan Step 20 said "call synthesize and next_action", but the JS sandbox cannot run Python and re-implementing the reduction/decision in JS would drift from the tested helpers; `decide_round` reuses both landed pure functions (`synthesize` + imported `next_action`) in one deterministic invocation. The `__main__` guard never fires under import; `synthesize` + its original tests untouched; 5 new tests added |
| Lens prompt packaging | "`qrspi-design-critic.md` (or four per-lens prompt files)" — left open | four separate per-lens prompt files | Plan resolved the open layout choice to four files mapping 1:1 to lens names via `qrspi-design-critic-${lens}.md` |
| Lens design-path arg | "staged `stg(id,'design')`" | prompt-variable `DESIGN_PATH` (runner binds it to `stg(id,'design')`) | Naming follows the RUS-55 critic agent's named-path-variable convention; no behavioral deviation — the runner binds the staged path to `DESIGN_PATH` |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Foundation 1/5 JS glue (`runCriticLoop`, `criticConfig`, `CRITIC_VERDICT_SCHEMA`) unlanded in this worktree | mitigated — this ticket built the orchestration seam (panel variant) itself as first-class scope rather than extending a missing function | Revert qrspi-batch.js panel additions |
| A reviser writing an empty `stg(id,'design')` flips persist to `ok:false` and stops the ticket | mitigated — reviser re-spawn rewrites the staged file in place; single persist runs only after the loop; a null revise re-spawn ends the panel gracefully (`ok:true`, persists current design) rather than failing the ticket | Disable panel (remove `critics.design` config block) ⇒ no revise spawns |
| Eval before/after score cannot be produced — harness is a ~0 placeholder | accepted — AC5 reduced to a documented procedure (OQ4), not a measured run | N/A (no code) |
| Panel adds M agent spawns per round, raising cost/latency | mitigated — panel confined to design phase, capped at maxRounds default 2, round-1 pass-break short-circuits revise; entirely opt-in (off by default) | Remove `critics.design` config block to disable |
| A silently fail-closed lens contributes no findings, weakening coverage | accepted with mitigation — per-round `r<N>:pass/fail(<k>)` + `cap_reached` summary logged and folded into `res.summary` as `[critic: ...]`; a degraded panel is visible in run output | N/A (observability only) |
| New (discovered): JS fan-out wiring not exercised end-to-end | accepted — pure decision logic, config seam, and residual-splice each independently verified; live e2e deferred (requires live Linear ticket + stack + reviewer) | Opt-in seam off by default means production design runs are unaffected until a `critics.design` block is set |

## Open Items

- **AC5 eval procedure (deferred from implementation per OQ4):** the design-phase eval score is produced by injecting a live `model` into `evals/suite.json` `defaults` (API key supplied out-of-band), then running design cases `case_005/006/014` through `eval_all.py` → `run_eval.py` + `grade.py` (RUS-37 graders: `no_code_blocks`, `has_section`, the `NEW PATTERN?` marker) **before and after** the panel lands, recording the delta. The repeatable procedure — not a CI-gated number — is the deliverable; the harness is a non-functional ~0 placeholder, so an actual model-backed run is an optional manual exercise.
- **End-to-end batch run (T26) not executed:** the live produce→persist→submit path with four parallel lens spawns + revise rounds requires a live Linear ticket, Graphite stack, and reviewer (the finalize/submit path the orchestrator drives). Recommend a manual e2e run with a deliberately-flawed design (to force ≥1 revise round) and a clean design (to confirm zero revise spawns, AC3) before relying on the panel in production.
- **Config reader limitation (carried forward):** `qrspi_config.py --key` resolves a single top-level key only (no dot-path), and JS `parseConfigEnvelope` rejects non-string values. The panel reads the top-level `critics` key and parses `.design` with a separate lenient `parseCriticConfig`. A future generalized nested-config reader would let other phases adopt the same pattern without a bespoke parser.
- **Follow-up (this is critics 2/5):** the remaining QRSPI-critics tickets (3/5–5/5) extend the panel/critic pattern to other phases; the single-phase confinement here is intentional scope, not an omission.
