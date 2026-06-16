# Research — Codebase Map

**Questions source:** questions.md @ /workspaces/qrspi/.worktrees/RUS-84/.qrspi/RUS-84/questions.md
**Generated:** 2026-06-16T00:00:00Z
**Status:** draft

> Path convention: all paths below are relative to REPO_ROOT = `/workspaces/qrspi/.worktrees/RUS-84/`.

## Q1: How does `runCriticPanelLoop` currently receive its upstream and input artifact paths (research.md / questions.md / ticket), and where are those design-specific paths assembled before the call?

**Answer:** `runCriticPanelLoop(name, id, criticConfig)` reads ALL paths off the single `criticConfig` object — it has no other args. It pulls `criticConfig.upstreamPath` (→ `researchPath`), `criticConfig.ticketContentPath`, `criticConfig.questionsPath`, plus `criticConfig.codebasePath` (RUS-82). The artifact-under-review path is computed locally as `stg(id, name)` (the staging path), NOT passed in. All design-specific paths are assembled in `doDesign` (where `wd`/`r` are in scope) into the `designCritic` object.

**Evidence:**

```js
async function runCriticPanelLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const lenses = criticConfig.lenses
  const artifactPath = stg(id, name)
  const researchPath = criticConfig.upstreamPath
  const ticketContentPath = criticConfig.ticketContentPath
  const questionsPath = criticConfig.questionsPath
```

— `.claude/workflows/qrspi-batch.js:844-850`

```js
const designCritic = critics.design.enabled ? {
  upstreamPath: art(wd, t.id, 'research.md'),
  maxRounds: critics.design.maxRounds,
  lenses: critics.design.lenses,
  ticketContentPath: r.ticketContentPath,
  questionsPath: art(wd, t.id, 'questions.md'),
  codebasePath: wd,
  candidates: critics.design.candidates,
  templatePath: tpl(wd, 'design.md'),
} : undefined
```

— `.claude/workflows/qrspi-batch.js:1736-1750`

**Dependencies:** `doDesign` → `runPhase` (passes `criticConfig`) → `runCriticPanelLoop`. Path helpers `art(wd,id,name)` = `${wd}/.qrspi/${id}/${name}` (`:647`), `stg(id,name)` = `/tmp/phase-stage/${id}/${name}.md` (`:652`).
**Implicit contracts:** The panel reads its subject from `stg(id, name)` (the pre-persist staging window), NOT the canonical persisted path. All input paths are absolute and resolved by the caller because `r`/`wd` are not in scope inside the loop.

## Q2: How is `CODEBASE_PATH` threaded into the design panel lens spawn prompt today, and what value is passed for it?

**Answer:** Inside `runCriticPanelLoop`'s per-lens fan-out, `codebaseLine` is built from `criticConfig.codebasePath` and appended (uniformly, mirroring `digestLine`) to every lens prompt as `\nCODEBASE_PATH = <path>`. The value passed is `wd` (the worktree root, `r.worktreeDir`), set as `codebasePath: wd` in `doDesign`. Only the `design-review` (node-validity) lens actually uses it; the four edge-fidelity lenses ignore it.

**Evidence:**

```js
const codebaseLine = criticConfig.codebasePath ? `\nCODEBASE_PATH = ${criticConfig.codebasePath}` : ''
...
`...QUESTIONS_PATH = ${questionsPath}${digestLine}${codebaseLine}
Read every path provided above and judge DESIGN_PATH through your lens. Return { pass, findings } per the schema.`
```

— `.claude/workflows/qrspi-batch.js:894`, `:903-904`

**Dependencies:** `codebasePath` flows from `doDesign` (`codebasePath: wd`, `:1745`) on the `designCritic` config.
**Implicit contracts:** When `codebasePath` is falsy, NO `CODEBASE_PATH` line is emitted (`''`), so a lens that depends on it (`design-review`) would lack codebase access. The teeth-eval workflow threads its OWN `CODEBASE_PATH` (= `ENGINE_ROOT`) because it does not go through `runCriticPanelLoop` (`qrspi-teeth-eval.js:61`, `:150`).

## Q3: For the plan phase, what artifacts exist on disk at the time the critic runs, and what are the file names/paths for `structure.md` and `plan.md`?

**Answer:** In `doPlan`, the structure phase runs first (persisting `structure.md`), then the plan phase produces `plan.md`. At the moment the PLAN critic runs (inside `runPhase('plan', ...)`), `structure.md` and `design.md` are already persisted at the canonical worktree path `${wd}/.qrspi/${id}/<name>`, while `plan.md` is still at its staging path `/tmp/phase-stage/${id}/plan.md` (the pre-persist window). The plan critic's `upstreamPath` is `art(wd, t.id, 'structure.md')`.

**Evidence:**

```js
const planCritic = critics.plan.enabled ? {
  upstreamPath: art(wd, t.id, 'structure.md'),
  maxRounds: critics.plan.maxRounds,
} : undefined
...
if (!await runPhase('plan', 'qrspi-plan',
  `TICKET_ID = ${t.id}
STRUCTURE_PATH = ${art(wd, t.id, 'structure.md')}
DESIGN_PATH = ${art(wd, t.id, 'design.md')}
OUTPUT_PATH = ${stg(t.id, 'plan')}
TEMPLATE_PATH = ${tpl(wd, 'plan.md')}`, r.existing, t.id, 'Plan', planCritic)) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:1843-1846`, `:1848-1853`

