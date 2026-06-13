# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Q1: How does the foundation loop (from 1/5) receive its upstream artifact as the rubric, and what is the exact parameter/argument shape a single edge critic invocation passes for questions, research, structure, and plan?

**Answer:** The single-critic foundation loop is `runCriticLoop(name, id, criticConfig)` (RUS-55). The upstream artifact (rubric anchor) is passed on `criticConfig.upstreamPath` — an absolute path resolved at the call site (`doPlan`/`doDesign`) where `wd` is in scope, so the loop needs no `wd`. The artifact under judgment is computed inside the loop as `stg(id, name)`. `criticConfig` consumed fields: `upstreamPath` (required), `maxRounds` (default 2 when omitted), and optional `rubric` (extra text spliced into the prompt as a `RUBRIC = ...` line; omitted when absent). Each round spawns ONE `qrspi-critic` agent with `UPSTREAM_PATH` / `ARTIFACT_PATH` (+ optional `RUBRIC`) and schema `CRITIC_VERDICT_SCHEMA`. Only the **plan** phase currently wires this single-critic loop today: `const planCritic = { upstreamPath: art(wd, t.id, 'structure.md'), maxRounds: 2 }`. **Questions, research, and structure currently pass NO `criticConfig`** (the trailing arg is omitted), so they skip the critic block entirely. So for "questions, research, structure, plan" the *shape* a single edge critic would receive is `{ upstreamPath, maxRounds?, rubric? }`, but only plan is wired now — the four new edge critics in this ticket must add that arg to questions/research/structure (and presumably keep plan).

**Evidence:**

```js
async function runCriticLoop(name, id, criticConfig) {
  const maxRounds = criticConfig.maxRounds ?? 2
  const upstreamPath = criticConfig.upstreamPath
  const artifactPath = stg(id, name)
  const rubricLine = criticConfig.rubric ? `RUBRIC = ${criticConfig.rubric}\n` : ''
  for (let round = 0; round < maxRounds; round++) {
    const verdict = await agent(
      `You are the qrspi-critic for ${id} artifact "${name}", round ${round + 1}/${maxRounds}.
UPSTREAM_PATH = ${upstreamPath}
ARTIFACT_PATH = ${artifactPath}
${rubricLine}Read BOTH paths and judge ARTIFACT_PATH as a faithful derivation of UPSTREAM_PATH ...`,
      { label: `critic:${id}:${name}#${round + 1}`, phase: 'Critic', agentType: 'qrspi-critic', schema: CRITIC_VERDICT_SCHEMA }
    )
```

— `.claude/workflows/qrspi-batch.js:586-601`

```js
  // Edge-critic on the plan artifact, anchored on its upstream structure.md (OQ4, default 2).
  const planCritic = { upstreamPath: art(wd, t.id, 'structure.md'), maxRounds: 2 }
