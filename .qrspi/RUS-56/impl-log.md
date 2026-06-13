# Implementation Log — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

## Session 1 — Slice 1: Pure synthesis helper (Python firewall)

**Timestamp:** 2026-06-13T13:42:52Z
**Tasks completed:** T0, T1, T2, T3, T4, T5
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_critic_synthesize_test.py` → 24 passed, 0 failed (exit 0)

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- none

**Notes for next session:**

- New file `scripts/qrspi_critic_synthesize.py` exports `synthesize(verdicts: list) -> {"pass": bool, "findings": list}`. It reduces M raw per-lens replies to one authoritative round verdict: `pass` is True only if the list is non-empty AND every coerced lens passed; `findings` is the exact-string-deduped union (first-seen order).
- `synthesize` reuses the LANDED coercion from `qrspi_critic_loop.py` (no re-implemented coercion): dict entries route through `_coerce_verdict`, string entries through `parse_critic_verdict`, anything else fails closed to NOT-passed. Verified by a test asserting a passing JSON-string entry's synthesis matches `parse_critic_verdict`'s own output.
- Optional lens-tagging: a lens entry carrying a top-level `"lens": "<id>"` key has its bare-string findings wrapped as `{"text": <finding>, "lens": <id>}`; findings from an unidentified lens, and findings already shaped as `{text, lens}` dicts, are emitted unchanged. Dedupe keys on finding TEXT (so `"dup"` and `{"text":"dup",...}` collapse to one, first-seen wins).
- Slice 2 (lens prompts) only needs the verdict contract `{pass, findings}` — it does NOT need synthesize's internals. The four lens agents should emit replies that `parse_critic_verdict` accepts; `runCriticPanelLoop` (Slice 3) will pass each reply to `synthesize` as a dict with an added `lens` key for tagging (so the panel can populate the lens tag at fan-out time — lens prompts themselves need not emit a `lens` field).
- `synthesize` never raises (battery of garbage inputs tested). Empty verdict list ⇒ `pass:false` (fail closed: no lens attested).

---

## Session 2 — Slice 2: Lens agent prompts

**Timestamp:** 2026-06-13T13:45:44Z
**Tasks completed:** T6, T7, T8, T9, T10
**Tasks failed:** none
**Tests:**

- `python3 -c "...parse_critic_verdict('{\"pass\": true, \"findings\": []}')..."` ingest probe → returns `{'pass': True, 'findings': []}` (valid reply, not coerced to not-passed). A fail-with-findings reply `{"pass": false, "findings": ["AC2 ... never addressed"]}` also parses unchanged. → pass
- `grep -rn CRITIC_VERDICT_SCHEMA .claude/workflows/qrspi-batch.js` → only the landed definition (line 416) + its landed reference (line 515); no new schema const in any new `.md` (grep over the four lens files matches nothing). → confirms no `CRITIC_VERDICT_SCHEMA` added.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- Plan step 6 names the staged design input only as "staged `stg(id,'design')`" without a fixed prompt variable name. The four prompts standardize on `DESIGN_PATH` for the staged design (alongside the explicitly-named `TICKET_CONTENT_PATH`/`RESEARCH_PATH`/`QUESTIONS_PATH`). Slice 3's `runCriticPanelLoop` must pass the staged design path under `DESIGN_PATH` in the lens spawn prompts. This is a naming choice, not a contract change — the verdict output contract `{pass, findings}` is unchanged.

**Notes for next session:**

- Four lens prompt files created under `.claude/agents/`: `qrspi-design-critic-completeness.md`, `qrspi-design-critic-internal-consistency.md`, `qrspi-design-critic-edge-alignment.md`, `qrspi-design-critic-simplicity.md`. Each declares `name:` matching its filename and `claude: tools: Read` (read-only, mirroring the landed `qrspi-critic.md`).
- **Lens id ↔ agent name mapping for Slice 3's DEFAULT_FOUR / agentType:** the structure/plan default lens set is `["completeness","internal-consistency","edge-alignment","simplicity"]`; each lens id maps to agent `qrspi-design-critic-<id>` (e.g. lens `edge-alignment` → agentType `qrspi-design-critic-edge-alignment`). `runCriticPanelLoop` will need to derive the agentType from the lens id this way (prefix `qrspi-design-critic-`).
- **Spawn-prompt inputs each lens expects** (Slice 3 must splice these absolute paths into each lens `agent()` thunk's prompt): `DESIGN_PATH` = staged `stg(id,'design')`; `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` = persisted `art(...)` paths for ticket content / research.md / questions.md. All four lenses take the identical input set.
- Each lens emits a `{pass, findings}` reply only (no `lens` field) — confirmed against the landed `parse_critic_verdict` and the per Session-1 note that the panel adds the `lens` tag at fan-out time. So Slice 3 should spawn each lens with `schema: CRITIC_VERDICT_SCHEMA` (the landed constant at qrspi-batch.js:416, mirroring how `runCriticLoop` spawns `qrspi-critic` at qrspi-batch.js:515) and tag each reply with its lens id before handing the list to `synthesize`.
- No JS, config, or Python files were touched in this slice — Markdown agent definitions only. `CRITIC_VERDICT_SCHEMA` was referenced (the landed constant), not re-added.

---

## Session 3 — Slice 3: Panel loop + doDesign rewiring + config

**Timestamp:** 2026-06-13T00:00:00Z
**Tasks completed:** T11, T12, T13, T14, T15, T16, T18 (logic+regression+dispatch verification), T19, T20
**Tasks failed:** none
**Tasks deferred:** T17 (document the eval before/after procedure) — this is a `pr-summary.md` deliverable produced in the PR phase (`/qrspi-pr`), not an implementation artifact; not fabricated here. T18's true e2e (live design run) is manual/non-automatable per Q12 — the runnable portions (JS logic, regression, dispatch-by-inspection) are verified below.

**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → OK (syntax clean after all edits)
- Node logic harness for `parseCriticConfig` + `resolveDesignCritic` (verbatim copies of the two new source functions, exercised against config envelopes + override matrices) → 17/17 passed (no-config⇒undefined, ok:false/key-mismatch/garbage⇒undefined, nested design returned; maxRounds override + invalid⇒default 2; lens subset/unknown-dropped/all-unknown⇒four/empty⇒four/non-array⇒four)
- `python3 scripts/qrspi_critic_synthesize_test.py` → 24 passed, 0 failed (exit 0) — the new CLI shim did NOT regress the pure reducer
- New `qrspi_critic_synthesize.py` CLI shim verified: tagged-verdict stdin (the shape the JS fan-out sends) → `{"pass": false, "findings": [{"text": "dropped AC3", "lens": "edge-alignment"}]}`; empty/garbage stdin → `{"pass": false, "findings": []}` (fail-closed)
- `python3 -c json.load(.qrspi/config.example.json)` → OK (valid JSON after the `critics.design` block)
- Dispatch-by-inspection (T19): `planCritic` (line 1097) has NO `lenses` field ⇒ `criticConfig.lenses?.length` falsy ⇒ routes to the landed single-critic `runCriticLoop`; only `designCritic` sets `lenses` ⇒ routes to `runCriticPanelLoop`. Plan phase untouched.
- Lens id↔agentType mapping (T11): all four default lenses resolve `qrspi-design-critic-<id>` to a landed agent whose `name:` field MATCHES; all four lens prompts declare the identical `DESIGN_PATH/TICKET_CONTENT_PATH/RESEARCH_PATH/QUESTIONS_PATH` input set the fan-out splices.
- Regression (T20): `python3 scripts/qrspi_critic_loop_test.py` → 33/33 (exit 0); `python3 scripts/qrspi_pr_body_test.py` → 23/23 (exit 0) — landed RUS-55 reused contracts intact.

**Deviations from structure.md:**

- **Added a thin CLI shim to `scripts/qrspi_critic_synthesize.py`.** Slice 1 created the pure `synthesize` function but NO CLI entry point. Slice 3's `runCriticPanelLoop` must invoke `synthesize` from the JS sandbox, which cannot run Python — exactly the constraint `criticDecision`→`qrspi_critic_loop.py`'s CLI solves. I added a `main()` stdin→stdout shim (`printf '%s' '<json array>' | python3 qrspi_critic_synthesize.py` → `{pass, findings}`) mirroring `qrspi_critic_loop.py`'s landed shim verbatim. The pure `synthesize` function is UNCHANGED (its 24-check test still passes); this is additive wiring, squarely in Slice 3's "panel loop wiring" scope. Structure §Contracts described "call `synthesize`" without specifying the invocation mechanism — this is the mechanism, not a contract change.

**Deviations from plan.md:**

- Plan step 15 says "fold a panel summary into `res.summary`". In `doDesign` the result object is `out` (from `finResult`), not `res` (`res` is a land-action local at line ~1281). I folded the panel's per-round pass/fail summary into `out.summary` alongside the existing residual-finding fold (mirroring the landed line 1041 pattern). `runCriticPanelLoop` returns a `summary` string, `runPhase` writes it back as `criticConfig.criticSummary`, and `doDesign` appends it to `out.summary`. Same intent, correct variable.
- Plan step 14 keeps `upstreamPath: art(wd,id,'research.md')` and adds `lenses`. I ALSO added `ticketContentPath` + `questionsPath` to the `designCritic` object, because the lens prompts (Slice 2) require all four inputs (`DESIGN_PATH/TICKET_CONTENT_PATH/RESEARCH_PATH/QUESTIONS_PATH`) and `runCriticPanelLoop` needs the upstream paths on `criticConfig` (it has no `wd`/`r` in scope, per the deferred-context pattern). The single-critic `runCriticLoop` ignores these extra fields, so the plan-phase path is unaffected.

**Notes for next session:**

- This is the final implementation slice. Remaining for the PR phase (`/qrspi-pr`): write `pr-summary.md` INCLUDING the documented design-phase eval before/after procedure (plan T17 / AC5 — inject a live `model` into `evals/suite.json` `defaults`, run design cases `case_005/006/014` through `eval_all.py`→`run_eval.py`+`grade.py` before/after, record the delta; the eval harness is a non-functional placeholder so no measured score is produced — the procedure is documentation only).
- **Files changed this slice:** `.claude/workflows/qrspi-batch.js` (added `SYNTHESIZED_VERDICT_SCHEMA`, `DEFAULT_DESIGN_LENSES`/`KNOWN_DESIGN_LENSES`, `parseCriticConfig`, `resolveDesignCritic`, `runCriticPanelLoop`, `synthesizeVerdicts`, `readDesignCriticConfig`; rewired `runPhase` dispatch + `doDesign` designCritic build + `out.summary` fold), `.qrspi/config.example.json` (added optional `critics.design` block + `$comment` doc), `scripts/qrspi_critic_synthesize.py` (added CLI shim — see structure deviation).
- **The panel is opt-in and the single-critic path is byte-for-byte unchanged.** With no `critics.design` config, `doDesign` still runs the panel with the DEFAULT four lenses (this is the design phase's new always-on behavior, replacing today's single design edge-critic). Every OTHER `runPhase` caller (questions/research/structure/worktree) passes no `criticConfig`; the plan phase passes a `planCritic` WITHOUT `lenses` and routes to `runCriticLoop`. Only the design phase gets the panel.
- True end-to-end verification (a live design run producing real lens spawns + a revise round) was NOT run — the JS orchestration glue is not unit-testable in this sandbox (no `agent()`/`parallel()` runtime; per Q12 it is manual-e2e only). The logic, regression, dispatch, and mapping are all verified above; the e2e checkpoint (flawed design ⇒ ≥1 revise then converge/cap; clean design ⇒ 0 revise spawns; cap ⇒ residuals in PR body; config override) remains a manual reviewer step on a real batch run.

---
