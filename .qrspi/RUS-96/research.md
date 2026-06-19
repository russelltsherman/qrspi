# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-19T00:00:00Z
**Generated:** 2026-06-19T00:00:00Z
**Status:** draft

> Scope note: all paths below are under `/Users/russelltsherman/src/github.com/russelltsherman/qrspi/.worktrees/RUS-96/`. Paths are written relative to that worktree root for brevity.

---

## Q1: How does `doDesign` currently sequence produce → persist → finalize, and where exactly between produce and finalize would a `workflow('qrspi-review', {...mode:'gate'})` call insert without disturbing the existing persist/finalize steps?

**Answer:** `doDesign(t, r)` runs three producer phases — `questions`, `research`, `design` — each through the helper `runPhase(...)`, then a single `Finalize` agent that commits + submits the design PR. `runPhase` itself folds produce-then-persist: it spawns the phase producer agent, then calls `persistArtifact(...)` which runs `scripts/qrspi_persist.py` to move the staged file into the worktree (this persist IS the per-phase success gate). The natural insertion point for a producer-gate review call is **after the `design` `runPhase` returns true (design.md is persisted into the worktree) and before `phase('Finalize')`** (`.claude/workflows/qrspi-batch.js:711`→`713`). At that point `design.md` exists at its canonical worktree path, no PR yet exists for the design branch, and the finalize/commit step has not run — so a gate can read/rewrite the persisted artifact before it is committed without disturbing the commit+submit logic.

**Evidence:**

```js
async function doDesign(t, r) {
  const wd = r.worktreeDir
  phase('Design')
  // questions ...
  // research ...
  if (!await runPhase('design', 'qrspi-design',
    `TICKET_ID = ${t.id}
...
TEMPLATE_PATH = ${tpl(wd, 'design.md')}`, r.existing, t.id, 'Design')) return failTicket(t)

  phase('Finalize')
  const fin = await agent(
    `${provisionStep(r, t)}You are the DESIGN-PHASE finalize worker for ${t.id} ...`,
```

— `.claude/workflows/qrspi-batch.js:683-721`

`runPhase` (produce → deterministic persist gate):

```js
async function runPhase(name, agentType, prompt, existing, id, phaseLabel) {
  if (existing && existing[name]) { log(`  ${id}: reusing existing ${name}.md`); return true }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { ... return false }
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { ... return false }
  ...
}
```

— `.claude/workflows/qrspi-batch.js:512-532`

**Dependencies:** `doDesign` is dispatched from the action switch `case 'run_design': res = await doDesign(t, r)` (`.claude/workflows/qrspi-batch.js:1645`). It depends on `runPhase`, `persistArtifact`/`qrspi_persist.py`, `stg()`, `art()`/`tpl()` path helpers, `failTicket`, `finResult`, and `provisionStep`. There is **no existing `workflow(...)` call inside `qrspi-batch.js`** — the batch does not currently invoke the review engine as a sub-workflow.

**Implicit contracts:**
- `runPhase` returning `true` means the staged artifact was moved to `<wd>/.qrspi/<id>/<name>.md` and is non-empty (the persist verify is the success gate).
- The comment at `.claude/workflows/qrspi-batch.js:687` and `:509-511` explicitly states the autonomous batch runs **no phase critics or node-checks** today: "each phase persists ungated … the on-demand /review-* family is the surviving review path." A gate would change this invariant for design only.
- A failure must funnel through `failTicket(t)` (the producers) — the existing early-returns all `return failTicket(t)`.

---

## Q2: What inputs does the existing `advisory` mode of the review engine receive, what scratch-copy path does it operate on, and what does it return to its caller today?

**Answer:** There is **NO `mode` parameter today** — the engine `qrspi-review.js` has exactly one behavior, which is the advisory/propose-only path. "Advisory" is a description of that single behavior, not a selectable mode. The engine's only input is `args = { ticket: string, phase: 'design'|'plan'|'impl' }` (parsed at `.claude/workflows/qrspi-review.js:225-232`). It scratch-copies the phase artifact to `/tmp/phase-stage/<ticket>/review/<artifact>.md` (the Resolve worker `cp`s the tracked file there — `qrspi-review.js:272-275`), and the panel reads the COPY, never the tracked file. Its return on success is `{ ok, ticket, phase, pr, terminalAction, shaUnchanged, summary }`; on failure `{ ok:false, ticket, phase, error }` (and a bare `{ ok:false, error }` for missing inputs).

**Evidence:**

```js
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const TICKET = (typeof input?.ticket === 'string' && input.ticket.trim() !== '') ? input.ticket.trim() : undefined
const PHASE_KEY = (typeof input?.phase === 'string') ? input.phase.trim() : undefined
```

— `.claude/workflows/qrspi-review.js:225-232`

```js
return {
  ok: true, ticket: TICKET, phase: PHASE_KEY, pr: resolved.pr,
  terminalAction: fin.terminalAction, shaUnchanged: true, summary: fin.summary,
}
```

— `.claude/workflows/qrspi-review.js:514-522`

Scratch copy path (Resolve worker step 4): `cp "<worktreeDir>/.qrspi/<ticket>/<artifact>" /tmp/phase-stage/<ticket>/review/<artifact>` → `scratch = /tmp/phase-stage/<ticket>/review/<artifact>` (`.claude/workflows/qrspi-review.js:272-275`).

**Dependencies:** invoked by the three thin SKILL wrappers `.claude/skills/review-{design,plan,implementation}/SKILL.md`, each calling `Workflow({ name: "qrspi-review", args: { ticket, phase } })` (e.g. `.claude/skills/review-design/SKILL.md:22`). It spawns worker agents for Resolve, the Panel lenses, the design-only Readiness lens, and the Synopsis/finalize worker.

**Implicit contracts:**
- The wrappers pass exactly `{ticket, phase}` — no other key is read, so adding a `mode` key requires both wrapper and engine changes.
- The engine's entire contract is propose-only: the only GitHub writes are one `gh pr comment` and a local ledger append; it captures the head SHA before and re-asserts it after (`qrspi-review.js:40-46`, `:502-511`).

---

## Q3: How is the design artifact written and moved into the worktree via the Fix-A staging path today, and what staging path / move contract would a reviser rewrite have to follow to land in `.worktrees/<id>/.qrspi/<id>/`?

