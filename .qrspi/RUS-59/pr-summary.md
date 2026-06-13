# PR: RUS-59 Generation-side N-select for Design (judge + graft)

**Ticket:** RUS-59
**Design:** design.md @ 2026-06-13T00:00:00Z
**Structure:** structure.md @ 2026-06-13T00:00:00Z

## Summary

Adds an optional generation-side N-select stage to the Design phase: when enabled, the
orchestrator fans out N design candidates under distinct framings (`mvp-first`,
`risk-first`, `extensibility-first`), an LLM judge scores them on the four RUS-56 lenses
and names per-runner-up ideas worth grafting, a deterministic pure selector picks the
highest-scoring base, and a graft agent merges the named runner-up ideas in place — landing
one synthesized `design.md` that the unchanged critic panel + persist consume. The feature
is OFF by default behind `critics.design.candidates` (clamped `[1,3]`); N=1 keeps the
existing single-produce path byte-for-byte unchanged with zero extra spawns. Reviewer focus:
(1) the fail-closed abort posture and non-empty re-checks in `runDesignSelectLoop`, and
(2) the OFF/clamp guard in `resolveDesignCritic` + the `runPhase` splice, since these are
verified by manual e2e only (no JS unit-test harness exists for `qrspi-batch.js`). The pure
selector (`scripts/qrspi_design_select.py`) is fully unit-tested (28 cases).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: N-candidate generate → judge → synthesize (winner grafted with runner-up ideas) → one `design.md` into the panel | `qrspi-batch.js:runDesignSelectLoop` + `DESIGN_JUDGE_SCHEMA` + `DEFAULT_DESIGN_FRAMINGS`; `scripts/qrspi_design_select.py:select`; `.claude/agents/qrspi-design-judge.md`, `.claude/agents/qrspi-design-graft.md`, framing hook in `.claude/agents/qrspi-design.md` | `scripts/qrspi_design_select_test.py` (winner/tie/graft directives, 28 pass); judge+graft content-merge = manual e2e (T22) |
| AC2: Eval scores reported to justify N× spend (token-cost descoped, OQ1) | `qrspi-batch.js` folds per-candidate judge scores into the `doDesign` result via `criticConfig.selectSummary` + `log`/`summaryRounds` | Manual e2e — scores appear in `doDesign` summary/logs (structure Slice 2 checklist); token-cost half accepted-descoped |
| AC3: OFF by default; single flag enables it | `qrspi-batch.js:resolveDesignCritic` parses+clamps `candidates` to `[1,3]`; `runPhase` `if (criticConfig && criticConfig.candidates > 1)` guard short-circuits to single produce when N≤1; `.qrspi/config.example.json` documents the flag | `resolveDesignCritic` clamp logic extracted + exercised, 12/12 cases (OFF: absent/`0`/`-5`/`1`/non-numeric/NaN ⇒ N=1; clamp `2`⇒2,`3`⇒3,`99`⇒3+log,`2.7`⇒2); zero-extra-spawn assertion = manual e2e (T20/T21) |

## Changes by Slice

### Slice 1: Pure judge-base selector + tests (commit 310c17b)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_design_select.py` | new | +141 |
| `scripts/qrspi_design_select_test.py` | new | +170 |
| `.qrspi/RUS-59/impl-log.md` | modified | +39 |

### Slice 2: N-select wired into the design phase, OFF by default (commit 5e45b06)

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | modified | +324, -14 |
| `.claude/agents/qrspi-design-judge.md` | new | +57 |
| `.claude/agents/qrspi-design-graft.md` | new | +36 |
| `.claude/agents/qrspi-design.md` | modified | +2 |
| `.qrspi/config.example.json` | modified | +4, -1 |
| `.qrspi/RUS-59/impl-log.md` | modified | +65 |

### Phase artifacts (commits 9ff19fb [QR], 2a9e79c [SP])

| File | Change | Lines |
|------|--------|-------|
| `.qrspi/RUS-59/questions.md` | new | +49 |
| `.qrspi/RUS-59/research.md` | new | +316 |
| `.qrspi/RUS-59/design.md` | new | +139 |
| `.qrspi/RUS-59/structure.md` | new | +120 |
| `.qrspi/RUS-59/plan.md` | new | +121 |
| `.qrspi/RUS-59/worktree.md` | new | +66 |

## Testing Summary

