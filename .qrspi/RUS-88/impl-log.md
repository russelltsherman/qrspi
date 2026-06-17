# Implementation Log — Retire the fidelity-only edge critic (qrspi-critic / runCriticLoop)

## Session 1 — Slice 1

**Timestamp:** 2026-06-17T19:40:00Z
**Tasks completed:** Steps 1-4 (trace/re-locate), 5-8a (Python resolver), 9-21 (JS harness), 22-25 (deletions), 26-31e (tests + fixtures), 33-36 (config/docs sweep), 37-40 (verify checkpoints)
**Tasks failed:** none

**Tests:**

- `python3 scripts/run_tests.py` → 39 passed, 0 failed (was 40 suites; `qrspi_slice_critic_test.py` deleted with its module)
- `python3 scripts/qrspi_critics_config_test.py` → 46 passed (lockstep JS↔Python 2-key shape pinned)
- `python3 scripts/qrspi_contract_fixtures_consumer_test.py` → 22 passed (Node parser path, 2-key golden)
- `node --check .claude/workflows/qrspi-batch.js` → OK

**Resolved open questions / decisions:**

- **OQ2:** `scripts/qrspi_slice_critic.py` had NO consumer other than `sliceCriticDecide` + its own test (`git grep` + import scan confirmed). Per the decision rule, the module + test were DELETED (steps 24-25 applied).
- **perSliceFindings scope (Risk Register row 7):** every `perSliceFindings` assignment/read in `doImplementation` was per-slice-critic-only (the decl, the `[s.n] = sc.residualFindings` write, and the lowest-N-first splice loop). All removed; the coherence-findings → slice-1 splice (`spliceTargets` for `kind:'coherence'`) was KEPT (coherence critic survives).

**Changes (verifiable end-to-end):**

- `scripts/qrspi_critics_config.py` — deleted `EDGE_PHASES`, `resolve_edge_phase`; `resolve_critics` now returns `{design, implementation}`; `resolve_design` drops `gateBehindEdge`; `resolve_implementation` reduced to `{coherence: {enabled, maxRounds}}`. Module docstrings updated.
- `.claude/workflows/qrspi-batch.js` — `DEFAULT_CRITIC_PHASES` reduced to `{design (no gateBehindEdge), implementation: {coherence}}`; deleted `runCriticLoop`, `runSliceCritic`, `sliceCriticDecide`, `SLICE_DECIDE_SCHEMA`; `runPhase` critic gate is now `if (criticConfig?.lenses?.length)` (panel-only; no edge fallback, no gateBehindEdge short-circuit); removed the per-slice critic block + `perSliceFindings` in `doImplementation`; removed `questionsCritic`/`researchCritic`/`structureCritic`/`planCritic` builds and their criticMetrics/findings folds in `doDesign`/`doPlan`. Research's deterministic citation node-check is PRESERVED (rides a `nodeCheck`-only criticConfig, runs unconditionally). Stale comments swept.
- Deleted: `.claude/agents/qrspi-critic.md`, `.claude/skills/qrspi-critic/` (dir), `scripts/qrspi_slice_critic.py`, `scripts/qrspi_slice_critic_test.py`.
- Tests: rewrote `qrspi_critics_config_test.py` (dropped `TestResolveEdgePhase` + gateBehindEdge cases, added 2-key/no-edge-phase + panel/coherence-still-resolve assertions, updated lockstep + impl shape). Rewrote `EXPECTED_DEFAULT_CRITIC_PHASES` + discriminator (flips `implementation.coherence`) + partial-merge loop in `qrspi_contract_fixtures_consumer_test.py`. Updated key-set assertion in `qrspi_contract_fixtures_producer_test.py`.
- Fixtures: regenerated `critics/wellformed.json` (= serialized `default_phases()`) + `wellformed_consumer.json` (flips surviving `implementation.coherence.enabled`). `malformed.json`/`partial_merge.json` verified compatible (no edit).
- Config/docs: `.qrspi/config.example.json` critics block reduced to `design` + `implementation.coherence` (removed gateBehindEdge, four planning sub-blocks, impl top-level enabled/maxRounds, with updated comments). `docs/testing-dynamic-workflows.md` swept (`qrspi_slice_critic.py` → `qrspi_critics_config.py`; `qrspi-critic` → design panel + coherence pass). `CLAUDE.md`/`.claude/CLAUDE.md` had no critic prose to sweep.

**Verification of KEPT / NO-TOUCH surfaces:**

- `runCriticPanelLoop` and `runCoherenceCritic` function bodies confirmed BYTE-FOR-BYTE identical to HEAD (Python diff against `git show HEAD:`); only their preceding doc-comments were updated.
- `scripts/qrspi_critic_loop.py`, `scripts/qrspi_critic_metrics.py`, and the five `.claude/agents/qrspi-design-critic-*.md` show NO modification (`git status --porcelain` clean) — honored as NO-TOUCH (their docstrings retain historical `runCriticLoop` mentions, allowed by AC5 "intentional/historical").

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none (step 41 manual e2e is the uncovered harness-coupled seam — requires a live batch run with Linear, out of this agent's reach; the unit + contract-fixture suite is the primary gate per CLAUDE.md and is green).

**Notes for next session:**

- This is the only slice; no further slices.
- PR-body / post-merge notes to carry (per plan Rollback Notes — NOT code steps): (1) the live gitignored `.qrspi/config.json` retains inert `gateBehindEdge` + four planning-phase + `implementation` per-slice `enabled` keys; they are now silently ignored (no crash) but should be pruned by hand post-merge. (2) Confirm RUS-84 is formally Canceled and note the RUS-79 cancellation recommendation (human/Linear, no code impact).
