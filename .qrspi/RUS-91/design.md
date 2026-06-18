# Design — Bring the /review-* on-demand review family up to manual-review depth

**Ticket:** RUS-91
**Research basis:** research.md @ 2026-06-18T00:30:00Z
**Generated:** 2026-06-18T01:00:00Z
**Status:** draft

## Current State

Each `/review-*` skill is thin orchestration (SKILL.md prose) over three layers: adversarial lens **agents**, pure stdlib **reducer CLIs**, and deterministic **IO scripts** (ref: Discovered Patterns). Every per-phase skill resolves paths, derives the phase PR, makes a scratch copy of the artifact under `/tmp/phase-stage/<id>/review/`, and runs a 0..2 round loop that spawns exactly ONE node-validity lens via the `Agent` tool (ref: Q1). The lens receives named PATH inputs (artifact scratch copy, research, codebase, optional upstream artifacts) but the **ticket text is never supplied** — the design/impl lenses declare an optional `TICKET_CONTENT_PATH` that no skill passes, so node-validity is judged against research + code only, never ticket intent (ref: Q1, Inconsistencies).

The design phase has five lens agents (`completeness`, `edge-alignment`, `internal-consistency`, `simplicity`, and node-validity `design-review`); only `design-review` has codebase Grep access, and the `/review-design` skill spawns only that one (ref: Q3). The plan and implementation phases have exactly ONE lens each — `plan-review` and `impl-review`, both node-validity — and **no fidelity/completeness/consistency/simplicity lens of any kind** (ref: Q4). `qrspi_critics_config.py` knows only DESIGN lenses; there is no plan/impl lens allow-list (ref: Q4).

The reducer CLIs already AND-reduce a multi-lens verdict array: `qrspi_critic_synthesize.py` reduces a JSON array of per-lens verdicts to `{pass, findings}` (pass only if non-empty AND every lens passed; findings are the deduped union), and `qrspi_critic_loop.py` reads the array, treats the last element as authoritative, and emits `converged | cap_reached | revise` (ref: Q2). The five-lens unit test proves adding lenses requires **no synthesize change** (ref: Q2, Q12). Both are fail-closed and `_test.py`-covered; the CI gate is `python3 scripts/run_tests.py` (ref: Q12).

On `revise`, each skill re-spawns the SAME producer that wrote the artifact (`qrspi-design`/`qrspi-plan`/`qrspi-implement`) to rewrite the scratch copy in place, given `residual_findings` (ref: Q8). The producer is invoked by `subagent_type` only — swapping it is a one-line change (ref: Q8). The `/review-design` open-question pass (Step 5) spawns the SAME producer in advisory mode to "answer" the design's own open questions as free text for the synopsis; there is no resolved-vs-blocking classifier and the answers do not feed the verdict (ref: Q9).

The blocking-only severity bar lives in the **lens prompts**, not in any reducer — a finding the lens judges non-blocking is never emitted, so the synopsis reports "converged, pass, zero findings" even when a real-but-non-blocking inaccuracy exists (the `critics_config` slip) (ref: Q10). The synopsis verdict text is hand-composed prose keyed only on the terminal action; neither the comment nor the ledger records which quality axes were checked — a single lens id stands in for all its axes, and the ledger collapses findings to a count (ref: Q10, Q7, Q14). The propose-only invariant rests on a scratch copy, an in-session before/after head-SHA assertion, and a comment-only write; the proof is ephemeral (transcript only) (ref: Q6, Q15). The whole-stack `/review` resolves the frontier via `gh pr list --state all`, loops the per-phase scratch loops, and posts one rolled-up synopsis with per-phase sub-sections — composing the three single lenses and inheriting every gap (ref: Q5). No RUS-86 / PR #347 regression fixture exists anywhere; the eval harness is a non-functional placeholder (ref: Q13).

## Desired End State

Each acceptance criterion maps to concrete behavior:

