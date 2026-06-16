# Structure Outline — Holistic design critic: adversarial node-validity lens with codebase access

**Design basis:** design.md @ 2026-06-16T00:00:00Z
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft

## New Types

- No new structured data types. The new lens emits the existing `CRITIC_VERDICT_SCHEMA` shape `{pass: boolean, findings: string[]}` (ref: design.md §Current State / AC1).
- `design-review` — a new lens **id** (string literal), not a type. Member of `KNOWN_DESIGN_LENSES` but NOT of `DEFAULT_DESIGN_LENSES` (ref: design.md §Delta, Decision 2).
- `CODEBASE_PATH` — a new prompt-input **variable name** (string path line) threaded by `runCriticPanelLoop` and consumed by the new agent. Not a code type; a prompt contract (ref: design.md Decision 1, Decision 3).

## Modified Types

- `designCritic` object (assembled in `doDesign`, `qrspi-batch.js`) — add field `codebasePath: <worktree root `wd`>` (ref: design.md §Delta item 2, Decision 1).
- `KNOWN_DESIGN_LENSES` (`scripts/qrspi_critics_config.py`) — redefined from `set(DEFAULT_DESIGN_LENSES)` to `set(DEFAULT_DESIGN_LENSES) | {"design-review"}` (ref: design.md §Delta, Decision 2 Option B).
- `LENS_MARKERS` (`.claude/workflows/qrspi-teeth-eval.js`) — add `design-review: <unique marker>` entry; `LENSES = Object.keys(LENS_MARKERS)` then includes it (ref: design.md §Delta item 4, AC5).

## Contracts

- `resolve_design(config) -> list[str]` (`scripts/qrspi_critics_config.py`) — UNCHANGED signature/behavior: keeps any config lens id that is in `KNOWN_DESIGN_LENSES`, drops the rest with a warning, falls back to `DEFAULT_DESIGN_LENSES` when the resolved set is empty. Behavior shifts only because `KNOWN_DESIGN_LENSES` now also admits `design-review` (ref: design.md §Current State, Decision 2).
- `runCriticPanelLoop(name, id, criticConfig)` (`qrspi-batch.js`) — UNCHANGED signature. Now splices a `CODEBASE_PATH: <criticConfig.codebasePath>` line uniformly into every lens prompt (Option A, Decision 3) and replaces the hard-coded "Read all four paths" wording with path-agnostic wording (ref: design.md §Delta item 3, Decision 3). **NOTE:** the teeth eval (`qrspi-teeth-eval.js`) is a separate standalone fan-out that does NOT call this loop — it threads its OWN `CODEBASE_PATH` line into its inline prompt (see its Files-touched entry).
- Critic verdict contract (`CRITIC_VERDICT_SCHEMA`) — UNCHANGED shape. The new lens honors the **blocking-only** invariant `pass:false ⟺ findings non-empty` entirely in its prompt; no schema/synthesize change (ref: design.md AC4, Decision 4 Option B).
- `qrspi_critic_synthesize.py` reducer — UNCHANGED: AND-reduces over the supplied verdict list (pass only if non-empty and every lens passed). Handles the five-lens case with no code change (ref: design.md §Current State, Decision 4).
- New-agent input contract: `.claude/agents/qrspi-design-critic-design-review.md` consumes the EXACT loop-supplied variable names `DESIGN_PATH` (artifact under review), `RESEARCH_PATH` (upstream input, read in full — digest opt-out), `CODEBASE_PATH` (repo root to Read/Grep). Judging prose is phase-generic; variable names are the panel's existing design-keyed names (ref: design.md §Delta, Decision 1, Decision 5).

## Slice 1: Config whitelist decoupling (default-OFF, opt-in) + tests

**Goal:** `design-review` becomes whitelist-acceptable but inactive by default. `resolve_design` keeps it when a config lists it in `critics.design.lenses` and drops it when not, while the default resolved set stays the four. This is the pure-logic core, fully verifiable in isolation via `run_tests.py` before any agent/JS wiring exists.
**Files touched:**

- ⚠️ `scripts/qrspi_critics_config.py` — redefine `KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}`; leave `DEFAULT_DESIGN_LENSES` as the existing four; add a code comment recording the deliberate whitelist/default decoupling (ref: design.md Decision 2 Option B, Risk: whitelist/default desync).
- ⚠️ `scripts/qrspi_critics_config_test.py` — assert (a) default resolved set is still the four; (b) `design-review` is DROPPED when not listed; (c) `design-review` is KEPT when listed; (d) empty-resolve still falls back to the four (ref: design.md AC8, §Delta tests).
**Verification:**
- [ ] `python3 scripts/run_tests.py qrspi_critics_config` passes (new assertions green).
- [ ] `python3 scripts/run_tests.py` full suite stays green (no regression in synthesize/teeth-assert tests).
**Context cost:** S
**Depends on:** none

## Slice 2: Node-validity lens agent + panel wiring + teeth defect + tests

