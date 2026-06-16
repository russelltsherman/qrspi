# Implementation Plan — Holistic design critic: adversarial node-validity lens with codebase access

**Structure basis:** structure.md @ 2026-06-16T00:00:00Z
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft
**Total steps:** 19

## Slice 1: Config whitelist decoupling (default-OFF, opt-in) + tests

### Core Logic

1. ⚠️ Modify `scripts/qrspi_critics_config.py` — decouple the whitelist from the default set so `design-review` is whitelist-acceptable but inactive by default (ref: structure.md Slice 1, design.md Decision 2 Option B).
   - **Current:** `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES)` (whitelist *is* the default-active four).
   - **After:** `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}`; `DEFAULT_DESIGN_LENSES` left as the existing four unchanged.

2. ⚠️ Modify `scripts/qrspi_critics_config.py` — add a code comment immediately above the redefined `KNOWN_DESIGN_LENSES` recording the deliberate whitelist/default decoupling and the default-OFF intent (ref: structure.md Slice 1, design.md Risk: whitelist/default desync).
   - **Current:** no comment marking the relationship between `KNOWN_DESIGN_LENSES` and `DEFAULT_DESIGN_LENSES`.
   - **After:** comment states `design-review` is whitelisted (config-addable) but deliberately NOT in `DEFAULT_DESIGN_LENSES` (default-OFF); do not re-couple.

### Tests

3. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add an assertion that the default resolved set of `resolve_design` (config without a `critics.design.lenses` entry) is still exactly the existing four lenses, `design-review` absent (ref: structure.md Slice 1, design.md AC3/AC8).
   - **Current:** existing whitelist keep/drop assertions over the four lenses.
   - **After:** plus a test asserting default resolve = the four (default-OFF invariant pinned).

4. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add an assertion that `resolve_design` DROPS `design-review` (with the documented warning) when a config lists it nowhere it is admitted, i.e. an unlisted lens is filtered (ref: structure.md Slice 1, design.md AC8).
   - **Current:** drop assertions for arbitrary unknown ids.
   - **After:** plus an explicit assertion that an unlisted `design-review` does not appear in the resolved set.

5. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add an assertion that `resolve_design` KEEPS `design-review` when a config lists it in `critics.design.lenses` (opt-in activation survives the whitelist filter) (ref: structure.md Slice 1, design.md AC3/AC8).
   - **Current:** keep assertions for the default four only.
   - **After:** plus an assertion that a config listing `design-review` yields a resolved set containing `design-review`.

6. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add an assertion that an empty-after-filter resolve still falls back to `DEFAULT_DESIGN_LENSES` (the four), confirming the empty-fallback path is unaffected by the whitelist change (ref: structure.md Slice 1, design.md Decision 2).
   - **Current:** existing empty-fallback assertion (if present) or none.
   - **After:** explicit assertion that a config resolving to empty falls back to the four.

7. Run: `python3 scripts/run_tests.py qrspi_critics_config`
   - **Expected:** all `qrspi_critics_config` assertions pass (new keep/drop/default/fallback green).

### Verify Slice 1

8. **Checkpoint:** `python3 scripts/run_tests.py`
   - [ ] `python3 scripts/run_tests.py qrspi_critics_config` passes (new assertions green).
   - [ ] Full suite stays green (no regression in synthesize/teeth-assert tests).
   - [ ] `DEFAULT_DESIGN_LENSES` is still the four (default-OFF preserved); `design-review` present only in `KNOWN_DESIGN_LENSES`.

---

## Slice 2: Node-validity lens agent + panel wiring + teeth defect + tests

### Setup

