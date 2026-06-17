# Implementation Plan — Node-validity lens for the plan phase: generalize the critic panel beyond design

**Structure basis:** structure.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft
**Total steps:** 23

## Slice 1: Python resolver + config + tests for the plan whitelist

### Setup

1. ⚠️ Modify `scripts/qrspi_critics_config.py` — add the plan default lens list constant near `DEFAULT_DESIGN_LENSES`.
   - **Current:** module defines `DEFAULT_DESIGN_LENSES` and `KNOWN_DESIGN_LENSES`; no plan lens constants.
   - **After:** add `DEFAULT_PLAN_LENSES: list[str] = []` (opt-in empty default; ref structure New Types, Decision 3 Option A).

2. ⚠️ Modify `scripts/qrspi_critics_config.py` — add the plan whitelist constant mirroring `KNOWN_DESIGN_LENSES`.
   - **Current:** only `KNOWN_DESIGN_LENSES` exists.
   - **After:** add `KNOWN_PLAN_LENSES: set[str] = set(DEFAULT_PLAN_LENSES) | {'plan-node-validity'}` (ref structure New Types, OQ2).

### Core Logic

3. ⚠️ Modify `scripts/qrspi_critics_config.py` — add the standalone `resolve_plan` function.
   - **Current:** plan is resolved by `resolve_edge_phase`, which emits `{enabled, maxRounds}` and silently ignores `lenses`.
   - **After:** add `resolve_plan(critics_cfg: dict) -> dict` that validates `critics.plan.lenses` against `KNOWN_PLAN_LENSES`, drops unknowns with a warning, and emits `{enabled, maxRounds, lenses}` with `lenses == []` when none configured — mirroring `resolve_design`'s per-phase shape WITHOUT touching `resolve_design` (ref Contracts, Decision 2 Option A).

4. ⚠️ Modify `scripts/qrspi_critics_config.py` — re-wire the `plan` branch of `resolve_critics`.
   - **Current:** `resolve_critics` routes `plan` through `resolve_edge_phase`; `plan` is a member of `EDGE_PHASES`.
   - **After:** `resolve_critics` routes `plan` through `resolve_plan`; remove `plan` from `EDGE_PHASES` (ref Modified Types, §Delta Q6).

### Config docs

5. ⚠️ Modify `.qrspi/config.example.json` — document the optional plan `lenses` knob.
   - **Current:** plan block comment reads "Single-edge-critic planning phase — same shape as 'questions' ('enabled' + 'maxRounds' only)."
   - **After:** comment documents the optional `lenses` knob naming `plan-node-validity`, mirroring the design block; example values stay `"enabled": false` / `"maxRounds": 2` with no lenses (still no-op) (ref §Delta, Slice 1 Files touched).

### Tests

6. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add plan lens-set membership + whitelist assertions.
   - Add: `plan-node-validity` is a member of `KNOWN_PLAN_LENSES`; plan whitelist order/content matches `set(DEFAULT_PLAN_LENSES) | {'plan-node-validity'}`.

7. ⚠️ Modify `scripts/qrspi_critics_config_test.py` — add `resolve_plan` behavior assertions.
   - Add: no `lenses` → empty `lenses` (routes single-critic / falsy); `['plan-node-validity']` → kept; an unknown id → dropped with a warning; default-OFF/empty invariant; opt-in-keep. Confirm design assertions are unregressed.

### Verify Slice 1

8. **Checkpoint:** `python3 scripts/run_tests.py critics_config`
   - [ ] All new plan assertions pass; design assertions unregressed.
   - [ ] `resolve_plan` with no `lenses` returns empty `lenses`; with `['plan-node-validity']` returns it; with an unknown id drops it with a warning.

---

## Slice 2: Plan node lens agent file (RUS-82 reuse alias)

### Setup

9. ✨ Create `.claude/agents/qrspi-plan-critic-plan-node-validity.md` — spawnable plan node-validity lens agent (thin alias single-sourcing the RUS-82 judging body).
   - Frontmatter `tools: Read, Grep`; subject label `PLAN_PATH`, phase word "plan-phase"; consumes `STRUCTURE_PATH` (immediate upstream), `DESIGN_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`, and required `CODEBASE_PATH`; opts out of digest (mirroring RUS-82) (ref Contracts, Slice 2, AC3, Decision 1 Option B).
   - The judging body includes/parameterizes the RUS-82 `qrspi-design-critic-design-review.md` criteria with plan labels; no forked judging logic. Map `structure.md` as the immediate upstream without breaking the inherited intent-vs-codebase verification prose (ref Unverified Assumptions: upstream-path label mapping).

