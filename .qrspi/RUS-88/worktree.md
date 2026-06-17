# Work Tree — Retire the fidelity-only edge critic (qrspi-critic / runCriticLoop)

**Plan basis:** plan.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft
**Total sessions:** 5
**Critical path:** T3 → T5 → T9 → T11 → T26 → T32 → T37 (re-locate JS → resolver shape → JS mirror → runPhase gate → lockstep test update → suite green → final checkpoint)

> One plan slice (41 steps), partitioned into 5 sessions purely for context budget — every session ships under the same `RUS-88/slice-1` branch and there is **no green intermediate state** until the Verify session. The JS↔Python 6→2-key shape change (T5–T7 ⇄ T9–T10) is a single cross-file contract that must land together; the lockstep test (T30/T26) is its guard. Session 1 (trace/re-locate) is read-only and produces the facts every later edit anchors on — its findings must be carried forward in the load manifest as notes, not re-derived.

## Session 1 — Re-confirm anchors & resolve open questions (read-only)

**Load:** plan.md §Setup (steps 1–4), structure.md §Contracts, design.md §Risk Register (rows 4, 7, "stray reader"), design.md OQ2
**Estimated context:** ~18%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Trace `qrspi_slice_critic` consumers; resolve OQ2 (delete module vs NO-TOUCH) | — | §1 | S | pending |
| T2 | Enumerate every `perSliceFindings` assignment/read; classify per-slice-only vs shared-with-coherence | — | §2 | S | pending |
| T3 | Re-locate `runCriticLoop`/`gateBehindEdge`/`lenses?.length`/`runSliceCritic`/`sliceCriticDecide`/`implCriticCfg` against main HEAD; capture exact ternary text | — | §3 | M | pending |
| T4 | Re-locate every `critics.(questions\|research\|structure\|plan)` reader in qrspi-batch.js | — | §4 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Setup is read-only fact-gathering; its findings (consumer list, exact ternary/line anchors, perSliceFindings classification) are compact notes that flow forward. A fresh context for the edit phase avoids carrying the full grep transcripts.

## Session 2 — Python resolver + JS harness (the 6→2-key shape change)

**Load:** plan.md §Core Logic — Python resolver (steps 5–8a), plan.md §Core Logic — JS harness (steps 9–21), structure.md §Contracts (2-key map, lockstep boundary, runPhase critic-block gate), Session 1 notes (T1 OQ2 result, T2 perSliceFindings classification, T3 exact ternary/anchors, T4 reader list)
**Estimated context:** ~40%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T5 | Delete `EDGE_PHASES` constant in qrspi_critics_config.py | T3 | §5 | S | pending |
| T6 | Delete `resolve_edge_phase(...)` function | T5 | §6 | S | pending |
| T7 | Remove four edge-phase entries from `resolve_critics` → `{design, implementation}` | T6 | §7 | S | pending |
| T8 | Delete `gateBehindEdge` from `resolve_design` | T7 | §8 | S | pending |
| T8a | Reduce `resolve_implementation` → `{coherence}` (drop dead per-slice `enabled`/`maxRounds`) | T8, T16 | §8a | S | pending |
| T9 | Delete `.design` mirror's `gateBehindEdge` in `DEFAULT_CRITIC_PHASES` (JS) | T3, T8 | §9 | S | pending |
| T10 | Delete four planning-phase keys from `DEFAULT_CRITIC_PHASES` → `{design, implementation}` | T9 | §10 | S | pending |
| T10a | Reduce JS `DEFAULT_CRITIC_PHASES.implementation` mirror → `{coherence}` (lockstep with T8a) | T10, T8a | §10a | S | pending |
| T11 | Replace `lenses?.length` ternary in `runPhase` with panel-only gate | T3, T10 | §12 | M | pending |
| T12 | Delete `gateBehindEdge` short-circuit in `runPhase` | T3, T11 | §13 | S | pending |
| T13 | Delete `runCriticLoop` function | T3, T11 | §11 | M | pending |
| T14 | Delete `sliceCriticDecide` shim | T3 | §15 | S | pending |
| T15 | Delete `runSliceCritic` function | T3, T14 | §14 | M | pending |
| T16 | Remove `implCriticCfg.enabled`-gated per-slice block in `doImplementation` | T15 | §16 | M | pending |
| T17 | Remove orphaned `qrspi_slice_critic.py` invocation/import in JS | T15 | §20 | S | pending |
| T18 | Remove per-slice-critic-only `perSliceFindings` plumbing (keep shared-with-coherence) | T2, T16 | §21 | M | pending |
| T19 | Remove every `critics.(questions\|research\|structure\|plan)` reader (doDesign/doPlan builds + .enabled) | T4 | §17 | M | pending |
| T20 | Remove `out.criticMetrics`/PR-body folds for retired planning critics + runCriticLoop residuals | T13, T19 | §18 | S | pending |
| T21 | Remove doDesign/doPlan plumbing passing retired configs into runPhase (call with `criticConfig = undefined`) | T19, T20 | §19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All source edits to the two coupled files are done and tightly interdependent (~19 edits, at the 40% budget). Deletions and tests start from a clean slate; a fresh context keeps the editing transcript out of the way and lets the deletion/test session load only the affected file list.

