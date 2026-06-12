# Research — Codebase Map

**Questions source:** questions.md @ /workspaces/qrspi/.worktrees/RUS-55/.qrspi/RUS-55/questions.md
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

> All paths below are under REPO_ROOT = `/workspaces/qrspi/.worktrees/RUS-55`. The orchestrator file `.claude/workflows/qrspi-batch.js` is referenced throughout; line numbers are from that file unless stated otherwise.
>
> **Framing note (firewall):** The questions reference proposed primitives (`runCriticLoop`, a `critic` agent-type, a `{ pass, findings }` contract, per-phase critic config). **None of these exist in the codebase today** — they are the *target* of future work. Each answer maps the EXISTING facts the proposed primitive would plug into.

## Q1: How does a phase agent currently pass its produced staged artifact from `produce` through to finalize/submit inside `runPhase` in `qrspi-batch.js`, and at which point would a pre-finalize step be inserted?

**Answer:** `runPhase(name, agentType, prompt, existing, id, phaseLabel)` is the single per-artifact pipeline (`.claude/workflows/qrspi-batch.js:458-478`). Its sequence is: (1) resume short-circuit — if `existing[name]` is truthy it logs "reusing" and returns `true` without spawning anything; (2) spawn the typed phase agent via `agent(prompt, { label, phase, agentType })`; a `null` return means failed/skipped → return `false`; (3) **persist gate** — call `persistArtifact(id, name, phaseLabel)`, which deterministically moves the staged file to the canonical worktree path; a falsy/`!p.ok` result returns `false`; (4) log success and return `true`. The artifact is NOT passed in-memory between phases — each phase agent writes to a token-free **staging** path `stg(id,name)` and `persistArtifact` moves it to `.worktrees/<id>/.qrspi/<id>/<name>.md`. Downstream phases read it back off the canonical path (e.g. `doDesign` passes `QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}` to the research agent, `:607`).

A pre-finalize critic step has two natural insertion points: **(a) inside `runPhase`, between the `agent()` produce call (`:463`) and the `persistArtifact` gate (`:471`)** — i.e. critique the staged file before it is moved/committed; or **(b) inside each `doX` action (`doDesign`/`doPlan`) after all `runPhase` calls but before `phase('Finalize')`** (e.g. `doDesign` :614-623). Insertion point (a) is per-artifact and uniform; (b) is per-phase and sees the full artifact set.

**Evidence:**

```js
async function runPhase(name, agentType, prompt, existing, id, phaseLabel) {
  if (existing && existing[name]) {
    log(`  ${id}: reusing existing ${name}.md`)
    return true
  }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) {
    log(`  ${id}: ${name} phase failed or was skipped — stopping this ticket`)
    return false
  }
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { ... return false }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
}
```

— `.claude/workflows/qrspi-batch.js:458-478`
**Dependencies:** `runPhase` ← called by `doDesign` (:598-621), `doPlan` (:642-659). It calls `agent()` (runner primitive) and `persistArtifact()` (:440-453) → `scripts/qrspi_persist.py`.
**Implicit contracts:** A phase agent's contract is "write your artifact to OUTPUT_PATH (= `stg(id,name)`) and return a one-line summary string." `runPhase` treats the agent's return value as opaque except for the `null`-means-failed sentinel; the real success gate is whether a non-empty staged file exists for `persistArtifact` to move. Any inserted step must preserve: returning `false` stops the ticket (callers do `if (!await runPhase(...)) return failTicket(t)`).

## Q2: How are upstream artifact(s) for a given phase located and read today (staging paths via the `stg()` helper vs the persisted `.worktrees/<id>/.qrspi/<id>/` paths), so the critic can be handed the upstream artifact as the rubric anchor?

**Answer:** Three path helpers exist (`.claude/workflows/qrspi-batch.js:412-418`):
- `tpl(wd, name)` → `${wd}/.qrspi/templates/${name}` — template path.
- `art(wd, id, name)` → `${wd}/.qrspi/${id}/${name}` — the **canonical persisted** artifact path inside the worktree.
- `stg(id, name)` → `/tmp/phase-stage/${id}/${name}.md` — the **token-free staging** path a phase agent WRITES to (the qrspi-token-free path the weak model cannot mangle).

The convention is asymmetric and deliberate: a phase agent **writes** to `stg(...)` (its `OUTPUT_PATH`) but **reads upstream** artifacts from `art(...)` (the persisted canonical path), because `persistArtifact` has already moved the upstream file there. E.g. the research agent's `QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}` (:607); the design agent reads `QUESTIONS_PATH`/`RESEARCH_PATH` via `art(...)` (:618-619); the structure agent reads `DESIGN_PATH = ${art(wd, t.id, 'design.md')}` (:644). So an upstream artifact used as a critic rubric anchor is reliably available at `art(wd, id, '<upstream>.md')` by the time the current phase produces, because the persist gate ran for the upstream phase first.

**Evidence:**

```js
const tpl = (wd, name) => `${wd}/.qrspi/templates/${name}`
const art = (wd, id, name) => `${wd}/.qrspi/${id}/${name}`
// Token-free staging path a phase agent writes its artifact to (Fix A)...
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:412-418`

```js
  if (!await runPhase('research', 'qrspi-research',
    `TICKET_ID = ${t.id}