### Verify Slice 2

10. **Checkpoint:** `test -f .claude/agents/qrspi-plan-critic-plan-node-validity.md && grep -E '^tools:.*Read.*Grep' .claude/agents/qrspi-plan-critic-plan-node-validity.md`
    - [ ] Agent file present at the path `agentTypeFor('plan','plan-node-validity')` produces (`qrspi-plan-critic-plan-node-validity`).
    - [ ] Frontmatter `tools: Read, Grep`; prompt references `PLAN_PATH`/`STRUCTURE_PATH`/`CODEBASE_PATH`, no `DESIGN_PATH`-as-subject wording; judging logic matches RUS-82's body (no forked criteria).

---

## Slice 3: Phase-generic panel loop + plan wiring in qrspi-batch.js

### Setup

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — update `DEFAULT_CRITIC_PHASES.plan` to mirror the resolver.
    - **Current:** `DEFAULT_CRITIC_PHASES.plan` is the bare `{ enabled: false, maxRounds: 2 }`.
    - **After:** `plan` carries an empty `lenses: []` plus the digest/codebasePath/gateBehindEdge parallels matching the design block, in lockstep with the resolver (ref Modified Types, §Delta, Q8). Define the exact JS↔Python plan-block key set against the current design block (ref Unverified Assumptions: which keys the plan block needs).

12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add the `agentTypeFor(phase, lens)` helper.
    - **Current:** the panel hardcodes `` `qrspi-design-critic-${lens}` ``.
    - **After:** add `agentTypeFor(phase, lens)` mapping `('design','design-review') → 'qrspi-design-critic-design-review'` and `('plan','plan-node-validity') → 'qrspi-plan-critic-plan-node-validity'` (ref Contracts `agentTypeFor`, Decision 1 Option B, OQ2).

### Core Logic

13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — parameterize `runCriticPanelLoop` on phase.
    - **Current:** `runCriticPanelLoop(name, id, criticConfig)` hardcodes agentType `` `qrspi-design-critic-${lens}` ``, the "design-phase" prompt word, and the `DESIGN_PATH` subject label.
    - **After:** UNCHANGED signature; reads `criticConfig.phaseLabel`, `criticConfig.subjectLabel`, and `criticConfig.agentTypeFor`/`agentTypePrefix` for the spawn prompt and agentType. Subject artifact still computed locally as `stg(id, name)`. Design-call behavior must be byte-for-byte unchanged (ref Contracts `runCriticPanelLoop`, AC2). Confirm the exact field shape against the current loop so the design call stays identical (ref Unverified Assumptions: criticConfig field names).

14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — set the design `criticConfig` fields so the design call is unchanged.
    - **Current:** `doDesign` builds `designCritic` without `phaseLabel`/`subjectLabel`/`agentTypeFor` (panel used hardcoded literals).
    - **After:** populate `phaseLabel: 'design'`, `subjectLabel: 'DESIGN_PATH'`, and `agentTypeFor` (or `agentTypePrefix`) on the design config so the now-parameterized loop reproduces the prior literals exactly.

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — build the plan lens config in `doPlan`.
    - **Current:** `doPlan` builds `planCritic` without `lenses`/`codebasePath`/phase labels.
    - **After:** add `lenses` (from the resolved plan critics), `codebasePath: wd`, `phaseLabel: 'plan'`, `subjectLabel: 'PLAN_PATH'`, `agentTypeFor`, and the upstream/input paths (`structure.md`, `design.md`, `research.md`, `questions.md`); subject-under-review remains the staged `plan.md` computed as `stg(id, name)` (ref Modified Types `planCritic`, §Delta, OQ3).

16. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — fold `criticMetrics`/`criticSummary` in `doPlan`'s finalize.
    - **Current:** `doPlan`'s finalize folds only `planFindings`, NOT `criticMetrics`/`criticSummary`.
    - **After:** extend the finalize to fold `criticMetrics`/`criticSummary` like `doDesign` (ref §Delta Q20, Risk Register).