```

— `.claude/workflows/qrspi-batch.js:1096-1097`

**Dependencies:** `runCriticLoop` calls `agent()` (harness builtin), `criticDecision()` → `scripts/qrspi_critic_loop.py`; consumed by `runPhase`. Callers: `doPlan` (plan), `doDesign` (design, but via the panel variant).
**Implicit contracts:** `upstreamPath` must already be persisted at the canonical path (`art(wd,id,name)`) by the time the critic runs (it is the PRIOR phase's output, persisted in a prior `runPhase`). The critic judges the **edge** (upstream→produced), reading only the two paths. Return shape is `{ ok, residualFindings }`; `ok:false` is treated by `runPhase` as a phase failure.

## Q2: Where in `runPhase` does the citation validator slot relative to the research edge critic, and how is the "node check runs before the edge critic" ordering currently enforced for any existing node-then-critic phase?

**Answer:** `runPhase(name, agentType, prompt, existing, id, phaseLabel, criticConfig)` has a fixed sequence: (1) reuse-existing short-circuit; (2) spawn the producer `agent(prompt)`; (3) **if `criticConfig`** run the critic loop (panel if `criticConfig.lenses?.length`, else single `runCriticLoop`) on the still-staged `stg(id,name)`; (4) `persistArtifact` (the success gate). **There is NO node-check step today** — no phase currently runs a node validator before its edge critic. The closest analogue is the producer→critic ordering: the producer writes `stg(id,name)`, then the critic reads it. A citation validator (a NODE check on research.md) would slot **after the producer succeeds and BEFORE the edge critic**, both inside the pre-persist staging window (so persist stays the single gate). The current code has exactly one branch point (`if (criticConfig)`) where a node check would be inserted ahead of the `runCriticPanelLoop`/`runCriticLoop` dispatch.

**Evidence:**

```js
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { ... return false }
  // Edge-critic loop (RUS-55): runs BETWEEN produce-success and the persist gate ...
  if (criticConfig) {
    const cr = criticConfig.lenses?.length
      ? await runCriticPanelLoop(name, id, criticConfig)
      : await runCriticLoop(name, id, criticConfig)
    if (!cr || !cr.ok) { ... return false }
    criticConfig.residualFindings = cr.residualFindings
    if (cr.summary) criticConfig.criticSummary = cr.summary
  }
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { ... return false }
```

— `.claude/workflows/qrspi-batch.js:866-897`

**Dependencies:** `runPhase` → `agent`, `runCriticLoop`/`runCriticPanelLoop`, `persistArtifact` → `scripts/qrspi_persist.py`.
**Implicit contracts:** All critic/validator work happens on the **staged** file `stg(id,name)` (`/tmp/phase-stage/<id>/<name>.md`) BEFORE persist, so a failed check leaves nothing persisted and `runPhase` returns `false` (the ticket stops). A node check must therefore (a) read the staged path, not the canonical one, and (b) return a boolean-style result `runPhase` can gate on, matching the existing `if (!cr || !cr.ok) return false` pattern.

## Q3: How is the staged artifact path for each planning phase (questions.md, research.md, structure.md, plan.md) resolved and handed to a critic, given the staging-then-persist convention?

**Answer:** The staged path is `stg(id, name) => `/tmp/phase-stage/${id}/${name}.md`` (token-free, no "qrspi" token — Fix A). The producer is told to write there via `OUTPUT_PATH = ${stg(t.id, '<name>')}` in its phase prompt. The critic loop independently recomputes `stg(id, name)` as `artifactPath` (it does NOT receive it on `criticConfig`). The **upstream** anchor handed to the critic is the PRIOR phase's already-persisted CANONICAL path, `art(wd, id, '<name>.md') => `${wd}/.qrspi/${id}/${name}.md``. So the critic compares: produced = staged `stg`, upstream = persisted `art`. After the critic loop, `persistArtifact(id, name, ...)` invokes `scripts/qrspi_persist.py --ticket <id> --artifact <name>`, which moves `stg` → `art` (the script owns the qrspi-laden dest and verifies non-empty).

**Evidence:**

```js
const tpl = (wd, name) => `${wd}/.qrspi/templates/${name}`
const art = (wd, id, name) => `${wd}/.qrspi/${id}/${name}`
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:525-531`

```js
  if (!await runPhase('research', 'qrspi-research',
    `TICKET_ID = ${t.id}
QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
OUTPUT_PATH = ${stg(t.id, 'research')}
TEMPLATE_PATH = ${tpl(wd, 'research.md')}
REPO_ROOT = ${wd}
...`, r.existing, t.id, 'Design')) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:1027-1034`

**Dependencies:** `stg`/`art` helpers; `scripts/qrspi_persist.py` (`staging_path`, `dest_path`, `persist`); `STAGE_ROOT = "/tmp/phase-stage"` kept in sync between JS `stg()` and the Python script.
**Implicit contracts:** The staging path must contain NO "qrspi" token (the weak worker mangles it). `qrspi_persist.py` accepts `--artifact` only from a fixed allow-list `ARTIFACTS = ["questions","research","design","structure","plan","worktree"]` (`scripts/qrspi_persist.py:52`). A critic/validator runs against `stg` while the canonical `art` upstream already exists.

## Q4: What invocation contract do the existing design-stage edge critics expose (inputs, verdict schema), so the four new single edge critics conform to the same `parse_critic_verdict` / CRITIC_VERDICT_SCHEMA shape?

**Answer:** The design-stage critics are four LENS agents (`qrspi-design-critic-{completeness,internal-consistency,edge-alignment,simplicity}`), each `tools: Read` only. Each is spawned by `runCriticPanelLoop` with four input paths — `DESIGN_PATH` (= staged `stg(id,'design')`), `TICKET_CONTENT_PATH`, `RESEARCH_PATH` (= `criticConfig.upstreamPath`), `QUESTIONS_PATH` — and `schema: CRITIC_VERDICT_SCHEMA`. The single foundation critic `qrspi-critic` takes `UPSTREAM_PATH` + `ARTIFACT_PATH` (+ optional `RUBRIC`), same schema. The verdict schema is `{ pass: boolean (required), findings: array<string> (required) }`. `pass:true` ⇒ findings SHOULD be empty; `pass:false` ⇒ findings MUST be non-empty, each a self-contained string naming the specific upstream item dropped/contradicted/distorted. The Python-side canonical shape is `parse_critic_verdict` / `_coerce_verdict` → `{pass: bool, findings: list}` (fail-closed to NOT-passed). Four new single edge critics should mirror `qrspi-critic`'s `{ UPSTREAM_PATH, ARTIFACT_PATH, RUBRIC? }` contract and emit `CRITIC_VERDICT_SCHEMA`.

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

```yaml
name: qrspi-design-critic-completeness
claude:
  tools: Read