- [x] Slice 1: selector unit tests — `python3 scripts/qrspi_design_select_test.py` — 28 passed, 0 failed
- [x] Slice 2: workflow syntax — `node --check .claude/workflows/qrspi-batch.js` — SYNTAX_OK
- [x] Slice 2: config validity — `.qrspi/config.example.json` JSON-validates — CONFIG_JSON_OK
- [x] Slice 2: selector regression — `python3 scripts/qrspi_design_select_test.py` — 28/28 (unaffected by Slice 2)
- [x] Slice 2: `resolveDesignCritic` clamp logic extracted + exercised under stub `log` — 12/12 cases pass
- [ ] Manual e2e (T20): `candidates` absent/`0`/`-5` ⇒ N=1, zero extra spawns — requires live Workflow runtime
- [ ] Manual e2e (T21): `candidates: 2` ⇒ 2 runs; `99` ⇒ clamped-to-3 with clamp log — requires live runtime
- [ ] Manual e2e (T22): N>1 produces non-empty synthesized `design.md`; graft rewrites in place (no-op when graftDirectives empty)
- [ ] Manual e2e (T23): null/empty candidate aborts the ticket (fail-closed) — requires live runtime spawning judge/graft

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `candidates` parse+clamp location | plan §11 named both `resolveDesignCritic` and `parseCriticConfig` | parse+clamp lives entirely in `resolveDesignCritic` | `parseCriticConfig` only extracts the raw `.design` object; the numeric parse belongs in the resolver. No contract change — `candidates` still rides the returned config object as the plan requires. |
| selector-worker + filesystem (copy / non-empty re-check) mechanism | left to be filled in inside Slice 2 (structure §Unverified Assumptions) | implemented by mirroring `synthesizeVerdicts`/`persistArtifact` worker pattern — `selectDesignWinner`, `stageDesignWinner`/`graftDesignWinner`/`candidatesNonEmpty` | Under-specified glue resolved per the documented precedent; no contract change. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| N-select runs when flag absent/garbled, incurring N× spend | mitigated — `runPhase` guard `criticConfig.candidates > 1` short-circuits; clamp-logic test confirms absent/`0`/`-5`/non-numeric ⇒ N=1; live zero-spawn assertion pending manual e2e | Set/leave `critics.design.candidates` unset (default OFF) |
| Candidate staging paths collide and clobber the canonical `design` slot | mitigated — distinct `stg(id,'design-cand-K')`; winner copied to `stg(id,'design')` only after selection; persist non-empty gate | n/a (revert Slice 2 commit) |
| Graft step drops winner content / produces empty file | mitigated — graft mirrors panel-reviser in-place contract; `runDesignSelectLoop` re-checks `stg(id,'design')` non-empty post-graft and post-copy; persist gate backstop; content-merge quality pending manual e2e | Revert Slice 2; OFF default leaves single-produce path |
| A candidate run flakes (null/empty), wasting other runs | accepted — fail-closed (Decision 4 Option A): any null/empty candidate aborts the ticket, matching panel precedent; survivor-tolerance deferred (OQ4) | n/a — fail-closed by design |
| AC2 token-cost reporting unsatisfiable (`agent()` returns no token counts) | accepted, not mitigated (OQ1 — token cost OUT OF SCOPE); judge scores reported via `log`/`summary`; no token accounting added | n/a |
| Judge produces a tie / no clear winner | mitigated — deterministic tie-break in selector (highest score, ties by candidate index); explicit unit-test coverage | n/a |

## Open Items

- Manual e2e remains (T20–T23 runtime halves): OFF/zero-spawn, clamp+log, synthesized-design+graft, and fail-closed candidate abort. These need the live Workflow runtime (`agent`/`parallel`), which the sandbox cannot exercise — they are orchestrator/operator steps outside the implement agent.
- AC2 token-cost reporting is descoped (OQ1-resolved): `agent()` exposes no token counts; only judge scores are reported. Accepted gap, not an oversight.
- OQ4 (deferred enhancement): partial-failure policy may later move from fail-closed to proceed-with-survivors above a threshold, only if e2e runs show single-candidate flakiness materially wastes N× spend. Recorded, not built.
- No JS unit-test harness exists for `qrspi-batch.js` (no `package.json`); the clamp, `runDesignSelectLoop`, and the splice are verified by manual e2e + the extracted clamp-logic test. Optional follow-up: factor count-resolution into a `scripts/`-side pure helper with a `_test.py` sibling for automated clamp coverage.
