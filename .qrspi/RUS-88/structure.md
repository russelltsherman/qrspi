# Structure Outline — Retire the fidelity-only edge critic (qrspi-critic / runCriticLoop)

**Design basis:** design.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## New Types

None. This ticket is a removal/refactor; no new data shapes are introduced.

## Modified Types

- `resolve_critics(...) -> dict` return shape (`scripts/qrspi_critics_config.py`) — changes from a 6-key map `{questions, research, structure, plan, design, implementation}` to a 2-key map `{design, implementation}` (ref: design.md §Delta, Decision 3). `design` loses the `gateBehindEdge` field; `implementation` loses its per-slice edge-critic sub-shape but retains `coherence`.
- JS `DEFAULT_CRITIC_PHASES` (`.claude/workflows/qrspi-batch.js:638`) — `.design` mirror loses the `gateBehindEdge` key; the four planning-phase entries are no longer built/read (ref: design.md §Delta).

## Contracts

These are the cross-cutting interfaces whose shape change ripples across both the Python and JS sides — they are the lockstep boundary that forces the work into one slice.

- `resolve_critics(cfg): { design, implementation }` — Python resolver now emits exactly two phase keys; the JS-mirror lockstep test in `qrspi_critics_config_test.py` pins this shape against the JS `DEFAULT_CRITIC_PHASES`.
- `runPhase(...)` critic-block gate — `if (criticConfig?.lenses?.length)` → `runCriticPanelLoop`; otherwise the entire critic block is skipped and `persistArtifact` is the sole gate (Decision 1, Option A). No edge fallback branch.
- `runCriticPanelLoop(...): { ok, ... }` — KEPT, byte-for-byte unchanged; the only surviving `lenses`-carrying critic path.
- `runCoherenceCritic(...)` — KEPT, byte-for-byte unchanged (whole-stack pass, independent of the edge critic).
- `criticDecision` / `CRITIC_VERDICT_SCHEMA` / `recordCriticMetrics` (`scripts/qrspi_critic_loop.py`) — KEPT; shared by the design panel + coherence pass. NO-TOUCH.
- The five `qrspi-design-critic-*` lens agents (incl. `edge-alignment`) — KEPT. NO-TOUCH (namesake-confusion risk; see design.md Risk Register).

## Slice 1: Retire the edge critic end-to-end and reconcile to ungated

**Goal:** Delete the fidelity-only edge critic (loop, per-slice critic, shared agent/skill, resolver edge-phase surface, `gateBehindEdge`) and reconcile `runPhase` so non-panel phases persist ungated, with the test suite green and the docs swept. Delivers the complete AC1–AC5 behavior as one verifiable end-to-end change: the harness runs design→plan→implementation with the panel + coherence critics intact and every planning phase ungated.

**Why one slice (not split):** The Python resolver shape change (6→2 keys) and the JS config-builder/reader removal are bound by the JS↔Python lockstep test in `qrspi_critics_config_test.py` — changing either side alone fails that test, so they cannot be verified independently. Deleting the shared `qrspi-critic` agent requires BOTH its consumers (`runCriticLoop`, `runSliceCritic`) removed first (Decision 2, Option A), coupling AC1 and AC2. The doc sweep and `git grep` completeness check are the final validation step of the same removal, not separable work. There is no intermediate state that compiles, passes tests, and is independently meaningful. File count is justified by genuine mutual dependence (rule 8).

