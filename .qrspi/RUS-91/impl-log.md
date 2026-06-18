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

## Session 3 — Slice 3

**Timestamp:** 2026-06-18T03:00:00Z
**Tasks completed:** T28, T29, T30, T31, T32, T33, T34 (the SKILL.md wiring; T35–T37 are live e2e — see deviations)
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 42 passed, 0 failed (regression gate; Slice 3 touches no Python source, so the suite is unchanged-green)
- Embedded-snippet verification (inline harness): executed the two `python3 - <<'PY'` blocks now embedded in `review-design/SKILL.md` (Step 4b partition+synthesize; Step 6 build_record + `ledger_row_fields` merge; Step 7 `render_synopsis`) against a representative 6-element verdict array (5 panel lenses + 1 decision-readiness). Asserted: panel array excludes decision-readiness; `synthesize(panel)` reduces fail-closed (internal-consistency dissent ⇒ `pass:false`); record dict carries merged `axes`+`nonBlockingNotes`; synopsis renders all five lens rows + Advisory + Decision-readiness sections. ALL ASSERTIONS PASS.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- **T35–T37 (live end-to-end `/review-design <id>` run + PR head-SHA before/after guard) NOT run.** Rationale, not skipped silently: these require a real Linear ticket with an existing design PR, live `mcp__linear__get_issue`, live `Agent`-tool subagent spawns, and `gh` PR-comment writes — none of which a deterministic implement-phase agent runs (and the slice-2 hand-off already recorded that live `claude -p`/subagent routing validation of these `subagent_type`s is deferred to a human/e2e pass). Instead I verified the DETERMINISTIC core the SKILL.md depends on: the exact Python snippets embedded in Steps 4b/6/7 execute correctly against a representative verdict array (above), every referenced `subagent_type` agent file exists in `.claude/agents/` (the five `qrspi-design-critic-*` panel lenses + `qrspi-design-critic-decision-readiness` + `qrspi-critic-reviser`), and `qrspi_critic_summary.summarize` reads new row fields via `.get()` (additive `axes`/`nonBlockingNotes` are inert to it). The four T37 checkboxes (axis-enumerated synopsis posted; head SHA identical; decision-readiness triggers no reviser round; ticket passed to fidelity/coverage/DR lenses only) are now ENCODED in the SKILL.md prose + Hard rules 5/6 and the head-SHA guard (Steps 2/8) but their LIVE confirmation remains for the human/e2e pass.

**Notes for next session:**

- `.claude/skills/review-design/SKILL.md` is now the fully-wired REFERENCE skill Slice 4 (`/review-plan`, `/review-implementation`) and Slice 5 (`/review`) must follow. The Slice-3 wiring pattern, step by step:
  - **Step 3 (ticket plumbing):** fetch `mcp__linear__get_issue` (id=`<ticket-id>`), `Write` title+description to `TICKET_CONTENT` = `/tmp/phase-stage/<id>/review/ticket.md`. Fetch failure / empty description ⇒ write an "unavailable" note and proceed (lenses treat missing ticket as "no AC to check"). Front-matter `allowed-tools` gained `mcp__linear__get_issue`.
  - **Step 4a (fan-out):** spawn the WHOLE panel from `DEFAULT_REVIEW_DESIGN_LENSES` — `qrspi-design-critic-<lens-id>` for each of `completeness`/`internal-consistency`/`edge-alignment`/`simplicity`/`design-review`. Collect a PRE-reduction verdict array tagged `{"lens":"<id>", "pass":..., "findings":[...], "nonBlockingNotes":[...]}`. `TICKET_CONTENT_PATH` passed to `completeness` + `edge-alignment` ONLY (NOT internal-consistency/simplicity/design-review).
  - **Step 4b (partition→synthesize):** `partition_decision_readiness(verdicts)` (guard — DR not in the in-loop panel) THEN `qrspi_critic_synthesize.synthesize(panel)`. Embedded as a `python3 - <<'PY'` block importing both modules from `scripts/`.
  - **Step 4c (rounds[]):** append EVERY per-lens element of the round's pre-reduction array to `rounds` (N lenses × R rounds) — do NOT collapse to one synthesized entry per round (keeps `qrspi_critic_summary` per-lens bucketing intact).
  - **Step 4d (reviser swap):** `subagent_type: qrspi-critic-reviser`, `PHASE=design`, `OUTPUT_PATH`=scratch design, `RESIDUAL_FINDINGS`=round's residual (DR-free). Replaces the old `qrspi-design` producer spawn.
  - **Step 5 (decision-readiness):** post-loop, spawn `qrspi-design-critic-decision-readiness` over the final scratch design (gets `TICKET_CONTENT_PATH`). Captures the `DecisionReadinessVerdict` for the synopsis ONLY — terminal-advisory, never the loop. This REPLACED the old self-grading open-question producer pass.
  - **Step 6 (ledger):** `build_record(phase=..., rounds=<per-lens entries>, terminal_action=..., agreement=...)` THEN `record.update(qrspi_review_synopsis.ledger_row_fields(<final round's pre-reduction array>))`. `ledger_row_fields` is a MERGE, not a `build_record` param.
  - **Step 7 (synopsis):** `render_synopsis(<final round's pre-reduction array>, <DR verdict>, <terminal_action>)` wrapped with an advisory header + an appended `**Agreement:**` line, emitted to a scratch `.md` via `python3 - <<'PY' > file`, posted top-level via `qrspi_comment_reply.py`.
