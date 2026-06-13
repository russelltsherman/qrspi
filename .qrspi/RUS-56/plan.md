# Implementation Plan — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Structure basis:** structure.md @ 2026-06-13 (rebuilt against current `main`)
**Generated:** 2026-06-13 (rebuilt)
**Status:** draft
**Total steps:** 20

> **Reconciliation note (see structure.md §Reconciliation):** RUS-55's full single-critic seam
> is **landed on `main`** (`CRITIC_VERDICT_SCHEMA`, `runPhase(criticConfig)`, `runCriticLoop`,
> `next_action`, `parse_critic_verdict`, `compose_message`, `qrspi_critic_body.py`,
> `criticBodyStep`, and a `doDesign` design-phase critic). This plan **reuses** all of it and adds
> only: a pure `synthesize`, four lens prompts, a parallel `runCriticPanelLoop`, and a
> config-overridable `critics.design` block. It creates **no** `qrspi_critic_body.py`, adds **no**
> `CRITIC_VERDICT_SCHEMA`, and changes **no** `runPhase` signature — the items that caused the
> RUS-55 collision are gone.

## Slice 1: Pure synthesis helper (Python firewall)

### Setup

1. ✨ Create `scripts/qrspi_critic_synthesize.py` — module shell importing `parse_critic_verdict` from `scripts/qrspi_critic_loop.py` (`from qrspi_critic_loop import parse_critic_verdict`, with the established self-locating `sys.path` insert if siblings do not import directly). Purpose: house the pure `synthesize` reducer (ref: structure §Contracts, Decision 1).

### Core Logic

2. ✨ Implement `synthesize(verdicts: list[LensVerdict]) -> SynthesizedVerdict` in `scripts/qrspi_critic_synthesize.py` — coerce each entry via the landed `parse_critic_verdict` first (fail-closed), then reduce: `pass` is `True` only if **every** coerced lens passed; `findings` is the exact-string-deduped union of all lens findings, preserving first-seen order (ref: OQ2, §New Types `SynthesizedVerdict`).
3. ✨ Add optional lens-tagging in `synthesize` — when a lens entry carries a lens identifier, each emitted finding may be wrapped as `{text, lens}` for audit; bare-string findings remain bare (ref: §New Types `LensVerdict`, OQ2 "optionally lens-tagged").

### Tests

4. ✨ Create `scripts/qrspi_critic_synthesize_test.py` — `check()`-style stdlib sibling with literal `{pass, findings}` list fixtures: all-pass ⇒ `pass:true`; one-fail ⇒ `pass:false`; duplicate-across-lenses ⇒ deduped union; empty/malformed-lens entry ⇒ coerced to not-passed, contributes no findings (ref: structure Slice 1, Q12).
5. Run: `python3 scripts/qrspi_critic_synthesize_test.py`
   - **Expected:** exit 0, all fixtures pass.

### Verify Slice 1

   - [ ] `python3 scripts/qrspi_critic_synthesize_test.py` exits 0.
   - [ ] A one-fail fixture yields `pass:false` and the deduped union; an all-pass fixture yields `pass:true`.
   - [ ] `synthesize` imports and reuses the landed `parse_critic_verdict` (no re-implemented coercion).

---

## Slice 2: Lens agent prompts

### Setup

6. ✨ Create `.claude/agents/qrspi-design-critic-completeness.md` — design lens prompt: receives `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` (persisted `art(...)`) + staged `stg(id,'design')` as rubric; rubric = does the design cover all ticket acceptance criteria and answered questions; emits a `parse_critic_verdict`-valid `{pass, findings}` reply conforming to the landed `CRITIC_VERDICT_SCHEMA` (ref: structure Slice 2, AC2, OQ1).
7. ✨ Create `.claude/agents/qrspi-design-critic-internal-consistency.md` — same input contract; rubric = internal contradictions / dangling references / contract mismatches within the design (ref: OQ1).
8. ✨ Create `.claude/agents/qrspi-design-critic-edge-alignment.md` — same input contract; rubric = the edge critic: design aligns with ticket intent and research facts, no scope drift / unsupported claims (ref: OQ1, "ticket/research alignment (edge)").
9. ✨ Create `.claude/agents/qrspi-design-critic-simplicity.md` — same input contract; rubric = unjustified complexity / simpler alternative not taken (ref: OQ1).

### Tests

