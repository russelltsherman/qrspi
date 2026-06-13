# Implementation Plan — Generation-side N-select for Design

**Structure basis:** structure.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft
**Total steps:** 23

## Slice 1: Pure judge-base selector + tests

### Setup

1. ✨ Create `scripts/qrspi_design_select.py` — pure, stdlib-only stdin-JSON → stdout-JSON selector module. Reads the judge output from stdin, computes `{winner, scores, graftDirectives}`, writes to stdout. Mirror the shape of `scripts/qrspi_critic_synthesize.py` (stdlib only, `json.load(sys.stdin)` → compute → `json.dump(result, sys.stdout)`; non-zero exit / error envelope on failure).

### Core Logic

2. ⚠️ Modify `scripts/qrspi_design_select.py` — add the `select(judgeOutput)` function implementing the structure.md contract `select(judgeOutput) -> { winner, scores, graftDirectives }`.
   - **Current:** file contains only module scaffold from step 1.
   - **After:** `def select(judge_output: dict) -> dict:` — `winner` = candidate id with highest `score`; deterministic tie-break = lowest candidate index (order of appearance in `scores`); `scores` echoed through; `graftDirectives` = deduped list of `graft_ideas` drawn from all **non-winning** candidates (winner's own `graft_ideas` excluded), preserving first-seen order. Input shape `{ scores: [{candidate, score, rationale, graft_ideas?: string[]}], winner? }`.

3. ⚠️ Modify `scripts/qrspi_design_select.py` — add fail-closed handling for empty/malformed input.
   - **Current:** `select()` assumes well-formed input.
   - **After:** raise / emit an error envelope and exit non-zero when stdin is empty, not valid JSON, `scores` missing/empty, or any score entry lacks `candidate`/`score`. Matches "Fail-closed (non-zero exit / error envelope) on empty or malformed input" from structure.md Contracts.

4. ⚠️ Modify `scripts/qrspi_design_select.py` — add the `__main__` stdin→stdout driver wiring `select()` to `sys.stdin`/`sys.stdout`, mirroring `qrspi_critic_synthesize.py`'s entrypoint.
   - **Current:** module exposes `select()` but no CLI entrypoint.
   - **After:** `if __name__ == "__main__":` reads stdin JSON, calls `select()`, dumps result to stdout; on error prints error envelope to stdout/stderr and exits non-zero.

### Tests

5. ✨ Create `scripts/qrspi_design_select_test.py` — stdlib `unittest` `_test.py` sibling. Cases per structure.md Verification: single-winner (highest score selected); tie → deterministic lowest-index tie-break; all-pass; no-runners-up → empty `graftDirectives` (graft is a downstream no-op); empty input → fail-closed; malformed input → fail-closed. Import `select` directly and assert on its return value; cover the fail-closed cases by asserting it raises / returns an error envelope.

### Verify Slice 1

6. **Checkpoint:** `python3 scripts/qrspi_design_select_test.py`
   - [ ] All cases pass: single-winner selects highest score.
   - [ ] Tie resolves to lowest candidate index (deterministic).
   - [ ] No-runners-up case yields empty `graftDirectives`.
   - [ ] Empty and malformed inputs fail closed (raise / error envelope, non-zero exit from the CLI driver).

---

## Slice 2: N-candidate generate → judge → synthesize, wired into the design phase (OFF by default)

### Setup

7. ✨ Create `.claude/agents/qrspi-design-judge.md` — judge agent prompt. Consumes N candidate design paths + their framing labels (passed as inputs), scores each candidate on the four RUS-56 lenses (`completeness`, `internal-consistency`, `edge-alignment`, `simplicity`) with **equal weight**, and names per-non-winning-candidate `graft_ideas` (strong ideas worth grafting into the winner). Emits exactly `DESIGN_JUDGE_SCHEMA`: `{ scores: [{ candidate, score, rationale, graft_ideas: string[] }], winner }`. Document that `graft_ideas` is empty for the winner / candidates with nothing distinctive.

8. ✨ Create `.claude/agents/qrspi-design-graft.md` — graft agent prompt. Consumes the winning base design path (`stg(id,'design')`) + the selector's `graftDirectives`. Rewrites that file IN PLACE, merging the named runner-up ideas while preserving the winner's structure. Mirror the panel reviser's in-place-rewrite-then-non-empty contract: write back to the same path, never empty it.

### Core Logic

9. ⚠️ Modify `qrspi-batch.js` — add the `DESIGN_JUDGE_SCHEMA` JS object schema near the existing `CRITIC_VERDICT_SCHEMA`.
   - **Current:** no judge schema exists; only `CRITIC_VERDICT_SCHEMA` (binary `{pass, findings}`).
   - **After:** `const DESIGN_JUDGE_SCHEMA = { ... }` encoding `{ scores: [{ candidate: string, score: number, rationale: string, graft_ideas: string[] }], winner: string }`, in the schema style used by `CRITIC_VERDICT_SCHEMA`.

10. ⚠️ Modify `qrspi-batch.js` — add the `DEFAULT_DESIGN_FRAMINGS` const near `DEFAULT_DESIGN_LENSES`.
    - **Current:** only `DEFAULT_DESIGN_LENSES` exists.
    - **After:** `const DEFAULT_DESIGN_FRAMINGS = ['mvp-first', 'risk-first', 'extensibility-first'];`

11. ⚠️ Modify `qrspi-batch.js` — extend `parseCriticConfig` / `resolveDesignCritic` to parse the numeric `candidates` field off `value.design`.
    - **Current:** `value.design` parsing handles lenses/maxRounds only; no `candidates` field.
    - **After:** read `candidates: number` from `value.design`; clamp to `[1, DEFAULT_DESIGN_FRAMINGS.length]` (= `[1, 3]`); absent / non-numeric / `≤1` ⇒ `1`; `≥2` ⇒ `min(candidates, 3)`. **Log when clamping** (mirroring the unknown-lens log-and-drop idiom). Resolved value carried on the design critic config object the existing precedence (config>default) produces.

12. ⚠️ Modify `qrspi-batch.js` — add the `runDesignSelectLoop(name, id, config)` helper returning `{ ok, summary? }`.
    - **Current:** no N-select helper exists.
    - **After:** fans out N framings (first N of `DEFAULT_DESIGN_FRAMINGS`) via `parallel` into per-candidate `stg(id,'design-cand-K')` thunks (K in `0..N-1`), each spawning the `qrspi-design` agentType with a per-framing instruction line; collects results and aborts (`ok:false`) on any null/empty candidate (fail-closed, Decision 4 Option A). Mirror `synthesizeVerdicts`/`criticDecision` structure for the worker calls.

13. ⚠️ Modify `qrspi-batch.js` — within `runDesignSelectLoop`, run the judge then the pure selector via a worker.
    - **Current:** helper has fan-out only (from step 12).
    - **After:** spawn the `qrspi-design-judge` agent over the N candidate paths + framing labels to get a `DESIGN_JUDGE_SCHEMA` result; invoke `scripts/qrspi_design_select.py` via a worker agent (the JS-sandbox-can't-run-python pattern used by `synthesizeVerdicts`/`criticDecision`), passing the judge output on stdin, to obtain `{ winner, scores, graftDirectives }`.

14. ⚠️ Modify `qrspi-batch.js` — within `runDesignSelectLoop`, copy the winning candidate to the canonical slot then conditionally graft.
    - **Current:** helper has selection result (from step 13) but does not stage the winner.
    - **After:** copy the winning candidate's `stg(id,'design-cand-K')` content to `stg(id,'design')`; when `graftDirectives` is non-empty, spawn the `qrspi-design-graft` agent to rewrite `stg(id,'design')` in place merging runner-up ideas; when empty, skip graft (no-op). Re-check `stg(id,'design')` is non-empty after the copy and after any graft, aborting (`ok:false`) if empty (Risk Register: graft-empties-file mitigation).

15. ⚠️ Modify `qrspi-batch.js` — within `runDesignSelectLoop`, log per-candidate judge scores and the graft summary; build the returned `summary`.
    - **Current:** helper completes selection + graft (from step 14) without surfacing scores.
    - **After:** fold per-candidate judge scores into the result via the existing `log(...)` / `summaryRounds` / returned-`summary` pattern, and return `{ ok: true, summary }` (AC2 scores half).

16. ⚠️ Modify `qrspi-batch.js` — splice `runDesignSelectLoop` into `runPhase` between the single produce `agent()` call and the `if (criticConfig)` critic block, guarded by `N>1` (Decision 1 Option A).
    - **Current:** `runPhase` calls the single produce `agent()` then falls straight into the critic dispatch.
    - **After:** after the produce call, if the resolved design `candidates` N > 1, call `runDesignSelectLoop(...)`; abort the ticket on `!ok`. When N=1 the path is byte-for-byte unchanged (no extra spawns). The critic block + `persistArtifact` consume `stg(id,'design')` exactly as today.

17. ⚠️ Modify `qrspi-batch.js` — thread the resolved `candidates` (N) value from the design critic config into `runPhase`/`doDesign` so the N>1 guard (step 16) can read it.
    - **Current:** `doDesign` builds the design critic config and passes it to `runPhase`; N is not consumed by the splice.
    - **After:** the splice in `runPhase` reads N off the passed critic config object (the field set in step 11); `doDesign` folds the N-select summary into its result summary alongside the existing panel summary.

18. ⚠️ Modify `.claude/agents/qrspi-design.md` — accept an optional per-framing instruction line spliced in by `runDesignSelectLoop` (Decision 2 Option A).
    - **Current:** the design prompt has no framing variation; one agentType, one prompt.
    - **After:** the prompt honors an optional framing directive (e.g. an extra input line / placeholder) instructing the run to design under the named framing (`mvp-first` / `risk-first` / `extensibility-first`); absent the line, behavior is unchanged (preserves the N=1 single-produce path).

### Config

19. ⚠️ Modify `.qrspi/config.example.json` — document `critics.design.candidates`.
    - **Current:** `critics.design` documents lenses/maxRounds only.
    - **After:** add `candidates` (numeric N, clamped `[1,3]`, default OFF / N=1) to the documented `critics.design` block.

### Verify Slice 2

20. **Checkpoint (OFF / clamp behavior):** Manual e2e run with `critics.design.candidates` absent, `0`, and `-5`.
    - [ ] Each yields N=1: only the single produce agent spawns; **zero** extra spawns (no judge, selector, or graft); downstream path byte-for-byte unchanged.

21. **Checkpoint (clamp log):** Manual e2e run with `candidates: 2` and `candidates: 99`.
    - [ ] `candidates: 2` ⇒ 2 candidate runs.
    - [ ] `candidates: 99` ⇒ clamped to 3 with a clamp log line emitted.

22. **Checkpoint (synthesis + graft):** Manual e2e run with N>1.
    - [ ] A non-empty synthesized `design.md` lands at `stg(id,'design')`.
    - [ ] When the judge emits runner-up `graft_ideas`, the graft agent rewrites in place; when `graftDirectives` is empty, graft is skipped (no-op).
    - [ ] Per-candidate judge scores appear in the `doDesign` result summary / logs (AC2 scores half).

23. **Checkpoint (fail-closed):** Manual e2e run where one candidate is forced null/empty.
    - [ ] The ticket aborts (fail-closed, Decision 4 Option A); no partial winner is selected.

---

## Rollback Notes

- Step 19 (`.qrspi/config.example.json`): documentation-only change; revert the file to remove the `candidates` doc line. No runtime effect.
- Steps 9–18 (`qrspi-batch.js`, `.claude/agents/*`): purely additive and default-OFF. With `critics.design.candidates` absent/≤1 the design phase runs the single-produce path unchanged, so rolling back is reverting the additions; no migration or persisted state is affected.
- No DB migrations, no destructive operations, no irreversible config changes in this plan.
