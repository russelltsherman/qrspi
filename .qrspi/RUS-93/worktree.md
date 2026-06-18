# Work Tree — Upgrade the /review-* advisory review family

**Plan basis:** plan.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T00:00:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T1 → T3 → T4 → T10 (Slice 1) → T29 → T30 → T31 → T32 → T33 → T34 → T35 → T40 (Slice 4) → T41 → T44 → T45 → T47 (Slice 5)

> Critical path = Slice 1 (synopsis rendering, a Slice-4 input) → Slice 4 (engine, gated on Slices 1+2+3) → Slice 5 (SKILL wrappers, gated on Slice 4). Slices 2 and 3 are off the critical path: both are independent of Slice 1 and complete before Slice 4 needs them, so they run in their own sessions without extending the longest chain. Length = 16 tasks.

## Session 1 — Slice 1: Honest synopsis rendering (AC1 + AC2)

**Load:** structure.md §Types (`HeadlineVerdict`, `ProposedDiffAppendix`), structure.md §Contracts (`render_synopsis`, `build_record`), plan.md §Slice 1
**Estimated context:** ~22%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add `pin_headline(round0_array) -> HeadlineVerdict dict` to `qrspi_review_synopsis.py` | — | §1.1 | S | pending |
| T2 | Add `diff_scratch_vs_original(original, scratch) -> ProposedDiffAppendix` to `qrspi_review_synopsis.py` | — | §1.2 | S | pending |
| T3 | Extend `render_synopsis` to emit per-lens finding text under count header | T1 | §1.3 | M | pending |
| T4 | Change `render_synopsis` signature to take `HeadlineVerdict` + `ProposedDiffAppendix`; append labeled fix-suggestion section | T2, T3 | §1.4 | M | pending |
| T5 | Extend `qrspi_critic_metrics.py` `build_record` to carry per-lens `findings: list[str]` | — | §1.5 | S | pending |
| T6 | Test: `cap_reached` panel renders surviving lens finding text | T3 | §1.6 | S | pending |
| T7 | Test: headline tracks round-0 verdict (round-0 FAIL + later PASS = FAIL headline) | T4 | §1.7 | S | pending |
| T8 | Test: proposed-diff appendix present, labeled suggestion, never reads as "passed" | T4 | §1.8 | S | pending |
| T9 | Test: ledger record per-lens entries carry `findings` text list | T5 | §1.9 | S | pending |
| T10 | **Verify Slice 1** — `run_tests.py synopsis && run_tests.py metrics` | T6, T7, T8, T9 | §1.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and verified. Slice 2 touches different files (`qrspi_critics_config.py`) and has no dependency on Slice 1 — fresh context to drop the synopsis-rendering working set.

## Session 2 — Slice 2: Per-phase review config + lensModel resolution (AC5)

**Load:** structure.md §Contracts (`resolve_review_config`, `ReviewConfig`), plan.md §Slice 2, MEMORY note "Config reader is single-top-level-key only"
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Add `_phase_critic_block(raw_config, phase)` reading whole `critics` object once (single-key workaround) | — | §2.11 | S | pending |
| T12 | Add `resolve_review_config(phase, raw_config) -> ReviewConfig`; default `maxRounds=2` for all phases (normalizes plan/impl 3→2) | T11 | §2.12 | M | pending |
| T13 | Wire `lensModel` resolution for plan/impl; `None` when unset (session-model fallback) | T12 | §2.13 | S | pending |
| T14 | Select per-phase `reviewLenses` from `DEFAULT_REVIEW_<PHASE>_LENSES`; keep batch `DEFAULT_DESIGN_LENSES` decoupled | T12 | §2.14 | S | pending |
| T15 | Test: `maxRounds==2` default per phase + explicit override honored | T12 | §2.15 | S | pending |
| T16 | Test: `lensModel` resolves for plan/impl (set→value, unset→None) | T13 | §2.16 | S | pending |
| T17 | Test: `reviewLenses` per phase == `DEFAULT_REVIEW_<PHASE>_LENSES`; regression: `DEFAULT_DESIGN_LENSES` unchanged | T14 | §2.17 | S | pending |
| T18 | **Verify Slice 2** — `run_tests.py critics_config && run_tests.py` (no batch critic regression) | T15, T16, T17 | §2.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete and verified. Slice 3 is independent (different file, `qrspi_review_agreement.py`) — fresh context.

## Session 3 — Slice 3: Post-decision agreement re-run path (AC6)

**Load:** structure.md §Contracts (`compute`, `recompute_with_decision`), plan.md §Slice 3, plan.md §Unverified Assumptions (OQ3)
**Estimated context:** ~15%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Add `recompute_with_decision(panel_pass, review_decision)` calling unchanged `compute` with present `reviewDecision` | — | §3.19 | M | pending |
| T20 | Add module docstring documenting v1 trigger = manual `/review-<phase>` re-invocation (OQ3, flagged Unverified) | T19 | §3.20 | S | pending |
| T21 | Test: `agree` when `reviewDecision==APPROVED` and `panel_pass` matches | T19 | §3.21 | S | pending |
| T22 | Test: `disagree` when present `reviewDecision` contradicts `panel_pass` | T19 | §3.22 | S | pending |
| T23 | Test: `pending` only when `reviewDecision` absent/`null` | T19 | §3.23 | S | pending |
| T24 | **Verify Slice 3** — `run_tests.py agreement` | T21, T22, T23 | §3.24 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slices 1–3 (all Slice-4 inputs) complete and verified. Slice 4 is large (JS engine + contract-seam fixtures + agent wiring) and explicitly depends on 1+2+3 — fresh context loads the converged contracts as references rather than full prior working sets.

