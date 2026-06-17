# PR: RUS-88 Retire the fidelity-only edge critic (runCriticLoop)

**Ticket:** RUS-88
**Design:** design.md @ 2026-06-17T00:00:00Z
**Structure:** structure.md @ 2026-06-17T00:00:00Z

## Summary

Removes the fidelity-only edge critic end-to-end: the `runCriticLoop` phase loop, the per-slice `runSliceCritic`/`sliceCriticDecide` path, the shared `qrspi-critic` agent + skill, the Python resolver's four edge-phase entries (`EDGE_PHASES`/`resolve_edge_phase`), and the `gateBehindEdge` lever. `runPhase` is reconciled to a single critic branch gated on `criticConfig?.lenses?.length` (panel only); any non-panel phase now falls through to the pre-existing ungated persist path, so every planning phase ships ungated. The design-critic **panel** (`runCriticPanelLoop` + five `qrspi-design-critic-*` lenses, incl. `edge-alignment`) and the whole-stack **coherence** pass (`runCoherenceCritic`) are kept byte-for-byte, as is the shared decision core (`qrspi_critic_loop.py`). Reviewer focus: (1) the `runPhase` gate change and confirmation no `critics.<phase>.enabled` reader survives the 6→2-key resolver shape change, and (2) that the KEPT panel/coherence surfaces are genuinely untouched (namesake-confusion risk between the deleted *edge critic* and the kept *edge-alignment lens*).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: Remove `runCriticLoop` + `qrspi-critic` agent + skill | `.claude/workflows/qrspi-batch.js` (delete `runCriticLoop`); deleted `.claude/agents/qrspi-critic.md`, `.claude/skills/qrspi-critic/SKILL.md` | `node --check .claude/workflows/qrspi-batch.js`; `git grep -n 'runCriticLoop'` (completeness) |
| AC2: Remove per-slice edge critic | `.claude/workflows/qrspi-batch.js` (delete `runSliceCritic`, `sliceCriticDecide`, `SLICE_DECIDE_SCHEMA`, the `implCriticCfg.enabled` slice block + its `perSliceFindings` plumbing); deleted `scripts/qrspi_slice_critic.py` | `scripts/run_tests.py` (broken-import gate; `qrspi_slice_critic_test.py` deleted with module) |
| AC3: Reconcile `runPhase` routing to ungated | `.claude/workflows/qrspi-batch.js` (`runPhase` gate → `criticConfig?.lenses?.length`; no edge fallback) | `scripts/qrspi_critics_config_test.py` (panel still resolves); `node --check` |
| AC4: Remove `gateBehindEdge` + edge config | `scripts/qrspi_critics_config.py` (delete `EDGE_PHASES`, `resolve_edge_phase`, four phase entries, `gateBehindEdge` from `resolve_design`); `.claude/workflows/qrspi-batch.js` (`.design` mirror + short-circuit); `.qrspi/config.example.json` | `scripts/qrspi_critics_config_test.py` (2-key shape, lockstep); `scripts/qrspi_contract_fixtures_consumer_test.py`; `scripts/qrspi_contract_fixtures_producer_test.py` |
| AC5: Tests updated + docs swept | `scripts/qrspi_critics_config_test.py`, `scripts/qrspi_contract_fixtures_*_test.py`; `scripts/fixtures/contract_seam/critics/wellformed*.json`; `docs/testing-dynamic-workflows.md`, `scripts/qrspi_critic_body.py` (docstring) | `scripts/run_tests.py` (39 suites green); `git grep -n 'runCriticLoop\|gateBehindEdge\|edge critic'` (only historical/intentional remain) |

## Changes by Slice

### Slice 1: Retire the edge critic end-to-end and reconcile to ungated

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +~80, -~450 (net 531 changed) |
| `scripts/qrspi_critics_config.py` | ⚠️ modified | 76 changed |
| `scripts/qrspi_critics_config_test.py` | ⚠️ modified | 139 changed |
| `scripts/qrspi_contract_fixtures_consumer_test.py` | ⚠️ modified | 40 changed |
| `scripts/qrspi_contract_fixtures_producer_test.py` | ⚠️ modified | 5 changed |
| `scripts/qrspi_critic_body.py` | ⚠️ modified (docstring sweep) | 19 changed |
| `.qrspi/config.example.json` | ⚠️ modified | 33 changed |
| `docs/testing-dynamic-workflows.md` | ⚠️ modified | 6 changed |
| `scripts/fixtures/contract_seam/critics/wellformed.json` | ⚠️ modified (regenerated) | 2 changed |
| `scripts/fixtures/contract_seam/critics/wellformed_consumer.json` | ⚠️ modified (regenerated) | 2 changed |
| `.claude/agents/qrspi-critic.md` | 🗑️ deleted | -52 |
| `.claude/skills/qrspi-critic/SKILL.md` | 🗑️ deleted | -23 |
| `scripts/qrspi_slice_critic.py` | 🗑️ deleted | -129 |
| `scripts/qrspi_slice_critic_test.py` | 🗑️ deleted | -93 |

