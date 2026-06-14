# Structure Outline — qrspi critics 4/5 — Stage 3 (Implementation): per-slice code critics + whole-stack coherence pass

**Design basis:** design.md @ 2026-06-13T21:10:00Z
**Generated:** 2026-06-13T21:35:00Z
**Status:** draft

## New Types

These are the data shapes the new pure module exchanges with its JS caller. They are
plain dicts/JSON (stdlib-only convention), described as pseudo-types.

- `SliceCriticSetup { slices: Array<{ alreadyCommitted: bool }>, sliceIndex: int (1-based), id: string }` — the input the diff-scope/skip reducer reads (mirrors the `setup` blob already in `doImplementation`).
- `SliceCriticDecision { run: bool, skipReason: "alreadyCommitted" | "single-slice" | null, diffBase: string | null, diffHead: string | null }` — the reducer's verdict: whether to run the per-slice critic for this slice, and if so the Graphite diff range `${diffBase}..${diffHead}`.
- `ImplementationCriticConfig { enabled: bool, maxRounds: int, coherence: { enabled: bool, maxRounds: int } }` — the parsed `critics.implementation` block (shape mirrors the existing design/plan critic config; coherence settings nested). Absent block → disabled defaults.

## Modified Types

- `_PHASE_BRANCH` (in `scripts/qrspi_critic_body.py`) — add a `slice` entry mapping `--phase slice --slice N` to branch `${id}/slice-N` (ref: design.md §Delta, Decision 4). Today maps only `design`/`plan`.

## Contracts

- `qrspi_slice_critic.py :: decide(setup, slice_index) -> SliceCriticDecision` — pure reducer: returns `run=False` with `skipReason="alreadyCommitted"` when the slice is already committed (resume), `run=False` with `skipReason="single-slice"` when `len(setup.slices) == 1`, else `run=True` with `diffBase = ${id}/plan` for slice 1 or `${id}/slice-(N-1)` otherwise, and `diffHead = ${id}/slice-N` (ref: Decision 1A, Decision 5, Decision 7, Q10, Q11).
- `qrspi_critic_loop.py :: next_action(verdicts, round, max_rounds) -> ...` — **EXISTING, reused verbatim** for the per-slice converge/revise/cap decision. NOT re-implemented (ref: Decision 5, Q3).
- `qrspi_critic_body.py` (CLI) — invoked as `--phase slice --slice N` to amend residual findings into `${id}/slice-N`'s commit message; serves both per-slice findings (`--slice N`) and carried coherence findings (`--slice 1`) (ref: Decision 4, Q5).
- `readImplementationCriticConfig(wd, id) -> ImplementationCriticConfig` (JS, in `qrspi-batch.js`) — round-trips the whole `critics` object via `--key critics` and digs `value.implementation`, never `--key critics.implementation` (ref: Q6, inconsistency 1, MEMORY: config reader is single-top-level-key only).
- `doImplementation(t, r)` (JS, modified) — runs the coherence pass at the seam (carries findings in memory), runs the per-slice critic inside the slice loop, surfaces both into PR bodies, and fails-closed on critic `ok:false` (ref: §Delta, AC1, AC2, Risk Register rows 2,3).

## Slice 1: Diff-scope/skip reducer (`qrspi_slice_critic.py`)

**Goal:** A standalone, unit-tested pure Python module that, given a `setup` blob and a 1-based slice index, returns the per-slice critic decision (run/skip + Graphite diff range). Verifiable entirely in isolation with stubbed dict inputs — no JS, no Graphite, no critic spawn.
**Files touched:**

- ✨ `scripts/qrspi_slice_critic.py` — the `decide(setup, slice_index)` reducer: `alreadyCommitted` skip, single-slice skip (`len(slices)==1`), and diff-base selection (`${id}/plan` for slice 1, `${id}/slice-(N-1)` otherwise).
- ✨ `scripts/qrspi_slice_critic_test.py` — stdlib-only `_test.py` sibling covering: slice 1 diff base = `${id}/plan`; slice N>1 diff base = `${id}/slice-(N-1)`; `alreadyCommitted` → skip with reason; `len(slices)==1` → single-slice skip; multi-slice non-committed → run.
**Verification:**
- [ ] `python3 scripts/qrspi_slice_critic_test.py` passes (all decision branches: two diff bases, two skip reasons, the run case).
**Context cost:** S
**Depends on:** none

## Slice 2: Extend `qrspi_critic_body.py` with the `slice` branch

**Goal:** The residual-findings-into-commit-message script can target a `${id}/slice-N` branch via `--phase slice --slice N`, the single mechanism that serves both per-slice and coherence surfacing. Verifiable in isolation against the script's existing `_test.py` plus the new `slice` case — independent of the JS wiring that will call it.
**Files touched:**

