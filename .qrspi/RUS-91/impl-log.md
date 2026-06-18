# Implementation Log — Bring the /review-* on-demand review family up to manual-review depth

## Session 1 — Slice 1

**Timestamp:** 2026-06-18T02:44:22Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7, T8, T9, T10
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 42 passed, 0 failed
- `python3 scripts/run_tests.py critic` → 6 passed, 0 failed
- `python3 scripts/run_tests.py synopsis` → 1 passed, 0 failed

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- T8 (`qrspi_critic_summary.py`) confirmed a NO-OP, as the plan anticipated (step 8 / Unverified Assumption 1): `summarize` already reads every row field via `.get()` and buckets per-lens on the bare `rnd["lens"]`. The new optional `axes`/`nonBlockingNotes` row fields are inert to its math, so no source change was made — only the backward-compat test (T9) was added.

**Notes for next session:**

- New config constants in `scripts/qrspi_critics_config.py` (all importable):
  - `DEFAULT_REVIEW_DESIGN_LENSES = ("completeness", "internal-consistency", "edge-alignment", "simplicity", "design-review")` — ORDERED tuple; DISTINCT from the batch `DEFAULT_DESIGN_LENSES` (four lenses, no `design-review`).
  - `DEFAULT_REVIEW_PLAN_LENSES = ("plan-review", "plan-fidelity", "plan-completeness")`
  - `DEFAULT_REVIEW_IMPL_LENSES = ("impl-review", "impl-fidelity", "impl-completeness")`
  - `KNOWN_PLAN_LENSES` / `KNOWN_IMPL_LENSES` — `set(...)` allow-lists of the two panels.
  - Lens id → agent mapping is `qrspi-<phase>-critic-<lens-id>`. Plan/impl ids are phase-qualified (e.g. `plan-fidelity` → `qrspi-plan-critic-plan-fidelity`). The Slice 2 agent FILENAMES must therefore be `qrspi-plan-critic-plan-fidelity.md`, `qrspi-plan-critic-plan-completeness.md`, `qrspi-impl-critic-impl-fidelity.md`, `qrspi-impl-critic-impl-completeness.md` — NOTE the worktree.md task table (T14/T16/T18/T20) lists shorter names (`qrspi-plan-critic-fidelity.md` etc.); the structure.md/plan.md authoritative names (phase-qualified) are the ones that resolve correctly. Follow structure.md/plan.md, not the worktree.md filename shorthand.