## Testing Summary

- [x] Slice 1: full suite — `python3 scripts/run_tests.py` — 39 passed, 0 failed (was 40; `qrspi_slice_critic_test.py` deleted with its module)
- [x] Slice 1: resolver lockstep — `python3 scripts/qrspi_critics_config_test.py` — 46 passed (JS↔Python 2-key shape pinned)
- [x] Slice 1: contract fixtures — `python3 scripts/qrspi_contract_fixtures_consumer_test.py` — 22 passed (Node parser path, 2-key golden)
- [x] Slice 1: JS parse — `node --check .claude/workflows/qrspi-batch.js` — OK
- [x] AC5 completeness — `git grep -n 'runCriticLoop|gateBehindEdge|edge critic'` — only intentional/historical mentions remain
- [ ] Manual end-to-end: design+plan+implementation run with panel + coherence active and every planning phase ungated — NOT run (harness-coupled seam requiring a live Linear batch run, out of this agent's reach; the unit + contract-fixture suite is the primary gate per CLAUDE.md)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `scripts/qrspi_slice_critic.py` deletion (OQ2) | conditional — delete IFF no other consumer | deleted | `git grep` + import scan confirmed `sliceCriticDecide` + its own test were the only consumers; deletion condition satisfied |
| `scripts/qrspi_critic_body.py` | not enumerated in structure file list | docstring-only edit | Part of the AC5 doc sweep (stale `runCriticLoop`/edge-critic prose in the module docstring); no behavior change — the script still serves the kept panel/coherence loops |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Deleting a shared pure module breaks panel/coherence critics | mitigated — `qrspi_critic_loop.py`/`criticDecision`/`CRITIC_VERDICT_SCHEMA`/`recordCriticMetrics` confirmed NO-TOUCH; suite green | Revert the slice-1 commit (`b3269b2`) |
| `edge-alignment` panel lens deleted by namesake confusion | mitigated — five `qrspi-design-critic-*` agents confirmed unmodified (`git status --porcelain` clean) | Restore agent files from `main` |
| JS `runPhase`/`doImplementation` edits harness-coupled, uncovered by Python gate | accepted — verified via JS↔Python lockstep + contract fixtures + `node --check`; manual e2e NOT run (out of reach) | Revert slice-1 commit; run a manual batch e2e before relanding |
| RUS-84 lands a different routing line | void — RUS-84 abandoned (PRs #335/#336 closed unmerged, no `blockedBy` edge); built against `main` pre-RUS-84 form | n/a |
| 6→2-key shape change leaves a stray `critics.<phase>.enabled` reader → `undefined.enabled` crash | mitigated — all `questions`/`research`/`structure`/`plan` config builds + readers removed; lockstep + suite green | Revert slice-1 commit |
| Stale live `.qrspi/config.json` keys read as "critics still active" | accepted (low) — keys now inert (silently ignored, no crash); manual post-merge prune required | n/a — no code rollback; restore pruned keys if needed |
| `runSliceCritic`/`sliceCriticDecide` removal leaves orphan `perSliceFindings` or dangling import | mitigated — all per-slice `perSliceFindings` plumbing removed; coherence→slice-1 splice KEPT; `run_tests.py` green (no broken import) | Revert slice-1 commit |

## Open Items

- **Operator cleanup (manual, post-merge):** the live gitignored `.qrspi/config.json` retains inert `gateBehindEdge` + `questions`/`research`/`structure`/`plan` + `implementation` per-slice `enabled: true` keys. They are now silently ignored (no crash) but should be pruned by hand so the dead flags don't misrepresent active critics. The PR cannot edit a gitignored file.
- **Linear housekeeping (no code impact):** confirm RUS-84 is formally **Canceled** (PRs #335/#336 already closed unmerged) so a future batch run cannot resurrect a "wait on RUS-84" framing; and action the RUS-79 cancellation recommendation (it cannot tune a now-deleted critic).
- **Manual end-to-end run deferred:** the design+plan+implementation harness path (panel + coherence active, planning phases ungated) is the uncovered harness-coupled seam; run it on a live batch before relying on the autonomous loop.
