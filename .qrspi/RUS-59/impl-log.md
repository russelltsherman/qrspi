# Implementation Log — Generation-side N-select for Design

## Session 1 — Slice 1

**Timestamp:** 2026-06-13T17:10:39Z
**Tasks completed:** T1, T2, T3, T4, T5, T6
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_design_select_test.py` → 28 passed, 0 failed

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- New module `scripts/qrspi_design_select.py` exposes a pure `select(judge_output: dict) -> dict`
  plus a `main()` CLI driver. Slice 2 worker invocation: `printf '%s' '<judge JSON>' | python3 scripts/qrspi_design_select.py`.
- CLI contract: reads the judge output (a JSON OBJECT, not array) from stdin; on success prints
  `{ "winner": str, "scores": [...], "graftDirectives": [str] }` to stdout and exits 0; on
  empty / non-JSON / malformed input prints `{ "error": <message> }` to stdout and exits NON-ZERO
  (fail-closed). Worker callers must check exit code, not just parse stdout.
- `winner` is computed deterministically from `scores` (highest `score`, tie-break = lowest index).
  The judge's own `winner` field, if present, is IGNORED by the selector — the judge prompt (T7)
  need not be relied on for the authoritative winner, though emitting it is harmless.
- `graftDirectives` excludes the winner's own `graft_ideas` and is the first-seen-deduped union of
  all non-winning candidates' `graft_ideas`. Empty ⇒ Slice 2 graft step is a no-op (per Decision 3).
- Malformed = input not a dict, `scores` missing/non-list/empty, or any score entry not a dict or
  lacking a non-empty string `candidate` / numeric `score` (bool is rejected as non-numeric). The
  whole selection fails closed on a single bad entry — it does not skip-and-continue.
- Module raises `SelectError` (a `ValueError` subclass) from `select()`; the CLI catches it and
  renders the error envelope. Slice 2 e2e fail-closed test (T23) relies on this non-zero exit.

---

## Session 2 — Slice 2 (full)

**Timestamp:** 2026-06-13T17:24:37Z
**Tasks completed:** T7, T8, T9, T10, T11, T12, T13, T14, T15, T16, T17, T18, T19 (the full Slice 2 — worktree Sessions 2 + 3)
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX_OK
- config.example.json JSON-validates → CONFIG_JSON_OK
- `python3 scripts/qrspi_design_select_test.py` → 28/28 pass (Slice 1 selector unaffected)
- `resolveDesignCritic` clamp logic (extracted + exercised under a stub `log`): 12/12 cases PASS
  — OFF (absent / no-key / `0` / `-5` / `1` / non-numeric / NaN ⇒ N=1) and clamp (`2`⇒2, `3`⇒3,
  `99`⇒3 with the clamp log line, `2.7`⇒floor 2); coexists with lenses/maxRounds. (Covers the
  deterministic half of checkpoints T20/T21.)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none. Two clarifications on under-specified glue (no contract change): (a) the `candidates`
  parse+clamp lives entirely in `resolveDesignCritic` (plan §11 named both it and
  `parseCriticConfig`; `parseCriticConfig` only extracts the raw `.design` object, so the numeric
  parse belongs in the resolver — `candidates` rides the returned config object as the plan
  requires). (b) The plan left the selector-worker and filesystem (copy/non-empty-check) mechanism
  to be filled in inside Slice 2 (structure §Unverified Assumptions); implemented by mirroring the
  `synthesizeVerdicts`/`persistArtifact` worker pattern — `selectDesignWinner` (stdin→`qrspi_design_select.py`),
  `stageDesignWinner`/`graftDesignWinner`/`candidatesNonEmpty` (verbatim one-command workers).

**Verification status (manual-e2e checkpoints):**

- T20 (OFF / N=1, zero extra spawns) and T21 (clamp + clamp log): the **deterministic** core
  (`resolveDesignCritic` + the `criticConfig.candidates > 1` guard in `runPhase`) is verified by
  the clamp-logic test above and code review. The runtime spawn-count assertions require the live
  Workflow runtime (`agent`/`parallel`) which the sandbox cannot exercise.
- T22 (synthesis + graft) and T23 (fail-closed candidate abort): NOT runnable here — they require
  the live Workflow runtime spawning the judge/graft agents. Per structure §Unverified Assumptions,
  no JS unit-test harness exists for `qrspi-batch.js`; these are manual-e2e items. The fail-closed
  abort paths (null/empty candidate, judge/selector/stage/graft failure ⇒ `{ok:false}` ⇒ ticket
  abort) are implemented mirroring `runCriticPanelLoop`'s landed precedent and verified by review.

**Notes for next session:**

- Slice 2 is COMPLETE — no further implementation slices for RUS-59 (this was the last). What
  remains is the manual e2e run (T20–T23 runtime halves) and the pr-summary.md / PR submission,
  both orchestrator/operator steps outside this implement agent.
- Files: 2 new agent prompts (`.claude/agents/qrspi-design-judge.md`, `.claude/agents/qrspi-design-graft.md`),
  3 modified (`.claude/workflows/qrspi-batch.js`, `.claude/agents/qrspi-design.md`, `.qrspi/config.example.json`).
- Wiring contract for any e2e verifier: enable via `.qrspi/config.json` →
  `critics.design.candidates: 2` (or 3). `resolveDesignCritic` clamps to [1,3]; N≤1 ⇒ OFF
  (byte-for-byte-unchanged single-produce path, the `if (criticConfig && criticConfig.candidates > 1)`
  guard in `runPhase` short-circuits). N>1 ⇒ `runDesignSelectLoop` fans out the first N of
  `DEFAULT_DESIGN_FRAMINGS = ['mvp-first','risk-first','extensibility-first']` to per-candidate
  `stg(id,'design-cand-K')`, judges (`qrspi-design-judge` → `DESIGN_JUDGE_SCHEMA`), selects via the
  Slice-1 python selector (`selectDesignWinner` worker), copies the winner to `stg(id,'design')`,
  conditionally grafts (`qrspi-design-graft`), then the EXISTING critic panel + persist consume
  `stg(id,'design')` unchanged.
- The `qrspi-design` agent now honors an optional `FRAMING` input line; absent ⇒ unchanged (the
  N=1 path passes no FRAMING). Per-candidate judge scores + winner + graft summary are folded into
  the `doDesign` result line via `criticConfig.selectSummary` (AC2 scores half). AC2 token-cost
  half remains descoped (structure §Unverified Assumptions — `agent()` exposes no token counts).

---
