# PR: RUS-56 Stage-1 design multi-lens critic panel

**Ticket:** RUS-56
**Design:** design.md @ 2026-06-13T00:00:00Z
**Structure:** structure.md @ 2026-06-13 (rebuilt against current `main`)

## Summary

This replaces the design phase's single edge-critic with a four-lens critic panel
(completeness, internal-consistency, edge-alignment, simplicity) that fans out in
parallel each round, synthesizes the lens verdicts into one authoritative
`{pass, findings}`, and feeds that to the landed `next_action` for the
converge/revise/cap decision — all inside the produce→persist window before the single
`persistArtifact`. The reduction lives in a new pure Python helper
(`scripts/qrspi_critic_synthesize.py`, all-pass-for-pass + exact-string-deduped
finding union) so the merge logic is unit-tested in isolation, mirroring the landed
`qrspi_critic_loop.py` firewall. The panel is config-overridable (`critics.design` in
`.qrspi/config.json` tunes `maxRounds` and the lens set) and **opt-in by lens presence**:
`runPhase` dispatches to the new `runCriticPanelLoop` only when `criticConfig.lenses?.length`
is truthy, so the plan phase and every non-design caller keep the landed single-critic
path byte-for-byte. Reviewer focus: (1) the `runPhase` dispatch branch and that the
single-critic path is unchanged; (2) the fail-closed synthesis contract (empty/garbage
lens ⇒ not-passed, never falsely converges); (3) that the residual-findings → PR-body
splice reuses the landed `criticBodyStep` unchanged (no new body splicer). Note the JS
orchestration glue is manual-e2e-only per the established test convention (no `agent()`/
`parallel()` runtime in this sandbox) — the live design-run e2e checkpoints remain a
reviewer step.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Design phase runs M-lens panel → synthesize → revise ≤ maxRounds before submit | `runCriticPanelLoop` + `runPhase` dispatch in `.claude/workflows/qrspi-batch.js`; `synthesize` in `scripts/qrspi_critic_synthesize.py` | Node logic harness for `parseCriticConfig`/`resolveDesignCritic` (17/17); `scripts/qrspi_critic_synthesize_test.py` (24/24); manual e2e (flawed design ⇒ ≥1 revise then converge/cap) |
| AC2: Each lens gets ticket/research/questions + `design.md`; findings schema-validated | Four lens prompts under `.claude/agents/qrspi-design-critic-*.md` (each declares `DESIGN_PATH`/`TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH`); ingested via landed `parse_critic_verdict` in `runCriticPanelLoop` | `python3 -c` `parse_critic_verdict` ingest probe on valid + fail-with-findings replies (pass); lens-input grep over the four prompt files |
| AC3: Panel-pass on round 1 ⇒ no revise | `next_action` returns `converged` on round-0 `pass:true` in `runCriticPanelLoop` (loop break before revise spawn) | `scripts/qrspi_critic_loop_test.py` (33/33, landed `next_action` contract); manual e2e (clean design ⇒ 0 revise spawns) |
| AC4: Unresolved findings after cap surfaced into design PR body | Cap-reached sets `residualFindings`; spliced via landed `criticBodyStep`/`qrspi_critic_body.py` (reused unchanged) into the design finalize commit | `scripts/qrspi_pr_body_test.py` (23/23, landed `compose_message` splice); manual e2e (capped run ⇒ residuals in submitted PR body) |
| AC5: Design-phase eval score (post-RUS-37 checks) reported before/after | Documentation deliverable (see Open Items — eval procedure); no executable slice (harness is a non-functional ~0 placeholder per OQ4) | N/A — documented procedure, not a CI gate |

## Changes by Slice

### Slice 1: Pure synthesis helper (Python firewall)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critic_synthesize.py` | ✨ new | +151 |
| `scripts/qrspi_critic_synthesize_test.py` | ✨ new | +165 |

