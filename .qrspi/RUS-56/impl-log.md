# Implementation Log — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

## Session 1 — Slice 1

**Timestamp:** 2026-06-13T02:29:29Z
**Tasks completed:** T0, T1, T2, T3, T4, T5, T6, T7, T8, T9, T10
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_critic_synthesize_test.py` → 18 passed, 0 failed
- `python3 scripts/qrspi_critic_body_test.py` → 20 passed, 0 failed

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- Slice 1 pure Python firewall is landed and green. Two new modules + two test siblings:
  - `scripts/qrspi_critic_synthesize.py` — `synthesize(verdicts: list) -> {pass, findings}`.
    Reduces M lens entries: `pass` is True only if EVERY coerced lens passed (all-pass AND);
    `findings` is the exact-string-deduped union in first-seen order. Each entry is coerced
    fail-closed (strings via the landed `parse_critic_verdict`; dicts via a sibling `_coerce_dict`
    mirroring the landed parser's dict path). Empty/non-list input ⇒ `{pass:false, findings:[]}`.
  - `scripts/qrspi_critic_body.py` — pure core `splice(message, raw_findings) -> str` plus a
    git-free CLI (`--findings-file`, `--message-file` or stdin → spliced message on stdout).
    Empty/absent findings ⇒ message returned UNCHANGED (no-op). Reuses landed
    `compose_message` from `qrspi_pr_body.py` for the subject/body/trailer splice.
- **Lens-tagging contract (for Slice 2/3 wiring):** a lens entry carries its identifier as a
  `lens` (or `name`) string key alongside `{pass, findings}`. When present, each of that lens's
  bare-string findings is emitted as `{text, lens}`; already-`{text, lens}`-tagged findings are
  kept verbatim. Dedup keys on the plain finding TEXT (first occurrence + its tag wins). So when
  Slice 3 builds the per-lens fan-out, attach the lens name to each agent's parsed verdict before
  passing the list to `synthesize` if lens-tagged audit findings are wanted.
- **Findings serialization the body CLI accepts:** a JSON array (synthesize's `findings`, whose
  elements are bare strings or `{text, lens}` dicts — dicts render as `"text (lens)"`) OR plain
  text one-finding-per-line. So Slice 3 can stage `synthesize(...)["findings"]` as JSON directly
  into the residual-findings file `qrspi_critic_body.py` reads.
- **T0 pre-build verification (reads only) confirmed the landed signatures match structure.md:**
  `parse_critic_verdict(text) -> dict` (qrspi_critic_loop.py:49), `next_action(verdicts, round,
  max_rounds)` (qrspi_critic_loop.py:80), `compose_message(existing_message, body_text) -> str`
  (qrspi_pr_body.py:108). The `parallel()`/`agent()`/`doDesign`-config checks in §Pre-build are
  Slice 2/3 concerns (no JS touched this slice) and were NOT verified here — Slice 3 must confirm
  the `parallel()`/`agent()` call shape and `runPhase`'s 6-param signature before wiring.
- No JS, config, or shared-module files were modified — this slice is purely additive (four new
  `scripts/qrspi_critic_*.py` files). Rollback = `rm` those four files.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-13T03:05:00Z
**Tasks completed:** T11, T12, T13, T14, T15, T16, T17, T18
**Tasks failed:** none
**Tests:**

- `python3 -c "... parse_critic_verdict('{\"pass\": true, \"findings\": []}')"` → prints `{'pass': True, 'findings': []}` (valid lens reply NOT coerced to not-passed) — Step 17
- prose-wrapped non-pass probe `parse_critic_verdict('Here is my verdict:\n{...pass:false, findings:[...]...}')` → `{'pass': False, 'findings': ['AC2 ...']}` (embedded-JSON ingest works)
- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX_OK
- input-wiring grep: each of the four lens prompts references `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`, `DESIGN_PATH`, and `CRITIC_VERDICT_SCHEMA`
- scope grep: `CRITIC_VERDICT_SCHEMA` present (1 decl) in qrspi-batch.js; `runCriticPanelLoop`/`runCriticLoop` occurrences = 0 (no panel-loop wiring added, per Step 15)

**Deviations from structure.md:**

- none. The structure left lens-file packaging open ("`qrspi-design-critic.md` (or four per-lens prompt files)"); the plan (Steps 11–14) resolved it to **four separate per-lens prompt files**, which is what was built.

**Deviations from plan.md:**

- Input path arg named `DESIGN_PATH` (not the staged `stg(id,'design')` literal). The plan/structure phrase the rubric input as "staged `stg(id,'design')`"; that is the runner-side value Slice 3 will splice into the spawn prompt. Each lens prompt exposes it under the prompt-variable name `DESIGN_PATH`, matching the existing RUS-55 critic agent's `ARTIFACT_PATH` convention (a named path variable supplied by the spawner). The lens reads whatever absolute path the runner binds to `DESIGN_PATH`; Slice 3 binds it to `stg(id,'design')`. No behavioral deviation.

**Notes for next session (Slice 3 — panel loop + doDesign wiring):**

- **Four lens prompt files exist** at `.claude/agents/qrspi-design-critic-<lens>.md` for the four lens names the plan defaults to: `completeness`, `internal-consistency`, `edge-alignment`, `simplicity`. So Slice 3's default lens set `['completeness','internal-consistency','edge-alignment','simplicity']` maps 1:1 to filenames via `qrspi-design-critic-${lens}.md`. Keep that naming when building the `agent()` thunks so the lens-name → agent-file mapping stays mechanical.
- **Each lens prompt's input contract (the spawn-prompt variables Slice 3 must bind):**
  `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` → the persisted upstream `art(wd, id, ...)` paths (`research.md`, `questions.md`; the ticket content is the fetched ticket body); and `DESIGN_PATH` → the staged `stg(id,'design')` rubric being judged. Each lens emits a `{pass, findings}` reply; ingest it through `parse_critic_verdict` (qrspi_critic_loop.py:49), attach the lens name (see Slice 1's lens-tag note), then `synthesize` the M verdicts.
- **`CRITIC_VERDICT_SCHEMA` is declared** in `.claude/workflows/qrspi-batch.js` (module-level, right after `PERSIST_SCHEMA`, ~line 419) as a JSON-schema `{ pass: boolean, findings: array<string> }`. It matches the runner schema-constant convention (cf. `WORKER_SCHEMA`/`TICKETS_SCHEMA`). It is declared-but-unused this slice **by design** (Step 15: schema only, no loop) — Slice 3's `runCriticPanelLoop` is where it gets passed as each lens `agent()`'s output schema. Do NOT re-declare it; reference the existing constant.
- **STILL UNVERIFIED for Slice 3 (carry-forward from Slice 1, no JS runner primitives touched this slice):** the `parallel()` / `agent()` call shape and `runPhase`'s real 6-param signature `runPhase(name, agentType, prompt, existing, id, phaseLabel)` (plan §Pre-build cites qrspi-batch.js:458). Slice 3 must confirm these before wiring the fan-out (plan Steps 19–20) and the `criticConfig` 7th param.
- Both Slice 1 modules and the RUS-55 landed siblings remain green; no shared module was mutated this slice (qrspi-batch.js change is the additive schema constant only).

---

## Session 3 — Slice 3

**Timestamp:** 2026-06-13T03:45:00Z
**Tasks completed:** T19, T20, T21, T22, T23, T24, T25 (partial — see deviations)
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_critic_synthesize_test.py` → 23 passed, 0 failed (added 5 `decide_round` checks)
- `python3 scripts/qrspi_critic_body_test.py` → 20 passed, 0 failed
- `python3 scripts/qrspi_critic_loop_test.py` → 33 passed, 0 failed (RUS-55 regression, Step 27)
- `python3 scripts/qrspi_pr_body_test.py` → 23 passed, 0 failed (RUS-55 regression, Step 27)
- `node --check .claude/workflows/qrspi-batch.js` → SYNTAX_OK
- JS helper probe (extracted `parseCriticConfig` + `buildDesignCriticConfig` over 12 fixtures) → ALL PASS
- Config round-trip: `qrspi_config.py --key critics` with a block → `value` is the nested object; absent block → `value:""` (→ `parseCriticConfig` returns `undefined` → panel off, today's behavior)
- End-to-end residual splice: `qrspi_critic_body.py` with a `[{text,lens},"bare"]` residual JSON → "## Residual critic findings" block in the design commit body; `[]` → message unchanged (no-op)

**Deviations from structure.md:**

- `runPhase` gains a **7th `criticConfig` param AND an 8th `criticCtx` param** (not just the single trailing param structure/plan named). `criticConfig` is the immutable `{lenses, maxRounds, upstream}`; `criticCtx` `{wd, r, residualFindings, panelSummary}` is the mutable side-channel the panel writes its residual-findings JSON + summary back into (the panel needs `wd`/`r` for the `art()`/`stg()`/`ticketContentPath` paths, and must hand its residuals back to the finalize splice). Both are optional and guarded by `if (criticConfig && criticCtx)`; absent → byte-for-byte today's produce→persist. No other `runPhase` caller passes them.

**Deviations from plan.md:**

- **Added a `decide_round` CLI to `scripts/qrspi_critic_synthesize.py` (additive, `__main__`-guarded).** Step 20 says "call `synthesize` (via `scripts/qrspi_critic_synthesize.py`)" and "call `next_action`", but the Slice-1 `synthesize` module was a pure LIBRARY with NO CLI, and the JS sandbox cannot run python. Rather than re-implement the reduction/decision in JS (forbidden — it would drift from the tested helpers) or embed a fragile inline `python3 -c`, I added `decide_round(verdicts, round, max_rounds)` + a stdin/stdout `__main__` that reuses BOTH landed pure functions (`synthesize` here + `next_action` imported from `qrspi_critic_loop`) in one deterministic invocation. The panel worker pipes `{verdicts, round, max_rounds}` to it and gets back `{action, pass, synthesized_findings, residual_findings}`. The Slice-1 `synthesize` function and its tests are untouched (the `__main__` guard never fires under import); 5 new `decide_round` unit tests added to the existing test file.
- **T25 (eval before/after procedure doc) is deferred to the PR-summary phase**, per plan Step 25 / structure §Unverified-Assumptions item 4 (the eval harness is a non-functional placeholder; no code slice produces a measured score). The repeatable procedure belongs in `pr-summary.md`, authored by the `/qrspi-pr` phase, not in this implementation slice.
- **T26 end-to-end batch run is NOT executed here** (manual e2e, JS glue is not unit-tested per Q12). It requires a live Linear ticket + Graphite stack + reviewer, which is the finalize/submit path the orchestrator drives — outside this slice's verifiable scope. The panel's pure decision logic (`decide_round`), the config seam (`parseCriticConfig`/`buildDesignCriticConfig`), and the residual-splice (`qrspi_critic_body.py`) are each independently verified above; the JS fan-out wiring is syntax-checked and its helper logic probed.

**Notes for next session (Slice 3 is the final slice; these are for PR / review):**

- **`runCriticPanelLoop(name, id, criticConfig, wd, r, phaseLabel)`** runs inside `runPhase`'s produce→persist window (after the design agent stages `stg(id,'design')`, before `persistArtifact`). Per round: `parallel()`-fan-out `runLens(lens, ...)` for each `criticConfig.lenses` (agentType `qrspi-design-critic-${lens}`, schema `CRITIC_VERDICT_SCHEMA`); attach the lens name; pipe `{verdicts, round, max_rounds}` to `scripts/qrspi_critic_synthesize.py` (`decide_round`); on `converged` → return (residual `[]`); on `cap_reached` → stage residual findings JSON + return; on `revise` → re-spawn the `qrspi-design` agent to REWRITE `stg(id,'design')` in place with the synthesized findings, then next round. A null lens reply fails closed (not-passed). A null synth-worker or null revise re-spawn ends the panel gracefully (`ok:true`, persist the current staged design) rather than failing the ticket — the panel is an opt-in quality gate, not a hard blocker.
- **Opt-in seam:** `doDesign` reads the top-level `critics` key via a config worker (`qrspi_config.py --key critics`), `parseCriticConfig` extracts `.design`, `buildDesignCriticConfig` resolves `{lenses, maxRounds:2, upstream:'research'}` with **config > JS default** precedence (unknown lenses dropped + warned; empty resolved set falls back to the four; invalid `maxRounds` ignored). Absent/garbled config ⇒ `criticConfig` undefined ⇒ `runPhase` reproduces today's single-persist behavior. The panel is also skipped entirely when resuming an already-persisted `design.md` (`r.existing['design']`).
- **PR-body splice:** when the panel caps, `criticCtx.residualFindings` (JSON of synthesize's findings) rides into the design finalize worker, which writes it to `/tmp/phase-stage/<id>/critic-residual.json` and runs `qrspi_critic_body.py --findings-file ... --message-file ...` to splice a "Residual critic findings" block into the design commit message BEFORE `gt modify -c` (the only non-interactive PR-body lever — no `gt` body flag, no `gh pr edit`). Converged/panel-off ⇒ no splice step emitted (the commit message is unchanged).
- **`res.summary` fold:** the per-round `r<N>:pass/fail(<k>)` + `cap_reached` summary is logged per round and appended to the ticket result summary as `[critic: ...]`.
- **Config example:** `.qrspi/config.example.json` documents the optional `critics.design` `{maxRounds, lenses}` block. The live override is the gitignored `.qrspi/config.json`; deleting the block disables the panel at runtime.

---