QUESTIONS_PATH = ${art(wd, t.id, 'questions.md')}
OUTPUT_PATH = ${stg(t.id, 'research')}
TEMPLATE_PATH = ${tpl(wd, 'research.md')}
REPO_ROOT = ${wd}
...
```

— `.claude/workflows/qrspi-batch.js:605-612`
**Dependencies:** `art`/`stg`/`tpl` are pure string builders consumed by every `doX` action. `stg` must stay in sync with `STAGE_ROOT = "/tmp/phase-stage"` in `scripts/qrspi_persist.py:57` (comment at :416-417 states this).
**Implicit contracts:** Upstream-as-rubric works only AFTER the upstream phase's persist gate has run (the file is at `art(...)`, not `stg(...)`, by then). For the SAME phase being produced, the just-written artifact is still at `stg(id,name)` and has NOT yet been moved (the persist call at `:471` happens after produce) — so a critic invoked between produce and persist must read the **staging** path `stg(id,name)`, while the upstream anchor is read from `art(wd,id,...)`.

## Q3: How is a produced artifact's persistence verified and the result surfaced back into `runPhase` (the Fix A staging + move), and does that verification gate run before or after where the critic loop would sit?

**Answer:** `persistArtifact(id, name, phaseLabel)` (:440-453) spawns a one-command PERSIST worker that runs `python3 <engine>/scripts/qrspi_persist.py --ticket <id> --artifact <name>` and returns the parsed `PERSIST_SCHEMA` envelope `{ ok, error?, dest, bytes }` (:399-408). The script (`scripts/qrspi_persist.py:74-92`, `persist()`) verifies the staged `src` exists AND is non-empty (`size == 0` → error), `shutil.move`s it to the self-located canonical `dest`, and re-checks the destination is non-empty. The move/verify is deterministic and self-locating (repo root from `__file__` / git-common-dir, not from the worker's cwd). In `runPhase`, the result is surfaced at `:471-475`: `if (!p || !p.ok) { ...return false }`. The comment at `:468-470` calls this "the real success gate."

**Ordering relative to a critic loop:** The persist gate runs **AFTER** the produce `agent()` call (`:463` produce → `:471` persist). The critic loop (per Q1) would sit BEFORE persist if inserted at point (a) — meaning it would critique/revise the **staged** file (`stg(id,name)`) while it still exists at the staging path, and only AFTER convergence (or cap) would the existing persist gate move the final version. This is consistent with the "verify the staged file is non-empty before moving" contract: a critic loop that rewrites the staging file in place leaves the persist gate's non-empty check intact.

**Evidence:**

```python
def persist(src, dest):
    try:
        size = os.path.getsize(src)
    except OSError:
        return 0, "staged artifact not found or unreadable: %s" % src
    if size == 0:
        return 0, "staged artifact is empty: %s" % src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    ...
    return out, None
```

— `scripts/qrspi_persist.py:74-92`
**Dependencies:** `runPhase` (:471) → `persistArtifact` (:440) → PERSIST worker → `scripts/qrspi_persist.py`. `PERSIST_SCHEMA` (:399-408) validates the worker's StructuredOutput.
**Implicit contracts:** Persist is idempotent-ish but **destructive of the staging file** (`shutil.move` removes `src`). A critic loop inserted before persist MUST finish all read/rewrite cycles on `stg(id,name)` before the move; once persisted the staging path is gone. Persist requires the staged file to be **non-empty** — a critic that empties or deletes the staging file would convert to a persist failure (`ok:false` → ticket stops).

## Q4: What is the existing signature and call convention for spawning a typed phase agent (e.g. the `agent()`/`parallel()`/`pipeline()` primitives) that `runCriticLoop` would reuse to invoke critic and revise agents?

**Answer:** `agent()` and `parallel()` are **runner-provided primitives** (the Workflow tool injects them; they are NOT defined anywhere in the repo — confirmed: no definition in `qrspi-batch.js`, no `package.json`, no JS module). The observed call convention is `await agent(promptString, optionsObject)`. The options object carries:
- `label` — a short identifier string (every call sets it, e.g. `` `resolve:${t.id}` ``).
- `phase` — the phase title string (must match a `phases[].title` from `meta`, set via `phase(...)` and passed here).
- `agentType` — OPTIONAL; when present it names a registered `.claude/agents/<type>` typed agent (e.g. `'qrspi-research'`); when ABSENT the call spawns a generic worker agent.
- `schema` — OPTIONAL JSON-Schema object; when present, the call returns the parsed StructuredOutput object; when absent, the call returns the agent's final message as a plain string.

`parallel(arrayOfThunks)` runs an array of `() => agent(...)` thunks concurrently and returns an array of results (used once, the Query fan-out at `:1220-1232`). `pipeline()` is **referenced only in the questions file / workflow-creator vocabulary — it is NOT used in `qrspi-batch.js`** (grep found no `pipeline(` call). A `runCriticLoop` would reuse `agent({ agentType, schema })` exactly like `persistArtifact` (a generic-worker schema'd call, :441-452) or `runPhase` (a typed-agent call, :463).

**Evidence:**

```js
const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
```

— `.claude/workflows/qrspi-batch.js:463`  (typed phase agent, no schema → string return)

```js
  return await agent(
    `You are the PERSIST worker for ${id} artifact "${name}". ...`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA }
  )
```

— `.claude/workflows/qrspi-batch.js:441-452`  (generic worker, schema → object return)

```js
const batches = await parallel(
  STATUSES.map(status => () => agent(`Use mcp__linear__list_issues ...`,
    { label: `list:...`, phase: 'Query', schema: TICKETS_SCHEMA })))