**Answer:** Fix-A: the producer agent writes to a **token-free staging path** `stg(id, name) => /tmp/phase-stage/<id>/<name>.md` (`.claude/workflows/qrspi-batch.js:464`), then `scripts/qrspi_persist.py` verifies the staged file is non-empty and `shutil.move`s it to the canonical worktree dest `<repo_root>/.worktrees/<id>/.qrspi/<id>/<artifact>.md`. The destination path (the `qrspi` token) is computed entirely inside the script, never typed by the model. The host root is resolved via `qrspi_paths.resolve_repo_root(cwd=..., validate=False)` (git-common-dir first → MAIN checkout even from a worktree). `--artifact` is constrained to a fixed list `["questions","research","design","structure","plan","worktree"]`. A reviser that wants to land a rewrite into the worktree's `.qrspi/<id>/design.md` would have to (a) write to `stg(id, 'design')` = `/tmp/phase-stage/<id>/design.md`, and (b) invoke `qrspi_persist.py --ticket <id> --artifact design`. **Note:** the current on-demand reviser is propose-only and writes only to the scratch `/tmp/phase-stage/<id>/review/<artifact>` path, which is NOT a persist staging path — `qrspi_persist.py` only knows `/tmp/phase-stage/<id>/<artifact>.md` (no `review/` segment).

**Evidence:**

```python
STAGE_ROOT = "/tmp/phase-stage"
def staging_path(stage_root, ticket, artifact):
    return os.path.join(stage_root, ticket, "%s.md" % artifact)
def dest_path(repo_root, ticket, artifact):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket, "%s.md" % artifact)
def persist(src, dest):
    size = os.path.getsize(src)        # OSError -> "not found"
    if size == 0: return 0, "staged artifact is empty: %s" % src
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    shutil.move(src, dest)
    ...
```

— `scripts/qrspi_persist.py:52-92`

```python
ARTIFACTS = ["questions", "research", "design", "structure", "plan", "worktree"]
REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)
```

— `scripts/qrspi_persist.py:50-52`, and `--artifact` `choices=ARTIFACTS` at `:101`

`stg` helper (kept in sync with `STAGE_ROOT`):

```js
const stg = (id, name) => `/tmp/phase-stage/${id}/${name}.md`
```

— `.claude/workflows/qrspi-batch.js:464`

**Dependencies:** `persistArtifact()` (`.claude/workflows/qrspi-batch.js:492-505`) is the only JS caller; it runs the script via a worker and parses `{ ok, dest, bytes, error? }` (PERSIST_SCHEMA). `qrspi_persist.py` imports `qrspi_paths.resolve_repo_root`.

**Implicit contracts:**
- `--artifact` is a closed enum: a reviser landing a rewrite must use one of the six names (e.g. `design`). There is no `review/`-subdir-aware persist mode today.
- Persist is fail-closed and never retried (`:24-25` docstring); an empty/missing staged file returns `ok:false`.
- The staging path carries no `qrspi` token by design (the weak-worker path-mangling mitigation).

---

## Q4: What is the current call signature, argument schema, and return shape of the review engine when invoked as a workflow, and what fields would `{converged, rounds, residualFindings, logPath}` need to coexist with the advisory-mode return?

**Answer:** Invoked as `Workflow({ name: "qrspi-review", args: { ticket: string, phase: 'design'|'plan'|'impl' } })`. Args are parsed leniently (string-JSON or object). Success return: `{ ok:true, ticket, phase, pr, terminalAction, shaUnchanged:true, summary }`. Failure return: `{ ok:false, ticket, phase, error }` (or `{ ok:false, error }` for a missing ticket/phase before resolution). The existing `terminalAction` is the string `"converged" | "exhausted"` (round-0 pass ⇒ `converged`, else `exhausted`). The proposed gate fields `{converged, rounds, residualFindings, logPath}` would be NEW keys; today there is no `rounds` count, no `residualFindings` array, and no `logPath` in the return — `terminalAction` is the only convergence signal and it is a string, not a boolean `converged`. `residualFindings` has a clear analogue in `qrspi_critic_loop.next_action`'s `residual_findings` (the latest verdict's findings when not passed — `scripts/qrspi_critic_loop.py:113`), and `qrspi_critic_synthesize.synthesize` already returns `{pass, findings}` from which a residual set is derivable.

**Evidence:**

```js
const SYNOPSIS_SCHEMA = {
  type: 'object',
  required: ['ok', 'summary'],
  properties: {
    ok: { type: 'boolean' }, error: { type: 'string' },
    terminalAction: { type: 'string' }, // converged | exhausted
    posted: { type: 'boolean' },
    shaUnchanged: { type: 'boolean' },
    headShaAfter: { type: 'string' },
    summary: { type: 'string' },
  },
}
```