- ⚠️ `scripts/qrspi_critic_body.py` — add a `slice` entry to `_PHASE_BRANCH`; accept/route `--phase slice --slice N` to branch `${id}/slice-N`.
- ⚠️ `scripts/qrspi_critic_body_test.py` — add cases: `--phase slice --slice N` resolves to `${id}/slice-N`; existing `design`/`plan` paths unchanged (regression guard).
**Verification:**
- [ ] `python3 scripts/qrspi_critic_body_test.py` passes, including the new `slice` branch resolution and the unchanged design/plan cases.
**Context cost:** S
**Depends on:** none

## Slice 3: Wire the coherence pass + per-slice critic into `doImplementation`

**Goal:** The end-to-end implementation phase runs the whole-stack coherence pass once at the seam (carrying findings in memory), runs the per-slice edge critic inside the slice loop using the Slice-1 reducer and the existing `next_action` for converge/cap, routes non-pass to `qrspi_revise_amend.py`, surfaces both per-slice and carried-coherence residual findings into the correct PR bodies via the Slice-2 `slice` branch, reads `critics.implementation` config correctly, and fails-closed on any critic spawn `ok:false`. This is the cohesive orchestrator change — the config reader, the coherence-path resolution, the loop insertion, the surfacing calls, and the `ok:false` guards are mutually dependent and cannot be verified independently of one another. Verified by a documented manual end-to-end run on a multi-slice ticket (AC4).
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — in `doImplementation`: (1) `readImplementationCriticConfig` reader round-tripping `--key critics`; (2) resolve the six coherence-input paths inline (`art(wd,id,name)` × 5 + `r.ticketContentPath`, mirroring `doDesign` lines 1349-1360) with a fail-closed missing/empty guard, then run the coherence critic before the slice loop and carry its findings in memory; (3) inside the slice loop (post-commit), call the `qrspi_slice_critic.py` reducer for diff scope/skip, run the single-critic per-slice loop (omit `lenses`), route non-pass to `qrspi_revise_amend.py`, converge via existing `next_action`; (4) on slice-1 commit, surface BOTH slice-1 residual findings and carried coherence findings via `qrspi_critic_body.py --phase slice --slice 1` (and `--slice N` for each later slice's own residual findings); (5) handle coherence-critic and slice-critic `ok:false` as `skip(...)`, mirroring the implement/commit failure paths.
- ✨ `.claude/agents/qrspi-coherence-critic.md` — new agent prompt for the whole-stack coherence critic (the per-slice critic reuses the existing `qrspi-critic` agent).
- ⚠️ `.qrspi/config.example.json` — add a `critics.implementation` block (`enabled`, `maxRounds`, nested `coherence.{enabled,maxRounds}`).
- ⚠️ `.claude/skills/qrspi-implement/...` (the implement skill/agent wrapper, only if a doc reference to the new critic seam is needed) — documentation touch; mark NEW only if a wrapper file actually changes.
**Verification:**
- [ ] Documented manual end-to-end run on a multi-slice ticket: coherence pass runs once at the seam; per-slice critic runs per non-first/non-committed slice and skips on `alreadyCommitted`; a single-slice ticket skips the per-slice critic; residual findings appear in the slice-1 PR body (coherence) and each slice's PR body (per-slice); per-ticket result-summary line reports the run (AC4).
- [ ] Manual check: a forced critic spawn `ok:false` produces a `skip(...)` (no silent ship).
- [ ] Manual check: `critics.implementation` absent → critic disabled (byte-for-byte-unchanged path); present → enabled.
**Context cost:** L
**Depends on:** Slice 1, Slice 2

---

## Unverified Assumptions

- **Config shape for `critics.implementation`.** The design specifies the *read mechanism* (round-trip `--key critics`, dig `value.implementation`) and that a block is added to `.qrspi/config.example.json`, but not the exact field names/nesting. The structure above assumes `{ enabled, maxRounds, coherence: { enabled, maxRounds } }` by analogy to the existing design/plan critic config; the actual field names must be confirmed against the existing `critics.design`/`critics.plan` blocks during planning.
- **`next_action` signature.** The design names `qrspi_critic_loop.py::next_action(verdicts, round, max_rounds)` as reused verbatim; the exact parameter list/return shape is taken from the design's prose (ref: Q3, Decision 5) and not re-derived from code (no codebase reads allowed here). Planning must confirm the call site signature.
- **`art(wd,id,name)` / `r.ticketContentPath` / `doDesign` lines 1349-1360.** The design asserts these helpers and the inline panel-input resolution pattern exist in `qrspi-batch.js`. Structure trusts the design's Delta; the exact helper names and line anchors must be confirmed when editing the JS.
- **Whether a `qrspi-implement` wrapper/doc file needs editing.** Slice 3 lists a conditional doc touch; the design does not require it. Confirm during planning whether any skill/wrapper doc must reference the new critic seam, or drop the file from the slice.
- **AC4 "eval score before/after" is satisfied by manual e2e + summary line only** (OQ2 RESOLVED). No `run_eval.py` scoring exists; this is recorded so a reviewer does not expect a numeric eval delta artifact.