```

— `.claude/workflows/qrspi-batch.js:1220-1232`  (parallel fan-out)
**Dependencies:** `agent`/`parallel`/`phase`/`log` are injected by the Workflow runner (the `workflow-creator` skill, located OUTSIDE REPO_ROOT at `/home/vscode/.agents/skills/workflow-creator` — NOT readable under the research firewall). The `meta.phases` array (:5-14) declares the legal `phase` titles.
**Implicit contracts:** A schema'd `agent()` returns a parsed object or `null` (callers check `if (!setup || !setup.ok)` :687, `if (res === null)` :464). A non-schema `agent()` returns a string (callers parse it themselves, e.g. `parseResolveEnvelope(out, ...)` :547). Per the header comment (:20-26), the workflow RUNNER can spawn registered `agentType`s but a workflow SUBAGENT cannot — so all typed-agent spawning must originate from this script.

## Q5: How are agent-type contracts currently defined and registered (where phase agent definitions live), so a new `critic` agent-type with a StructuredOutput schema can be added consistently?

**Answer:** Typed phase agents are Markdown files in `.claude/agents/` with YAML frontmatter, one per type: `qrspi-questions.md`, `qrspi-research.md`, `qrspi-design.md`, `qrspi-structure.md`, `qrspi-plan.md`, `qrspi-worktree.md`, `qrspi-implement.md`, `qrspi-pr.md`. The frontmatter declares `name:` (the agentType string passed to `agent({ agentType })`), `description:`, and `claude.tools:` (the tool allowlist). The body is the system prompt. Registration is **by file presence + the `name:` field** — there is no central registry/manifest; `agent({ agentType: 'qrspi-research' })` resolves to `.claude/agents/qrspi-research.md` by its `name`. A new `critic` agent-type would be added as `.claude/agents/qrspi-critic.md` with `name: qrspi-critic` and an appropriate `tools:` list (a critic likely needs `Read` only, plus `Write` if it stages a verdict). Its slash-command wrapper would live under `.claude/skills/` (the convention: "Phase agent definitions live in `.claude/agents/`; their slash-command wrappers live in `.claude/skills/`" — `.claude/CLAUDE.md` Codebase conventions). Note: the agent `.md` files define NO StructuredOutput schema themselves — the schema is declared in `qrspi-batch.js` and passed at the call site (see Q6).

**Evidence:**

```
---
name: qrspi-research
description: Internal QRSPI workflow agent — maps codebase facts...
claude:
  tools: Read, Write, Glob, Grep
---
```

— `.claude/agents/qrspi-research.md:1-6`

```
---
name: qrspi-questions
...
claude:
  tools: Read, Write