## Session 4 — Slice 4: Deterministic review engine + contract-seam parsers (AC3 + AC4 + AC5 wiring)

**Load:** structure.md §Contracts (`ReviewRunEnvelope`, `RoundVerdict`, seam parsers), plan.md §Slice 4, plan.md §Unverified Assumptions (Agent spawn `model` param), `qrspi-batch.js` (meta-block + injected-globals + `Agent` spawn shape — reference), Slice 1 `render_synopsis`/`pin_headline`/`diff_scratch_vs_original` signatures (notes only), Slice 2 `resolve_review_config` signature (notes only)
**Estimated context:** ~38%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T25 | Create fixture `review_envelope/valid.json` (resolve→engine seam golden) | T18 | §4.25 | S | pending |
| T26 | Create fixture `review_envelope/null_lensmodel.json` (session-model fallback) | T18 | §4.26 | S | pending |
| T27 | Create fixture `round_panel/pass.json` (pre-reduction all-pass `[RoundVerdict]`) | T10 | §4.27 | S | pending |
| T28 | Create fixture `round_panel/findings.json` (`cap_reached`-shape, pass:false + findings) | T10 | §4.28 | S | pending |
| T29 | Create `qrspi_review_seam.py` producers: `build_review_envelope`, `serialize_round_panel` | T25, T26, T27, T28 | §4.29 | M | pending |
| T30 | Create `.claude/workflows/qrspi-review.js` scaffold (meta block, injected-globals, `run` entry) | T29 | §4.30 | M | pending |
| T31 | Add pure JSON-seam parsers `parse_review_envelope`, `parse_round_panel` (no I/O) | T30 | §4.31 | M | pending |
| T32 | Implement run sequence: resolve → capture `headRefOid` early → scratch-copy artifact | T31, T18 | §4.32 | M | pending |
| T33 | Implement round loop `0..maxRounds-1`: fan-out lenses threading `lensModel`; partition→synthesize→next_action | T32 | §4.33 | L | pending |
| T34 | Render synopsis via Slice-1 `render_synopsis` (round-0 headline + diff appendix); post ONE PR comment | T33, T10 | §4.34 | M | pending |
| T35 | Re-read `headRefOid` after post; fail loud on mismatch (propose-only terminal gate) | T34 | §4.35 | M | pending |
| T36 | Create `qrspi_review_seam_test.py`: producers emit both golden sets; document JS-parser consumer parity | T29 | §4.36 | S | pending |
| T37 | Wire `model` spawn-param seam in `qrspi-design-critic-design-review.md`; refresh stale `runCriticPanelLoop` note → engine | T33 | §4.37 | S | pending |
| T38 | Same model-seam wiring + stale-note refresh in `qrspi-plan-critic-plan-review.md` | T33 | §4.38 | S | pending |
| T39 | Same model-seam wiring + stale-note refresh in `qrspi-impl-critic-impl-review.md` | T33 | §4.39 | S | pending |
| T40 | **Verify Slice 4** — `run_tests.py review_seam` + manual e2e (synopsis posts, `headRefOid` byte-identical) | T35, T36, T37, T38, T39 | §4.40 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 4 (the engine) complete and verified. Slice 5 is doc/SKILL surgery + a destructive directory delete that depends only on the engine existing — fresh context drops the engine-implementation working set and keeps only "engine invocation contract" as a reference.

## Session 5 — Slice 5: SKILLs to thin wrappers + remove /review + dereference (AC4 + AC7)

**Load:** plan.md §Slice 5, plan.md §Rollback Notes (step 44 destructive delete), `qrspi-review.js` invocation contract `{ticket, phase}` (notes only from Slice 4)
**Estimated context:** ~16%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T41 | `review-design/SKILL.md` → thin wrapper (`phase:"design"`); drop loop prose + whole-stack cross-link | T40 | §5.41 | S | pending |
| T42 | `review-plan/SKILL.md` → thin wrapper (`phase:"plan"`); drop cross-link | T40 | §5.42 | S | pending |
| T43 | `review-implementation/SKILL.md` → thin wrapper (`phase:"impl"`); drop cross-link | T40 | §5.43 | S | pending |
| T44 | Delete `.claude/skills/review/` directory (destructive — see Rollback Notes) | T41, T42, T43 | §5.44 | S | pending |
| T45 | Update `.claude/CLAUDE.md`: delete `/review` blurb; refresh three per-stage blurbs to engine behavior | T44 | §5.45 | S | pending |
| T46 | Remove `/review` reference in `docs/testing-dynamic-workflows.md` | T44 | §5.46 | S | pending |
| T47 | **Verify Slice 5** — grep: no orphaned `/review`; no `runCriticPanelLoop`/`runCoherenceCritic`; manual: each `/review-*` invokes engine | T45, T46 | §5.47 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All 5 slices implemented and verified. End of work tree — proceed to PR phase.