(The CLI `main()` stdin→stdout shim in `qrspi_critic_synthesize.py` was added in Slice 3 — see Deviations — but lives in this file.)

### Slice 2: Lens agent prompts

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-design-critic-completeness.md` | ✨ new | +49 |
| `.claude/agents/qrspi-design-critic-internal-consistency.md` | ✨ new | +48 |
| `.claude/agents/qrspi-design-critic-edge-alignment.md` | ✨ new | +52 |
| `.claude/agents/qrspi-design-critic-simplicity.md` | ✨ new | +49 |

### Slice 3: Panel loop + doDesign rewiring + config

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +279, -8 |
| `.qrspi/config.example.json` | ⚠️ modified | +8, -2 |

### Workflow artifacts (non-code, this stack)

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-56/plan.md` | ✨ new | +123 |
| `.qrspi/RUS-56/structure.md` | ✨ new | +111 |
| `.qrspi/RUS-56/worktree.md` | ✨ new | +66 |
| `.qrspi/RUS-56/impl-log.md` | ✨ new | +92 |

## Testing Summary

- [x] Slice 1: pure reducer — `python3 scripts/qrspi_critic_synthesize_test.py` — 24 passed, 0 failed (exit 0)
- [x] Slice 3: CLI shim — tagged-verdict stdin → `{"pass": false, "findings": [{"text": "dropped AC3", "lens": "edge-alignment"}]}`; empty/garbage stdin → `{"pass": false, "findings": []}` (fail-closed)
- [x] Slice 3: JS syntax — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] Slice 3: config-resolution logic — Node harness for `parseCriticConfig` + `resolveDesignCritic` (verbatim source copies) — 17/17 passed
- [x] Slice 3: config validity — `python3 -c json.load(.qrspi/config.example.json)` — OK after `critics.design` block
- [x] Slice 2: lens-reply ingest — `parse_critic_verdict` probe on valid + fail-with-findings replies — both parse unchanged
- [x] Slice 2: no schema dup — grep confirms no new `CRITIC_VERDICT_SCHEMA` (landed constant referenced only)
- [x] Dispatch-by-inspection: `planCritic` has no `lenses` ⇒ routes to landed `runCriticLoop`; only `designCritic` sets `lenses` ⇒ `runCriticPanelLoop`
- [x] Lens id↔agentType mapping: all four `qrspi-design-critic-<id>` agents have matching `name:` fields and identical input set
- [x] Regression: `python3 scripts/qrspi_critic_loop_test.py` — 33/33 (exit 0); `python3 scripts/qrspi_pr_body_test.py` — 23/23 (exit 0) — landed RUS-55 contracts intact
- [ ] Manual e2e (reviewer): live design run — flawed design ⇒ ≥1 revise then converge/cap; clean design ⇒ 0 revise spawns; capped run ⇒ residuals in PR body; `critics.design` config override. JS glue is not unit-testable in this sandbox (no `agent()`/`parallel()` runtime, per Q12).

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `synthesize` invocation mechanism | Structure §Contracts described "call `synthesize`" with no CLI entry point (Slice 1 created the pure function only) | Added a thin `main()` stdin→stdout CLI shim to `scripts/qrspi_critic_synthesize.py` (mirrors the landed `qrspi_critic_loop.py` shim verbatim) | `runCriticPanelLoop` runs in the JS sandbox, which cannot call Python directly — exactly the constraint `criticDecision`→`qrspi_critic_loop.py`'s CLI already solves. The pure `synthesize` is unchanged (24/24 test still passes); additive wiring in Slice 3's panel-loop scope, not a contract change. |
| Lens staged-input variable name | Plan step 6 named the staged design only as "staged `stg(id,'design')`", no fixed prompt variable | The four lens prompts standardize on `DESIGN_PATH` (alongside `TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH`) | Naming choice, not a contract change; the verdict output contract `{pass, findings}` is unchanged. Slice 3 splices the staged design under `DESIGN_PATH`. |
| `designCritic` object fields | Plan step 14 kept `upstreamPath: art(wd,id,'research.md')` + added `lenses` | Also added `ticketContentPath` + `questionsPath` to the `designCritic` object | The four lens prompts require all four inputs and `runCriticPanelLoop` has no `wd`/`r` in scope (deferred-context pattern). Single-critic `runCriticLoop` ignores the extra fields, so the plan-phase path is unaffected. |
| Panel summary fold target | Plan step 15 said "fold a panel summary into `res.summary`" | Folded into `out.summary` (from `finResult`) in `doDesign` | `res` is a land-action local (~line 1281); `out` is the design result object. Same intent, correct variable (mirrors the landed residual-finding fold). |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Foundation 1/5 JS glue (`runCriticLoop`, `criticConfig`, `CRITIC_VERDICT_SCHEMA`) unlanded in the worktree | **Resolved / obsolete** — RUS-55 landed the full single-critic seam on `main` (commit `8028105`); structure was re-derived to reuse it. Panel is a new peer to the landed `runCriticLoop`, not a rebuild. | Revert the RUS-56 stack; the landed RUS-55 single-critic seam remains intact. |
| A reviser writing an empty `stg(id,'design')` flips persist to `ok:false` and stops the ticket | **Mitigated** — `runCriticPanelLoop` re-spawns the design agent with synthesized findings to rewrite the staged file in place; the single persist runs only after the loop, preserving the non-empty gate. (Verified by inspection, not live e2e.) | Set no `critics.design` config and revert `doDesign` to the single-critic `designCritic`. |
| Eval before/after score cannot be produced — harness is a ~0 placeholder | **Accepted (documented)** — AC5 satisfied by documenting the repeatable procedure (OQ4), not a measured number; no fabricated score. | N/A — documentation only. |
| Panel adds M agent spawns per round, raising cost/latency | **Mitigated** — confined to the design phase only; capped at `maxRounds` default 2; round-1 pass-break short-circuits revise; lens set is config-tunable. | Lower `maxRounds`/shrink `lenses` in `.qrspi/config.json`, or remove the config block to fall back to default four. |
| A silently fail-closed lens contributes no findings, weakening coverage | **Mitigated** — per-round `log(...)` pass/fail + a `res.summary` fold surface a degraded panel in run output. | Inspect run logs / `out.summary`; no code rollback needed. |