**Dependencies:** `scripts/qrspi_persist.py` moves `/tmp/phase-stage/<id>/<name>.md` → `${wd}/.qrspi/<id>/<name>.md` (via `persistArtifact`, `:680-693`). The plan agent's inputs are `STRUCTURE_PATH` + `DESIGN_PATH` (`.claude/agents/qrspi-plan.md:13-14`).
**Implicit contracts:** The critic-under-review subject is always the STAGED file (`stg(id,name)`), upstream is the PERSISTED file. A plan node lens would have `structure.md`, `design.md` (persisted) and `plan.md` (staged) available, plus `research.md`/`questions.md` if their paths were threaded onto `planCritic`.

## Q4: What is the parameter signature of `runCriticPanelLoop`, and which of agentType, prompt text, and input paths are currently passed as arguments versus hardcoded as literals?

**Answer:** Signature: `async function runCriticPanelLoop(name, id, criticConfig)`. The lens `agentType` is hardcoded as the template literal `` `qrspi-design-critic-${lens}` `` (DESIGN-specific). The lens prompt text is a hardcoded inline literal naming "qrspi design-phase critic panel". Input paths come from `criticConfig` fields (`upstreamPath`, `ticketContentPath`, `questionsPath`, `codebasePath`, `lenses`, `maxRounds`, `digest`, `lensModel`). So lens-id→agentType mapping and the design-phase prompt wording are the only design-hardcoded pieces; paths are data.

**Evidence:**

```js
const agentType = `qrspi-design-critic-${lens}`
...
const verdict = await agent(
  `You are the ${lens} lens of the qrspi design-phase critic panel for ${id}, round ${round + 1}/${maxRounds}.
DESIGN_PATH = ${artifactPath}
TICKET_CONTENT_PATH = ${ticketContentPath}
RESEARCH_PATH = ${researchPath}
QUESTIONS_PATH = ${questionsPath}${digestLine}${codebaseLine}
```

— `.claude/workflows/qrspi-batch.js:886`, `:898-903`

**Dependencies:** Lens agent files must exist at `.claude/agents/qrspi-design-critic-<lens>.md` for the agentType to resolve.
**Implicit contracts:** Generalizing to plan requires either a new `qrspi-plan-critic-<lens>` agentType scheme or reuse of the design lens prompt with plan-appropriate path labels (`DESIGN_PATH` literal is hardcoded as the subject label). The prompt hardcodes the label `DESIGN_PATH` for the subject and `RESEARCH_PATH`/`QUESTIONS_PATH`/`TICKET_CONTENT_PATH` for inputs — none are phase-parameterized.

## Q5: What is the routing expression in `runPhase` that selects `runCriticPanelLoop` vs `runCriticLoop`, and what exactly does it read from `criticConfig`?

**Answer:** The dispatch is a single ternary keyed on `criticConfig.lenses?.length`: a non-empty `lenses` array routes to `runCriticPanelLoop` (panel); its absence/emptiness routes to `runCriticLoop` (single edge critic). It reads ONLY the truthiness of `lenses.length`.

**Evidence:**

```js
// Dispatch on lenses: a non-empty criticConfig.lenses selects the multi-lens PANEL
// (design phase); its absence (the single-critic plan phase, or any other caller) keeps
// the landed single-critic path byte-for-byte unchanged.
const cr = criticConfig.lenses?.length
  ? await runCriticPanelLoop(name, id, criticConfig)
  : await runCriticLoop(name, id, criticConfig)
