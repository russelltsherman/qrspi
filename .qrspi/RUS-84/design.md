# Design — Node-validity lens for the plan phase: generalize the critic panel beyond design

**Ticket:** RUS-84
**Research basis:** research.md @ /workspaces/qrspi/.worktrees/RUS-84/.qrspi/RUS-84/research.md
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft

## Current State

The critic panel mechanism is design-only today. `runCriticPanelLoop(name, id, criticConfig)` reads every path off the single `criticConfig` object — `upstreamPath`, `ticketContentPath`, `questionsPath`, `codebasePath` — and computes the artifact-under-review locally as `stg(id, name)`; the design-specific paths are assembled in `doDesign` (ref: Q1). `CODEBASE_PATH` is threaded uniformly into each lens prompt as a `codebaseLine` built from `criticConfig.codebasePath` (value `wd`, the worktree root); only the `design-review` node lens uses it, the four edge lenses ignore it (ref: Q2).

The dispatch between the panel and the single critic is one ternary in `runPhase`: `criticConfig.lenses?.length ? runCriticPanelLoop : runCriticLoop` — it reads ONLY the truthiness of `lenses.length` (ref: Q5). The `plan` phase config carries no `lenses` key, so plan always routes to `runCriticLoop` (ref: Q5, Q8, Q10). `runCriticPanelLoop` hardcodes the lens agentType as `` `qrspi-design-critic-${lens}` `` and an inline "qrspi design-phase critic panel" prompt that labels the subject `DESIGN_PATH`; input paths are data, but the agentType scheme and prompt wording are the only design-hardcoded pieces (ref: Q4).

In Python, `scripts/qrspi_critics_config.py` resolves `plan` via `resolve_edge_phase`, which emits only `{enabled, maxRounds}` and silently ignores any `lenses` key — there is no plan whitelist; only `resolve_design` validates lenses against `KNOWN_DESIGN_LENSES` (= `DEFAULT_DESIGN_LENSES` ∪ `{design-review}`), dropping unknowns with a warning and falling back to defaults when all are unknown (ref: Q6, Q9). `DEFAULT_CRITIC_PHASES` in `qrspi-batch.js` is the lockstep JS mirror; its `plan` entry is the bare `{ enabled: false, maxRounds: 2 }` while `design` carries `lenses` plus `candidates`/`digest`/`gateBehindEdge` (ref: Q8).

The RUS-82 node-validity lens agent is `qrspi-design-critic-design-review` (file `.claude/agents/qrspi-design-critic-design-review.md`), `tools: Read, Grep`, accepting `DESIGN_PATH` (subject), `RESEARCH_PATH` (upstream), `CODEBASE_PATH` (required for verification), and optional `TICKET_CONTENT_PATH`/`QUESTIONS_PATH`/`DIGEST_PATH` (it opts out of the digest) (ref: Q7). It is default-OFF in production (whitelist-acceptable but not in `DEFAULT_DESIGN_LENSES`) yet unconditionally active in the teeth eval via `LENS_MARKERS` membership (ref: Q7, Q13). At plan-critic time, `structure.md` and `design.md` are persisted at the canonical path while `plan.md` is still staged at `/tmp/phase-stage/<id>/plan.md`; the plan critic's `upstreamPath` is `structure.md` (ref: Q3).

