# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T17:00:00Z
**Status:** draft

## Q1: How does the design-step input (research.md and the upstream artifact) reach each of the 4 design-panel lenses today — is the full ~36KB research.md passed verbatim to every lens, or is there any shared/derived digest already produced before fan-out?

**Answer:** Each lens receives **file PATHS, not content** — the full research.md (and the other inputs) are passed by absolute path and each lens agent Reads them itself. There is NO shared/derived digest. The panel (`runCriticPanelLoop`) fans out one agent per lens in `parallel()`; every lens gets the **identical** four paths: `DESIGN_PATH` (the staged design), `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, `QUESTIONS_PATH`. So the full research.md is read verbatim by all 4 lenses (4× independent reads of the same file), once per round. There is no pre-fan-out summarization, truncation, or digest step anywhere in the path.

**Evidence:**

```js
const replies = await parallel(
  lenses.map(lens => async () => {
    const agentType = `qrspi-design-critic-${lens}`
    const verdict = await agent(
      `You are the ${lens} lens of the qrspi design-phase critic panel for ${id}, round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}
Read all four paths and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`,
```

— `.claude/workflows/qrspi-batch.js:813-823`

The lens agent definition confirms it reads the paths itself (tools: Read):

```
- `RESEARCH_PATH` — absolute path to `research.md` (the codebase facts the design was derived from).
...
1. Read `TICKET_CONTENT_PATH`, `RESEARCH_PATH`, and `QUESTIONS_PATH` in full.
```

— `.claude/agents/qrspi-design-critic-completeness.md:13,22`

The inputs are resolved once in `doDesign` and handed on `designCritic`:

```js
const designCritic = critics.design.enabled ? {
  upstreamPath: art(wd, t.id, 'research.md'),
  maxRounds: critics.design.maxRounds,
  lenses: critics.design.lenses,
  ticketContentPath: r.ticketContentPath,
  questionsPath: art(wd, t.id, 'questions.md'),
  candidates: critics.design.candidates,
  templatePath: tpl(wd, 'design.md'),
} : undefined
```

— `.claude/workflows/qrspi-batch.js:1518-1528`

**Dependencies:** `runCriticPanelLoop` (consumer) ← `doDesign` (assembles the path bundle) ← `runPhase` (dispatches to the panel on `criticConfig.lenses?.length`, batch.js:1284-1286). Lens agents `.claude/agents/qrspi-design-critic-<lens>.md` are the downstream readers.
**Implicit contracts:** Inputs cross the agent boundary as **absolute file paths only**, never inlined content — the harness-wide "file→file, never round-trip fragile text through stdout" convention (cf. ticketContentPath rationale, batch.js:1313-1317). Every lens is assumed to receive a present, readable research.md; there is no fallback if it is missing/empty (the producer + persist gate are assumed to have guaranteed it upstream).

## Q2: What is the ordering and data hand-off between the 2 edge critics, the 4 panel lenses, and the 3 synthesize/decide steps (which step's output feeds which) within a single design step?

**Answer:** A "design step" (`doDesign`, batch.js:1457) runs THREE phases sequentially through `runPhase`: questions → research → design. Each phase, when its critic is enabled, runs the critic loop INSIDE the pre-persist staging window (produce → [N-select] → [node-check] → critic loop → persist). The "2 edge critics" are the single-critic loops on **questions** (anchored on the ticket) and **research** (anchored on questions.md, plus a citation node-check) — each via `runCriticLoop`. The "4 panel lenses" run on the **design** artifact via `runCriticPanelLoop`. Within one round of the panel the hand-off is: 4 lenses (parallel) → each returns `{pass, findings}` tagged with its lens → **synthesize** (`synthesizeVerdicts` → `scripts/qrspi_critic_synthesize.py`) reduces M lens verdicts to ONE round verdict → **decide** (`criticDecision` → `scripts/qrspi_critic_loop.py next_action`) returns converged/revise/cap_reached. On `revise` the design **producer** is re-spawned with the synthesized findings, then the round repeats. The single-critic loops use the same decide step but skip synthesize (one verdict passed as a one-element list).

**Evidence:**

```js
const synth = await synthesizeVerdicts(lensVerdicts)          // reduce M → 1
...
const decision = await criticDecision([{ pass: passed, findings: synthFindings }], round, maxRounds)  // decide
...
if (decision.action === 'converged') { ... return ... }
if (decision.action === 'cap_reached') { ... return { ok: true, residualFindings: decision.residual_findings, ... } }
// action === 'revise': re-spawn the design producer to rewrite stg(id, name) in place
```

— `.claude/workflows/qrspi-batch.js:845,859,864,868,872-887`

runPhase ordering (produce → N-select → node-check → critic → persist):

```js
const res = await agent(prompt, ...)            // produce
if (criticConfig && criticConfig.candidates > 1) { ... runDesignSelectLoop ... }   // N-select (design only, N>1)
if (criticConfig && criticConfig.nodeCheck) { ... runNodeCheck ... }               // node-check (research only)
if (criticConfig) {
  const cr = criticConfig.lenses?.length
    ? await runCriticPanelLoop(name, id, criticConfig)   // design panel
    : await runCriticLoop(name, id, criticConfig)        // single edge critic
  ...
}
const p = await persistArtifact(id, name, phaseLabel)    // persist gate
```

— `.claude/workflows/qrspi-batch.js:1243,1255-1262,1269-1276,1280-1295,1299`

**Dependencies:** Producers (`qrspi-questions`/`qrspi-research`/`qrspi-design` agents) → critic loop → `qrspi_critic_synthesize.py` (panel only) → `qrspi_critic_loop.py` (`next_action`, all loops) → persist. The `qrspi-critic` SKILL (`.claude/skills/qrspi-critic/SKILL.md`) is a standalone wrapper, NOT in the batch hand-off (the batch spawns the `qrspi-critic` agent directly).
**Implicit contracts:** Each round reduces M lens verdicts to exactly ONE authoritative verdict before the decision; the panel reuses the SAME `next_action` the single critic uses (single source of truth). On `revise` the PRODUCER (not a separate reviser agent) is re-spawned for design (batch.js:876-887). The whole critic loop runs **inside the staging window** so persist remains the single success gate (batch.js:1277-1279).

## Q3: What is the current input/output contract of the edge critic — what does it return on a passing critique, and is the `{pass, findings}` verdict shape consumed anywhere that would need to change to gate the panel behind the edge critic?

**Answer:** The edge critic returns a structured `{pass: bool, findings: string[]}` verdict (CRITIC_VERDICT_SCHEMA). On a PASS, `pass: true` and `findings: []` (empty). On FAIL, `pass: false` and a non-empty list of self-contained strings, each naming a specific upstream requirement dropped/contradicted/distorted. The verdict is the agent's **structured reply**, not a staged file. Consumers of `{pass, findings}`: (1) `runCriticLoop`/`runSliceCritic`/`runCoherenceCritic` read `verdict.pass`/`verdict.findings` directly; (2) the panel tags each lens reply and feeds it to `synthesize`; (3) `next_action`/`synthesize` (the pure Python cores) consume the canonical shape and fail-closed (a non-dict/missing-field verdict reads as NOT-passed). There is currently NO gating of the panel behind the edge critics — questions/research edge critics and the design panel run as independent per-phase loops; introducing a "run panel only if edge critic passed" gate would be NEW wiring (no existing consumer enforces it).

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

— `.claude/workflows/qrspi-batch.js:482-489`

Fail-closed coercion (the canonical shape, single source of truth):

```python
def _coerce_verdict(obj):
    if not isinstance(obj, dict):
        return {"pass": False, "findings": []}
    passed = bool(obj.get("pass", False))
    findings = obj.get("findings", [])
    if not isinstance(findings, list):
        findings = [findings] if findings else []
    return {"pass": passed, "findings": findings}
```

— `scripts/qrspi_critic_loop.py:36-48`

**Dependencies:** Producers: the `qrspi-critic` agent (`.claude/agents/qrspi-critic.md`), the 4 `qrspi-design-critic-<lens>` agents, `qrspi-coherence-critic`. Consumers: `runCriticLoop`/`runCriticPanelLoop`/`runSliceCritic`/`runCoherenceCritic` (batch.js), and the pure cores `qrspi_critic_loop.py` / `qrspi_critic_synthesize.py`.
**Implicit contracts:** PASS ⟺ empty findings (the agent prompt and schema enforce this convention but it is not validated). The verdict NEVER round-trips through a worker stdout echo — it is the schema'd agent return. `findings` items are pinned to STRINGS by CRITIC_VERDICT_SCHEMA, but `SYNTHESIZED_VERDICT_SCHEMA` (batch.js:571-590) additionally accepts `{text, lens}` objects post-synthesis — any new consumer must accept both forms.

## Q4: How is the model selected for each critic lens currently — is the lens model a single hard-coded value, or is it already parameterized in a way that would allow a cheaper lens model per the cost-reduction goal?

**Answer:** **NOT FOUND in the orchestration layer — there is NO per-agent model selection in `qrspi-batch.js` at all.** Every `agent(...)` call passes only `{ label, phase, agentType?, schema? }`; none passes a `model` option. (The 4 textual matches for "model" in the file are all the phrase "weak worker model" in comments — batch.js:184,627,647,1316 — not a model parameter.) The model is therefore determined by the harness/agent-runtime default (and possibly per-agent-type frontmatter), not by the workflow. The lens agent definitions (`.claude/agents/qrspi-design-critic-*.md`) carry frontmatter `claude: { tools: Read }` but NO `model` key. So today a cheaper lens model is **not** parameterized anywhere in the workflow or the agent files — adding it would be new. No `.qrspi/config.json` key controls a critic model (the critics block has only `enabled`/`maxRounds`/`lenses`/`candidates`/`coherence` — see config.example.json).

**Evidence:**

```bash
$ grep -nc "model" .claude/workflows/qrspi-batch.js   # 4 — all "weak worker model" comments, no model: option
```

Representative lens spawn — no model option:

```js
{ label: `critic:${id}:${name}:${lens}#${round + 1}`, phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA }
```

— `.claude/workflows/qrspi-batch.js:823`

Lens agent frontmatter (no model key):

```
---
name: qrspi-design-critic-completeness
description: ...
claude:
  tools: Read
---
```

— `.claude/agents/qrspi-design-critic-completeness.md:1-6`

The critics config block has no model knob (only enabled/maxRounds/lenses/candidates):

— `.qrspi/config.example.json` (critics → design block), and `scripts/qrspi_critics_config.py:115-155` (`resolve_design` returns only `{enabled, maxRounds, lenses, candidates}`)

**Dependencies:** `agent()` is a harness-injected global (not defined in the file; see docs/testing-dynamic-workflows.md:32-34). Model selection lives in the runtime / per-agent-type config, outside the workflow's control surface as written.
**Implicit contracts:** The agent options object is `{ label, phase, agentType, schema }` uniformly; adding `model` would be a new option the harness must honor. Lens agentType is derived by string template `qrspi-design-critic-${lens}` (batch.js:815) — a per-lens model would need to ride either that agent file's frontmatter or a new config-resolved field threaded through `criticConfig`.

## Q5: Where, if anywhere, are per-step critic outcomes (pass/fail, findings count, artifact changes, token usage) currently recorded or persisted after a design step completes?

**Answer:** Per-step critic outcomes are recorded in TWO transient places only — **never persisted to disk as structured data**: (1) the in-run progress `log(...)` stream (PASS/FAIL, per-round pass-count, findings count, converge/cap-reached); (2) the per-ticket **result `summary` string** folded into the workflow's return value. Specifically the panel returns a `summary` like `panel converged@r1 [r1:pass]` or `panel cap-reached@r2 (3 residual) [...]`, which `doDesign` splices into the result summary (`out.summary`), alongside the N-select summary and a `[critic: N residual finding(s) in PR body]` tag. The only thing that PERSISTS is cap-reached **residual findings**, which are spliced into the PR commit body (not a metrics record). `scripts/qrspi_persist.py` moves the artifact file and emits `{ok, repoRoot, src, dest, bytes, error?}` — it records bytes of the artifact, NOT critic outcomes. **There is NO token-usage capture anywhere** (no token/usage field in any envelope or result). There is no per-step critic outcome ledger, JSON log, or metrics file.

**Evidence:**

```js
log(`  ${id}: ${name} panel round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${passCount}/${lenses.length} lenses passed, ${synthFindings.length} finding(s))`}`)
summaryRounds.push(`r${round + 1}:${passed ? 'pass' : `${passCount}/${lenses.length}`}`)
...
return { ok: true, residualFindings: [], summary: `panel converged@r${round + 1} [${summaryRounds.join(' ')}]` }
```

— `.claude/workflows/qrspi-batch.js:853-854,866`

doDesign folds the summaries into the per-ticket result (the persisted-as-return-value record):

```js
if (designCritic?.selectSummary) out.summary = `${out.summary} [${designCritic.selectSummary}]`
if (designCritic?.criticSummary) out.summary = `${out.summary} [${designCritic.criticSummary}]`
if (designFindings.length) out.summary = `${out.summary} [critic: ${designFindings.length} residual finding(s) in PR body]`
```

— `.claude/workflows/qrspi-batch.js:1574-1576`

Persist envelope shape (artifact bytes only, no critic data):

```
    { ok, repoRoot, src, dest, bytes, error? }
```

— `scripts/qrspi_persist.py:28`

**Dependencies:** `runCriticPanelLoop`/`runCriticLoop` (emit log lines + summary) → `doDesign` (folds into result) → main loop `results.push(res)` (batch.js:2606) → final `return { ticketsProcessed, results, reconciliation }` (batch.js last line). `qrspi_critic_body.py` persists residual findings into the commit message only.
**Implicit contracts:** Critic outcomes are HUMAN-READABLE strings (log + summary), not machine-readable records — any metrics consumer would have to parse free-text summaries. The result object is `{ ticketId, action, newStatus?, summary, prUrl? }` (batch.js:632, 2277) — there is no slot for structured critic metrics. cap-reached residual findings are the ONLY critic output with durable on-disk persistence (PR body).

## Q6: What configuration mechanism controls whether the critic layer (or individual lenses) runs, and does it support the nested keys an `implCriticCfg.enabled`-style gate would need?

**Answer:** The mechanism is the OPTIONAL `critics` block of `.qrspi/config.json`, resolved in ONE pass by `scripts/qrspi_critics_config.py` (the "single read discipline"), surfaced to JS via `readCriticsConfig` → `parseCriticsEnvelope`. Every phase honors a uniform `enabled` flag (default **OFF** — critics are opt-in across the board); only an explicit boolean flips it. The resolver emits a per-phase envelope: `questions/research/structure/plan` → `{enabled, maxRounds}`; `design` → `{enabled, maxRounds, lenses, candidates}` (individual lenses ARE selectable via the `lenses` allow-list); `implementation` → `{enabled, maxRounds, coherence: {enabled, maxRounds}}`. **Nested keys are already fully supported** — `implementation.coherence.enabled` is the exact precedent for an `implCriticCfg.enabled`-style nested gate (`resolve_implementation` reads a nested dict and resolves a nested `enabled`/`maxRounds`). NOTE: `scripts/qrspi_config.py` (the single-key reader) is single-top-level-key only and could NOT read a nested critic key; the nested resolution lives entirely in `qrspi_critics_config.py`.

**Evidence:**

```python
def resolve_implementation(cfg):
    cfg = cfg if isinstance(cfg, dict) else {}
    coh = cfg.get("coherence") if isinstance(cfg.get("coherence"), dict) else {}
    return {
        "enabled": resolve_enabled(cfg, False),
        "maxRounds": _pos_int_or(cfg.get("maxRounds"), DEFAULT_MAX_ROUNDS),
        "coherence": {
            "enabled": resolve_enabled(coh, False),
            "maxRounds": _pos_int_or(coh.get("maxRounds"), DEFAULT_MAX_ROUNDS),
        },
    }
```

— `scripts/qrspi_critics_config.py:158-173`

Per-lens selection (the `lenses` allow-list with fallback):

```python
known = [l for l in raw_lenses if isinstance(l, str) and l in KNOWN_DESIGN_LENSES]
...
lenses = known if known else list(DEFAULT_DESIGN_LENSES)
```

— `scripts/qrspi_critics_config.py:129-141`

JS consumption — one read, indexed per phase:

```js
const implCriticCfg = (await readCriticsConfig('Implementation')).implementation
...
if (implCriticCfg.coherence.enabled) { ... }
...
if (implCriticCfg.enabled) { ... per-slice critic ... }
```

— `.claude/workflows/qrspi-batch.js:1808,1814,1894`

**Dependencies:** `.qrspi/config.json` (gitignored; example at `.qrspi/config.example.json`) → `qrspi_config.read_config` (best-effort reader, reused) → `qrspi_critics_config.resolve_critics` → `readCriticsConfig`/`parseCriticsEnvelope` (batch.js:354-377, 1154-1169) → `doDesign`/`doPlan`/`doImplementation`. JS fallback mirror is `DEFAULT_CRITIC_PHASES` (batch.js:612-619).
**Implicit contracts:** `enabled` default is uniformly OFF; only an explicit boolean overrides (non-boolean ⇒ default). The resolver is best-effort: it NEVER throws; on any failure JS falls back to `DEFAULT_CRITIC_PHASES` (batch.js:374-377). The JS default mirror MUST be kept in lockstep with the Python resolver's defaults (verified by `qrspi_critics_config_test.py`). config.json lives in the MAIN checkout (engineCmd-addressed), shared by all worktrees.

## Q7: What happens to the design step when a critic lens returns findings (a non-passing verdict) — is there an existing skip-on-failure / re-run / accumulate-residual path, and how is a failed Linear or persistence write during that path handled?

**Answer:** A non-passing verdict triggers the **produce→critique→revise loop**: `next_action` returns `revise` (rounds remain) or `cap_reached` (final round). On `revise`, the design **producer** is re-spawned in place to rewrite `stg(id,'design')` addressing the synthesized findings, then the panel re-critiques next round. On `cap_reached`, the loop returns `ok: true` with `residualFindings` (ship-with-disclosure) which are AGGREGATED across questions/research/design and spliced into the Design PR body via `criticBodyStep` → `qrspi_critic_body.py`. Distinct failure modes: a critic/synthesize/decision **spawn** failure (null result) returns `ok: false`, which makes `runPhase` return false → `failTicket(t)` (the whole ticket stops, nothing persists). For the **implementation** precedent (`doImplementation`), a per-slice critic spawn failure maps to `skip(...)`; cap-reached accumulates into `perSliceFindings[s.n]`. **Linear/persistence writes are NOT in the critic path** — the critic loop runs entirely in the pre-persist staging window, so a critic outcome never triggers a Linear or persist write directly; the persist gate runs AFTER the loop, and Linear projection is BEST-EFFORT in the finalize worker (a failed Linear write is a WARN, still returns ok:true).

**Evidence:**

```python
def next_action(verdicts, round, max_rounds):
    latest = _coerce_verdict(verdicts[-1]) if isinstance(verdicts, list) and verdicts else {"pass": False, "findings": []}
    if latest["pass"]:
        return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:82-113`

Slice-critic skip-on-failure / accumulate precedent (doImplementation):

```js
const sc = await runSliceCritic(t, r, wd, s.n, dec, s.planSlice, s.structureSlice, implCriticCfg.maxRounds)
if (!sc.ok) {
  return skip(t, r.decision, `Slice ${s.n} critic spawn failed; stopped without shipping.`)
}
perSliceFindings[s.n] = sc.residualFindings
```

— `.claude/workflows/qrspi-batch.js:1905-1909`

Best-effort Linear projection in finalize (a failed write is a WARN):

```
3. BEST-EFFORT project Linear → "Design Review" (a failed Linear write is a WARN, not a failure — still return ok:true with the PR created).
```

— `.claude/workflows/qrspi-batch.js:1565`

**Dependencies:** `next_action` (`qrspi_critic_loop.py`) decides; the producer re-spawn (batch.js:876-887) executes revise; `criticBodyStep` (batch.js:1221-1225) + `qrspi_critic_body.py` persist residual findings into the PR commit body. `failTicket`/`skip` are the ticket-level stop paths.
**Implicit contracts:** Fail-closed everywhere — a missing/garbled verdict reads NOT-passed (never silently converges). A spawn failure stops the ticket (no fabrication / no silent ship). cap-reached is "ship with disclosure" (artifact still persists; findings surfaced in PR body). The critic loop is firewalled from Linear/persist — persist is the single success gate AFTER the loop, Linear is best-effort and post-persist.

## Q8: How does the layer behave if the shared digest (once introduced) is empty, truncated, or fails to generate — does any current code assume each lens always receives the full research.md?

**Answer:** There is no shared digest today (Q1), so this concerns the assumptions any digest would have to satisfy. Yes — current code **assumes each lens receives the full research.md by path** and that the file is present and non-empty: the panel passes `RESEARCH_PATH = ${researchPath}` unconditionally and instructs every lens to "Read all four paths." There is NO empty/truncation guard on lens INPUTS — the only non-empty guards in the design path apply to OUTPUTS (staged candidate files, the winner copy, the graft result: `candidatesNonEmpty`, `stageDesignWinner`, `graftDesignWinner`, all via `test -s`). The closest precedent for an input-presence guard is `doImplementation`'s coherence pass, which fail-closed `skip(...)`s when any of its six inputs is missing/empty (using the resolver's `existing` flags). So a digest-generation step would need to ADD a non-empty/availability guard analogous to those output guards or the coherence input guard; nothing today validates that a lens input is non-empty before fan-out.

**Evidence:**

```js
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}
Read all four paths and judge DESIGN_PATH through your lens.
```

— `.claude/workflows/qrspi-batch.js:820-822` (no presence/non-empty check on the inputs)

Output non-empty guard precedent (`test -s`):

```js
const test = paths.map(p => `test -s ${p}`).join(' && ')
...
${test} && printf '{"ok":true}\\n' || printf '{"ok":false}\\n'
```

— `.claude/workflows/qrspi-batch.js:1131,1136`

Coherence input fail-closed guard precedent:

```js
const missing = ['questions', 'research', 'design', 'structure', 'plan'].filter(k => !ex[k])
if (!r.ticketContentPath) missing.push('ticket')
if (missing.length) {
  log(`  ${t.id}: coherence pass enabled but inputs missing/empty [${missing.join(', ')}] — skipping ticket`)
  return skip(t, r.decision, `Coherence inputs missing/empty: ${missing.join(', ')}.`)
}
```

— `.claude/workflows/qrspi-batch.js:1830-1836`

**Dependencies:** `runCriticPanelLoop` (assumes input present) ← upstream `runPhase` produce + persist of research.md (the only guarantee research.md exists is that the research phase's own persist gate succeeded earlier in `doDesign`). The resolver `existing` flags (batch.js:1829) are the available presence-check primitive.
**Implicit contracts:** Lens inputs are assumed present and complete by construction (an earlier phase's persist gate). The harness convention is to guard generated OUTPUTS with `test -s` and abort fail-closed, and to guard required INPUTS via resolver `existing` flags + `skip()`. A digest step that produces an input would, to match precedent, need its own `test -s` non-empty gate that fails the phase rather than letting a lens read an empty digest.

## Q9: What is the current behavior when subagent token consumption is large (the ~749K-token first attempt) — is there any budget cap, timeout, or abort threshold on a critic step, or does it run unbounded?

**Answer:** There is **NO budget cap, token threshold, or timeout on any critic step** (or any agent call) in the workflow. The only bound on a critic loop is the **round cap** (`maxRounds`, default 2) — a count of iterations, not of tokens or wall-clock. Each round spawns the lenses in parallel (4 agents for the default panel) with no per-agent or per-round token/time limit. `agent(...)` calls never pass a `model`, `maxTokens`, `budget`, or `timeout` option (grep confirms: zero such options; the harness exposes an injected `budget` global per docs but the workflow never references it). The N-select stage adds N more produce spawns + 1 judge per design step when enabled, and each lens re-reads the full research.md every round (Q1) — all unbounded by anything except the round cap. So a large-context critic step runs to completion (or fails on the harness's own runtime limits, which are outside this file's control).

**Evidence:**

```bash
$ grep -nc "budget\|timeout\|maxTokens\|tokenLimit" .claude/workflows/qrspi-batch.js   # 0 (after excluding the 4 "model" comment hits)
```

The only loop bound is the round cap:

```js
async function runCriticPanelLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  ...
  for (let round = 0; round < maxRounds; round++) { ... }
```

— `.claude/workflows/qrspi-batch.js:801-810`

`maxRounds` default = 2 (the resolver default):

```python
DEFAULT_MAX_ROUNDS = 2
```

— `scripts/qrspi_critics_config.py:58`

**Dependencies:** `maxRounds` resolved by `qrspi_critics_config.py` → `criticConfig.maxRounds`. The injected `budget` global is documented (docs/testing-dynamic-workflows.md:34) but unused by the workflow.
**Implicit contracts:** The ONLY convergence bound is iteration count (`maxRounds`); cost/latency are unmanaged. Each lens re-reads the full inputs each round (no caching/digest), so per-round token cost scales with input size × lens count × rounds. Any token-budget/abort-threshold feature would be entirely new — there is no existing seam (no per-agent options threading, no usage capture per Q5) to hook it onto.

## Q10: What is the existing pattern for a "teeth" / behavioral eval that asserts a critic fails on a flawed input, and where would a fixture of a deliberately-flawed design live relative to the current test harness?

**Answer:** Two distinct harnesses exist, and the "teeth" pattern lives in DIFFERENT places for each. (1) The **functional** test harness (`scripts/run_tests.py` over `scripts/*_test.py`, stdlib-only) tests the PURE DECISION cores deterministically — `qrspi_critic_loop_test.py` asserts that a fail/garbled/empty verdict yields revise/cap_reached (NOT converged), and `qrspi_critic_synthesize_test.py` asserts any single failing lens fails the round. This is "teeth on the reducer," NOT teeth on the LLM critic itself. (2) The **eval** harness (`evals/` + `scripts/run_eval.py`) is the place for behavioral "critic fails on a flawed design" evals AND ALREADY HAS deliberately-flawed fixtures — `evals/fixtures/structure_broken_contract.md`, `plan_broken_contract_slice1.md`, `worktree_session_broken_contract.md`, plus sparse research (`research_multi_tenancy_sparse.md`). HOWEVER per CLAUDE.md + project memory the `evals/`+`run_eval.py` harness is a **non-functional placeholder** — so there is currently no RUNNING behavioral teeth eval; the fixture convention is `evals/fixtures/<artifact>_<scenario>.md` with golden outputs under `evals/golden/`.

**Evidence:**

```python
# Covers (...):
#   - pass-first-round  ⇒ converged on round 0, no revise (AC4)
#   - fail→revise→pass  ⇒ revise then converged (AC2)
#   - fail at cap        ⇒ cap_reached surfacing residual findings (AC2, AC4)
#   - malformed/empty/garbage verdict ⇒ fail closed to NOT-passed, never raises (Q11)
```

— `scripts/qrspi_critic_loop_test.py:6-12`

Deliberately-flawed fixtures already present:

```
evals/fixtures/structure_broken_contract.md
evals/fixtures/plan_broken_contract_slice1.md
evals/fixtures/worktree_session_broken_contract.md
evals/fixtures/research_multi_tenancy_sparse.md
evals/golden/.gitkeep
```

— `evals/fixtures/` directory listing

The aggregating functional runner (the regression gate):

— `scripts/run_tests.py` (runs every `scripts/*_test.py` as a subprocess; CI gate at `.github/workflows/tests.yml`)

**Dependencies:** Functional teeth: `qrspi_critic_loop_test.py` / `qrspi_critic_synthesize_test.py` → `run_tests.py` → CI. Behavioral teeth: `evals/suite.json` + `evals/fixtures/*` + `evals/golden/*` → `scripts/run_eval.py` (placeholder, non-functional).
**Implicit contracts:** Deterministic logic is tested with stdlib assert-based `_test.py` siblings (no third-party deps, no runner) and gated in CI. LLM-behavioral teeth belong in `evals/` (fixture + golden), NOT the per-PR functional gate. A flawed-design fixture would conventionally be `evals/fixtures/design_<scenario>_broken.md` with an expected `{pass:false, findings:[...]}` golden — but the runner that would execute it is a placeholder.
**Inconsistency note:** `evals/fixtures/README.md` and `evals/suite.json` present an operational-looking harness, but CLAUDE.md and project memory both state it is a non-functional placeholder (see Inconsistencies).

## Q11: How are critic-layer behaviors currently tested given that `qrspi-batch.js` is documented as harness-coupled and not unit-testable in isolation — what is the JS↔Python contract-fixture seam that a critic change would be verified against?

**Answer:** Per `docs/testing-dynamic-workflows.md`, the strategy is "Functional Core / Imperative Shell": ALL deterministic critic logic lives in tested Python (`qrspi_critic_loop.py`, `qrspi_critic_synthesize.py`, `qrspi_critics_config.py`, `qrspi_design_select.py`, `qrspi_slice_critic.py`), each with a `_test.py` sibling; `qrspi-batch.js` is the untestable shell that only shells out and never re-derives logic. The doc identifies the JS↔Python **contract-fixture seam** as the strongest repo-specific fit — capture real Python-script output envelopes as committed fixtures and assert BOTH sides (Python produces them, JS parsers consume them). CRITICAL FINDING: this contract-fixture seam is **described as RECOMMENDED but NOT YET IMPLEMENTED** — the doc tracks it as a QRSPI ticket, and there are currently NO contract-fixture files and NO JS-side tests (the workflow is harness-coupled: top-level `return`, injected globals `agent()/parallel()/phase()/log()/budget`, no import support — confirmed empirically). So today a critic change is verified ONLY by the Python `_test.py` cores + the `node --check`-style syntax gate; the JS parsers (`parseCriticsEnvelope`, etc.) have no direct test, only their Python producers do.

**Evidence:**

```
3. (Strongest repo-specific fit) Contract / golden fixtures at the JS↔Python
   seam. Capture real Python-script output envelopes as committed fixtures, and
   assert both sides against them ... *(Tracked as a QRSPI ticket.)*
```

— `docs/testing-dynamic-workflows.md:124-131`

Why the JS is not unit-testable (the seam constraint):

```
- Top-level `return` (last line) and top-level `await` throughout the driver.
- References harness-injected globals that do not exist in plain Node:
  `agent()`, `parallel()`, `pipeline()`, `phase()`, `log()`, `args`, `budget`, `workflow()`.
```

— `docs/testing-dynamic-workflows.md:32-34`

Existing Python core tests that DO cover critic logic: `scripts/qrspi_critic_loop_test.py`, `scripts/qrspi_critic_synthesize_test.py`, `scripts/qrspi_critics_config_test.py`, `scripts/qrspi_design_select_test.py`, `scripts/qrspi_slice_critic_test.py`, `scripts/qrspi_critic_body_test.py` (all run by `scripts/run_tests.py`).

**Dependencies:** `run_tests.py` → `scripts/*_test.py` → CI (`.github/workflows/tests.yml`). The syntax gate is `scripts/check_workflows.js` (+ `check_workflows_test.py`). The (proposed, unbuilt) contract seam would bridge `qrspi_critics_config.py` output ↔ `parseCriticsEnvelope`.
**Implicit contracts:** New deterministic critic logic MUST be a `scripts/*.py` helper with a `_test.py` sibling, never inlined as nontrivial JS (the written convention). The JS parsers are a "thin second validation layer over an already-tested core." A critic change is verified by (a) extending the Python core test, (b) the syntax gate, and (c) manual end-to-end — NOT by any JS unit test or contract fixture (neither exists yet).

## Q12: What logging, counters, or run-summary output exists today that could carry critic base-rate metrics (pass/fail counts, findings counts, per-lens token usage), and what format does the batch run currently emit per ticket?

**Answer:** Two output channels exist, both free-text / unstructured for critic data. (1) **Progress logs** (`log(...)`, an injected global): per-round PASS/FAIL with lens pass-count and findings count, converge/cap-reached lines, per-round summary tokens like `r1:pass` / `r2:2/4`. (2) **Per-ticket result object** pushed to `results` and returned: shape `{ ticketId, action, newStatus?, summary, prUrl? }` — the critic info rides the free-text `summary` (e.g. `... [panel cap-reached@r2 (3 residual) [r1:1/4 r2:2/4]] [critic: 3 residual finding(s) in PR body]`). The whole run returns `{ ticketsProcessed, results, reconciliation }`. **There are NO machine-readable counters** — no pass/fail count fields, no findings-count fields, and absolutely NO per-lens token usage (token usage is never captured anywhere, Q5/Q9). To add critic base-rate metrics, a new structured field on the result object (and a usage capture seam, which does not exist) would be required.

**Evidence:**

```js
const summary = `N-select N=${n} winner=${sel.winner}(${winner.framing}) scores[${scoreParts.join(' ')}] ${graftSummary}`
```

— `.claude/workflows/qrspi-batch.js:1122` (representative free-text summary)

Per-ticket result shapes (no structured critic counters):

```js
return { ticketId: t.id, action: decision.action, summary: note }        // skip()
return { ticketId: t.id, action, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }   // doX finalize
```

— `.claude/workflows/qrspi-batch.js:632, 2277`

Whole-run output:

```js
return { ticketsProcessed: results.length, results, reconciliation }
```

— `.claude/workflows/qrspi-batch.js` (final line)

**Dependencies:** `log()` (injected global, sink controlled by harness) for progress; `results.push(res)` (batch.js:2606) → final return for the structured-ish record. The panel/loop `summary` strings (batch.js:866,870,896,1122) and `doDesign` folding (batch.js:1574-1576) are the critic-metric carriers today.
**Implicit contracts:** Critic metrics are human-readable strings, not parseable counters; the per-round summary token grammar is `r<N>:pass` or `r<N>:<passCount>/<lensCount>`. The result object has a fixed small key set with no metrics slot. Any base-rate-metrics feature must add structured fields (and a token-usage seam, which is entirely absent — there is no `tokens`/`usage` field in any envelope, schema, or result in the workflow).

---

## Discovered Patterns

- **Functional Core / Imperative Shell is the load-bearing architecture.** EVERY deterministic critic decision is a pure stdlib-only Python module (`qrspi_critic_loop.py` `next_action`, `qrspi_critic_synthesize.py` `synthesize`, `qrspi_critics_config.py` `resolve_*`, `qrspi_design_select.py`, `qrspi_slice_critic.py`) with a `_test.py` sibling; `qrspi-batch.js` only shells out via worker agents and "never re-derives decision logic." The JS sandbox cannot run Python, so each pure module is invoked through a verbatim-one-command worker that pipes JSON on stdin and parses the JSON stdout (`criticDecision`, `synthesizeVerdicts`, `selectDesignWinner`, `readCriticsConfig`).
- **Fail-closed is universal.** Every verdict path coerces a missing/garbled/empty reply to NOT-passed (`_coerce_verdict`); a spawn failure (`null`) stops the ticket; an empty/all-unknown lens set falls back to the full default four; the config resolver never throws and falls back to all-defaults. A garbled critic can never silently mark an artifact converged.
- **All cross-agent data is passed by absolute PATH, never inlined content** (the "fragile text never round-trips through worker stdout" rule). Inputs to lenses, producers, and revisers are file paths the agent Reads itself; fragile JSON (verdicts, findings) is piped on stdin to the Python cores.
- **Critic loops run inside the pre-persist staging window**, so `qrspi_persist.py` remains the SINGLE per-phase success gate; the disabled-critic path is byte-for-byte unchanged (guarded by `if (criticConfig)`).
- **Critic config is uniformly opt-in (default OFF) across all six phases**, resolved in ONE read (the "single read discipline"); `implementation.coherence` is the existing nested-key precedent.
- **Output non-empty gating uses `test -s` worker commands** (`candidatesNonEmpty`, `stageDesignWinner`, `graftDesignWinner`); required-input gating uses the resolver's `existing` flags + `skip()` (coherence pass).
- **The revise step re-spawns the PRODUCER agent**, not a dedicated reviser agent type — the producer already knows how to write the artifact; findings are the only new input (single + panel loops). The per-slice critic is the exception (it routes to `qrspi_revise_amend.py`).

## Inconsistencies

- **Eval harness: documented placeholder vs. operational-looking artifacts.** `evals/suite.json`, `evals/graphite-evals.json`, `evals/fixtures/README.md`, and `scripts/run_eval.py` present a full eval harness with deliberately-flawed fixtures (`*_broken_contract.md`, `*_sparse.md`) and a `golden/` dir — but CLAUDE.md and the project memory both state the `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** ("verify pure logic with the unit tests and orchestration changes with manual end-to-end runs"). A "teeth" eval that runs a critic against a flawed-design fixture has fixtures and a runner present but is NOT actually wired to execute.
- **Contract-fixture seam: recommended but absent.** `docs/testing-dynamic-workflows.md` names the JS↔Python contract-fixture seam as the "strongest repo-specific fit" and "Tracked as a QRSPI ticket," but no contract-fixture files and no JS-side parser tests exist yet — the JS parsers (`parseCriticsEnvelope`, `extractJson*`) are currently UNtested except indirectly via their Python producers.
- **No token/cost instrumentation despite a cost-reduction premise.** The questions reference a ~749K-token attempt and per-lens token usage, but the codebase captures token usage NOWHERE (no `tokens`/`usage`/`budget` field in any schema, envelope, result, or log line); the harness exposes an injected `budget` global that the workflow never references. Per-lens model selection is likewise absent from the workflow (`agent()` never passes `model`). Any cost-reduction or budget-cap feature starts from zero instrumentation and zero per-agent model/budget threading.
- **Two senses of "critic" metrics surface.** The pure-core `_test.py` files give deterministic "teeth" on the REDUCER (a failing verdict must not converge), which is sometimes conflated with behavioral teeth on the LLM critic itself (does the critic detect a flawed design?). Only the former is tested today; the latter has fixtures but no running harness.
