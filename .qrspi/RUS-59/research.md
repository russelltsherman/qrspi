# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Q1: How does the Design phase currently flow from inputs (ticket, questions, research) to a single produced `design.md`, and at what point would an N-candidate generation step splice in before the existing critic panel?

**Answer:** `doDesign(t, r)` (`.claude/workflows/qrspi-batch.js:1016`) runs three sequential `runPhase()` calls: `questions` → `research` → `design`. Each `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)` (`:861`) spawns ONE typed phase agent which writes its artifact to the token-free staging path `stg(id, name)` = `/tmp/phase-stage/<id>/<name>.md` (`:531`), THEN — only for the `design` call — runs the critic loop on the staged file, THEN deterministically persists the staged file to the canonical worktree path via `persistArtifact` (`:893`). So today exactly ONE design agent produces ONE `design.md` at `stg(id, 'design')`.

The critic dispatch happens inside `runPhase` AFTER produce-success and BEFORE persist (the "pre-persist staging window", `:871-889`): when `criticConfig` is present it calls `runCriticPanelLoop` (if `criticConfig.lenses?.length`) or `runCriticLoop`. An N-candidate generation step would splice into `runPhase` (or a new design-specific helper called from `doDesign`) BETWEEN the single `agent(prompt, …)` produce call (`:866`) and the `if (criticConfig)` critic block (`:874`) — i.e. it must produce one winning `design.md` at `stg(id, 'design')` before the existing panel runs, leaving `runCriticPanelLoop` and `persistArtifact` untouched.

**Evidence:**

```js
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
if (res === null) { /* stop */ }
if (criticConfig) {
  const cr = criticConfig.lenses?.length
    ? await runCriticPanelLoop(name, id, criticConfig)
    : await runCriticLoop(name, id, criticConfig)
  // …
}
const p = await persistArtifact(id, name, phaseLabel)
```

— `.claude/workflows/qrspi-batch.js:866-893`
**Dependencies:** `doDesign` → `runPhase` → `agent()` (runtime global) → `runCriticPanelLoop`/`runCriticLoop` → `persistArtifact` → `scripts/qrspi_persist.py`. The produce `agent()` call is the single splice point.
**Implicit contracts:** The produce step must leave a non-empty file at `stg(id, name)`; persist verifies non-empty and is "the real success gate" (`:892`). `criticConfig` absent ⇒ the critic block is skipped byte-for-byte (AC1 no-critic behavior, `:856`).

## Q2: How are the per-candidate framing prompts (e.g. MVP-first / risk-first / simplest-thing) materialized and passed to each parallel design-agent run, and where would diverse framing variants be defined?

**Answer:** NOT FOUND as an existing feature — there is no per-candidate framing mechanism today. The single design agent is spawned with ONE fixed prompt built inline in `doDesign` (`:1051-1058`) and dispatched via `runPhase` → `agent(prompt, { agentType: 'qrspi-design' })`. The agent prompt template lives at `.claude/agents/qrspi-design.md`; its frontmatter is `name: qrspi-design`, `tools: Read, Write`, and the body has no notion of a "framing" or "candidate variant" — it produces one design with fixed required sections (Current State, Desired End State, Delta, Pattern Decisions, Risk Register, Open Questions).

The closest EXISTING parallel-fan-out-with-per-run-variation pattern is the critic panel: `runCriticPanelLoop` (`:677`) maps over `lenses` and varies each parallel run's prompt by lens id and `agentType = qrspi-design-critic-${lens}` (`:690-699`). A diverse-framing variant would follow that pattern: define framing ids (analogous to `DEFAULT_DESIGN_LENSES` at `:520`), and in the parallel map, interpolate a per-framing instruction into the otherwise-identical design prompt (all candidates can reuse the SAME `qrspi-design` agentType with a framing line spliced into the prompt, OR new per-framing agent prompt files mirroring the lens files).

**Evidence:**

```js
if (!await runPhase('design', 'qrspi-design',
  `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
