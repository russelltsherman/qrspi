# Research — Codebase Map

**Questions source:** questions.md @ .qrspi/RUS-82/questions.md
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft

All paths below are relative to `REPO_ROOT = /workspaces/qrspi/.worktrees/RUS-82`.

## Q1: What inputs does `runCriticPanelLoop` currently assemble and thread into each design-critic lens spawn prompt (design.md, ticket, research.md, questions.md, and any shared digest), and at what point would a `CODEBASE_PATH` (worktree/repo root) value be available to splice in?

**Answer:** `runCriticPanelLoop(name, id, criticConfig)` (signature is `name`/`id`/`criticConfig` only — no `r`/`wd`/`repoRoot` argument) threads **four** path lines into every lens prompt, plus an optional fifth `DIGEST_PATH` line:

- `DESIGN_PATH` = `artifactPath` = `stg(id, name)` (the staged design at `/tmp/phase-stage/<id>/<name>.md`)
- `TICKET_CONTENT_PATH` = `criticConfig.ticketContentPath`
- `RESEARCH_PATH` = `criticConfig.upstreamPath` (research.md)
- `QUESTIONS_PATH` = `criticConfig.questionsPath`
- `DIGEST_PATH` (conditional) = `/tmp/phase-stage/<id>/research-digest.md` — only appended (`digestLine`) when `digestPath` is non-null (digest lever ON).

There is **no** repo/worktree root in scope inside `runCriticPanelLoop`. The function comments explicitly note `r`/`repoRoot` is NOT in scope (it takes only `name`/`id`/`criticConfig`). The worktree root (`wd = r.worktreeDir`) is in scope at the **call site** `doDesign(t, r)`, where `criticConfig` (the `designCritic` object) is fully assembled. A `CODEBASE_PATH` would therefore be plumbed by (a) adding a field to the `designCritic` object in `doDesign` (where `wd` is available) and (b) splicing a prompt line in `runCriticPanelLoop`, mirroring how `ticketContentPath`/`questionsPath` are already passed.

**Evidence:**

```js
const verdict = await agent(
  `You are the ${lens} lens of the qrspi design-phase critic panel for ${id}, round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}${digestLine}
Read all four paths and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`,
  agentOpts
)
```

— `.claude/workflows/qrspi-batch.js:894-902`

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

— `.claude/workflows/qrspi-batch.js:1732-1742` (call site in `doDesign`, `wd` in scope)

**Dependencies:** `runCriticPanelLoop` is called by `runPhase` (`.claude/workflows/qrspi-batch.js:1493-1495`); `criticConfig` is built in `doDesign`; `stg`/`art`/`tpl` helpers at `:646-652`.
**Implicit contracts:** Every lens receives the identical 4-path input set; the prompt asserts "Read all four paths" (hard-coded "four" — adding a 5th `CODEBASE_PATH` line would make that count wrong). Adding a path requires touching BOTH the `doDesign` config object and the prompt template.

## Q2: How is the shared "digest" (from RUS-78) constructed and passed to the lenses today, and what is the mechanism by which an individual lens could opt out of the digest in favor of full research + source?

**Answer:** The digest is built **once per step** before the round loop. When `criticConfig.digest.enabled` is true, `runCriticPanelLoop` sets `digestPath = /tmp/phase-stage/<id>/research-digest.md` and calls `buildResearchDigest(id, researchPath, digestPath)`, which spawns a worker running the tested `scripts/qrspi_research_digest.py` and guards the output with `test -s` (fail-closed: empty/missing digest aborts the ticket). When ON, each lens prompt gets the extra `DIGEST_PATH = ...` line (`digestLine`); when OFF (`digestPath` null), no `DIGEST_PATH` line is added and lenses fall back to `RESEARCH_PATH`.

The opt-out mechanism is **per-lens-agent, in the prompt instructions, not per-call**: each lens agent's spec says "When [`DIGEST_PATH`] present, Read `DIGEST_PATH` in place of `RESEARCH_PATH`; when absent, Read `RESEARCH_PATH`." There is currently **no per-lens flag in the loop** to thread the digest to some lenses but not others — `digestLine` is computed once and applied uniformly to every lens in the `lenses.map(...)`. A lens that needed full research + source would either need its agent prompt rewritten to ignore `DIGEST_PATH`, or the loop would need a per-lens conditional on `digestLine`.

**Evidence:**