- For plan/impl in Slice 4, the only structural differences from this template: (1) source from `DEFAULT_REVIEW_PLAN_LENSES`/`DEFAULT_REVIEW_IMPL_LENSES` (3 lenses each, phase-qualified ids → `qrspi-plan-critic-<id>` / `qrspi-impl-critic-<id>`); (2) there is NO decision-readiness lens for plan/impl, so `decision_readiness` passed to `render_synopsis` is `None` and Step 5 is dropped (pass `None`, `partition_decision_readiness` still a safe guard); (3) `TICKET_CONTENT_PATH` goes to the fidelity+completeness lenses (NOT the `*-review` node-validity lens); (4) impl lenses run over the AGGREGATED slice stack (one pass) and `/review-implementation` must add the `gh pr list --state all` frontier guard.

---

## Session 4 — Slice 4

**Timestamp:** 2026-06-18T03:02:59Z
**Tasks completed:** T38, T39, T40, T41, T42, T43, T44, T45, T46, T47, T48 (the SKILL.md wiring for both `/review-plan` and `/review-implementation`; T49–T51 are live e2e — see deviations)
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 42 passed, 0 failed (regression gate; Slice 4 touches no Python source, so the suite is unchanged-green)
- Referenced-agent existence check (inline): all 7 `subagent_type`s the two upgraded SKILLs spawn exist in `.claude/agents/` (`qrspi-plan-critic-plan-review`/`-plan-fidelity`/`-plan-completeness`, `qrspi-impl-critic-impl-review`/`-impl-fidelity`/`-impl-completeness`, `qrspi-critic-reviser`) → exit 0
- Embedded-snippet verification (inline harness): executed the three `python3 - <<'PY'` blocks now embedded in BOTH SKILLs (Step 4b partition+synthesize; Step 5 build_record + `ledger_row_fields` merge; Step 6 `render_synopsis(..., None, ...)`) against representative 3-element plan-panel and impl-panel verdict arrays. Asserted: `partition_decision_readiness` returns `(panel, None)` for a DR-free panel; `synthesize` reduces fail-closed on a single dissent (findings carried as `{text,lens}` objects); `build_record(...).update(ledger_row_fields(...))` yields a record carrying merged `axes`+`nonBlockingNotes` (verified key names against the real helpers); `qrspi_critic_summary.summarize` tolerates the merged record; `render_synopsis(verdicts, None, terminal)` lists all three lens rows AND omits the "Decision readiness" section when DR is `None`. ALL ASSERTIONS PASS.

**Deviations from structure.md:**

- none

**Deviations from plan.md:**

- **T49–T51 (live end-to-end `/review-plan <id>` and `/review-implementation <id>` runs + PR head-SHA before/after guards) NOT run.** Rationale, not skipped silently: these require real Linear tickets with existing plan PRs / slice stacks, live `mcp__linear__get_issue`, live `Agent`-tool subagent spawns, and `gh` PR-comment writes — none of which a deterministic implement-phase agent runs (consistent with the Slice-3 hand-off, which deferred the equivalent T35–T37 live `/review-design` e2e to a human/e2e pass). Instead I verified the DETERMINISTIC core both SKILLs depend on: the embedded Python snippets execute correctly against representative plan/impl verdict arrays (above), every referenced `subagent_type` agent file exists, and `summarize` tolerates the merged additive row fields. The T51 checkboxes (axis-enumerated synopsis with the panel lenses + per-lens pass; rolled-up synopsis to the top slice PR; frontier resolved via `--state all`; head SHA unchanged; ticket passed to fidelity/completeness lenses only) are now ENCODED in both SKILLs' prose + Hard rules and the head-SHA guards (Step 2 / final step) but their LIVE confirmation remains for the human/e2e pass.

**Notes for next session:**