The reconciliation reducer `scripts/qrspi_critic_synthesize.py` is strict-unanimity (AND-semantics), unioning deduped findings; it has no severity concept — severity is the lens's responsibility under the invariant `pass:false ⟺ findings non-empty`; it is fully phase-agnostic and reusable verbatim (ref: Q11, Q17). A clean run produces `{pass:true, findings:[]}`, driving `criticDecision → converged → {ok:true, residualFindings:[]}`; a flawed run produces a non-empty union and fails (ref: Q16, Q17). The teeth-eval deterministic core `scripts/qrspi_teeth_assert.py` (`evaluate`/`_is_catch`) is 100% phase-agnostic, keyed only on the lens→marker map and threshold; the eval workflow itself is design-hardcoded (fixtures, `LENS_MARKERS`, agentType literal, prompt, `DESIGN_PATH` label) and is OFF CI, though its core lives in `scripts/` and IS unit-tested (ref: Q13, Q14, Q19). No plan teeth fixture or plan lens→defect map exists today (ref: Q15). `doPlan`'s finalize folds only `planFindings`, NOT `criticMetrics`/`criticSummary` like `doDesign` does, though `recordCriticMetrics` already takes `phase` as a parameter and records `phase: 'plan'` automatically (ref: Q20).

## Desired End State

After this ships, the plan phase can run an opt-in node-validity panel that judges plan steps against real source, while design behavior and the single-critic fallback are byte-for-byte unchanged.

- **AC1 — plan panel config.** `DEFAULT_CRITIC_PHASES.plan` (JS) and the Python resolver gain a plan `lenses` block validated against a new `KNOWN_PLAN_LENSES` whitelist mirroring `KNOWN_DESIGN_LENSES`. The panel runs only when `critics.plan.lenses` resolves non-empty; an absent/empty `lenses` keeps plan on `runCriticLoop` (ref: Q6, Q8, Q9, Q10).
- **AC2 — phase-generic panel loop.** `runCriticPanelLoop` is parameterized on phase: agentType, the "<phase>-phase critic panel" prompt text, the subject label, and the upstream/input paths come from `criticConfig`, not literals. For plan, the upstream artifact is `structure.md` and the subject-under-review is the staged `plan.md`; `CODEBASE_PATH` is threaded as for design. Design inputs/outputs are unchanged when called for design (ref: Q1, Q2, Q3, Q4).
- **AC3 — reuse the RUS-82 agent.** The plan node lens reuses RUS-82's `design-review` judging logic; only panel wiring + spawn-prompt parameters differ. Any agentType difference is a thin alias/parameterization, not a forked prompt (ref: Q7, Q12).
- **AC4 — severity bar inherited.** The plan lens fails only on material/blocking defects (a step contradicted by real source, an unsound approach, a missing required step), nits as non-blocking notes, so the panel converges under the unchanged strict-unanimity reducer (ref: Q11, Q17).
- **AC5 — teeth on a plan node defect.** A deliberately-flawed plan fixture (a false codebase claim / unsound approach, not a dropped step) makes the lens fail and cite the defect, asserted via the reused `qrspi_teeth_assert.py` core (ref: Q13, Q14, Q15).
- **AC6 — no regression toward noise.** A known-clean plan still converges with zero fabricated findings (`synthesize → {pass:true, findings:[]}` → converged), mirrored as a non-vacuity control (ref: Q16, Q17).
- **AC7 — unit tests.** Stdlib-only `scripts/*_test.py` cover plan lens-set membership, resolver whitelist acceptance for plan, and synthesize handling, auto-discovered by `run_tests.py`; the JS generalization is verified by end-to-end run plus a green design regression (ref: Q18, Q19).

## Delta

**Modified — Python resolver `scripts/qrspi_critics_config.py`:** Add `DEFAULT_PLAN_LENSES` (default empty, for opt-in) and `KNOWN_PLAN_LENSES` (mirroring the design whitelist, including the plan node lens id). Add a `resolve_plan` function (or parameterize the existing design lens-filter loop) that validates `critics.plan.lenses` against `KNOWN_PLAN_LENSES`, drops unknowns with a warning, and emits an empty `lenses` when none configured. Re-wire the `plan` branch of `resolve_critics` from `resolve_edge_phase` to the new plan resolver (ref: Q6, Q9, Q10). Remove `plan` from `EDGE_PHASES` if it no longer routes through `resolve_edge_phase`.