**Goal:** Deliver the end-to-end runtime path: a new `design-review` agent that reads source, threaded into the panel via `CODEBASE_PATH`, activated by the teeth-eval config, catching a labelled codebase-claim defect — plus the synthesize five-lens and teeth-marker test coverage. These pieces are mutually dependent (the agent file is useless without the loop threading its `CODEBASE_PATH`; the loop line is inert without an agent that consumes it; the teeth defect proves both) and share no internal testability boundary, so they are one unit.
**Files touched:**

- ✨ `.claude/agents/qrspi-design-critic-design-review.md` — node-validity lens. Frontmatter `tools: Read, Grep` (no Bash, no model key). Prose: phase-generic "find what is materially wrong" framing (architectural soundness, correctness, failure modes, edge cases, operability, testability, security/perf, alternatives); consumes `DESIGN_PATH`/`RESEARCH_PATH`/`CODEBASE_PATH` by those exact names; reads full `RESEARCH_PATH` even when `DIGEST_PATH` present (digest opt-out); enforces blocking-only findings (`pass:false ⟺ findings non-empty`); findings must cite a real source location; records target-model intent (Opus-tier) as a doc note only (ref: design.md AC1, AC2, AC4, AC7, Decision 1, Decision 5).
- ⚠️ `.claude/workflows/qrspi-batch.js` — (a) add `codebasePath: wd` to the `designCritic` object in `doDesign`; (b) in `runCriticPanelLoop` splice a uniform `CODEBASE_PATH` prompt line and replace "Read all four paths" with path-agnostic wording; (c) leave JS `DEFAULT_DESIGN_LENSES` fallback as the four; do NOT set `lensModel` (panel-wide seam) (ref: design.md §Delta items 1-4, Decision 1, Decision 3, AC7, Risk: lensModel).
- ⚠️ `evals/teeth/design.md` — add a labelled node-defect: an unverifiable codebase claim (a false assertion about real source, e.g. "extends helper `foo()` in `bar.py`" where no such symbol exists) with a unique marker (ref: design.md AC5, OQ3).
- ⚠️ `.claude/workflows/qrspi-teeth-eval.js` — STANDALONE fan-out (no `runCriticPanelLoop`, no `critics.design.lenses`): add `design-review` → marker to `LENS_MARKERS` (the sole activation lever), thread `CODEBASE_PATH = <engine/repo root>` into the eval's own inline lens prompt, and replace "Read all four paths" with path-agnostic wording. Without the threaded `CODEBASE_PATH` the lens can't read source and AC5 fails (ref: design.md §Delta item 4, AC5).
- ⚠️ `scripts/qrspi_critic_synthesize_test.py` — add a five-lens reduction assertion (ref: design.md AC8).
- ⚠️ `scripts/qrspi_teeth_assert_test.py` — assert the new marker is in the marker map / owning-lens mapping if asserted there (ref: design.md §Delta tests, AC8).
**Verification:**
- [ ] `python3 scripts/run_tests.py` full suite passes (five-lens synthesize + teeth-assert additions green).
- [ ] Manual/teeth e2e: run `Workflow({name:"qrspi-teeth-eval"})` with the eval config listing `design-review`; the `design-review` lens fails citing the codebase-claim marker (AC5/AC2 demonstration), and on a clean design returns `pass:true, findings:[]` (AC6).
- [ ] Inspect agent frontmatter: `tools: Read, Grep`, no Bash, no model key.
**Context cost:** L
**Depends on:** Slice 1 (the lens id must be whitelist-accepted before the panel/teeth config can activate it).

---

## Unverified Assumptions

- **`evals/` harness is a placeholder.** The codebase conventions state the `evals/` + `run_eval.py` harness is non-functional; AC5/AC6 end-to-end verification of the live panel can only be done via the dedicated `qrspi-teeth-eval` workflow and manual runs, not an automated eval gate. The *deterministic* marker/majority math is CI-tested via `qrspi_teeth_assert_test.py`, but whether the live lens actually reads source and catches the defect is a manual/teeth-run claim, not a unit-test-provable one (ref: design.md AC5, codebase conventions).
- **`lensModel` may be inert.** The design records (OQ1, AC7) that the panel-wide `lensModel` seam may have no runtime effect at all, and the lens inherits the panel's session model. The "target Opus-tier model" intent therefore cannot be verified to take effect by any concrete code or test — it is documentation only. The actual model the lens runs under at runtime is not asserted anywhere.
- **Exact teeth codebase-claim wording is unspecified.** OQ3 leaves the precise false-source-assertion wording as an implementation detail; the structure cannot pin it to a concrete symbol/file until Plan/Implementation chooses one that is genuinely absent from the repo (the claim must reference a symbol that truly does not exist, which requires a repo check at implementation time).
- **Phase-generic prose vs. design-keyed variable names is a documented tradeoff, not a fully-closed contract.** The lens consumes `DESIGN_PATH`/`RESEARCH_PATH` (design-keyed) while its prose avoids the word "design"; the design explicitly defers the `ARTIFACT_PATH`/`UPSTREAM_PATH` aliasing to RUS-84. This is intentional but means the "phase-generic" claim is partial — verifiable only by prose inspection, not by any mechanism that would let a plan-phase artifact flow through unchanged.
