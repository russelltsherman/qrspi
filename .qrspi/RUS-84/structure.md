# Structure Outline — Node-validity lens for the plan phase: generalize the critic panel beyond design

**Design basis:** design.md @ 2026-06-16T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft

## New Types

- `KNOWN_PLAN_LENSES: set[str]` (Python, `qrspi_critics_config.py`) — whitelist of acceptable plan lens ids, `= DEFAULT_PLAN_LENSES ∪ {'plan-node-validity'}`, mirroring `KNOWN_DESIGN_LENSES`.
- `DEFAULT_PLAN_LENSES: list[str] = []` (Python) — the opt-in default (empty), so an unconfigured plan stays on the single critic.
- `planCritic.lenses: string[]` (JS `criticConfig` shape extension on the plan branch) — resolved plan lens list; empty/absent → `runCriticLoop`, non-empty → `runCriticPanelLoop`.
- `criticConfig.phaseLabel: string` (JS) — phase word for the panel prompt, e.g. `"design"` / `"plan"`.
- `criticConfig.subjectLabel: string` (JS) — subject path label, e.g. `"DESIGN_PATH"` / `"PLAN_PATH"`.
- `criticConfig.agentTypeFor: (phase, lens) => string` (JS) OR an `agentTypePrefix` string — derives the spawnable agentType (e.g. `qrspi-plan-critic-plan-node-validity`) instead of the hardcoded `qrspi-design-critic-${lens}`.
- Teeth plan `LENS_MARKERS: { 'plan-node-validity': 'TEETH-PLAN-NODE-VALIDITY' }` (JS, in the new plan eval workflow).

## Modified Types

- `DEFAULT_CRITIC_PHASES.plan` (JS, `qrspi-batch.js`) — replace the bare `{ enabled: false, maxRounds: 2 }` with a block carrying an empty `lenses: []` (plus any `digest`/`codebasePath`/`gateBehindEdge` parallels to design), in lockstep with the resolver (ref: design.md §Delta, Q8).
- `criticConfig` (JS, the universal carrier) — add `phaseLabel`, `subjectLabel`, `agentTypeFor`/`agentTypePrefix` fields; consumed by `runCriticPanelLoop` (ref: §Delta AC2).
- `resolve_critics` `plan` branch (Python) — re-wire from `resolve_edge_phase` to new `resolve_plan`; drop `plan` from `EDGE_PHASES` if it no longer routes through `resolve_edge_phase` (ref: §Delta, Q6).
- `planCritic` object built in `doPlan` (JS) — add `lenses`, `codebasePath: wd`, `phaseLabel: 'plan'`, `subjectLabel: 'PLAN_PATH'`, and the upstream/input paths (`structure.md`, `design.md`, `research.md`, `questions.md`); subject-under-review remains the staged `plan.md` computed as `stg(id, name)` (ref: §Delta, OQ3).

## Contracts

- `resolve_plan(critics_cfg: dict) -> dict` (Python) — validates `critics.plan.lenses` against `KNOWN_PLAN_LENSES`, drops unknowns with a warning, emits `{enabled, maxRounds, lenses}` with `lenses == []` when none configured. Mirrors `resolve_design`'s per-phase shape (ref: Decision 2 Option A).
- `runCriticPanelLoop(name, id, criticConfig)` (JS) — UNCHANGED signature; now reads `criticConfig.phaseLabel`, `criticConfig.subjectLabel`, and `criticConfig.agentTypeFor`/`agentTypePrefix` for the spawn prompt and agentType instead of the hardcoded `"design-phase"` / `DESIGN_PATH` / `qrspi-design-critic-${lens}`. Subject artifact still computed locally as `stg(id, name)`. Design-call behavior must be byte-for-byte unchanged (ref: AC2).
- `agentTypeFor(phase: string, lens: string) -> string` (JS) — maps `('design','design-review') → 'qrspi-design-critic-design-review'` and `('plan','plan-node-validity') → 'qrspi-plan-critic-plan-node-validity'` (ref: Decision 1 Option B, OQ2).
- Plan node lens agent `qrspi-plan-critic-plan-node-validity` (`.claude/agents/`) — `tools: Read, Grep`; accepts `PLAN_PATH` (subject), `STRUCTURE_PATH`/`RESEARCH_PATH`/`DESIGN_PATH`/`QUESTIONS_PATH` (upstream inputs), `CODEBASE_PATH` (required). Includes/parameterizes the RUS-82 `qrspi-design-critic-design-review.md` judging body with plan labels; no forked judging logic (ref: AC3, Decision 1 Option B).
- `qrspi_teeth_assert.py::evaluate` / `_is_catch` (Python) — REUSED VERBATIM from stdin; keyed on the plan lens→marker map + threshold (ref: AC5, OQ4).

