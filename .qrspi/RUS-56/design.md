# Design — qrspi critics 2/5: Stage 1 (Design) multi-lens critic panel + design edge critic

**Ticket:** RUS-56
**Research basis:** research.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Current State

The design phase is driven by `doDesign(t, r)` in `.claude/workflows/qrspi-batch.js`, which calls `runPhase()` for `questions`, `research`, then `design`, then a Finalize agent that commits the three artifacts onto `<id>/design` and submits the PR (ref: Q1). Each `runPhase` call short-circuits if the artifact exists, spawns the phase agent (which writes to the token-free staging path `stg(id,name)`), then calls `persistArtifact`, which is the real success gate (ref: Q1). There is currently **no critic step between produce and persist** — `runPhase` has no `criticConfig` parameter and `runCriticLoop` does not exist in the file (ref: Q1).

Artifact paths come from two pure helpers: `art(wd,id,name)` for the canonical persisted path and `stg(id,name)` for staging (ref: Q2). The design agent receives `QUESTIONS_PATH`/`RESEARCH_PATH` as already-persisted `art(...)` paths and `TICKET_CONTENT_PATH` as a staged file it Reads (ticket text never round-trips through worker stdout); it writes to `stg(id,'design')` (ref: Q2).

The foundation (RUS-55, 1/5) is **only partially landed in this worktree**: the pure decision module `scripts/qrspi_critic_loop.py`, its test, the `qrspi-critic` agent, and the `qrspi-critic` skill exist, but the JS glue (`runCriticLoop`, the `criticConfig` parameter on `runPhase`, and the `CRITIC_VERDICT_SCHEMA` constant) is **absent from `qrspi-batch.js`** — grep returns zero hits (ref: Q1, Q3, Q4). The pure module is **single-critic, single-verdict**: `next_action(verdicts, round, max_rounds)` consumes an already-parsed verdict list (last element authoritative) and returns `converged`/`revise`/`cap_reached`; it does not run lenses, spawn agents, or parallelize (ref: Q3). RUS-55 OQ2 explicitly pinned the primitive to one critic per round with **no cross-critic aggregation**, deferring multi-critic fan-out to the per-phase tickets (ref: Q3, Q10). The verdict schema is `{pass: bool, findings: list}`; the only landed validation is the fail-closed Python backstop `parse_critic_verdict`/`_coerce_verdict`, which never raises and coerces garbage to NOT-passed (ref: Q4, Q11).

`maxRounds` is intended to be per-phase via `criticConfig.maxRounds ?? 2` with no module-level constant and no config-file key — but no `criticConfig` exists and `.qrspi/config.example.json` carries no critic keys (ref: Q5). There is **no synthesis/merge/dedupe module**; `synthes*`/`dedup*`/`precedence` return no hits (ref: Q6, Q10). The critic loop is meant to run entirely within the produce→persist window, so `design.md` persists **once** at the end; each round rewrites `stg(id,'design')` in place and the next round re-reads it from disk (ref: Q7). Cap-reached returns **success** so a non-converging critic never blocks submission (ref: Q9, Q11).

Design/plan PRs currently have **subject-only** commit bodies: the finalize worker runs `gt modify -c` with subject `"${t.id} [QR]: Design — ${t.title}"` then `gt submit --publish` (ref: Q9). `scripts/qrspi_pr_body.py` exists but is implementation-slice-only; its `compose_message(existing, body)` splices a body between subject and trailers — there is no design/plan equivalent, and the planned `qrspi_critic_body.py` is NOT FOUND (ref: Q9). The eval harness (`eval_all.py` → `run_eval.py` + `grade.py` over design cases `case_005/006/014`, with RUS-37 graders like `no_code_blocks`/`has_section`/the `NEW PATTERN?` marker) is a documented non-functional placeholder scoring ~0 uniformly; a real before/after score requires injecting a live `model` into `evals/suite.json` `defaults` (ref: Q13). The established test idiom is pure-logic-in-Python with a stdlib `_test.py` sibling fed literal `{pass, findings}` dict fixtures; `agent()`/JS glue is not unit-tested, only manually e2e-verified (ref: Q12). Observability is `log(...)` lines plus a fold into `res.summary`, with the PR body as the durable audit surface for residual findings (ref: Q14).

## Desired End State

