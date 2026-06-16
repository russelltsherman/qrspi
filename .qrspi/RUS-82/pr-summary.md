# PR: RUS-82 Adversarial node-validity design critic lens (default-OFF)

**Ticket:** RUS-82
**Design:** design.md @ 2026-06-16T00:00:00Z
**Structure:** structure.md @ 2026-06-16T00:00:00Z

## Summary

Adds a fifth, adversarial design-critic lens — `design-review` — that judges the
NODE (architectural soundness, correctness, failure modes, codebase claims) rather
than upstream-fidelity, and is the first critic lens granted read-only codebase
access (`tools: Read, Grep`) so it can verify a design's claims against real source.
The lens is wired into the panel via a new uniform `CODEBASE_PATH` prompt line but
ships **default-OFF**: it is added only to the `KNOWN_DESIGN_LENSES` whitelist
(decoupled from `DEFAULT_DESIGN_LENSES`), so it activates only when a config lists it
in `critics.design.lenses`. Reviewer focus areas: (1) the whitelist/default
decoupling in `qrspi_critics_config.py` (the default resolved panel must stay the
four edge-fidelity lenses), (2) the blocking-only verdict contract in the new agent
(`pass:false ⟺ findings non-empty`, to avoid polluting the dissent metric), and
(3) the teeth fixture's false-codebase-claim defect, whose catch is provable only by
a manual/teeth run, not the unit-test gate.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: node-validity lens exists (judges the node, standard `{pass, findings}`) | `.claude/agents/qrspi-design-critic-design-review.md` | `scripts/qrspi_critic_synthesize_test.py` (five-lens reduction); live: `qrspi-teeth-eval` |
| AC2: read-only codebase access (`Read, Grep`, `CODEBASE_PATH`) | agent frontmatter `tools: Read, Grep`; `qrspi-batch.js` `runCriticPanelLoop` `codebaseLine` + `doDesign` `codebasePath: wd` | demonstrated by AC5 codebase-claim defect; live `qrspi-teeth-eval` |
| AC3: wired into panel, DEFAULT-OFF (whitelist-accepted, opt-in only) | `scripts/qrspi_critics_config.py` `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) \| {"design-review"}` | `qrspi_critics_config_test.py::DesignReviewWhitelistTests` (default-four / drop-unlisted / keep-listed / empty-fallback) |
| AC4: severity bar — blocking-only findings (`pass:false ⟺ findings non-empty`) | agent prose (blocking-only invariant); synthesize unchanged | `qrspi_critic_synthesize_test.py` (only-design-review-fails ⇒ pass:false) |
| AC5: teeth on a node defect (false codebase claim) + marker | `evals/teeth/design.md` DEFECT 4 (`TEETH-NODE-VALIDITY`); `qrspi-teeth-eval.js` `LENS_MARKERS['design-review']` | `qrspi_teeth_assert_test.py::test_design_review_marker_owned_and_independent`; live catch via `qrspi-teeth-eval` |
| AC6: no regression toward noise (clean design ⇒ `pass:true, []`) | agent blocking-only invariant (clean ⇒ no findings) | `qrspi_critic_synthesize_test.py` (all-five-pass ⇒ pass:true, []); live `qrspi-teeth-eval` clean path |
| AC7: cost/model profile decided (digest opt-out; model = intent only, no `lensModel`) | agent doc note (reads full `RESEARCH_PATH`; Opus-tier intent, not wired); `qrspi-batch.js` leaves `lensModel` unset | `qrspi_critics_config_test.py::JsMirrorParityTests` (JS default lenses unchanged) |
| AC8: stdlib-only unit tests (whitelist, default-OFF, opt-in, synthesize) | n/a | `qrspi_critics_config_test.py`, `qrspi_critic_synthesize_test.py`, `qrspi_teeth_assert_test.py` — all green under `run_tests.py` |

## Changes by Slice