- New module `scripts/qrspi_review_synopsis.py` (pure stdlib, no I/O). Public API the Slice 3+ skills will call:
  - `partition_decision_readiness(verdict_array) -> (panel_array, decision_readiness_verdict_or_None)` — splits the `decision-readiness` lens element out of the pre-reduction verdict array so it never reaches `qrspi_critic_synthesize.py`. Returns `None` for the DR verdict when the lens is absent.
  - `render_synopsis(verdict_array, decision_readiness, terminal_action) -> str` — Markdown synopsis: an axis-enumeration table (one row per lens: `| <lens> | PASS|FAIL | <blockingCount> |`), an "Advisory (non-blocking)" section (union of each lens's `nonBlockingNotes`, omitted if empty), a "Decision readiness (blocking for human)" section (DR `blockingDecisions`, omitted if DR is None or has no blocking items), and a `**Terminal action:** <x>` line. Accepts `decision_readiness=None`.
  - `ledger_row_fields(verdict_array) -> {"axes": [{"lens","pass","blockingCount"}], "nonBlockingNotes": [str]}` — the additive `critic-metrics.jsonl` fields. Per plan step 34, MERGE this dict onto the row dict returned by `qrspi_review_record.build_record(...)` before appending the metrics row (it is NOT a `build_record` parameter).
  - `DECISION_READINESS_LENS = "decision-readiness"` — the lens-id constant the partition keys on.

- `LensVerdict` shape consumed by these helpers: `{"lens": str, "pass": bool, "findings": [str], "nonBlockingNotes": [str](optional)}`. `findings` is the BLOCKING channel (drives `blockingCount`); `nonBlockingNotes` is advisory only. `blockingCount` = `len(findings)`.

- `DecisionReadinessVerdict` shape: `{"lens": "decision-readiness", "blockingDecisions": [{"question": str, "rationale": str}], "answerable": [{"question": str}]}`.

---

## Session 2 — Slice 2

**Timestamp:** 2026-06-18T02:49:38Z
**Tasks completed:** T11, T12, T13, T14, T15, T16, T17, T18, T19, T20, T21, T22 (six agent files authored with full contracts inline)
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 42 passed, 0 failed (regression gate; Slice 2 adds no new Python so the suite is unchanged-green)
- Agent-frontmatter validation script (inline) → all 6 agents: well-formed `---` frontmatter, `name` field equals filename, `description` + `tools` present → exit 0

**Deviations from structure.md:**

- none — all six agent FILENAMES follow the structure.md/plan.md authoritative phase-qualified names (`qrspi-plan-critic-plan-fidelity.md`, `qrspi-plan-critic-plan-completeness.md`, `qrspi-impl-critic-impl-fidelity.md`, `qrspi-impl-critic-impl-completeness.md`, `qrspi-design-critic-decision-readiness.md`, `qrspi-critic-reviser.md`), NOT the worktree.md shorthand (T14/T16/T18/T20 listed shorter `qrspi-plan-critic-fidelity.md` etc.). This honors the Slice-1 hand-off note and the load-bearing lens-id ↔ agent mapping `qrspi-<phase>-critic-<lens-id>`.

**Deviations from plan.md:**

- **T11/T23 (skill-creator eval loop) NOT run as written; T24–T26 routing/manual probes NOT run.** Rationale, not skipped silently: (a) these six are `.claude/agents/*.md` SUBagents, not SKILL.md skills — the `skill-creator` skill targets SKILL.md authoring; (b) MEMORY directive `skill-creator-run-eval-invalid-in-sandbox` records that the skill-creator `run_eval`/`run_loop` returns bogus uniform results in this sandbox, so running it would produce no real signal; (c) the `claude -p` routing probes (plan T24) and manual descoped-sample / reviser-write probes (T25/T26) require spawning live `claude -p` subagent subprocesses, which is out of scope for a deterministic implement-phase agent and is not a runnable gate here. Instead, the agents were authored to EXACT fidelity with the repo's three already-shipped, code-verified sibling lens agents (`qrspi-plan-critic-plan-review.md`, `qrspi-impl-critic-impl-review.md`, `qrspi-design-critic-completeness.md`) — same frontmatter shape, same `{pass, findings}` verdict-schema discipline, same fail-closed + blocking-only invariant — and validated structurally (frontmatter + name↔filename + verdict-schema/contract prose present). The live routing/probe validation (T24–T27 checkboxes) remains for a human/e2e pass before Slice 3 wiring relies on these `subagent_type`s.

**Notes for next session:**

- Six new agents now exist in `.claude/agents/`, each with its full contract authored INLINE (no separate spec file). Slice 3 wires them by `subagent_type` (= the filename without `.md`):
  - `qrspi-critic-reviser` — the SHARED non-producer reviser. Inputs: `PHASE` (`design|plan|impl`), `OUTPUT_PATH` (the ONLY writable path — scratch-verbatim), `RESIDUAL_FINDINGS` (node-validity/fidelity findings ONLY — decision-readiness excluded by contract), plus OPTIONAL `RESEARCH_PATH`/`CODEBASE_PATH`/`TICKET_CONTENT_PATH`/`QUESTIONS_PATH`/`STRUCTURE_PATH`/`PLAN_PATH`/`DESIGN_PATH`/`TEMPLATE_PATH`. Tools: `Read, Grep, Write`. Replaces the producer (`qrspi-design`/`qrspi-plan`/`qrspi-implement`) in the revise loop. It writes the revised artifact back to `OUTPUT_PATH` verbatim and returns a plain-text summary. THIS is the only Slice-2 agent with `Write`.
  - `qrspi-plan-critic-plan-fidelity` (lens id `plan-fidelity`) and `qrspi-plan-critic-plan-completeness` (`plan-completeness`) — plan-panel fidelity + coverage lenses. Tools: `Read, Grep`. Inputs: `PLAN_PATH`, `TICKET_CONTENT_PATH` (declared + consumed), OPTIONAL `STRUCTURE_PATH`/`RESEARCH_PATH`/`CODEBASE_PATH` (fidelity) / `QUESTIONS_PATH` (completeness).
  - `qrspi-impl-critic-impl-fidelity` (`impl-fidelity`) and `qrspi-impl-critic-impl-completeness` (`impl-completeness`) — impl-panel fidelity + coverage lenses. Tools: `Read, Grep`. Inputs: `IMPL_PATH`, `TICKET_CONTENT_PATH`, `CODEBASE_PATH` (REQUIRED — they verify against real implemented source + tests over the AGGREGATED slice stack, one pass, per plan step 44), OPTIONAL `PLAN_PATH`/`STRUCTURE_PATH`/`QUESTIONS_PATH`.
  - All four fidelity/completeness lenses emit the EXTENDED `LensVerdict`: `{pass, findings, nonBlockingNotes?}` — `findings` is the BLOCKING channel (drives the synthesize/revise loop), `nonBlockingNotes` is the OPTIONAL advisory channel that `render_synopsis()` surfaces. They enforce the adversarial contract: a NAMED descoping/deviation counter-example OR an affirmative "no AC narrowed/uncovered, checked each: <list>", with fail-closed `pass:false` default under uncertainty.
  - `qrspi-design-critic-decision-readiness` (lens id `decision-readiness`) — emits the DISTINCT `DecisionReadinessVerdict` `{lens:"decision-readiness", blockingDecisions:[{question,rationale}], answerable:[{question}]}`, NOT `{pass, findings}`. Tools: `Read, Grep`. Inputs: `DESIGN_PATH`, `TICKET_CONTENT_PATH`, OPTIONAL `RESEARCH_PATH`/`QUESTIONS_PATH`/`CODEBASE_PATH`. It is NON-PRODUCING and TERMINAL-ADVISORY: Slice 3 must call `partition_decision_readiness()` (Slice-1 helper) to split this verdict OUT of the array fed to `qrspi_critic_synthesize.py` so it never drives a revise round — it feeds `render_synopsis()`'s decision-readiness section only.
  - `TICKET_CONTENT_PATH` is now a declared+consumed input on all five lenses; Slice 3/4 must actually pass it (= `/tmp/phase-stage/<id>/review/ticket.md`) to the fidelity/completeness/decision-readiness lenses ONLY (node-validity `*-review` lenses stay research+code-only, unchanged).

---