— `.claude/workflows/qrspi-review.js:209-221` (the worker envelope; the engine's own return is at `:514-522`)

```js
print("converged" if reduced.get("pass") else "exhausted")
```

— the round-0 terminal action computation, `.claude/workflows/qrspi-review.js:437`

**Dependencies:** the return is consumed by the three SKILL wrappers, which report `summary` and surface `error` on `ok:false` (`.claude/skills/review-design/SKILL.md:25`). No machine consumer parses `terminalAction`/`shaUnchanged` programmatically today — they are reported to the human.

**Implicit contracts:**
- The return is reported, not branched-on, by the wrapper. A gate caller in `doDesign` would be the first machine consumer, so any new field set (`converged`, `residualFindings`, `logPath`) needs no backward shimming for existing callers — but a `mode:'gate'` return must still satisfy the SKILL wrappers if they ever invoke gate mode (they do not today).
- `terminalAction` is constrained to the `qrspi_critic_metrics.VALID_TERMINAL_ACTIONS` set when it reaches `build_record` (`converged`/`exhausted` are valid; `revise` is rejected — `scripts/qrspi_critic_metrics.py:50-51, 76-80`).

---

## Q5: What functions does `scripts/qrspi_critic_synthesize.py` currently expose, what input shape do they consume, and what verdict shape do they emit that AC4's `{pass, residualFindings}` reduce would reuse or extend?

**Answer:** It exposes `synthesize(verdicts)` (the pure reducer), plus internal helpers `_coerce_lens`, `_lens_id`, `_finding_key`, and a thin `main()` stdin→stdout CLI. `synthesize` consumes a **list of per-lens verdict entries** for one round; each entry is a dict (coerced via `qrspi_critic_loop._coerce_verdict`) or a string (via `parse_critic_verdict`), anything else fails closed. It emits `{"pass": bool, "findings": list}` where `pass` is True only if the list is non-empty AND **every** coerced lens passed; `findings` is the exact-string-deduped union (lens-tagged as `{text, lens}` when a `lens` id is present). An AC4 `{pass, residualFindings}` reduce would directly reuse `synthesize`'s `pass`, and reuse `findings` as `residualFindings` (the union of blocking findings across lenses is exactly the residual set when `pass` is False).

**Evidence:**

```python
def synthesize(verdicts):
    if not isinstance(verdicts, list) or not verdicts:
        return {"pass": False, "findings": []}
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

— `scripts/qrspi_critic_synthesize.py:76-118`

**Dependencies:** imports `_coerce_verdict`, `parse_critic_verdict` from `qrspi_critic_loop` (the retained module). It is invoked in `qrspi-review.js`'s Synopsis worker (`qrspi_critic_synthesize.synthesize(panel)` at `.claude/workflows/qrspi-review.js:436`) after `partition_decision_readiness` strips the decision-readiness lens.

**Implicit contracts:**
- Empty verdict list ⇒ `pass:False` (fail closed — no lens attested).
- `pass:True` ⟺ every lens passed; any single fail flips the round.
- `findings` dedupe is exact-string on the bare string or the `text` key; lens-tagging is additive and only when a `lens` id is present.

---

## Q6: What config keys does `scripts/qrspi_critics_config.py` already read for the design critics, and what reader pattern (precedence, default handling) would `critics.design.reviewLoop` (`enabled`, `maxRounds`, debate cap) follow?

**Answer:** For design, `resolve_design(cfg, warnings)` reads `critics.design.{enabled, maxRounds, lenses, candidates, digest:{enabled}, lensModel}`. The on-demand review family reads a separate `critics.review.lensModel` via `resolve_review_lens_model(cfg)`. Reader patterns to mirror for a new `critics.design.reviewLoop` block:
- **enabled:** `resolve_enabled(cfg, default)` — only an explicit `True`/`False` flips it; any non-boolean falls back to `default` (every phase passes `False`, i.e. opt-in OFF). Source: `scripts/qrspi_critics_config.py:126-140`.
- **maxRounds / a debate cap (positive int):** `_pos_int_or(value, default)` — returns value only if it is a positive int and NOT a bool; else `default` (`DEFAULT_MAX_ROUNDS = 2`). Source: `:114-123`, `:56`.
- **Nested block:** read the sub-block as a dict only when it is a dict (`cfg.get("digest") if isinstance(...) else {}`), then resolve fields inside it — the `digest` block precedent at `:194-195`.
- **Optional string override (omit-when-unset):** the `lensModel` precedent — the key is OMITTED entirely (not None) unless config supplies a non-empty stripped string (`:208-211`, and the `review.lensModel` reader `:247-255`).

**Evidence:**

```python
def resolve_enabled(cfg, default):
    cfg = cfg if isinstance(cfg, dict) else {}
    value = cfg.get("enabled")
    if value is True: return True
    if value is False: return False
    return default
```

— `scripts/qrspi_critics_config.py:126-140`

```python
def _pos_int_or(value, default):
    if isinstance(value, bool): return default
    if isinstance(value, int) and value > 0: return value
    return default
```

— `scripts/qrspi_critics_config.py:114-123`

`resolve_review_lens_model` (the on-demand decoupled reader, fail-closed):

```python
def resolve_review_lens_model(cfg):
    if not isinstance(cfg, dict): return None
    review = cfg.get("review")
    if not isinstance(review, dict): return None
    lens_model = review.get("lensModel")
    if isinstance(lens_model, str) and lens_model.strip(): return lens_model.strip()
    return None
```

— `scripts/qrspi_critics_config.py:232-255`

**Dependencies:** `resolve_critics(critics)` (`:258-270`) dispatches to `resolve_design`/`resolve_implementation`; `default_phases()` and `main()` emit the JSON envelope. `read_config` comes from `qrspi_config`. `.qrspi/config.example.json` documents `critics.design.maxRounds` as the one live knob (`.qrspi/config.example.json:6-11`).

**Implicit contracts:**
- Critics are uniformly **opt-in (default OFF)** — `resolve_enabled` defaults False everywhere.
- The docstring of `resolve_review_lens_model` (`:243-246`) explicitly warns NOT to couple a new on-demand reader to `resolve_design`/`DEFAULT_DESIGN_LENSES`/`critics.design.*` — a new `critics.design.reviewLoop` would live under `critics.design` and may belong with `resolve_design`, but the design intentionally keeps batch-design vs on-demand-review keys decoupled.
- The example config comment (`.qrspi/config.example.json:7`) states the `critics` block "now drives ONLY the on-demand /review-* family" and the autonomous batch runs no phase critics — a producer-gate review loop would re-introduce a batch-side consumer of `critics.design.*`.

---

## Q7: What is the current definition and dormant state of the `qrspi-critic-reviser` agent, and what does "un-dormant" change in how it is invoked or registered?

**Answer:** `qrspi-critic-reviser` is the single shared, phase-parameterized NON-PRODUCER reviser. It is explicitly marked **DORMANT as of RUS-93** — "not spawned by `/review-*`" — because the review engine collapsed to a single round-0 pass with no revise loop. The agent definition is retained (not deleted). Its inputs are `PHASE`, `OUTPUT_PATH` (the scratch path it rewrites verbatim, the ONLY path it may Write), `RESIDUAL_FINDINGS` (the round's blocking findings — decision-readiness items are excluded by contract), and optional `RESEARCH_PATH`/`CODEBASE_PATH`/upstream paths. Tools: `Read, Grep, Write`. "Un-dormant" means **re-introducing a spawn call site** — currently nothing invokes it (`qrspi-review.js` never references `qrspi-critic-reviser`). A producer-gate loop would `agent(..., { agentType: 'qrspi-critic-reviser' })` per round, passing `OUTPUT_PATH`, `RESIDUAL_FINDINGS` (from `synthesize`/`next_action`), and the context paths. No registry edit is needed — the agent is already discoverable in `.claude/agents/`; only a caller is missing.

**Evidence:**

```markdown
> **DORMANT as of RUS-93 — not spawned by `/review-*`.** The on-demand `/review-*` family was
> collapsed onto the deterministic engine `.claude/workflows/qrspi-review.js`, which runs the
> review panel **once** (round 0, no revise loop). Because there is no revise round, this reviser
> is **no longer spawned** ... The agent definition is **retained** (not deleted) ... Nothing
> currently invokes this agent.
```

— `.claude/agents/qrspi-critic-reviser.md:8-15`

Write-target invariant (propose-only by design, scratch-only):

```markdown
- `OUTPUT_PATH` — absolute scratch path of the artifact you must rewrite in place, verbatim
  (e.g. `/tmp/phase-stage/<ticket-id>/review/design.md`). This is the ONLY path you may Write.
```

— `.claude/agents/qrspi-critic-reviser.md:35-37`; rules: "Write ONLY to OUTPUT_PATH … never to a tracked path under .qrspi/ or anywhere in the repo working tree" `:66-71`.

**Dependencies:** none currently — there is **no live caller**. The related `qrspi_critic_loop` MODULE is retained (still imported by `qrspi_critic_synthesize` for `_coerce_verdict`/`parse_critic_verdict`) — only the reviser-spawn call site was removed (`.claude/workflows/qrspi-review.js:26-28`).

**Implicit contracts:**
- The reviser is **propose-only and scratch-only today** — its rules forbid writing any tracked path or running `gt`/`git`/`gh`. For a producer gate to LAND a rewrite into the worktree, either the reviser's write target/contract changes, or a separate persist step moves its scratch output (see Q3: `qrspi_persist.py` only knows `/tmp/phase-stage/<id>/<artifact>.md`, not the `review/` scratch path).
- `RESIDUAL_FINDINGS` excludes decision-readiness items by contract (`:38-40`, `:72-73`).

---

## Q8: Which design critic lens agents exist, and what finding/output structure does each emit that the per-round full panel and cross-critic debate would consume?

**Answer:** The design lens agents in `.claude/agents/` are:
- `qrspi-design-critic-completeness` (tools: Read) — coverage of ACs + answered questions.
- `qrspi-design-critic-internal-consistency` (edge/consistency lens).
- `qrspi-design-critic-edge-alignment` (tools: Read) — faithful derivation of ticket intent + research facts.
- `qrspi-design-critic-simplicity`.
- `qrspi-design-critic-design-review` (tools: Read, Grep) — the adversarial NODE-VALIDITY lens; verifies codebase claims against real source; carries the `critics.review.lensModel` override at spawn.
- `qrspi-design-critic-decision-readiness` (tools: Read, Grep) — terminal-advisory; partitions open questions into human-decisions vs answerable; emits `DecisionReadinessVerdict`, NOT a `{pass, findings}` verdict.

Every panel lens (all but decision-readiness) emits the same `{pass, findings, nonBlockingNotes?}` verdict shape, validated as `CRITIC_VERDICT_SCHEMA` at the runner boundary, with the strict invariant `pass:false ⟺ findings non-empty`. `findings` are self-contained strings, each citing a real source location. `nonBlockingNotes` is the optional advisory channel. This uniform shape is exactly what `synthesize` reduces and what a per-round full panel + cross-critic debate would consume.

**Evidence:**

```markdown
- `pass` (bool) ... `false` when one or more blocking problems exist.
- `findings` (list) — one self-contained string per blocking problem ...
- `nonBlockingNotes` (list, OPTIONAL) — advisory observations that are NOT blocking ...
When `pass` is `true`, `findings` MUST be empty. When `pass` is `false`, `findings` MUST be non-empty.
```

— `.claude/agents/qrspi-design-critic-design-review.md:56-60`

CRITIC_VERDICT_SCHEMA (the runner-boundary contract every lens satisfies):

```js
const CRITIC_VERDICT_SCHEMA = {
  type: 'object', required: ['pass', 'findings'],
  properties: {
    pass: { type: 'boolean' },
    findings: { type: 'array', items: { type: 'string' } },
    nonBlockingNotes: { type: 'array', items: { type: 'string' } },
  },
}
```

— `.claude/workflows/qrspi-review.js:153-161`

DecisionReadinessVerdict (the exception — terminal-advisory, partitioned out):

```js
const DECISION_READINESS_SCHEMA = {
  type: 'object', required: ['lens', 'blockingDecisions', 'answerable'], ...
}
```

— `.claude/workflows/qrspi-review.js:165-183`; agent at `.claude/agents/qrspi-design-critic-decision-readiness.md:1-23`

**Dependencies:** the panel set the engine fans out is `cfg.lenses` for design = `['completeness','internal-consistency','edge-alignment','simplicity','design-review']` (`.claude/workflows/qrspi-review.js:119`), mirroring `DEFAULT_REVIEW_DESIGN_LENSES` in `scripts/qrspi_critics_config.py:84-90`. Each lens's agentType = `qrspi-design-critic-<lensId>` (`qrspi-review.js:324`). The ticket-text lenses are `['completeness','edge-alignment']` (`:118`); `design-review` is the `reviewLens` that carries the model override and NEVER receives `TICKET_CONTENT_PATH` (`:116-117`, `:332`).

**Implicit contracts:**
- `pass:false ⟺ findings non-empty` is strict for the node-validity lens; "SHOULD be empty" for some edge lenses (e.g. completeness `:`"When pass is true, findings SHOULD be empty").
- `design-review` opts OUT of any digest and always reads full `RESEARCH_PATH` (node-validity needs complete evidence — `.claude/agents/qrspi-design-critic-design-review.md:19, 68`).
- decision-readiness is partitioned OUT of the synthesize input (`partition_decision_readiness`) so it can never drive a revise round (`scripts/qrspi_review_synopsis.py:72-93`).

---

## Q9: How is the review ledger represented and appended today by the advisory path, and what state does it track that gate mode must NOT touch (since gate mode posts no PR comment)?

**Answer:** The ledger is a per-ticket JSON-lines file `<root>/.worktrees/<id>/.qrspi/<id>/critic-metrics.jsonl`. Each appended line is a `ReviewRecord` (built by `qrspi_review_record.build_record(phase, rounds, terminal_action, agreement)`) wrapped in the `CriticMetricsLedgerLine` envelope (`qrspi_metrics_append.py` injects `ticketId`, `timestamp`, `runId`). The ReviewRecord = base `{phase, rounds:[{lens,pass,findingsCount}], terminalAction}` + `agreement` block + `mode:"on-demand-review"`. The advisory engine calls `build_record(..., agreement={})` (F2 dropped agreement) and `ledger_row_fields(...)` (adds `axes`, `nonBlockingNotes`), then appends via `qrspi_metrics_append.py`. **The ledger append and the PR-comment write are decoupled steps in the Synopsis worker** (steps 4 = comment, 5 = append — `.claude/workflows/qrspi-review.js:474-484`). The state a gate mode must NOT touch is the **`mode:"on-demand-review"` discriminator + the `agreement` block**, which mark a row as an on-demand-review row distinct from batch panel rows; a gate-mode (producer) review row should be distinguishable (e.g. a different `mode`) so ledger consumers do not conflate it with on-demand reviews.

**Evidence:**

```python
def build_record(phase, rounds, terminal_action, agreement):
    record = qrspi_critic_metrics.build_record(rounds, terminal_action, phase=phase)
    record["agreement"] = agreement
    record["mode"] = MODE_ON_DEMAND_REVIEW   # "on-demand-review"
    return record
```

— `scripts/qrspi_review_record.py:48-72`

```python
def ledger_path(repo_root, ticket):
    return os.path.join(repo_root, ".worktrees", ticket, ".qrspi", ticket, "critic-metrics.jsonl")
def wrap_envelope(record, ticket, timestamp, run_id):
    line = dict(record); line["ticketId"]=ticket; line["timestamp"]=timestamp; line["runId"]=run_id; return line
```

— `scripts/qrspi_metrics_append.py:60-79`

Engine append (decoupled from the comment):

```
4. Post the synopsis as ONE top-level advisory comment ... qrspi_comment_reply.py ...
5. Append the ReviewRecord to the ledger ... qrspi_metrics_append.py --ticket ... --record ...
```

— `.claude/workflows/qrspi-review.js:474-484`

**Dependencies:** `qrspi_review_record` imports `qrspi_critic_metrics.build_record`; `qrspi_metrics_append` imports `qrspi_paths`. `ledger_row_fields` lives in `qrspi_review_synopsis.py:96-125`. The synopsis comment path uses `qrspi_comment_reply.py` (NOT exercised by a gate that posts no comment).

**Implicit contracts:**
- `runId` is required on every line (`qrspi_metrics_append.py:111-113`).
- The appender is the single envelope authority — its `ticketId`/`timestamp`/`runId` win over any pre-existing record fields (`:67-79`).
- `mode:"on-demand-review"` is the consumer discriminator (`scripts/qrspi_review_record.py:10-13, 45`). A gate row would need its own mode value to avoid polluting on-demand-review analytics.
- The comment write and ledger append are independent: a gate mode can append a ledger row (or not) without posting a comment — these are separate worker steps with no shared state beyond the record file.

---

## Q10: What does `doDesign` do today when the review/loop config is absent or disabled, and what code path constitutes the "additive / loop-off → today's ungated `doDesign`" behavior AC10 requires?

**Answer:** Today `doDesign` does **NOT read any review/loop config at all** — there is no config check in `doDesign`. It unconditionally runs `questions → research → design` (each ungated via `runPhase`) then `Finalize`. The comment at `.claude/workflows/qrspi-batch.js:687` is explicit: "The autonomous batch runs no phase critics or node-checks; each phase persists ungated." So the entire current body of `doDesign` (`.claude/workflows/qrspi-batch.js:683-723`) IS the "loop-off / ungated" path. For AC10's additive contract (loop-off ⇒ today's behavior byte-for-byte), a gate must be a NEW conditional block inserted after the design `runPhase` and before `phase('Finalize')`, guarded by `resolve_review_lens_model`-style config (e.g. a new `critics.design.reviewLoop.enabled`, default OFF via `resolve_enabled(cfg, False)`), such that when absent/disabled the function executes exactly the steps it does now.

**Evidence:**

```js
async function doDesign(t, r) {
  const wd = r.worktreeDir
  phase('Design')
  // The autonomous batch runs no phase critics or node-checks; each phase persists ungated.
  if (!await runPhase('questions', 'qrspi-questions', ...)) return failTicket(t)
  if (!await runPhase('research', 'qrspi-research', ...)) return failTicket(t)
  if (!await runPhase('design', 'qrspi-design', ...)) return failTicket(t)
  phase('Finalize')
  ...
}
```

— `.claude/workflows/qrspi-batch.js:683-723` (no config read present)

The default-OFF config reader pattern to gate it:

```python
def resolve_enabled(cfg, default):  # default False everywhere — opt-in
```

— `scripts/qrspi_critics_config.py:126-140`

**Dependencies:** the only config the batch reads about critics today is `resolve_review_lens_model` (read INSIDE the on-demand engine, not the batch). `qrspi-batch.js` does read flat `ciReviseCap` config elsewhere but not any `critics.design.*` gate for `doDesign`. `.qrspi/config.example.json:7` confirms "The autonomous qrspi-batch workflow runs NO phase critics."

**Implicit contracts:**
- "Additive / loop-off" means: with no config (or `enabled:false`), `doDesign` must produce the identical commit+submit outcome it does now. The default for any new gate flag must be OFF (`resolve_enabled(..., False)`).
- A gate inserted between design-persist and finalize must not change the `failTicket`/`finResult` contracts on the existing paths.

---

## Q11: How is a design PR submitted today (the `gt submit` + commit-message-as-body path), and what mechanism attaches extra content to a PR after creation that AC8's "publish anyway with residual findings attached" would use?

**Answer:** The design Finalize worker (1) verifies the three artifacts exist non-empty, (2) stages ONLY those three and commits them as a single commit (subject `<id> [QR]: Design — <title>`) onto the pre-created `<id>/design` branch with `gt modify -c`, then submits PUBLISHED with `gt submit --publish<reviewerFlags>`, (3) best-effort projects Linear → "Design Review". The PR body is **seeded by Graphite from the branch commit message at CREATION only** (`gt submit` has no body flag). The mechanism to attach extra content AFTER creation is the **GitHub REST API PATCH**: `gh api repos/<owner>/<repo>/pulls/<N> -X PATCH -F body=@<file>` (preferred over `gh pr edit`, which can abort on the Projects-classic GraphQL deprecation). This is documented in the impl/submit finalize prompts (`.claude/workflows/qrspi-batch.js:840`, `:860`) and the project CLAUDE.md. So "publish anyway with residual findings attached" (AC8) would: submit via `gt submit --publish` (publishing still goes through `gt`, never `gh`), then PATCH the PR body via `gh api … -X PATCH -F body=@<file>` to append the residual findings.

**Evidence:**

```js
2. Stage ONLY those three artifacts; add them as the single commit (subject "${t.id} [QR]:
   Design — ${t.title}") on the pre-created ${t.id}/design branch with `gt modify -c` ...
   Then submit the Design PR PUBLISHED with `gt submit --publish${reviewerFlags(r)}` ...
```

— `.claude/workflows/qrspi-batch.js:717`

Post-creation body PATCH mechanism (documented in the impl finalize prompt):

```js
A post-hoc body correction, if ever needed, uses `gh api repos/<owner>/<repo>/pulls/<N>
-X PATCH -F body=@<file>` (NOT `gh pr edit`, which can abort on the Projects-classic GraphQL bug).
```

— `.claude/workflows/qrspi-batch.js:840` (also `:860`)

`scripts/qrspi_pr_body.py` (the implementation-phase body splicer — splices `pr-summary.md` into the slice-1 commit message BEFORE `gt submit`):

```js
python3 ${engineCmdFor(r, 'scripts/qrspi_pr_body.py')} --ticket ${t.id} --slice 1
```

— `.claude/workflows/qrspi-batch.js:843` (it preserves subject+trailer, splices the summary, amends via `gt modify`, prints `{ ok, branch, subject, bytes, error? }`)

**Dependencies:** `gt submit` (Graphite) for publishing; `gh api … pulls/<N> -X PATCH` for post-hoc body. `reviewerFlags(r)` (`.claude/workflows/qrspi-batch.js:480-485`) splices `--reviewers`/`--team-reviewers`. `qrspi_pr_body.py` is the implementation-phase commit-message splicer (design phase uses the heredoc commit message directly as the body, no splicer).

**Implicit contracts:**
- **Publishing always goes through `gt submit`, never `gh`** (project CLAUDE.md; the body-edit lift is body/title only).
- Design/plan PR bodies = the heredoc commit message (no post-hoc splice today). Only implementation uses `qrspi_pr_body.py` to splice `pr-summary.md` into the slice-1 commit message before submit.
- A post-hoc body PATCH must use the REST API, NOT `gh pr edit`.

---

## Q12: How does the advisory mode currently SHA-lock the PR head, and what code path enforces that lock so gate mode can be confirmed to NOT SHA-lock while leaving advisory's lock byte-for-byte intact?

**Answer:** The advisory (only) path SHA-locks by: (1) the Resolve worker records the PR head SHA BEFORE the panel (`gh pr view <PR> --json headRefOid --jq '.headRefOid'` → `resolved.headSha`, `.claude/workflows/qrspi-review.js:269-271`); (2) the Synopsis worker re-reads the head SHA AFTER all writes (step 6, `:486-490`) and returns it as `headShaAfter`; (3) **the ENGINE — not the worker — compares** `headShaAfter === resolved.headSha` and FAILS the run if they differ or `headShaAfter` is blank (`:506-511`). The worker's own `shaUnchanged` self-report is advisory only; the engine's comparison is authoritative. A gate mode that LANDS a rewrite into the design branch (a real commit) would deliberately NOT perform this re-assert (the head SHA is EXPECTED to change). To leave advisory byte-for-byte intact, a gate path must branch around this `shaMatches` check rather than weaken it — the existing block (`:502-511`) must remain reachable and unchanged for the advisory/propose-only path.

**Evidence:**

```js
const headShaAfter = typeof fin.headShaAfter === 'string' ? fin.headShaAfter.trim() : ''
const shaMatches = headShaAfter !== '' && headShaAfter === String(resolved.headSha).trim()
if (!shaMatches) {
  log(`review-${PHASE_KEY} ${TICKET}: PR head SHA changed or unverifiable ...`)
  return { ok: false, ..., error: `propose-only invariant violated: PR head SHA ...` }
}
```

— `.claude/workflows/qrspi-review.js:502-511`

Before-snapshot (Resolve step 3) and after-snapshot (Synopsis step 6):

```
3. Record the PR head SHA NOW (the propose-only "before" snapshot):
     gh pr view <PR> --json headRefOid --jq '.headRefOid'
...
6. Re-read the PR head SHA (the propose-only "after" snapshot) ... gh pr view ${resolved.pr} ...
   The ENGINE — not you — compares it against the resolve snapshot ${resolved.headSha} ...
```

— `.claude/workflows/qrspi-review.js:269-271`, `:486-490`

**Dependencies:** the comparison consumes `resolved.headSha` (RESOLVE_SCHEMA `:187-206`) and `fin.headShaAfter` (SYNOPSIS_SCHEMA `:209-221`). No external module — the lock is pure engine JS string comparison.

**Implicit contracts:**
- A blank `headShaAfter` is treated as a violation (fail closed — cannot prove the branch is untouched).
- The propose-only invariant (engine header `:40-46`) forbids any branch-mutating `gt`/`gh` command in advisory mode. Gate mode (which DOES mutate the branch by landing a rewrite) is the inverse and must be a separate code path, not a relaxation of this check.

---

## Q13: How do existing critic/config/synthesize scripts structure their stdlib-only `_test.py` siblings, and what test conventions would the new debate-stabilization, dissent-preserving reduce, and convergence/cap pure cores follow?

**Answer:** Every pure-core script has a sibling `scripts/<name>_test.py` that is a standalone stdlib `unittest` module: it inserts the scripts dir on `sys.path`, imports the module under test, defines small `_helper` builders for fixtures, groups assertions into `unittest.TestCase` subclasses, and ends with `unittest.main()` runnable via `python3 scripts/<name>_test.py` (exit 0/non-0). `scripts/run_tests.py` discovers every `*_test.py`, runs each as its own subprocess, and exits non-zero if any fail (the CI gate via `.github/workflows/tests.yml`). New debate-stabilization / dissent-preserving-reduce / convergence-cap pure cores would follow the same pattern: a pure `scripts/qrspi_<name>.py` with a `_test.py` sibling, fail-closed semantics tested with in-memory dicts, and registration is automatic (discovery is by filename glob — no manual registry).

**Evidence:**

```python
import os, sys, unittest
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qrspi_review_synopsis import (
    DECISION_READINESS_LENS, ledger_row_fields, partition_decision_readiness, render_synopsis,
)
def _verdict(lens, passed, findings=None, non_blocking=None): ...
class PartitionDecisionReadinessTests(unittest.TestCase):
    def test_partitions_out_the_decision_readiness_lens(self): ...
```

— `scripts/qrspi_review_synopsis_test.py:1-40`

Discovery + subprocess-per-file runner:

```python
def discover_tests(scripts_dir=SCRIPT_DIR, pattern=None):
    names = sorted(n for n in os.listdir(scripts_dir) if n.endswith("_test.py"))
    if pattern: names = [n for n in names if pattern in n]
    return [os.path.join(scripts_dir, n) for n in names]
```

— `scripts/run_tests.py:38-49` (per-file subprocess at `:51-60`; exits non-zero on any failure)

**Dependencies:** `run_tests.py` is the aggregating runner and the CI regression gate (`.github/workflows/tests.yml`, per the project CLAUDE.md). 40 `_test.py` files exist under `scripts/` (e.g. `qrspi_critic_synthesize_test.py`, `qrspi_critics_config_test.py`, `qrspi_review_record_test.py`, `qrspi_review_synopsis_test.py`).

**Implicit contracts:**
- A test file MUST be named `*_test.py` to be discovered; `run_tests.py` itself and `run_tests_test.py` are handled specially (`run_tests.py:30-33`).
- Tests are stdlib-only (no pytest), self-locating, exit-code-gated.
- Pure cores are argument-driven (no IO) so tests exercise them with in-memory dicts (the `synthesize`/`build_record`/`resolve_*` precedent).
- JS (`qrspi-batch.js` / `qrspi-review.js`) coverage is deliberately out of scope — the workflow files are harness-coupled and not unit-testable (`run_tests.py:21-22`; project CLAUDE.md).

---

## Q14: What existing test coverage guards the advisory mode's behavior, and which tests would have to keep passing unchanged to prove `advisory` mode is behaviorally byte-for-byte preserved?

**Answer:** The advisory engine `qrspi-review.js` is JS and has **NO direct unit test** (JS workflow coverage is deferred — `run_tests.py:21-22`). Its behavior is guarded INDIRECTLY by the pure Python cores it drives, each with a `_test.py` sibling that must keep passing:
- `scripts/qrspi_review_synopsis_test.py` — `partition_decision_readiness`, `ledger_row_fields`, `render_synopsis` (the axis table, advisory section, decision-readiness section, terminal action).
- `scripts/qrspi_review_record_test.py` — `build_record` shape (`phase/rounds/terminalAction/agreement/mode`), the `{lens,pass,findingsCount}` rounds reduction, the `mode:"on-demand-review"` discriminator.
- `scripts/qrspi_critic_synthesize_test.py` — the `{pass, findings}` reduce (all-pass ⇒ pass, any-fail ⇒ fail, dedupe, fail-closed empty).
- `scripts/qrspi_critic_metrics_test.py` — `VALID_TERMINAL_ACTIONS` validation (converged/exhausted valid; revise rejected).
- `scripts/qrspi_metrics_append_test.py` — the ledger envelope/append.
- `scripts/qrspi_critics_config_test.py` — `resolve_review_lens_model` (and the design/impl resolvers).
- `scripts/qrspi_review_agreement_test.py` — `compute` (retained; advisory passes `agreement={}`, but the module/tests remain).

To prove advisory mode is byte-for-byte preserved, **all of the above must pass unchanged**, since they pin the deterministic Python transforms the advisory path invokes verbatim. The JS-level propose-only invariant (SHA re-assert) is not unit-tested and is verified end-to-end.

**Evidence:**

```python
# JavaScript test coverage (the qrspi-batch.js workflow orchestrator) is
# deliberately out of scope here and deferred to future development.
```

— `scripts/run_tests.py:19-22` (and `qrspi-review.js` is likewise uncovered; the engine header `:48-61` records that "there is no JS<->python parser seam to fixture here")

```python
rec = m.build_record(phase="design", rounds=verdicts, terminal_action="cap_reached", agreement=_agreement())
self.assertEqual(rec["rounds"], [{"lens": "design-review", "pass": False, "findingsCount": 2}])
```

— `scripts/qrspi_review_record_test.py:16-31`

**Dependencies:** the engine header (`.claude/workflows/qrspi-review.js:48-61`) explicitly states the deterministic Python transforms it drives are "ALREADY stdlib-unit-tested under scripts/run_tests.py" and that no new JS↔python parser seam exists to fixture.

**Implicit contracts:**
- Behavioral preservation of advisory mode is proven at the Python-core level (the transforms), not at the JS-engine level.
- Adding `mode:'gate'` must not alter the inputs passed to these cores on the advisory path, so their tests keep passing.
- `qrspi_review_agreement` is retained even though advisory passes `agreement={}` — its test must keep passing.

---

## Q15: How are per-phase process logs (if any) currently rendered and committed alongside design artifacts, and what rendering module would produce the per-round `.qrspi/<id>/design-review-log.md` content?

**Answer:** **There is NO per-phase process-log artifact rendered or committed today.** Grepping for `review-log` / `design-review-log` / `render.*log` / `process.*log` across `scripts/*.py` and `.claude/workflows/*.js` finds only incidental matches (`qrspi_pr_state.py`, `qrspi_pr_body_test.py`) — none render a per-round review log. The design Finalize worker stages and commits ONLY the three artifacts `questions.md, research.md, design.md` (`.claude/workflows/qrspi-batch.js:716-717`); the implementation phase has an `impl-log.md` artifact (produced by the `qrspi-implement` agent and committed with the slices — `.claude/workflows/qrspi-batch.js:805-806`, `:830`), but that is a producer log, not a review-round log. The closest existing rendering module is `scripts/qrspi_review_synopsis.py` (`render_synopsis`), which renders the axis-enumerated synopsis Markdown (panel verdicts, blocking findings, advisory non-blocking notes, decision-readiness, terminal action) — but it renders a SINGLE round-0 synopsis posted as a PR comment, NOT a committed per-round file, and it has no "debate outcomes / preserved dissent / reviser summary / verification results" sections. A new `.qrspi/<id>/design-review-log.md` would need either an extension of `render_synopsis` or a new pure renderer + a commit step (and a new `qrspi_persist.py` artifact name, since `design-review-log` is not in the `ARTIFACTS` enum — see Q3).

**Evidence:**

```python
def render_synopsis(verdict_array, decision_readiness, terminal_action):
    # 1. Axis enumeration | 1b. Blocking findings text per FAIL lens
    # 2. Advisory non-blocking notes | 3. Decision readiness (blocking for human)
    # 4. Terminal action
```

— `scripts/qrspi_review_synopsis.py:128-217` (the only existing review-rendering module; output goes to a PR comment, not a committed file)

The synopsis is written to a scratch file then posted as a comment (never committed):

```
3. Render the axis-enumerated synopsis to ${synopsisFile} ...
4. Post the synopsis as ONE top-level advisory comment to PR ... qrspi_comment_reply.py ...
```

— `.claude/workflows/qrspi-review.js:459-476` (`synopsisFile = /tmp/phase-stage/<id>/review/synopsis-<phase>.md`, `:414`)

Design commit step stages only the three producer artifacts:

```js
2. Stage ONLY those three artifacts ... single commit (subject "${t.id} [QR]: Design — ${t.title}") ...
```

— `.claude/workflows/qrspi-batch.js:717`

**Dependencies:** `render_synopsis` is called in the Synopsis worker (`.claude/workflows/qrspi-review.js:469`). The implementation producer log `impl-log.md` flows through `art(wd, id, 'impl-log.md')` and the `qrspi-implement`/`qrspi-pr` agents. No module renders a committed per-round review log.

**Implicit contracts:**
- Today's review output is ephemeral (a PR comment from a `/tmp` scratch file) + a `critic-metrics.jsonl` ledger line — neither is a committed Markdown log.
- A committed `design-review-log.md` would be a NEW artifact: it is absent from `qrspi_persist.py`'s `ARTIFACTS` enum (`scripts/qrspi_persist.py:52`) and from the design Finalize commit set, so both would need extending.
- The ledger (`critic-metrics.jsonl`) is the structured per-step record; a human-readable per-round log is a distinct, currently-nonexistent artifact.

---

## Discovered Patterns

- **JS↔Python worker seam.** Both `qrspi-batch.js` and `qrspi-review.js` run in a sandbox that cannot execute python or touch the filesystem, so EVERY python/gh operation is handed to a worker agent as a literal command STRING and the worker returns a JSON envelope validated by a JSON schema at the `agent()` boundary (`.claude/workflows/qrspi-review.js:48-61`). Pure logic lives in `scripts/*.py` (unit-tested); the JS is thin orchestration glue.
- **Self-locating scripts.** `qrspi_persist.py`, `qrspi_metrics_append.py`, `qrspi_critics_config.py`, `qrspi_resolve.py` all resolve the repo root from `__file__`/`git-common-dir` (`qrspi_paths.resolve_repo_root`), never cwd, so a worker types only short tokens (`--ticket`, `--artifact`) and every `qrspi`-laden path is computed in Python (the weak-worker path-mangling mitigation, "Fix A").
- **Uniform opt-in (default OFF) config vocabulary.** Every `enabled` flag flips only on an explicit boolean (`resolve_enabled(cfg, False)`); positive ints via `_pos_int_or(value, default)`; optional string overrides are OMITTED when unset (not None). Critics are uniformly opt-in.
- **Fail-closed reducers.** `synthesize` (empty/garbled ⇒ not-passed), `next_action`, `build_record` (rejects non-terminal `revise`), `partition_decision_readiness` — all coerce defensively so a missing/garbled verdict can never silently pass.
- **Propose-only invariant via SHA re-assert.** The on-demand review engine captures the PR head SHA before the panel and re-asserts it unchanged after, comparing in the ENGINE (not trusting the worker's self-report), failing closed on a blank or changed SHA.
- **Decision-readiness is terminal-advisory.** It is partitioned OUT of the synthesize input so it can NEVER drive a revise round; it feeds the synopsis only. Its agent emits a distinct `DecisionReadinessVerdict`, not `{pass, findings}`.
- **Test discovery by filename glob.** New pure cores need no registration — a `*_test.py` sibling is auto-discovered by `run_tests.py` and gated in CI.

## Inconsistencies

- **"Advisory mode" presupposes a mode that does not exist.** The questions repeatedly reference an existing `advisory` mode and a future `gate` mode. In the current code, `qrspi-review.js` has NO `mode` parameter — it has a single propose-only behavior that is *called* advisory. Adding `{...mode:'gate'}` (Q1, Q4) is net-new surface in both the engine and the three SKILL wrappers, not a toggle on an existing dispatch.
- **The reviser is propose-only/scratch-only, but a producer gate must LAND a rewrite.** `qrspi-critic-reviser` writes ONLY to a `/tmp/phase-stage/<id>/review/` scratch path and forbids any tracked-path write or `gt`/`gh` command (`.claude/agents/qrspi-critic-reviser.md:35-37, 66-71`). `qrspi_persist.py` only persists `/tmp/phase-stage/<id>/<artifact>.md` (no `review/` segment) and only the six enum artifact names (`scripts/qrspi_persist.py:52, 62-64`). So "un-dormant the reviser to gate the producer" (Q7) requires either changing the reviser's write contract or adding a scratch→worktree persist step the current persist script does not support.
- **Stale doc comment on terminal actions.** `scripts/qrspi_critic_metrics.py:34-38` notes `design.md:76` is stale (lists only `converged/cap_reached`) while the faithful set is four values; `structure.md:19` flags it. The authoritative set is `qrspi_critic_metrics.VALID_TERMINAL_ACTIONS = {converged, cap_reached, exhausted, aborted}`.
- **No committed process log exists** despite Q15 framing it as "rendered and committed alongside design artifacts today." The only review rendering (`render_synopsis`) produces an ephemeral PR comment, and the only committed log (`impl-log.md`) is an implementation-phase producer log, not a per-round design review log.
- **`config.example.json` says the batch runs NO phase critics**, and the `critics` block "now drives ONLY the on-demand /review-* family" (`.qrspi/config.example.json:7`). A producer-gate review loop in `doDesign` (Q6, Q10) re-introduces a batch-side consumer of `critics.design.*`, partially reversing the RUS-88 retirement of batch critics — a design-intent tension to surface.