```js
let digestPath = null
if (criticConfig.digest && criticConfig.digest.enabled) {
  digestPath = `/tmp/phase-stage/${id}/research-digest.md`
  const built = await buildResearchDigest(id, researchPath, digestPath)
  if (!built) { ...return { ok: false, ... } }
}
...
const digestLine = digestPath ? `\nDIGEST_PATH = ${digestPath}` : ''
```

— `.claude/workflows/qrspi-batch.js:863-873, 890`

```
- `DIGEST_PATH` — OPTIONAL. ... When present, Read `DIGEST_PATH` in place of `RESEARCH_PATH`; when absent, Read `RESEARCH_PATH` as usual.
```

— `.claude/agents/qrspi-design-critic-completeness.md:15` (identical text in all four lens specs)

**Dependencies:** `buildResearchDigest` (`.claude/workflows/qrspi-batch.js:1024-1037`) → worker → `scripts/qrspi_research_digest.py`; digest gate resolved by `resolve_design` in `scripts/qrspi_critics_config.py:169-170` (`digest: {"enabled": ...}`, default OFF).
**Implicit contracts:** The lens agent — not the loop — decides which of `DIGEST_PATH`/`RESEARCH_PATH` to read. The digest is built ONCE and reused across all revise rounds (only the staged design changes between rounds). Note: this is RUS-77 cost-lever code (comments say RUS-77; the question attributes it to RUS-78 — both ticket numbers appear in the digest/teeth lineage).

## Q3: What is the exact `CRITIC_VERDICT_SCHEMA` shape (`{pass, findings}`) that every design-critic lens must emit, and where is it defined and consumed?

**Answer:** `CRITIC_VERDICT_SCHEMA` is a JSON-schema object requiring `pass` (boolean) and `findings` (array of strings). It is defined once in `qrspi-batch.js` and passed as the `schema` option on every lens `agent()` spawn (and the single-critic, coherence-critic, and slice-critic spawns). The Python side's canonical verdict is the same `{pass, findings}` shape, coerced fail-closed by `_coerce_verdict`/`parse_critic_verdict` in `qrspi_critic_loop.py`.

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

— `.claude/workflows/qrspi-batch.js:502-509`

Consumed at: lens panel spawn `agentOpts` (`:892`), single-critic spawn (`:759`), coherence-critic (`:1904`), slice-critic (`:1960`). The panel's per-round reduction emits `SYNTHESIZED_VERDICT_SCHEMA` (`:591-610`) which additionally allows findings as `{text, lens}` objects.

**Dependencies:** Schema is the runner-boundary validator; the Python `_coerce_verdict` (`scripts/qrspi_critic_loop.py:36-48`) is the fail-closed backstop with the same field contract.
**Implicit contracts:** `pass:true` ⇒ findings SHOULD be empty; `pass:false` ⇒ findings MUST be non-empty (enforced by lens prompts, not the schema). At the JS boundary `findings` items are pinned to strings; the synthesized verdict broadens to allow `{text, lens}` objects.

## Q4: What frontmatter fields (notably `tools` and any model/seam key like `lensModel`) do the existing four design-critic agents declare, and what is the exact format for granting `Read` + `Grep` and a per-lens model override?

**Answer:** All four lens agent files declare identical frontmatter: `name`, `description`, and a `claude:` block with `tools: Read` (Read ONLY — no Grep, no Glob, no Bash). There is **no model key** in any lens agent's frontmatter. The frontmatter format is YAML with a nested `claude:` map.

To grant `Read` + `Grep`, the format (proven by `qrspi-research.md`) is a comma-separated list: `tools: Read, Grep` (or `Read, Write, Glob, Grep`).

The per-lens **model override** is NOT in the agent frontmatter — it is a runtime `agent()` option `model` set from `criticConfig.lensModel` in `runCriticPanelLoop`. The loop reads `lensModel` (non-empty string only) and rides it as `agentOpts.model`. The code comment flags this as a **speculative/possibly-inert seam**: "there is no evidence the harness honors an agent() `model` option, so this lever may be inert."

**Evidence:**

```
---
name: qrspi-design-critic-completeness
description: Internal QRSPI workflow agent — one lens of the design-phase critic panel (COMPLETENESS). ...
claude:
  tools: Read
---
```

— `.claude/agents/qrspi-design-critic-completeness.md:1-6` (all four lenses identical: `simplicity:1-6`, `edge-alignment:1-6`, `internal-consistency:1-6`)

```
claude:
  tools: Read, Write, Glob, Grep
```

— `.claude/agents/qrspi-research.md:4-5` (the Read+Grep grant format)