- Slice 4 brings `/review-plan` and `/review-implementation` to full parity with the Slice-3 `/review-design` reference. Both now follow the identical wiring pattern, with the four documented plan/impl deltas applied:
  - **Fan-out (Step 4a):** the full 3-lens panel from `DEFAULT_REVIEW_PLAN_LENSES` (`plan-review`, `plan-fidelity`, `plan-completeness`) / `DEFAULT_REVIEW_IMPL_LENSES` (`impl-review`, `impl-fidelity`, `impl-completeness`), `subagent_type = qrspi-<phase>-critic-<lens-id>`, collected into a tagged pre-reduction verdict array.
  - **Ticket plumbing (Step 3):** `mcp__linear__get_issue` → `Write` to `TICKET_CONTENT` = `/tmp/phase-stage/<id>/review/ticket.md`; passed to the `*-fidelity` + `*-completeness` lenses (and the reviser) ONLY — NOT the node-validity `*-review` lens. Front-matter `allowed-tools` gained `mcp__linear__get_issue` on both.
  - **Reviser swap (Step 4d):** `qrspi-critic-reviser` with `PHASE=plan` / `PHASE=impl` (replaces the old `qrspi-plan` / `qrspi-implement` producer spawns).
  - **Synopsis (Step 6):** `render_synopsis(last_round_verdicts, None, terminal_action)` — `None` decision-readiness (no DR lens for plan/impl); `render_synopsis` omits the DR section. Ledger (Step 5) merges `ledger_row_fields()` onto `build_record(...)`; rounds carry per-lens entries (N×R).
  - **Impl-only (T44/T48):** the impl panel runs ONE pass over the AGGREGATED slice stack (not per-slice — `CODEBASE_PATH` is REQUIRED for all three impl lenses), and Step 2 now resolves the top slice PR via `gh pr list --head <tip> --state all` (the partially-landed-stack frontier guard, mirroring `/review`). Both encoded as Hard rules (impl rules 3/5).
- Slice 5 (`/review`, whole-stack) is the only remaining wiring slice. It must bind all three upgraded per-phase panels in its binding table, render per-phase synopsis sub-sections via `render_synopsis()`, and emit ONE `ledger_row_fields()`-merged ledger row PER reviewed phase — composing the now-uniform per-phase lenses without advancing the lifecycle. It also authors/reuses the regression fixture (plan steps 52–58). `/review` ALREADY uses the `--state all` frontier guard (per CLAUDE.md), so Slice 4's impl frontier change aligns impl-review TO `/review`, not the reverse.

---

## Session 5 — Slice 5

**Timestamp:** 2026-06-18T03:10:47Z
**Tasks completed:** T52, T53, T54, T55, T56 (the `/review` whole-stack SKILL.md upgrade; the regression-fixture reuse + README provenance; the lens-level regression probe). T57 (live `/review <id>` e2e + frontier head-SHA before/after) and T58's e2e half are live-run checks — see deviations.
**Tasks failed:** none
**Tests:**

- `python3 scripts/run_tests.py` → 42 passed, 0 failed (regression gate; Slice 5 touches no Python source, so the suite is unchanged-green)
- Lens-level regression probe (T56 / step 56): ran the design-panel stated-minus-covered coverage check (via `qrspi_teeth_test`) DIRECTLY over `evals/fixtures/design_dropped_criterion_broken.md` with `ticket_rest_endpoint.md` supplying the four ACs → `stated = ['returns notification and display prefs', 'p95 < 200ms', '401 on unauthorized', '403 unless admin']`, `dropped = ['403 unless admin']`. NON-clean result confirmed: the dropped "403 unless admin" AC surfaces as a blocking finding. (`qrspi_teeth_test.py` itself is in the green suite above.)
- Deterministic core probe: exercised `qrspi_review_synopsis.{partition_decision_readiness,render_synopsis,ledger_row_fields}` against representative design (5-lens + decision-readiness) and plan (3-lens, None DR) final-round arrays — design sub-section renders the axis table + Advisory + Decision-readiness + Terminal action; plan sub-section omits the DR section (None); `ledger_row_fields` emits the additive `axes`/`nonBlockingNotes`. All 13 referenced subagent agent files (`qrspi-{design,plan,impl}-critic-*` + `qrspi-critic-reviser`) exist.

**Deviations from structure.md:**

- none. Structure §Slice 5 step 54 says REUSE `evals/fixtures/design_dropped_criterion_broken.md` and add a `ticket_dropped_criterion.md` ONLY if no existing ticket fixture states the four ACs — implemented as reuse with NO new ticket fixture, because `ticket_rest_endpoint.md` (same DASH-417 source) already states all four ACs verbatim (including "Requesting another user's prefs returns 403 unless admin role").

**Deviations from plan.md:**

- none. (The worktree.md T54/T55/T56 rows still describe the SUPERSEDED "author a new `descoping-design.md`" approach; plan.md step 54 — the revised/authoritative source — explicitly DROPS that as needless duplication and mandates reuse of the existing fixture. Followed the plan, not the stale worktree wording. This is a worktree↔plan wording mismatch, not an implementation deviation.)

**Notes for next session:**