This ticket maps to five acceptance criteria:

1. **Design phase runs the M-lens panel → synthesize → revise ≤ maxRounds before submit.** `doDesign` passes a `criticConfig` carrying the M lens definitions and `maxRounds` (default 2) into the design `runPhase`. Both `maxRounds` and the lens set are config-file-overridable per run via an optional `critics.design` block in `.qrspi/config.json`, with the JS literal supplying defaults when the key is absent (resolved per OQ3). A new `runCriticPanelLoop` runs the M lenses in parallel per round, synthesizes their verdicts into one authoritative `{pass, findings}`, delegates the converge/revise/cap decision to the existing `next_action`, and on `revise` re-spawns the design agent with the synthesized findings — all inside the produce→persist window, before the single `persistArtifact` call.

2. **Each lens receives upstream (ticket/research/questions) + `design.md`; findings schema-validated.** Each lens agent is handed `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH` (the `art(...)` persisted paths) plus the staged `stg(id,'design')` as its rubric, and emits `{pass, findings}` validated by `parse_critic_verdict`.

3. **Panel-pass on round 1 ⇒ no revise.** When the synthesized round-0 verdict is `pass:true`, `next_action` returns `converged` and the loop breaks before any revise agent spawns.

4. **Unresolved findings after the cap are surfaced into the design PR body.** On `cap_reached`, residual findings are written to a token-free staged file and spliced into the design finalize commit message (the only non-interactive PR-body lever), then the phase proceeds to submit normally.

5. **Measured: design-phase eval score (post-RUS-37 checks) reported before/after.** The design cases are run through `eval_all.py`/`run_eval.py` + `grade.py` with a live model before and after the panel lands, and the delta is recorded.

When `criticConfig` is absent, `runPhase` behaves byte-for-byte as today (opt-in seam).

## Delta

**New files:**
- `scripts/qrspi_critic_synthesize.py` — pure function `synthesize(verdicts) -> {pass, findings}` that reduces M lens verdicts to one authoritative verdict: `pass` only if every lens passed; `findings` is the union of all lens findings, deduped (exact-string), with each finding optionally lens-tagged for audit.
- `scripts/qrspi_critic_synthesize_test.py` — stdlib `check()`-style sibling with literal `{pass, findings}` list fixtures covering all-pass, one-fail, duplicate-across-lenses, and empty/malformed-lens cases.
- `scripts/qrspi_critic_body.py` + `_test.py` — design/plan-phase body splicer reusing `compose_message`, turning residual findings into a commit-message body block (Q9 Path A helper).
- `.claude/agents/qrspi-design-critic.md` (or M lens prompts) — the four lenses: completeness, internal consistency, ticket/research alignment (edge), simplicity.

**Modified files:**
- `.claude/workflows/qrspi-batch.js` — (a) add `CRITIC_VERDICT_SCHEMA`; (b) add `runCriticPanelLoop(name, id, criticConfig, ...ctx)` that parallel-spawns lenses, calls `synthesize`, then `next_action`, re-spawning the design agent on `revise`; (c) extend `runPhase` with an optional trailing `criticConfig` guarded by `if (criticConfig)` (absent ⇒ unchanged); (d) have `doDesign` read the optional `critics.design` config block and pass `criticConfig {lenses:[...], maxRounds:2, upstream:'research'}` with config values overriding the JS defaults (config > default); (e) splice cap-reached residual findings into the design finalize commit via `qrspi_critic_body.py`; (f) add `log(...)` lines + a `res.summary` fold for per-round pass/fail/cap (ref: Q14).
- `.qrspi/config.example.json` — add an optional `critics.design` block (`{"maxRounds": 2, "lenses": [...]}`) documenting the per-run override surface; `.qrspi/config.json` (gitignored) is where a user sets it. `doDesign` reads it (via the existing config-loading path) and folds it into `criticConfig`, JS literal supplying defaults when absent (resolved per OQ3).

**No new DB/queries** — this is workflow-orchestration glue plus pure Python helpers.

Because the RUS-55 Slice 3 JS glue is unlanded (ref: Q1, Q3), this ticket must **introduce the orchestration seam itself** (the panel variant), not merely extend an existing `runCriticLoop`.

## Pattern Decisions