**Modified — JS mirror `.claude/workflows/qrspi-batch.js`:** Update `DEFAULT_CRITIC_PHASES.plan` to carry an empty `lenses` (and any digest/codebase parallels) in lockstep with the resolver. Parameterize `runCriticPanelLoop` on phase: derive `agentType`, the panel prompt's phase word, the subject label, and the upstream label from `criticConfig` (new fields, e.g. `phaseLabel`, `agentTypePrefix`/`agentTypeFor`, `subjectLabel`) rather than the hardcoded `qrspi-design-critic-${lens}` / `DESIGN_PATH` / "design-phase". Thread the plan lens config onto `planCritic` in `doPlan` (add `lenses`, `codebasePath: wd`, and the input paths the node lens needs). Extend `doPlan`'s finalize to fold `criticMetrics`/`criticSummary` like `doDesign` (ref: Q1, Q2, Q4, Q20).

**Modified — `.qrspi/config.example.json`:** Update the plan block comment from "Single-edge-critic planning phase — same shape as 'questions' ('enabled' + 'maxRounds' only)." to describe the new optional `lenses` knob (name the plan lens ids), mirroring the design block's documentation style. The example values stay `"enabled": false` / `"maxRounds": 2` (no lenses) so the example is still no-op.

**Modified/new — plan node lens agent under `.claude/agents/`:** Thin alias `qrspi-plan-critic-plan-node-validity.md` (Decision 1 Option B) that includes/parameterizes the RUS-82 `qrspi-design-critic-design-review.md` judging body with plan-appropriate labels (`PLAN_PATH` instead of `DESIGN_PATH`, "plan-phase" instead of "design-phase"). No forked judging logic (ref: Q7, Q12).

**New — tests `scripts/qrspi_critics_config_test.py` additions (or sibling):** Plan lens-set membership, plan whitelist order-preservation, unknown-drop-with-warning, opt-in-keep, default-OFF/empty, plan node lens whitelist acceptance — mirroring the design tests (ref: Q18).

**New — teeth fixtures + plan eval (AC5/AC6):** `evals/teeth/plan-*.md` flawed fixture embedding a unique quotable marker (e.g. `TEETH-PLAN-NODE-VALIDITY`) on a step naming a non-existent symbol, a plan `LENS_MARKERS` map, `evals/teeth/plan-clean.md` clean control, and `qrspi-teeth-plan-eval.js` (Decision 4 Option B — new workflow file, not generalization) reusing `qrspi_teeth_assert.py` verbatim (ref: Q13, Q14, Q15, Q16).

## Pattern Decisions

### Decision 1: How to parameterize the panel agentType for plan

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep `qrspi-design-critic-${lens}` and reuse the design node lens agent verbatim for plan | Zero new agent files; honors "reuse, don't fork" (AC3) most literally | The `qrspi-design-critic-*` scheme + design-worded prompt is semantically wrong for plan; confusing in logs/metrics |
| B | Add an `agentTypeFor(phase, lens)` parameter on `criticConfig` (e.g. `qrspi-plan-critic-design-review`) with a thin alias agent file that includes/parameterizes the RUS-82 judging body | Phase-correct agentType + labels; judging logic still single-sourced; clean metrics/logs | One thin alias agent file per plan lens; must keep alias and source in sync |

**Recommendation:** Option B
**Rationale:** The research flags the design-named agentType scheme as semantically design-specific and notes a plan lens "either needs a parallel `qrspi-plan-critic-*` (or generic) scheme, or must reuse the design-flavored agent whose prompt prose is design-worded even when judging a plan" (ref: Q4, Q7, Q12, Inconsistencies). Option B parameterizes agentType as data (consistent with the `criticConfig`-as-universal-carrier pattern, ref: Discovered Patterns) and keeps the judging logic single-sourced per AC3's "thin alias/parameterization, not a forked prompt." The loop already fail-closes on a lens with no spawnable agent (ref: Q12), so the alias file must exist.
**NEW PATTERN?** No — extends the existing `criticConfig` carrier + design-critic agentType convention to a phase-parameterized form.