### Slice 1: Config whitelist decoupling (default-OFF, opt-in) + tests

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_critics_config.py` | ⚠️ modified — decouple `KNOWN_DESIGN_LENSES` from `DEFAULT_DESIGN_LENSES`, add `design-review` to whitelist only + decoupling comment | +7, -1 |
| `scripts/qrspi_critics_config_test.py` | ⚠️ modified — new `DesignReviewWhitelistTests` (default-four, drop-unlisted, keep-listed, alone-kept, empty-fallback) | +50, -0 |

### Slice 2: Node-validity lens agent + panel wiring + teeth defect + tests

| File | Change | Lines |
|------|--------|-------|
| `.claude/agents/qrspi-design-critic-design-review.md` | ✨ new — node-validity lens (`tools: Read, Grep`; consumes `DESIGN_PATH`/`RESEARCH_PATH`/`CODEBASE_PATH`; digest opt-out; blocking-only; Opus-tier intent as doc note) | +73, -0 |
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified — `codebasePath: wd` on `designCritic`; uniform `codebaseLine`/`CODEBASE_PATH` splice in `runCriticPanelLoop`; "Read all four paths" → path-agnostic wording | +10, -2 |
| `.claude/workflows/qrspi-teeth-eval.js` | ⚠️ modified — `LENS_MARKERS['design-review'] = 'TEETH-NODE-VALIDITY'` (sole activation lever); thread `CODEBASE_PATH = ENGINE_ROOT` into inline prompt; path-agnostic wording | +16, -1 |
| `evals/teeth/design.md` | ⚠️ modified — add DEFECT 4: false claim of `merge_lens_findings()` in `scripts/qrspi_critic_synthesize.py` (absent symbol); banner THREE→FOUR | +24, -1 |
| `scripts/qrspi_critic_synthesize_test.py` | ⚠️ modified — five-lens AND-reduction assertions (all-pass; only design-review fails) | +24, -0 |
| `scripts/qrspi_teeth_assert_test.py` | ⚠️ modified — `MARKERS` gains `design-review`; rename `test_all_three_lenses_catch`→`test_all_lenses_catch`; add `test_design_review_marker_owned_and_independent` | +22, -1 |

> Workflow byproduct (not a code change): `.qrspi/RUS-82/critic-metrics.jsonl` (+5)
> and the `.qrspi/RUS-82/*.md` phase artifacts (questions/research/design/structure/
> plan/worktree/impl-log) are the QRSPI run's own persisted artifacts, carried in the
> branch by the lifecycle, not part of the feature delta.

## Testing Summary

- [x] Slice 1: config unit tests — `python3 scripts/run_tests.py qrspi_critics_config` — 1 file passed, 0 failed
- [x] Slice 1 + 2: full regression suite — `python3 scripts/run_tests.py` — 40 files passed, 0 failed
- [x] Slice 2: JS syntax — `node --check .claude/workflows/qrspi-batch.js` and `node --check .claude/workflows/qrspi-teeth-eval.js` — both OK / exit 0
- [x] Agent frontmatter inspection: `tools: Read, Grep` (no Bash, no model key) — verified
- [ ] Live teeth e2e — `Workflow({name:"qrspi-teeth-eval"})` — NOT RUN (opt-in, spawns live model agents; outside the unit-test gate per structure §Unverified Assumptions). The deterministic majority/marker math IS covered green by `qrspi_teeth_assert_test.py`.

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `worktree.md` T15 wording | "Ensure eval critic config lists `design-review` in `critics.design.lenses`" | Activation is via `LENS_MARKERS` only; T15's real content is threading `CODEBASE_PATH = ENGINE_ROOT` into the eval's inline prompt | The worktree one-liner was stale; plan.md / structure.md §Slice 2 both authoritatively state the teeth eval is a STANDALONE fan-out with NO `critics.design.lenses` config and does not call `resolve_design`. No functional deviation from design/structure. |

No deviations from `structure.md` or `plan.md` were recorded in the implementation log (impl-log §Slice 1 and §Slice 2 both "none" against structure.md/plan.md; the single deviation above is against the stale `worktree.md` task wording only).

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Always-dissent veto (node lens fails on stylistic items, burns `maxRounds`, ships via `cap_reached`) | mitigated — agent enforces blocking-only `pass:false ⟺ findings non-empty`; clean design ⇒ `pass:true,[]` (synthesize tests pin it). Live behavior unverified (lens is default-OFF) | Remove `design-review` from any `critics.design.lenses` config (lens is OFF by default — no rollback needed for default users) |
| Dissent-metric pollution (advisory findings count as dissent) | mitigated — blocking-only findings keep `findingsCount` a clean blocking signal; no synthesize change | n/a (prompt-level invariant) |
| Default-OFF regression (`design-review` lands in `DEFAULT_DESIGN_LENSES` / JS fallback) | mitigated — added to `KNOWN_DESIGN_LENSES` only; `DEFAULT_DESIGN_LENSES` unchanged; JS fallback unchanged; tests pin default-four + JS-mirror parity | Revert `qrspi_critics_config.py` line to `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES)` |
| Whitelist/default desync (future edit re-couples them) | accepted (deliberate decoupling) — code comment records the intent; tests pin both sets independently | n/a (covered by tests) |
| Variable-name contract mismatch (agent vs loop) | resolved (RUS-82) — agent consumes the loop's exact `DESIGN_PATH`/`RESEARCH_PATH`/`CODEBASE_PATH`. Residual: RUS-84 must alias these to plan-phase paths | n/a |
| Missing agent file → spawn null → ticket abort | mitigated — agent file shipped in same change as whitelist edit; abort is loud, not silent | n/a |
| `lensModel` seam panel-wide / possibly inert | mitigated — model recorded as intent only; `lensModel` NOT set (would re-model all lenses) | n/a |
| Codebase-access fabrications (source-reading lens invents findings) | discovered-residual — findings must cite a real source location; AC5/AC6 teeth+clean pair guards it, but live fabrication resistance is a manual/teeth-run claim, not unit-test-proven | Disable lens (default-OFF) |
| "Read all four paths" miscount | mitigated — replaced with path-agnostic "Read every path provided above" in both `qrspi-batch.js` and `qrspi-teeth-eval.js` | n/a |

**Whole-change rollback:** revert commits `34f339b` (Slice 1) and `b798099` (Slice 2). Because the lens is default-OFF, no production critic run is affected until a config opts in, so the blast radius of landing is limited to opt-in configs and the teeth eval.

## Open Items

- Live teeth e2e (`Workflow({name:"qrspi-teeth-eval"})`) and the live clean-design AC6 path are unrun — opt-in, spawn live model agents, outside the CI unit-test gate (structure §Unverified Assumptions). Whether the live lens actually reads source and catches/avoids fabricating findings is a manual claim, not unit-test-provable.
- `lensModel` Opus-tier targeting is intent/documentation only — the lens inherits the panel's session model at runtime; no code or test asserts the actual model. A true per-lens model override would restructure the loop (out of scope; tracked in OQ1).
- RUS-84 (plan-phase reuse, blockedBy RUS-82) must add a `DESIGN_PATH`/`RESEARCH_PATH` → `ARTIFACT_PATH`/`UPSTREAM_PATH` aliasing step: the phase-generic prose reduces but does not eliminate the reuse cost, since the agent still consumes design-keyed variable names (design.md §Delta tradeoff).
- "Phase-generic" prose is verifiable only by inspection, not by any mechanism that flows a plan-phase artifact through unchanged (structure §Unverified Assumptions).