9. ✨ Create `.claude/agents/qrspi-design-critic-design-review.md` — the node-validity lens agent (ref: structure.md Slice 2, design.md AC1/AC2/AC4/AC7, Decision 1, Decision 5).
   - Frontmatter `tools: Read, Grep` (comma-list form; no Bash, no model key).
   - Prose: phase-generic "find what is materially wrong" framing — architectural soundness, correctness, failure modes, edge cases, operability, testability, security/perf, alternatives not considered; avoids hardcoding the word "design" in its reasoning.
   - Consumes exactly `DESIGN_PATH` ("the artifact under review"), `RESEARCH_PATH` ("the upstream input"), `CODEBASE_PATH` (repo root to Read/Grep) by those exact variable names.
   - Digest opt-out: reads full `RESEARCH_PATH` even when `DIGEST_PATH` is present.
   - Severity bar: blocking-only findings, `pass:false ⟺ findings non-empty`; sound-but-imperfect design returns `pass:true, findings:[]`; stylistic notes not emitted into structured `findings`.
   - Findings must cite a real source location.
   - Emits the standard `{pass, findings}` verdict (`CRITIC_VERDICT_SCHEMA` shape).
   - Records target-model intent (strongest available / Opus-tier) as a doc note only — NOT wired via `lensModel`.

### Core Logic

10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a `codebasePath` field to the `designCritic` object assembled in `doDesign`, sourced from the worktree root `wd` in scope (ref: structure.md Slice 2, design.md §Delta item 2, Decision 1).
    - **Current:** `designCritic` object assembled in `doDesign` without a `codebasePath` field.
    - **After:** `designCritic` includes `codebasePath: wd`.

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `runCriticPanelLoop`, splice a uniform `CODEBASE_PATH: <criticConfig.codebasePath>` line into every lens prompt (mirroring the uniform `digestLine` application), using that exact variable name (ref: structure.md Slice 2, design.md §Delta item 3, Decision 3 Option A).
    - **Current:** loop threads `DESIGN_PATH`/`TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH` (+ optional `DIGEST_PATH`); no `CODEBASE_PATH`.
    - **After:** a uniform `CODEBASE_PATH` line is also spliced into every lens prompt.

12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — replace the hard-coded "Read all four paths" prompt wording in `runCriticPanelLoop` with path-agnostic wording (a fifth/sixth input now exists) (ref: structure.md Slice 2, design.md §Delta item 3, Risk: "Read all four paths" miscount).
    - **Current:** prompt text says "Read all four paths" (already wrong-by-one with `DIGEST_PATH`).
    - **After:** path-agnostic wording with no hard-coded path count; existing variable names unchanged; JS `DEFAULT_DESIGN_LENSES` fallback left as the four; `lensModel` NOT set.

### Teeth

13. ⚠️ Modify `evals/teeth/design.md` — add a labelled node-defect: an unverifiable codebase claim (a false assertion about real source — a symbol/file that genuinely does not exist in this repo) carrying a unique marker (ref: structure.md Slice 2, design.md AC5, OQ3).
    - **Current:** flawed design fixture with markers for `completeness`/`internal-consistency`/`edge-alignment` only.
    - **After:** plus a `design-review`-owned codebase-claim defect with its own unique marker; the false symbol must be verified absent from the repo at implementation time.
    - Rollback note: see Rollback Notes (fixture edit; revert the added defect block).

14. ⚠️ Modify `.claude/workflows/qrspi-teeth-eval.js` — add a `design-review: <unique marker>` entry to `LENS_MARKERS` (matching the marker added to `evals/teeth/design.md`), so `LENSES = Object.keys(LENS_MARKERS)` then includes `design-review`. **This is the SOLE activation lever for the teeth eval** — the eval is a standalone fan-out and has no `critics.design.lenses` config / does not call `resolve_design`, so the default-OFF whitelist is irrelevant here (ref: structure.md Slice 2, design.md §Delta item 4, AC5).
    - **Current:** `LENS_MARKERS` maps `completeness`/`internal-consistency`/`edge-alignment` markers.
    - **After:** plus `design-review` → its unique marker.