---
```

— `.claude/agents/qrspi-questions.md:1-6`
**Dependencies:** `.claude/agents/*.md` ← referenced by `agentType` strings in `doDesign`/`doPlan`/`doImplementation`. Slash-command wrappers in `.claude/skills/qrspi-*/` (8 directories exist). Templates the agents reference live in `.qrspi/templates/` (10 files).
**Implicit contracts:** The agent body is prompt-driven and consumes `KEY = value` inputs spliced into the prompt by the orchestrator (e.g. `TICKET_ID`, `OUTPUT_PATH`, `TEMPLATE_PATH`, `REPO_ROOT`). A new critic agent must: declare a `name:` matching the `agentType` string used in JS; restrict `tools:` to what it needs; write any staged output to a token-free path it is handed (the Fix A convention) if its output must be persisted. There is NO StructuredOutput declaration inside the `.md` — validation is the caller's via the `schema` option (Q6).

## Q6: How are StructuredOutput schemas currently declared and validated for existing agents, and what mechanism would validate the `{ pass: bool, findings: [...] }` findings contract?

**Answer:** StructuredOutput schemas are plain JS-object JSON-Schemas declared as `const`s in the `--- schemas ---` section of `qrspi-batch.js` (:149-408): `TICKETS_SCHEMA` (:151), `WORKER_SCHEMA` (:336), `IMPL_SETUP_SCHEMA` (:348), `SLICE_COMMIT_SCHEMA` (:373), `COMMENT_REPLY_SCHEMA` (:387), `PERSIST_SCHEMA` (:399), `RECONCILE_CANDIDATES_SCHEMA` (:1076). Each has `type:'object'`, a `required:[...]` list, and `properties:{...}` with per-field `{ type: ... }`. Validation is performed by the **runner** when the schema is passed as `agent(prompt, { schema })` — a valid result returns the parsed object; an invalid/empty result returns `null` (callers then branch on `if (!x || !x.ok)`).

A `{ pass: bool, findings: [...] }` critic contract would be declared the same way: a new `const CRITIC_SCHEMA = { type:'object', required:['pass','findings'], properties:{ pass:{type:'boolean'}, findings:{ type:'array', items:{ type:'object', required:[...], properties:{...} } } } }` and passed via `agent(criticPrompt, { agentType:'qrspi-critic', schema: CRITIC_SCHEMA })`.

**Important caveat (documented failure mode):** The codebase has a recurring pattern of **abandoning StructuredOutput for a weak worker model** because it "could not populate the StructuredOutput tool — it emitted an empty {} and looped against schema validation, stalling the whole batch" (:171-176). For RESOLVE/RESTACK/CLEANUP/CONFIG/LAND-VERIFY/ORDER, the schema path was replaced with **"return JSON as plain text, parse it in JS"** via `extractJsonObject()` (:190-206) + a hand-written `parse*Envelope()` validator (e.g. `parseResolveEnvelope` :212-226, `parseCleanupEnvelope` :286-294, `parseLandVerdict` :300-309). So there are **two** validation mechanisms a critic could inherit: (1) the runner-validated `schema` option (used by phase/setup/commit/persist/comment-reply workers); (2) the plain-text-return + JS-side `extractJsonObject` + bespoke validator (used by the python-invoking workers that hit the weak-model schema-stall). Which to choose depends on which model runs the critic.

**Evidence:**

```js
const WORKER_SCHEMA = {
  type: 'object',
  required: ['ok', 'summary'],
  properties: {
    ok: { type: 'boolean' },
    error: { type: 'string' },
    prUrl: { type: 'string' },
    newStatus: { type: 'string' },
    summary: { type: 'string' },
  },
}
```

— `.claude/workflows/qrspi-batch.js:336-346`

```js
function parseResolveEnvelope(text, ticketId) {
  const raw = extractJsonObject(text)
  if (!raw) return { ok: false, error: 'resolve: no JSON envelope in worker output' }
  let env
  try { env = JSON.parse(raw) } catch (e) { return { ok: false, error: `resolve: unparseable envelope (${e.message})` } }
  if (typeof env.ok !== 'boolean') return { ok: false, error: 'resolve: envelope missing ok flag' }
  if (!env.ok) return env
  ...
}
```

— `.claude/workflows/qrspi-batch.js:212-226`
**Dependencies:** Schemas are passed to `agent()` (runner-validated) OR consumed by `parse*Envelope` helpers that call `extractJsonObject`/`extractJsonArray` (:190-247).
**Implicit contracts:** Schema'd-`agent()` callers treat a missing object as failure (`!x`). The plain-text validators ALWAYS return an `{ ok:false, error }` on any malformation (never throw) so a garbled echo degrades to a clean skip, not a crash — the documented "fail toward a clean ok:false" convention (:208-211, :269-276).

## Q7: How is per-phase configuration (which phase maps to which agent/template/artifact) represented in `qrspi-batch.js`, so an OPTIONAL per-phase critic configuration can be attached without affecting phases that have none?

**Answer:** There is **no declarative per-phase config table/map**. The phase→agent→template→artifact mapping is **imperative and inlined** as positional arguments to `runPhase(...)` calls inside the `doX` action functions. Each `runPhase` call hard-codes the artifact `name` (string), the `agentType` (string), the prompt (which splices `art`/`stg`/`tpl` for that artifact), and the phase label. Example — the Design action wires three artifacts in sequence (:598-621): `runPhase('questions','qrspi-questions', ...)`, `runPhase('research','qrspi-research', ...)`, `runPhase('design','qrspi-design', ...)`. The Plan action does the same for `structure`/`plan`/`worktree` (:642-659). The ONLY structured `phases` list is the descriptive `meta.phases` array (:5-14), which is documentation/UX metadata (titles + detail strings), NOT a runtime mapping.

Because the mapping is per-`runPhase`-call, an OPTIONAL critic config is most naturally attached as an **additional optional parameter to `runPhase`** (e.g. a `criticConfig` object) that defaults to absent — phases that pass nothing keep their exact current behavior (see Q9). Alternatively a small const map keyed by artifact name (e.g. `CRITICS = { design: {...}, plan: {...} }`) could be added and looked up inside `runPhase`, leaving the call sites that have no entry unaffected.

**Evidence:**

```js
  if (!await runPhase('questions', 'qrspi-questions',
    `TICKET_ID = ${t.id}
TICKET_CONTENT_PATH = ${r.ticketContentPath}
OUTPUT_PATH = ${stg(t.id, 'questions')}
TEMPLATE_PATH = ${tpl(wd, 'questions.md')}`, r.existing, t.id, 'Design')) return failTicket(t)
```

— `.claude/workflows/qrspi-batch.js:598-603`
**Dependencies:** `meta.phases` (:5-14) is descriptive only. The real mapping lives in the bodies of `doDesign` (:594-633), `doPlan` (:638-671), `doImplementation` (:676-759). `runPhase`'s signature (:458) is the single choke point all design/plan artifacts flow through.
**Implicit contracts:** `runPhase`'s positional signature is `(name, agentType, prompt, existing, id, phaseLabel)`. Adding an optional trailing parameter preserves every existing call (JS ignores absent trailing args → `undefined`). A guard `if (criticConfig) { ...loop... }` then leaves no-critic phases byte-for-byte unchanged (Q9). Implementation slices do NOT go through `runPhase` (they use `agent({agentType:'qrspi-implement'})` directly, :697-716), so a `runPhase`-attached critic naturally covers only design/plan artifacts.

## Q8: How is the human-review PR body composed today for design/plan phases (the heredoc commit message), so remaining non-converged critic findings can be appended to it?

**Answer:** For design/plan the PR **body == the branch commit message** (Graphite seeds the PR description from the commit message at creation; `gt submit` has no body flag). The body is composed inside the finalize worker's PROMPT as the commit `subject` only — there is **no separate body text** for design/plan today. `doDesign`'s finalize worker (:624-631) instructs: commit with subject `` "${t.id} [QR]: Design — ${t.title}" `` via `gt modify -c`, then `gt submit --publish`. `doPlan`'s finalize (:662-669) uses subject `` "${t.id} [SP]: Plan — ${t.title}" `` via `gt create`. Neither splices a multi-line body. (Only the IMPLEMENTATION phase builds a rich body, via `scripts/qrspi_pr_body.py` splicing `pr-summary.md` into the slice-1 commit message, :748-753 — design/plan have no analog.)

So "appending remaining non-converged critic findings to the PR body" for design/plan means **extending the finalize commit message** from a bare subject to subject + blank line + a findings body. That body would have to be assembled and handed to the finalize worker (either spliced into the prompt's commit instruction, or written to a staged file the worker reads — mirroring how `qrspi_pr_body.py` splices a file for implementation). There is no existing helper for design/plan bodies, so a new mechanism (a body string in the prompt, or a small body-splice analog) would be required.

**Evidence:**

```js
  const fin = await agent(
    `You are the DESIGN-PHASE finalize worker for ${t.id}, in ${wd}. ...
2. Stage ONLY those three artifacts; add them as the single commit (subject "${t.id} [QR]: Design — ${t.title}") on the pre-created ${t.id}/design branch with \`gt modify -c\` ...; submit the Design PR PUBLISHED with \`gt submit --publish${reviewerFlags(r)}\`...
```

— `.claude/workflows/qrspi-batch.js:624-627`

`scripts/qrspi_pr_body.py` (implementation-only) sets the slice-1 commit message to `<subject> + <body file contents> + <trailer>` and amends via `gt modify -m`, so Graphite seeds the PR body at creation — the ONLY non-interactive body lever.
— `scripts/qrspi_pr_body.py:1-29`
**Dependencies:** Design/plan finalize bodies = inline prompt strings (:627, :665). Implementation body = `scripts/qrspi_pr_body.py` (self-locating). `reviewerFlags(r)` (:428-433) splices reviewer flags.
**Implicit contracts:** The commit message is the SOLE non-interactive PR-body lever (`gt submit` has no `--body`; documented :748, `.claude/CLAUDE.md`). Whatever body is produced must survive being a heredoc/commit subject+body — i.e. multi-line findings would need the same subject/blank-line/body/trailer shape the implementation path already uses, and must avoid shell-quoting hazards (the implementation path writes findings to a FILE and splices via python precisely to dodge worker command-line quoting — the safer pattern to mirror).

## Q9: When a phase has no critic configured, what is the exact current control path through `runPhase` that must remain byte-for-byte unchanged, and what branch would guard the new step?

**Answer:** The current `runPhase` control path (the path that must remain unchanged for a no-critic phase) is exactly the four steps at `.claude/workflows/qrspi-batch.js:458-478`: (1) resume short-circuit `if (existing && existing[name]) return true`; (2) `const res = await agent(prompt, {...agentType})`; `if (res === null) return false`; (3) `const p = await persistArtifact(...)`; `if (!p || !p.ok) return false`; (4) `log(...)`; `return true`. There is no other code in the function. The guard for a new critic step would be a truthiness check on an OPTIONAL critic parameter/config — e.g. `if (criticConfig) { ...runCriticLoop... }` inserted between step 2's success and step 3 (per Q1, point (a)). With `criticConfig` absent/undefined for a phase, that `if` is skipped entirely and the function executes its current statements verbatim. The same guard pattern is already used throughout the file for optional behavior (e.g. `if (cl.ok && stranded.length) res.reconcileRetry = true` :1048; `if (out && commentSummary) {...}` :870; `if (!changeRequested) { ... }` :844).

**Evidence:**

```js
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { ... return false }
  // <-- a critic loop guarded by `if (criticConfig)` would sit here -->
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { ... return false }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
```

— `.claude/workflows/qrspi-batch.js:463-477`
**Dependencies:** Callers depend on the `true`/`false` return contract (`if (!await runPhase(...)) return failTicket(t)`, :598/:605/:614/:642/:648/:655). `existing[name]` comes from the resolver envelope's `existing{}` (:179-181) — a reused artifact must continue to skip everything (no critic either, since nothing was produced).
**Implicit contracts:** `runPhase` returns `true` on success/reuse, `false` on failure (any non-`true` stops the ticket). The resume short-circuit must NOT run a critic (no fresh artifact was produced). Adding a trailing optional param keeps the 6 existing call sites valid because JS supplies `undefined` for omitted trailing args — the guard `if (criticConfig)` is then false and the path is identical.

## Q10: How are round counters / loop caps expressed in existing deterministic JS control flow in `qrspi-batch.js`, and how does the codebase currently guard against non-terminating loops in orchestration?

**Answer:** All existing loops are **bounded by a finite collection**, never by a "retry until converged" counter — there is no `while(true)`/round-cap pattern anywhere in the file. The loop forms present are: (a) `for (let i = 0; i < tickets.length; i++)` — the main per-ticket loop (:1289); (b) `for (const s of setup.slices)` — per-slice (:694); (c) `for (let i = 0; i < targets.length; i++)` — per reviewer comment (:901); (d) `for (const id of pending)` / `for (const b of batches)` — reconcile/flatten (:1118, :1236). Termination is structural: each iterates a fixed array. The codebase's stance on non-termination at the AGENT level is the **"loop-safe termination signal"** for `revise`: re-requesting review flips `reviewDecision` to `REVIEW_REQUIRED` so the next batch pass resolves to `wait` instead of re-firing (:38-43, :806-809) — i.e. each ticket advances **at most ONE autonomous step per run** (:36-37). There is NO existing in-process bounded-retry counter to copy; a critic loop with a `maxRounds` cap would be the FIRST such construct and must introduce its own counter (e.g. `for (let round = 0; round < maxRounds; round++)` with a `pass`-break) — there is no precedent helper to reuse, only the per-collection `for` idiom.

**Evidence:**

```js
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  ...
}
```

— `.claude/workflows/qrspi-batch.js:1289-1353`

```js
// Per run, each ticket advances at most ONE autonomous step ...
```

— `.claude/workflows/qrspi-batch.js:36`  (the orchestration-level non-termination guard)
**Dependencies:** The per-ticket loop is sequential (comment :1285: "tickets share one .git index, so worktree/Graphite ops must not race"). `respondToComments` is likewise sequential (:899-901).
**Implicit contracts:** Every loop here terminates because it consumes a finite array. The "advance one step per run; re-request review flips the state" pattern is how multi-pass agentic work is made loop-safe ACROSS runs — but a critic loop converging WITHIN a single `runPhase` call has no existing in-process cap precedent, so a finite `maxRounds` bound (counter-driven `for`, break on `pass`) must be added explicitly to guarantee termination.

## Q11: What happens today if a critic-equivalent agentic call returns malformed or schema-invalid output — is there existing handling for agent output that fails schema validation that the findings contract would inherit?

**Answer:** Yes — two well-established handlers:
1. **Schema'd `agent({ schema })` calls:** a malformed/empty result comes back falsy/`null`, and every caller guards with `if (!x || !x.ok)` (or `=== null`) and degrades to a recorded skip/failure WITHOUT throwing. Examples: `if (!setup || !setup.ok)` (:687), `if (!fin || !fin.ok)` (:790, :1014, :1057), `if (res === null)` (:464), `if (!p || !p.ok)` (:472). The result is a `skip(...)`/`failTicket(...)`/`finResult(...)` record, never a crash.
2. **Plain-text-return calls (the weak-model-safe path):** the `parse*Envelope`/`parseLandVerdict` helpers run `extractJsonObject(text)` then `JSON.parse` inside a `try/catch`, and ANY failure (no JSON, unparseable, missing `ok`, wrong shape) returns a clean `{ ok:false, error:'...' }` — it NEVER throws (`parseResolveEnvelope` :212-226, `parseCleanupEnvelope` :286-294, `parseLandVerdict` :300-309, `parseConfigEnvelope` :316-326). The orchestrator then treats `ok:false` as resolve_failed/skip.

A `{ pass, findings }` critic contract would inherit whichever it picks: via `schema` → falsy-guard + skip; via plain-text → `extractJsonObject` + a new `parseCriticEnvelope` returning `{ ok:false }` on malformation. The documented design preference for python-/echo-driven workers is the plain-text path BECAUSE the weak local model "emitted an empty {} and looped against schema validation" (:171-176) — so a critic running on that model should NOT rely on `schema` alone. The over-arching convention is **"fail toward a clean ok:false / wait, never throw, never act on a corrupt verdict"** (:208-211).

**Evidence:**

```js
function parseLandVerdict(text) {
  const raw = extractJsonObject(text)
  if (!raw) return { status: 'incomplete', openBranches: [], error: 'land-verify: no JSON verdict in worker output' }
  let v
  try { v = JSON.parse(raw) } catch (e) { return { status: 'incomplete', openBranches: [], error: `...` } }
  if (v.status !== 'landed' && v.status !== 'incomplete') {
    return { status: 'incomplete', openBranches: [], error: 'land-verify: verdict missing/unknown status' }
  }
  ...
}
```

— `.claude/workflows/qrspi-batch.js:300-309`
**Dependencies:** `extractJsonObject` (:190-206) / `extractJsonArray` (:231-247) underpin all plain-text validators. Per-ticket `try/catch` (:1297-1352) is the final backstop: a thrown phase agent is caught, recorded as `errored`, and the loop continues — "must NOT abort the remaining tickets" (:1293-1296).
**Implicit contracts:** Validators must NEVER throw — they always return a typed `ok:false` (or fail-closed default like `incomplete`/`wait`). A critic that fails validation must fail-closed: per the dominant convention, treat an unreadable verdict as NOT-passed (do not silently mark the artifact converged on a corrupt critic reply), mirroring how `parseLandVerdict` fails closed to `incomplete` and the resolver fails toward `wait`.

## Q12: How are the existing stdlib-only `_test.py` unit tests structured for pure orchestration logic, and is the JS loop control flow in `qrspi-batch.js` currently unit-tested anywhere, or is JS logic verified only by manual e2e?

**Answer:** The Python tests are **stdlib-only, assert-based, no pytest** — each `scripts/qrspi_*_test.py` imports the pure function under test, builds tiny fixture factories, registers `(name, input, expected)` CASES, and runs them with `assert`, exiting 0 on all-pass / 1 on first failure. `qrspi_resolve_state_test.py` is the canonical example: `_phase()`/`_impl()`/`_slice()`/`_ct()`/`state()` builders (:14-47), a `case(name, st, expect)` registry (:60-61), and a substring helper `contains()` (:50-54). They are run with `python3 scripts/qrspi_<x>_test.py` (`.claude/CLAUDE.md`: "stdlib-only unit tests as `_test.py` siblings ... run with `python3`"). There are **22** such `_test.py` files (one per script).

**The JS in `qrspi-batch.js` is NOT unit-tested anywhere.** There is no `package.json`, no `*.test.js`/`*.spec.mjs`, no JS test runner, and no JS import harness in the repo (confirmed by search). The orchestration JS is verified ONLY by manual end-to-end runs — `.claude/CLAUDE.md` states explicitly: "verify pure logic with the unit tests and orchestration changes with manual end-to-end runs," and the eval harness is "a **non-functional placeholder**." The established testing strategy is therefore to **push pure logic OUT of the JS and into a `scripts/qrspi_*.py` helper with a `_test.py` sibling**, then have the JS delegate to it (exactly the pattern for the resolver, persist, restack, order, land-verify, pr-body, revise-amend, comment-reply). A critic loop's pure decision logic (e.g. "given findings + round, converge/continue/cap") would, to be testable, follow this same extract-to-python pattern.

**Evidence:**

```python
"""Unit tests for qrspi_resolve_state.resolve().
Stdlib-only, assert-based (no pytest dependency) to match the repo's script
conventions. Run with: python3 scripts/qrspi_resolve_state_test.py
Exits 0 if all pass, 1 on the first failure."""
import sys
from qrspi_resolve_state import resolve
```

— `scripts/qrspi_resolve_state_test.py:2-11`
**Dependencies:** Each `_test.py` imports its sibling module directly (e.g. `from qrspi_resolve_state import resolve` :11). No JS runtime dependency. The decision logic the JS branches on (`r.decision.action`, :1320-1339) lives in `scripts/qrspi_resolve_state.py` precisely so it is testable.
**Implicit contracts:** Pure, side-effect-free logic goes in a python module with a `_test.py`; orchestration glue stays in JS and is e2e-only. To unit-test critic *control flow*, the deterministic part (round counting, converge/continue/append-to-body decision) must be a pure python function with stdlib-only `_test.py`, leaving only the agent-spawn glue in untested JS.

## Q13: How does the existing test setup stub or fake agentic calls so the produce→critique→revise control flow can be tested with stubbed critic/revise functions?

**Answer:** **There is NO stubbing of agentic (`agent()`) calls anywhere — because the JS orchestration (where `agent()` lives) is not unit-tested at all (Q12).** The Python `_test.py` files never touch `agent()`; they test PURE functions that receive plain dict/JSON inputs and return dicts, with NO agent, network, subprocess, or filesystem dependency in the hot path. The "fake" in these tests is simply hand-built fixture dicts: e.g. `qrspi_resolve_state_test.py` builds `state(...)` envelopes with `_phase`/`_slice`/`_impl` factories (:14-47) and asserts `resolve(state)` returns the expected `{action: ...}` — the gather (`qrspi_pr_state.py`) and the agent that runs it are entirely absent from the test; only the pure resolver is exercised. Where a script DOES do I/O, the test substitutes temp dirs (e.g. `qrspi_persist.py`'s `persist(src, dest)` is "unit-testable against temp dirs," :77) rather than mocking an agent.

Consequently there is **no precedent for stubbing a critic/revise `agent()` call** to test produce→critique→revise in JS. To make that flow testable under the repo's conventions, the deterministic loop logic would need to be extracted into a pure function that takes the critic VERDICTS (already-parsed `{pass, findings}` dicts) as plain inputs — exactly as `resolve()` takes a pre-gathered state dict — so a `_test.py` can feed it fixture verdicts (pass-on-round-2, never-pass-hit-cap, malformed) without any agent. The agent-spawn shell around it stays e2e-only.

**Evidence:**

```python
def _phase(branch=True, pr=True, decision="REVIEW_REQUIRED", threads=0, comments=None, merged=False):
    return {"branchExists": branch, "prExists": pr, "reviewDecision": decision,
            "unresolvedThreads": threads, "commentTargets": comments or [], "merged": merged}
```

— `scripts/qrspi_resolve_state_test.py:14-18`  (fixture-dict "stub," not an agent mock)
**Dependencies:** Tests import pure functions only; no agent/runner symbols are importable in the repo. `persist()` (`scripts/qrspi_persist.py:74`) isolates FS I/O so the test can pass temp paths.
**Implicit contracts:** Testability == purity. A function is unit-tested only if it accepts plain data and returns plain data with no agent/IO coupling. The convention to make critic control flow testable is: parse the verdict in the (untestable) JS/agent boundary, then pass the plain verdict into a pure, python-tested decision function — NOT to mock `agent()`.

## Q14: How does `runPhase` currently report progress, per-phase outcomes, and failures (logging / return envelope) so critic rounds, pass/fail per round, and cap-reached surfacing can be observed?

**Answer:** `runPhase` reports via the runner-provided `log(...)` primitive and a boolean return. Progress/outcome lines: reuse → `log(\`  ${id}: reusing existing ${name}.md\`)` (:460); produce-fail → `log(\`  ${id}: ${name} phase failed or was skipped — stopping this ticket\`)` (:465); persist-fail → `log(\`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ...}\`)` (:473); success → `log(\`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0,60)})\`)` (:476). The RETURN is just `true`/`false` — no structured envelope; the caller converts `false` into `failTicket(t)` (a `{ ticketId, action:'failed', summary }` record, :1053-1055). Phase banners are emitted by `phase('Design')`/`phase('Plan')`/`phase('Finalize')` (runner primitive, e.g. :596, :623). The aggregate observability is the per-ticket `results.push(res)` array returned at the end (:1359 `return { ticketsProcessed, results, reconciliation }`), where each `res` carries `{ ticketId, action, newStatus?, summary, prUrl? }` from `finResult`/`skip`/`failTicket`.

To surface **critic rounds / per-round pass-fail / cap-reached**, the existing channels are: (1) `log(...)` lines for human-visible per-round trace (the dominant idiom — e.g. the revise path logs `evaluated N/M reviewer comment(s)`, :831/:837); (2) folding a summary string into the ticket's `res.summary` (the pattern `out.summary = \`${out.summary} Also ${commentSummary}.\`` at :870-872, and the `commentSummary` assembly at :836-840). `runPhase` itself returns only a boolean, so cap/round detail would either be `log`ged inline or threaded into the eventual `res.summary` the way `commentSummary` is.

**Evidence:**

```js
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) {
    log(`  ${id}: ${name} reported done but no artifact was staged/persisted — ${p?.error ?? 'no result'} (stopping this ticket)`)
    return false
  }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B (${String(res).slice(0, 60)})`)
  return true
```

— `.claude/workflows/qrspi-batch.js:471-477`

```js
  const commentSummary = targets.length
    ? `evaluated ${answered.length}/${targets.length} reviewer comment(s)`
      + `${answered.some(a => a.applied) ? ` (${answered.filter(a => a.applied).length} applied as changes)` : ''}`
      + `${failures.length ? `, ${failures.length} failed` : ''}`
    : ''
```

— `.claude/workflows/qrspi-batch.js:836-840`  (the summary-folding idiom a cap/round report would mirror)
**Dependencies:** `log`/`phase` are runner primitives (not defined in repo). The final `results[]` array (:1340, :1359) is the machine-readable run report; `finResult` (:1056-1062), `skip` (:420-422), `failTicket` (:1053-1055) shape its entries.
**Implicit contracts:** `runPhase` returns a bare boolean — any richer per-round signal must be emitted via `log` and/or merged into the ticket-level `res.summary` (there is no structured per-phase telemetry channel). Log lines are 2-space-indented under the ticket id by convention (`\`  ${id}: ...\``). A cap-reached condition that still produces a (committed-with-findings) artifact should return `true` (so the phase proceeds to finalize), surfacing "cap reached, N findings appended" via `log` + summary — consistent with the existing non-fatal-warning idiom (e.g. best-effort Linear writes are WARN, still `ok:true`, :628/:666).