**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — delete `runCriticLoop` (≈739-836); change the `runPhase` critic gate to `criticConfig?.lenses?.length` (replacing the ternary at ≈1497-1499) so non-panel configs fall through to ungated persist; delete the `gateBehindEdge` short-circuit (≈1478-1493) and the `.design` mirror key (638); delete `runSliceCritic` (≈1955) and `sliceCriticDecide` (≈1387); remove the `implCriticCfg.enabled` slice block (≈2130-2147) and its `perSliceFindings` plumbing; remove `questionsCritic`/`researchCritic`/`structureCritic`/`planCritic` config builds in `doDesign`/`doPlan`, their `out.criticMetrics`/summary folds, and **every** `critics.<phase>.enabled` reader (no surviving `undefined.enabled` access).
- ⚠️ `scripts/qrspi_critics_config.py` — delete `EDGE_PHASES`, `resolve_edge_phase`, the four phase entries in `resolve_critics`, and `gateBehindEdge` from `resolve_design`; `resolve_critics` returns `{design, implementation}`.
- ⚠️ `scripts/qrspi_critics_config_test.py` — drop `TestResolveEdgePhase`, the four `gateBehindEdge` cases, the edge-phase toggle test; add assertions pinning "no lenses ⇒ resolver emits no edge phase / panel + coherence still resolve"; update the JS-mirror lockstep test (and `test_default_phases_matches_empty_resolution`) to the 2-key shape with `.implementation` reduced to `{coherence}`.
- ⚠️ `scripts/qrspi_contract_fixtures_consumer_test.py` — rewrite the 6-key `EXPECTED_DEFAULT_CRITIC_PHASES` golden to the 2-key shape (drop the four planning phases + `gateBehindEdge`, reduce `implementation` to `{coherence}`); re-choose the `test_critics_wellformed_accepted` discriminator (it currently flips `questions`, now gone) to a surviving key.
- ⚠️ `scripts/qrspi_contract_fixtures_producer_test.py` — `test_critics`: change the asserted top-level key-set to `{design, implementation}` (the `wellformed.json == default_phases()` equality follows from the regenerated golden).
- ⚠️ `scripts/fixtures/contract_seam/critics/wellformed.json` + `wellformed_consumer.json` — regenerate to the 2-key shape (golden = `default_phases()`; consumer flips a surviving key). `malformed.json` / `partial_merge.json` need no shape edit (verify).
- ⚠️ `.qrspi/config.example.json` — remove `gateBehindEdge`, the four planning-phase critic sub-blocks, and their explanatory `$comment` strings.
- 🗑️ `.claude/agents/qrspi-critic.md` — delete (no remaining consumer once both AC1/AC2 paths are gone).
- 🗑️ `.claude/skills/qrspi-critic/` — delete (directory; the slash-command wrapper for the deleted agent).
- 🗑️ `scripts/qrspi_slice_critic.py` — delete IFF it has no other consumer (resolve OQ2 during plan; trace `sliceCriticDecide`/per-slice-decide imports first).
- 🗑️ `scripts/qrspi_slice_critic_test.py` — delete with its module.
- ⚠️ `CLAUDE.md` + `.claude/CLAUDE.md` — revise critic/lifecycle prose that references the edge critic / `runCriticLoop` / per-slice edge critic / `gateBehindEdge`.
- ⚠️ `docs/*.md` — scan and revise edge-critic / `runCriticLoop` / `gateBehindEdge` mentions (notably testing-dynamic-workflows + PR-gated-lifecycle docs); leave intentional/historical mentions.

Note: This list exceeds 10 files, but every entry is mutually dependent through the lockstep contract and the shared-agent coupling — there is no testability boundary at which a subset can be verified independently (rule 8). Splitting would produce a non-green intermediate state.

**Verification:**

- [ ] `python3 scripts/run_tests.py` is green (the lockstep + contract-fixture tests prove the JS↔Python shape change is consistent; this is the primary gate for the harness-coupled JS edits per CLAUDE.md).
- [ ] `git grep -n 'runCriticLoop\|gateBehindEdge\|edge critic'` returns only intentional/historical mentions (AC5 completeness check).
- [ ] No `critics.questions\|research\|structure\|plan` reader remains in `qrspi-batch.js` (grep) — guards against `undefined.enabled` crash from the 6→2-key shape change.
- [ ] `runCriticPanelLoop`, `runCoherenceCritic`, `qrspi_critic_loop.py`, the five `qrspi-design-critic-*` agents are unchanged (grep / diff confirms no edits to KEPT surfaces).
- [ ] Manual end-to-end: a design+plan+implementation run completes with the design panel + coherence pass active and every planning phase ungated (the uncovered harness-coupled seam, per Risk Register).

**Context cost:** L
**Depends on:** none

---

## Unverified Assumptions

- **Exact line numbers may have drifted.** The design's Delta cites line numbers (`runCriticLoop@739`, ternary@1499, `gateBehindEdge`@1478-1493, etc.) against `main`'s pre-RUS-84 form, but flags that RUS-82 landed nearby. The implementer must re-confirm the ternary text and all line ranges against `main` HEAD immediately before editing (design.md Risk Register row 4). Line numbers in this structure are approximate.
- **`scripts/qrspi_slice_critic.py` deletion is conditional (OQ2).** Whether the module is deleted outright or has another consumer is not resolved in the design; it must be traced during plan. If a consumer exists, the file becomes a NO-TOUCH and only the per-slice wiring in `qrspi-batch.js` is removed.
- **`perSliceFindings` plumbing scope.** The design says to remove `perSliceFindings` "tied only to it" — the exact extent (which assignments/reads in `doImplementation` are exclusive to the per-slice critic vs shared with coherence) is not enumerated to concrete code and must be traced during plan (design.md Risk Register row 7).
- **Documentation sweep is judgment-bound, not enumerated.** The design names `CLAUDE.md`, `.claude/CLAUDE.md`, and "`docs/*.md` (notably …)" but does not list every file/line to edit; "intentional/historical mentions" vs "stale" is a per-occurrence editorial decision verified by `git grep`, not a mechanical map.
- **Operator cleanup of live `.qrspi/config.json` is out of PR scope (manual).** The gitignored live config's inert `gateBehindEdge` + four planning-phase + per-slice `enabled: true` keys cannot be committed; this must be recorded as a PR-body note + a tracked post-merge task, not implemented in any slice (design.md §Delta → Operator cleanup).
- **RUS-79 / RUS-84 Linear housekeeping (OQ3, OQ4).** Canceling RUS-79 and formally Canceling RUS-84 are human/Linear actions with no code impact; at most a PR-body note. Not mappable to code.