```

— `.claude/agents/qrspi-design-critic-completeness.md:2-5`

**Dependencies:** Verdict consumed by `criticDecision` → `scripts/qrspi_critic_loop.py` (`next_action`, `_coerce_verdict`). Panel verdicts additionally reduced by `scripts/qrspi_critic_synthesize.py`.
**Implicit contracts:** Each lens id maps by string convention to `agentType = `qrspi-design-critic-${lens}`` (`.claude/workflows/qrspi-batch.js:691`); an unknown lens name would fail to spawn, hence the `KNOWN_DESIGN_LENSES` allow-list. Agents must read ONLY their declared input paths, write no files, call no MCP tools, and return only the structured verdict (`.claude/agents/qrspi-critic.md:44-53`).

## Q5: What command-line interface and exit-code convention do existing self-locating stdlib scripts follow (e.g., `qrspi_persist.py`, `qrspi_resolve.py`), which `qrspi_verify_citations.py` must match to integrate as a node check?

**Answer:** Convention (shared by `qrspi_persist.py`, `qrspi_config.py`, `qrspi_critic_loop.py`, etc.): stdlib-only (`argparse`, `json`, `sys`, `os`/`pathlib`); self-locate the repo root from `__file__` (never cwd, never a trusted arg) — `qrspi_persist.py`/`qrspi_paths.py` use `qrspi_paths.resolve_repo_root()` (git-common-dir first, `__file__` parent last resort); `qrspi_config.py` uses `Path(__file__).resolve().parents[1]`. Output is a SINGLE JSON envelope on stdout, typically `{ ok: bool, ..., error?: str }`. Exit code: `return 0 if error is None else 1` (`main()` returns the int, `sys.exit(main())`). On error, print the envelope with `ok:false` and a verbatim `error` string — reported ONCE, never retried. Pure helpers are factored out for unit testing (no I/O), and a thin `main()` CLI wraps them. `qrspi_verify_citations.py` must: be stdlib-only, self-locate its root, expose pure parse/resolve helpers, accept short token args (e.g. `--ticket`/`--artifact` or a file path), and print `{ ok, ... , error? }` with exit 0/1.

**Evidence:**

```python
def main():
    ...
    bytes_written, error = persist(src, dest)
    env = { "ok": error is None, "repoRoot": repo_root, "src": src, "dest": dest, "bytes": bytes_written }
    if error is not None: env["error"] = error
    json.dump(env, sys.stdout, indent=2); print()
    return 0 if error is None else 1
if __name__ == "__main__":
    sys.exit(main())
```

— `scripts/qrspi_persist.py:97-137`

```python
REPO_ROOT = Path(__file__).resolve().parents[1]
...
print(json.dumps({"ok": True, "key": key, "value": value})); return 0
... print(json.dumps({"ok": False, "key": key, "value": None, "error": str(exc)})); return 1
```

— `scripts/qrspi_config.py:29,71-75`

**Dependencies:** `qrspi_paths.resolve_repo_root` (shared self-locating helper, git-common-dir-first); `argparse`/`json`/`sys` stdlib.
**Implicit contracts:** The JS glue runs these via a worker that types ONE verbatim command and returns stdout JSON; the script must therefore emit exactly one JSON object and nothing else. `ok:false` is a HARD STOP for the worker (no retry/improvise). Pure functions are kept side-effect-free so `_test.py` siblings exercise them in-memory.

## Q6: How does the batch dispatch decide between a critic panel (cardinality > 1) and a single edge critic (cardinality = 1), and what config key gates `maxRounds`?

**Answer:** `runPhase` dispatches on `criticConfig.lenses?.length`: a non-empty `lenses` array routes to `runCriticPanelLoop` (multi-lens panel — design only); its absence routes to `runCriticLoop` (single critic — plan today). So the "panel vs single" switch is presence-of-`lenses`, not a numeric cardinality field. `maxRounds` is read from `criticConfig.maxRounds ?? 2` inside BOTH loops (default 2). For design specifically, `maxRounds` and `lenses` come from `.qrspi/config.json` `critics.design` via `readDesignCriticConfig` → `parseCriticConfig` (extracts top-level `critics` envelope, returns `value.design`) → `resolveDesignCritic` (config-value > JS-default precedence; `maxRounds` is a positive integer from `cfg.maxRounds` else 2; `lenses` filtered to `KNOWN_DESIGN_LENSES`, falling back to the default four). Plan's single critic hard-codes `maxRounds: 2` with no config read.

**Evidence:**

```js
    const cr = criticConfig.lenses?.length
      ? await runCriticPanelLoop(name, id, criticConfig)
      : await runCriticLoop(name, id, criticConfig)
```

— `.claude/workflows/qrspi-batch.js:878-880`

```js
function resolveDesignCritic(design) {
  const cfg = design && typeof design === 'object' ? design : {}
  const maxRounds = Number.isInteger(cfg.maxRounds) && cfg.maxRounds > 0 ? cfg.maxRounds : 2
  let lenses = DEFAULT_DESIGN_LENSES
  if (Array.isArray(cfg.lenses)) { ... lenses = known.length ? known : DEFAULT_DESIGN_LENSES }
  return { maxRounds, lenses }
}
```

— `.claude/workflows/qrspi-batch.js:358-376`

**Dependencies:** `readDesignCriticConfig` → worker → `scripts/qrspi_config.py --key critics`; `parseCriticConfig`, `resolveDesignCritic`, `DEFAULT_DESIGN_LENSES`/`KNOWN_DESIGN_LENSES`.
**Implicit contracts:** Only `critics.design` is read today; there is NO per-phase config read for questions/research/structure/plan. The config override is opt-in and best-effort (any parse failure ⇒ JS defaults, never gates the run). `maxRounds` is gated on being a positive integer; a non-positive or non-integer value silently falls back to 2.

## Q7: How is a critic's pass/fail verdict propagated back into the phase result, and what determines whether a failed critic blocks submit versus revises and retries up to `maxRounds`?

**Answer:** Inside the loop, each round computes a verdict, then delegates the converge/revise/cap decision to `criticDecision([verdict], round, maxRounds)` → `scripts/qrspi_critic_loop.py next_action`. The pure rule: `pass` truthy ⇒ `converged` (return `{ ok:true, residualFindings:[] }`, exit loop). Not passed AND `round+1 >= maxRounds` ⇒ `cap_reached` (return `{ ok:true, residualFindings: <latest findings> }` — the artifact is STILL finalized, findings surfaced to the PR body). Not passed AND rounds remain ⇒ `revise`: spawn a reviser (the producer re-prompted with findings) to REWRITE `stg(id,name)` in place, then re-critique next iteration. A failed AGENT SPAWN (critic/reviser/synthesize returns null) ⇒ `{ ok:false }`, which `runPhase` treats as a phase failure (`return false` → `failTicket`). So a failing critic does NOT block submit per se — it either converges, revises-then-retries up to the cap, or hits the cap and finalizes WITH residual findings in the body. Only an infrastructure/spawn failure blocks. `runPhase` writes `criticConfig.residualFindings = cr.residualFindings` (and `criticConfig.criticSummary = cr.summary`) back onto the caller's config object; `doDesign`/`doPlan` then splice those into the finalize commit body via `criticBodyStep`.

**Evidence:**

```js
    const decision = await criticDecision([verdict], round, maxRounds)
    if (!decision) { ... return { ok: false, residualFindings: [] } }
    if (decision.action === 'converged') { ... return { ok: true, residualFindings: [] } }
    if (decision.action === 'cap_reached') { ... return { ok: true, residualFindings: decision.residual_findings } }
    // action === 'revise': spawn a reviser to rewrite stg(id, name) in place ...