### Decision 2: Where plan lens validation lives in the resolver

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New `resolve_plan` function with its own `KNOWN_PLAN_LENSES`, plan branch re-wired off `resolve_edge_phase` | Symmetric with `resolve_design`; clear plan whitelist; easy to test | Some duplication of the lens-filter loop |
| B | Generalize the design lens-filter into a shared `_resolve_lenses(cfg, whitelist, default)` helper used by both design and plan | DRY; single filter implementation; one tested core | Touches `resolve_design` (risk of design regression); larger blast radius on the serialized critic family |

**Recommendation:** Option A
**Rationale:** Research shows `resolve_design` owns the only lens-filtering loop and `resolve_edge_phase` silently drops plan lenses with no validation (ref: Q6, Q9). A dedicated `resolve_plan` mirrors the existing per-phase resolver shape and lets the plan whitelist default to empty (opt-in), which research warns is mandatory — a non-empty default would flip every plan run to the panel and break back-compat (ref: Q10). It avoids editing `resolve_design`, honoring the constraint not to disturb landed design behavior and reducing blast radius on the serialized panel/config files. A later refactor to Option B's shared helper can follow once both phases are stable.
**NEW PATTERN?** No — mirrors the existing `resolve_design`/`resolve_edge_phase` per-phase resolver pattern.

### Decision 3: Default plan lens set (opt-in posture)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `DEFAULT_PLAN_LENSES = []` (empty); plan node lens whitelist-acceptable but never default-on | Matches the RUS-82 default-OFF asymmetry; back-compat free (ref: Q10) | Requires explicit config to ever exercise the plan panel |
| B | Default plan lenses to the node lens only | Panel runs out of the box | Violates the ticket's "Default-OFF / opt-in" constraint and the back-compat requirement |

**Recommendation:** Option A
**Rationale:** The ticket mandates default-OFF/opt-in, and research is explicit that a plan resolver "wanting opt-in panels must default to empty" or it breaks back-compat by flipping every plan run to the panel (ref: Q10). This mirrors the RUS-82 lens-activation asymmetry where `design-review` is whitelist-acceptable but excluded from defaults (ref: Q7, Discovered Patterns).
**NEW PATTERN?** No — directly mirrors RUS-82's default-OFF node-lens posture.

### Decision 4: Plan teeth evaluation — new workflow vs generalization

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Generalize `qrspi-teeth-eval.js` with a phase parameter (or `--phase plan` flag) | Single eval file; shared fan-out structure | Risks regressing the design teeth path; adds branching complexity to a non-CI workflow |
| B | New workflow file (`qrspi-teeth-plan-eval.js`) mirroring the design eval structure | Zero regression risk; plan fixtures isolated; same deterministic assertion core (`qrspi_teeth_assert.py`) reused | Duplicates fan-out structure (but it is a thin structure, not logic) |

