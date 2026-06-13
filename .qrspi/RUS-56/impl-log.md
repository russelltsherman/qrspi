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