```

— `.claude/workflows/qrspi-batch.js:612-639`

```python
    if latest["pass"]: return {"action": "converged", "residual_findings": []}
    if int(round) + 1 >= int(max_rounds):
        return {"action": "cap_reached", "residual_findings": list(latest["findings"])}
    return {"action": "revise", "residual_findings": list(latest["findings"])}
```

— `scripts/qrspi_critic_loop.py:107-113`

**Dependencies:** `runCriticLoop`/`runCriticPanelLoop` → `criticDecision` → `qrspi_critic_loop.py`; `runPhase` write-back; `criticBodyStep` → `qrspi_critic_body.py` (PR-body splice at commit time).
**Implicit contracts:** `next_action` fails closed — an empty/garbled verdict reads as NOT-passed, so a missing verdict can never report `converged`. Residual findings only ever surface on `cap_reached`; `converged` carries none. PR-body seeding happens at `gt submit` creation only, so findings must be in the commit message BEFORE submit.

## Q8: Where is `critics.design` configured today and how is the per-phase critic config (questions/research/structure/plan) read from `.qrspi/config.json` given the single-top-level-key limitation of the config reader?

**Answer:** `critics.design` is configured in `.qrspi/config.json` (gitignored) under a top-level `critics` object, documented in `.qrspi/config.example.json` (`critics.design.maxRounds`, `critics.design.lenses`). The config reader `qrspi_config.py` is SINGLE-TOP-LEVEL-KEY only — `--key critics.design` would not dot-path; the JS reads `--key critics` and round-trips the WHOLE `critics` object as `{"ok":true,"key":"critics","value":{...}}`, then `parseCriticConfig` extracts `value.design` in JS. There is **no per-phase config read for questions/research/structure/plan today** — only `critics.design`. To add per-phase config (e.g. `critics.research`), the same mechanism applies: read `--key critics` once, then index `value.<phase>` in JS. Note `select_value` returns the raw value when truthy — a non-empty dict IS truthy and round-trips intact as JSON, so an OBJECT value (the whole `critics` block) survives `qrspi_config.py` even though the reader is "single-key"; only DOT-PATHS are unsupported, not object values.

**Evidence:**

```json
  "critics": {
    "design": { "maxRounds": 2, "lenses": ["completeness", "internal-consistency", "edge-alignment", "simplicity"] }
  }
```

— `.qrspi/config.example.json` (critics block)

```python
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`

```js
// qrspi_config.py is single-top-level-key only — `--key critics.design` returns the default;
// `--key critics` round-trips the whole object as {"ok":true,"key":"critics","value":{...}}
function parseCriticConfig(text) {
  ... if (env.key !== 'critics') return undefined
  const design = value.design
  if (!design || typeof design !== 'object' || Array.isArray(design)) return undefined
  return design
}
```

— `.claude/workflows/qrspi-batch.js:329-348`

**Dependencies:** `readDesignCriticConfig` → `qrspi_config.py --key critics`; `parseCriticConfig` extracts `.design`.
**Implicit contracts:** `parseCriticConfig` hard-codes `env.key === 'critics'` and `value.design`; a per-phase extension must generalize the `.design` index. `value` may be `""` when the key is absent (the JS guards `typeof value !== 'object'`). Note the type hint `select_value(...) -> str` is INACCURATE for object values (see Inconsistencies).

## Q9: What citation formats appear in real `research.md` artifacts (`file:line`, bare `file`, symbol references), and how should the validator parse each form to determine resolvability?

**Answer:** No `qrspi_verify_citations.py` exists yet (NOT FOUND in `scripts/`). From real `.qrspi/RUS-*/research.md` artifacts, citation tokens appear in backticks in these forms: (1) **`file:line`** and **`file:start-end`** — the dominant Evidence-block form the template prescribes (`— \`path:line\`` or `— \`path:start-end\``), e.g. `scripts/run_eval.py:116-137`, `.claude/skills/qrspi-work/SKILL.md:282`; 1226 such `file:line` tokens across artifacts. (2) **Bare file** paths — `SKILL.md`, `scripts/qrspi_resolve.py`, `.claude/CLAUDE.md` (no line). (3) **Glob / wildcard / placeholder** forms — `scripts/qrspi_*_test.py`, `.claude/agents/<name>.md`, `.claude/skills/*/SKILL.md` (944 tokens containing `*` or `<...>`). The template's canonical Evidence citation is the em-dash form `— \`<file_path>:<start_line>-<end_line>\`` (`.qrspi/templates/research.md:16`). A validator should: parse the trailing `:N` or `:N-M` to split path from line range; resolve path relative to the worktree root; treat bare-file as path-only (existence check); and SKIP/EXCLUDE glob/placeholder forms (containing `*`, `<`, `>`) as non-literal — they are illustrative, not resolvable references.