- **Ticket/AC descoping caught.** The design panel gains the `edge-alignment` (ticket-fidelity) and `completeness` lenses, and these lenses receive `TICKET_CONTENT_PATH` (currently never passed). Plan and impl gain new adversarial, ticket-grounded fidelity + completeness lenses. A lens that sees the ticket can flag the RUS-86 retry-events / shared-log deviation. **Ticket exposure is a made decision, not an open one** (resolves former OQ3, see Decision 6): the ticket text is plumbed to the fidelity/completeness/decision-readiness lenses ONLY; the node-validity lens stays research+code-only, preserving the research-phase firewall on the path where it was deliberate.
- **Deferred blocking decisions surfaced.** The self-grading open-question pass is replaced by a **non-producer decision-readiness lens** that classifies each open question as genuinely-human-to-decide (blocking) vs. answerable, and emits blocking ones as findings rather than laundering them into resolution. **These findings are terminal-advisory: they are reported to the synopsis and do NOT re-spawn the reviser** (a reviser cannot resolve a human product decision — forcing it to "address" one reproduces exactly the laundering the ticket bars). See Decision 5 for the loop-termination contract.
- **Completeness gaps caught.** The `completeness` lens (design) and its new plan/impl counterparts assert every AC + answered question is covered by the artifact.
- **Internal inconsistencies caught.** The `internal-consistency` lens is added to the design panel; plan/impl gain a consistency check in their new lens set.
- **Real non-blocking findings surfaced.** The synopsis reports non-blocking observations in a distinct, advisory section so the blocking-only bar no longer swallows them. (Lenses still gate the verdict on blocking findings; non-blocking notes are reported, not gated.)
- **Honest verdict.** The synopsis enumerates which quality axes (lenses) ran and their per-lens pass state, so it states what was reviewed vs. what remains open instead of a bare "pass / zero findings."
- **Producer-as-reviser replaced.** Every `revise` loop and the open-question pass spawn a **non-producer/adversarial reviser** satisfying the same `OUTPUT_PATH`=scratch-verbatim + propose-only contract (ref: Q8).
- **Regression check.** A RUS-86 / PR #347 design fixture is authored; re-running upgraded `/review-design` over it surfaces the descoping + decision-readiness gaps (no clean pass) (ref: Q13).
- **Propose-only invariant preserved.** Scratch-copy loop, unchanged PR head SHA before/after, comment-only write — unchanged across every edit (ref: Q6, Q15).
- **Whole-stack `/review` upgraded.** It composes the upgraded multi-lens panels per phase and renders the honest per-phase synopsis (ref: Q5).

## Delta

**New lens agents** (under `.claude/agents/`, authored via skill-creator):
- `qrspi-plan-critic-fidelity.md`, `qrspi-plan-critic-completeness.md` — adversarial, ticket-grounded plan lenses.
- `qrspi-impl-critic-fidelity.md`, `qrspi-impl-critic-completeness.md` — adversarial, ticket-grounded impl lenses.
- `qrspi-design-critic-decision-readiness.md` — non-producer lens replacing the self-grading open-question pass.
- `qrspi-critic-reviser.md` — ONE shared, non-producer adversarial reviser, parameterized by phase (design/plan/impl), used by every `revise` loop (resolves OQ2; see Decision 3).

**Modified skills** (`.claude/skills/*/SKILL.md`):
- `review-design`: spawn the full panel (`design-review` + `edge-alignment` + `completeness` + `internal-consistency` + `simplicity` — simplicity INCLUDED, resolving OQ1, to match the batch `DEFAULT_DESIGN_LENSES` so the human review is no thinner than the autonomous critic) instead of one lens; pass `TICKET_CONTENT_PATH`; feed the verdict array to `qrspi_critic_synthesize.py`; replace Step 5 with the decision-readiness lens; widen the synopsis (axis enumeration + non-blocking section).
- `review-plan`, `review-implementation`: spawn their new multi-lens panels; pass ticket; widen synopsis.
- `review`: compose the upgraded per-phase panels in its binding table; honest per-phase synopsis.
- All four: swap the `revise` reviser `subagent_type` to the single shared `qrspi-critic-reviser` (phase passed as input).