---

## Discovered Patterns

1. **Worker-delegation architecture.** The JS sandbox cannot run python/git/gh/Linear; the workflow RUNNER spawns agents via `agent()`, and all non-JS mechanics are delegated to single-command worker agents that run a self-locating `scripts/qrspi_*.py` and echo its JSON (`.claude/workflows/qrspi-batch.js:17-34`). A critic loop must follow this: pure decisions in python (`_test.py`-covered), agent-spawn glue in JS.

2. **Two result-return modes.** `agent({ schema })` → runner-validated object (used by phase/setup/commit/persist/comment workers). `agent()` (no schema) → plain string parsed in JS via `extractJsonObject` + a bespoke `parse*Envelope` (used by every python-invoking worker, because the weak local model stalls the StructuredOutput tool, :171-176). The choice hinges on which model runs the worker.

3. **Fix A staging discipline.** Every persisted artifact is written by the agent to a token-free `/tmp/phase-stage/<id>/<name>.md` path (`stg()`), then moved by `scripts/qrspi_persist.py` to the canonical `.qrspi` path — because the weak model mangles the literal `qrspi` token in long paths (`qrspi_persist.py:1-29`). Any new staged artifact (e.g. a critic verdict file) must use a token-free path; reply bodies already do this (`comment-reply-${i}.md`, :906).