```

— `.claude/workflows/qrspi-batch.js:1494-1499`

**Dependencies:** The `if (criticConfig)` guard at `:1469` wraps this; `criticConfig` is `undefined` when the phase critic is disabled, skipping the whole block.
**Implicit contracts:** This is THE generalization seam — making `planCritic` carry a non-empty `lenses` array would automatically route the plan phase to the panel. Currently `planCritic` (`:1843-1846`) carries only `{upstreamPath, maxRounds}` (no `lenses`), so it always routes to the single critic.

## Q6: What functions/values does `scripts/qrspi_critics_config.py` export, and how is the per-phase `lenses` block and a lens whitelist like `KNOWN_DESIGN_LENSES` represented?

**Answer:** Module exports: constants `DEFAULT_MAX_ROUNDS=2`, `DEFAULT_DESIGN_LENSES` (four edge lenses), `KNOWN_DESIGN_LENSES` (the whitelist = default four ∪ `{"design-review"}`), `DEFAULT_DESIGN_FRAMINGS`, `EDGE_PHASES=("questions","research","structure","plan")`; and functions `_pos_int_or`, `resolve_enabled`, `resolve_edge_phase`, `resolve_design`, `resolve_implementation`, `resolve_critics`, `default_phases`, `main`. The lens whitelist is a Python `set`; config lenses are filtered against it (`l in KNOWN_DESIGN_LENSES`), unknowns dropped with a warning, all-unknown falls back to `DEFAULT_DESIGN_LENSES`.

**Evidence:**

```python
DEFAULT_DESIGN_LENSES = ["completeness", "internal-consistency", "edge-alignment", "simplicity"]
# Whitelist/default DECOUPLING (RUS-82 ...): design-review is whitelist-acceptable ...
# but is DELIBERATELY NOT in DEFAULT_DESIGN_LENSES — it stays default-OFF ...
KNOWN_DESIGN_LENSES = set(DEFAULT_DESIGN_LENSES) | {"design-review"}
```

— `scripts/qrspi_critics_config.py:64-71`

```python
EDGE_PHASES = ("questions", "research", "structure", "plan")
```

— `scripts/qrspi_critics_config.py:78`; `resolve_edge_phase` returns only `{enabled, maxRounds}` (`:110-118`); `resolve_design` owns the lens filtering loop (`:143-158`).

**Dependencies:** Imports `read_config` from `qrspi_config.py` (`:52`). `resolve_critics` (`:219-235`) maps `plan` → `resolve_edge_phase` (NO lenses today).
**Implicit contracts:** `plan` is currently an EDGE phase (bare `{enabled, maxRounds}`). To add a plan lens, the plan branch must move to a `resolve_*` variant that emits `lenses` and validate against a plan-specific whitelist (e.g. a `KNOWN_PLAN_LENSES` mirroring `KNOWN_DESIGN_LENSES`). The JS-side mirror `DEFAULT_CRITIC_PHASES` must stay in lockstep (verified by tests).

## Q7: What is the agentType naming scheme for the RUS-82 node-validity lens agent, and what spawn-prompt parameters does it accept?

**Answer:** The RUS-82 node-validity lens is `agentType = qrspi-design-critic-design-review` (file `.claude/agents/qrspi-design-critic-design-review.md`). It is named `design-review` (the lens id) — there is currently NO plan-phase node lens agent. Its spawn-prompt parameters: `DESIGN_PATH` (subject, required), `RESEARCH_PATH` (upstream, required), `CODEBASE_PATH` (repo root, required for codebase verification), and OPTIONAL `TICKET_CONTENT_PATH`, `QUESTIONS_PATH`, `DIGEST_PATH` (which it explicitly opts OUT of — always reads full `RESEARCH_PATH`).

**Evidence:**

```
- `DESIGN_PATH` — absolute path to the artifact under review (the staged artifact)...
- `RESEARCH_PATH` — absolute path to the upstream input the artifact was derived from...
- `CODEBASE_PATH` — absolute path to the repository root. Read and Grep real source here...
- `TICKET_CONTENT_PATH` — OPTIONAL...
- `QUESTIONS_PATH` — OPTIONAL...
- `DIGEST_PATH` — OPTIONAL... You opt OUT of the digest...
```

— `.claude/agents/qrspi-design-critic-design-review.md:14-19`; frontmatter `tools: Read, Grep` (`:5`); model note "Opus-tier intent, doc-only, NOT wired" (`:71-73`).

**Dependencies:** Spawned by `runCriticPanelLoop` with `CRITIC_VERDICT_SCHEMA` (`{pass, findings}`). Lens id `design-review` maps to agentType `qrspi-design-critic-design-review` via the `qrspi-design-critic-${lens}` literal.
**Implicit contracts:** The lens prompt hardcodes `DESIGN_PATH` as the subject label and judges "node validity" against real source. A plan node lens would need a plan-flavored equivalent (judging plan steps' codebase claims) OR reuse this agent if the design-flavored prose is acceptable; the agentType scheme `qrspi-design-critic-*` is design-named. The invariant `pass:false ⟺ findings non-empty` is strict (`:48`).

## Q8: How is `DEFAULT_CRITIC_PHASES` structured in `qrspi-batch.js`, and what does the current `plan` entry look like alongside the `design` entry that carries `lenses`?

**Answer:** `DEFAULT_CRITIC_PHASES` is a JS object with six keys. `plan` is the bare edge shape `{ enabled: false, maxRounds: 2 }` (no `lenses`); `design` carries `{ enabled: false, maxRounds: 2, lenses: DEFAULT_DESIGN_LENSES, candidates: 1, digest: {enabled:false}, gateBehindEdge: {enabled:false} }`. It is the JS-side fallback mirror of the Python resolver's all-defaults, kept in lockstep.

**Evidence:**

```js
const DEFAULT_CRITIC_PHASES = {
  questions: { enabled: false, maxRounds: 2 },
  research: { enabled: false, maxRounds: 2 },
  design: { enabled: false, maxRounds: 2, lenses: DEFAULT_DESIGN_LENSES, candidates: 1, digest: { enabled: false }, gateBehindEdge: { enabled: false } },
  structure: { enabled: false, maxRounds: 2 },
  plan: { enabled: false, maxRounds: 2 },
  implementation: { enabled: false, maxRounds: 2, coherence: { enabled: false, maxRounds: 2 } },
}
```

— `.claude/workflows/qrspi-batch.js:632-642`; `DEFAULT_DESIGN_LENSES` at `:617`.

**Dependencies:** Returned verbatim by `parseCriticsEnvelope` on config-read failure (`:391`, `:393`, `:395`) and shallow-merged under a partial envelope (`:397`). Must stay in lockstep with `scripts/qrspi_critics_config.py` defaults (verified by `qrspi_critics_config_test.py`).
**Implicit contracts:** Adding plan lenses requires editing BOTH this JS constant and the Python resolver's `plan` branch, plus their lockstep tests. The `plan` entry has no `lenses` key today, so the dispatch ternary (Q5) never routes plan to the panel.

## Q9: How does config from `.qrspi/config.json` override `DEFAULT_CRITIC_PHASES`, and how is a non-empty `critics.plan.lenses` value resolved and validated against the whitelist?

**Answer:** `readCriticsConfig` shells out to `scripts/qrspi_critics_config.py` (the single tested resolver), which reads `.qrspi/config.json` ONCE via `read_config`, resolves every phase, and emits a JSON envelope `{ok, phases, warnings}`. JS `parseCriticsEnvelope` parses it and shallow-merges over `DEFAULT_CRITIC_PHASES`. CRITICALLY: `critics.plan` is resolved by `resolve_edge_phase`, which IGNORES any `lenses` key entirely — there is NO plan whitelist today. A `critics.plan.lenses` value is currently silently dropped (not surfaced, not validated). Only `resolve_design` validates lenses (against `KNOWN_DESIGN_LENSES`).

**Evidence:**

```python
def resolve_edge_phase(cfg):
    cfg = cfg if isinstance(cfg, dict) else {}
    return {
        "enabled": resolve_enabled(cfg, False),
        "maxRounds": _pos_int_or(cfg.get("maxRounds"), DEFAULT_MAX_ROUNDS),
    }