```js
const lensModel = typeof criticConfig.lensModel === 'string' && criticConfig.lensModel ? criticConfig.lensModel : null
...
const agentOpts = { label: ..., phase: 'Critic', agentType, schema: CRITIC_VERDICT_SCHEMA }
if (lensModel) agentOpts.model = lensModel
```

— `.claude/workflows/qrspi-batch.js:879, 892-893`

**Dependencies:** `lensModel` resolved by `resolve_design` in `scripts/qrspi_critics_config.py:188-190` (key OMITTED entirely when not a non-empty string; default ABSENT).
**Implicit contracts:** Lenses are currently Read-only (the rules say "Do not explore the codebase" — see Q9). The `model` agent option is unproven; the existing tools format is a flat comma list under `claude.tools`.

## Q5: Where is the default design lens set (`DEFAULT_DESIGN_LENSES`) defined, and how does the config resolver's whitelist (`KNOWN_DESIGN_LENSES`) gate which lenses `critics.design.lenses` may activate?

**Answer:** `DEFAULT_DESIGN_LENSES = ['completeness', 'internal-consistency', 'edge-alignment', 'simplicity']` is defined in **two** places that must stay in lockstep:
1. `.claude/workflows/qrspi-batch.js:617` (JS-side fallback baked into `DEFAULT_CRITIC_PHASES`).
2. `scripts/qrspi_critics_config.py:64` (the tested resolver, source of truth).

`KNOWN_DESIGN_LENSES` is defined ONLY in Python as `set(DEFAULT_DESIGN_LENSES)` (`scripts/qrspi_critics_config.py:65`). The resolver `resolve_design` filters config-supplied `lenses`: it keeps only string entries present in `KNOWN_DESIGN_LENSES` (`known`), drops the rest (`unknown`) with a warning, and — critically — if the resolved `known` set is empty (all-unknown), it falls back to the full default four rather than disabling the panel. So a NEW lens id (e.g. a validity lens) would be **dropped as unknown** unless it is added to `DEFAULT_DESIGN_LENSES` (which feeds `KNOWN_DESIGN_LENSES`).

**Evidence:**

```python
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES)
...
known = [l for l in raw_lenses if isinstance(l, str) and l in KNOWN_DESIGN_LENSES]
unknown = [l for l in raw_lenses if not (isinstance(l, str) and l in KNOWN_DESIGN_LENSES)]
if unknown:
    warnings.append("dropping unknown design-critic lens(es) [" + ...)
lenses = known if known else list(DEFAULT_DESIGN_LENSES)
```

— `scripts/qrspi_critics_config.py:64-65, 140-152`

**Dependencies:** JS `DEFAULT_DESIGN_LENSES` (`.claude/workflows/qrspi-batch.js:617`) → `DEFAULT_CRITIC_PHASES.design.lenses` (`:638`). Each lens id maps to agentType `qrspi-design-critic-<id>` at the spawn (`:886`), so adding a lens id requires a matching agent file to exist.
**Implicit contracts:** Adding a lens requires THREE coordinated edits: (1) the agent file `.claude/agents/qrspi-design-critic-<id>.md` must exist, (2) `DEFAULT_DESIGN_LENSES` in `qrspi_critics_config.py` (whitelist source), (3) `DEFAULT_DESIGN_LENSES` in `qrspi-batch.js` (JS fallback). A lens added to config but not the whitelist is silently dropped.

## Q6: How does `scripts/qrspi_critic_synthesize.py` AND-reduce per-lens verdicts, and how does it currently determine the set of expected lenses for a round (so an added lens is counted in unanimity)?

**Answer:** `synthesize(verdicts)` AND-reduces: `pass` is True ONLY if the verdict list is non-empty AND **every** coerced lens passed (`all_passed` starts True, any non-passing lens flips it False). `findings` is the exact-string-deduped UNION of all lenses' findings in first-seen order, optionally wrapped as `{text, lens}` when a lens id is present.

Critically, it does **NOT** know an "expected set" of lenses — it reduces over **whatever list it is handed**. The expected-lens membership is determined upstream in JS: `runCriticPanelLoop` builds `lensVerdicts` from `replies.map(...)` over `criticConfig.lenses`, and a **failed-spawn lens aborts the ticket** (`failedLens` guard) BEFORE synthesize is called. So unanimity is over the exact lens list passed; an added lens is automatically counted because it is in `criticConfig.lenses` and thus in the verdict list. An empty list reads as NOT-passed (fail closed). There is no count/quorum check inside synthesize.

**Evidence:**

```python
if not isinstance(verdicts, list) or not verdicts:
    return {"pass": False, "findings": []}
all_passed = True
...
for entry in verdicts:
    coerced = _coerce_lens(entry)
    if not coerced["pass"]:
        all_passed = False
    ...
return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:94-118`

