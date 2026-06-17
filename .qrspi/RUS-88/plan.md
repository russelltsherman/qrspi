# Implementation Plan — Retire the fidelity-only edge critic (qrspi-critic / runCriticLoop)

**Structure basis:** structure.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft
**Total steps:** 41 (+7 inserted sub-steps: 8a, 10a, 31a–31e — contract-fixture seam + `implementation` shape)

> One slice (structure rule 8 justified: the JS↔Python lockstep + shared-agent coupling admit no green intermediate state). Steps are ordered: **(A) re-confirm line numbers & resolve plan-phase open questions → (B) Python resolver → (C) JS harness → (D) deletions → (E) tests → (F) config/docs → (G) verify**. Line numbers in the structure/design are approximate (RUS-82 landed nearby); every JS/Python edit step is preceded by a re-locate (grep) step so the editor anchors on real text, not a drifted line number (design.md Risk Register row 4).

## Slice 1: Retire the edge critic end-to-end and reconcile to ungated

### Setup — re-confirm anchors and resolve plan-phase open questions

These trace steps are read-only and produce the facts that make the later edits atomic. They MUST run first; their findings (consumer lists, exact ternary text) feed the edit steps below.

1. Trace: `git grep -n 'qrspi_slice_critic\|sliceCriticDecide\|slice_critic' -- scripts/ .claude/` and `python3 -c "import scripts.qrspi_slice_critic"` import scan — resolve **OQ2**: does `scripts/qrspi_slice_critic.py` have any consumer other than `runSliceCritic`/`sliceCriticDecide`?
   - **Decision rule:** zero other consumers ⇒ delete the module + its test (steps 24-25 apply); any other consumer ⇒ mark `qrspi_slice_critic.py` NO-TOUCH and only remove the per-slice wiring in `qrspi-batch.js`.
2. Trace: `git grep -n 'perSliceFindings' -- .claude/workflows/qrspi-batch.js` — enumerate every assignment/read of `perSliceFindings`; classify each as **per-slice-critic-only** (remove) vs **shared-with-coherence** (keep). Records the exact scope for step 21 (design.md Risk Register row 7, OQ on `perSliceFindings`).
3. Re-locate: `git grep -n 'runCriticLoop\|gateBehindEdge\|lenses?.length\|runSliceCritic\|sliceCriticDecide\|implCriticCfg' -- .claude/workflows/qrspi-batch.js` against `main` HEAD — capture the **current** line numbers and the **exact ternary text** in `runPhase` (the design's `@739/@1499/@1478/@1955/@1387/@2130` are pre-edit estimates and may have drifted).
4. Re-locate: `git grep -n "critics\.\(questions\|research\|structure\|plan\)" -- .claude/workflows/qrspi-batch.js` — enumerate every `critics.<planning-phase>.enabled` reader so none is missed in step 17 (guards against `undefined.enabled` after the 6→2-key shape change; Risk Register row "stray reader").

### Core Logic — Python resolver (`scripts/qrspi_critics_config.py`)

Do Python first so the lockstep test has a stable target shape before the JS mirror is edited.

5. ⚠️ Modify `scripts/qrspi_critics_config.py` — delete the `EDGE_PHASES` constant (the list of the four planning-phase keys).
   - **Current:** `EDGE_PHASES = [...]` module-level list driving `resolve_edge_phase` iteration.
   - **After:** removed; no module-level edge-phase enumeration remains.
6. ⚠️ Modify `scripts/qrspi_critics_config.py` — delete the `resolve_edge_phase(...)` function.
   - **Current:** `def resolve_edge_phase(cfg, phase) -> {enabled, maxRounds}`.
   - **After:** function removed.
7. ⚠️ Modify `scripts/qrspi_critics_config.py` — remove the four `resolve_edge_phase`-built entries from `resolve_critics`.
   - **Current:** `resolve_critics(cfg) -> {questions, research, structure, plan, design, implementation}`.
   - **After:** `resolve_critics(cfg) -> {design, implementation}` (Contracts: 2-key map; Decision 3 Option A).
8. ⚠️ Modify `scripts/qrspi_critics_config.py` — delete `gateBehindEdge` from `resolve_design`.
   - **Current:** `resolve_design(...)` emits `{enabled, maxRounds, lenses, gateBehindEdge}` (gateBehindEdge resolved at ~178-180).
   - **After:** `resolve_design(...)` emits `{enabled, maxRounds, lenses}` — no `gateBehindEdge` key.
8a. ⚠️ Modify `scripts/qrspi_critics_config.py` — drop the now-dead per-slice fields from `resolve_implementation` so it returns only `{coherence: {enabled, maxRounds}}`.
   - **Current:** `resolve_implementation(...)` returns `{enabled, maxRounds, coherence: {enabled, maxRounds}}`; the top-level `enabled`/`maxRounds` drove ONLY the per-slice edge critic (`implCriticCfg.enabled` gate + `implCriticCfg.maxRounds` → `runSliceCritic`), both removed in step 16.
   - **After:** `resolve_implementation(...)` returns `{coherence: {enabled, maxRounds}}` — matches structure.md Modified Types ("implementation loses its per-slice edge-critic sub-shape but retains coherence") and the design's `{design, implementation}`-minus-per-slice shape. **Precondition:** step 16 must have removed every top-level `implementation.enabled`/`.maxRounds` reader (confirmed by step 2's trace: only `.coherence.*` survives in `doImplementation`); a stray reader would now throw `undefined.enabled` — guard with the grep checkpoint (step 39a).