## Open Items

- **AC5 eval before/after procedure (documentation deliverable, plan T17 deferred to PR phase).** The design-phase eval score is not a measured number — the `evals/` harness is a non-functional ~0 placeholder. Repeatable procedure to produce the delta when a live model is available: (1) inject a live `model` into `evals/suite.json` `defaults` (API key supplied out-of-band); (2) run the design cases `case_005`, `case_006`, `case_014` through `eval_all.py` → `run_eval.py` + `grade.py` (RUS-37 graders: `no_code_blocks`, `has_section`, the `NEW PATTERN?` marker) **before** the panel lands; (3) repeat **after**; (4) record the delta. This is a manual, model-backed exercise, not a CI gate — consistent with the documented convention that the eval harness is verified manually.
- **Manual e2e checkpoints remain a reviewer step.** A live design run producing real lens spawns + a revise round was not executed (no `agent()`/`parallel()` runtime in this sandbox, per Q12). Reviewer should confirm on a real batch run: flawed design ⇒ ≥1 revise then converge/cap; clean design ⇒ 0 revise spawns; capped run ⇒ residuals in PR body; `critics.design` override takes effect.
- **Lens prompt packaging chose four separate files** (vs. one parameterized agent) for clarity, per the structure's unverified-assumption note. No follow-up required unless prompt drift across the four becomes a maintenance burden.
- **Downstream QRSPI critics tickets (3/5, 4/5, 5/5)** extend the panel pattern to the remaining phases; the `synthesize` reducer and `runCriticPanelLoop` peer are reusable seams for them.