```js
const failedLens = replies.find(rp => !rp || rp.verdict === null)
if (failedLens) { ...return { ok: false, ... } }   // missing lens aborts, not silent-pass
const lensVerdicts = replies.map(rp => ({ pass: ..., findings: ..., lens: rp.lens }))
const synth = await synthesizeVerdicts(lensVerdicts)
```

— `.claude/workflows/qrspi-batch.js:909-933`

**Dependencies:** `_coerce_lens` → `_coerce_verdict`/`parse_critic_verdict` from `qrspi_critic_loop.py` (`scripts/qrspi_critic_synthesize.py:39-53`). Caller `synthesizeVerdicts` worker (`.claude/workflows/qrspi-batch.js:997-1011`).
**Implicit contracts:** "No lens is privileged" — unanimity (AND) over the supplied set. The expected-lens count lives entirely in the JS fan-out (`criticConfig.lenses`); synthesize is set-agnostic. A lens that returns `pass:false` with no findings still flips `all_passed` (its prompt is supposed to carry findings, but synthesize does not enforce it).

## Q7: How does the panel loop behave when unanimity is never reached — what does `maxRounds` / `cap_reached` do, and how does a perpetually-dissenting lens currently surface (ship via `cap_reached` vs block)?

**Answer:** The loop runs at most `maxRounds` (default 2). Each round, the synthesized verdict is handed to `criticDecision([{pass, findings}], round, maxRounds)` → `next_action`. `next_action` returns `cap_reached` when the latest verdict did NOT pass AND `round + 1 >= max_rounds`. On `cap_reached`, `runCriticPanelLoop` returns `{ ok: true, residualFindings: decision.residual_findings, ... }` — i.e. it **SHIPS** (ok:true) and carries the residual findings into the PR body. A perpetually-dissenting lens therefore does **not block**: after maxRounds it ships via `cap_reached` with its findings surfaced as PR-body residuals. The only blocking outcomes are abort paths (`ok:false`): a lens that fails to spawn, a synthesize failure, a decision-compute failure, or a reviser failure — all stop the ticket. A lens that simply keeps returning `pass:false` is NOT a block; it caps out and ships.

**Evidence:**

```python
if int(round) + 1 >= int(max_rounds):
    return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:110-113`

```js
if (decision.action === 'cap_reached') {
  log(`  ${id}: ${name} panel CAP-REACHED at round ${round + 1} — ${decision.residual_findings.length} residual finding(s) carried to PR body`)
  const metrics = await recordCriticMetrics(id, name, metricRounds, 'cap_reached')
  return { ok: true, residualFindings: decision.residual_findings, summary: ..., metrics }
}
```

— `.claude/workflows/qrspi-batch.js:959-963`

**Dependencies:** `criticDecision` worker → `scripts/qrspi_critic_loop.py` `next_action`; residual findings spliced into the Design PR body downstream of `doDesign` (`criticConfig.residualFindings`, `.claude/workflows/qrspi-batch.js:1502`).
**Implicit contracts:** A non-converging critic is non-blocking by design (it surfaces findings, never gates the PR). A dissenting lens cannot stop the ticket; only an infrastructure failure (null/abort) can. This is the existing "critics ship via cap_reached" behavior.

## Q8: How does `runCriticPanelLoop` handle a lens that returns a malformed verdict, times out, or emits no `{pass, findings}` — does a missing verdict count as fail, pass, or abort?

**Answer:** Two distinct failure modes:

1. **Null verdict (spawn failed / timed out / no reply):** `replies.find(rp => !rp || rp.verdict === null)` finds it; the loop logs and returns `{ ok: false }` — **ABORTS the ticket** (it does NOT treat a missing lens as a pass). Partial replies that did arrive are still recorded to the metrics ledger as an `aborted` step.

2. **Malformed-but-present verdict (wrong shape):** First, the `agent()` `schema: CRITIC_VERDICT_SCHEMA` validates at the runner boundary (a schema-invalid reply surfaces as `null` ⇒ falls into the abort path above). Second, if a verdict slips through, the JS coerces defensively (`rp.verdict.pass === true` ⇒ anything not exactly true reads as fail; `Array.isArray(...) ? ... : []`), and the Python `_coerce_lens`/`_coerce_verdict` in synthesize fail-closed to NOT-passed. So a malformed verdict reads as **FAIL** (not pass), and a wholly-missing verdict reads as **ABORT**. Nothing fails open.

**Evidence:**

