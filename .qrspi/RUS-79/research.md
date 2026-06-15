# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-15T00:00:00Z
**Generated:** 2026-06-15T00:00:00Z
**Status:** draft

## Q1: What does a critic verdict object contain end-to-end (pass/fail flag, findings, lens identity, dissent signal), and how does it flow from a single critic agent invocation back through the orchestration into a panel-level decision?

**Answer:** The atomic critic verdict is `{ pass: bool, findings: string[] }`, validated at the runner boundary as `CRITIC_VERDICT_SCHEMA`. There is no explicit "dissent signal" field and no lens identity *inside* the verdict — the lens identity is attached by the orchestrator at the call site (`{ lens, verdict }`), not emitted by the critic. Flow:

1. A single edge critic (`runCriticLoop`) spawns one `qrspi-critic` agent per round with `CRITIC_VERDICT_SCHEMA`; the verdict is wrapped as a one-element list and passed to `criticDecision([verdict], round, maxRounds)` → `next_action`.
2. The design panel (`runCriticPanelLoop`) fans out M lens agents in `parallel()`, tags each reply with its lens id (`{ lens, verdict }`), builds `lensVerdicts = [{pass, findings, lens}]`, reduces them to ONE `{pass, findings}` round verdict via `synthesizeVerdicts` (the `qrspi_critic_synthesize.py` worker), then passes that single synthesized verdict to the SAME `criticDecision`/`next_action`.

The dissent signal is *derived downstream* from the recorded per-round verdicts (pass=false OR findingsCount>0), not carried on the verdict object — see Q2/Q12.

**Evidence:**

```js
const CRITIC_VERDICT_SCHEMA = {
  type: 'object',
  required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
  },
}
```

— `.claude/workflows/qrspi-batch.js:495-502`

```js
const lensVerdicts = replies.map(rp => ({
  pass: rp.verdict.pass === true,
  findings: Array.isArray(rp.verdict.findings) ? rp.verdict.findings : [],
  lens: rp.lens,
}))
const synth = await synthesizeVerdicts(lensVerdicts)
const decision = await criticDecision([{ pass: passed, findings: synthFindings }], round, maxRounds)
```

— `.claude/workflows/qrspi-batch.js:911-935`

**Dependencies:** `.claude/agents/qrspi-critic.md` (verdict producer) → `runCriticLoop`/`runCriticPanelLoop` (collectors) → `qrspi_critic_synthesize.py` (panel reduction) → `qrspi_critic_loop.py::next_action` (decision). Verdict schema mirrored in `qrspi_critic_loop.py` canonical `{pass, findings}`.
**Implicit contracts:** `pass:true` ⇒ findings SHOULD be empty; `pass:false` ⇒ findings MUST be non-empty (per `qrspi-critic.md:42`, enforced only by the prompt, not the schema). Lens identity is an orchestration-layer wrapper, never part of the agent's emitted verdict. A `null` agent reply (spawn failure) is NOT a verdict — it aborts the step.

## Q2: How does the RUS-78 instrumentation record the dissent base rate — what fields are captured per verdict, where are they written, and in what format — so this ticket can reuse that path to measure a before/after delta?

**Answer:** Instrumentation is a two-stage pipeline. (1) **Capture+reduce:** every loop round pushes `{lens, pass, findings}` into a `metricRounds[]` accumulator; on ANY termination, `recordCriticMetrics(id, phase, metricRounds, terminalAction)` runs `qrspi_critic_metrics.py::build_record`, which reduces each round to a `CriticRoundRecord {lens, pass: bool, findingsCount: int}` and wraps them as a `CriticStepMetrics {phase, rounds[], terminalAction, tokensIn?, tokensOut?}`. (2) **Durable sink:** `qrspi_metrics_append.py` wraps that record in a `CriticMetricsLedgerLine` envelope (injecting `ticketId`, `timestamp` UTC ISO-8601, and `runId`) and appends ONE JSON line to `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`.

The dissent base rate itself is NOT stored — it is *computed on read* by `qrspi_critic_summary.py::summarize`, where a round counts as **dissent** if `pass is False OR findingsCount > 0`. `dissentRate = dissent_rounds / total_rounds`. RUS-78 added the `runId` field so a before/after delta can be scoped to exactly one run (`--run-id`). Note: token cost fields ship UNMEASURED (the harness exposes no per-subagent usage; `usage` is never supplied — `qrspi_critic_metrics.py:38-45`).