## Session 3 — Agent/script deletions

**Load:** plan.md §Deletions (steps 22–25), Session 1 notes (T1 OQ2 result governing T24/T25)
**Estimated context:** ~12%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T22 | Delete `.claude/agents/qrspi-critic.md` | T13, T15 | §22 | S | pending |
| T23 | Delete `.claude/skills/qrspi-critic/` wrapper dir | T22 | §23 | S | pending |
| T24 | Delete `scripts/qrspi_slice_critic.py` — ONLY if T1 found no other consumer | T1, T15, T17 | §24 | S | pending |
| T25 | Delete `scripts/qrspi_slice_critic_test.py` — conditional on T24 | T24 | §25 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Deletions complete. The test session edits a distinct file set (the `_test.py` suite) and ends in the first green checkpoint — a fresh context isolates the test-fix loop and its run output.

## Session 4 — Tests + config/docs sweep

**Load:** plan.md §Tests (steps 26–32, incl. the 31a–31e contract-fixture seam), plan.md §Config and documentation sweep (steps 33–36), structure.md §Contracts (2-key map, lockstep boundary), Session 1 notes (T1 OQ2)
**Estimated context:** ~33%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T26 | Delete `TestResolveEdgePhase` class in qrspi_critics_config_test.py | T6 | §26 | S | pending |
| T27 | Delete four `gateBehindEdge` test cases + edge-phase toggle test | T8 | §27 | S | pending |
| T28 | Add assertion: `resolve_critics` keys exactly `{design, implementation}` for no-lenses config | T7 | §28 | S | pending |
| T29 | Add assertion: design panel + `implementation.coherence` still resolve | T7, T8 | §29 | S | pending |
| T30 | Update JS-mirror lockstep test + `test_default_phases_matches_empty_resolution`: keys `{design, implementation}`, `.design` no `gateBehindEdge`, `.implementation` only `{coherence}` | T10, T10a, T28 | §30 | M | pending |
| T31 | Rewrite `EXPECTED_DEFAULT_CRITIC_PHASES` golden → 2-key (drop 4 planning phases + `gateBehindEdge`; `implementation`→`{coherence}`) | T7, T8, T8a | §31 | M | pending |
| T31a | Re-choose `test_critics_wellformed_accepted` discriminator (flip a surviving key, not `questions`) | T31 | §31a | S | pending |
| T31b | Regenerate `wellformed.json` → 2-key golden (byte-equals `default_phases()`) | T7, T8, T8a | §31b | S | pending |
| T31c | Re-author `wellformed_consumer.json` → 2-key, flip the same surviving key as T31a | T31a | §31c | S | pending |
| T31d | Verify `malformed.json`/`partial_merge.json` need no shape edit | T31 | §31d | S | pending |
| T31e | Producer `test_critics`: change key-set assertion → `{design, implementation}` | T7, T31b | §31e | S | pending |
| T32 | Run `python3 scripts/run_tests.py` — suite green (lockstep + contract-fixture) | T26, T27, T28, T29, T30, T31, T31a, T31b, T31c, T31d, T31e | §32 | S | pending |
| T33 | Sweep `.qrspi/config.example.json` — remove gateBehindEdge + four planning sub-blocks + $comments; keep design.lenses + implementation.coherence | T7, T8 | §33 | S | pending |
| T34 | Revise edge-critic/runCriticLoop/gateBehindEdge prose in `CLAUDE.md` | T32 | §34 | M | pending |
| T35 | Same sweep in `.claude/CLAUDE.md` | T34 | §35 | S | pending |
| T36 | Sweep `docs/*.md` (testing-dynamic-workflows.md, qrspi-pr-gated-lifecycle-design.md); keep historical | T34 | §36 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** All edits done and the suite is green once. The Verify session runs the final acceptance checkpoints (grep completeness + KEPT-surface assertions + manual e2e) against the fully-edited tree with a clean context — verification must not share the editing session that produced what it checks.

## Session 5 — Verify Slice 1

**Load:** plan.md §Verify Slice 1 (steps 37–41), design.md §Risk Register (rows 1–3), design.md §Acceptance Criteria (AC1–AC5)
**Estimated context:** ~15%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T37 | Checkpoint: `python3 scripts/run_tests.py` exits 0 | T32, T33, T34, T35, T36 | §37 | S | pending |
| T38 | Checkpoint: `git grep 'runCriticLoop\|gateBehindEdge\|edge critic'` → only intentional/historical | T37 | §38 | S | pending |
| T39 | Checkpoint: `git grep -E "critics\.(questions\|research\|structure\|plan)"` in qrspi-batch.js → nothing | T37 | §39 | S | pending |
| T39a | Checkpoint: `git grep -E "implCriticCfg\.(enabled\|maxRounds)"` in qrspi-batch.js → nothing (only `.coherence.*` survives) | T37 | §39a | S | pending |
| T40 | Checkpoint: `runCriticPanelLoop`/`runCoherenceCritic` present; `qrspi_critic_loop.py` + five `qrspi-design-critic-*` agents unmodified | T37 | §40 | S | pending |
| T41 | Checkpoint (manual e2e): design+plan+impl pass on a scratch ticket — panel + coherence active, planning phases ungated | T38, T39, T39a, T40 | §41 | L | pending |