4. **Self-locating scripts.** Every `scripts/qrspi_*.py` derives its repo root from `__file__`/git-common-dir, never from cwd or a model-typed argument (`qrspi_persist.py:45-50`), and is addressed via `engineCmd(rel)`/`engineCmdFor(r, rel)` (:76-105) so it survives the engine not being the worker's cwd.

5. **Fail-closed, never-throw validators.** Every `parse*` helper returns a typed `{ ok:false }`/`incomplete`/`wait` on any malformation instead of throwing (:208-211, :300-309). The per-ticket `try/catch` (:1297-1352) is the final backstop so one bad ticket never aborts the batch.

6. **One-autonomous-step-per-run loop safety.** Multi-pass agentic work (revise) is made loop-safe ACROSS runs by a state flip (re-request review → `REVIEW_REQUIRED` → next pass `wait`), not by an in-process counter (:36-43). There is no existing in-process bounded-retry primitive.

7. **Pure-logic-extraction testing strategy.** JS orchestration is e2e-only (no JS test harness exists); anything testable is pushed into a python module with a stdlib-only assert-based `_test.py` sibling (22 of them) that feeds hand-built fixture dicts to a pure function (`qrspi_resolve_state_test.py`).

8. **Implementation slices bypass `runPhase`.** Design/plan artifacts flow through `runPhase` (+persist gate); implementation slices are spawned directly via `agent({agentType:'qrspi-implement'})` and committed per-slice (:694-733). A `runPhase`-attached critic covers design/plan only.