## Slice 1: Python resolver + config + tests for the plan whitelist

**Goal:** The Python resolver accepts an opt-in `critics.plan.lenses` validated against a plan whitelist, defaults empty (preserving single-critic back-compat), and is proven by unit tests — verifiable end-to-end via `python3 scripts/run_tests.py` with no JS changes yet.
**Files touched:**

- ⚠️ `scripts/qrspi_critics_config.py` — add `DEFAULT_PLAN_LENSES = []`, `KNOWN_PLAN_LENSES`, `resolve_plan`; re-wire the `plan` branch of `resolve_critics` to `resolve_plan`; remove `plan` from `EDGE_PHASES` if no longer edge-routed.
- ⚠️ `scripts/qrspi_critics_config_test.py` — add: plan lens-set membership, plan whitelist order-preservation, unknown-drop-with-warning, opt-in-keep, default-OFF/empty, plan node lens (`plan-node-validity`) whitelist acceptance, and absent/empty `lenses` → falsy (routes single-critic).
- ⚠️ `.qrspi/config.example.json` — replace the plan block comment with documentation of the optional `lenses` knob (naming `plan-node-validity`), mirroring the design block; example values stay `enabled:false`/`maxRounds:2`, no lenses (still no-op).
**Verification:**
- [ ] `python3 scripts/run_tests.py critics_config` passes (all new plan assertions green, design assertions unregressed)
- [ ] `resolve_plan` with no `lenses` returns empty `lenses`; with `['plan-node-validity']` returns it; with an unknown id drops it with a warning
**Context cost:** S
**Depends on:** none

## Slice 2: Plan node lens agent file (RUS-82 reuse alias)

**Goal:** A spawnable `qrspi-plan-critic-plan-node-validity` agent exists, single-sourcing the RUS-82 judging body with plan-appropriate labels, so the panel loop can spawn it without fail-closing. Verifiable by file existence + label inspection before any loop wires to it.
**Files touched:**

- ✨ `.claude/agents/qrspi-plan-critic-plan-node-validity.md` — thin alias including/parameterizing the RUS-82 `qrspi-design-critic-design-review.md` judging body; `tools: Read, Grep`; subject label `PLAN_PATH`, phase word "plan-phase"; consumes `STRUCTURE_PATH` (immediate upstream), `DESIGN_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`, and required `CODEBASE_PATH`; opts out of digest (mirroring RUS-82).
**Verification:**
- [ ] Agent file present at the path the `agentTypeFor('plan','plan-node-validity')` mapping produces
- [ ] Frontmatter `tools: Read, Grep`; prompt references `PLAN_PATH`/`STRUCTURE_PATH`/`CODEBASE_PATH`, no `DESIGN_PATH`-as-subject wording; judging logic matches RUS-82's body (no forked criteria)
**Context cost:** S
**Depends on:** none

## Slice 3: Phase-generic panel loop + plan wiring in qrspi-batch.js

