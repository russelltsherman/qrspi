# Structure Outline — Generation-side N-select for Design

**Design basis:** design.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## New Types

- `DESIGN_JUDGE_SCHEMA` (JS object schema in `qrspi-batch.js`) — the judge agent's comparative output:
  `{ scores: [{ candidate: string, score: number, rationale: string, graft_ideas: string[] }], winner: string }`.
  `graft_ideas` per candidate names the strong ideas in that candidate worth grafting into the winner
  (empty for the winner / candidates with nothing distinctive). Distinct from `CRITIC_VERDICT_SCHEMA`
  (binary `{pass, findings}`, no ranking, no graft dimension) (ref: Delta, Decision 3).
- `DEFAULT_DESIGN_FRAMINGS = ['mvp-first', 'risk-first', 'extensibility-first']` (JS const in
  `qrspi-batch.js`) — three orthogonal framing axes, analogous to `DEFAULT_DESIGN_LENSES` (ref: Delta, OQ2).

## Modified Types

- Critic config `value.design` object — add numeric field `candidates: number` (the N flag),
  parsed by `resolveDesignCritic`/`parseCriticConfig`, clamped to `[1, len(DEFAULT_DESIGN_FRAMINGS)]`
  (= `[1, 3]`); absent/`≤1` ⇒ N=1 (ref: design.md §Delta, AC3, OQ3).

## Contracts