### Decision 1: Where the multi-lens reduction lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Pure Python `synthesize(verdicts)` reducing M verdicts to one, then existing `next_action` | Reuses the tested single-verdict module unchanged; reduction is unit-testable with dict fixtures (ref: Q12); fits the pure-decision-in-Python firewall (ref: Q12) | One more module + JS plumbing to collect M replies |
| B | Teach `next_action` to accept M lens verdicts and reduce internally | Single module | Breaks the module's "one authoritative verdict per round" contract (ref: Q10); rewrites tested code; conflates synthesis with loop control |

**Recommendation:** Option A
**Rationale:** The module's contract is one authoritative verdict per round and the last element wins (ref: Q3, Q10). A separate pure `synthesize` keeps that contract intact, reuses the dominant `check()`-style test pattern (ref: Q12), and isolates merge/dedupe logic for testing.
**NEW PATTERN?** Yes — multi-lens synthesis (merge/dedupe/precedence) does not exist anywhere; the foundation is explicitly single-critic (ref: Q10). Justified because design is the only phase warranting a panel (ticket cardinality rationale) and the foundation deferred fan-out to per-phase tickets.

### Decision 2: How M lenses run per round

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `parallel()` fan-out of M lens `agent()` thunks, collect verdicts, synthesize | Concurrency; `parallel()` is already in the runner vocabulary (ref: Q10); matches "run in parallel" in the ticket | New panel loop (`runCriticPanelLoop`) since the foundation's single-critic loop is unbuilt anyway (ref: Q3) |
| B | Sequential lens spawns in a JS loop | Simplest control flow | Slower; ignores the ticket's explicit "in parallel" requirement |

**Recommendation:** Option A
**Rationale:** The ticket requires parallel lenses; `parallel()` exists as a runner primitive (ref: Q10). Since RUS-55's single-critic `runCriticLoop` is not landed (ref: Q3), this ticket builds `runCriticPanelLoop` fresh rather than retrofitting a sequential loop.
**NEW PATTERN?** Yes — `parallel()` was explicitly NOT used for critics in the foundation (ref: Q10). Justified by the ticket's parallel-panel requirement at the one phase where redundancy cost is warranted.

### Decision 3: Lens failure / schema-invalid handling

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Each lens verdict passed through `parse_critic_verdict`; an errored/garbled lens coerces to `{pass:false, findings:[]}`; panel never aborts, never blocks | Reuses the landed fail-closed backstop (ref: Q11); a bad lens biases toward another round/cap, never falsely converges; cap-reached still submits (ref: Q9, Q11) | A silently-failing lens contributes no findings (mitigated by logging, ref: Q14) |
| B | Abort the panel / block submission on any lens error | Loud | Contradicts the fail-closed, never-block contract (ref: Q11); a flaky lens would stall the whole pipeline |

**Recommendation:** Option A
**Rationale:** The landed contract is fail-closed and non-blocking — a missing verdict can never report converged, and cap-reached is success not failure (ref: Q11). Reusing `parse_critic_verdict` per lens preserves that property at the panel level.
**NEW PATTERN?** No — extends the existing fail-closed verdict-parsing pattern (ref: Q11) to M lenses.

### Decision 4: Surfacing residual findings into the PR body

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Write residual findings to a staged file; splice into the design finalize commit message via a new `qrspi_critic_body.py` reusing `compose_message` | Mirrors the only working non-interactive body lever (ref: Q9); avoids shell-quoting breakage; testable | New helper (the planned one is NOT FOUND, ref: Q9) |
| B | Inline findings into the heredoc commit subject | No new file | Rejected by RUS-55 Decision 4 — multi-line in a subject breaks shell quoting (ref: Q9) |