## Inconsistencies

1. **`pipeline()` is in the questions/runner vocabulary but unused here.** Q4 names `pipeline()` as an existing primitive to reuse, but `qrspi-batch.js` never calls `pipeline(` (grep: 0 hits). Only `agent()` and `parallel()` are actually used. The runner may provide `pipeline()`, but there is no in-repo precedent for it.

2. **`meta.phases` is descriptive, not a runtime mapping.** A reader might expect `meta.phases` (:5-14) to drive phase dispatch, but the real phase→agent→artifact wiring is imperative inside the `doX` functions; `meta.phases` is documentation/UX only. The two can drift (e.g. `meta.phases` lists "Restack/Reconcile" as phases but those are not artifact-producing phases).

3. **StructuredOutput declared-but-distrusted.** `RECONCILE_CANDIDATES_SCHEMA` (:1076) and several `*_SCHEMA`s are passed to `agent({schema})`, yet the file's own comments (:171-176, :281, :313) document that the weak local model "could not populate the StructuredOutput tool." So some workers use the schema path and others were explicitly migrated OFF it to plain-text+`extractJsonObject` — an unresolved tension a critic implementer must consciously navigate (which return mode to pick).

4. **No design/plan PR-body mechanism exists** despite the implementation phase having a dedicated `scripts/qrspi_pr_body.py`. Q8's "append findings to the PR body" has no design/plan analog — the design/plan body is a bare commit subject (:627, :665), so appending findings requires new machinery, not an extension of an existing one.