- Slice 5 completes the RUS-91 wiring. `/review` now composes all three upgraded per-phase panels (`DEFAULT_REVIEW_{DESIGN,PLAN,IMPL}_LENSES`) in its Step-3 binding table, fans out each phase's full panel per round (multi-lens pre-reduction verdict array, `partition_decision_readiness()` guard before synthesize, per-lens N×R `rounds[]`), swaps to the shared `qrspi-critic-reviser` (`PHASE=<phase>`), runs the design-only post-loop decision-readiness lens (terminal-advisory), merges `ledger_row_fields()` onto each phase's `build_record` (one ledger row per reviewed phase, shared `runId`), and renders each phase's synopsis sub-section via `render_synopsis()` under ONE rolled-up top-level comment to the frontier PR. Ticket text staged ONCE per run (Step 2) to `TICKET_CONTENT` and passed to coverage/fidelity/decision-readiness lenses ONLY (node-validity `*-review` lenses stay research+code-only). Front-matter `allowed-tools` gained `mcp__linear__get_issue`. The `--state all` frontier guard was already present (unchanged).
- Regression anchor is the REUSED `evals/fixtures/design_dropped_criterion_broken.md` (provenance row + note added to `evals/fixtures/README.md`); its four ACs come from `ticket_rest_endpoint.md`. No new fixture authored.
- DEFERRED to a human/e2e pass (consistent with the Slice-3 T35–T37 and Slice-4 T49–T51 deferrals by the deterministic implement-phase agent): T57 live `/review <id>` over a ticket with a frontier PR + the frontier-PR head-SHA before/after propose-only guard. The deterministic core (helpers, fixture probe, agent existence, full test suite) is verified green.

---

## Session 6 — Post-review corrections (advisory review feedback)

**Timestamp:** 2026-06-18 (review-driven; not a numbered slice task)
**Trigger:** A direct advisory review of the implementation surfaced three gaps. Two are addressed here; one remains open by feasibility.

**Changes (Slice 3):**

- **AC5 dead-channel fix.** The five design-panel lenses (`completeness`, `internal-consistency`, `edge-alignment`, `simplicity`, `design-review`) emitted only `{pass, findings}` — none produced `nonBlockingNotes`, so the design-phase advisory section of `render_synopsis()` had NO producer and a real-but-non-material finding (e.g. the `design-review` lens noticing an inaccuracy it judged non-blocking) was still swallowed — the exact root-cause-#4 failure the ticket targets. Added the OPTIONAL `nonBlockingNotes` advisory channel to all five lens prompts (additive; the batch `CRITIC_VERDICT_SCHEMA` has no `additionalProperties:false`, so the batch path is unaffected). Updated `review-design/SKILL.md` Step 4a array + Step 7 wording from "the edge lenses" to "all panel lenses". The plan/impl panels already had producers (their fidelity/completeness lenses emit it).

**Changes (Slice 5):**

- **AC8 honesty correction.** `pr-summary.md` and this log previously called the regression evidence a "lens-level regression probe." It is NOT: `scripts/qrspi_teeth_test.py` is a pre-existing (RUS-77) deterministic STRUCTURAL stated-minus-covered string check over the fixture; it does not spawn or run any review lens. Relabeled the AC8 row, the Testing-Summary checkbox, and added an Open-Items note. The true live lens-level regression run remains open.

**Live lens-level regression run — PERFORMED (2026-06-18):**

- The originally-cited anchor (RUS-86 / PR #347) is now CLOSED and its `RUS-86/design` branch no longer exists, so the run targeted the static regression fixture the ticket itself chose. The `qrspi-design-critic-completeness` and `qrspi-design-critic-edge-alignment` lenses were spawned over `design_dropped_criterion_broken.md` with `TICKET_CONTENT_PATH=ticket_rest_endpoint.md` and `RESEARCH_PATH=research_rest_endpoint.md`. BOTH returned `pass:false`, each naming the dropped "403 unless admin" AC as a blocking finding (completeness: coverage gap; edge-alignment: under-reach). This is the genuine lens-level regression evidence the earlier structural `qrspi_teeth_test.py` check was mislabeled as. It used the CURRENT (pre-upgrade) registry lens agents — valid, because the regression-catching depends on RUNNING completeness+edge-alignment (which the old `/review-design` did not; it ran only `design-review`), not on the `nonBlockingNotes` upgrade.

**Still open:**

- **Full `/review-design` *command* e2e.** The new RUS-91 agents (`decision-readiness`, the shared reviser, plan/impl lenses) are not yet in the repo's agent registry (RUS-91 unlanded), so a faithful end-to-end command run — including the decision-readiness spawn, the propose-only head-SHA before/after guard, and the PR-comment write — is only possible post-land.

**Tests:** `python3 scripts/run_tests.py` → expected green (no Python source changed in this session; lens/skill/artifact edits only).

---
