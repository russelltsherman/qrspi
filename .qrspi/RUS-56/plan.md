# Implementation Plan — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Structure basis:** structure.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft
**Total steps:** 27

## Slice 1: Pure synthesis + body helpers (Python firewall)

### Setup

1. ✨ Create `scripts/qrspi_critic_synthesize.py` — module shell importing `parse_critic_verdict` from `scripts/qrspi_critic_loop.py` (`from qrspi_critic_loop import parse_critic_verdict`, with the established self-locating `sys.path` insert if siblings do not import directly). Purpose: house the pure `synthesize` reducer (ref: structure §Contracts, Decision 1).

### Core Logic

2. ✨ Implement `synthesize(verdicts: list[LensVerdict]) -> SynthesizedVerdict` in `scripts/qrspi_critic_synthesize.py` — coerce each entry via `parse_critic_verdict` first (fail-closed), then reduce: `pass` is `True` only if **every** coerced lens passed; `findings` is the exact-string-deduped union of all lens findings, preserving first-seen order (ref: OQ2, §New Types `SynthesizedVerdict`).
3. ✨ Add optional lens-tagging in `synthesize` — when a lens entry carries a lens identifier, each emitted finding may be wrapped as `{text, lens}` for audit; bare-string findings remain bare (ref: §New Types `LensVerdict` findings `list[str|{text, lens}]`, OQ2 "optionally lens-tagged").
4. ✨ Create `scripts/qrspi_critic_body.py` — CLI: reads a staged residual-findings file (path arg) + the finalize commit message (path arg or stdin), imports `compose_message` from `scripts/qrspi_pr_body.py`, splices the formatted residual-findings block as the body, emits the spliced message to stdout (ref: §Contracts `qrspi_critic_body.py`, Decision 4, Q9 Path A).
5. ✨ Add empty-findings short-circuit to `scripts/qrspi_critic_body.py` — when the residual-findings file is empty/absent, emit the original commit message unchanged (idempotent no-op body) (ref: Decision 4).

### Tests

6. ✨ Create `scripts/qrspi_critic_synthesize_test.py` — `check()`-style stdlib sibling with literal `{pass, findings}` list fixtures: all-pass ⇒ `pass:true`; one-fail ⇒ `pass:false`; duplicate-across-lenses ⇒ deduped union; empty/malformed-lens entry ⇒ coerced to not-passed, contributes no findings (ref: structure Slice 1, §Delta, Q12).
7. Run: `python3 scripts/qrspi_critic_synthesize_test.py`
   - **Expected:** exit 0, all fixtures pass.
8. ✨ Create `scripts/qrspi_critic_body_test.py` — `check()`-style sibling: empty findings (message unchanged), single finding, multi-line findings, idempotent re-splice (re-running on already-spliced message yields same output) (ref: structure Slice 1).
9. Run: `python3 scripts/qrspi_critic_body_test.py`
   - **Expected:** exit 0.

### Verify Slice 1

10. **Checkpoint:** `python3 scripts/qrspi_critic_synthesize_test.py && python3 scripts/qrspi_critic_body_test.py`
    - [ ] Both test files exit 0 (all fixtures pass).
    - [ ] A one-fail fixture yields `pass:false` and the deduped union of findings; an all-pass fixture yields `pass:true`.
    - [ ] `synthesize` imports and reuses landed `parse_critic_verdict` (no re-implemented coercion).

---

## Slice 2: Lens agent prompts + verdict schema

### Setup

11. ✨ Create `.claude/agents/qrspi-design-critic-completeness.md` — design lens prompt: receives `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` (persisted `art(...)`) + staged `stg(id,'design')` as rubric; rubric = does the design cover all ticket acceptance criteria and answered questions; emits a `parse_critic_verdict`-valid `{pass, findings}` reply (ref: structure Slice 2, §Delta, AC2, OQ1).
12. ✨ Create `.claude/agents/qrspi-design-critic-internal-consistency.md` — same input contract; rubric = internal contradictions / dangling references / contract mismatches within the design; emits `{pass, findings}` (ref: OQ1).
13. ✨ Create `.claude/agents/qrspi-design-critic-edge-alignment.md` — same input contract; rubric = the edge critic: design aligns with the ticket intent and research facts, no scope drift / unsupported claims; emits `{pass, findings}` (ref: OQ1, "ticket/research alignment (edge)").
14. ✨ Create `.claude/agents/qrspi-design-critic-simplicity.md` — same input contract; rubric = unjustified complexity / simpler alternative not taken; emits `{pass, findings}` (ref: OQ1).

### Core Logic

15. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `CRITIC_VERDICT_SCHEMA` constant only (no loop wiring yet): the `{pass, findings}` shape handed to lens agents as their required output contract.
    - **Current:** no `CRITIC_VERDICT_SCHEMA` in the file (grep returns zero hits per design §Current State).
    - **After:** module-level `const CRITIC_VERDICT_SCHEMA = ...` describing the required `{pass: bool, findings: list}` lens output, referenced by lens-agent prompts (ref: structure §Contracts, §Delta item a).