**New/modified scripts:** extend `qrspi_critics_config.py` (or add a sibling) with plan/impl lens allow-lists; helper(s) to render the axis-enumerated synopsis and richer ledger fields, each with a `_test.py` sibling. **Axis-enumeration source:** `qrspi_critic_synthesize.py` AND-reduces to a single `{pass, findings}`, discarding per-lens pass state — so the skill MUST retain the *pre-reduction* per-lens verdict array (the input it already pipes to synthesize) and feed THAT to the synopsis helper for per-lens enumeration; the reduced verdict alone is insufficient. This array is also the natural source for the richer per-axis ledger fields, which are added as **optional additive fields on the existing `critic-metrics.jsonl` row** (resolves OQ4) — the reader (`qrspi_critic_summary.summarize`) accesses every field via `.get()` with defaults, so new keys are backward-compatible and old rows still parse; the row's `rounds[]` already carries per-lens `{lens, pass, findingsCount}`, so only non-blocking findings are a genuinely new datum. **Regression fixture (resolves OQ5):** the original RUS-86 / PR #347 `design.md` is treated as unrecoverable, so the regression AC is **re-scoped** to an *independently-authored* descoping fixture (a design that quietly narrows a known AC) under `evals/fixtures/` + a provenance-table row in `evals/fixtures/README.md` (ref: Q13) — NOT a reconstruction of the RUS-86 artifact from the ticket, which would be circular (it would bake in exactly the flaws the lens then "detects"). **Ticket-path plumbing:** the skills must fetch/stage the ticket text to a `TICKET_CONTENT_PATH` for the fidelity/completeness lenses.

## Pattern Decisions

### Decision 1: How to add multi-lens coverage

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Reuse `qrspi_critic_synthesize.py` / `qrspi_critic_loop.py`; skill fans out the panel and pipes the verdict array | Zero reducer change (five-lens test proves it, ref: Q12); matches batch `runCriticPanelLoop` shape (ref: Q3); fail-closed AND-reduction inherited | Skill prose grows; per-phase panel list must live somewhere |
| B | New per-phase orchestration / reducer | Full control of reduction semantics | Reinvents tested machinery; violates ticket "reuse existing machinery" constraint; new untested surface |

**Recommendation:** Option A
**Rationale:** The reducers already AND-reduce M lenses and are locked by the five-lens test (ref: Q2, Q12); the batch design panel already fans out `qrspi-design-critic-${lens}` ids into synthesize (ref: Q3). The single-phase Step 4a / `/review` Step 3b are the documented plug points (ref: Q5).
**NEW PATTERN?** No — extends the existing panel-into-synthesize pattern.

### Decision 2: Where the per-phase lens allow-list lives

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Extend `qrspi_critics_config.py` with `KNOWN_PLAN_LENSES` / `KNOWN_IMPL_LENSES` + defaults | One tested config seam; mirrors `KNOWN_DESIGN_LENSES` (ref: Q3) | Couples on-demand panel to a batch-oriented config file |
| B | Hard-code the panel list in each SKILL.md | Simplest; no script change | Drifts from the design-lens config pattern; not unit-testable |

**Recommendation:** Option A
**Rationale:** `qrspi_critics_config.py` is the established, tested home for `KNOWN_DESIGN_LENSES` and defaults (ref: Q3); plan/impl have no allow-list today (ref: Q4), so adding parallel constants is the minimal consistent extension and gets a `_test.py` sibling per project convention (ref: Q12).
**NEW PATTERN?** No — replicates the existing design-lens config idiom per phase.

### Decision 3: Replacing the producer-as-reviser and self-grading open-question pass

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | New non-producer adversarial reviser agent + decision-readiness lens; swap `subagent_type` in each loop | Breaks circularity (ref: root cause 2/3); one-line `subagent_type` swap (ref: Q8); same scratch/propose-only contract | Two+ new agents to author + trigger-validate |
| B | Keep producer but add a constraint prompt forbidding self-endorsement | No new agents | Same agent type = same blind spots; does not satisfy "replaced with a non-producer/adversarial agent" |