15. ⚠️ Modify `.claude/workflows/qrspi-teeth-eval.js` — **thread `CODEBASE_PATH` into the eval's OWN inline lens prompt** (~L126-137), pointing at the engine/repo root that `engineCmd` resolves against, and replace the eval's hard-coded "Read all four paths" wording with path-agnostic wording. The teeth eval does NOT call `runCriticPanelLoop`, so step 11's loop-side `CODEBASE_PATH` splice does NOT reach it — without this edit the `design-review` lens gets no repo path, cannot Read/Grep source, and **AC5/AC2 cannot pass** (ref: structure.md Slice 2, design.md §Delta item 4; review finding: teeth eval bypasses the loop).
    - **Current:** the eval's inline prompt threads `DESIGN_PATH`/`TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH`/`DIGEST_PATH` and says "Read all four paths" — no `CODEBASE_PATH`. (There is no `critics.design.lenses` in the eval; activation is via `LENS_MARKERS`, step 14.)
    - **After:** the eval's inline prompt also threads `CODEBASE_PATH = <engine/repo root>` with path-agnostic wording, so `design-review` can verify the codebase-claim defect against real source.

### Tests

16. ⚠️ Modify `scripts/qrspi_critic_synthesize_test.py` — add a five-lens reduction assertion: the unchanged AND-reducer passes only when all five (including `design-review`) pass and fails when any one fails (ref: structure.md Slice 2, design.md AC8).
    - **Current:** synthesize assertions over the four-lens verdict list.
    - **After:** plus a five-lens reduction case (all-pass → pass; one-fail → fail).

17. ⚠️ Modify `scripts/qrspi_teeth_assert_test.py` — if the marker/owning-lens map is asserted there, add the `design-review` marker to the asserted map (ref: structure.md Slice 2, design.md §Delta tests, AC8).
    - **Current:** teeth-assert tests cover the three existing markers.
    - **After:** plus the `design-review` marker in the asserted marker/owning-lens mapping.

18. Run: `python3 scripts/run_tests.py`
    - **Expected:** full suite passes (five-lens synthesize + teeth-assert additions green).

### Verify Slice 2

19. **Checkpoint:** `python3 scripts/run_tests.py`
    - [ ] Full suite passes (five-lens synthesize + teeth-assert additions green).
    - [ ] Agent frontmatter is `tools: Read, Grep` — no Bash, no model key.
    - [ ] Manual/teeth e2e: `Workflow({name:"qrspi-teeth-eval"})` (lens active via `LENS_MARKERS`; `CODEBASE_PATH` threaded into the eval prompt) — the `design-review` lens fails citing the codebase-claim marker, having Read/Grep'd real source to confirm the claimed symbol is absent (AC5/AC2).
    - [ ] AC6 (no noise): run the activated panel over a **known-clean, previously-passed real design** — name the specific committed `design.md` used (there is no clean teeth fixture) — and confirm `design-review` returns `pass:true, findings:[]` (AC6).

---

## Rollback Notes

- Step 1/2 (config change): revert `KNOWN_DESIGN_LENSES` to `set(DEFAULT_DESIGN_LENSES)` and remove the decoupling comment to restore the original whitelist=default coupling. No data migration; pure-logic change covered by tests.
- Step 13 (teeth fixture edit): the `design-review` defect block is additive to `evals/teeth/design.md`; remove the added marked block to restore the prior fixture. The `evals/` harness is a non-functional placeholder, so this affects only the dedicated `qrspi-teeth-eval` run, not CI.
- Steps 14/15 (teeth-eval wiring): remove the `design-review` entry from `LENS_MARKERS` and the `design-review` entry from the eval's `critics.design.lenses` to deactivate the lens in the teeth run. Default-OFF means no production panel is affected by leaving or removing these.
- Steps 10–12 (qrspi-batch.js wiring): the `codebasePath` field and the spliced `CODEBASE_PATH` line are additive; reverting them removes the path from all lens prompts. Since `design-review` is default-OFF, the four default lenses ignore the path and are unaffected either way.