### Tests

16. ✨ Verify lens-reply parseability — confirm a lens agent reply text is accepted by `parse_critic_verdict` via a `python3 -c` ingest probe (feed a representative `{pass, findings}` lens reply through `parse_critic_verdict` and assert it does not coerce a valid reply to not-passed) (ref: structure Slice 2 verification).
17. Run: `python3 -c "import sys; sys.path.insert(0,'scripts'); from qrspi_critic_loop import parse_critic_verdict; print(parse_critic_verdict('{\"pass\": true, \"findings\": []}'))"`
    - **Expected:** prints a `{pass:true, findings:[]}`-equivalent (valid reply not coerced to not-passed).

### Verify Slice 2

18. **Checkpoint:** spawn a single lens agent against a sample `design.md` and confirm the reply parses; inspect each lens prompt for input wiring.
    - [ ] A single lens agent spawned against a sample `design.md` returns text that `parse_critic_verdict` accepts.
    - [ ] Each of the four lens prompts references the correct upstream inputs (ticket/research/questions + staged design).
    - [ ] `CRITIC_VERDICT_SCHEMA` exists in `qrspi-batch.js` and no panel-loop wiring was added in this slice.

---

## Slice 3: Panel loop + doDesign wiring + config + PR-body splice

### Setup

19. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — extend `runPhase` with an optional trailing `criticConfig` parameter, guarded by `if (criticConfig)`.
    - **Current (verified signature):** `runPhase(name, agentType, prompt, existing, id, phaseLabel)` — produce (short-circuit if artifact exists) → `persistArtifact`; no critic step. (The structure/plan's earlier `runPhase(name, id, ...ctx)` shorthand was inaccurate; the real 6-param signature is the one to extend.)
    - **After:** append `criticConfig` as a **7th** trailing parameter → `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)`, passed only by `doDesign`'s design call. When `criticConfig` is present, run `runCriticPanelLoop(name, id, criticConfig, ...)` inside the produce→persist window before the single `persistArtifact`; when absent (every other caller), behavior is byte-for-byte today's (ref: §Modified Types `runPhase`, §Delta item c, AC §Desired End State).

### Core Logic

20. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `runCriticPanelLoop(name, id, criticConfig, ...ctx)`.
    - **Current:** no `runCriticLoop`/`runCriticPanelLoop` in the file.
    - **After:** per round — `parallel()`-fan-out the `criticConfig.lenses` lens `agent()` thunks against staged `stg(id,'design')` + persisted upstream `art(...)` paths; ingest each reply through `parse_critic_verdict`; call `synthesize` (via `scripts/qrspi_critic_synthesize.py`); append the synthesized verdict to the per-round verdict list; call `next_action(verdicts, round, max_rounds)`; on `revise` re-spawn the design agent with the synthesized findings (rewriting `stg(id,'design')` in place, never emptying it); break on `converged`; on `cap_reached` stage residual findings and return success (ref: §Contracts `runCriticPanelLoop`, Decisions 1–3, Risk Register row 2).
21. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a lenient critic-config parser and have `doDesign` read the optional `critics.design` block and build `criticConfig`.
    - **Current:** `doDesign(t, r)` calls `runPhase` for questions/research/design with no `criticConfig`. There is **no existing path that reads a nested `critics.design` block** — verified: `scripts/qrspi_config.py --key <KEY>` resolves a **single top-level** key only (`select_value` returns `config.get(key)`; no dot-path), so `--key critics.design` → `None`; and the JS consumer `parseConfigEnvelope` (qrspi-batch.js:324) **hard-rejects any non-string value** (`typeof env.value !== 'string'` ⇒ ok:false), so it cannot surface a nested object today.
    - **Mechanism (Option A — in-slice, no shared-module change):**
      a. **Do NOT modify `scripts/qrspi_config.py`.** It already round-trips an object value: `python3 scripts/qrspi_config.py --key critics` emits `{"ok":true,"key":"critics","value":{"design":{…}}}` (the top-level `critics` key, whose value is the nested block).
      b. Add a **lenient** parser in `.claude/workflows/qrspi-batch.js` (e.g. `parseCriticConfig(text)`) — separate from `parseConfigEnvelope` so the string-only contract there is untouched. It extracts the envelope (reuse `extractJsonObject`), accepts an **object** `value` from `--key critics`, takes `value.design` (object or `undefined`); a missing/garbled/`ok:false` envelope ⇒ `undefined` (config simply absent — opt-in seam stays off).
    - **After:** `doDesign` runs `python3 scripts/qrspi_config.py --key critics` via a config worker, passes the text to `parseCriticConfig` to get the `critics.design` object (or `undefined`); builds `CriticConfig {lenses, maxRounds:2, upstream:'research'}` applying **config value > JS default** precedence — `maxRounds` default 2, `lenses` default the four (`completeness`, `internal-consistency`, `edge-alignment`, `simplicity`); drop unknown lens names with a `log(...)` warning; an empty resolved lens set falls back to the default four (per OQ3); pass `criticConfig` as `runPhase`'s **7th** arg for the design phase only. When the `critics.design` block is absent, `criticConfig` is `undefined` and `runPhase` reproduces today's behavior (ref: §New Types `CriticConfig`, §Delta item d, OQ3, OQ1).
22. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — splice cap-reached residual findings into the design finalize commit message via `scripts/qrspi_critic_body.py` before `gt submit` (ref: §Delta item e, AC4, Decision 4).
23. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add `log(...)` per-round pass/fail/cap lines and fold a panel summary into `res.summary` (ref: §Delta item f, Risk Register row 5, Q14).

### Config

24. ⚠️ Modify `.qrspi/config.example.json` — add an optional `critics.design` block documenting the override surface.
    - **Current:** no critic keys present.
    - **After:** `"critics": {"design": {"maxRounds": 2, "lenses": ["completeness","internal-consistency","edge-alignment","simplicity"]}}` documented as optional per-run override (config > JS default) (ref: §Modified Types config schema, §Delta, OQ3).

### Tests

25. ✨ Document the design-phase eval before/after procedure (AC5) — fold the repeatable procedure (inject a live `model` into `evals/suite.json` `defaults`; run design cases `case_005/006/014` through `eval_all.py` → `run_eval.py` + `grade.py` before/after; record the delta) into the PR summary / a doc. No code slice produces a measured score (ref: OQ4, structure §Unverified Assumptions item 4, Risk Register row 3).

### Verify Slice 3

26. **Checkpoint:** end-to-end design run against the worktree (manual e2e — JS glue is not unit-tested per Q12).
    - [ ] A deliberately-flawed design triggers ≥1 revise round, then converges or caps; `res.summary` shows per-round pass/fail.
    - [ ] A design passing all four lenses on round 0 produces zero revise spawns (AC3).
    - [ ] A capped run writes residual findings into the design PR body (inspect submitted PR / staged commit message) (AC4).
    - [ ] `doDesign` with no `critics.design` config key reproduces today's single-persist design behavior (opt-in seam).
    - [ ] A `critics.design` block in `.qrspi/config.json` overrides `maxRounds` / `lenses` for the run (OQ3).

27. **Checkpoint:** regression — existing scripts unit tests still pass.
    - **Expected:** `python3 scripts/qrspi_critic_loop_test.py` and `python3 scripts/qrspi_pr_body_test.py` (the landed RUS-55 siblings) still exit 0 — confirming the new modules did not break reused contracts.

---

## Pre-build verification (blocking, before Slice 1)

Per structure §Unverified Assumptions, confirm before wiring (reads only — no code change):

- `scripts/qrspi_critic_loop.py` exports `next_action(verdicts, round, max_rounds)` and `parse_critic_verdict(raw)` with the documented signatures.
- `scripts/qrspi_pr_body.py` exports `compose_message(existing, body)`.
- `parallel()` and `agent()` runner primitives exist in `.claude/workflows/qrspi-batch.js` with a usable call shape for the lens fan-out (verify the exact signature before Step 20).
- **`runPhase`'s real signature is `runPhase(name, agentType, prompt, existing, id, phaseLabel)` (6 params, verified at qrspi-batch.js:458)** — Step 19 appends `criticConfig` as the 7th; do not assume the `runPhase(name, id, ...ctx)` shorthand.
- **No existing path reads a nested `critics.design` block (verified).** `scripts/qrspi_config.py` resolves a single top-level key only (`--key critics.design` → `None`), and `parseConfigEnvelope` rejects non-string values. Step 21 therefore reads the top-level `critics` key (whose value round-trips as an object) and parses `.design` with the new lenient `parseCriticConfig` — it does **not** rely on any pre-existing nested-block loader.

If any signature differs from structure.md, stop and report the mismatch before building.

## Rollback Notes

- **Step 15 / 19–23** (`.claude/workflows/qrspi-batch.js` edits): reversible by reverting the commit; the `if (criticConfig)` guard (Step 19) means an absent `critics.design` config already preserves today's behavior, so a partial revert that leaves config absent is safe. To fully disable the panel without reverting code, remove the `critics.design` block from `.qrspi/config.json`.
- **Step 24** (`.qrspi/config.example.json`): documentation-only; revert the commit to remove. The gitignored `.qrspi/config.json` is the live override surface — deleting the `critics.design` key there disables the panel at runtime.
- **Steps 1–9** (new Python helper + test files): new files only; `rm` the four `scripts/qrspi_critic_synthesize*.py` / `scripts/qrspi_critic_body*.py` files to roll back. No shared-module mutation.
- No DB migrations, no destructive ops — this is orchestration glue + pure Python helpers (ref: §Delta "No new DB/queries").