**Goal:** `runCriticPanelLoop` is parameterized on phase; the JS `DEFAULT_CRITIC_PHASES.plan` mirror matches the resolver; `doPlan` threads the plan lens config + upstream paths + `codebasePath` and folds `criticMetrics`/`criticSummary`. End-to-end: an opt-in plan config runs the panel against `plan.md`; an absent `lenses` stays on `runCriticLoop`; design panel byte-for-byte unchanged.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — update `DEFAULT_CRITIC_PHASES.plan` to carry empty `lenses` (+ digest/codebase parallels) in lockstep with the resolver; parameterize `runCriticPanelLoop` on `phaseLabel`/`subjectLabel`/`agentTypeFor` (replacing `"design-phase"`/`DESIGN_PATH`/`qrspi-design-critic-${lens}`); add the `agentTypeFor(phase,lens)` helper; in `doPlan` build `planCritic` with `lenses`, `codebasePath: wd`, `phaseLabel:'plan'`, `subjectLabel:'PLAN_PATH'`, upstream paths (`structure.md`/`design.md`/`research.md`/`questions.md`); extend `doPlan`'s finalize to fold `criticMetrics`/`criticSummary` like `doDesign`.
**Verification:**
- [ ] Manual end-to-end: a plan config with `lenses:['plan-node-validity']` routes plan to `runCriticPanelLoop`, spawns `qrspi-plan-critic-plan-node-validity`, and judges the staged `plan.md` against `structure.md` + codebase
- [ ] Manual end-to-end: a plan config with no `lenses` still routes to `runCriticLoop` (back-compat)
- [ ] A design run regresses green — design inputs/outputs/agentType/prompt unchanged
**Context cost:** M
**Depends on:** Slice 1 (resolver shape + plan lens id), Slice 2 (spawnable agent must exist before its id is live)

## Slice 4: Plan teeth eval + fixtures (teeth + non-vacuity control)

**Goal:** A deliberately-flawed plan fixture makes the plan node lens fail and cite the defect, and a clean control converges — proving the plan panel keeps its teeth non-vacuously, reusing `qrspi_teeth_assert.py` verbatim.
**Files touched:**

- ✨ `evals/teeth/plan-flawed.md` — flawed plan fixture embedding the unique marker `TEETH-PLAN-NODE-VALIDITY` on a step naming a non-existent symbol (a false codebase claim / unsound approach, not a dropped step).
- ✨ `evals/teeth/plan-clean.md` — known-clean plan control (non-vacuity: a never-catching lens must FAIL the eval).
- ✨ `.claude/workflows/qrspi-teeth-plan-eval.js` — new workflow (Decision 4 Option B) mirroring the design eval's fan-out; uses plan fixtures, the plan `LENS_MARKERS` map, the `qrspi-plan-critic-plan-node-validity` agentType, `PLAN_PATH` label; pipes to `qrspi_teeth_assert.py` verbatim; OFF CI.
**Verification:**
- [ ] `Workflow({name:"qrspi-teeth-plan-eval"})` run: the lens catches the marker on the flawed fixture by the majority threshold
- [ ] The clean-control assertion FAILS the eval for a never-catching lens (non-vacuity), and the clean plan itself converges with zero fabricated findings
**Context cost:** M
**Depends on:** Slice 2 (the plan node lens agent), Slice 3 (the phase-generic spawn path / agentType mapping)

---

## Unverified Assumptions

- **JS `criticConfig` field names** (`phaseLabel`, `subjectLabel`, `agentTypeFor`/`agentTypePrefix`) are design-proposed examples, not mapped to existing code symbols — the implementer must confirm the exact field shape against the current `runCriticPanelLoop` / `doDesign` so the design call stays byte-for-byte unchanged (design.md §Delta lists them as "e.g.").
- **`gateBehindEdge`/`digest`/`candidates` parallels on `DEFAULT_CRITIC_PHASES.plan`** — design says "any digest/codebase parallels" without pinning which keys the plan block needs; the lockstep test must define the exact JS↔Python plan-block contract (Risk Register: lockstep drift).
- **Whether `resolve_plan` is a standalone function vs a parameterized reuse of the design lens-filter loop** — Decision 2 picks Option A (standalone) but the design also says "(or parameterize the existing design lens-filter loop)"; the implementer should not touch `resolve_design`'s loop (Option A), keeping blast radius off the landed design path.
- **Exact upstream-path label names the plan node lens agent expects** (`STRUCTURE_PATH` vs reusing `RESEARCH_PATH` semantics) — OQ3 names the set but the RUS-82 agent body uses `RESEARCH_PATH` for intent-vs-codebase verification; the alias must map `structure.md` as the immediate upstream without breaking the inherited verification prose.
- **RUS-82 serialization dependency** — design Risk Register flags this family edits the same panel/config/wiring files as RUS-82 and must rebase on RUS-82 once landed before editing; this is a process precondition outside the code structure, surfaced for human attention before planning.