**Recommendation:** Option A
**Rationale:** `gt submit` has no `--body` flag; the commit message is the only lever, and `compose_message` already splices a body between subject and trailers for slices (ref: Q9). A design-phase sibling reuses that exact mechanism.
**NEW PATTERN?** No — reuses the `compose_message` body-splice pattern (ref: Q9), applied to the design phase.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Foundation 1/5 JS glue (`runCriticLoop`, `criticConfig`, `CRITIC_VERDICT_SCHEMA`) is unlanded in this worktree (ref: Q1, Q3, Q4) | high | high | This ticket must build the orchestration seam (panel variant) itself, not extend a missing function; account for it in the structure phase as first-class scope, not a dependency assumed present |
| A reviser writing an empty `stg(id,'design')` flips persist to `ok:false` and stops the ticket (ref: Q1, Q7) | med | high | Reviser prompt must rewrite the staged file in place and never empty it; the single persist runs only after the loop, preserving the non-empty gate |
| Eval before/after score cannot be produced — harness is a ~0 placeholder (ref: Q13) | high | med | Acceptance criterion 5 requires injecting a live `model` into `evals/suite.json` `defaults` and an API key; treat the measured delta as a manual, model-backed run, not a CI gate |
| Panel adds M agent spawns per round, raising cost/latency (ref: Q3, ticket cardinality rationale) | med | med | Confine the panel to the design phase only (per ticket scope); cap at `maxRounds` default 2; pass-break on round 1 short-circuits revise (ref: Q8) |
| A silently fail-closed lens contributes no findings, weakening coverage without signaling (ref: Q11, Q14) | med | low | Log per-lens pass/fail and parse outcomes via `log(...)`; fold a summary into `res.summary` so a degraded panel is visible in run output |

## Open Questions

- OQ1 (RESOLVED — reviewer: "all four"): All four lenses ship in this ticket: completeness, internal consistency, ticket/research alignment (edge), and simplicity. No subset; the panel fans out four parallel lens spawns per round, capped at `maxRounds` (default 2) with pass-break on round 1 to bound the cost (ref: Decision 2, Risk Register row 4).
- OQ2 (RESOLVED — reviewer: "all-pass-required-for-pass plus finding-union"): Synthesis precedence is **all-pass-required-for-pass plus finding-union** — no lens carries veto or priority weight. `synthesize(verdicts)` sets `pass:true` **only if every lens passed**, and `findings` is the **union of all lens findings**, deduped (exact-string), each optionally lens-tagged for audit. No edge/alignment lens (nor any other) is privileged; a single failing lens fails the round and contributes its findings like any other. This is exactly the rule already specified in the Delta (`scripts/qrspi_critic_synthesize.py`) and Decision 1, so the resolution confirms the existing design with no structural change — only the open question is now settled. The foundation's round-to-round latest-wins (ref: Q10) is unaffected: synthesis produces one authoritative verdict per round, and `next_action` still treats the last round's synthesized verdict as authoritative.
- OQ3 (RESOLVED — reviewer: "mac rounds and lens set should be configurable"): Both `maxRounds` **and** the lens set are config-file-overridable. `.qrspi/config.json` (gitignored; example in `.qrspi/config.example.json`) gains an optional `critics.design` block — e.g. `{"maxRounds": 2, "lenses": ["completeness","internal-consistency","edge-alignment","simplicity"]}`. `doDesign` reads it (via the existing config-loading path the resolver/reviewer flags already use) and folds it into the `criticConfig` it passes to `runPhase`, with the JS literal supplying defaults when the key is absent (precedence: config value > JS default `maxRounds:2` / the four-lens default set). This extends RUS-55's JS-literal default (ref: Q5) rather than replacing it: absent config ⇒ today's behavior, present config ⇒ per-run override. Unknown lens names are ignored with a `log(...)` warning (fail-soft, consistent with the fail-closed lens contract in Decision 3); an empty resolved lens set falls back to the default four so the panel never runs zero lenses.
- OQ4 (RESOLVED — reviewer: "documenting the procedure"): Acceptance criterion 5 is satisfied by **documenting the procedure**, not by an in-scope API-key-backed model run. The harness is a non-functional ~0 placeholder without a live model (ref: Q13), so this ticket does **not** carry an API-key-backed before/after eval run as a deliverable. Instead, criterion 5 is met by documenting the repeatable procedure to produce the score: inject a live `model` into `evals/suite.json` `defaults` (with an API key supplied out-of-band), then run the design cases `case_005/006/014` through `eval_all.py` → `run_eval.py` + `grade.py` (RUS-37 graders: `no_code_blocks`, `has_section`, the `NEW PATTERN?` marker) **before** and **after** the panel lands and record the delta. The procedure (not a CI-gated number) is the deliverable; an actual model-backed run remains an optional manual exercise outside this ticket's scope. This keeps the measurement honest — no fabricated score from a placeholder harness — and is consistent with the documented convention that the eval harness is verified manually, not as a CI gate.