```js
const failedLens = replies.find(rp => !rp || rp.verdict === null)
if (failedLens) {
  log(`  ${id}: ${name} panel round ${round + 1} — lens "${failedLens.lens}" failed/skipped, stopping this ticket`)
  ...
  const metrics = await recordCriticMetrics(id, name, metricRounds, 'aborted')
  return { ok: false, residualFindings: [], metrics }
}
const lensVerdicts = replies.map(rp => ({
  pass: rp.verdict.pass === true,
  findings: Array.isArray(rp.verdict.findings) ? rp.verdict.findings : [],
  lens: rp.lens,
}))
```

— `.claude/workflows/qrspi-batch.js:909-928`

```python
def _coerce_lens(entry):
    if isinstance(entry, dict): return _coerce_verdict(entry)
    if isinstance(entry, str): return parse_critic_verdict(entry)
    return {"pass": False, "findings": []}
```

— `scripts/qrspi_critic_synthesize.py:45-53`

**Dependencies:** Runner schema validation (the `schema` agent option); `_coerce_verdict` (`scripts/qrspi_critic_loop.py:36-48`).
**Implicit contracts:** Missing reply = abort (fail-closed, never silent pass). Malformed reply = fail. Comment at `:907-908`: "A lens that failed to spawn (null verdict) cannot attest the design — stop this ticket rather than silently treating a missing lens as a pass."

## Q9: What distinguishes the design-keyed plumbing (agentType prefix `qrspi-design-critic-`, design input paths, "design-phase" prompt text) from anything reusable, given the ticket requires the lens prompt be authored phase-generically for a future plan-phase reuse?

**Answer:** The design-specific coupling is concentrated in a few spots:

- **agentType prefix:** hard-coded `const agentType = \`qrspi-design-critic-${lens}\`` (`.claude/workflows/qrspi-batch.js:886`). A phase-generic panel would need the prefix parameterized (e.g. `qrspi-<phase>-critic-<lens>`).
- **Prompt text:** "the qrspi **design-phase** critic panel", "judge `DESIGN_PATH`" — the prompt names `DESIGN_PATH` as the subject variable (`.claude/workflows/qrspi-batch.js:895-900`). Input var names are design-keyed: `DESIGN_PATH`, `RESEARCH_PATH`, `TICKET_CONTENT_PATH`, `QUESTIONS_PATH`.
- **Input path resolution:** `doDesign` resolves `upstreamPath = research.md`, `ticketContentPath`, `questionsPath` — design-phase-specific upstreams.
- **Agent specs themselves:** every lens file's prose is design-keyed ("design-phase critic panel", "the produced design", "DESIGN_PATH").

**Reusable parts:** the loop *control structure* (round loop, parallel fan-out, synthesize reduction, `next_action` decision, metrics) is phase-agnostic — it operates on `criticConfig.lenses` + paths generically. The single-critic `runCriticLoop` is already used for non-design phases (questions/research/structure/plan) with generic `UPSTREAM_PATH`/`ARTIFACT_PATH` naming (`.claude/workflows/qrspi-batch.js:756-757`). So the reuse template already exists in the single-critic path's generic var naming; the PANEL path is the only one hard-keyed to "design".

**Evidence:**

```js
const agentType = `qrspi-design-critic-${lens}`
...
`You are the ${lens} lens of the qrspi design-phase critic panel for ${id}, round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
...
Read all four paths and judge DESIGN_PATH through your lens.`
```

— `.claude/workflows/qrspi-batch.js:886, 895-900`

```js
`You are the qrspi-critic for ${id} artifact "${name}", round ${round + 1}/${maxRounds}.
UPSTREAM_PATH = ${upstreamPath}
ARTIFACT_PATH = ${artifactPath}`
```

— `.claude/workflows/qrspi-batch.js:755-757` (the already-phase-generic single critic, for contrast)