```

— `scripts/qrspi_critics_config.py:110-118` (note: no `lenses` read); `resolve_critics` wires `"plan": resolve_edge_phase(c.get("plan"))` (`:232`).

```python
known = [l for l in raw_lenses if isinstance(l, str) and l in KNOWN_DESIGN_LENSES]
unknown = [l for l in raw_lenses if not (isinstance(l, str) and l in KNOWN_DESIGN_LENSES)]
...
lenses = known if known else list(DEFAULT_DESIGN_LENSES)
```

— `scripts/qrspi_critics_config.py:146-158` (design only)

**Dependencies:** `readCriticsConfig` (`:1343`) → `engineCmd` worker run of the resolver → `parseCriticsEnvelope` (`:389`). config.example.json documents the plan block as "`enabled` + `maxRounds` only ... there is no `lenses`/`candidates` knob" (`.qrspi/config.example.json:43`).
**Implicit contracts:** To honor `critics.plan.lenses`, a new resolver (mirroring `resolve_design` with a plan whitelist) must replace `resolve_edge_phase` for plan, AND `doPlan` must thread the resolved `lenses` onto `planCritic`. The config.example.json plan comment would also need updating (currently asserts "no lenses knob").

## Q10: When `critics.plan.lenses` is empty or absent, what code path ensures the plan phase still routes to the single-critic `runCriticLoop` (back-compat)?

**Answer:** Back-compat is preserved by the SAME `criticConfig.lenses?.length` ternary in `runPhase` (Q5): with no/empty `lenses`, the falsy branch routes to `runCriticLoop`. Today `planCritic` never sets `lenses` (`:1843-1846`), so plan ALWAYS hits the single critic. The optional-chaining `?.length` is null-safe for `undefined`/missing/empty arrays. So any future plan-lens generalization gets back-compat for free as long as an empty/absent `lenses` resolves to falsy.

**Evidence:**

```js
const cr = criticConfig.lenses?.length
  ? await runCriticPanelLoop(name, id, criticConfig)
  : await runCriticLoop(name, id, criticConfig)
```

— `.claude/workflows/qrspi-batch.js:1497-1499`

**Dependencies:** Decided in `runPhase` (`:1494-1499`); `resolve_edge_phase` (Python) never emits `lenses`, so the envelope's `plan.lenses` is absent → `planCritic.lenses` undefined → falsy.
**Implicit contracts:** A plan-lens resolver MUST emit an absent/empty `lenses` when none are configured (not a non-empty default), or it would flip every plan run to the panel and break back-compat. (Design's `resolve_design` defaults to the full four — a plan resolver wanting opt-in panels must default to empty.)

## Q11: How does `scripts/qrspi_critic_synthesize.py` reconcile multiple lens verdicts under strict-unanimity, and how does it treat non-blocking nits versus material/blocking defects?

**Answer:** `synthesize(verdicts)` is strict-unanimity (AND semantics): `pass` is True ONLY if the list is non-empty AND every coerced lens passed — any single fail fails the round. `findings` is the exact-string-deduped UNION of all lens findings in first-seen order, optionally lens-tagged. It does NOT distinguish "nit" from "blocking" — it has no severity concept. Severity is the LENS's responsibility (a lens emits a finding only when blocking, and `pass:false ⟺ findings non-empty`). So a lens that returns `pass:true` with nit findings still unions those findings but does not fail the round.

**Evidence:**

```python
all_passed = True
findings = []
seen = set()
for entry in verdicts:
    coerced = _coerce_lens(entry)
    if not coerced["pass"]:
        all_passed = False
    ...