**Recommendation:** Option A
**Rationale:** The reviser is invoked by `subagent_type` only and must satisfy `OUTPUT_PATH`=scratch-verbatim + propose-only (ref: Q8); a non-producer agent satisfies that contract while removing the circularity the ticket names as root causes 2 and 3. Decision-readiness must be a distinct lens because the current pass has no resolved-vs-blocking classifier (ref: Q9). **Reviser shape (resolves OQ2):** ONE shared `qrspi-critic-reviser` agent, parameterized by phase, serves all three loops — NOT a repurposed critic (a judge that also edits would grade toward its own rewrite, a fresh circularity) and NOT one reviser per phase (three agents to trigger-validate for no prompt-divergence benefit).
**NEW PATTERN?** Yes — a non-producer reviser is new. Justified: every existing reviser is the artifact's own producer (ref: Q8), which is exactly the circularity the ticket bars; no existing agent both edits the scratch artifact and is independent of its production.

### Decision 4: Surfacing non-blocking findings without breaking the gate

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Lens emits non-blocking notes in a separate field; synopsis renders them advisory-only; gate still keys on blocking findings | Keeps `pass:false ⟺ blocking findings non-empty` invariant (ref: Q10) intact; reports vs. gates | Lens prompt + synopsis renderer change; reducer must pass notes through untouched |
| B | Lower the blocking bar so non-blocking findings count | Simplest prompt edit | Pollutes the verdict; would never converge; breaks loop/test contracts (ref: Q2, Q12) |

**Recommendation:** Option A
**Rationale:** The blocking-only bar lives in the lens prompt and the reducers apply no severity filter (ref: Q10); a separate non-blocking channel surfaces the swallowed `critics_config`-class finding without breaking the AND-reduction/convergence contract the tests lock (ref: Q12).
**NEW PATTERN?** Yes — a non-blocking advisory channel is new. Justified: today findings are binary/blocking-only (ref: Q10), so there is no existing structure for "real but non-blocking" notes to ride.

### Decision 5: How decision-readiness findings interact with the revise loop

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Decision-readiness findings are **terminal-advisory**: routed straight to the synopsis as "blocking-for-human," they do NOT count toward the reviser's `residual_findings` and never re-spawn the reviser | A reviser cannot resolve a human product decision; excluding it from the loop is the only way to surface the decision without laundering it (ref: root cause 3) — exactly the AC | Two finding classes now flow differently (node-validity/fidelity → revise loop; decision-readiness → synopsis-only); the skill must keep them in separate buckets |
| B | Treat decision-readiness like any other blocking finding (feeds `residual_findings`, drives `revise`) | Uniform loop handling; no new routing | The reviser is asked to "address" an open human decision — it either invents a resolution (the laundering the ticket bars) or churns to `cap_reached` for no gain |

**Recommendation:** Option A
**Rationale:** The loop reducer emits `revise` whenever blocking findings are non-empty (ref: Q2), and the reviser's only move is to rewrite the scratch artifact (ref: Q8). For a genuinely-human decision neither is appropriate — the correct terminal state is "surfaced to the reviewer, unresolved." So decision-readiness findings bypass `qrspi_critic_loop.py`'s revise path entirely and are merged into the synopsis after the node-validity/fidelity panel converges (or caps). The lens still RUNS inside the panel fan-out for parallelism, but its findings are partitioned out of the verdict array fed to `qrspi_critic_synthesize.py` so they cannot trigger a pointless reviser round.
**NEW PATTERN?** Yes — a finding class that reports without gating the loop is new. Justified: today every blocking finding drives `revise` (ref: Q2, Q8); a human-decision finding has no valid reviser action, so it needs a report-only path that did not exist.

### Decision 6: Scope of ticket exposure to the lenses (resolves OQ3)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Expose `TICKET_CONTENT_PATH` to the **fidelity / completeness / decision-readiness** lenses only; leave the node-validity lens research+code-only | Ticket-fidelity is impossible without the ticket; node-validity firewall stays intact where it was deliberate (ref: Q1, Risk Register); bounded, no config surface | A per-lens split in what inputs each agent receives — the skill must pass the path selectively |
| B | Expose the ticket to every lens uniformly | Simplest plumbing | Dissolves the research-phase firewall on the node-validity path for no benefit (node-validity judges against code, not intent) |
| C | Gate ticket exposure behind a config flag | Maximal control | New config + test surface for a decision with one sensible default; over-engineered (ref: ticket "reuse existing machinery") |