### Verify Slice 3

17. **Checkpoint:** Manual end-to-end run with a plan config setting `lenses:['plan-node-validity']`.
    - [ ] Plan routes to `runCriticPanelLoop`, spawns `qrspi-plan-critic-plan-node-validity`, and judges the staged `plan.md` against `structure.md` + codebase.
    - [ ] A plan config with no `lenses` still routes to `runCriticLoop` (back-compat).
    - [ ] A design run regresses green — design inputs/outputs/agentType/prompt unchanged.

18. **Checkpoint:** `python3 scripts/run_tests.py` (lockstep + full suite regression gate)
    - [ ] The lockstep test covers the plan block (JS `DEFAULT_CRITIC_PHASES.plan` ↔ Python `resolve_plan` shape); full suite green.

---

## Slice 4: Plan teeth eval + fixtures (teeth + non-vacuity control)

### Setup

19. ✨ Create `evals/teeth/plan-flawed.md` — deliberately-flawed plan fixture.
    - Embed the unique quotable marker `TEETH-PLAN-NODE-VALIDITY` on a step naming a non-existent symbol (a false codebase claim / unsound approach, NOT a dropped step) (ref Slice 4 Files, AC5, Risk Register: vacuity).

20. ✨ Create `evals/teeth/plan-clean.md` — known-clean plan control (non-vacuity).
    - A clean plan that converges with zero fabricated findings; a never-catching lens must FAIL the eval on this control (ref Slice 4 Files, AC6).

### Core Logic

21. ✨ Create `.claude/workflows/qrspi-teeth-plan-eval.js` — new plan teeth workflow (Decision 4 Option B).
    - Mirror the design eval's fan-out structure; use the plan fixtures, the plan `LENS_MARKERS = { 'plan-node-validity': 'TEETH-PLAN-NODE-VALIDITY' }` map, the `qrspi-plan-critic-plan-node-validity` agentType, the `PLAN_PATH` label; pipe to `qrspi_teeth_assert.py` verbatim; OFF CI (ref structure New Types, Slice 4 Files, OQ4).

### Verify Slice 4

22. **Checkpoint:** `Workflow({name:"qrspi-teeth-plan-eval"})`
    - [ ] The lens catches the `TEETH-PLAN-NODE-VALIDITY` marker on the flawed fixture by the majority threshold.

23. **Checkpoint:** Inspect the clean-control assertion result from the same run.
    - [ ] The clean-control assertion FAILS the eval for a never-catching lens (non-vacuity), and the clean plan itself converges with zero fabricated findings.

---

## Rollback Notes

- **Step 5** (`.qrspi/config.example.json`): documentation/comment-only change; revert the comment text. Example values were never changed (still `enabled:false`/`maxRounds:2`, no lenses), so no runtime behavior to roll back.
- **Steps 3–4** (`resolve_plan` + `resolve_critics` re-wire): to roll back, restore the `plan` branch to `resolve_edge_phase` and re-add `plan` to `EDGE_PHASES`. Because `DEFAULT_PLAN_LENSES = []`, the resolver is a no-op for any unconfigured plan, so a roll back cannot strand a live plan panel.
- **Step 11** (`DEFAULT_CRITIC_PHASES.plan`): the JS mirror is consulted only on config-read failure; reverting to the bare `{ enabled:false, maxRounds:2 }` is safe as long as it is reverted in lockstep with Steps 3–4 (the lockstep test in Step 18 is the guard against drift).
- **No DB migrations or destructive ops** in this plan.

## Sequencing constraints (from structure Depends-on)

- Slice 1 and Slice 2 have no dependencies (parallelizable).
- Slice 3 depends on Slice 1 (resolver shape + plan lens id) and Slice 2 (the spawnable agent file must exist before its id is live — the loop fail-closes on a whitelisted id with no agent; ref Risk Register).
- Slice 4 depends on Slice 2 (the plan node lens agent) and Slice 3 (the phase-generic spawn path / agentType mapping).
- **Process precondition (outside code):** rebase on RUS-82 once landed before editing the shared panel/config/wiring files; this family must serialize (ref structure Unverified Assumptions, design Risk Register).
