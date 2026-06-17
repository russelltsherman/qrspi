# Work Tree — Node-validity lens for the plan phase: generalize the critic panel beyond design

**Plan basis:** plan.md @ 2026-06-17T00:00:00Z
**Generated:** 2026-06-17T00:00:00Z
**Status:** draft
**Total sessions:** 4
**Critical path:** T1 → T3 → T4 → T8 (Verify Slice 1) → T11 → T13 → T15 → T16 → T17 (Verify Slice 3 e2e) → T18 (Verify Slice 3 suite) → T21 → T22 (Verify Slice 4 teeth)

> Critical path = 12 tasks. Slice 3 is the convergence point: it depends on both Slice 1 (resolver shape + plan lens id) and Slice 2 (the spawnable agent file), so the longest chain runs Slice 1 → Slice 3 → Slice 4. Slice 2 is short and off the critical path (parallelizable with Slice 1).
>
> **Process precondition (outside this DAG):** rebase on RUS-82 once landed before editing the shared panel/config/wiring files (this family serializes). Holds before Session 1.

## Session 1 — Slice 1: Python resolver + config + tests for the plan whitelist

**Load:** structure.md §New Types (DEFAULT_PLAN_LENSES / KNOWN_PLAN_LENSES), structure.md §Contracts (resolve_plan), structure.md §Modified Types (EDGE_PHASES delta), plan.md §Slice 1
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add `DEFAULT_PLAN_LENSES: list[str] = []` constant in `qrspi_critics_config.py` | — | §1.1 | S | pending |
| T2 | Add `KNOWN_PLAN_LENSES = set(DEFAULT_PLAN_LENSES) \| {'plan-node-validity'}` constant | T1 | §1.2 | S | pending |
| T3 | Add standalone `resolve_plan(critics_cfg)` emitting `{enabled, maxRounds, lenses}`, validating against `KNOWN_PLAN_LENSES`, dropping unknowns with a warning | T2 | §1.3 | M | pending |
| T4 | Re-wire `resolve_critics` plan branch to `resolve_plan`; remove `plan` from `EDGE_PHASES` | T3 | §1.4 | S | pending |
| T5 | Document optional plan `lenses` knob in `.qrspi/config.example.json` (comment-only) | — | §1.5 | S | pending |
| T6 | Add plan lens-set membership + whitelist assertions in `qrspi_critics_config_test.py` | T2 | §1.6 | S | pending |
| T7 | Add `resolve_plan` behavior assertions (empty/kept/dropped/default-OFF; design unregressed) | T3 | §1.7 | M | pending |
| T8 | **Verify Slice 1** — `python3 scripts/run_tests.py critics_config` (plan asserts pass, design unregressed) | T4, T5, T6, T7 | §1.8 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 (Python) complete. Slice 2 is independent (no dependency on Slice 1) and touches a different file domain (agent markdown, not Python); a fresh context loads only the RUS-82 agent reference instead of the Python config surface.

## Session 2 — Slice 2: Plan node lens agent file (RUS-82 reuse alias)

**Load:** structure.md §Contracts (Slice 2 / agent file), `.claude/agents/qrspi-design-critic-design-review.md` (RUS-82 judging body to single-source), plan.md §Slice 2
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T9 | Create `.claude/agents/qrspi-plan-critic-plan-node-validity.md` — `tools: Read, Grep`; subject `PLAN_PATH`; consumes `STRUCTURE_PATH` (upstream), `DESIGN_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`, required `CODEBASE_PATH`; digest-opt-out; single-sources RUS-82 judging body with plan labels (no forked criteria) | — | §2.9 | M | pending |
| T10 | **Verify Slice 2** — file present at `agentTypeFor('plan','plan-node-validity')` path; frontmatter `tools: Read, Grep`; references PLAN_PATH/STRUCTURE_PATH/CODEBASE_PATH, no DESIGN_PATH-as-subject wording; judging matches RUS-82 | T9 | §2.10 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 is the convergence point — it depends on BOTH Slice 1 (resolver shape + plan lens id) and Slice 2 (the spawnable agent file must exist, since the loop fail-closes on a whitelisted id with no agent). A fresh context here loads the JS orchestrator surface plus the byte-for-byte design-call invariants, which were not needed for the prior Python/markdown work.

## Session 3 — Slice 3: Phase-generic panel loop + plan wiring in qrspi-batch.js