**Recommendation:** Option B
**Rationale:** The teeth eval is a thin fan-out shell that is not on CI and not on the critical path. Isolating the plan eval prevents any accidental regression to the design path (Option A's stated risk). The deterministic core (`qrspi_teeth_assert.py`) is reused verbatim — the only duplication is the fixture-discovery and parallel-lens fan-out structure, which carries negligible maintenance cost relative to the safety benefit. Both evals are OFF CI (ref: Q13).
**NEW PATTERN?** No — extends the existing teeth eval pattern; mirrors design structure for plan.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Non-empty plan default flips every plan run to the panel, breaking the single-critic back-compat | med | high | Default `DEFAULT_PLAN_LENSES = []`; add a resolver test asserting absent/empty `lenses` resolves falsy → `runCriticLoop` (Decision 3, ref: Q10) |
| JS `DEFAULT_CRITIC_PHASES` and Python resolver drift out of lockstep, mis-resolving on config-read failure | med | med | Extend the existing lockstep test to cover the plan block; the JS mirror is used only on read-failure but must match (ref: Q8, Q9) |
| Plan node lens spawns with no matching agent file (whitelist-valid id, missing agentType) → loop fail-closes and aborts the ticket | med | high | Author the plan alias agent file before adding its id to `KNOWN_PLAN_LENSES`; the loop's `failedLens` guard aborts rather than silently passing (ref: Q12) |
| Reusing the design-worded prompt/labels (`DESIGN_PATH`, "design-phase") for plan confuses the lens and produces design-shaped judgments on plan steps | med | med | Parameterize subject label + phase word (AC2); point upstream at `structure.md` and subject at staged `plan.md`; verify on a clean plan that it converges (AC6, ref: Q3, Q4) |
| `doPlan` not folding `criticMetrics`/`criticSummary` leaves the plan panel's verdicts/convergence invisible in batch results | med | low | Extend `doPlan`'s finalize to mirror `doDesign`'s fold (ref: Q20, Inconsistencies) |
| Teeth fixture is vacuous (lens "catches" via design-flavored prose, not a real plan codebase claim) | low | med | Embed a unique quotable marker on a step naming a non-existent symbol; add a clean-control row asserting a never-catching lens FAILS the eval (non-vacuity, ref: Q14, Q15, Q16) |
| Serialized critic-family edits collide with RUS-82 (same panel/config/wiring files) | high | med | Rebase on RUS-82 once landed before editing; the family must serialize (ticket Constraints, ref: Inconsistencies) |

## Open Questions

- **OQ1 (RESOLVED — Decision 1 Option B):** Plan node lens gets a thin `qrspi-plan-critic-design-review` alias agent file; the panel loop parameterizes agentType via `agentTypeFor(phase, lens)`. The alias includes/parameterizes the RUS-82 judging body rather than forking logic. (resolves initial ambiguity about whether the design-worded agent is reusable directly — rejected for plan in favor of Option B)
- **OQ2 — Lens id:** `plan-node-validity`. This is the canonical plan-phase node-lens id. It mirrors `design-review` in the design whitelist (`KNOWN_DESIGN_LENSES`) but is a distinct id in `KNOWN_PLAN_LENSES`. The agentType maps as `qrspi-plan-critic-plan-node-validity` via `agentTypeFor('plan', 'plan-node-validity')`. The teeth `LENS_MARKERS` key is `'plan-node-validity': 'TEETH-PLAN-NODE-VALIDITY'`. (ref: Decision 1 Option B)
- **OQ3 — Upstream/subject scope:** Thread `structure.md` (upstream), `design.md`, and `research.md` (upstream inputs), plus `questions.md` onto `planCritic`, identical to the design panel's upstream set. The node lens already consumes `RESEARCH_PATH` and uses it for intent-vs-codebase verification (ref: Q7). For plan, `structure.md` is the immediate upstream (the plan was derived from structure), `design.md` is the structural ancestor, and `research.md` is the evidence base. `CODEBASE_PATH` is threaded as `wd` for codebase verification. This avoids a narrow scope that would blind the lens to the full design chain.
- **OQ4 (RESOLVED — new workflow):** Plan teeth eval is a NEW workflow file (`qrspi-teeth-plan-eval.js`), not a generalization of `qrspi-teeth-eval.js`. The new file mirrors the design workflow's fan-out/structure but uses plan fixtures, the plan `LENS_MARKERS` map, the `qrspi-plan-critic-plan-node-validity` agentType, and `PLAN_PATH` label. This avoids any regression risk to the design teeth path and isolates the plan fixture to its own eval. The deterministic assertion core (`qrspi_teeth_assert.py`) is reused verbatim from stdin. Both evals are OFF CI (same exclusion as the design eval). (ref: Q13, Q15)