10. ✨ Verify lens-reply parseability — confirm a representative lens reply is accepted by the landed `parse_critic_verdict`:
    `python3 -c "import sys; sys.path.insert(0,'scripts'); from qrspi_critic_loop import parse_critic_verdict; print(parse_critic_verdict('{\"pass\": true, \"findings\": []}'))"`
    - **Expected:** prints a `{pass:true, findings:[]}`-equivalent (valid reply not coerced to not-passed).

### Verify Slice 2

    - [ ] A single lens agent spawned against a sample `design.md` returns text the landed `parse_critic_verdict` accepts.
    - [ ] Each of the four lens prompts references the correct upstream inputs (ticket/research/questions + staged design).
    - [ ] **No** new `CRITIC_VERDICT_SCHEMA` was added — the landed constant (`qrspi-batch.js:416`) is referenced.

---

## Slice 3: Panel loop + doDesign rewiring + config

### Core Logic

11. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `runCriticPanelLoop(name, id, criticConfig)` as a **parallel peer** to the landed `runCriticLoop`.
    - **Per round:** `parallel()`-fan-out the `criticConfig.lenses` lens `agent()` thunks against staged `stg(id,'design')` + persisted upstream `art(...)` paths; ingest each reply through `parse_critic_verdict`; call `synthesize` (via `scripts/qrspi_critic_synthesize.py`); append the synthesized verdict to the per-round verdict list; call `next_action(verdicts, round, max_rounds)`; on `revise` re-spawn the design agent with the synthesized findings (rewriting `stg(id,'design')` in place, never emptying it — Risk Register row 2); break on `converged`; on `cap_reached` set `residualFindings` and return success.
    - **Returns** the same `{ residualFindings }` shape as `runCriticLoop` so `runPhase`'s existing write-back (`qrspi-batch.js:631`) is unchanged (ref: §Contracts `runCriticPanelLoop`, Decisions 1–3).
12. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `runPhase`'s **existing** `if (criticConfig)` branch (`qrspi-batch.js:624`), dispatch on lenses: `const cr = criticConfig.lenses?.length ? await runCriticPanelLoop(name, id, criticConfig) : await runCriticLoop(name, id, criticConfig)`.
    - **No signature change** (the 7th `criticConfig` param already exists). The single-critic path (plan phase, `planCritic` has no `lenses`) is byte-for-byte unchanged; absent `criticConfig` ⇒ today's behavior (ref: §Modified Types `runPhase`).
13. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add the lenient `parseCriticConfig(text)` parser (separate from the string-only `parseConfigEnvelope`): extract the `qrspi_config.py --key critics` envelope (reuse `extractJsonObject`), accept an **object** `value`, return `value.design` (object or `undefined`); a missing/garbled/`ok:false` envelope ⇒ `undefined`.
    - **Why top-level `critics`:** verified — `scripts/qrspi_config.py --key critics.design` → `None` (single-top-level-key resolver, no dot-path), and `parseConfigEnvelope` rejects non-string values. So read the top-level `critics` key (value round-trips as `{"design":{…}}`) and pull `.design` here (ref: structure §Unverified Assumptions, OQ3).
14. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — in `doDesign`, **replace** the hard-coded `const designCritic = { upstreamPath: art(wd, t.id, 'research.md'), maxRounds: 2 }` with a config-built object: run `python3 scripts/qrspi_config.py --key critics` via a config worker, pass the text to `parseCriticConfig`, and build `designCritic = { upstreamPath: art(wd,t.id,'research.md'), maxRounds: <config.maxRounds ?? 2>, lenses: <config.lenses ?? DEFAULT_FOUR> }`.
    - Apply **config value > JS default** precedence; default `maxRounds` 2; default `lenses` = `["completeness","internal-consistency","edge-alignment","simplicity"]`; drop unknown lens names with a `log(...)` warning; an empty resolved lens set falls back to the default four (OQ3).
    - Keep the existing `designCritic.residualFindings`/`criticBodyStep` lines **unchanged** — the panel populates `residualFindings` exactly as the single critic did (ref: §New Types `CriticConfig`, §Delta item d, OQ1/OQ3).
15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `log(...)` per-round pass/fail/cap lines inside `runCriticPanelLoop` and fold a panel summary into `res.summary` (ref: §Delta item f, Risk Register row 5, Q14).

### Config