**Load:** structure.md §Modified Types (DEFAULT_CRITIC_PHASES.plan, planCritic), structure.md §Contracts (agentTypeFor, runCriticPanelLoop), structure.md §Delta (Q6/Q8/Q20), plan.md §Slice 3, impl-log.md §Slice 1 (resolved plan-block key set — notes only), impl-log.md §Slice 2 (agentType id — notes only)
**Estimated context:** ~32% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T11 | Update `DEFAULT_CRITIC_PHASES.plan` in `qrspi-batch.js` to mirror the resolver (`lenses: []` + digest/codebasePath/gateBehindEdge parallels, in lockstep with Python) | T8 | §3.11 | M | pending |
| T12 | Add `agentTypeFor(phase, lens)` helper mapping design+plan lens ids to agentTypes | T10 | §3.12 | S | pending |
| T13 | Parameterize `runCriticPanelLoop` on phase via `criticConfig.phaseLabel`/`subjectLabel`/`agentTypeFor` (UNCHANGED signature; design call byte-for-byte identical) | T11, T12 | §3.13 | L | pending |
| T14 | Set design `criticConfig` fields in `doDesign` (`phaseLabel:'design'`, `subjectLabel:'DESIGN_PATH'`, `agentTypeFor`) so the parameterized loop reproduces prior literals exactly | T13 | §3.14 | S | pending |
| T15 | Build plan lens config in `doPlan` (`lenses`, `codebasePath:wd`, `phaseLabel:'plan'`, `subjectLabel:'PLAN_PATH'`, `agentTypeFor`, upstream/input paths; subject = staged `plan.md`) | T13 | §3.15 | M | pending |
| T16 | Fold `criticMetrics`/`criticSummary` into `doPlan`'s finalize (mirror `doDesign`) | T15 | §3.16 | S | pending |
| T17 | **Verify Slice 3 (e2e)** — manual run with `lenses:['plan-node-validity']`: routes to panel loop, spawns plan lens agent, judges staged plan.md vs structure.md + codebase; no-lenses falls back to `runCriticLoop`; design run regresses green | T14, T16 | §3.17 | M | pending |
| T18 | **Verify Slice 3 (suite)** — `python3 scripts/run_tests.py` (lockstep covers plan block JS↔Python; full suite green) | T17 | §3.18 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 3 wiring complete and regression-green. Slice 4 is eval fixtures + a new teeth workflow — a separate file domain (evals/, teeth workflow JS) that only needs the now-live agentType and spawn path as facts, not the qrspi-batch.js internals. A fresh context keeps the eval authoring under budget.

## Session 4 — Slice 4: Plan teeth eval + fixtures (teeth + non-vacuity control)

**Load:** structure.md §New Types (LENS_MARKERS plan map), structure.md §Slice 4 Files, plan.md §Slice 4, `.claude/workflows/qrspi-teeth-eval.js` (design eval fan-out to mirror), impl-log.md §Slice 3 (live agentType + spawn path — notes only)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T19 | Create `evals/teeth/plan-flawed.md` — flawed fixture embedding marker `TEETH-PLAN-NODE-VALIDITY` on a step naming a non-existent symbol (false codebase claim) | T10 | §4.19 | S | pending |
| T20 | Create `evals/teeth/plan-clean.md` — known-clean plan control (non-vacuity: a never-catching lens must fail on it) | — | §4.20 | S | pending |
| T21 | Create `.claude/workflows/qrspi-teeth-plan-eval.js` — mirror design eval fan-out; plan fixtures, `LENS_MARKERS={'plan-node-validity':'TEETH-PLAN-NODE-VALIDITY'}`, plan agentType, `PLAN_PATH` label; pipe to `qrspi_teeth_assert.py`; OFF CI | T18, T19, T20 | §4.21 | M | pending |
| T22 | **Verify Slice 4 (teeth)** — `Workflow({name:"qrspi-teeth-plan-eval"})`: lens catches `TEETH-PLAN-NODE-VALIDITY` on flawed fixture by majority threshold | T21 | §4.22 | S | pending |
| T23 | **Verify Slice 4 (non-vacuity)** — clean-control assertion FAILS the eval for a never-catching lens; clean plan converges with zero fabricated findings | T22 | §4.23 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** All slices implemented and verified. Final boundary closes the DAG; next action is the plan/implementation PR submission, handled outside this work tree.