- **Pure selector (Python, stdin-JSON → stdout-JSON):**
  `qrspi_design_select.select(judgeOutput) -> { winner, scores, graftDirectives }`
  - input: `{ scores: [{candidate, score, rationale, graft_ideas?: string[]}], winner? }`
  - `winner` = highest-`score` candidate id; deterministic tie-break = lowest candidate index.
  - `graftDirectives` = deduped list of `graft_ideas` drawn from all **non-winning** candidates
    (excluding the winner's own). Empty when no runner-up carries a distinctive idea.
  - Fail-closed (non-zero exit / error envelope) on empty or malformed input.
  (ref: Delta `scripts/qrspi_design_select.py`, Decision 3, Q5/Q8/Q11)
- **JS helper:** `runDesignSelectLoop(name, id, config) -> { ok, summary? }` in `qrspi-batch.js`
  — fans out N framings, judges, calls the pure selector via a worker (like `synthesizeVerdicts`/
  `criticDecision`), copies the winning candidate to `stg(id,'design')`, runs the graft agent in
  place when `graftDirectives` non-empty, re-checks non-empty. Lands the final synthesized design at
  exactly `stg(id, 'design')` for the unchanged panel + persist to consume (ref: Delta, Decision 1).
- **Candidate staging paths:** `stg(id, 'design-cand-K')` for K in `0..N-1` — distinct per-candidate
  slots; winner copied to `stg(id, 'design')` only after selection (ref: Decision 2, Risk Register).
- **Judge agent (`qrspi-design-judge`):** consumes N candidate paths + framing labels, emits
  `DESIGN_JUDGE_SCHEMA` (ref: Delta).
- **Graft agent (`qrspi-design-graft`):** consumes the winning base path (`stg(id,'design')`) +
  `graftDirectives`; rewrites that file IN PLACE merging runner-up ideas while preserving the
  winner's structure — mirrors the panel reviser's in-place-rewrite-then-non-empty contract
  (ref: Delta, Decision 3, Q3).

## Slice 1: Pure judge-base selector + tests

**Goal:** A deterministic, stdlib-only selector that takes judge output and returns
`{winner, scores, graftDirectives}`, independently verifiable end-to-end via `python3` unit tests
with no JS or agent dependency. This is the deterministic core the orchestration will call via a worker.
**Files touched:**

- ✨ `scripts/qrspi_design_select.py` — pure stdin-JSON → stdout-JSON selector: highest-score winner,
  tie-break by candidate index; `graftDirectives` = deduped runner-up `graft_ideas` (winner excluded);
  fail-closed on empty/malformed. Mirrors `qrspi_critic_synthesize.py` shape.
- ✨ `scripts/qrspi_design_select_test.py` — `_test.py` sibling covering: all-pass, ties (deterministic
  index tie-break), single-winner, empty/malformed fail-closed, and the no-runners-up case
  (empty `graftDirectives` ⇒ graft is a downstream no-op).
**Verification:**
- [ ] `python3 scripts/qrspi_design_select_test.py` passes all cases (single-winner, tie→index,
  no-runners-up→empty graftDirectives, empty/malformed→fail-closed).
**Context cost:** S
**Depends on:** none

## Slice 2: N-candidate generate → judge → synthesize, wired into the design phase (OFF by default)

**Goal:** The full N-select stage running end-to-end behind the `critics.design.candidates` flag:
N framing fan-out → judge → pure selector (Slice 1) → copy winner → conditional graft → panel + persist.
With the flag absent/≤1, the design phase spawns exactly the single produce agent as today (zero extra
spawns). Verified by manual e2e: panel-only vs. N-select+panel, and the OFF/clamp behaviors. All files
here are mutually dependent JS/prompt glue — none is independently e2e-verifiable without the others, so
they form one slice.
**Files touched:**

- ⚠️ `qrspi-batch.js` — add `DESIGN_JUDGE_SCHEMA`, `DEFAULT_DESIGN_FRAMINGS`, the
  `runDesignSelectLoop` helper, the produce↔critic splice in `runPhase` guarded by N>1 (Decision 1
  Option A), the `candidates` clamp+log in `resolveDesignCritic`/`parseCriticConfig`, and folding
  per-candidate judge scores into the `doDesign` result summary via `log`/`summaryRounds`/`summary`.
- ✨ `.claude/agents/qrspi-design-judge.md` — judge prompt: scores N candidates on the four
  RUS-56 lenses (equal weight) AND names per-non-winner `graft_ideas`; emits `DESIGN_JUDGE_SCHEMA`.
- ✨ `.claude/agents/qrspi-design-graft.md` — graft prompt: rewrites the winning base at
  `stg(id,'design')` in place, merging named runner-up ideas, preserving winner structure
  (panel-reviser-shaped contract).
- ⚠️ existing `qrspi-design` agent prompt (`.claude/agents/qrspi-design.md`) — accept an optional
  per-framing instruction line spliced in by `runDesignSelectLoop` (Decision 2 Option A: one
  agentType, framings as data; no new per-framing agent files).
- ⚠️ `.qrspi/config.example.json` — document `critics.design.candidates` (numeric N, clamped `[1,3]`,
  default OFF).
**Verification:**
- [ ] Manual e2e: `candidates` absent / `0` / `-5` ⇒ N=1, single produce agent only, **zero** extra
  spawns (judge/selector/graft), byte-for-byte-unchanged downstream path.
- [ ] Manual e2e: `candidates: 2` ⇒ 2 candidate runs; `candidates: 99` ⇒ clamped to 3 with a clamp log line.
- [ ] Manual e2e: N>1 run produces a non-empty synthesized `design.md` at `stg(id,'design')`; when the
  judge emits runner-up `graft_ideas`, the graft agent rewrites in place (no-op skip when graftDirectives empty).
- [ ] Manual e2e: any null/empty candidate aborts the ticket (fail-closed, Decision 4 Option A).
- [ ] Per-candidate judge scores appear in the `doDesign` result summary / logs (AC2 scores half).
**Context cost:** M
**Depends on:** Slice 1 (calls `qrspi_design_select.py` via a worker for `{winner, scores, graftDirectives}`)

---

## Unverified Assumptions

- **No JS unit-test harness exists** for `qrspi-batch.js` (no `package.json`), so the `candidates`
  clamp, `runDesignSelectLoop`, and the splice are verified only by manual e2e — not automated tests.
  The design records factoring count-resolution into a `scripts/`-side pure helper with a `_test.py`
  sibling as an *option* (not mandated); not built here. If the reviewer wants unit coverage of the
  clamp, that pure helper becomes a third file in Slice 1 (still independently testable). (ref: design.md §Delta testability note)
- **Worker-invocation mechanism for the pure selector** is assumed to mirror the existing
  `synthesizeVerdicts`/`criticDecision` worker pattern (JS sandbox cannot run python; a worker agent
  runs `python3 scripts/qrspi_design_select.py`). The design asserts this precedent (ref: Q8) but the
  exact worker-agent prompt/wiring is not spelled out at code level and is implemented inside Slice 2.
- **Graft agent in-place-rewrite safety** rests on it faithfully mirroring the panel reviser's
  non-empty-rewrite contract; the design mitigates via a post-graft non-empty re-check in
  `runDesignSelectLoop` plus the persist gate, but the graft *content-merge* quality is generative and
  verifiable only by manual e2e, not by any deterministic test (ref: Decision 3, Risk Register).
- **AC2 token-cost reporting is explicitly descoped** (OQ1-resolved): `agent()` exposes no token
  counts; only judge *scores* are reported. No code maps to the token-cost half of the ticket's AC2 —
  this is an accepted, unmitigated gap, not an oversight.