**Recommendation:** Option A
**Rationale:** The ticket-fidelity premise of the whole ticket REQUIRES the fidelity/completeness/decision-readiness lenses to see the ticket; the node-validity lens deliberately judges against research+code (ref: Q1), so it keeps the firewall. This is a bounded, made decision — not a deferred one — which is why former OQ3 is removed rather than left open.
**NEW PATTERN?** No — `TICKET_CONTENT_PATH` is an already-declared optional lens input (ref: Q1); this just passes it on the paths that need it.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| New plan/impl lenses written fidelity-only reproduce the rubber-stamp bug | med | high | **Concrete adversarial contract, not just the constraint:** each new lens prompt must (a) require the lens to produce a *specific named descoping/deviation counter-example* (artifact element vs. the ticket AC it narrows) OR affirmatively assert "no AC is narrowed, checked each: <list>" — a bare "looks faithful" is a prompt failure; (b) default to `pass:false` under uncertainty (fail-closed, mirrors the existing lens bar, ref: Q10); (c) be regression-anchored — the plan/impl analogue of the independently-authored descoping fixture (a plan/impl that quietly narrows an AC, per OQ5) must yield a blocking finding before the lens is accepted. Author via skill-creator; validate triggering with `claude -p` routing probes (sandbox run_eval invalid, ref: research/CLAUDE) |
| Ticket text was firewalled from review by design; passing `TICKET_CONTENT_PATH` may conflict with the research-firewall intent | med | med | Scope ticket exposure to fidelity/completeness/decision-readiness lenses only; keep node-validity lens research+code-only as today (ref: Q1) |
| Multi-lens panel changes convergence/round behavior, breaking synthesize/loop tests | low | high | Reuse unchanged reducers (Decision 1); keep all `_test.py` green via `run_tests.py`; add tests for new config/synopsis helpers (ref: Q12) |
| Partially-landed-stack misfire already inconsistent in `/review-implementation` (no `--state all`) could corrupt impl review (ref: Q11, Inconsistencies) | med | med | Align `/review-implementation` frontier resolution with `/review`'s `--state all` guard while touching the skill |
| Non-blocking channel makes synopsis noisy / never-passing if mis-scoped | low | med | Keep gate keyed on blocking findings only (Decision 4); render non-blocking notes as clearly advisory |
| Propose-only invariant regressed by a new reviser writing a tracked path/branch | low | high | New reviser inherits `OUTPUT_PATH`=scratch-verbatim + propose-only contract; head-SHA assertion retained (ref: Q6, Q8, Q15) |

## Open Questions

All open questions are **resolved** (human decisions, 2026-06-18). None remain blocking for the Structure phase.

- ~~OQ1~~ **RESOLVED — include `simplicity`.** The design panel is `design-review` + `edge-alignment` + `completeness` + `internal-consistency` + `simplicity`, matching the batch `DEFAULT_DESIGN_LENSES` so the human review is no thinner than the autonomous critic; Decision 4's non-blocking channel absorbs simplicity's lower-severity output.
- ~~OQ2~~ **RESOLVED — one shared `qrspi-critic-reviser`, phase-parameterized** (see Decision 3 / Delta). Not a repurposed critic (judge+editor = new circularity); not per-phase revisers (no prompt-divergence benefit).
- ~~OQ3~~ **RESOLVED — see Decision 6.** Ticket exposure is scoped to the fidelity/completeness/decision-readiness lenses only; the node-validity lens stays research+code-only. No config gate (rejected as over-engineered).
- ~~OQ4~~ **RESOLVED — additive optional fields on the existing `critic-metrics.jsonl` row** (see Delta). The reader is lenient (`.get()` with defaults), `rounds[]` already carries per-lens state, so only non-blocking findings are new; a separate record was rejected as needless write/correlation surface.
- ~~OQ5~~ **RESOLVED — re-scope the regression AC.** The original RUS-86 / PR #347 `design.md` is unrecoverable, so the regression check uses an *independently-authored* descoping fixture rather than a reconstruction of the RUS-86 artifact (which would be circular). The Structure phase owns authoring the fixture and may pick a representative AC to descope.