**Evidence:**

```python
is_pass_false = rnd.get("pass") is False
is_dissent = is_pass_false or (rnd.get("findingsCount", 0) or 0) > 0
...
dissent_rate = (dissent_rounds / total_rounds) if total_rounds else 0.0
```

— `scripts/qrspi_critic_summary.py:145-164`

```python
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record)
    line["ticketId"] = ticket
    line["timestamp"] = timestamp
    line["runId"] = run_id
    return line
```

— `scripts/qrspi_metrics_append.py:67-79`

**Dependencies:** `runCriticLoop`/`runCriticPanelLoop` (capture) → `qrspi_critic_metrics.py` (reduce) → `qrspi_metrics_append.py` (append) → `qrspi_critic_summary.py` (read-side base-rate report). `runId` defined once in `qrspi-batch.js:116-119`.
**Implicit contracts:** The ledger is append-only JSONL, one line per *terminated* critic step (including aborts, so base rates aren't biased toward successes — `qrspi_critic_metrics.py:30-31`). `terminalAction` is validated against `{converged, cap_reached, exhausted, aborted}`; `revise` is rejected (non-terminal). A `null` lens (single edge critic) rolls under the literal key `"edge"` in per-lens summaries. The before/after delta procedure RUS-79 would reuse is: run with critic prompts vN, summarize `--run-id`; change prompts; run vN+1; compare `dissentRate`.

## Q3: What is the exact set of critic agent prompt files in scope, and what shared structure or section ordering do they have in common?

**Answer:** The critic prompt files under `.claude/agents/` are:
- `qrspi-critic.md` — the single edge critic (questions/research/structure/plan phases).
- `qrspi-design-critic-completeness.md`, `qrspi-design-critic-internal-consistency.md`, `qrspi-design-critic-edge-alignment.md`, `qrspi-design-critic-simplicity.md` — the four design-panel lenses (agentType `qrspi-design-critic-<id>`).
- `qrspi-coherence-critic.md` — the whole-stack implementation-seam coherence critic.

(Adjacent but distinct: `qrspi-design-judge.md` and `qrspi-design-graft.md` are the N-select judge/graft agents, NOT pass/fail critics — they use `DESIGN_JUDGE_SCHEMA`, not `CRITIC_VERDICT_SCHEMA`.)

All six pass/fail critics share an identical section skeleton, in this order: YAML frontmatter (`name`, `description`, `claude: tools: Read`) → role sentence ("You are the X lens/critic …") → `## Inputs (provided in your spawn prompt)` → `## What to do` (numbered) → `## The <lens> lens (what you are judging)` (or "What you are judging") → `## Verdict schema` (the `{pass, findings}` contract, "When pass is true findings SHOULD be empty; when false MUST be non-empty") → `## Rules` (7 numbered for lenses, ending with the "fail closed on doubt" and "no Linear/MCP" and "no approval prompts" rules).

**Evidence:**

```
8: You are the COMPLETENESS lens of the QRSPI design-phase critic panel...
25: ## The completeness lens (what you are judging)
33: ## Verdict schema
42: ## Rules
...
3. Fail closed on doubt: if you cannot confirm ... that is a finding — do not pass it on benefit of the doubt.
```

— `.claude/agents/qrspi-design-critic-completeness.md:8-46`

**Dependencies:** All read-only (`tools: Read`). Each lens id is bound to its agentType in `DEFAULT_DESIGN_LENSES` (`qrspi-batch.js:610`) and consumed by `runCriticPanelLoop` (`agentType = qrspi-design-critic-${lens}`). The edge critic is the agentType `qrspi-critic` (`qrspi-batch.js:746`).
**Implicit contracts:** Every lens prompt carries the line "**Fail closed on doubt** … that is a finding — do not pass it on benefit of the doubt" — this is the existing anti-pass-bias lever already present in prose. Every lens prompt explicitly scopes itself to ONE lens and says "do not duplicate the other lenses' jobs". The `DIGEST_PATH` optional input (read in place of `RESEARCH_PATH`) is present in all four design lenses (RUS-77).

## Q4: What threshold knobs exist in the `critics` config block, what keys and value ranges do they accept, and how are they read and applied at runtime?

**Answer:** The `critics` block is resolved by `scripts/qrspi_critics_config.py::resolve_critics` (the single tested source of truth) into a per-phase envelope. Keys:
- `enabled` (bool, default **OFF** for every phase) — only an explicit boolean flips it; any non-boolean falls back to default.
- `maxRounds` (positive int, default `2`) — caps the produce→critique→revise loop; non-positive/non-int/bool → 2. **This is the per-phase critic revise cap** (Q8).
- Design-only: `lenses` (list, default the four; unknown names dropped+warned; all-unknown → default four), `candidates` (numeric N-select, default `1`=OFF, clamped to `[2, 3]`), `digest: {enabled}` (default OFF, RUS-77 cost lever), `lensModel` (string, default ABSENT/omitted), `gateBehindEdge: {enabled}` (default OFF).
- Implementation-only: nested `coherence: {enabled, maxRounds}` (both default OFF/2).

There is **NO numeric pass-threshold / quorum knob** — the panel is strict unanimity (Q5), not a configurable threshold. At runtime, `parseCriticsEnvelope` in `qrspi-batch.js` reads the envelope once (the "single read discipline") with `DEFAULT_CRITIC_PHASES` as the JS-side fallback mirror.

**Evidence:**

```python
def _pos_int_or(value, default):
    if isinstance(value, bool):
        return default
    if isinstance(value, int) and value > 0:
        return value
    return default
```

— `scripts/qrspi_critics_config.py:75-84`

```python
"design": resolve_design(c.get("design"), warnings),
... "maxRounds": _pos_int_or(cfg.get("maxRounds"), DEFAULT_MAX_ROUNDS),
```

— `scripts/qrspi_critics_config.py:135, 224`

**Dependencies:** `qrspi_config.py::read_config` (self-locating reader) → `qrspi_critics_config.py::resolve_critics` → `qrspi-batch.js` `DEFAULT_CRITIC_PHASES` (line 625-635, kept in lockstep). Tested by `scripts/qrspi_critics_config_test.py`.
**Implicit contracts:** `DEFAULT_CRITIC_PHASES` in JS MUST stay byte-identical to the Python resolver defaults (verified in `qrspi_critics_config_test.py`). `lensModel` key is OMITTED (not null) when unset so the default shape is byte-identical to pre-RUS-77. The config reader handles a single top-level key only (no dot-path) — a RUS-79 prompt-only change needs no new config knob if it stays in the prompt files.

## Q5: How is a panel-level pass/fail decision computed from individual lens verdicts — is it a majority, unanimity, or threshold rule — and where is that aggregation logic implemented?

**Answer:** **Strict unanimity.** `qrspi_critic_synthesize.py::synthesize` reduces M lens verdicts to one `{pass, findings}`: `pass` is True ONLY if the verdict list is non-empty AND **every** coerced lens passed (any single lens fail ⇒ the round fails). `findings` is the exact-string-deduped union of all lens findings (first-seen order), optionally lens-tagged as `{text, lens}`. There is no majority/quorum — one dissenting lens fails the round. The synthesized verdict then feeds `next_action` (`qrspi_critic_loop.py`) which decides converged/revise/cap_reached. (Distinct: the *teeth eval* uses a per-lens majority threshold — Q9 — but that is the eval's catch-rule, not the production panel aggregation.)

**Evidence:**

```python
all_passed = True
for entry in verdicts:
    coerced = _coerce_lens(entry)
    if not coerced["pass"]:
        all_passed = False
    ...
return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:97-118`

**Dependencies:** `qrspi_critic_synthesize.py` reuses `_coerce_verdict`/`parse_critic_verdict` from `qrspi_critic_loop.py` (fail-closed coercion). Invoked by `runCriticPanelLoop` via the `synthesizeVerdicts` worker (`qrspi-batch.js:984-998`). Tested by `qrspi_critic_synthesize_test.py`.
**Implicit contracts:** An EMPTY verdict list reads as NOT-passed (no lens attested ⇒ fail closed). A malformed lens reply coerces to NOT-passed with no findings — so a garbled lens cannot silently pass the round, but also contributes no finding text. Because aggregation is unanimity, *lowering* any single lens's pass bar (e.g. RUS-79 anti-pass-bias) directly raises the panel fail rate; the aggregation itself needs no change.

## Q6: How does the shared-digest / lens-model / gating cost-reduction shape from RUS-78 currently structure what each lens receives as input, so a prompt-only change can avoid disturbing it?

**Answer:** Each lens receives four input PATHS in its spawn prompt: `DESIGN_PATH` (staged design), `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`. The RUS-77 cost levers add a conditional fifth line:
- **digest** (primary lever): when `criticConfig.digest.enabled`, `buildResearchDigest` produces `/tmp/phase-stage/<id>/research-digest.md` ONCE before the round loop, and a `DIGEST_PATH = ...` line is appended to each lens prompt; the lens prompt instructs "Read DIGEST_PATH in place of RESEARCH_PATH". Default OFF ⇒ `digestPath` stays null ⇒ no `DIGEST_PATH` line ⇒ lenses read full `RESEARCH_PATH` (byte-for-byte prior behavior).
- **lensModel** (speculative): when set, rides as the `agent()` `model` option per lens; default absent. Documented as possibly inert (no evidence the harness honors it).
- **gateBehindEdge**: skips the whole panel if an upstream edge passed; default OFF, and a no-op in the design call graph (design routes to panel OR edge, not a sequence — `qrspi-batch.js:1475`).

A prompt-only RUS-79 change edits the `.claude/agents/qrspi-*critic*.md` files; the input-threading (the four/five `*_PATH =` lines built in `runCriticPanelLoop`) is orthogonal and need not change, as long as the prompts keep honoring the `DIGEST_PATH`-in-place-of-`RESEARCH_PATH` contract.

**Evidence:**

```js
const digestLine = digestPath ? `\nDIGEST_PATH = ${digestPath}` : ''
...
`DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}${digestLine}
Read all four paths and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`
```

— `.claude/workflows/qrspi-batch.js:877, 883-887`

**Dependencies:** `buildResearchDigest` → `qrspi_research_digest.py` (trims fenced evidence; guarded with `test -s`, fail-closed). Lens prompts consume `DIGEST_PATH` (`qrspi-design-critic-*.md` Inputs section).
**Implicit contracts:** The digest is built ONCE per step and reused across revise rounds (only the staged design changes). Every lens prompt MUST keep the "Read DIGEST_PATH in place of RESEARCH_PATH when present" instruction (`qrspi-design-critic-completeness.md:15, 48`), or a digest-ON run silently reads the wrong file. A prompt-only change that adds adversarial framing should preserve the input-path enumeration verbatim.

## Q7: How does the critic loop currently behave when a critic returns an ambiguous or malformed verdict, and is there a defined default — and does that default currently lean pass or fail?

**Answer:** It **fails closed (leans FAIL/not-passed)**. Two layers: (1) the runner schema (`CRITIC_VERDICT_SCHEMA`) validates the agent reply; a `null` agent reply (spawn failure) is treated as an abort (`ok:false`, `recordCriticMetrics(... 'aborted')`), NOT a pass. (2) The pure parser `qrspi_critic_loop.py::parse_critic_verdict` / `_coerce_verdict` is a defensive backstop: any non-dict, missing/garbled fields, empty/non-JSON, or unreadable input coerces to `{"pass": False, "findings": []}` and NEVER raises. `next_action` reads the latest verdict through `_coerce_verdict`, so a missing/garbled verdict can never report "converged". The same fail-closed coercion governs each panel lens (`_coerce_lens`) and the teeth catch-rule (`_is_catch`).

**Evidence:**

```python
def _coerce_verdict(obj):
    if not isinstance(obj, dict):
        return {"pass": False, "findings": []}
    passed = bool(obj.get("pass", False))
    ...
```

— `scripts/qrspi_critic_loop.py:36-48`

```python
if not isinstance(text, str) or not text.strip():
    return {"pass": False, "findings": []}
```

— `scripts/qrspi_critic_loop.py:62-63`

**Dependencies:** `parse_critic_verdict`/`_coerce_verdict` (`qrspi_critic_loop.py`) reused by `synthesize` (`qrspi_critic_synthesize.py:39-42`) and the loop decision. JS callers treat `null` agent replies as abort (`qrspi-batch.js:748-752, 896-908`).
**Implicit contracts:** Fail-closed is the established convention — "a garbled critic reply can never silently mark an artifact converged". The CONTRACT comment notes the primary path is runner StructuredOutput schema validation; the parser is the residual weak-model-stall backstop. NOTE for RUS-79: a malformed verdict already counts as fail, but it contributes **no finding text** — an "ambiguous ⇒ fail" framing would not surface *why* it failed unless the prompt forces a finding.

## Q8: What stops an adversarial "default to fail if uncertain" framing from producing a non-terminating revise loop — what bounds the number of critic-driven revise cycles per phase, and where is that bound enforced?

**Answer:** The per-phase critic loop is hard-bounded by **`maxRounds`** (default `2`), enforced in `next_action` (`qrspi_critic_loop.py`) and the `for (let round = 0; round < maxRounds; round++)` loops in both `runCriticLoop` and `runCriticPanelLoop`. When the latest verdict does not pass AND `round + 1 >= max_rounds`, `next_action` returns `"cap_reached"` (NOT another revise) and the loop finalizes the artifact anyway, surfacing residual findings into the PR body. So an always-fail critic costs at most `maxRounds` rounds, then the phase advances with findings noted — it cannot loop forever. (Defensive belt-and-suspenders: the loop also has an `exhausted` tail returning `ok:true` if it ever falls out without an explicit decision.)

This is DISTINCT from the unrelated CI-revise cap (`ciReviseCap`, default 3) in `qrspi_resolve_state.py` (`resolve(state, ci_revise_cap=3)`), which bounds *PR-CI-driven* revises across batch invocations — not the in-phase critic loop.

**Evidence:**

```python
if latest["pass"]:
    return {"action": "converged", "residual_findings": []}
if int(round) + 1 >= int(max_rounds):
    return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:107-113`

```js
if (decision.action === 'cap_reached') {
  ... return { ok: true, residualFindings: decision.residual_findings, metrics }
}
```

— `.claude/workflows/qrspi-batch.js:772-775` (single) / `:946-949` (panel)

**Dependencies:** `next_action` is the single decision authority; `runCriticLoop`/`runCriticPanelLoop` consume it via `criticDecision`. `maxRounds` resolved per-phase by `qrspi_critics_config.py`. CI cap is separate (`qrspi_resolve_state.py:173, 129-134`).
**Implicit contracts:** `cap_reached` is a TERMINAL success (`ok:true`) — the artifact is still finalized; the loop guarantees termination regardless of critic verdicts. Residual findings on cap are spliced into the PR body (`criticConfig.residualFindings` → `qrspi_critic_body.py`). RUS-79's anti-pass-bias is therefore safe by construction: a stricter critic increases revise rounds up to `maxRounds` then stops, raising dissent rate without risking non-termination.

## Q9: How does the teeth eval define which lens "owns" which deliberately-flawed defect, and what majority threshold must each owning lens hit to pass?

**Answer:** Ownership is a literal map `LENS_MARKERS` in the teeth-eval workflow, binding three lenses to three unique quotable marker strings embedded in the flawed `evals/teeth/design.md`:
- `completeness` → `AC-TEETH-COMPLETENESS`
- `internal-consistency` → `TEETH-INCONSISTENCY`
- `edge-alignment` → `frobnicate_widget()` (a research-fact marker a correct digest must retain — the non-vacuity / digest-risk guard).

(`simplicity` is NOT exercised in the teeth eval.) A trial "catches" iff BOTH `pass is False` AND the lens's marker appears as a substring of some finding (`qrspi_teeth_assert.py::_is_catch`). A lens passes iff `caught >= threshold`, where `threshold = floor(trials/2) + 1` (integer majority; default trials=3 ⇒ threshold 2, i.e. ">=2-of-3"). `overallPass` is True iff EVERY evaluated lens passes (empty set ⇒ False, fail-closed).

**Evidence:**

```js
const LENS_MARKERS = {
  'completeness': 'AC-TEETH-COMPLETENESS',
  'internal-consistency': 'TEETH-INCONSISTENCY',
  'edge-alignment': 'frobnicate_widget()',
}
```

— `.claude/workflows/qrspi-teeth-eval.js:62-66`

```python
def _is_catch(verdict, marker):
    if not isinstance(verdict, dict): return False
    if verdict.get("pass") is not False: return False
    ...
    for finding in findings:
        if isinstance(finding, str) and marker in finding: return True
```

— `scripts/qrspi_teeth_assert.py:58-78`

**Dependencies:** `qrspi-teeth-eval.js` (runner, off CI) → `qrspi_research_digest.py` (digest-ON) → `qrspi-design-critic-<lens>` agents → `qrspi_teeth_assert.py::evaluate` (decision math, CI-tested). Fixtures in `evals/teeth/`.
**Implicit contracts:** A RUS-79 prompt change MUST keep each owning lens able to fail AND cite its exact marker substring — changing a lens prompt such that it stops naming `AC-TEETH-COMPLETENESS` / `TEETH-INCONSISTENCY` / `frobnicate_widget()` would break the teeth eval. The catch-rule requires `pass is False` exactly (not falsy), so anti-pass-bias that makes lenses fail MORE is compatible, but the marker citation must survive any wording change.

## Q10: What existing tests cover critic verdict parsing, panel aggregation, and the teeth-eval majority/marker math, and which of them run in the CI regression gate?

**Answer:** All run in CI via `python3 scripts/run_tests.py` (the `python` job in `.github/workflows/tests.yml`, on every PR + push to main). The relevant `scripts/*_test.py`:
- **Verdict parsing / loop decision:** `qrspi_critic_loop_test.py` (assert-based, exercises `parse_critic_verdict`, `_coerce_verdict`, `next_action`).
- **Panel aggregation:** `qrspi_critic_synthesize_test.py` (unanimity + dedupe + lens-tagging + fail-closed).
- **Metrics reduce + dissent base-rate:** `qrspi_critic_metrics_test.py` (build_record), `qrspi_metrics_append_test.py` (envelope+append), `qrspi_critic_summary_test.py` (DissentTest, DissentRevisedRateTest, LoaderTest — the dissent-rate math).
- **Teeth majority/marker:** `qrspi_teeth_assert_test.py` (catch-rule, majority threshold, overallPass, CLI round-trip) and `qrspi_teeth_test.py`.
- **Config:** `qrspi_critics_config_test.py`, `qrspi_config_test.py`.

A second CI job `workflow-syntax` statically validates `.claude/workflows/*.js` via `scripts/check_workflows.js` (so `qrspi-batch.js` and `qrspi-teeth-eval.js` are compile-checked, not unit-tested).

**Evidence:**

```yaml
- name: Run Python test suite
  run: python3 scripts/run_tests.py
...
- name: Validate workflow scripts
  run: node scripts/check_workflows.js .claude/workflows/*.js
```

— `.github/workflows/tests.yml`

```
qrspi_critic_loop_test.py / qrspi_critic_synthesize_test.py /
qrspi_critic_summary_test.py / qrspi_teeth_assert_test.py / qrspi_critics_config_test.py
```

— `python3 scripts/run_tests.py --list` output

**Dependencies:** `run_tests.py` runs every `scripts/*_test.py` as its own subprocess; non-zero on any failure (the regression gate). The teeth eval *workflow* itself is OFF CI by design (`qrspi-teeth-eval.js:30-34`) — only its pure assertion core is CI-tested.
**Implicit contracts:** Tests are stdlib-only (no pytest/third-party). A RUS-79 prompt change to the agent `.md` files is NOT covered by any unit test (prompts are not unit-testable); the only automated guard on lens behavior is the opt-in, off-CI teeth eval. The dissent-rate math is the testable surface for the "base rate measurably moves" criterion.

## Q11: How is a "known-clean artifact" before/after run performed today — is there a fixture of a previously-passed real design the panel can be re-run against, and where would such a fixture live?

**Answer:** There is **NO clean/passing design fixture today** — the only committed design fixture is the deliberately-FLAWED teeth fixture at `evals/teeth/design.md` (carrying the three labelled defects). The teeth eval proves lenses CATCH defects (negative fixture); there is no positive "known-clean design the panel should PASS" fixture. The fixtures dir `evals/teeth/` holds `design.md`, `research.md`, `questions.md`, `ticket.md` — all crafted to be flawed/markered, not clean.

For a literal before/after on real artifacts, the documented procedure is the **manual A/B runbook** `docs/critic-cost-ab.md`: run the SAME real ticket through the design panel twice (lever OFF vs ON) and compare externally observed token totals — but it measures *tokens*, not pass/dissent rate, and is explicitly off CI. The reusable before/after path for *dissent rate* is the ledger + `qrspi_critic_summary.py --run-id` (Q2/Q12), scoping two runs of the same ticket.

**Evidence:**

```
evals/teeth/: design.md  questions.md  research.md  ticket.md   (all flawed/markered)
```

— `ls evals/teeth/`

```
// a deliberately-flawed design fixture carrying three labelled defects is fed to the REAL lenses
```

— `.claude/workflows/qrspi-teeth-eval.js:14-16`

**Dependencies:** `evals/teeth/*` (flawed fixtures) consumed only by `qrspi-teeth-eval.js`. `docs/critic-cost-ab.md` (manual token A/B). `qrspi_critic_summary.py` (read-side delta on the ledger).
**Implicit contracts:** NOT FOUND for a "known-clean previously-passed design" fixture — none exists in the repo. RUS-79 would need to EITHER add a clean positive fixture (and a teeth-style assert that the panel PASSES it, guarding against over-correction into pass→fail false positives) OR rely on the ledger before/after dissent-rate delta against a real ticket. The teeth harness (`qrspi-teeth-eval.js` + `qrspi_teeth_assert.py`) is the natural extension point — a clean fixture would live alongside `evals/teeth/` (e.g. `evals/teeth/clean-design.md`).

## Q12: Where are critic verdicts and the dissent base rate surfaced for inspection, and what is the unit of measurement RUS-78 emits that this ticket's "dissent base rate measurably moves" criterion would be evaluated against?

**Answer:** Per-step verdicts are surfaced in three places: (1) **live logs** via `log(...)` lines in the loops (e.g. "panel round N/M → PASS/FAIL (k/M lenses passed, j finding(s))"); (2) the **durable ledger** `.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl` (one `CriticMetricsLedgerLine` per terminated step); (3) the **PR body** for residual findings on cap-reached (via `criticConfig.residualFindings`/`criticSummary`). The dissent base rate is NOT auto-emitted anywhere at runtime — `qrspi-batch.js` only *appends* the ledger; it never calls `qrspi_critic_summary.py`. The summary is produced **on demand** by running `python3 scripts/qrspi_critic_summary.py [--run-id ID] [--ticket RUS-XX] <ledger.jsonl>`.

The **unit of measurement** RUS-78 emits is the `CriticSummary` dict, whose key metric is `dissentRate` (a float in [0,1]: fraction of recorded rounds that dissented, where dissent = `pass is False OR findingsCount > 0`), plus `dissentRevisedRate`, `terminalActionCounts`, and `perLens.{lens}.dissentRate`. RUS-79's "dissent base rate measurably moves" criterion is evaluated against `dissentRate` (and per-lens `dissentRate`) computed from two runId-scoped ledger summaries — before vs after the prompt change.

**Evidence:**

```python
return {
  "stepCount": len(scoped),
  "timestampSpan": span,
  "dissentRate": dissent_rate,
  "dissentRevisedRate": dissent_revised_rate,
  "terminalActionCounts": terminal_counts,
  "perLens": per_lens_out,
  "abortedRecords": aborted,
}
```

— `scripts/qrspi_critic_summary.py:176-184`

```js
// CriticMetricsLedgerLine so a summarizer (scripts/qrspi_critic_summary.py) can scope
// a base-rate report to exactly one run (RUS-78, AC-Instrumentation).
```

— `.claude/workflows/qrspi-batch.js:110-111`

**Dependencies:** Ledger written by `qrspi_metrics_append.py`; read by `qrspi_critic_summary.py`. No automated summarization step exists in the orchestrator. `runId` (`qrspi-batch.js:116`) is the scoping key.
**Implicit contracts:** The ledger is the system of record; the summary is a pure read-side reduction (no aggregation stored). `dissentRate` is the canonical "base rate" unit. A `null` lens (single edge critic) rolls under per-lens key `"edge"`. Because the summary is on-demand only, measuring the RUS-79 delta is a MANUAL step (run summary before, run summary after) — there is no committed baseline number to diff against today.

---

## Discovered Patterns

- **Functional-core / imperative-shell everywhere.** Every non-trivial decision is a pure stdlib-only Python module (`qrspi_critic_loop.py`, `qrspi_critic_synthesize.py`, `qrspi_critic_metrics.py`, `qrspi_critic_summary.py`, `qrspi_teeth_assert.py`, `qrspi_critics_config.py`), each with a thin stdin→stdout CLI shim and a `*_test.py` sibling. The JS orchestrator (`qrspi-batch.js`) NEVER re-derives these decisions — it calls the python via a "worker" agent that runs one verbatim command (the `synthesizeVerdicts`/`criticDecision`/`recordCriticMetrics` pattern), because the JS sandbox cannot run python.
- **Uniform fail-closed coercion.** A single `_coerce_verdict`/`parse_critic_verdict` (in `qrspi_critic_loop.py`) is the shared fail-closed primitive reused by panel synthesis and the teeth catch-rule. Malformed/missing/null ⇒ NOT-passed, never raises. A `null` agent reply ⇒ abort (still emits an `aborted` metrics record).
- **Uniform `enabled` vocabulary, default OFF.** Every phase critic is opt-in; only an explicit boolean flips `enabled`. JS `DEFAULT_CRITIC_PHASES` mirrors the Python resolver defaults in lockstep (test-enforced).
- **Anti-pass-bias prose already present.** Every critic/lens prompt already carries a "Fail closed on doubt: … that is a finding" rule and an explicit edge-not-node framing. The pass-bias lever RUS-79 targets is the PROMPT WORDING, not the loop/aggregation wiring (which is fail-closed and unanimity-strict by construction).
- **maxRounds vs ciReviseCap are two unrelated caps.** `maxRounds` (default 2) bounds the in-phase critic produce→critique→revise loop; `ciReviseCap` (default 3, `qrspi_resolve_state.py`) bounds PR-CI-driven revises across batch runs. Easy to conflate.

## Inconsistencies

- **`design.md` (RUS-77) `terminalAction` enum is stale.** `qrspi_critic_metrics.py:33-36` notes "`design.md:76` is stale — it lists only `converged/cap_reached`; the four-value set {converged, cap_reached, exhausted, aborted} here is the faithful one" (flagged in `structure.md:19`). The CODE is authoritative.
- **Verdict schema vs prompt contract mismatch (latent).** `CRITIC_VERDICT_SCHEMA` permits `pass:false` with an EMPTY `findings` array (no min-items constraint). The prompts SAY `pass:false` ⇒ findings MUST be non-empty (`qrspi-critic.md:42`), and `next_action`/synthesize tolerate empty findings on a fail. So an "ambiguous ⇒ fail" framing could yield a fail with zero actionable findings — the schema would not reject it. Relevant to RUS-79: stricter pass bias should also force a finding, or it surfaces fails the reviser cannot act on.
- **Dissent base rate is never auto-surfaced.** `qrspi-batch.js` appends the ledger but never invokes `qrspi_critic_summary.py`; the "base rate" only exists once a human runs the summary CLI. There is no committed baseline figure, so RUS-79's "measurably moves" is a manual before/after, not an automated assertion.
- **No clean/positive design fixture.** The teeth eval only proves lenses CATCH a flawed design; there is no fixture proving the panel PASSES a known-good design. An anti-pass-bias change risks introducing pass→fail false positives that NO existing test or fixture would catch.
- **`lensModel` lever documented as possibly inert.** `qrspi-batch.js:863-865` and the config comment both note there is no evidence the harness honors an `agent()` `model` option — the lever ships default-OFF and may be a no-op. Not load-bearing for RUS-79 but worth noting if cost interacts with prompt length.
