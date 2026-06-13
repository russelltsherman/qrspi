# Implementation Plan — qrspi critics 4/5 — Stage 3 (Implementation): per-slice code critics + whole-stack coherence pass

**Structure basis:** structure.md @ 2026-06-13T21:35:00Z
**Generated:** 2026-06-13T21:55:00Z
**Status:** draft
**Total steps:** 24

## Slice 1: Diff-scope/skip reducer (`qrspi_slice_critic.py`)

### Setup

1. ✨ Create `scripts/qrspi_slice_critic.py` — new stdlib-only pure module exposing the diff-scope/skip reducer `decide(setup, slice_index)`. No imports beyond stdlib; mirrors the dict-in/dict-out convention of `qrspi_critic_loop.py`.

### Core Logic

2. ✨ In `scripts/qrspi_slice_critic.py`, implement `decide(setup, slice_index) -> SliceCriticDecision` per structure.md contract:
   - Inputs: `setup = { slices: [ { alreadyCommitted: bool }, ... ], id: str }`, `slice_index` (1-based int).
   - Return shape `{ run: bool, skipReason: "alreadyCommitted" | "single-slice" | None, diffBase: str | None, diffHead: str | None }`.
   - Skip branch A (`alreadyCommitted`): when `setup["slices"][slice_index-1]["alreadyCommitted"]` is true → `{ run: False, skipReason: "alreadyCommitted", diffBase: None, diffHead: None }` (ref: Decision 1A, Decision 5, Q10).
   - Skip branch B (`single-slice`): when `len(setup["slices"]) == 1` → `{ run: False, skipReason: "single-slice", diffBase: None, diffHead: None }` (ref: Decision 7, Q10).
   - Run branch: else → `run: True`, `skipReason: None`, `diffHead = f"{id}/slice-{slice_index}"`, and `diffBase = f"{id}/plan"` when `slice_index == 1` else `f"{id}/slice-{slice_index-1}"` (ref: Decision 1A, Q11).
   - Resolve skip precedence: evaluate `single-slice` only when not already `alreadyCommitted` (a single committed slice yields `alreadyCommitted`, matching the resume-skip intent of Q10).

3. ✨ In `scripts/qrspi_slice_critic.py`, add a `__main__` guard only if needed for CLI parity with sibling pure modules; otherwise leave the module import-only (the JS caller shells out to read JSON). Decide by matching the invocation style of `scripts/qrspi_critic_loop.py` (confirm during edit whether it exposes a CLI or is import-only).

### Tests

4. ✨ Create `scripts/qrspi_slice_critic_test.py` — stdlib-only `_test.py` sibling (`unittest` or assert-based, matching the existing `scripts/qrspi_*_test.py` style) covering every branch from structure.md §Verification:
   - slice 1, multi-slice, non-committed → `run=True`, `diffBase == f"{id}/plan"`, `diffHead == f"{id}/slice-1"`.
   - slice N>1, multi-slice, non-committed → `run=True`, `diffBase == f"{id}/slice-(N-1)"`, `diffHead == f"{id}/slice-N"`.
   - `alreadyCommitted` slice → `run=False`, `skipReason == "alreadyCommitted"`.
   - `len(slices) == 1` → `run=False`, `skipReason == "single-slice"`.
   - multi-slice non-committed run case asserts no skip reason set.

### Verify Slice 1

5. **Checkpoint:** `python3 scripts/qrspi_slice_critic_test.py`
   - [ ] All decision branches pass (two diff bases, two skip reasons, the run case).
   - [ ] Exit code 0.

---

## Slice 2: Extend `qrspi_critic_body.py` with the `slice` branch

### Setup

6. ⚠️ Modify `scripts/qrspi_critic_body.py` — read the existing `_PHASE_BRANCH` mapping and the `--phase` argument parsing to learn current shape before editing.
   - **Current:** `_PHASE_BRANCH` maps only `design` → `${id}/design` and `plan` → `${id}/plan`; CLI accepts `--phase {design,plan}`.
   - **After:** `_PHASE_BRANCH` additionally resolves a `slice` phase to `${id}/slice-N` using a new `--slice N` argument.

### Core Logic

7. ⚠️ Modify `scripts/qrspi_critic_body.py` — add a `slice` entry / branch-resolution path to `_PHASE_BRANCH` (or its resolver function) that consumes `--slice N` and returns `f"{id}/slice-{N}"`.
   - **Current:** branch is looked up by `--phase` key alone (`design`/`plan`), no slice index.
   - **After:** `--phase slice --slice N` resolves to `f"{id}/slice-{N}"`; `--phase design|plan` paths unchanged.

8. ⚠️ Modify `scripts/qrspi_critic_body.py` — extend `argparse` (or equivalent) to accept `--slice` (int), required only when `--phase slice`; design/plan invocations must not require `--slice`.
   - **Current:** no `--slice` argument exists.
   - **After:** `--slice N` parsed and routed into branch resolution; absent/ignored for design/plan.

### Tests