RESEARCH_PATH = ${art(wd, t.id, 'research.md')}
OUTPUT_PATH = ${stg(t.id, 'design')}
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design', designCritic)) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:1051-1058`
**Dependencies:** `doDesign` builds the prompt string; `art()`/`tpl()`/`stg()` helpers (`:525-531`) build the paths; the `qrspi-design` agent reads `QUESTIONS_PATH`/`RESEARCH_PATH`/`TICKET_CONTENT_PATH` and writes `OUTPUT_PATH`.
**Implicit contracts:** A design agent receives inputs as `KEY = value` lines and MUST write exactly to the `OUTPUT_PATH` it is given. If N candidates run in parallel they need N DISTINCT output paths (the single `stg(id,'design')` would collide); the panel pattern uses no per-run output file (critics return schema'd JSON, not files), so candidate generation needs a new per-candidate staging-path convention.

## Q3: How does the synthesized winning `design.md` reach the staging path consumed by the critic panel, and how is staging handled today for the single-design path?

**Answer:** Today the single design agent writes DIRECTLY to `stg(id, 'design')` (`/tmp/phase-stage/<id>/design.md`) as its `OUTPUT_PATH` (`:1057`). The critic panel then reads that SAME path: `runCriticPanelLoop` sets `artifactPath = stg(id, name)` and passes it to every lens as `DESIGN_PATH` (`:680, :694`), and the reviser rewrites it IN PLACE (`:752-762`). Finally `persistArtifact(id, 'design', …)` (`:893`) invokes `scripts/qrspi_persist.py --ticket <id> --artifact design`, which self-locates the repo root, verifies the staged file is non-empty, and moves `/tmp/phase-stage/<id>/design.md` → `.worktrees/<id>/.qrspi/<id>/design.md`. So the staging path is the single contract surface between produce, critic, and persist.

For N-select: the synthesis step must land the WINNING candidate's content at exactly `stg(id, 'design')` before `runCriticPanelLoop` runs (which keys off that path). The persist gate and panel need no change — only that one file must exist non-empty at that path.

**Evidence:**

```js
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
// …in runCriticPanelLoop:
const artifactPath = stg(id, name)        // :680
// …the lens prompt:
DESIGN_PATH = ${artifactPath}             // :694
```

— `.claude/workflows/qrspi-batch.js:531, :680, :694`; persist at `scripts/qrspi_persist.py`
**Dependencies:** `stg()` (`:531`) is "kept in sync with scripts/qrspi_persist.py STAGE_ROOT" (`:530`). `persistArtifact` (`:553`) → `qrspi_persist.py`.
**Implicit contracts:** Token-free staging path carries NO "qrspi" token so a weak worker model can't mangle it (`:528-530`). The path is `id`+`name` only; any N-candidate intermediate files must use distinct names (e.g. `design-cand-1`) so they don't clobber the canonical `design` staging slot before synthesis writes the winner there.

## Q4: What is the existing critic-panel entry contract (`runCriticPanelLoop` / `runCriticLoop`) that an N-select stage must produce a single `design.md` for, and what shape does it expect?

**Answer:** `runCriticPanelLoop(name, id, criticConfig)` (`:677`) and `runCriticLoop(name, id, criticConfig)` (`:586`) share the entry/return contract. Both read the artifact from `stg(id, name)`, run a bounded produce→critique→revise loop, and return `{ ok: boolean, residualFindings: string[] }` (the panel additionally returns an optional `summary` string, `:742/:746/:772`). `runPhase` consumes the return: on `!cr.ok` it stops the ticket (`:881`); otherwise it writes `criticConfig.residualFindings = cr.residualFindings` and `criticConfig.criticSummary = cr.summary` back onto the passed config object (`:887-888`).

`criticConfig` fields consumed by the PANEL (`:677-683`): `lenses` (non-empty list — the panel switch), `maxRounds` (default 2), `upstreamPath` (research.md, used as `RESEARCH_PATH`), `ticketContentPath`, `questionsPath`. These are populated in `doDesign` (`:1043-1049`). An N-select stage must (a) write the winning design to `stg(id, 'design')` and (b) leave `criticConfig` shaped for the panel exactly as `doDesign` builds it — the panel itself is unchanged.

**Evidence:**

```js
async function runCriticPanelLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const lenses = criticConfig.lenses
  const artifactPath = stg(id, name)
  const researchPath = criticConfig.upstreamPath
  const ticketContentPath = criticConfig.ticketContentPath
  const questionsPath = criticConfig.questionsPath
  // … returns { ok, residualFindings, summary? }
```

— `.claude/workflows/qrspi-batch.js:677-684`, return shapes `:710/:724/:742/:746/:772`
**Dependencies:** `runPhase` (`:874-889`) is the sole caller; `doDesign` (`:1043`) builds the config; `runCriticPanelLoop` → `synthesizeVerdicts` (`:721`) + `criticDecision` (`:735`).
**Implicit contracts:** Return MUST include `ok` and `residualFindings`; `ok:false` aborts the ticket. The panel is byte-for-byte unchanged whether or not N-select preceded it — it only reads `stg(id, 'design')` and the three upstream paths.

## Q5: What verdict/score schema do existing critic and lens agents emit (`CRITIC_VERDICT_SCHEMA`, `parse_critic_verdict`), and what schema would a judge agent scoring N candidates on a rubric reuse or extend?

**Answer:** Three relevant schemas live in `.claude/workflows/qrspi-batch.js`:
1. `CRITIC_VERDICT_SCHEMA` (`:466-473`) — `{ pass: boolean, findings: string[] }`. Emitted by both the single `qrspi-critic` agent AND every lens agent `qrspi-design-critic-<lens>` (spawned with this schema at `:600` and `:699`).
2. `SYNTHESIZED_VERDICT_SCHEMA` (`:494-513`) — the reduced round verdict `{ pass, findings }` where each finding may be a bare string OR `{ text, lens }`.
3. `LOOP_DECISION_SCHEMA` (`:479-486`) — `{ action: 'converged'|'revise'|'cap_reached', residual_findings: string[] }`.

The lens prompts return the `{pass, findings}` contract (lens agent `.claude/agents/qrspi-design-critic-completeness.md` etc.). Python side: `parse_critic_verdict` / `_coerce_verdict` (`scripts/qrspi_critic_loop.py:36-79`) coerce to `{pass: bool, findings: list}` fail-closed.

There is NO existing per-candidate SCORE schema — all verdicts are binary `pass` + findings, NOT a numeric rubric score. A judge agent ranking N candidates would NEED A NEW schema (e.g. `{ scores: [{ candidate, score, rationale }], winner }`); the closest reusable element is the `{pass, findings}` shape and the deduped-union reduction pattern in `synthesize`, but neither carries a comparative/ranking score.

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

— `.claude/workflows/qrspi-batch.js:466-473`
**Dependencies:** Schemas are passed to `agent({ schema })`; `qrspi_critic_loop.py` / `qrspi_critic_synthesize.py` are the Python-side canonical coercion.
**Implicit contracts:** Verdicts are binary pass + free-text findings, never numeric. A "judge scoring on a rubric" introduces a NEW comparative dimension absent from the current schemas — it cannot simply reuse `CRITIC_VERDICT_SCHEMA` if it must rank/select among N.

## Q6: How is the N×-cost gate configured today for the existing Design panel (`critics.design`), and where is the single enabling flag for N-select generation read and parsed?

**Answer:** The design panel reads the OPTIONAL top-level `critics` key from `.qrspi/config.json`. `readDesignCriticConfig()` (`:800-815`) spawns a CONFIG worker that runs `python3 scripts/qrspi_config.py --key critics`, then pipes the output through `parseCriticConfig(text)` (`:337-348`) and `resolveDesignCritic(design)` (`:358-376`). `qrspi_config.py` is single-top-level-key only (no dot-path), so `--key critics` returns the whole object; `parseCriticConfig` extracts `value.design` (an object) or `undefined`. `resolveDesignCritic` applies config>default precedence: `maxRounds` (positive int, default 2) and `lenses` (filtered to `KNOWN_DESIGN_LENSES`, default `DEFAULT_DESIGN_LENSES` four). Config schema documented at `.qrspi/config.example.json` under `critics.design` (`maxRounds`, `lenses`).

There is NO N-select flag today — `critics.design` has only `maxRounds` + `lenses`. An N-select enabling flag (e.g. `critics.design.candidates` or a boolean) would be parsed in `parseCriticConfig`/`resolveDesignCritic` (read off the same `value.design` object). Note: any non-positive/absent value must default OFF (Q10). The parser is lenient/best-effort — a garbled critics block silently disables the override and falls back to JS defaults (`:335-336`), so an absent flag must mean N=1.

**Evidence:**

```js
function resolveDesignCritic(design) {
  const cfg = design && typeof design === 'object' ? design : {}
  const maxRounds = Number.isInteger(cfg.maxRounds) && cfg.maxRounds > 0 ? cfg.maxRounds : 2
  let lenses = DEFAULT_DESIGN_LENSES
  if (Array.isArray(cfg.lenses)) { /* filter to KNOWN_DESIGN_LENSES, default fallback */ }
  return { maxRounds, lenses }
}
```

— `.claude/workflows/qrspi-batch.js:358-376`
**Dependencies:** `readDesignCriticConfig` → CONFIG worker → `scripts/qrspi_config.py --key critics` → `parseCriticConfig` → `resolveDesignCritic`. Documented in `.qrspi/config.example.json`.
**Implicit contracts:** `qrspi_config.py` reads ONE top-level key only (MEMORY: "Config reader is single-top-level-key only"); a nested `critics.design.X` must be reached by reading `critics` and walking the object in JS, NOT by `--key critics.design` (which returns the default ""). `select_value` in `qrspi_config.py:36-42` returns the raw value (an object for `critics`) despite str type hints. Best-effort: any parse failure ⇒ defaults, never gates the run.

## Q7: How are parallel agent fan-out runs (multiple candidates) currently coordinated and collected, including how the per-round results are accumulated?

**Answer:** Parallel fan-out uses the runtime-injected `parallel(thunks)` global (it is NOT defined in qrspi-batch.js — confirmed by grep finding 0 definitions; it is provided by the Workflow runner). Two call sites: (1) the Query phase `parallel(STATUSES.map(status => () => agent(...)))` (`:1676-1688`), and (2) the critic panel `runCriticPanelLoop` (`:689-703`). In the panel, `parallel(lenses.map(lens => async () => { … return { lens, verdict } }))` runs one agent per lens concurrently; results are collected as an array of `{ lens, verdict }`, then: failed-spawn check (`replies.find(rp => !rp || rp.verdict === null)`, `:707`), build `lensVerdicts` (`:714`), reduce via `synthesizeVerdicts` (`:721`). The loop runs up to `maxRounds`, accumulating `summaryRounds.push(...)` per round (`:730`) for the final log line.

This `parallel(items.map(x => async () => agent(...)))` → collect array → check-for-failures → reduce pattern is exactly what N-candidate generation would reuse: map N framings to N design-agent thunks, collect the candidate artifacts, then judge+synthesize.

**Evidence:**

```js
const replies = await parallel(
  lenses.map(lens => async () => {
    const agentType = `qrspi-design-critic-${lens}`
    const verdict = await agent(/* … */, { /* …schema: CRITIC_VERDICT_SCHEMA */ })
    return { lens, verdict }
  })
)
const failedLens = replies.find(rp => !rp || rp.verdict === null)
```

— `.claude/workflows/qrspi-batch.js:689-707`
**Dependencies:** `parallel` + `agent` are Workflow-runtime globals; `synthesizeVerdicts` (`:779`) reduces the collected array.
**Implicit contracts:** Each thunk returns a tagged object so the reducer can attribute results; a null result from any thunk is a hard stop (a missing lens is never treated as a pass, `:706-711`). Candidates that return a SCHEMA'd value collect cleanly; a candidate that writes a FILE (like a design agent) needs a distinct staging path per thunk to avoid collision (see Q3).

## Q8: What happens when the N candidate design runs disagree such that the judge produces a tie or no clear winner — where would tie-breaking in judge scoring/synthesis selection be handled?

**Answer:** NOT FOUND as existing logic — there is no judge/selection/tie-break code today (no N-candidate selection exists). The CLOSEST analog is the panel's two reduction modules, both pure/stdlib/tested, which establish where such logic WOULD live:
- `scripts/qrspi_critic_synthesize.py::synthesize(verdicts)` (`:76-118`) — reduces M lens verdicts to one with AND-semantics (`pass` only if EVERY lens passed) and an exact-string-deduped union of findings. Fail-closed: empty/garbled ⇒ NOT-passed.
- `scripts/qrspi_critic_loop.py::next_action(verdicts, round, max_rounds)` (`:82-113`) — converge/revise/cap decision.

Judge scoring + synthesis selection (including tie-break) would be a NEW pure module alongside these (e.g. `scripts/qrspi_design_select.py`), mirroring the synthesize/next_action pattern: a deterministic stdin-JSON → stdout-JSON selector invoked from JS via a worker (like `synthesizeVerdicts` at `:779-793` and `criticDecision` at `:821-835`). Tie-break must be DETERMINISTIC (the existing reducers are pure and deterministic — first-seen order, AND-semantics) — e.g. highest score, ties broken by candidate index.

**Evidence:**

```python
def synthesize(verdicts):
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}
    all_passed = True
    findings = []
    seen = set()
    for entry in verdicts:  # deterministic first-seen-order dedupe
        ...
```

— `scripts/qrspi_critic_synthesize.py:76-118`
**Dependencies:** New selector would sit beside `qrspi_critic_synthesize.py` / `qrspi_critic_loop.py`; JS would call it via a worker like `synthesizeVerdicts`/`criticDecision`.
**Implicit contracts:** Reduction logic is PURE, stdlib-only, deterministic, fail-closed, and unit-tested separately from the JS glue (the JS "never re-derives the reduction", `:657-658`). A tie-break must therefore be deterministic and testable in isolation.

## Q9: How are partial failures of parallel runs handled — e.g. if one of the N design-agent runs errors or produces an empty/unparseable artifact, does the phase abort or proceed with the surviving candidates?

**Answer:** Today's parallel sites are FAIL-CLOSED / abort-on-any-failure, NOT proceed-with-survivors. In `runCriticPanelLoop`, a single null lens verdict stops the whole ticket: `const failedLens = replies.find(rp => !rp || rp.verdict === null); if (failedLens) { … return { ok: false, residualFindings: [] } }` (`:707-711`). Likewise `synthesizeVerdicts` returning null (`:722`) or `criticDecision` null (`:736`) aborts. At the `runPhase` level, a null produce result (`res === null`, `:867`) stops the ticket, and the persist gate (`:894`) stops if no non-empty artifact was staged. The Query-phase `parallel` (`:1690-1698`) is more lenient — it skips null batches (`if (!b) continue`) — but that is a sweep, not a quality gate.

So the EXISTING convention for a quality-bearing fan-out is "any failure aborts." A design-candidate fan-out that wants to "proceed with survivors" would be a DEPARTURE from the panel's all-or-nothing rule and must be an explicit design choice (e.g. require ≥1 valid candidate, or ≥K). The empty/unparseable case for produced FILES is enforced downstream by `qrspi_persist.py` (non-empty check); for SCHEMA'd returns, the runner's schema validation + the `=== null` check catch unparseable.

**Evidence:**

```js
const failedLens = replies.find(rp => !rp || rp.verdict === null)
if (failedLens) {
  log(`  ${id}: ${name} panel round ${round + 1} — lens "${failedLens.lens}" failed/skipped, stopping this ticket`)
  return { ok: false, residualFindings: [] }
}
```

— `.claude/workflows/qrspi-batch.js:707-711`
**Dependencies:** `runCriticPanelLoop` abort → `runPhase` `!cr.ok` → `failTicket`. Persist gate: `qrspi_persist.py`.
**Implicit contracts:** "a missing lens is never silently treated as a pass" (`:705-706`); the same fail-closed posture (a missing/empty candidate is never silently treated as a winner) would be the natural extension. Any "survivors" policy contradicts the current all-or-nothing precedent and needs an explicit minimum-survivor threshold.

## Q10: When the N-select flag is OFF (the default), what guarantees the Design phase behaves exactly as the panel-only path does today with no extra spend?

**Answer:** The guarantee mechanism for opt-in seams in this codebase is the `if (criticConfig)`-style guard plus default-OFF config parsing. Two precedents:
1. `runPhase` (`:856-857`): "Absent (undefined) ⇒ the guard is false ⇒ the four original statements run VERBATIM (AC1, byte-for-byte unchanged no-critic behavior)." The critic block at `:874` is entirely skipped when `criticConfig` is undefined.
2. The panel dispatch at `:878`: `criticConfig.lenses?.length ? runCriticPanelLoop : runCriticLoop` — a falsy/absent `lenses` keeps the single-critic path unchanged.
3. `resolveDesignCritic` (`:358-376`) defaults to the JS values when config is absent/garbled — best-effort, never gates.

For N-select OFF: the splice point (between produce and the critic block in `runPhase`, per Q1) must be guarded by an N>1 check that defaults to N=1 when the flag is absent. When N=1, the design phase must run the SINGLE produce `agent(prompt, …)` exactly as today (`:866`) — no extra agent spawns, no judge worker, no synthesis — then fall through to the unchanged `runCriticPanelLoop`. The existing default-OFF, best-effort config pattern (`parseCriticConfig` returns `undefined` ⇒ JS defaults) is the template: an absent `critics.design` candidate count parses to N=1.

**Evidence:**

```js
// criticConfig … Absent (undefined) ⇒ the guard is false ⇒ the four original
// statements run VERBATIM (AC1, byte-for-byte unchanged no-critic behavior).
if (criticConfig) { /* critic loop … */ }
```

— `.claude/workflows/qrspi-batch.js:856-857, :874`
**Dependencies:** `runPhase` guard; `resolveDesignCritic` defaults; `parseCriticConfig` undefined-on-garble.
**Implicit contracts:** The byte-for-byte-unchanged-when-off invariant is an explicit AC pattern in this codebase (AC1). N-select must spawn ZERO extra agents when N=1, mirroring how an absent `criticConfig` spawns zero critic agents.

## Q11: How are existing parse/scoring helpers unit-tested with stubbed inputs (the `scripts/qrspi_*_test.py` pattern), and where would unit tests for judge scoring + synthesis selection with stubbed candidates live?

**Answer:** Pure helpers are tested by stdlib-only `_test.py` siblings run directly with `python3`, with NO test runner dependency — two styles coexist: (a) a `check(label, got, want)` assert-helper with module-level `check(...)` calls and a `failures`/`total` counter (`scripts/qrspi_critic_synthesize_test.py:29-54`), and (b) `unittest.TestCase` subclasses (`scripts/qrspi_config_test.py`). Both import the pure function and feed in-memory stubbed inputs (lists of verdict dicts, in-memory config dicts) — no `agent()`, no git, no IO. The JS sandbox can't run python, so the pure logic is moved into `scripts/qrspi_*.py` precisely so it's testable (`:611-612`, `:657-658`).

A judge-scoring + selection module would follow this exactly: a pure `scripts/qrspi_design_select.py` with a `scripts/qrspi_design_select_test.py` sibling exercising stubbed candidate-score lists (all-pass, ties, single-winner, empty/malformed fail-closed), mirroring `qrspi_critic_synthesize_test.py`'s coverage list (`:7-13`).

**Evidence:**

```python
def check(label, got, want):
    global failures, total
    total += 1
    if got == want:
        print("ok: %s" % label)
    else:
        failures += 1
        print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))
```

— `scripts/qrspi_critic_synthesize_test.py:29-36`
**Dependencies:** `*_test.py` imports the sibling pure module; `sys.path.insert(0, _HERE)` (`:19-20`) makes the import work from any cwd.
**Implicit contracts:** "All of the above have stdlib-only unit tests as `_test.py` siblings (`scripts/qrspi_*_test.py`, run with `python3`)" — per `.claude/CLAUDE.md` codebase conventions. Pure, IO-free, deterministic, fail-closed coverage (empty/malformed inputs explicitly tested).

## Q12: How does the eval harness compare configurations today, given it is a non-functional placeholder, and what is the mechanism for an eval comparison of panel-only vs. N-select + panel?

**Answer:** `scripts/run_eval.py` runs an eval SUITE (`evals/suite.json`, 15 cases, each with `id/prompt/assertions/...`) against ONE skill/agent prompt: `run_suite` (`:201`) fans out `cases × trials` via `ThreadPoolExecutor`, each calling `execute_single` → `call_model` (the mockable Anthropic seam, `:99-148`), and writes raw `output`/`tokens`/`transcript` per trial to `results.json` (`:271-289`). Critically: it RECORDS outputs but NEVER evaluates the `assertions` — there is no assertion-scoring, no pass/fail tally, and NO config-comparison or A/B mechanism. `suite.load_suite` validates that each case HAS `assertions` (`:54`) but nothing consumes them. Per project convention, "The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder — verify pure logic with the unit tests and orchestration changes with manual end-to-end runs" (`.claude/CLAUDE.md`; MEMORY: "Eval harness is a placeholder").

Therefore there is NO existing mechanism to compare panel-only vs N-select+panel via the eval harness. Comparison today must be done by: (a) unit tests for the pure judge/selection logic, and (b) manual end-to-end batch runs. Any harness-level A/B would be net-new (the harness has no notion of "configuration variants" — it takes one `--skill` path, one suite).

**Evidence:**

```python
for case in suite["cases"]:
    case_required = {"id", "prompt", "assertions"}
    case_missing = case_required - set(case.keys())
    if case_missing:
        raise ValueError(f"Case {case.get('id', '?')} missing: {case_missing}")
# … run_suite records output/tokens/transcript to results.json; assertions never scored
```

— `scripts/run_eval.py:53-57`, `:271-289`
**Dependencies:** `run_eval.py` → `evals/suite.json` + `call_model` (Anthropic SDK seam, mocked in tests). `results.json` is the only output.
**Implicit contracts:** Harness is a placeholder: assertions are declared but unscored; no comparison/grading; verification is unit-tests + manual e2e. Token cost IS captured per trial (`tokens: {input, output}`, `:136-139`) — the only quantitative signal the harness produces, but it is not aggregated or compared.

## Q13: How is per-round critic-panel activity logged today, and where would per-candidate judge scores AND token cost be reported so the N× spend can be justified against the panel alone?

**Answer:** Per-round panel activity is logged via the runtime `log(...)` global (not defined in qrspi-batch.js — runner-injected). In `runCriticPanelLoop`: a per-round PASS/FAIL line with lens pass-count and finding count (`:729`), a `summaryRounds.push('r1:pass' | 'r1:2/4')` accumulator (`:730`), and terminal CONVERGED/CAP-REACHED/exhausted lines carrying `[${summaryRounds.join(' ')}]` (`:741/:745/:771`). The panel returns a `summary` string (`:742/:746/:772`) which `doDesign` folds into the result summary: `out.summary = ${out.summary} [${designCritic.criticSummary}]` (`:1077`) and a residual-finding count (`:1078`). `doDesign` also logs the lens set + maxRounds up front (`:1050`).

Crucially: NO TOKEN-COST is logged anywhere in the orchestrator — token usage is captured ONLY inside `run_eval.py` (`tokens: {input, output}`, see Q12), never in qrspi-batch.js. So per-candidate judge scores and N× token cost have NO existing reporting surface in the batch run. New per-candidate score+cost reporting would follow the `log(...)` + `summaryRounds` + returned-`summary` pattern in the new selection helper / its JS glue (mirroring `:729-730` and the `summary` fold-in at `:1077-1078`), but a token-cost figure would need a NEW source (the runner's `agent()` does not currently return token counts to this script).

**Evidence:**

```js
log(`  ${id}: ${name} panel round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${passCount}/${lenses.length} lenses passed, ${synthFindings.length} finding(s))`}`)
summaryRounds.push(`r${round + 1}:${passed ? 'pass' : `${passCount}/${lenses.length}`}`)
// …
return { ok: true, residualFindings: [], summary: `panel converged@r${round + 1} [${summaryRounds.join(' ')}]` }
```

— `.claude/workflows/qrspi-batch.js:729-730, :742`
**Dependencies:** `log` (runtime global) → stdout; panel `summary` → `runPhase` (`criticConfig.criticSummary`, `:888`) → `doDesign` result summary (`:1077`).
**Implicit contracts:** Logging convention is a single indented `${id}: …` line per round plus a compact `summaryRounds` token list folded into the returned `summary`. The batch orchestrator has NO token-accounting today; justifying N× spend by token cost requires a new measurement source not present in `agent()`'s current return.

---

## Discovered Patterns

- **Pure-core / JS-glue split.** Every testable decision (synthesize, next_action, config select) lives in a pure, stdlib-only `scripts/qrspi_*.py` with a thin stdin-JSON→stdout-JSON CLI; the JS "never re-derives" it and invokes it through a worker agent because the JS sandbox cannot run python (`synthesizeVerdicts` `:779`, `criticDecision` `:821`, `qrspi_critic_synthesize.py:121-151`, `qrspi_critic_loop.py:116-153`). An N-select judge/selector should follow this exact split.
- **Token-free staging path + deterministic persist gate (Fix A).** Phase agents write to `/tmp/phase-stage/<id>/<name>.md` (`stg()`, `:531`); `qrspi_persist.py` verifies non-empty and moves to the canonical worktree path. Persist is the real per-phase success gate (`runPhase:893`). N candidates need DISTINCT staging names to avoid clobbering the canonical `design` slot.
- **Opt-in seam, default-OFF, byte-for-byte unchanged when absent.** `criticConfig` undefined ⇒ critic block skipped verbatim (`:856-857, :874`); `parseCriticConfig` garbled ⇒ JS defaults; config parsing is best-effort and "never gates the run." This is the repo's canonical way to add a feature behind a flag with zero default spend.
- **Fan-out is fail-closed.** Quality-bearing `parallel` (the critic panel) aborts the whole ticket on ANY null result; "a missing lens is never silently treated as a pass" (`:705-711`). Only the non-gating Query sweep skips nulls.
- **Verdicts are binary, not scored.** All critic/lens output is `{pass, findings}` (free-text findings). There is no numeric/comparative score anywhere — a "judge scoring on a rubric" is a genuinely new schema dimension.
- **`agent`, `parallel`, `log`, `phase` are Workflow-runtime globals** — not defined in qrspi-batch.js (grep confirms 0 definitions). They are provided by the Workflow runner; the script's contract is to call them.
- **Config reader reads ONE top-level key only.** `qrspi_config.py --key critics` returns the whole object; nested `critics.design.X` is walked in JS, never via a dot-path key (a `--key critics.design` returns the default). Confirmed by MEMORY note "Config reader is single-top-level-key only."

## Inconsistencies

- **`qrspi_config.py` type hints vs behavior.** `select_value(config, key, default) -> str` and `read_config -> dict` are annotated as returning strings, but for `--key critics` they return/select an OBJECT (the critics block), which `parseCriticConfig` relies on (`:343` accepts an object `value`). The docstring/envelope comment "value: <str|null>" (`qrspi_config.py:17`) understates the actual contract the design panel depends on. The code works; the annotations/comments are stale relative to the `critics` use.
- **Eval harness validates `assertions` but never scores them.** `load_suite` REQUIRES each case to carry `assertions` (`run_eval.py:54`), implying grading, but `run_suite`/`execute_single` only record raw outputs — no assertion is ever evaluated. The harness is documented as a "non-functional placeholder," so this is a known gap, but the required-field validation reads as if scoring exists when it does not.
- **Token cost is captured in the eval harness but nowhere in the orchestrator.** `run_eval.py` records `{input, output}` tokens per trial (`:136-139`), yet qrspi-batch.js has no token accounting at all. Any "justify N× spend by token cost" requirement straddles two subsystems and has no single existing surface.
- **Fan-out failure policy differs by call site.** The critic panel aborts on any null (`:707-711`); the Query sweep silently skips nulls (`:1693`). "Proceed with surviving candidates" for N-select would match the Query (lenient) precedent but CONTRADICT the panel (strict) precedent — the design must pick one explicitly.