### Core Logic — JS harness (`.claude/workflows/qrspi-batch.js`)

Anchor each edit on the text confirmed in steps 3-4, not the estimated line numbers.

9. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — delete the `.design` mirror's `gateBehindEdge` key in `DEFAULT_CRITIC_PHASES` (~638).
   - **Current:** `DEFAULT_CRITIC_PHASES.design = { ...lenses..., gateBehindEdge: {...} }`.
   - **After:** `.design` carries only the panel fields (no `gateBehindEdge`); mirrors the new `resolve_design` shape.
10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — delete the four planning-phase keys (`questions`/`research`/`structure`/`plan`) from `DEFAULT_CRITIC_PHASES` so the JS mirror is `{design, implementation}` (lockstep with step 7).
10a. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — reduce the `DEFAULT_CRITIC_PHASES.implementation` mirror (~641) to `{ coherence: { enabled: false, maxRounds: 2 } }`, dropping the top-level `enabled`/`maxRounds` keys (lockstep with step 8a; the lockstep test in step 30 compares this mirror field-for-field against `default_phases()`).
   - **Current:** `implementation: { enabled: false, maxRounds: 2, coherence: { enabled: false, maxRounds: 2 } }`.
   - **After:** `implementation: { coherence: { enabled: false, maxRounds: 2 } }`.
11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — delete the `runCriticLoop` function (~739-836).
    - **Current:** `function runCriticLoop(...) { ... } // spawns qrspi-critic per round, returns {ok, residualFindings, metrics}`.
    - **After:** function removed; no definition remains (verified by grep in step 38).
12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `runPhase`, replace the `lenses?.length` ternary with a single panel-only gate (Decision 1, Option A).
    - **Current:** `criticConfig.lenses?.length ? runCriticPanelLoop(...) : runCriticLoop(...)` (the ternary at ~1497-1499, exact text from step 3).
    - **After:** `if (criticConfig?.lenses?.length) { ...runCriticPanelLoop... }` — non-panel `criticConfig` falls through to the existing ungated `persistArtifact` path; no edge fallback branch (Contracts: `runPhase` critic-block gate).
13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — delete the `gateBehindEdge` short-circuit in `runPhase` (~1478-1493).
    - **Current:** `if (criticConfig.gateBehindEdge?.enabled) { ...short-circuit... }`.
    - **After:** block removed; no `gateBehindEdge` reader in JS.
14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — delete the `runSliceCritic` function (~1955).
    - **Current:** `function runSliceCritic(...) { ... } // per-slice edge critic loop + qrspi_revise_amend reviser`.
    - **After:** function removed (AC2).
15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — delete the `sliceCriticDecide` shim (~1387).
    - **Current:** `function sliceCriticDecide(...) { ... }`.
    - **After:** function removed; no remaining caller after step 14.
16. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove the `implCriticCfg.enabled`-gated per-slice block in `doImplementation` (~2130-2147) and any `implCriticCfg` derivation feeding only it.
    - **Current:** `if (implCriticCfg.enabled) { ...runSliceCritic per slice... }`.
    - **After:** slice loop ships each slice with no edge-fidelity judgment; `runCoherenceCritic` seam pass untouched (AC2).
17. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove **every** `critics.questions`/`research`/`structure`/`plan` reader enumerated in step 4 (the config builds in `doDesign`/`doPlan` plus any `.enabled` access).
    - **Current:** `doDesign` builds `questionsCritic`/`researchCritic`; `doPlan` builds `structureCritic`/`planCritic`; each read via `critics.<phase>.enabled`.
    - **After:** no `critics.<planning-phase>` access survives (guards `undefined.enabled`; Decision 3, Risk Register).
18. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove the `out.criticMetrics`/PR-body summary folds for the four retired planning-phase critics and for `runCriticLoop`'s residuals.
    - **Current:** `out.criticMetrics` array folds in `questionsCritic`/`researchCritic`/`structureCritic`/`planCritic` metrics; summary appends their residual findings.
    - **After:** only surviving critic records (design panel, coherence) fold in; the `undefined`-filter behavior is preserved for those.
19. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove the `doDesign`/`doPlan` plumbing that passed the retired critic configs into `runPhase` (the now-unused local critic-config objects).
    - **Current:** `runPhase(..., questionsCritic)` / `runPhase(..., structureCritic)` etc.
    - **After:** those phases call `runPhase` with `criticConfig = undefined` (ungated), matching today's disabled-phase path (AC3, Decision 1).
20. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove any now-orphaned `qrspi_slice_critic.py` invocation/import string left by step 14 (the spawn path the per-slice loop used).
    - **Current:** a `python3 scripts/qrspi_slice_critic.py ...` call or path reference inside the removed slice block.
    - **After:** no reference to `qrspi_slice_critic.py` in the JS.
21. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — remove the `perSliceFindings` assignments/reads classified **per-slice-critic-only** in step 2; leave any classified shared-with-coherence.
    - **Current:** `perSliceFindings` accumulated in the per-slice critic block and folded into the impl summary.
    - **After:** only coherence-owned findings plumbing remains (scope fixed by step 2's trace; Risk Register row 7).

### Deletions

22. 🗑️ Delete `.claude/agents/qrspi-critic.md` — the shared edge-critic agent definition; no consumer remains after steps 11 and 14 (AC1, Decision 2 Option A).
23. 🗑️ Delete `.claude/skills/qrspi-critic/` — the slash-command wrapper directory for the deleted agent (AC1).
24. 🗑️ Delete `scripts/qrspi_slice_critic.py` — **only if step 1 found no other consumer**; otherwise SKIP this step and keep the module NO-TOUCH (OQ2 resolution).
25. 🗑️ Delete `scripts/qrspi_slice_critic_test.py` — **conditional on step 24** (delete with its module; SKIP if step 24 was skipped).

### Tests

26. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — delete the `TestResolveEdgePhase` class (covers the removed `resolve_edge_phase`).
27. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — delete the four `gateBehindEdge` test cases and the edge-phase toggle test.
28. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add an assertion that `resolve_critics(cfg)` keys are exactly `{design, implementation}` for a no-lenses config (no edge phase emitted).
29. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add an assertion that the design panel + `implementation.coherence` still resolve (lenses present ⇒ panel resolves; coherence sub-shape retained).
30. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — update the JS-mirror lockstep test (~288-318, field-for-field vs `default_phases()`) to the new shape: `DEFAULT_CRITIC_PHASES` keys equal the resolver's `{design, implementation}`, `.design` has no `gateBehindEdge`, and `.implementation` carries only `{coherence: {enabled, maxRounds}}` (no top-level `enabled`/`maxRounds`, lockstep with steps 8a/10a). Also update `test_default_phases_matches_empty_resolution` (~367) which compares `default_phases()` to `resolve_critics({})[0]` — it passes structurally but its expectation must reflect 2 keys.

The remaining test steps cover the **contract-fixture seam** (`scripts/qrspi_contract_fixtures_*_test.py` + `scripts/fixtures/contract_seam/critics/*.json`). This seam is the JS↔Python contract gate per CLAUDE.md and is far more entangled than a single `gateBehindEdge` line: `EXPECTED_DEFAULT_CRITIC_PHASES` is a full 6-key golden compared by two consumer tests, and the producer test pins both the exact key-set and `wellformed.json == default_phases()`. All must move to the 2-key shape together or step 32 fails.

31. ⚠️ Modify `scripts/qrspi_contract_fixtures_consumer_test.py` — rewrite the `EXPECTED_DEFAULT_CRITIC_PHASES` constant (~72-93) to the 2-key shape: drop the `questions`/`research`/`structure`/`plan` entries, drop `gateBehindEdge` from `design`, and reduce `implementation` to `{coherence: {enabled, maxRounds}}` (lockstep with steps 8a/10a). This is NOT a one-line assertion edit — the constant is the golden consumed by `test_critics_malformed_defaults` (~236) + its per-phase loop (~254) and is the base of `test_critics_wellformed_accepted` (~149).
    - **After:** `{design: {enabled, maxRounds, lenses, candidates, digest}, implementation: {coherence: {enabled, maxRounds}}}`.
31a. ⚠️ Modify `scripts/qrspi_contract_fixtures_consumer_test.py` — re-choose the `test_critics_wellformed_accepted` discriminator. It currently overrides `"questions": {"enabled": True}` so the parsed value differs from the all-defaults golden; `questions` is no longer a phase. Flip a SURVIVING key instead (e.g. `"implementation": {"coherence": {"enabled": True, "maxRounds": 2}}`), matching the re-authored `wellformed_consumer.json` (step 31c); the `assertNotEqual(result, EXPECTED_DEFAULT_CRITIC_PHASES)` discriminator guard (~166) must still hold.
31b. ⚠️ Modify `scripts/fixtures/contract_seam/critics/wellformed.json` — regenerate to the 2-key envelope so it byte-equals the serialized `default_phases()` (this fixture is the PRODUCER golden, pinned by step 31e). Drop the four planning phases + `gateBehindEdge`; reduce `implementation` to `{coherence}`.
31c. ⚠️ Modify `scripts/fixtures/contract_seam/critics/wellformed_consumer.json` — 2-key shape, but flip the SAME surviving key chosen in step 31a (not `questions`) so the consumer fixture differs from the all-defaults golden (preserving the test's fail-open-vs-real-parse discriminator).
31d. Verify `scripts/fixtures/contract_seam/critics/{malformed,partial_merge}.json` — `malformed.json` (`"phases":"not-an-object"`) needs no edit (it fails open to the golden, now 2-key, via the EXPECTED constant). `partial_merge.json` (`{"design":{"enabled":true}}`) carries no planning-phase keys; confirm any consuming assertion of its merged output reflects the 2-key shape.
31e. ⚠️ Modify `scripts/qrspi_contract_fixtures_producer_test.py` — in `test_critics` (~139-150), change the asserted top-level key-set (~148) from `{questions, research, design, structure, plan, implementation}` to `{design, implementation}`; the `json.dumps(env)+"\n" == wellformed.json` equality (~150) then passes once step 31b regenerates the golden.
32. Run: `python3 scripts/run_tests.py`
    - **Expected:** suite green; the lockstep + contract-fixture tests pass against the new 2-key shape (primary gate for the harness-coupled JS edits, per CLAUDE.md).

### Config and documentation sweep

33. ⚠️ Modify `.qrspi/config.example.json` — remove the `gateBehindEdge` block, the four planning-phase critic sub-blocks (`questions`/`research`/`structure`/`plan`), and their explanatory `$comment` strings (AC4). Keep `design.lenses` + `implementation.coherence`.
34. ⚠️ Modify `CLAUDE.md` — revise critic/lifecycle prose that references the edge critic / `runCriticLoop` / per-slice edge critic / `gateBehindEdge`; leave intentional/historical mentions (AC5; editorial per-occurrence judgment).
35. ⚠️ Modify `.claude/CLAUDE.md` — same sweep as step 34 for the project-scoped copy.
36. ⚠️ Modify `docs/*.md` — scan (notably `docs/testing-dynamic-workflows.md` and `docs/qrspi-pr-gated-lifecycle-design.md`) and revise stale edge-critic / `runCriticLoop` / `gateBehindEdge` mentions; preserve intentional/historical references (AC5).

### Verify Slice 1

37. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] Suite exits 0 (lockstep + contract-fixture tests prove the JS↔Python 6→2-key shape change is consistent).
38. **Checkpoint:** `git grep -n 'runCriticLoop\|gateBehindEdge\|edge critic'`
    - [ ] Returns only intentional/historical mentions — no live code path or stale doc reference (AC5 completeness check).
39. **Checkpoint:** `git grep -nE "critics\.(questions|research|structure|plan)" -- .claude/workflows/qrspi-batch.js`
    - [ ] Returns nothing — no surviving planning-phase reader that could throw `undefined.enabled` after the shape change.
39a. **Checkpoint:** `git grep -nE "implCriticCfg\.(enabled|maxRounds)" -- .claude/workflows/qrspi-batch.js`
    - [ ] Returns nothing — after step 8a drops the top-level `implementation.enabled`/`.maxRounds`, only `implCriticCfg.coherence.*` may remain (guards the same `undefined`-access class introduced by the `implementation`-shape reduction).
40. **Checkpoint:** `git grep -n 'runCriticPanelLoop\|runCoherenceCritic' -- .claude/workflows/qrspi-batch.js && git status --porcelain scripts/qrspi_critic_loop.py .claude/agents/qrspi-design-critic-*.md`
    - [ ] `runCriticPanelLoop` and `runCoherenceCritic` still present; `qrspi_critic_loop.py` and the five `qrspi-design-critic-*` agents show **no** modification (KEPT/NO-TOUCH surfaces unchanged — Risk Register rows 1-2).
41. **Checkpoint (manual e2e):** run a design+plan+implementation pass on a scratch ticket.
    - [ ] Completes with the design panel + coherence pass active and every planning phase ungated (the uncovered harness-coupled seam — Risk Register row 3).

---

## Rollback Notes

- **Steps 5-21 (Python + JS edits):** pure source changes on the `RUS-88/slice-1` branch; revert by `gt`-reverting the slice commit (no migration, no persisted state). Two cross-file contracts must move together or their guard tests fail (intended): (a) the 6→2-key resolver shape — revert Python (5-8) and JS mirror (9-10) together (lockstep test, step 30); (b) the `implementation` per-slice shape reduction — revert Python (8a) and JS mirror (10a) together with the fixtures/EXPECTED (31, 31b, 31c) or the lockstep + contract-fixture tests fail.
- **Steps 22-25 (deletions):** recoverable from git history; if step 1 mis-traced a consumer, restoring `scripts/qrspi_slice_critic.py`/`_test.py` from `main` and reverting steps 14-16/20-21 re-enables the per-slice path. Confirm step 1's trace before deleting.
- **Steps 33-36 (config/docs):** non-functional; `.qrspi/config.example.json` is a committed template — revert restores the removed sub-blocks. No live config is touched (the gitignored `.qrspi/config.json` is out of PR scope).
- **Operator cleanup (NOT a step — PR-body note + post-merge task):** the live gitignored `.qrspi/config.json` retains inert `gateBehindEdge` + four planning-phase + `implementation` per-slice `enabled: true` keys after merge. They become silently-ignored (no crash), but must be pruned by hand so they don't misrepresent active critics. This PR cannot edit a gitignored file; record it in the PR body and as a tracked post-merge task (design.md §Delta → Operator cleanup).
- **Linear housekeeping (NOT a step — PR-body note):** confirm RUS-84 is formally Canceled (PRs #335/#336 closed unmerged; no `blockedBy` edge) and note the RUS-79 cancellation recommendation; both are human/Linear actions with no code impact (design.md OQ3/OQ4).