16. ⚠️ Modify `.qrspi/config.example.json` — add an optional, documented `critics.design` block.
    - **Current:** no critic keys present.
    - **After:** `"critics": {"design": {"maxRounds": 2, "lenses": ["completeness","internal-consistency","edge-alignment","simplicity"]}}` documented as optional per-run override (config > JS default) (ref: §Modified Types config schema, OQ3).

### Tests

17. ✨ Document the design-phase eval before/after procedure (AC5) — fold the repeatable procedure (inject a live `model` into `evals/suite.json` `defaults`; run design cases `case_005/006/014` through `eval_all.py` → `run_eval.py` + `grade.py` before/after; record the delta) into the PR summary. No code slice produces a measured score (ref: OQ4, structure §Unverified Assumptions, Risk Register row 3).

### Verify Slice 3

18. **Checkpoint:** end-to-end design run against the worktree (manual e2e — JS glue is not unit-tested per Q12).
    - [ ] A deliberately-flawed design triggers ≥1 revise round, then converges or caps; `res.summary` shows per-round pass/fail.
    - [ ] A design passing all four lenses on round 0 produces zero revise spawns (AC3).
    - [ ] A capped run writes residual findings into the design PR body via the landed `criticBodyStep` (inspect submitted PR / staged commit message) (AC4).
    - [ ] `doDesign` with no `critics.design` config key uses no `lenses` ⇒ single-critic-equivalent behavior (opt-in panel seam).
    - [ ] A `critics.design` block in `.qrspi/config.json` overrides `maxRounds` / `lenses` for the run (OQ3).
19. **Checkpoint:** dispatch correctness — the **plan phase** is untouched.
    - [ ] `doPlan`'s `planCritic` (no `lenses`) still routes to the single-critic `runCriticLoop` — confirm by inspection / a plan-phase e2e shows one `qrspi-critic` spawn per round, not a panel.
20. **Checkpoint:** regression — `python3 scripts/qrspi_critic_loop_test.py` and `python3 scripts/qrspi_pr_body_test.py` (landed RUS-55 siblings) still exit 0, confirming the reused contracts are intact.

---

## Pre-build verification (blocking, before Slice 1)

Reads only — no code change. **If any signature differs from structure.md, stop and report the mismatch before building.**

- `scripts/qrspi_critic_loop.py` exports `next_action(verdicts, round, max_rounds)` and `parse_critic_verdict(raw)` with the documented signatures (LANDED).
- `scripts/qrspi_pr_body.py` exports `compose_message(existing, body)`; `scripts/qrspi_critic_body.py` and `criticBodyStep` exist and splice residuals into the design body (LANDED — reused, not recreated).
- `CRITIC_VERDICT_SCHEMA` exists at `qrspi-batch.js:416` (LANDED — reused, not re-added).
- `runPhase`'s real signature is `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)` with the `criticConfig` 7th param **already present** (`qrspi-batch.js:611`); Step 12 only changes its internal dispatch.
- `doDesign` already builds `const designCritic = { upstreamPath, maxRounds: 2 }` and passes it as the 7th arg (`qrspi-batch.js:~782`); Step 14 modifies this object, not introduces it.
- `parallel()` and `agent()` runner primitives exist with a usable call shape for the lens fan-out (verify `parallel()`'s exact signature before Step 11).
- `qrspi_config.py --key critics` round-trips the nested object as `{"ok":true,"value":{"design":{…}}}`; `--key critics.design` returns `None` (single-top-level-key resolver) — Step 13 reads the top-level key.

## Rollback Notes

- **Steps 11–15** (`qrspi-batch.js` edits): reversible by reverting the commit. The dispatch (Step 12) only adds a panel branch; with no `critics.design` config and no `lenses`, every path falls through to the landed single-critic behavior, so a partial revert is safe. To disable the panel without reverting code, remove `lenses` from the `critics.design` block in `.qrspi/config.json` (the design phase reverts to single-critic).
- **Step 16** (`.qrspi/config.example.json`): documentation-only; revert the commit to remove.
- **Steps 1–4** (new `scripts/qrspi_critic_synthesize*.py`): new files only; `rm` to roll back. No shared-module mutation. **`qrspi_critic_body.py` is NOT touched** (landed, reused).
- **Steps 6–9** (lens prompts): new agent definition files only; `rm` to roll back.
- No DB migrations, no destructive ops — orchestration glue + one pure Python helper (ref: §Delta "No new DB/queries").