**Evidence:**

```
— `.claude/skills/qrspi-research/SKILL.md:1-7`
— `scripts/run_eval.py:116-137`
— `.claude/agents/qrspi-research.md:58`
— `scripts/qrspi_pr_state.py:142`
— `README.md:78-96`
```

— sampled from `.qrspi/RUS-*/research.md` (em-dash Evidence citations)

```
## Q1: ...
**Evidence:**
...
— `<file_path>:<start_line>-<end_line>`
```

— `.qrspi/templates/research.md:7-16`

**Dependencies:** None yet — the validator script does not exist. Real artifacts under `.qrspi/RUS-*/research.md` are the corpus.
**Implicit contracts:** Backtick-wrapped tokens with a trailing `:N`/`:N-M` are the resolvable form. Glob (`*`) and placeholder (`<...>`) tokens are NOT literal files and must be excluded to avoid false failures. The em-dash prefix `— ` marks the canonical Evidence citation but is not universal (inline `file:line` mentions also occur).

## Q10: How does a `file:line` citation resolve when the file exists but the line number exceeds the file length, and what is the verbatim-citation failure output expected on a non-resolving reference?

**Answer:** NOT FOUND — `scripts/qrspi_verify_citations.py` does not exist yet, so there is no current behavior for a line-number-out-of-range citation, nor a defined failure-output format. (Searched: `grep -rln "verify_citations|citation" scripts/` — only doc/agent prose mentions citations, no validator script.) The closest established convention to model is the QRSPI script envelope: a failure surfaces as a single `{ ok:false, ..., error:"<verbatim>" }` JSON object (e.g. `qrspi_persist.py`'s `"staged artifact not found or unreadable: %s"` / `"staged artifact is empty: %s"` style — `scripts/qrspi_persist.py:81-83`). A new validator would presumably: read the cited file, count its lines, and if the cited line > line count, mark that citation unresolved, reporting the verbatim citation token plus the actual line count in an `error`/findings field. The "verbatim-citation failure output" the question presumes is a design choice this ticket must DEFINE, not an existing fact.

**Evidence:**

```python
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
```

— `scripts/qrspi_persist.py:78-83` (model for verbatim error strings)

**Dependencies:** None (script absent). Pattern source: `qrspi_persist.py`, `qrspi_config.py` envelope conventions.
**Implicit contracts:** Per established convention an unresolved citation should fail closed and report the exact offending token verbatim (so a reviser can act without re-deriving it), mirroring the critic-findings "self-contained string" rule (`.claude/agents/qrspi-critic.md:42`).

## Q11: What is the worktree root the citation validator resolves paths against, and how does it behave for citations to deleted, renamed, or not-yet-created files within the same stack?

**Answer:** NOT FOUND for the validator itself (script absent). But the self-locating root convention is established: `qrspi_paths.resolve_repo_root()` (used by `qrspi_persist.py`) resolves via precedence `--repo-root` (validated) → **git-common-dir** auto-detect from cwd (validated) → `__file__`-parent fallback. CRITICAL CAVEAT for this ticket: `_git_common_dir` returns the *shared* git dir — i.e. the **MAIN checkout, NOT the worktree** — even when invoked from a worktree (`scripts/qrspi_paths.py:57-65` docstring: "returns the *shared* ... root"). `qrspi_persist.py` reflects this: its `dest_path` is `<repo_root>/.worktrees/<ticket>/.qrspi/<ticket>/...` — it explicitly re-prepends `.worktrees/<ticket>` because `repo_root` is the main checkout. A citation validator that must resolve `file:line` against the WORKTREE working tree therefore must NOT use the bare `resolve_repo_root()` result; it must either take the worktree dir explicitly (like `runPhase` passes `wd = r.worktreeDir` / `REPO_ROOT = ${wd}` to the research producer) or reconstruct `<root>/.worktrees/<ticket>`. Behavior for deleted/renamed/not-yet-created files in the same stack is UNDEFINED (no script) — but note research runs against the worktree's CURRENT tree, where stacked-but-uncommitted later-slice files may not yet exist; a citation to a not-yet-created file would fail an existence check.

**Evidence:**

```python
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket, "%s.md" % artifact)
```

— `scripts/qrspi_persist.py:67-71` (repo_root is MAIN checkout; worktree path is reconstructed)

```python
    common = _git_common_dir(cwd=cwd)
    if common:
        if validate: _validate_root(common)
        return common
    return os.path.dirname(engine_root())  # last resort
```

— `scripts/qrspi_paths.py:136-143`

```js
REPO_ROOT = ${wd}
Project scope: explore ONLY files under ${wd}. ...
```

— `.claude/workflows/qrspi-batch.js:1032-1034` (research producer is scoped to `wd = r.worktreeDir`)

**Dependencies:** `qrspi_paths.resolve_repo_root`, `_git_common_dir`, `_validate_root`; `r.worktreeDir` from `qrspi_resolve.py` envelope.
**Implicit contracts:** git-common-dir = MAIN checkout, not worktree. Any worktree-relative path resolution must add `.worktrees/<ticket>` or accept an explicit worktree root. The research producer already operates with `REPO_ROOT = wd` (worktree), so its citations are worktree-relative; the validator must resolve against the SAME `wd`.

## Q12: How does the phase behave when a planning phase has no upstream artifact yet (e.g., questions, whose upstream is the ticket rather than a prior artifact), and does the edge-critic rubric handling differ for that case?

**Answer:** The QUESTIONS phase's upstream is the TICKET, not a prior artifact: `doDesign` passes `TICKET_ID` + `TICKET_CONTENT_PATH = ${r.ticketContentPath}` to the questions producer, and calls `runPhase('questions', ...)` with **NO `criticConfig`** (the 7th arg is omitted), so the critic block is skipped entirely — questions has no edge critic today. By contrast the design panel uses `ticketContentPath` as a lens input (`TICKET_CONTENT_PATH = r.ticketContentPath`) alongside research/questions. So the "upstream is the ticket" case is handled by passing `r.ticketContentPath` as the upstream anchor (the design panel already does this). For a NEW questions edge critic, the upstream `upstreamPath` would be `r.ticketContentPath` (the ticket content file the resolver materialized) rather than an `art(wd,id,...)` artifact path. The rubric handling is the same `{pass, findings}` edge contract; only the source of the upstream path differs (ticket-content file vs prior artifact). `r.ticketContentPath` is supplied by `qrspi_resolve.py` (the resolver writes the ticket content to a file so phases never re-fetch Linear).

**Evidence:**

```js
  if (!await runPhase('questions', 'qrspi-questions',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}

OUTPUT_PATH = ${stg(t.id, 'questions')}
TEMPLATE_PATH = ${tpl(wd, 'questions.md')}`, r.existing, t.id, 'Design')) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:1020-1025` (no criticConfig arg)

```js
  const designCritic = {
    upstreamPath: art(wd, t.id, 'research.md'),
    ...
    ticketContentPath: r.ticketContentPath,
    questionsPath: art(wd, t.id, 'questions.md'),
  }