return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:97-118`; empty list → `{"pass": False, "findings": []}` fail-closed (`:94-95`).

**Dependencies:** Coerces each entry via the LANDED `_coerce_verdict`/`parse_critic_verdict` from `qrspi_critic_loop.py` (`:39-42`, `:45-53`) — fail-closed (malformed → NOT-passed, no findings). Invoked from `synthesizeVerdicts` JS worker (`:1001-1015`).
**Implicit contracts:** Phase-agnostic — `synthesize` takes a `verdicts` list with NO phase knowledge, so it is reusable verbatim for a plan panel. The test (`qrspi_critic_synthesize_test.py:49`) confirms "all-pass lenses carrying nit findings ⇒ pass:true but findings still unioned". A plan panel reuses this reducer unchanged.

## Q12: What happens in `runCriticPanelLoop` if a lens cited an unknown/unconfigured lens name, or if a configured lens is in the whitelist for one phase but not another?

**Answer:** Two separate layers. (1) WHITELIST validation happens UPSTREAM in `resolve_design` (Python) BEFORE the loop — an unknown lens id is dropped with a warning and never reaches `runCriticPanelLoop`; the loop only ever sees whitelist-valid lens ids. (2) In the LOOP itself, each lens id is mapped to `qrspi-design-critic-${lens}` and spawned; if a lens fails to spawn (null verdict — e.g. an agentType with no matching agent file), the loop hits the `failedLens` guard and ABORTS the ticket (fail-closed), NOT silently treating it as a pass. There is no per-phase whitelist scoping inside the loop — the loop trusts the resolved `lenses`.

**Evidence:**

```js
const failedLens = replies.find(rp => !rp || rp.verdict === null)
if (failedLens) {
  log(`  ${id}: ${name} panel round ${round + 1} — lens "${failedLens.lens}" failed/skipped, stopping this ticket`)
  ...
  return { ok: false, residualFindings: [], metrics }
}
```

— `.claude/workflows/qrspi-batch.js:913-925`; whitelist drop in `resolve_design` (`:148-155`).

**Dependencies:** The whitelist (`KNOWN_DESIGN_LENSES`) is design-scoped in Python; there is no plan whitelist. The loop's `agentType = qrspi-design-critic-${lens}` (`:886`) requires a matching agent file.
**Implicit contracts:** A lens id that is whitelist-valid but has NO agent file (or a plan lens id mapped through the design `qrspi-design-critic-*` literal) would null-spawn → abort. A plan panel needs both a plan whitelist AND a plan agentType mapping (or reuse of the design one) so every resolved lens has a spawnable agent.

## Q13: How is the existing design-phase teeth eval structured end-to-end, and which parts are design-hardcoded versus phase-generic?

**Answer:** `.claude/workflows/qrspi-teeth-eval.js` runs three phases: Digest (build shared research digest via `qrspi_research_digest.py`), Panel (fan out REAL `qrspi-design-critic-<lens>` agents over `LENSES × TRIALS` against the flawed fixture), Assert (hand grouped verdicts + markers + threshold to `qrspi_teeth_assert.py`). **Design-hardcoded:** fixture paths `evals/teeth/{design,ticket,research,questions}.md`; the `LENS_MARKERS` ownership map (completeness/internal-consistency/edge-alignment/design-review → markers); the `qrspi-design-critic-${lens}` agentType literal; the inline DESIGN-phase prompt; `DESIGN_PATH` subject label; `CODEBASE_PATH = ENGINE_ROOT`. **Phase-generic:** the trials/threshold math (`THRESHOLD = floor(TRIALS/2)+1`), the parallel fan-out structure, the failed-lens abort guard, the stdin-worker assert pattern, and `qrspi_teeth_assert.py` itself.

**Evidence:**

```js
const LENS_MARKERS = {
  'completeness': 'AC-TEETH-COMPLETENESS',
  'internal-consistency': 'TEETH-INCONSISTENCY',
  'edge-alignment': 'frobnicate_widget()',
  'design-review': 'TEETH-NODE-VALIDITY',
}
const LENSES = Object.keys(LENS_MARKERS)
```

— `.claude/workflows/qrspi-teeth-eval.js:75-81`; fixtures `:50-53`; CODEBASE_PATH `:61`; agentType + prompt `:144-152`; threshold `:111`.

**Dependencies:** Fixtures live at `evals/teeth/` (design.md, questions.md, research.md, ticket.md — verified present). Activation of a lens for the eval is SOLELY via membership in `LENS_MARKERS` (`:69-74`) — the eval does NOT call `resolve_design`, so production default-OFF whitelist is irrelevant.
**Implicit contracts:** A plan teeth eval would be a NEW workflow file (or generalized one) with plan fixtures, a plan `LENS_MARKERS` map, and the plan node-lens agentType. The deterministic core (`qrspi_teeth_assert.py`) is reused verbatim. The eval is OFF CI (a `.claude/workflows/*.js` is outside `run_tests.py`'s glob — `:29-34`).

## Q14: What is the deterministic majority/marker math the teeth eval asserts against (qrspi_teeth_assert.py), so a plan teeth eval can reuse the same assertion core?

**Answer:** `evaluate(trials_by_lens, markers, threshold=2)` is the pure core. Per lens: `caught = count of trials where _is_catch(verdict, marker)`; a lens passes iff `caught >= threshold`; `overallPass` is True iff EVERY evaluated lens passes (empty lens set → False, fail-closed). `_is_catch(verdict, marker)` requires BOTH `verdict["pass"] is False` AND `marker` is a substring of some finding string. Threshold coerces to int, non-int/≤0 → 2. It is 100% phase-agnostic — keyed only on the lens→marker map and threshold. `qrspi_teeth_assert_test.py` already includes `design-review`/`TEETH-NODE-VALIDITY` cases.

**Evidence:**

```python
def _is_catch(verdict, marker):
    if not isinstance(verdict, dict):
        return False
    if verdict.get("pass") is not False:
        return False
    if not isinstance(marker, str) or not marker:
        return False
    findings = verdict.get("findings")
    if not isinstance(findings, list):
        return False
    for finding in findings:
        if isinstance(finding, str) and marker in finding:
            return True
    return False
```

— `scripts/qrspi_teeth_assert.py:58-78`; `evaluate` pass/overall logic `:117-130`.

**Dependencies:** CLI: `printf '<trials_by_lens json>' | python3 qrspi_teeth_assert.py --markers '<json>' --threshold N` (`:146-169`). Tested by `qrspi_teeth_assert_test.py` (includes design-review marker cases, `:31`, `:119-142`).
**Implicit contracts:** A plan teeth eval reuses `evaluate`/`qrspi_teeth_assert.py` byte-for-byte — only the `markers` map and `trials_by_lens` (produced by the plan fan-out) differ. The catch contract is: defect embeds a unique quotable marker; the owning lens must (a) fail and (b) cite the marker substring.

## Q15: How would a deliberately-flawed plan fixture be built and labelled for AC5, and how is the node lens's defect ownership wired?

**Answer:** NOT FOUND as existing artifact — there is no plan teeth fixture or plan lens→defect map today (searched `.claude/workflows/`, `evals/`, `scripts/`). The PATTERN to mirror is the design fixture: `evals/teeth/design.md` (5439 bytes) carries three+ labelled defects, each embedding a unique quotable marker (`AC-TEETH-COMPLETENESS`, `TEETH-INCONSISTENCY`, `frobnicate_widget()`, `TEETH-NODE-VALIDITY`); ownership is wired via the `LENS_MARKERS` map in the workflow (`qrspi-teeth-eval.js:75-81`). For a plan node-validity defect (a plan step whose codebase claim is false / approach unsound — NOT a dropped step the edge critic catches), one would: (1) author an `evals/teeth/plan-*.md` fixture embedding a `TEETH-PLAN-NODE-VALIDITY`-style marker on a step that names a non-existent symbol; (2) add it to a plan `LENS_MARKERS` map owned by the plan node lens; (3) the eval asserts that lens fails + cites the marker via the reused `qrspi_teeth_assert.py`.

**Evidence:** Design fixture exists and is referenced; no plan equivalent:

```
evals/teeth/: design.md questions.md research.md ticket.md   (ls — no plan fixture)
```

— `evals/teeth/` directory listing; design node-validity defect activated via `'design-review': 'TEETH-NODE-VALIDITY'` (`.claude/workflows/qrspi-teeth-eval.js:79`).

**Dependencies:** The design node-validity marker `TEETH-NODE-VALIDITY` is cited when the lens verifies a false-codebase-claim in `design.md` against real source via `CODEBASE_PATH = ENGINE_ROOT` (the comment at `:69-74` says design.md falsely claims a symbol from `scripts/qrspi_critic_synthesize.py`).
**Implicit contracts:** The plan node lens must verify codebase claims in plan STEPS (the plan agent's steps reference real source). The marker must be a unique quotable string the lens cites. The eval must be non-vacuous (a clean run must NOT catch — see the design `_pass` control rows in `qrspi_teeth_assert_test.py:138-142`).

## Q16: How would a known-clean plan baseline verify it still converges without fabricated findings — and is there an existing design clean-baseline/no-noise check to mirror?

**Answer:** The convergence signal is in `runCriticPanelLoop`: a round-0 all-lens pass returns `{ok:true, residualFindings:[], summary:'panel converged@r1'}` via the `decision.action === 'converged'` branch — zero revise spawns, empty residuals. NOT FOUND as a dedicated "clean-baseline" eval: there is no separate no-false-positive clean-control WORKFLOW. The existing no-noise discipline lives in (a) the teeth eval's NON-VACUITY check — `overallPass` goes false if a lens spuriously passes a clean control (the `_pass` control rows in `qrspi_teeth_assert_test.py:138-142` assert a lens that never catches FAILS), and (b) the synthesize tests asserting all-pass clean reconciliation (`qrspi_critic_synthesize_test.py:40`). To mirror for plan, a clean plan fixture run through the plan panel should converge at round 1 with `residualFindings: []` and `overallPass`-style assertion that no lens fabricates a finding.

**Evidence:**

```js
if (decision.action === 'converged') {
  log(`  ${id}: ${name} panel CONVERGED at round ${round + 1} [${summaryRounds.join(' ')}]`)
  const metrics = await recordCriticMetrics(id, name, metricRounds, 'converged')
  return { ok: true, residualFindings: [], summary: `panel converged@r${round + 1} [${summaryRounds.join(' ')}]`, metrics }
}
```

— `.claude/workflows/qrspi-batch.js:958-962`

**Dependencies:** Convergence decision delegated to `criticDecision`/`next_action` (`:952`). The `converged` branch is the clean-pass signal; `cap_reached`/`exhausted` carry residuals.
**Implicit contracts:** A "no regression toward noise" assertion for plan = a clean plan fixture must yield `overallPass`-equivalent where the node lens PASSES (returns `pass:true, findings:[]`) — distinct from the flawed run where it must FAIL. The `qrspi_teeth_assert.py` `_is_catch` returns False on a `pass:true` verdict, so a clean run produces `caught:0` for every lens; a clean-baseline assertion would invert the threshold check (expect zero catches).

## Q17: What does strict-unanimity reconciliation produce on a clean-plan run versus a flawed run?

**Answer:** Clean run (all lenses `pass:true`, no findings): `synthesize` returns `{"pass": True, "findings": []}` — unanimous pass, empty union. Flawed run (≥1 lens `pass:false` with findings): `{"pass": False, "findings": [<deduped union>]}`. This is the concrete pass/converge signal for AC6 distinct from AC4 (AC4 = the verdict-reconciliation AND-semantics itself; AC6 = the OUTCOME on a clean input being a clean converge with zero material findings). The synthesize test explicitly covers the all-pass-no-findings case.

**Evidence:**

```python
return {"pass": all_passed, "findings": findings}
```

— `scripts/qrspi_critic_synthesize.py:118`; clean case verified:

```
- all lenses pass                ⇒ pass:true, no findings
```

— `scripts/qrspi_critic_synthesize_test.py:8` (and `check("all four lenses pass ⇒ pass:true, no findings", ...)` at `:40`).

**Dependencies:** Phase-agnostic; reused verbatim for plan. Feeds `criticDecision` which, on `pass:true`, returns `converged` (Q16).
**Implicit contracts:** AC6's concrete converge signal = `synthesize → {pass:true, findings:[]}` → `criticDecision → converged` → `runCriticPanelLoop → {ok:true, residualFindings:[]}`. A clean plan must produce zero fabricated findings at the synthesize layer for the panel to converge at round 1 with no revise.

## Q18: What patterns do the existing design-lens unit tests use to assert lens-set membership and resolver whitelist acceptance, so the plan equivalents can mirror them?

**Answer:** `qrspi_critics_config_test.py` patterns: a `_resolve(cfg)` helper that calls `resolve_design(cfg, warnings)` and returns `(out, warnings)`. Membership/whitelist tests assert: known subset kept in ORDER (`test_known_lenses_subset_kept_in_order`), unknown dropped WITH a warning (`test_unknown_lenses_dropped_with_warning`), all-unknown FALLS BACK to default (`test_all_unknown_lenses_fall_back_to_default`), non-list ignored (`test_non_list_lenses_ignored`). A dedicated RUS-82 class asserts `design-review` is NOT in the default set, NOT activated implicitly, but KEPT when opted-in (`assertIn`/`assertNotIn` on `out["lenses"]`). Edge-phase tests use `resolve_edge_phase` and assert the bare `{enabled, maxRounds}` shape.

**Evidence:**

```python
def test_known_lenses_subset_kept_in_order(self):
    out, warnings = self._resolve({"lenses": ["simplicity", "completeness"]})
    self.assertEqual(out["lenses"], ["simplicity", "completeness"])
...
out, warnings = self._resolve({"lenses": ["completeness", "design-review"]})
self.assertIn("design-review", out["lenses"])
self.assertEqual(out["lenses"], ["completeness", "design-review"])
```

— `scripts/qrspi_critics_config_test.py:128-130`, `:262-264`; default-OFF assertion `:248-250`.

**Dependencies:** Tests import `resolve_design`, `resolve_edge_phase`, `DEFAULT_DESIGN_LENSES`, `DEFAULT_MAX_ROUNDS` from `qrspi_critics_config` (`:21-22`).
**Implicit contracts:** Plan-lens tests mirror these: a `KNOWN_PLAN_LENSES` whitelist, plan default lens set (likely empty for opt-in), order-preservation, unknown-drop-with-warning, opt-in-keep, default-OFF for the plan node lens. The JS↔Python lockstep is also asserted (the resolver mirror must match `DEFAULT_CRITIC_PHASES`).

## Q19: How does `scripts/run_tests.py` discover and run `scripts/*_test.py` siblings, and the CI gate?

**Answer:** `discover_tests` lists `scripts/`, keeps every filename ending in `_test.py` (sorted), and `run_one` executes each as its own subprocess (`python3 scripts/<name>_test.py`), failing the aggregate non-zero if any fails. CI (`.github/workflows/tests.yml`) runs `python3 scripts/run_tests.py` in the `python` job on every `pull_request` + `push` to `main`. A second `workflow-syntax` job statically validates `.claude/workflows/*.js` via `scripts/check_workflows.js`. Any new `scripts/*_test.py` (e.g. plan-wiring or plan-teeth-assert tests) is auto-discovered with NO registration.

**Evidence:**

```python
names = [
    n for n in os.listdir(scripts_dir)
    if n.endswith("_test.py")
    ...
]
return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:42-48` (discover_tests, `:36`)

```yaml
- name: Run Python test suite
  run: python3 scripts/run_tests.py
...
- name: Validate workflow scripts
  run: node scripts/check_workflows.js .claude/workflows/*.js
```

— `.github/workflows/tests.yml:38-39`, `:55-56`

**Dependencies:** Optional substring filter arg; `--list` enumerates. CI jobs default-deny permissions, `contents: read` only.
**Implicit contracts:** New plan tests MUST be named `scripts/*_test.py` to be picked up. A new plan teeth WORKFLOW (`.claude/workflows/*.js`) is NOT run by CI tests but IS syntax-checked by `check_workflows.js`. Its deterministic core must live in `scripts/` to join the CI gate (mirroring `qrspi_teeth_assert.py`).

## Q20: What does `runCriticPanelLoop` currently log/record per round, and where does it surface?

**Answer:** Per round, `runCriticPanelLoop` calls `log(...)` with: the per-round PASS/FAIL line (e.g. `panel round 1/2 → FAIL (2/4 lenses passed, 3 finding(s))`), a `summaryRounds` accumulator (`r1:pass` / `r1:2/4`), and terminal lines (CONVERGED / CAP-REACHED / REVISE / exhausted). It also accumulates every lens verdict into `metricRounds` and, at every termination, calls `recordCriticMetrics(id, name, metricRounds, terminalAction)` which (a) builds a `CriticStepMetrics` record `{phase, rounds:[{lens, pass, findingsCount}], terminalAction}` via `qrspi_critic_metrics.py` and (b) DURABLY APPENDS it to the per-ticket ledger via `qrspi_metrics_append.py`. The loop returns `summary` (folded into the ticket result by the caller) and `metrics`.

**Evidence:**

```js
log(`  ${id}: ${name} panel round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${passCount}/${lenses.length} lenses passed, ${synthFindings.length} finding(s))`}`)
summaryRounds.push(`r${round + 1}:${passed ? 'pass' : `${passCount}/${lenses.length}`}`)
```

— `.claude/workflows/qrspi-batch.js:946-947`; metrics record/append `:1092-1106`; converged/cap/exhausted logs `:959`, `:964`, `:992`.

**Dependencies:** `recordCriticMetrics` worker chains `qrspi_critic_metrics.py` → `qrspi_metrics_append.py --ticket <id> --run-id <runId>` (`:1097`). The caller folds `criticConfig.criticMetrics` into `out.criticMetrics` (doDesign `:1800-1805`) and `criticConfig.criticSummary` into the result summary (`:1811`).
**Implicit contracts:** These signals are PHASE-GENERIC — `recordCriticMetrics(id, phase=name, ...)` already takes `phase` as a param (so a plan panel records `phase: 'plan'` automatically). The `CriticStepMetrics` schema's `phase` field accepts any string (`:1053`). For plan, the SAME logging/metrics path surfaces verdicts/convergence/round-count with no change — but `doPlan`'s finalize (`:1879-1881`) currently only folds `planFindings`, not `criticMetrics`/`criticSummary` (unlike `doDesign`), so a plan panel's metrics/summary fold would need adding in `doPlan`.

---

## Discovered Patterns

- **Single-config-read discipline:** every phase's critic config is resolved ONCE per batch action via `scripts/qrspi_critics_config.py` and indexed off the shared result (`doDesign`/`doPlan` each call `readCriticsConfig` once). The Python resolver is the single source of truth; `DEFAULT_CRITIC_PHASES` in JS is a lockstep mirror used only on read-failure.
- **Pure-core / imperative-shell split:** all deterministic decisions (synthesize, next_action, teeth assert, metrics reduction, config resolution) live in tested stdlib-only `scripts/*.py` with `_test.py` siblings; the JS workflow is untestable glue that shells out to them via worker agents (stdin for fragile text, verbatim-one-command discipline). Plan generalization should follow: any new decision math goes in `scripts/` to join CI.
- **`criticConfig` as the universal carrier:** `runPhase`, `runCriticLoop`, and `runCriticPanelLoop` all read every path/flag off one `criticConfig` object (resolved at the call site where `wd`/`r` are in scope) — the loops take only `(name, id, criticConfig)`. The dispatch between single-critic and panel is the single `lenses?.length` ternary.
- **RUS-82 lens-activation asymmetry:** the `design-review` node lens is default-OFF in production (whitelist-acceptable but not in `DEFAULT_DESIGN_LENSES`), yet UNCONDITIONALLY active in the teeth eval (activated solely by `LENS_MARKERS` membership). The teeth eval bypasses `resolve_design` entirely.
- **Staging-window critic gate:** every critic (single + panel + node-check) runs on the STAGED artifact (`stg(id,name)`) BEFORE persist, so persist remains the single success gate; upstream inputs are the persisted canonical paths.
- **Strict invariant on lenses:** `pass:false ⟺ findings non-empty`, blocking-only severity (the lens decides severity; synthesize has no severity concept and is pure-union).

## Inconsistencies

- **config.example.json asserts "no lenses knob" for plan** (`.qrspi/config.example.json:43`: "only 'enabled' ... and 'maxRounds' ... there is no 'lenses'/'candidates' knob"). This is accurate for current code but is the exact statement AC4/AC5 would invalidate; it must be updated when plan lenses land.
- **`resolve_edge_phase` silently drops `critics.plan.lenses`** (`qrspi_critics_config.py:110-118`): a user who sets `critics.plan.lenses` today gets NO warning and NO effect (unlike `resolve_design` which warns on unknowns). Generalization should add plan-lens validation symmetric to design.
- **`doPlan` does not fold `criticMetrics`/`criticSummary` into its result** (compare `doPlan:1879-1881` to `doDesign:1800-1813`): `doDesign` folds N-select summary, panel summary, AND `criticMetrics`; `doPlan` folds only `planFindings`. A plan panel's per-round summary and metrics would not surface in the batch result unless `doPlan`'s finalize is extended to mirror `doDesign`.
- **Design-named agentType scheme** (`qrspi-design-critic-${lens}`, `:886`) is reused by the teeth eval but is semantically design-specific. A plan node lens either needs a parallel `qrspi-plan-critic-*` (or generic `qrspi-critic-<lens>`) scheme, or must reuse the design-flavored `qrspi-design-critic-design-review` agent whose prompt prose (e.g. label `DESIGN_PATH`, "design-phase critic panel") is design-worded even when judging a plan.
- **No plan teeth fixture / plan lens→defect map exists** (Q15): the design teeth machinery is complete (fixtures + markers + node lens + tests) but has no plan counterpart; AC5/AC6 require authoring them from the design pattern.