9. ⚠️ Modify `scripts/qrspi_critic_body_test.py` — add cases per structure.md §Verification:
   - `--phase slice --slice N` resolves to `f"{id}/slice-{N}"` (e.g. N=1 and N>1).
   - Existing `--phase design` and `--phase plan` resolutions still produce their original branches (regression guard).
   - The residual-findings section rendering / commit-message amend behavior is unchanged for the new `slice` path (reuses existing rendering).

### Verify Slice 2

10. **Checkpoint:** `python3 scripts/qrspi_critic_body_test.py`
    - [ ] New `slice` branch resolution cases pass (`slice-1` and `slice-N`).
    - [ ] Pre-existing `design`/`plan` cases still pass (no regression).
    - [ ] Exit code 0.

---

## Slice 3: Wire the coherence pass + per-slice critic into `doImplementation`

> Depends on: Slice 1 (`qrspi_slice_critic.py`), Slice 2 (`qrspi_critic_body.py` `slice` branch). This is one cohesive orchestrator change; the steps below land together and are verified by a single documented manual end-to-end run (AC4) — they are not independently testable.

### Setup — confirm anchors (read-only, per structure.md Unverified Assumptions)

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — first locate and confirm the anchors the design asserts, before writing code: the `doDesign` panel-input resolution at the cited region (design.md says lines ~1349-1360), the `art(wd,id,name)` helper, `r.ticketContentPath`, the existing `critics.design`/`critics.plan` config blocks, and the `next_action` call site signature (`next_action(verdicts, round, max_rounds)`). Confirm the exact `critics.implementation` field names against the existing `critics.design`/`critics.plan` blocks (structure.md Unverified Assumption 1). If any anchor differs, plan the edit to the actual code, not the asserted line numbers.

### Core Logic — config reader

12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `readImplementationCriticConfig(wd, id) -> ImplementationCriticConfig` that round-trips the whole `critics` object via `--key critics`, parses the JSON value, and digs `value.implementation` (never `--key critics.implementation`; MEMORY: config reader is single-top-level-key only).
    - **Current:** no implementation-critic config reader exists.
    - **After:** returns `{ enabled, maxRounds, coherence: { enabled, maxRounds } }`; absent block / missing `implementation` key → disabled defaults (`enabled: false`).

### Core Logic — coherence pass at the seam

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — inside `doImplementation`, before the slice loop, resolve the six coherence-input paths inline: `art(wd, id, name)` for the five phase artifacts (questions, research, design, structure, plan/worktree as the existing `doDesign` panel does) + `r.ticketContentPath` for the ticket, mirroring the confirmed `doDesign` panel-input region.
    - **Current:** `doImplementation` resolves no coherence inputs; runs `impl-setup` then the slice loop directly.
    - **After:** six artifact paths resolved inline ahead of the slice loop.

14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a fail-closed guard: if any of the six resolved paths is missing or empty, return `skip(...)` (mirroring existing implement/commit failure paths) before spawning the coherence critic (ref: Risk Register row 3, Decision 6, pattern 7).
    - **Current:** no missing/empty-input guard at the seam.
    - **After:** missing/empty coherence input → `skip(...)`, no critic spawn.

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — run the coherence critic once at the seam (gated on `readImplementationCriticConfig(...).coherence.enabled`), spawning the new `qrspi-coherence-critic` agent against the six artifacts; capture its `{ ok, residualFindings }` (or `{ pass, findings }` converged via `next_action` up to `coherence.maxRounds`) and carry residual findings in an in-memory variable through `doImplementation` (NOT surfaced at the seam — no slice commit exists yet; ref: AC2, Decision 4).
    - **Current:** no coherence pass runs in `doImplementation`.
    - **After:** coherence critic runs once pre-loop when enabled; findings carried in memory.

16. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — handle a coherence-critic spawn failure (`ok:false`) as `skip(...)`, mirroring the existing implement/commit failure paths (no silent ship; ref: Risk Register row 2, Q8).
    - **Current:** no `ok:false` handling for a coherence critic (it does not exist).
    - **After:** coherence-critic `ok:false` → `skip(...)`.

### Core Logic — per-slice critic inside the loop

17. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — inside the slice loop, after the slice-commit worker creates `${id}/slice-N` (post-commit), call the Slice-1 `qrspi_slice_critic.py` reducer (shell out, parse JSON) with the `setup` blob and the 1-based slice index to get the `{ run, skipReason, diffBase, diffHead }` decision. When `run` is false, skip the per-slice critic for this slice (covers `alreadyCommitted` resume and the single-slice ticket).
    - **Current:** the slice loop commits each slice then proceeds; no per-slice critic.
    - **After:** per-slice critic gated by the reducer's `run`/`skipReason`.

18. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — when `run` is true, run the single-critic per-slice loop: spawn the EXISTING `qrspi-critic` agent against the slice diff `${diffBase}..${diffHead}`, using `s.planSlice` (and `s.structureSlice`) from the in-memory `impl-setup` blobs as the rubric, with a `criticConfig` that OMITS `lenses` (single-critic path; ref: AC3, Risk Register row 1). Drive converge/revise/cap via the EXISTING `qrspi_critic_loop.py::next_action(verdicts, round, max_rounds)` with `max_rounds = config.maxRounds` (NOT re-implemented; ref: Decision 5).
    - **Current:** no per-slice critic loop.
    - **After:** single-critic converge loop per runnable slice, capped by `next_action`.

19. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — route a non-pass per-slice verdict to the existing `qrspi_revise_amend.py --branch ${id}/slice-N` revise path, then re-run the critic on the amended branch within the `next_action` round budget; on `cap_reached`, ship-with-disclosure (do not block; ref: Decision 2, Q8).
    - **Current:** no revise path is triggered from the implementation seam.
    - **After:** per-slice non-pass → `qrspi_revise_amend.py` amend, re-critique, cap = ship-with-disclosure.

20. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — handle a per-slice-critic spawn failure (`ok:false`) as `skip(...)`, mirroring the implement/commit failure paths (ref: Risk Register row 2, Q8).
    - **Current:** no per-slice-critic `ok:false` handling.
    - **After:** per-slice-critic `ok:false` → `skip(...)`.

### Core Logic — surface residual findings into PR bodies

21. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — surface residual findings via the Slice-2 `slice` branch of `qrspi_critic_body.py` (`--phase slice --slice N`):
    - On slice-1 commit: surface BOTH the slice-1 per-slice residual findings AND the carried coherence residual findings into the slice-1 PR body via `--phase slice --slice 1` (ref: Decision 4, AC2 timing — coherence findings exist before the commit, written only after).
    - On each later slice N commit: surface that slice's own residual findings via `--phase slice --slice N`.
    - **Current:** implementation PR bodies carry no critic residual findings (`criticBodyStep`/`_PHASE_BRANCH` were design/plan-only).
    - **After:** slice-1 body carries per-slice + coherence findings; slice-N body carries its own findings.

### New agent prompt + config

22. ✨ Create `.claude/agents/qrspi-coherence-critic.md` — new agent prompt for the whole-stack coherence critic: reads the six artifacts, judges whole-stack intent drift, returns `{ pass, findings }` in the same shape `qrspi-critic` returns so `next_action` and `qrspi_critic_body.py` consume it unchanged. (The per-slice critic reuses the existing `qrspi-critic` agent — no new prompt for it.)

23. ⚠️ Modify `.qrspi/config.example.json` — add a `critics.implementation` block with the field names confirmed in step 11: `{ enabled, maxRounds, coherence: { enabled, maxRounds } }`, defaulting to OFF/disabled to preserve the byte-for-byte-unchanged path when absent.
    - **Current:** `critics` has only `design`/`plan` blocks.
    - **After:** `critics.implementation` documented with nested `coherence`.

   > Conditional (structure.md Unverified Assumption 4): if step 11 confirms a `qrspi-implement` skill/agent wrapper doc must reference the new critic seam, add that doc touch here as a sub-step; otherwise drop it. Do NOT mark a wrapper file NEW unless it actually changes.

### Verify Slice 3

24. **Checkpoint:** Documented manual end-to-end run on a multi-slice ticket (AC4), plus the forced-failure and config-absent checks:
    - [ ] Coherence pass runs once at the seam; its residual findings appear in the slice-1 PR body.
    - [ ] Per-slice critic runs per non-first/non-committed slice and skips on `alreadyCommitted` (resume) and on a single-slice ticket.
    - [ ] Per-slice residual findings appear in each slice's own PR body.
    - [ ] A forced critic spawn `ok:false` (coherence or per-slice) produces a `skip(...)` — no silent ship.
    - [ ] `critics.implementation` absent → critic disabled (byte-for-byte-unchanged path); present/enabled → runs.
    - [ ] Per-ticket result-summary line reports the run.
    - [ ] `python3 scripts/qrspi_slice_critic_test.py && python3 scripts/qrspi_critic_body_test.py` still pass (no regression from the JS wiring).

---

## Rollback Notes

- **Step 23 (`.qrspi/config.example.json`):** config-example change. Rollback = remove the `critics.implementation` block. Because the reader (step 12) defaults to disabled when the block is absent, removing it restores the byte-for-byte-unchanged single-produce path; no migration needed.
- **Steps 12–21 (`.claude/workflows/qrspi-batch.js`):** orchestrator changes. Rollback = revert the `doImplementation` edits and the `readImplementationCriticConfig` reader; the slice loop returns to commit→pr→finalize with no critic. No persisted state or branches are mutated by the wiring itself beyond the existing revise-amend (step 19), which only amends an already-committed slice branch.
- **Step 19 (`qrspi_revise_amend.py` amend):** a per-slice revise amends an existing `${id}/slice-N` branch commit. Rollback of a mistaken amend follows the existing revise-amend recovery (re-checkout the branch, `gt modify` back, or close/recreate the slice PR) — no new destructive surface beyond what `doRevise` already carries.
- Steps 1–10 (new `scripts/qrspi_slice_critic.py` + `_test.py`, and the additive `qrspi_critic_body.py` `slice` branch) are purely additive/back-compatible. Rollback = delete the new files / revert the additive branch; existing design/plan paths are untouched.