```

— `.claude/workflows/qrspi-batch.js:1043-1049`

**Dependencies:** `r.ticketContentPath` from `qrspi_resolve.py` envelope; `runPhase` criticConfig dispatch.
**Implicit contracts:** A phase whose upstream is the ticket must use `r.ticketContentPath` (a materialized file), NOT a `.qrspi/<id>/*.md` artifact. The research phase is itself ticket-blind (the ticket is hidden — `.claude/workflows/qrspi-batch.js:1034`), so a research edge critic anchored on the ticket would VIOLATE the research firewall; research's upstream is questions.md (`art(wd,id,'questions.md')`), not the ticket.

## Q13: What patterns do the existing `scripts/qrspi_*_test.py` stdlib-only tests use for fixture construction and for asserting exit codes, that `qrspi_verify_citations_test.py` should follow for resolving vs. broken file/line/symbol cases?

**Answer:** Two patterns coexist. (A) PURE-FUNCTION tests (the majority, e.g. `qrspi_critic_loop_test.py`, `qrspi_config_test.py`): `sys.path.insert(0, _HERE)`, import the pure functions directly, call them with in-memory dicts/strings, and assert equality — NO subprocess, NO real CLI. `qrspi_critic_loop_test.py` uses a hand-rolled `check(label, got, want)` with `failures`/`total` counters and prints `ok:`/`FAIL:`; `qrspi_config_test.py` uses `unittest.TestCase` with `assertEqual` and a `_write_config(root, ...)` temp-dir helper. (B) For subprocess-touching scripts, the subprocess/gh/git calls are STUBBED (e.g. `qrspi_paths_test.py` swaps `qrspi_paths.subprocess.run` with a fake; `qrspi_critic_body_test.py`/`qrspi_pr_body_test.py` explicitly note "subprocess-backed parts ... are intentionally NOT tested here") OR a real `subprocess.run(["git", ...])` against a temp git repo is used with a `git --version` guard (`qrspi_cleanup_test.py:113-121`). `qrspi_verify_citations_test.py` should follow (A): factor pure parse/resolve helpers, build temp files via `tempfile`/`_write_*` helpers, and assert resolving (existing file + in-range line) vs broken (missing file / out-of-range line / glob-excluded) cases in-memory; reserve exit-code assertions for a thin CLI smoke test if any.

**Evidence:**

```python
_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from qrspi_critic_loop import (next_action, parse_critic_verdict)
def check(label, got, want):
    global failures, total; total += 1
    if got == want: print("ok: %s" % label)
    else: failures += 1; print("FAIL: %s\n   got:  %r\n   want: %r" % (label, got, want))
```

— `scripts/qrspi_critic_loop_test.py:17-37`

```python
        rc = subprocess.run(["git", "--version"], capture_output=True).returncode
        ...
    res = subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)
```

— `scripts/qrspi_cleanup_test.py:113-121` (real-git-in-tempdir pattern, guarded)

**Dependencies:** stdlib `os`, `sys`, `json`, `unittest`/`tempfile`/`subprocess`; the script-under-test imported via `sys.path.insert`.
**Implicit contracts:** Tests are stdlib-only, no third-party deps, run via `python3 scripts/<name>_test.py`. Pure functions are the unit-test surface; subprocess/gh/git is stubbed or temp-dir-isolated. Each `_test.py` is a sibling of its script (`scripts/qrspi_*_test.py`).

## Q14: How are the existing critic-rubric wirings unit-tested with stubs, so the four new edge-critic wirings can be verified the same way?

**Answer:** The JS wiring in `qrspi-batch.js` (`runCriticLoop`, `runCriticPanelLoop`, `runPhase` dispatch, `parseCriticConfig`, `resolveDesignCritic`) has **NO JS unit tests** — there is no test harness for `.claude/workflows/qrspi-batch.js` (no `*.test.js`, and `CLAUDE.md` states the JS orchestration is verified by "manual end-to-end runs"). What IS unit-tested is the PURE PYTHON the wiring delegates to: `qrspi_critic_loop_test.py` (the `next_action` converge/revise/cap decision + `parse_critic_verdict` fail-closed parsing, covering pass-first-round/fail→revise→pass/fail-at-cap/malformed) and `qrspi_critic_synthesize_test.py` (the M-lens reduction). So "critic-rubric wirings are unit-tested" only insofar as the DECISION core is; the JS glue (lens fan-out, agentType string mapping, criticConfig assembly) is not unit-tested. Four new edge-critic wirings should follow the SAME split: push any new decision/parse logic into a pure, tested Python module (or reuse `qrspi_critic_loop.py`), and verify the JS glue by manual e2e — OR, if the new logic is the citation NODE check, fully unit-test `qrspi_verify_citations.py` as a pure Python sibling.

**Evidence:**

```python
"""Unit tests for qrspi_critic_loop pure decision core: next_action's converge/revise/
cap_reached decision and parse_critic_verdict's fail-closed parsing. ...
Covers (ref: structure §Slice 1 tests, ...): pass-first-round ⇒ converged ...
  - fail at cap ⇒ cap_reached surfacing residual findings (AC2, AC4)
  - malformed/empty/garbage verdict ⇒ fail closed to NOT-passed, never raises (Q11)"""
```

— `scripts/qrspi_critic_loop_test.py:2-12`

```
- The `evals/` + `scripts/run_eval.py` harness is a non-functional placeholder — verify
  pure logic with the unit tests and orchestration changes with manual end-to-end runs
```

— `.claude/CLAUDE.md` (Codebase conventions)

**Dependencies:** `qrspi_critic_loop_test.py`, `qrspi_critic_synthesize_test.py` (pure-module tests). No JS test runner exists.
**Implicit contracts:** All testable logic must live in pure Python modules with `_test.py` siblings; the JS orchestrator delegates to them and is NOT unit-tested. New wiring should keep testable logic out of the JS.

## Q15: How is per-round critic logging emitted today (the per-round logging added with `critics.design`), and where are per-phase eval scores recorded so before/after numbers can be reported per the acceptance criteria?

**Answer:** Per-round logging uses the ambient `log(...)` harness builtin (a workflow-runner global; not defined in `qrspi-batch.js`). Both loops emit a per-round line: e.g. `${id}: ${name} panel round ${round+1}/${maxRounds} → PASS / FAIL (P/N lenses passed, K finding(s))`, plus REVISE / CONVERGED / CAP-REACHED lines, and a `summaryRounds` array (`r1:pass`, `r2:2/4`, ...) folded into the return `summary`. That summary is folded into the ticket result via `out.summary = `${out.summary} [${designCritic.criticSummary}]`` (`.claude/workflows/qrspi-batch.js:1077`). The design panel also logs its lens set + maxRounds up front (`design critic panel — N lens(es) [...], maxRounds M`, line 1050). For EVAL SCORES: the `evals/` + `scripts/run_eval.py` harness is a **non-functional placeholder** (per `.claude/CLAUDE.md` and project memory `eval-harness-placeholder.md`). `evals/suite.json`/`graphite-evals.json` + `evals/golden/`/`evals/fixtures/` exist, and `run_eval.py` has an `ExecutionResult` dataclass with `metrics`/`duration_ms`, but the harness is NOT wired to produce trustworthy before/after per-phase scores. So "before/after numbers per the acceptance criteria" cannot be sourced from a working eval harness today — they must come from the per-round `log()` output and manual e2e observation, NOT from `run_eval.py`.

**Evidence:**

```js
    log(`  ${id}: ${name} panel round ${round + 1}/${maxRounds} → ${passed ? 'PASS' : `FAIL (${passCount}/${lenses.length} lenses passed, ${synthFindings.length} finding(s))`}`)
    summaryRounds.push(`r${round + 1}:${passed ? 'pass' : `${passCount}/${lenses.length}`}`)
```

— `.claude/workflows/qrspi-batch.js:729-730`

```js
    if (designCritic.criticSummary) out.summary = `${out.summary} [${designCritic.criticSummary}]`
```

— `.claude/workflows/qrspi-batch.js:1077`

**Dependencies:** `log` (harness global), `summaryRounds`, `finResult`/`out.summary`; `scripts/run_eval.py` + `evals/` (placeholder).
**Implicit contracts:** `log()` is the only observability surface for critic rounds — there is no structured metrics sink. The eval harness is explicitly non-functional; do not rely on it for acceptance-criteria numbers.

---

## Discovered Patterns

- **Staging firewall (Fix A):** Every phase producer writes to a token-free `stg(id,name) = /tmp/phase-stage/<id>/<name>.md`; `scripts/qrspi_persist.py` (self-locating, qrspi-token owner) moves it to the canonical `.worktrees/<id>/.qrspi/<id>/<name>.md` and is the REAL success gate. All critic/validator work runs on the STAGED file before persist (`.claude/workflows/qrspi-batch.js:531,866-897`).
- **Pure-Python-core / untested-JS-glue split:** All testable decision logic lives in self-locating stdlib-only Python modules (`qrspi_critic_loop.py`, `qrspi_critic_synthesize.py`, `qrspi_config.py`) with `_test.py` siblings exercising PURE functions in-memory; the JS orchestrator delegates via one-verbatim-command workers and is verified only by manual e2e. This is the canonical shape a new `qrspi_verify_citations.py` + test should adopt.
- **Single JSON envelope + fail-closed:** Scripts print exactly one `{ ok, ..., error? }` line, exit `0/1`, report errors verbatim ONCE, never retry. Parsers (`parse_critic_verdict`, `next_action`) fail CLOSED — malformed input ⇒ NOT-passed — so a garbled reply can never silently converge.
- **Worker-runs-one-command idiom:** Because the JS sandbox can't run python, JS spawns a worker that types ONE verbatim `python3 ${engineCmd(...)} ...` command and returns stdout JSON (`criticDecision`, `synthesizeVerdicts`, `readDesignCriticConfig`). Fragile text is passed via stdin or a staged JSON file, never echoed through heredocs.
- **Config is opt-in + best-effort:** `critics.design` overrides are read via `--key critics` (whole object) and resolved config>default; ANY parse failure silently falls back to JS defaults and NEVER gates the run.
- **Dispatch by presence, not cardinality:** `runPhase` chooses panel-vs-single on `criticConfig.lenses?.length` (truthy ⇒ panel). There is no numeric "cardinality" field — the ticket's "cardinality > 1 vs = 1" framing maps to "lenses present vs absent."
- **Lens id → agentType by string convention:** `qrspi-design-critic-${lens}`; guarded by `KNOWN_DESIGN_LENSES`. Four new single critics would presumably introduce four new `qrspi-*-critic` agent types and matching prompt files under `.claude/agents/`.

## Inconsistencies

- **`qrspi_config.py` type hint is wrong for object values.** `select_value(config, key, default) -> str` is annotated as returning `str`, but it returns `config[key]` as-is when truthy — for the `critics` key that is a DICT, not a str. The code works (a non-empty dict is truthy and JSON-serializes fine), but the `-> str` annotation and the `value: <str|null>` docstring (`scripts/qrspi_config.py:17,36`) understate the contract; the JS comment correctly notes the object round-trips (`.claude/workflows/qrspi-batch.js:330-331`).
- **"Single-top-level-key" is about DOT-PATHS, not value type.** Project memory and CLAUDE.md describe the reader as "single-top-level-key only," which is true for `--key a.b` (no dot-path), but it DOES return object-valued top-level keys intact. A plan that assumes object values can't be read would be wrong; the real limit is no nested-path indexing (the JS does the `.design` index itself).
- **No per-phase critic config exists yet, despite the questions framing.** Q6/Q8 presume a per-phase (questions/research/structure/plan) critic config and maxRounds gate; today ONLY `critics.design` is read, and only `plan` wires a single critic (hard-coded `maxRounds:2`, no config). questions/research/structure have NO critic wiring. This is the gap the ticket evidently fills.
- **`qrspi_verify_citations.py` does not exist.** Q5/Q9/Q10/Q11/Q13 target a script that is absent from `scripts/`. Its CLI, citation-parsing rules, out-of-range/line behavior, worktree-root resolution, and tests are all to-be-built, not existing facts. Searched: `grep -rln "verify_citations|citation" scripts/` (no script hits; only doc/agent prose).
- **git-common-dir returns the MAIN checkout, not the worktree.** `resolve_repo_root()`/`_git_common_dir` give the shared root; `qrspi_persist.py` re-prepends `.worktrees/<ticket>` to reach the worktree. A citation validator that naively uses `resolve_repo_root()` as "the worktree root" (Q11's phrasing) would resolve paths against the WRONG tree — it must take `wd = r.worktreeDir` explicitly or reconstruct `.worktrees/<ticket>`.
- **Research firewall vs an edge critic anchored on the ticket.** Q12 frames questions' upstream as the ticket; but the RESEARCH phase is deliberately ticket-blind (`The ticket is intentionally hidden from you`, `.claude/workflows/qrspi-batch.js:1034`). A research edge critic must anchor on questions.md, NOT the ticket, or it would breach the firewall — a constraint the design must respect.
