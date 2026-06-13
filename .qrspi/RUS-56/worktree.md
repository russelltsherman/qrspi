# Work Tree — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Plan basis:** plan.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T0 → T1 → T2 → T4 → T6 → T7 → T8 → T9 → T11 → T12 → T13 → T14 → T15 → T16 (14 tasks)

## Session 1 — Slice 1: Pure synthesis + body helpers (Python firewall)

**Load:** plan.md §Slice 1, plan.md §Pre-build verification, structure.md §Contracts, structure.md §New Types (`SynthesizedVerdict`, `LensVerdict`)
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T0 | Pre-build verification (reads only): confirm `parse_critic_verdict`/`next_action`, `compose_message`, `parallel()`/`agent()`, and the `doDesign` config path signatures match structure.md; stop on mismatch | — | §Pre-build | S | pending |
| T1 | Create `scripts/qrspi_critic_synthesize.py` module shell importing `parse_critic_verdict` | T0 | §1.1 | S | pending |
| T2 | Implement `synthesize(verdicts) -> SynthesizedVerdict` (coerce fail-closed, all-pass AND, order-preserving deduped union) | T1 | §1.2 | M | pending |
| T3 | Add optional lens-tagging in `synthesize` (`{text, lens}` wrap; bare strings stay bare) | T2 | §1.3 | S | pending |
| T4 | Create `scripts/qrspi_critic_body.py` CLI (reads residual findings + finalize message, splices via `compose_message`) | T0 | §1.4 | M | pending |
| T5 | Add empty-findings short-circuit to `qrspi_critic_body.py` (idempotent no-op body) | T4 | §1.5 | S | pending |
| T6 | Create `scripts/qrspi_critic_synthesize_test.py` (`check()`-style fixtures: all-pass, one-fail, dedupe, malformed) | T3 | §1.6 | M | pending |
| T7 | Run `python3 scripts/qrspi_critic_synthesize_test.py` (expect exit 0) | T6 | §1.7 | S | pending |
| T8 | Create `scripts/qrspi_critic_body_test.py` (`check()`-style: empty, single, multi-line, idempotent re-splice) | T5 | §1.8 | M | pending |
| T9 | Run `python3 scripts/qrspi_critic_body_test.py` (expect exit 0) | T8 | §1.9 | S | pending |
| T10 | **Verify Slice 1** — checkpoint: both test files exit 0; one-fail⇒`pass:false`+deduped union; `synthesize` reuses landed `parse_critic_verdict` | T7, T9 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (pure Python helpers + tests landed and green). The lens-agent prompts in Slice 2 are an independent body of work (Markdown agent definitions + verdict schema), needing none of Slice 1's implementation detail in context — only the verdict contract. Fresh context for Slice 2.

## Session 2 — Slice 2: Lens agent prompts + verdict schema

**Load:** plan.md §Slice 2, structure.md §Delta (item a), structure.md §Contracts, plan.md §Slice 1 (verify result only — verdict contract `{pass, findings}`)
**Estimated context:** ~16% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Create `.claude/agents/qrspi-design-critic-completeness.md` (covers all ACs + answered questions; emits `{pass, findings}`) | T10 | §2.11 | M | pending |
| T12 | Create `.claude/agents/qrspi-design-critic-internal-consistency.md` (contradictions / dangling refs / contract mismatches) | T11 | §2.12 | S | pending |
| T13 | Create `.claude/agents/qrspi-design-critic-edge-alignment.md` (edge critic: ticket/research alignment, no scope drift) | T12 | §2.13 | S | pending |
| T14 | Create `.claude/agents/qrspi-design-critic-simplicity.md` (unjustified complexity / simpler alternative) | T13 | §2.14 | S | pending |
| T15 | Modify `qrspi-batch.js` — add `CRITIC_VERDICT_SCHEMA` constant only (no loop wiring) | T14 | §2.15 | S | pending |
| T16 | Verify lens-reply parseability via `parse_critic_verdict` ingest probe | T15 | §2.16 | S | pending |
| T17 | Run `python3 -c` parse-probe on a representative `{pass, findings}` reply (expect valid not coerced) | T16 | §2.17 | S | pending |
| T18 | **Verify Slice 2** — checkpoint: single lens agent against sample `design.md` parses; four prompts wire correct upstream inputs; `CRITIC_VERDICT_SCHEMA` exists, no panel-loop wiring yet | T17 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete (four lens prompts + verdict schema in place). Slice 3 is the heaviest slice — the panel loop, `runPhase`/`doDesign` wiring, config surface, PR-body splice, and end-to-end e2e — and needs the full `qrspi-batch.js` orchestration surface plus Slice 1/2 results in context. Fresh context to stay under budget for the wiring work.

## Session 3 — Slice 3: Panel loop + doDesign wiring + config + PR-body splice

**Load:** plan.md §Slice 3, structure.md §Contracts (`runCriticPanelLoop`, `runPhase`), structure.md §New/Modified Types (`CriticConfig`, `runPhase`), structure.md §Delta (items c–f), plan.md §Slice 1 (verify result), plan.md §Slice 2 (verify result), structure.md §Decisions 1–4, structure.md §Risk Register
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Modify `qrspi-batch.js` — extend `runPhase` with optional trailing `criticConfig`, guarded by `if (criticConfig)` | T18 | §3.19 | M | pending |
| T20 | Modify `qrspi-batch.js` — add `runCriticPanelLoop` (parallel lens fan-out → ingest → synthesize → next_action → revise/converge/cap) | T19 | §3.20 | L | pending |
| T21 | Modify `qrspi-batch.js` — `doDesign` reads `critics.design`, builds `CriticConfig` (config>default, drop unknown lenses, empty⇒default four) | T20 | §3.21 | M | pending |
| T22 | Modify `qrspi-batch.js` — splice cap-reached residual findings into design finalize commit via `qrspi_critic_body.py` before `gt submit` | T21 | §3.22 | M | pending |
| T23 | Modify `qrspi-batch.js` — add per-round `log(...)` pass/fail/cap lines and fold panel summary into `res.summary` | T22 | §3.23 | S | pending |
| T24 | Modify `.qrspi/config.example.json` — add optional documented `critics.design` block | T21 | §3.24 | S | pending |
| T25 | Document the design-phase eval before/after procedure (AC5) in PR summary / a doc | T23 | §3.25 | S | pending |
| T26 | **Verify Slice 3** — e2e checkpoint: flawed design triggers ≥1 revise then converges/caps; clean design ⇒ 0 revise spawns; cap writes residual findings to PR body; no-config reproduces today's behavior; config block overrides maxRounds/lenses | T23, T24 | §3.26 | M | pending |
| T27 | **Verify Slice 3 regression** — `python3 scripts/qrspi_critic_loop_test.py` and `python3 scripts/qrspi_pr_body_test.py` still exit 0 | T26 | §3.27 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Final session. All slices implemented, e2e and regression verified — ready for the PR phase.