**Dependencies:** Panel dispatch is gated on `criticConfig.lenses?.length` in `runPhase` (`.claude/workflows/qrspi-batch.js:1493-1495`); only `doDesign` ever sets `lenses` today (`doPlan`'s structure/plan critics are single-critic, no lenses).
**Implicit contracts:** "design" is keyed in: the agentType prefix string, the prompt's phase noun, the input var names, and the agent files' prose. A phase-generic lens needs all four decoupled. The single-critic path's `UPSTREAM_PATH`/`ARTIFACT_PATH` naming is the existing phase-generic precedent.

## Q10: What pattern do the existing `scripts/*_test.py` tests use to assert lens-set membership, config-resolver whitelist acceptance, and synthesize behavior, so new wiring tests match the `python3 scripts/run_tests.py` gate?

**Answer:** Tests are stdlib-only `unittest` modules named `<module>_test.py`, importing the pure functions directly and asserting on returned dicts. `run_tests.py` discovers every `scripts/*_test.py`, runs each as a subprocess, and exits non-zero if any fails (the CI gate via `.github/workflows/tests.yml`). Patterns:

- **Whitelist/membership:** `qrspi_critics_config_test.py` imports `DEFAULT_DESIGN_LENSES`, `DEFAULT_MAX_ROUNDS` and calls `resolve_design`/`resolve_edge_phase` via a `_resolve(...)` helper, asserting `out["lenses"] == [...]` and that warnings list known-vs-unknown handling (`test_known_lenses_subset_kept_in_order`, `test_unknown_lenses_dropped_with_warning`).
- **Synthesize:** `qrspi_critic_synthesize_test.py` calls `synthesize([...])` on in-memory verdict lists and asserts the reduced `{pass, findings}`.
- A new lens added to `DEFAULT_DESIGN_LENSES` would be covered by adding it to the expected list in `test_defaults` and a `test_known_lenses_subset_kept_in_order`-style case.

**Evidence:**

```python
def test_known_lenses_subset_kept_in_order(self):
    out, warnings = self._resolve({"lenses": ["simplicity", "completeness"]})
    self.assertEqual(out["lenses"], ["simplicity", "completeness"])
    self.assertEqual(warnings, [])

def test_unknown_lenses_dropped_with_warning(self):
    out, warnings = self._resolve({"lenses": ["completeness", "bogus"]})
    self.assertEqual(out["lenses"], ["completeness"])
    self.assertEqual(len(warnings), 1)
```

— `scripts/qrspi_critics_config_test.py:128-136`

```python
names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
if pattern: names = [n for n in names if pattern in n]
```

— `scripts/run_tests.py:42-46` (discovery)

**Dependencies:** `run_tests.py` is the aggregating runner (`scripts/run_tests.py`); CI gate `.github/workflows/tests.yml` (referenced in CLAUDE.md). Each test imports its module via `sys.path.insert(0, scripts_dir)`.
**Implicit contracts:** No pytest — pure `unittest` + `__main__` guard; each test file must exit 0/non-zero standalone. Adding a lens means updating the expected-list assertions in `qrspi_critics_config_test.py` (both the default-four list and whitelist cases) or the gate fails.

## Q11: How is a deliberately-flawed design fixture (e.g. under `evals/teeth/`) currently structured for the teeth eval, and what marker/assertion mechanism does `scripts/qrspi_teeth_assert.py` use to verify a lens caught its defect?

**Answer:** The fixture set lives at `evals/teeth/` (`design.md`, `research.md`, `ticket.md`, `questions.md`). `design.md` embeds **three labelled defects, one per owning lens**, each carrying a unique quotable **marker** string the owning lens must cite. The lens→marker ownership map is hard-coded in the teeth-eval workflow:
- `completeness` → `AC-TEETH-COMPLETENESS`
- `internal-consistency` → `TEETH-INCONSISTENCY`
- `edge-alignment` → `frobnicate_widget()`

(Note: the `simplicity` lens is NOT exercised by the teeth eval — only three of the four lenses have defects.)

The assertion core `scripts/qrspi_teeth_assert.py::evaluate(trials_by_lens, markers, threshold)` decides catches via `_is_catch`: a trial "catches" iff BOTH (a) `verdict["pass"] is False` AND (b) the lens's marker appears as a substring of SOME finding. A lens passes iff `caught >= threshold` (default 2-of-3 majority). `overallPass` is True iff every evaluated lens passes (empty set ⇒ False, fail-closed). Malformed verdicts read as NOT-a-catch. The eval runs digest-ON (the cost-reduced config) to prove the panel keeps teeth.

**Evidence:**

```js
const LENS_MARKERS = {
  'completeness': 'AC-TEETH-COMPLETENESS',
  'internal-consistency': 'TEETH-INCONSISTENCY',
  'edge-alignment': 'frobnicate_widget()',
}
const LENSES = Object.keys(LENS_MARKERS)
```

— `.claude/workflows/qrspi-teeth-eval.js:62-67`

```python
def _is_catch(verdict, marker):
    if not isinstance(verdict, dict): return False
    if verdict.get("pass") is not False: return False
    if not isinstance(marker, str) or not marker: return False
    findings = verdict.get("findings")
    if not isinstance(findings, list): return False
    for finding in findings:
        if isinstance(finding, str) and marker in finding: return True
    return False
```

— `scripts/qrspi_teeth_assert.py:58-78`

```
<!-- DEFECT 2 (internal-consistency, marker TEETH-INCONSISTENCY): the retry cap ...
<!-- DEFECT 3 (edge-alignment, marker frobnicate_widget()): contradicts research.md ...
<!-- DEFECT 1 (completeness): the ticket's AC-TEETH-COMPLETENESS — emit a structured ...
```

— `evals/teeth/design.md:37, 56, 69`

**Dependencies:** `scripts/qrspi_teeth_assert.py` (pure core + CLI), `scripts/qrspi_teeth_assert_test.py` (CI test), `.claude/workflows/qrspi-teeth-eval.js` (opt-in spawner, off CI), fixtures `evals/teeth/*.md`. There is also `scripts/qrspi_teeth_test.py`.
**Implicit contracts:** Each defect must embed a unique quotable marker; the edge-alignment marker `frobnicate_widget()` is intentionally inline prose (not a fenced block) so a digest that trimmed code blocks still preserves it (comment at `.claude/workflows/qrspi-teeth-eval.js:58-60`). A new lens's teeth coverage requires (1) a new labelled defect + marker in `evals/teeth/design.md`, (2) the marker added to `LENS_MARKERS`.

## Q12: What does `runCriticPanelLoop` record or emit per-lens per-round (verdicts, findings, instrumentation from RUS-78), and where would a new lens's blocking-vs-non-blocking-note distinction be visible in that output?

**Answer:** Two output channels:

1. **`log()` lines** (human/per-ticket log): per round it logs `panel round N/M → PASS` or `FAIL (X/Y lenses passed, Z finding(s))`, plus a `summaryRounds` accumulator (`r1:pass` / `r1:2/4`) on converge/cap. Individual lens pass/fail is NOT separately logged per-lens — only the aggregate pass count.

2. **`metricRounds` → `recordCriticMetrics`** (durable ledger, the AC-INSTR instrumentation): every lens verdict each round is pushed as `{ lens, pass, findings }` into `metricRounds`. On termination, `recordCriticMetrics(id, name, metricRounds, terminalAction)` runs `scripts/qrspi_critic_metrics.py` (reducer derives `findingsCount` per round in Python) and appends one `CriticStepMetrics` record (`{phase, rounds:[{lens, pass, findingsCount}], terminalAction}`) to the per-ticket ledger via `qrspi_metrics_append.py`. `terminalAction` is one of `converged|cap_reached|exhausted|aborted`.

There is currently **NO** blocking-vs-non-blocking-note dimension in either channel. Every lens is treated identically — its `pass`/`findings` feed unanimity (AND-reduce, Q6) and findings flow to PR-body residuals on cap. A "non-blocking note" lens (one whose dissent should surface as advisory rather than flip `all_passed`) has no representation: `CriticStepMetrics.rounds[]` records `{lens, pass, findingsCount}` only — no blocking flag — and synthesize has no per-lens privilege. Introducing the distinction would need a new field on the per-lens verdict/metrics record AND a change to synthesize's AND-reduce (to exclude non-blocking lenses from `all_passed`) and/or the residual-findings routing.

**Evidence:**

```js
for (const v of lensVerdicts) metricRounds.push({ lens: v.lens, pass: v.pass, findings: v.findings })
...
log(`  ${id}: ${name} panel round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${passCount}/${lenses.length} lenses passed, ${synthFindings.length} finding(s))`}`)
summaryRounds.push(`r${round + 1}:${passed ? 'pass' : `${passCount}/${lenses.length}`}`)
```

— `.claude/workflows/qrspi-batch.js:930, 942-943`

```js
const CRITIC_METRICS_SCHEMA = {
  ...
  rounds: { type: 'array', items: { type: 'object',
    required: ['lens', 'pass', 'findingsCount'],
    properties: { lens: {...}, pass: {...}, findingsCount: {...} } } },
}
```

— `.claude/workflows/qrspi-batch.js:1045-1062`

**Dependencies:** `recordCriticMetrics` (`.claude/workflows/qrspi-batch.js:1088-1102`) → `scripts/qrspi_critic_metrics.py` + `scripts/qrspi_metrics_append.py`; metrics surfaced to caller via `criticConfig.criticMetrics` (`:1508`).
**Implicit contracts:** The ledger record is the only durable per-lens output; `findingsCount` is derived in Python, never JS. terminalAction never includes `revise` (a mid-loop continuation). No per-lens blocking flag exists today — the AND-reduce makes every lens equally blocking, so a "note-only" lens distinction is genuinely new wiring across the verdict shape, synthesize, and the metrics schema.

---

## Discovered Patterns

- **Pure-Python core + thin worker shim:** every non-trivial decision (synthesize, next_action, design-select, teeth-assert, critics-config, metrics) is a stdlib-only pure function with a `main()` stdin→stdout CLI; the JS sandbox cannot run Python, so JS spawns a worker that runs `python3 scripts/<x>.py` and parses stdout. Fragile text is piped on **stdin** (never the worker's stdout echo) — see `synthesizeVerdicts`, `criticDecision`, `recordCriticMetrics`, `selectDesignWinner`.
- **Fail-closed everywhere:** missing/malformed verdicts read as NOT-passed or abort the ticket, never silent-pass. Empty digest aborts. Empty lens set ⇒ `pass:false`. `bool` excluded from int checks (`_pos_int_or`).
- **Self-locating scripts:** every `scripts/qrspi_*.py` derives the repo root from `__file__` (`parents[1]`), never cwd, so the JS caller types only the invocation.
- **Lockstep JS/Python constants:** `DEFAULT_DESIGN_LENSES`, `DEFAULT_DESIGN_FRAMINGS`, `DEFAULT_MAX_ROUNDS`, and the `DEFAULT_CRITIC_PHASES` defaults are duplicated in `qrspi-batch.js` and `qrspi_critics_config.py` and must be kept in sync (Python is the tested source of truth; JS is the config-read-failure fallback).
- **Uniform `enabled` vocabulary:** every phase critic is opt-in (default OFF); only an explicit boolean flips it; nested cost-lever blocks (`digest`, `gateBehindEdge`) reuse the same `resolve_enabled` idiom.
- **Lenses are Read-only today:** all four lens agents declare `tools: Read` and their rules explicitly forbid codebase exploration ("Do not explore the codebase, do not read other artifacts") — directly relevant to any change granting a lens `Grep`/codebase access.
- **Phase-generic single critic already exists:** `runCriticLoop` uses generic `UPSTREAM_PATH`/`ARTIFACT_PATH` naming and serves questions/research/structure/plan; only the PANEL (`runCriticPanelLoop`) is hard-keyed to "design".

## Inconsistencies

- **`KNOWN_DESIGN_LENSES` referenced as being "in qrspi-batch.js" but does NOT exist there.** Code comments (`scripts/qrspi_critics_config.py:60-65`) say `KNOWN_DESIGN_LENSES` mirrors a constant "in qrspi-batch.js", but grep finds `KNOWN_DESIGN_LENSES` defined ONLY in `scripts/qrspi_critics_config.py:65`. The JS side has `DEFAULT_DESIGN_LENSES` only — there is no JS whitelist constant. The whitelist gating lives entirely in Python.
- **Ticket-number attribution drift (RUS-77 vs RUS-78):** the questions file attributes the digest to RUS-78, but the digest/lensModel/gateBehindEdge cost-lever code comments throughout `qrspi-batch.js` and `qrspi_critics_config.py` attribute it to **RUS-77** (AC-COST). The teeth eval (`evals/teeth/`, `qrspi_teeth_assert.py`) is RUS-78. Both numbers are in the same critic-effectiveness lineage; the digest itself is RUS-77 code.
- **`lensModel` is a documented-inert seam:** comments at `.claude/workflows/qrspi-batch.js:874-878` state "there is no evidence the harness honors an agent() `model` option, so this lever may be inert." The config resolver, schema, and loop all plumb it, but it may have no runtime effect — a wiring/behavior mismatch.
- **`gateBehindEdge` is a documented no-op for design:** comments at `.claude/workflows/qrspi-batch.js:1466-1488` state the design phase routes to EITHER the panel OR a single edge critic (mutually exclusive), so "there is no in-scope edge-critic pass/fail outcome for the design panel to gate behind" — the lever runs the panel anyway and records the gap.
- **Prompt hard-codes "Read all four paths":** the lens prompt string says "Read all four paths" even when a 5th `DIGEST_PATH` line is appended (`.claude/workflows/qrspi-batch.js:900`); the count is not updated when the digest line is present. Cosmetic but would be wrong-by-one if a `CODEBASE_PATH` 5th/6th input were added.
- **Teeth eval covers only 3 of 4 lenses:** `simplicity` has no defect/marker in `LENS_MARKERS` (`.claude/workflows/qrspi-teeth-eval.js:62-67`) or `evals/teeth/design.md`, so the simplicity lens's "teeth" are not asserted by the eval.
