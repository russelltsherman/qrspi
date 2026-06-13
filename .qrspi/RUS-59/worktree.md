# Work Tree — Generation-side N-select for Design

**Plan basis:** plan.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T9 → T11 → T12 → T13 → T14 → T15 → T16 → T17 → T23

## Session 1

**Load:** structure.md §Contracts (the `select(judgeOutput)` contract + fail-closed rule), structure.md §Verification, plan.md §Slice 1
**Estimated context:** ~15% of window

Slice 1 — pure stdlib selector module + its unit tests. Self-contained: one new script + one test file, no `qrspi-batch.js` or agent-prompt context needed.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_design_select.py` module scaffold (stdin-JSON → stdout-JSON, mirroring `qrspi_critic_synthesize.py`) | — | §1 | S | pending |
| T2 | Add `select(judgeOutput) -> {winner, scores, graftDirectives}` per structure.md contract (highest-score winner, lowest-index tie-break, runner-up graft dedup) | T1 | §2 | M | pending |
| T3 | Add fail-closed handling for empty/malformed input (error envelope + non-zero exit) | T2 | §3 | S | pending |
| T4 | Add `__main__` stdin→stdout driver wiring `select()` | T3 | §4 | S | pending |
| T5 | Create `scripts/qrspi_design_select_test.py` covering single-winner, tie, all-pass, no-runners-up, empty, malformed | T4 | §5 | M | pending |
| T6 | **Verify Slice 1** — `python3 scripts/qrspi_design_select_test.py` (all checkpoint boxes) | T5 | §6 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete and independently verified. Slice 2 loads a different, large context (`qrspi-batch.js` orchestration + four agent prompts); a fresh session avoids carrying the selector's internals forward and keeps each session under 40%.

## Session 2

**Load:** structure.md §Contracts, structure.md §Decisions (1, 2, 4 Option A), plan.md §Slice 2 (steps 7–11, 18–19), impl-log.md §Slice 1 (notes only — `qrspi_design_select.py` CLI contract)
**Estimated context:** ~32% of window

Slice 2 part A — the standalone, additive building blocks: the two new agent prompts, the design-prompt framing hook, the schema + framings consts, the config parse + clamp, and the config doc. These have no cross-dependencies on the orchestration helper (built in Session 3) beyond what they expose.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Create `.claude/agents/qrspi-design-judge.md` — judge prompt scoring N candidates on the four RUS-56 lenses, emitting `DESIGN_JUDGE_SCHEMA` with per-non-winner `graft_ideas` | T6 | §7 | M | pending |
| T8 | Create `.claude/agents/qrspi-design-graft.md` — graft prompt rewriting the winning design in place, merging runner-up ideas (non-empty contract) | T6 | §8 | M | pending |
| T9 | Modify `qrspi-batch.js` — add `DESIGN_JUDGE_SCHEMA` near `CRITIC_VERDICT_SCHEMA` | T6 | §9 | S | pending |
| T10 | Modify `qrspi-batch.js` — add `DEFAULT_DESIGN_FRAMINGS = ['mvp-first','risk-first','extensibility-first']` near `DEFAULT_DESIGN_LENSES` | T6 | §10 | S | pending |
| T11 | Modify `qrspi-batch.js` — extend `parseCriticConfig`/`resolveDesignCritic` to parse + clamp `candidates` to `[1,3]` with a clamp log | T10 | §11 | M | pending |
| T18 | Modify `.claude/agents/qrspi-design.md` — honor an optional per-framing instruction line (absent ⇒ unchanged N=1 path) | T6 | §18 | S | pending |
| T19 | Modify `.qrspi/config.example.json` — document `critics.design.candidates` (numeric, clamped `[1,3]`, default OFF) | T6 | §19 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Session 2 lands the additive primitives (schema, framings, config parse, prompts). Session 3 wires the `runDesignSelectLoop` orchestration helper and splices it into `runPhase` — a tightly coupled `qrspi-batch.js` editing burst plus the manual e2e verification matrix. Fresh context lets the implementer load the now-existing primitives as facts (via impl-log notes) rather than re-deriving them, staying under 40%.

## Session 3

**Load:** structure.md §Contracts, structure.md §Decisions (1 Option A, 4 Option A) + §Risk Register (graft-empties-file), plan.md §Slice 2 (steps 12–17, 20–23), impl-log.md §Slice 1 + §Slice 2-A (notes only — `DESIGN_JUDGE_SCHEMA`, `DEFAULT_DESIGN_FRAMINGS`, the `candidates` config field, the judge/graft/design prompt contracts)
**Estimated context:** ~34% of window

Slice 2 part B — assemble `runDesignSelectLoop` (fan-out → judge → selector → copy/graft → log), splice into `runPhase`, thread N, then run the manual e2e verification matrix.

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Modify `qrspi-batch.js` — add `runDesignSelectLoop(name,id,config)`: fan out N framings into per-candidate `stg(id,'design-cand-K')` thunks, abort fail-closed on any null/empty candidate | T7, T9, T10, T11, T18 | §12 | L | pending |
| T13 | Modify `qrspi-batch.js` — within the loop, run the judge then `scripts/qrspi_design_select.py` via worker to get `{winner, scores, graftDirectives}` | T12 | §13 | M | pending |
| T14 | Modify `qrspi-batch.js` — copy winning candidate to `stg(id,'design')`, conditionally spawn graft agent, re-check non-empty (abort if empty) | T8, T13 | §14 | M | pending |
| T15 | Modify `qrspi-batch.js` — log per-candidate judge scores + graft summary; build returned `summary` | T14 | §15 | S | pending |
| T16 | Modify `qrspi-batch.js` — splice `runDesignSelectLoop` into `runPhase` between produce `agent()` and the critic block, guarded by `N>1` (N=1 byte-for-byte unchanged) | T15 | §16 | M | pending |
| T17 | Modify `qrspi-batch.js` — thread resolved `candidates` (N) from design critic config into `runPhase`/`doDesign`; fold N-select summary into `doDesign` result | T16 | §17 | M | pending |
| T20 | **Verify (OFF/clamp):** e2e with `candidates` absent/`0`/`-5` ⇒ N=1, zero extra spawns, path unchanged | T17, T19 | §20 | S | pending |
| T21 | **Verify (clamp log):** e2e `candidates: 2` ⇒ 2 runs; `candidates: 99` ⇒ clamped to 3 with clamp log | T17, T19 | §21 | S | pending |
| T22 | **Verify (synthesis+graft):** e2e N>1 ⇒ non-empty `design.md` staged; graft runs on runner-up ideas, skipped when empty; per-candidate scores in `doDesign` summary | T17 | §22 | S | pending |
| T23 | **Verify (fail-closed):** e2e with one candidate forced null/empty ⇒ ticket aborts, no partial winner | T17 | §23 | S | pending |
