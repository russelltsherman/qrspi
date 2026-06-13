# Work Tree — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Plan basis:** plan.md @ 2026-06-13 (rebuilt against current `main`)
**Generated:** 2026-06-13 (rebuilt)
**Status:** draft
**Total sessions:** 3
**Critical path:** T0 → T1 → T2 → T3 → T4 → T6 → T11 → T12 → T13 → T14 → T15 → T18 (12 tasks)

> **Reconciliation note (see structure.md §Reconciliation):** RUS-55's single-critic seam is landed
> on `main` and **reused**. This DAG drops the previously-planned tasks that recreated it
> (`qrspi_critic_body.py`, the `CRITIC_VERDICT_SCHEMA` add, the `runPhase` param-add, the
> body-splice add) — those caused the collision. Net-new tasks only.

## Session 1 — Slice 1: Pure synthesis helper (Python firewall)

**Load:** plan.md §Slice 1, plan.md §Pre-build verification, structure.md §Contracts, structure.md §New Types (`SynthesizedVerdict`, `LensVerdict`)
**Estimated context:** ~14% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T0 | Pre-build verification (reads only): confirm landed `parse_critic_verdict`/`next_action`, `compose_message`, `qrspi_critic_body.py`/`criticBodyStep`, `CRITIC_VERDICT_SCHEMA` (qrspi-batch.js:416), `runPhase`'s 7-param signature, `doDesign`'s existing `designCritic`, `parallel()`/`agent()`, and the `qrspi_config.py --key critics` round-trip all match structure.md; stop on mismatch | — | §Pre-build | S | pending |
| T1 | Create `scripts/qrspi_critic_synthesize.py` module shell importing the landed `parse_critic_verdict` | T0 | §1 | S | pending |
| T2 | Implement `synthesize(verdicts) -> SynthesizedVerdict` (coerce fail-closed, all-pass AND, order-preserving deduped union) | T1 | §2 | M | pending |
| T3 | Add optional lens-tagging in `synthesize` (`{text, lens}` wrap; bare strings stay bare) | T2 | §3 | S | pending |
| T4 | Create `scripts/qrspi_critic_synthesize_test.py` (`check()`-style fixtures: all-pass, one-fail, dedupe, malformed) | T3 | §4 | M | pending |
| T5 | Run `python3 scripts/qrspi_critic_synthesize_test.py` (expect exit 0); confirm `synthesize` reuses landed `parse_critic_verdict` | T4 | §5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (the one pure Python helper + test landed and green). The lens-agent prompts in Slice 2 are an independent body of work (Markdown agent definitions) needing only the verdict contract `{pass, findings}` in context, not Slice 1's implementation detail. Fresh context for Slice 2.

## Session 2 — Slice 2: Lens agent prompts

**Load:** plan.md §Slice 2, structure.md §Contracts, plan.md §Slice 1 (verify result only — verdict contract `{pass, findings}`), note: `CRITIC_VERDICT_SCHEMA` is landed at qrspi-batch.js:416 (reference, do not re-add)
**Estimated context:** ~14% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Create `.claude/agents/qrspi-design-critic-completeness.md` (covers all ACs + answered questions; emits `{pass, findings}`) | T5 | §6 | M | pending |
| T7 | Create `.claude/agents/qrspi-design-critic-internal-consistency.md` (contradictions / dangling refs / contract mismatches) | T6 | §7 | S | pending |
| T8 | Create `.claude/agents/qrspi-design-critic-edge-alignment.md` (edge critic: ticket/research alignment, no scope drift) | T7 | §8 | S | pending |
| T9 | Create `.claude/agents/qrspi-design-critic-simplicity.md` (unjustified complexity / simpler alternative) | T8 | §9 | S | pending |
| T10 | Verify lens-reply parseability via the landed `parse_critic_verdict` ingest probe (expect a valid reply not coerced); confirm no new `CRITIC_VERDICT_SCHEMA` added | T9 | §10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (four lens prompts in place, referencing the landed schema). Slice 3 is the heaviest — the panel loop, `runPhase` dispatch, lenient config parser, `doDesign` rewiring, config surface, and end-to-end e2e — and needs the full `qrspi-batch.js` orchestration surface plus Slice 1/2 results in context. Fresh context for the wiring work.

## Session 3 — Slice 3: Panel loop + doDesign rewiring + config

**Load:** plan.md §Slice 3, structure.md §Contracts (`runCriticPanelLoop`, `parseCriticConfig`, `runPhase`), structure.md §New/Modified Types (`CriticConfig`, `runPhase`), structure.md §Reconciliation, structure.md §Decisions, structure.md §Risk Register, plan.md §Slice 1/2 (verify results)
**Estimated context:** ~30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Modify `qrspi-batch.js` — add `runCriticPanelLoop` (parallel lens fan-out → `parse_critic_verdict` ingest → `synthesize` → `next_action` → revise/converge/cap; returns `{residualFindings}`) | T10 | §11 | L | pending |
| T12 | Modify `qrspi-batch.js` — `runPhase` `if (criticConfig)` branch dispatches `lenses?.length ? runCriticPanelLoop : runCriticLoop` (no signature change; single-critic path unchanged) | T11 | §12 | S | pending |
| T13 | Modify `qrspi-batch.js` — add lenient `parseCriticConfig(text)` reading the top-level `critics` envelope, returning `.design` | T11 | §13 | M | pending |
| T14 | Modify `qrspi-batch.js` — `doDesign` replaces hard-coded `designCritic` with a config-built `{upstreamPath, maxRounds, lenses}` (config>default, drop unknown lenses, empty⇒default four); leave `residualFindings`/`criticBodyStep` lines unchanged | T12, T13 | §14 | M | pending |
| T15 | Modify `qrspi-batch.js` — per-round `log(...)` pass/fail/cap + `res.summary` panel fold | T14 | §15 | S | pending |
| T16 | Modify `.qrspi/config.example.json` — add optional documented `critics.design` block | T13 | §16 | S | pending |
| T17 | Document the design-phase eval before/after procedure (AC5) in the PR summary | T15 | §17 | S | pending |
| T18 | **Verify Slice 3** — e2e: flawed design ⇒ ≥1 revise then converge/cap; clean design ⇒ 0 revise spawns; cap writes residuals to PR body via landed `criticBodyStep`; no-config ⇒ single-critic-equivalent; config block overrides maxRounds/lenses | T15, T16 | §18 | M | pending |
| T19 | **Verify dispatch** — `doPlan`'s `planCritic` (no lenses) still routes to single-critic `runCriticLoop` (plan phase untouched) | T18 | §19 | S | pending |
| T20 | **Verify regression** — `python3 scripts/qrspi_critic_loop_test.py` and `python3 scripts/qrspi_pr_body_test.py` still exit 0 | T19 | §20 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. All slices implemented, e2e + dispatch + regression verified — ready for the PR phase.
