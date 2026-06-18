# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-18T00:00:00Z
**Generated:** 2026-06-18T21:35:00Z
**Status:** draft

## Q1: At each phase transition (start, end, success, failure, retry), where in the orchestrator's control flow does execution currently pass, so an event emission call can be threaded in without disrupting the existing flow?

**Answer:** The orchestrator (`.claude/workflows/qrspi-batch.js`) has two layers of control-flow seam points:

1. **The harness-injected `phase(label)` global** marks every phase transition. It is called at module top-level (`phase('Query')` line 1418, `phase('Sync')` line 1600) and inside every action handler at its entry: `doDesign` calls `phase('Design')` then `phase('Finalize')`; `doPlan` → `phase('Plan')`/`phase('Finalize')`; `doImplementation` → `phase('Implementation')`/`phase('Finalize')`; `doSubmit`/`doReset`/`doRevise`/`doLand` → `phase('Finalize')`; `runReconciliation` → `phase('Reconcile')`. `phase` is an injected global (documented in `docs/testing-dynamic-workflows.md:34-35`), not defined in the file — so it cannot be wrapped in-place without the harness.

2. **The per-ticket dispatch `switch` (lines 1644-1662)** is the single funnel where a ticket's resolved action is executed. Every action routes through it inside a `try/catch` (lines 1618-1675) that already provides per-ticket isolation. The `for` loop (line 1610) iterating `tickets` is the per-ticket boundary; `resolveTicket` (1619), `ensureRestacked` (1634), and the action handler (1645-1654) are the success/failure points; `finResult`/`failTicket`/`skip` (lines 1324-1333, 466-474) are where success and failure outcomes are constructed.

3. **`runPhase` (lines 512-532)** is the per-artifact boundary the questions reference: it spawns one phase agent (line 517), then persists (line 525), returning `true`/`false`. The resume short-circuit (`existing[name]` → reuse, line 513) and the two failure returns (517 `res===null`, 527 persist failed) are the natural start/end/success/failure hooks for a phase-scoped event.

**Evidence:**

```js
async function runPhase(name, agentType, prompt, existing, id, phaseLabel) {
  if (existing && existing[name]) { log(`  ${id}: reusing existing ${name}.md`); return true }
  const res = await agent(prompt, { label: `${name}:${id}`, phase: phaseLabel, agentType })
  if (res === null) { log(...); return false }
  const p = await persistArtifact(id, name, phaseLabel)
  if (!p || !p.ok) { log(...); return false }
  log(`  ${id}: ${name} → saved ${p.bytes ?? '?'}B ...`); return true
}
```

— `.claude/workflows/qrspi-batch.js:512-532`

```js
const a = r.decision.action
log(`  ${t.id}: decision=${a} — ${r.decision.reason}`)
let res
switch (a) {
  case 'run_design': res = await doDesign(t, r); break
  case 'advance': res = r.decision.nextPhase === 'plan' ? await doPlan(t, r) : ...
  case 'submit': res = await doSubmit(t, r); break
  ...
}
```

— `.claude/workflows/qrspi-batch.js:1641-1662`

**Dependencies:** `agent()`, `parallel()`, `phase()`, `log()`, `args`, `budget` are harness-injected globals (no `import`/`require`; see `docs/testing-dynamic-workflows.md:34-35`). The file is "harness-coupled imperative shell" with a top-level `return` (lines 1591, 1682) and is explicitly NOT unit-testable in isolation (CLAUDE.md "JS coverage … is deferred"; `docs/testing-dynamic-workflows.md`).

**Implicit contracts:** An emission threaded into JS must NOT do its own I/O (the JS sandbox cannot run python/git/gh — every side-effecting call is delegated to a worker `agent()` running a self-locating python script). Any new event write would have to follow the same pattern: a worker agent runs a deterministic `scripts/qrspi_*.py` and returns parsed JSON. `log()` writes to the run log (the existing human-facing channel); it is the only synchronous reporting primitive available in JS.

## Q2: How does the orchestrator currently obtain `runId`, `ticket_id`, `phase`, `agentType`, and `slice_number` at the point where a phase fires, so these can be populated into the event `context` and identity fields?

**Answer:**
- **`ticket_id`:** `t.id` from the ticket record (`{id,title,status,createdAt}`, schema lines 178-196), e.g. `t.id` at line 1611. Always available in every handler as `t.id`.
- **`phase`:** the literal label string passed to `phase('Design')` etc., and the `phase:` option on every `agent()` call (e.g. `{ label: ..., phase: 'Design', agentType }` at line 517). It is also carried as `r.decision.phase`/`r.decision.nextPhase` from the resolver decision (Q7).
- **`agentType`:** the literal passed to `agent(prompt, { agentType })` — e.g. `'qrspi-questions'`, `'qrspi-research'`, `'qrspi-design'` in `doDesign` (lines 688-704), `'qrspi-implement'` (line 807), `'qrspi-pr'` (line 835). Finalize/worker agents pass NO `agentType` (they are generic workers).
- **`slice_number`:** `s.n` from the impl-setup `slices[]` (schema line 408, loop at line 786, used as `SLICE_NUMBER = ${s.n}` line 791 and `slice ${s.n}` throughout `doImplementation`).
- **`runId`:** **NOT FOUND in qrspi-batch.js.** There is no `runId` variable, no `crypto.randomUUID`, no `Date.now()` in the workflow file (grep returned zero hits in `.claude/workflows/`). The ONLY `runId` producer in the codebase is the **separate, currently-unused** critic-metrics path: `scripts/qrspi_metrics_append.py` takes `--run-id` as a REQUIRED CLI arg supplied by a caller and stamps it onto each ledger line (lines 78, 111-113). That caller is not the live autonomous batch (the autonomous batch "runs no critics", per `runPhase` comment line 510-511 and `.qrspi/config.example.json` critics block). So a `runId` would have to be MINTED — see Inconsistencies for the prior `Date.now()`/`Math.random()` bug (project memory "qrspi-batch runId Date.now bug").

**Evidence:**

```js
async function resolveTicket(t) {
  phase('Resolve')
  const ticketFile = `/tmp/phase-stage/${t.id}/ticket.md`
  ...
}
```

— `.claude/workflows/qrspi-batch.js:537-544` (`t.id` is the universal ticket identity)

```python
parser.add_argument("--run-id", dest="run_id", required=True,
                    help="The orchestrator's per-invocation run id (always "
                         "stamped onto the appended line as runId)")
```

— `scripts/qrspi_metrics_append.py:111-113` (the only `runId` sink — caller supplies it)

**Dependencies:** ticket records come from the Query phase `mcp__linear__list_issues` / `get_issue` workers (TICKETS_SCHEMA). `slices[]` come from the impl-setup worker (IMPL_SETUP_SCHEMA).

**Implicit contracts:** `phase` and `agentType` are string literals chosen at the call site — there is no central enum in JS. The machine phase vocabulary lives in the resolver (Q7). Any `runId` design must account for the harness regenerating a named workflow from a cached snapshot mid-session (project memory "qrspi-batch-runid-datenow-bug") and the determinism rules forbidding `Date.now()`/`Math.random()` in workflow scripts.

## Q3: How is the active phase's `span_id` currently held (if at all) across the nested critic/retry/command shell-outs within a phase, so it can be passed as `parent_span_id` to nested events?

**Answer:** **NOT FOUND — there is no span/trace concept in the codebase.** Searches for `span_id`, `parent_span_id`, `traceId`, `span` returned nothing in `.claude/workflows/` or `scripts/`. Nesting today is expressed purely as JS call structure: a phase handler (`doRevise`) calls helpers (`respondToComments` line 941, `bumpCiReviseTrailers` line 1026, `resetCiReviseTrailer` line 1037), each of which spawns its own worker `agent()` calls in sequence. There is NO retry loop inside a phase (the autonomous batch advances "at most ONE autonomous step" per run, lines 36-37; failures return, they do not retry — e.g. `runPhase` returns `false` on failure, no loop). The former critic/retry loop was **removed** (commit `1898b39 Remove all autonomous batch critics`; `runPhase` comment lines 510-511: "the design panel, N-select, coherence pass, and research citation check were all removed"). The only identity threaded through nested calls is `(t, r, d)` — the ticket, resolve envelope, and decision — plus per-comment indices (`#${i}` in labels, line 1106). The `label` option on `agent()` (e.g. `revise:${t.id}`, `respond-comment:${t.id}#${i}`, `ci-revise-bump:${t.id}:${branch}`) is the closest existing analogue to a span identifier and is the natural carrier for any parent/child correlation.

**Evidence:**

```js
// One peer-reviewer worker per comment ... Sequential ...
for (let i = 0; i < targets.length; i++) {
  const ct = targets[i]
  const fin = await agent(`...`, { label: `respond-comment:${t.id}#${i}`, phase: 'Finalize', schema: COMMENT_REPLY_SCHEMA })
  ...
}
```

— `.claude/workflows/qrspi-batch.js:1072-1107` (nesting is call structure; identity carried as `t.id`+index in `label`)

**Dependencies:** none — no span infrastructure exists.

**Implicit contracts:** Any parent/child relation would be net-new. The existing convention is that the `label` string encodes a human-readable hierarchy (`<action>:<ticket>#<index>`/`:<branch>`); an event design could reuse that convention or mint ids in JS (subject to the no-`Date.now()`/no-`Math.random()` determinism rule).

## Q4: What is the existing config-reading mechanism's capability for nested keys, and does it support reading the `observability.*` block versus only top-level keys like `ciReviseCap`?

**Answer:** **The config reader supports ONLY a single flat top-level key — NO nested/dot-path keys.** `scripts/qrspi_config.py`'s `select_value(config, key, default)` does a bare `config.get(key)` (line 41) with no dot-splitting. The CLI takes `--key <name>` and resolves exactly one top-level key (lines 63-71). It therefore CAN read `ciReviseCap` (and does, via `load_ci_revise_cap` in `qrspi_resolve.py:407-410` which calls `qrspi_config.read_config` then `config.get("ciReviseCap")`), but CANNOT read `observability.eventLog` etc. as a path. To read the proposed `observability.*` block you would either (a) read the whole `observability` object via `--key observability` and parse its sub-keys in the consumer, or (b) add nested-key support to `qrspi_config.py`. The JS-side `parseConfigEnvelope` (qrspi-batch.js:362-372) additionally REJECTS any non-string value: `if (typeof env.value !== 'string') return { ok:false ... }` (line 370) — so the JS config path can ONLY consume string-valued top-level keys; an object value (`observability`) would fail JS validation outright. This is a documented, already-bit constraint (project memory "qrspi-config-reader-single-key-only": "plans must specify nested-config read mechanism, not assume an existing path").

**Evidence:**

```python
def select_value(config: dict, key: str, default: str) -> str:
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`

```js
if (typeof env.value !== 'string') return { ok: false, error: `config: envelope value not a string (got ${env.value})` }
```

— `.claude/workflows/qrspi-batch.js:370`

**Dependencies:** `qrspi_resolve.py` (`load_ci_revise_cap`, `read_config`) and the Query-scope worker (qrspi-batch.js:1470-1492) are the two live consumers. `read_config` (qrspi_config.py:45-56) is best-effort: returns `{}` on any `OSError`/`ValueError`, never raises.

**Implicit contracts:** A config consumer must tolerate a missing file (`{}` → per-key default). The `DEFAULTS` map (line 33) holds per-key defaults; unknown keys default to `""`. `ciReviseCap` is read directly in Python via `read_config(...).get("ciReviseCap")` (NOT via the `--key` CLI), with `coerce_cap` (qrspi_resolve.py:391-401) enforcing positive-int / default-3. The `.qrspi/config.example.json` has NO `observability` block today (it has `critics`, `ciReviseCap`, `linearProject`, `linearTeam`, `reviewers`, `teamReviewers`).

## Q5: What is the signature and call convention of the existing standalone scripts that a new shared importable logger module must match to be invoked from both Python scripts and the JS orchestrator?

**Answer:** Every standalone `scripts/qrspi_*.py` follows an identical convention:

1. **Self-location.** Two patterns coexist. The simple scripts derive the repo root from `__file__` two levels up: `REPO_ROOT = Path(__file__).resolve().parents[1]` (`qrspi_config.py:29`). The worktree-aware scripts use the shared helper: `REPO_ROOT = qrspi_paths.resolve_repo_root(cwd=os.getcwd(), validate=False)` (git-common-dir first, so it resolves the MAIN checkout even from a worktree — `qrspi_persist.py:45-50`, `qrspi_metrics_append.py:52-55`). A logger that must write to a path surviving worktree teardown should use `qrspi_paths.resolve_repo_root` (the main checkout), like `qrspi_metrics_append.py`.
2. **argparse CLI** with short token args (`--ticket`, `--artifact`, `--record`, `--run-id`); never a long qrspi-laden path typed by the caller (the path-mangling-avoidance rationale, `qrspi_persist.py:1-29`).
3. **Single JSON envelope on stdout** ending with a trailing newline (`json.dump(env, sys.stdout, indent=2); print()`). The envelope always carries an `ok` boolean and an `error` string on failure (`qrspi_persist.py:121-133`, `qrspi_metrics_append.py:137-149`, `qrspi_config.py:71-74`).
4. **Exit code mirrors `ok`** (`return 0 if error is None else 1`).
5. **Pure helpers separated from I/O** so each has a stdlib-only `_test.py` sibling (Q14).

**JS call convention:** the JS sandbox CANNOT run python, so it spawns a worker `agent()` whose prompt says "Run EXACTLY this one command verbatim … `python3 ${engineCmd('scripts/qrspi_X.py')} --ticket ${id} …`" and "Output that JSON as your FINAL message, exactly and verbatim". The JS then parses it with a dedicated `parseXEnvelope` (extract outermost `{...}` via `extractJsonObject`, `JSON.parse`, validate `ok` boolean). See `persistArtifact` (lines 492-505) as the canonical importable-from-JS shape, and `engineCmd`/`engineCmdFor` (lines 76, 105) for path construction.

**Evidence:**

```js
async function persistArtifact(id, name, phaseLabel) {
  return await agent(
    `You are the PERSIST worker for ${id} artifact "${name}". Your cwd is the main repo root.
Run EXACTLY this one command verbatim ...
  python3 ${engineCmd('scripts/qrspi_persist.py')} --ticket ${id} --artifact ${name}
... Parse that JSON and return it verbatim. ...`,
    { label: `persist:${id}:${name}`, phase: phaseLabel, schema: PERSIST_SCHEMA })
}
```

— `.claude/workflows/qrspi-batch.js:492-505`

**Dependencies:** `qrspi_paths` (sibling import, `sys.path.insert(0, ENGINE_ROOT)`); `engineCmd(rel)` = `${ENGINE_ROOT}/${rel}` for runner-cwd workers; `engineCmdFor(r, rel)` = root derived from `r.worktreeDir` for worker-cwd (worktree) prompts — using `engineCmd` from a worktree worker is a known bug class (project memory "batch-worker-cwd-engine-path").

**Implicit contracts:** A logger module importable from BOTH Python and JS must expose (a) pure functions for the Python `_test.py` and direct import by sibling scripts, AND (b) a CLI entrypoint that emits a single stdout JSON envelope so the JS worker pattern can invoke it. Writing must be fail-closed and verify non-emptiness (the persist/append precedent), or fail-OPEN if it mirrors the Linear best-effort precedent (Q15) — the two precedents differ; the design must choose.

## Q6: How does the resolver currently expose the `CI-Revise-Attempt` trailer value and the frontier head commit's `committedDate` that the backoff policy needs to compute `min(base · 2^(attempt-1), cap)`?

**Answer:**
- **`CI-Revise-Attempt`:** parsed by `qrspi_pr_state.ci_revise_attempt(message)` (lines 115-130) from the head-commit message via regex `^CI-Revise-Attempt:\s*(\d+)\s*$` (last occurrence wins; absent/malformed → 0). It is attached to each PR shape as **`ciReviseAttempt`** (parse_pr_nodes lines 303-320) — but **forced to 0 whenever `ciState != "red"`** (the read-side reset, lines 303-308). The resolver aggregates it via `ci_revise_attempt_of(phases, name)` (qrspi_resolve_state.py:129-138; `max(...)` across slices for implementation). **However, `qrspi_resolve.py`'s OUTPUT ENVELOPE does NOT expose `ciReviseAttempt` at top level** — grep found no `ciReviseAttempt` emission in `build_envelope` (lines 268-331). It lives only inside `phases.*` (not re-emitted), and is consumed internally by the resolver to compare against the cap. So the attempt count is computed and used inside python but is NOT currently surfaced to the JS consumer as a first-class envelope field.
- **`committedDate`:** **NOT FOUND ANYWHERE.** grep for `committedDate`/`committed_date`/`committerDate` returned ZERO hits across `scripts/` and `.claude/`. The GraphQL `PR_QUERY` (qrspi_pr_state.py:26-69) fetches `commits(last:1){ commit { message statusCheckRollup {...} } }` — it does NOT request `committedDate` or `authoredDate`. So the head-commit timestamp the backoff `min(base · 2^(attempt-1), cap)` formula needs is **not gathered today** and would require adding `committedDate` to the GraphQL commit selection and threading it through `parse_pr_nodes` → resolver → envelope.

**Evidence:**

```python
commits(last:1) {
  nodes { commit { message statusCheckRollup { state contexts(first:100){...} } } }
}
```

— `scripts/qrspi_pr_state.py:48-64` (no `committedDate` / timestamp field requested)

```python
if ci_state == "red":
    attempt = ci_revise_attempt(_head_commit(node).get("message"))
else:
    attempt = 0
return { ..., "ciState": ci_state, "ciFailingChecks": failing, "ciReviseAttempt": attempt }
```

— `scripts/qrspi_pr_state.py:303-320`

**Dependencies:** `ci_revise_attempt` (parser) → `parse_pr_nodes` (per-PR shape) → `ci_revise_attempt_of`/`ci_state` (resolver aggregation) → `resolve(..., ci_revise_cap)` (decision). The envelope re-emit helpers (`ci_failing_of`, `ci_failing_checks_of`, `red_branches_of`) in `qrspi_resolve.py:192-265` are the precedent for surfacing a CI field at top level — `ciReviseAttempt`/`committedDate` would need a new helper of the same shape.

**Implicit contracts:** The attempt counter is the EFFECTIVE (not-red→0-normalized) value at gather time (`qrspi_resolve_state.ci_revise_attempt_of` docstring lines 129-134: "read directly here, never re-zeroed"). The trailer is written by `qrspi_ci_revise_bump.py` (orchestrator-owned, qrspi-batch.js:1183-1209) and reset by `resetCiReviseTrailer`. Any backoff timing must reuse this SAME trailer to avoid double-counting (Q9) and must add committedDate to the GraphQL query (it is absent today).

## Q7: Where is the canonical machine vocabulary for `phase` values (`design`, `plan`, `implementation`) currently defined in the resolver?

**Answer:** In `scripts/qrspi_resolve_state.py`, the module-level constant `PHASES = ["design", "plan", "implementation"]` (line 61). It is the single source of phase ordering: `_order(phase)` returns `PHASES.index(phase)` (lines 80-81), and `PHASES[_order(active) + 1]` computes the next phase (line 331). The same list appears in `qrspi_pr_state.py`'s docstring (lines 14-17, "Phase -> head branch") and is realized as branch names `<ticket>/design`, `<ticket>/plan`, `<ticket>/slice-<n>` (note: implementation's branch form is `slice-<n>`, not `implementation`). A new `events.schema.json` enum must match `["design", "plan", "implementation"]` exactly. Note the resolver ALSO has a sibling `ACTIONS` tuple (lines 68-77: `entry_blocked, run_design, submit, wait, revise, advance, land, reset`) and the JS mirror `RESOLVE_ACTIONS` set (qrspi-batch.js:212-214) — if the event log records actions/decisions, those are the canonical action vocabularies.

**Evidence:**

```python
PHASES = ["design", "plan", "implementation"]
```

— `scripts/qrspi_resolve_state.py:61`

```python
def _order(phase): return PHASES.index(phase)
```

— `scripts/qrspi_resolve_state.py:80-81`

**Dependencies:** `qrspi_resolve_state.resolve` (the decision function), `qrspi_pr_state.build_state` (gathers per-phase), the JS dispatch switch (consumes `decision.phase`/`nextPhase`).

**Implicit contracts:** `implementation` is the machine phase name but its branches are `slice-<n>` (qrspi_pr_state.py:17, 376-384). Linear REPORTING statuses are a SEPARATE vocabulary (`Selected`/`Design Review`/`Plan Review`/`Code Review`/`Done`; SKILL.md:494-500, CLAUDE.md) and must not be conflated with machine phase values.

## Q8: How does `qrspi_cleanup.py` tear down worktrees today, and does it touch anything under `.qrspi/observability/` in the main checkout, given the event log must survive worktree teardown?

**Answer:** `scripts/qrspi_cleanup.py` reaps a fully-merged ticket's local state: it removes the `.worktrees/<id>` worktree via `git worktree remove --force <wt_path>` (`_remove_worktree`, lines 168-181), deletes local branches via `git branch -D` (`_delete_local_branch`, lines 184-198), and prunes remote refs. It runs from the MAIN checkout (REPO_ROOT self-located git-common-dir-first) and gates ALL destruction behind a classifier verdict `blocked > destroy > skip` — destroying ONLY a fully-merged clean stack; a dirty worktree → `blocked` (never forced); an in-flight stack → `skip`. It touches **NOTHING under `.qrspi/` in the main checkout** — its destruction targets are the `.worktrees/<id>` directory (which contains that worktree's own `.qrspi/<id>/`), local branches, and origin refs only. There is **no reference to `observability` anywhere in the file** (grep confirmed). Therefore an event log placed at `<main-checkout>/.qrspi/observability/` would SURVIVE worktree teardown — cleanup never reaches into the main checkout's `.qrspi/`. (Caveat: `git worktree remove --force` deletes the worktree's OWN `.qrspi/<id>/` artifacts along with it — so the event log must live in the MAIN checkout, not in any per-ticket worktree, to survive. This is exactly why `qrspi_metrics_append.py` resolves the main-checkout root via `qrspi_paths.resolve_repo_root` and writes to `<root>/.worktrees/<id>/...` — note even THAT path lives inside the worktree and would be reaped; a survive-teardown log must NOT be under `.worktrees/`.)

**Evidence:**

```python
def _remove_worktree(wt_path, dry_run):
    if not os.path.isdir(wt_path): return False
    if dry_run: return True
    rc, out, err = _run(["git", "worktree", "remove", "--force", wt_path], cwd=REPO_ROOT)
    if rc != 0: raise RuntimeError("git worktree remove failed: %s" % (err.strip() or out.strip()))
    return True
```

— `scripts/qrspi_cleanup.py:168-181`

**Dependencies:** `qrspi_paths.resolve_repo_root` (main checkout), `qrspi_restack.worktree_path` (line 56, the `.worktrees/<id>` path). Called from JS `runCleanup` (qrspi-batch.js:1223-1235) which MUST run from the main repo root (its prompt enforces "cwd is the MAIN repo root … the script self-locates REPO_ROOT … must see the real .worktrees/<id>").

**Implicit contracts:** Cleanup is idempotent (missing worktree/branch/ref → clean no-op). It NEVER touches trunk or anything outside `.worktrees/<id>` + branches + origin refs. A `.qrspi/observability/` directory in the main checkout root (a level ABOVE `.worktrees/`) is outside every destruction target and is safe. Anything inside `.worktrees/<id>/` is destroyed with the worktree.

## Q9: How is the `CI-Revise-Attempt` consecutive-red counter currently read and reset (read-side in the gather, writer-side in `doRevise`), so the new backoff timing derives `retry_attempt` from the same trailer without double-counting?

**Answer:** The counter has exactly the two resets CLAUDE.md documents:

1. **Read-side reset (gather, `qrspi_pr_state.parse_pr_nodes`):** the parsed trailer is forced to 0 whenever `ciState != "red"` (lines 303-308: `if ci_state == "red": attempt = ci_revise_attempt(...) else: attempt = 0`). So the EFFECTIVE `ciReviseAttempt` the resolver reads is already 0 unless CI is currently red.

2. **Writer-side, on the CI-failure path (`doRevise` → `bumpCiReviseTrailers`, qrspi-batch.js:1183-1209):** AFTER the content worker returns, for EACH branch in `r.ciRedBranches` (resolver-pre-aggregated, ascending), a thin worker runs `qrspi_ci_revise_bump.py --ticket --branch [--stack]` which increments the trailer by 1 (absent→1), amends message-only, re-publishes, verifies. Fires UNCONDITIONALLY when `ciFailing` (even if the worker reported failure / pushed no content amend) so an unfixable red PR still marches to the cap.

3. **Writer-side, on the NON-CI path (`doRevise` → `resetCiReviseTrailer`, qrspi-batch.js:1131-1150):** every non-CI amend overwrites the trailer to `CI-Revise-Attempt: 0` (idempotent; no-ops when absent/already 0). Called on the green-CI change-request path (line 1037, unconditional) and on the comment-only-with-apply path (line 964).

The trailer is written by a DISTINCT message-only `gt modify -m` after the content amend (the content amender `qrspi_revise_amend.py` preserves the message verbatim and cannot write the trailer — CLAUDE.md). A backoff design deriving `retry_attempt` from this trailer must read it via the SAME `ci_revise_attempt`/`ciReviseAttempt` path and must NOT itself increment it (the orchestrator owns the write; `bumpCiReviseTrailers` is the sole increment authority), or it double-counts.

**Evidence:**

```python
if ci_state == "red":
    attempt = ci_revise_attempt(_head_commit(node).get("message"))
else:
    attempt = 0  # not-red -> 0 read-side reset
```

— `scripts/qrspi_pr_state.py:303-308`

```js
if (ciFailing) { const bump = await bumpCiReviseTrailers(t, r, d); ... }
else if (changeRequested) { await resetCiReviseTrailer(t, r, d, answered) }
```

— `.claude/workflows/qrspi-batch.js:1019-1038`

**Dependencies:** `ci_revise_attempt` (parser) ← `parse_pr_nodes` ← `ci_revise_attempt_of` (resolver) ← `resolve` (cap comparison, qrspi_resolve_state.py:288-303). Increment authority: `scripts/qrspi_ci_revise_bump.py`. Reset authority: `resetCiReviseTrailer` worker. The resolver's cap check (lines 290-303) converts red→`wait`+`ciGaveUp` once `attempt >= ci_revise_cap`.

**Implicit contracts:** The EFFECTIVE count is "consecutive red revises". Any non-red rollup zeros it (read-side); any non-CI amend zeros it (writer-side). A backoff timer MUST consume the same trailer/field — re-deriving `retry_attempt` from a separate counter would diverge from the cap logic. The trailer is durable (committed to the head) and observable from GitHub (Decision 2 Option C, qrspi_pr_state.py:115-123).

## Q10: How is the resolver's CI-evaluation precedence currently ordered, so the new backoff `wait` deferral slots in at the correct position relative to the existing red→revise / pending→wait / at-cap→wait branches?

**Answer:** `resolve()` (qrspi_resolve_state.py:173-374) evaluates in this strict order:

1. **Entry gate** (step 1, lines 200-224): no design branch → `entry_blocked`/`run_design`/blocked.
2. **Reset check** (step 2, lines 226-238): a NON-frontier `CHANGES_REQUESTED` → `reset` (discard downstream). A frontier CR falls through.
3. **Unified feedback handler** (step 2b, lines 240-272): lowest phase with frontier CR OR unaddressed comments → `revise` (folds a same-phase red CI into the one pass via `ci_red`, lines 264-272).
4. **CI-gated revise/wait** (step 2c, lines 274-307): evaluated on the **FRONTIER** (`max(existing, key=_order)`). `red` → if `attempt < cap` → `revise(ciFailing=True)`; else → `wait(ciFailing, ciGaveUp)` (the at-cap park). `pending` → `wait`. `green`/`none` → fall through.
5. **Active-phase block** (step 3, lines 309-374): submit / wait (threads) / wait (not approved) / advance, and the implementation completeness gate + land.

So CI is slot 2c: AFTER the unified-feedback handler (2b) and BEFORE the active-phase block (3). A new backoff `wait` deferral for a red-but-not-yet-due frontier would slot INSIDE step 2c, on the `red` branch, BEFORE (or interleaved with) the `attempt < cap` → revise decision: e.g. if the head commit's `committedDate` plus the computed backoff window has not elapsed, return `wait` instead of `revise`, while still honoring the at-cap→`wait`+`ciGaveUp` terminal. It must remain AFTER 2b (a formal change request still wins) and operate only on the frontier.

**Evidence:**

```python
frontier = max(existing, key=_order)
fci = ci_state(phases, frontier)
if fci == "red":
    attempt = ci_revise_attempt_of(phases, frontier)
    if attempt < ci_revise_cap:
        return decision("revise", phase=frontier, ciFailing=True, ...)
    return decision("wait", phase=frontier, ciFailing=True, ciGaveUp=True, ...)
if fci == "pending":
    return decision("wait", phase=frontier, ...)
```

— `scripts/qrspi_resolve_state.py:288-307`

**Dependencies:** `ci_state`, `ci_revise_attempt_of` (aggregators); `ci_revise_cap` passed in from `qrspi_resolve.load_ci_revise_cap`. Downstream: the JS dispatch reads `decision.action`; `skip()` carries `ciGaveUp` (qrspi-batch.js:469-473).

**Implicit contracts:** Only the frontier's CI gates (a non-frontier red takes no CI action; an upstream regression resets at step 2). The cap-then-wait is the existing terminal signal (`ciGaveUp=True` resolves to `wait`, never `revise` — qrspi-batch.js:1042). `resolve()` is pure and unit-tested (`qrspi_resolve_state_test.py`); the cap default 3 is threaded in by the caller. A backoff slot-in must preserve the precedence comments (lines 274-287) which are load-bearing documentation.

## Q11: What happens in the current write path if a target directory (e.g., `.qrspi/observability/` or `.qrspi/observability/archive/`) does not yet exist, and how do existing scripts handle missing-directory and permission-failure conditions?

**Answer:** Existing write scripts CREATE the parent directory before writing and verify the result. `qrspi_persist.py.persist` does `os.makedirs(os.path.dirname(dest), exist_ok=True)` then `shutil.move`, then re-checks `os.path.getsize(dest)` and returns an error string if the destination is missing/empty (lines 84-92) — **fail-closed**. `qrspi_metrics_append.py.append_line` does the same: `os.makedirs(os.path.dirname(path), exist_ok=True)` then append-mode write, then non-empty verify (lines 88-99) — **fail-closed**. Neither wraps `makedirs`/`open` in a try/except for permission errors: a `PermissionError`/`OSError` from `makedirs` or the write would propagate as an UNCAUGHT exception (the CLI `main` has no top-level try for the I/O; `qrspi_config.py` catches in `main` lines 73-74 but the others do not). By contrast the READ path is best-effort: `qrspi_config.read_config` swallows `OSError`/`ValueError` → `{}` (lines 51-56), and `qrspi_pr_state` git helpers return `0`/`""`/`False` on any error. So: missing directory → auto-created (`exist_ok=True`, no nesting needed for `archive/` since `makedirs` is recursive); permission failure → currently an uncaught crash (`ok:false` only if caught — and `qrspi_config` is the only one that catches at `main`).

**Evidence:**

```python
os.makedirs(os.path.dirname(dest), exist_ok=True)
shutil.move(src, dest)
try:
    out = os.path.getsize(dest)
except OSError:
    return 0, "destination not written: %s" % dest
if out == 0:
    return 0, "destination is empty after move: %s" % dest
return out, None
```

— `scripts/qrspi_persist.py:84-92`

```python
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, "a") as fh:
    fh.write(json.dumps(ledger_line) + "\n")
```

— `scripts/qrspi_metrics_append.py:88-90`

**Dependencies:** `os.makedirs(..., exist_ok=True)` is the universal dir-create idiom; `shutil.move`/`open(..., "a")` the write idioms. `qrspi_paths.resolve_repo_root` resolves the base.

**Implicit contracts:** Recursive `makedirs(exist_ok=True)` means `.qrspi/observability/archive/` is created in one call regardless of which parents exist. The current write scripts are **fail-CLOSED** (verify non-empty, return `ok:false` / non-zero exit) and do NOT currently swallow permission errors — they crash. A "fail-OPEN" emitter (Q15) would be a DEPARTURE from the persist/append precedent and would need its own try/except around `makedirs`+`open`+`flush`/`fsync` returning success-anyway (mirroring the READ-path / Linear best-effort precedent instead).

## Q12: How does the orchestrator currently distinguish stdout (the JSON envelopes it parses) from stderr, so the CLI logger's interactive stderr emission cannot corrupt the parsed stdout stream?

**Answer:** The orchestrator does NOT read raw stdout/stderr streams directly — it never runs subprocesses itself (the JS sandbox cannot). Instead, a worker `agent()` runs the python script and returns the script's stdout AS THE WORKER'S FINAL TEXT MESSAGE (the prompt: "Output the command's STDOUT — the JSON envelope — as your FINAL message: exactly and verbatim, with NO surrounding prose, NO code fences"). The JS then extracts the JSON with `extractJsonObject(text)` (qrspi-batch.js:218-234), a brace-depth, string-aware scan that finds the FIRST balanced top-level `{...}` and ignores everything else. So any extra prose, log lines, or stderr the worker happens to include is tolerated as long as the JSON object is parseable and is the outermost one. The python scripts THEMSELVES write their envelope to `sys.stdout` (`json.dump(env, sys.stdout)`) and would write diagnostics to `sys.stderr` (subprocess capture in `run_tests.py` shows `proc.stdout + proc.stderr` are separable at the subprocess level, lines 66-74) — but the worker boundary collapses both into one text blob. The protection is therefore `extractJsonObject`'s outermost-balanced-object scan, NOT stream separation. A CLI logger emitting to stderr is SAFE only if (a) it writes to stderr (never stdout) so the script's stdout stays a single clean JSON object, AND (b) the worker is still instructed to return only the stdout JSON — because `extractJsonObject` takes the FIRST `{...}`, a stderr JSON-shaped log line preceding the real envelope in the merged blob COULD be mis-grabbed. The robust contract is: keep the envelope the sole/outermost JSON object in the worker's returned text.

**Evidence:**

```js
function extractJsonObject(text) {
  const s = String(text == null ? '' : text)
  const start = s.indexOf('{')
  ...
  for (let i = start; i < s.length; i++) {
    const c = s[i]
    ...
    else if (c === '{') depth++
    else if (c === '}') { depth--; if (depth === 0) return s.slice(start, i + 1) }
  }
  return null
}
```

— `.claude/workflows/qrspi-batch.js:218-234`

**Dependencies:** `extractJsonObject` is consumed by every `parseXEnvelope` (resolve/restack/sync/cleanup/config/land). `extractJsonArray` (lines 259-275) is its bracket twin for the order worker.

**Implicit contracts:** The envelope MUST be valid JSON and SHOULD be the only/outermost `{...}` in the worker's returned text. Scripts emit the envelope to stdout via `json.dump(...sys.stdout); print()`. A logger must emit interactive output to **stderr** to avoid polluting the stdout envelope; even so, because the worker merges streams and `extractJsonObject` grabs the FIRST balanced object, a JSON-shaped stderr line emitted BEFORE the envelope is a real corruption risk — the logger should emit non-JSON-shaped lines, or the script should emit its envelope first.

## Q13: Under the one-sequential-stack-per-ticket invariant, where is it enforced that only one writer touches a given `<ticket_id>.events.jsonl`, and is there any path where that invariant does not hold?

**Answer:** The single-writer invariant is enforced by the orchestrator running **strictly sequentially per ticket**: the main loop is a plain `for` over `tickets` (qrspi-batch.js:1610), and its comment states the reason: "Sequential: tickets share one .git index, so worktree/Graphite ops must not race" (line 1606). Within a ticket, all nested workers (respondToComments, bumpCiReviseTrailers) are ALSO sequential `for` loops with the same rationale (lines 1070-1071, 1188-1189). The ONLY `parallel()` is the Query-phase status sweep (lines 1528-1540) which fans out READ-only `list_issues` calls — no writes. So within ONE `qrspi-batch` invocation, exactly one writer touches a ticket's state at a time. **Paths where the invariant does NOT hold:**
1. **Concurrent batch runs.** Nothing prevents two `qrspi-batch` (or a `qrspi-batch` + a `/qrspi-work` for the same ticket, or a `/review-*`) from running simultaneously — there is NO lock file, NO PID guard, NO mutex anywhere (grep for lock/flock/mutex found nothing relevant). Two concurrent runs would both write the same `<ticket>.events.jsonl`. CLAUDE.md and project memory ("dependent-tickets-need-blocker-edge") confirm "concurrent batch runs produce divergent conflicting designs" is a real failure mode.
2. **A shared `cli.log` sink.** If the design adds a single shared `cli.log` (not per-ticket), EVERY ticket in a run writes it interleaved — the per-ticket sequencing does NOT serialize a cross-ticket shared file beyond the fact that the main loop is itself sequential (so within ONE run it is still single-threaded, but across concurrent runs it is not).
3. **The single-ticket scope path** (`input.ticket`, lines 1434-1463) runs ONE ticket but offers no exclusion against a parallel sweep touching the same ticket.

**Evidence:**

```js
// Sequential: tickets share one .git index, so worktree/Graphite ops must not race.
const results = []
const processed = new Set()
for (let i = 0; i < tickets.length; i++) {
  const t = tickets[i]
  ...
}
```

— `.claude/workflows/qrspi-batch.js:1606-1611`

**Dependencies:** the `for` loop (single-threaded JS); `parallel()` used ONLY for read-only Query (line 1528). No locking primitive exists.

**Implicit contracts:** Single-writer holds WITHIN one run by construction (sequential loop). It does NOT hold across concurrent invocations — there is no inter-process lock. A per-ticket `.events.jsonl` confines damage to one ticket under concurrency; a shared `cli.log` does not. Append-mode writes (`open(path,"a")`, like qrspi_metrics_append) are the existing pattern and are atomic for small writes on POSIX but offer no cross-process ordering guarantee.

## Q14: What is the established pattern for unit-testing pure logic with an injected clock or injected failure, and how do the existing `scripts/*_test.py` siblings structure such tests?

**Answer:** The established pattern (all stdlib `unittest`, run as `python3 scripts/<name>_test.py`, no pytest):
- **Pure-function tests** call the pure helper with in-memory args and assert on the return — e.g. `qrspi_config_test` exercises `select_value` with literal dicts; `qrspi_metrics_append_test.WrapEnvelopeTest` calls `wrap_envelope(record, ticket, timestamp, run_id)` with a literal timestamp string and asserts the injected fields (lines 38-62). **Time is injected as a plain function argument, not read from a clock** — `wrap_envelope` takes `timestamp`/`run_id` as parameters (qrspi_metrics_append.py:67), and only the CLI `main` calls `datetime.now(timezone.utc).isoformat()` (line 133). This is the canonical injectable-clock pattern: keep `datetime.now()` in the impure CLI, pass the timestamp into the pure helper.
- **Filesystem tests** use `tempfile.TemporaryDirectory()` in `setUp` and monkeypatch `qrspi_paths.resolve_repo_root = lambda *a, **k: self.root` (qrspi_metrics_append_test.py:67-72), restoring it in `tearDown` (lines 74-75). This is how `qrspi_persist_test`, `qrspi_metrics_append_test`, etc. test the move/append against real temp dirs without touching the repo.
- **Injected failure** is done by direct attribute monkeypatch (assign a stub onto the module's function then restore) — the same mechanism as the `resolve_repo_root` swap. There is no `unittest.mock` heavyweight pattern in evidence; the convention is plain attribute reassignment with `tearDown` restore.
- `scripts/run_tests.py` discovers every `scripts/*_test.py` (`discover_tests`, lines 36-48), runs each as a subprocess (`run_one`, lines 51-75), and aggregates PASS/FAIL (`run_suite`). CI gates on it (`.github/workflows/tests.yml`).

**Evidence:**

```python
def setUp(self):
    self.tmp = tempfile.TemporaryDirectory()
    self.root = self.tmp.name
    self._orig = qrspi_paths.resolve_repo_root
    qrspi_paths.resolve_repo_root = lambda *args, **kw: self.root
def tearDown(self):
    qrspi_paths.resolve_repo_root = self._orig
```

— `scripts/qrspi_metrics_append_test.py:66-75`

```python
line = a.wrap_envelope(SAMPLE_RECORD, "RUS-77", "2026-06-15T00:00:00+00:00", "run-A")
self.assertEqual(line["timestamp"], "2026-06-15T00:00:00+00:00")
```

— `scripts/qrspi_metrics_append_test.py:39-42` (clock injected as a literal arg)

**Dependencies:** `unittest`, `tempfile`, `json`, `os` (stdlib only). `run_tests.py` is the aggregating runner; `run_tests_test.py` tests the runner itself.

**Implicit contracts:** Pure logic takes its time/randomness/failure source as a PARAMETER so the test passes a fixed value; only the thin CLI `main` calls `datetime.now()`. Tests must exit non-zero on failure (the subprocess convention) and be importable (guard real execution under `if __name__ == "__main__":`). To test backoff timing, pass `committedDate`/`now` as arguments to a pure function; to test fail-open writes, monkeypatch `open`/`os.makedirs` to raise and assert the helper returns success-anyway.

## Q15: What logging, status reporting, or telemetry does the pipeline emit today, and how are write/`flush`/`fsync` failures currently surfaced or swallowed, so the new fail-open emitter mirrors the established best-effort precedent?

**Answer:** Today's telemetry is three things, none of them a structured event log:
1. **`log()` run-log lines** — the harness-injected `log()` global, called throughout qrspi-batch.js (e.g. lines 1586, 1612, 1642, 1670). Human-readable progress; no structured fields, no file the design controls.
2. **The Linear best-effort projection** — the canonical "swallow on failure" precedent. After every phase the finalize worker calls `mcp__linear__save_issue` to set status, and the rule is explicit: "if the Linear write fails, print a one-line warning (`WARN: Linear projection to <state> failed: <error>`) and **continue** — never hard-stop or roll back git/PR work because of a Linear write" (SKILL.md:506-510). In qrspi-batch.js this is encoded in every finalize prompt as "BEST-EFFORT project Linear → … (a failed Linear write is a WARN, not a failure — still return ok:true)" (e.g. lines 718, 756, 846). This is the FAIL-OPEN precedent the new emitter should mirror.
3. **The critic-metrics ledger** (`qrspi_metrics_append.py`) — a JSONL append sink that is **fail-CLOSED** (verifies non-empty, returns `ok:false`/exit 1 on failure, lines 91-99) and is NOT wired into the live autonomous batch (the batch runs no critics).

**`flush`/`fsync`: NOT FOUND.** grep for `flush`/`fsync` in `scripts/` and `.claude/` returned nothing — no script calls `fh.flush()` or `os.fsync()`. Writes rely on the `with open(...)` context manager's close-on-exit. So there is NO existing flush/fsync-failure handling to mirror; the closest "swallow" precedent is the READ-side best-effort (`qrspi_config.read_config` catches `OSError`/`ValueError` → `{}`, lines 51-56) and the Linear WARN-and-continue rule. A fail-open emitter would DEPART from the persist/append fail-closed precedent and instead follow the Linear/read-side best-effort precedent: wrap the write (`makedirs`+`open`+write+optional `flush`/`fsync`) in try/except, emit a WARN, and return success so a logging failure never blocks pipeline work.

**Evidence:**

```
**Best-effort rule:** if the Linear write fails, print a one-line warning
(`WARN: Linear projection to <state> failed: <error>`) and **continue** — never hard-stop
or roll back git/PR work because of a Linear write.
```

— `.claude/skills/qrspi-work/SKILL.md:506-508`

```js
3. BEST-EFFORT project Linear → "Design Review" (a failed Linear write is a WARN, not a failure — still return ok:true with the PR created).
```

— `.claude/workflows/qrspi-batch.js:718` (and 756, 846, 877, 1007)

**Dependencies:** `log()` (harness global); `mcp__linear__save_issue` (Linear projection); `qrspi_metrics_append.py` (fail-closed ledger, not live). `read_config` (read-side best-effort).

**Implicit contracts:** Best-effort = "WARN and continue, never block real work". The Linear/read precedent SWALLOWS failure; the persist/metrics precedent FAIL-CLOSES. The two are mutually exclusive design stances — a fail-OPEN event emitter must follow the Linear precedent (swallow + WARN + return ok), NOT the persist precedent (verify + ok:false). No flush/fsync code exists to copy; durability semantics for the event log would be net-new.

---

## Discovered Patterns

- **Functional Core / Imperative Shell.** Every `scripts/qrspi_*.py` splits PURE helpers (unit-tested, take all inputs as args including time) from a thin impure CLI `main` (does I/O, calls `datetime.now()`, runs subprocesses). `docs/testing-dynamic-workflows.md` names this explicitly. The JS workflow is the un-unit-testable imperative shell.
- **The "self-locating script + verbatim worker + parse envelope" triad.** Every python-side capability is a self-locating script (`__file__`-derived or `qrspi_paths.resolve_repo_root`), invoked by a worker `agent()` told to "Run EXACTLY this one command verbatim" and "Output that JSON as your FINAL message", parsed in JS by a dedicated `parseXEnvelope` over `extractJsonObject`. A new logger must fit this triad to be callable from JS.
- **Single JSON envelope contract.** Stdout = exactly one `{ ok, ..., error? }` object; exit code mirrors `ok`. `extractJsonObject` grabs the outermost balanced object, tolerating surrounding prose but NOT a second/earlier JSON object.
- **Token-free staging to avoid `qrspi`-path mangling.** Phase agents write to `/tmp/phase-stage/<id>/<name>.md` (the `stg()`/`STAGE_ROOT` convention) because the weak worker model corrupts `qrspi` in long paths; the canonical qrspi-laden path is computed ONLY inside the script. Any worker that must reference a `.qrspi/observability/` path should let the script own that path, not have the model type it.
- **Two best-effort stances coexist.** READ-side and Linear writes SWALLOW failure (best-effort); persist/metrics WRITES fail-CLOSED (verify + ok:false). The codebase has both — a new emitter must pick one deliberately.
- **`engineCmd` (runner cwd) vs `engineCmdFor(r, ...)` (worker/worktree cwd).** Worker prompts running inside a worktree MUST use `engineCmdFor(r, rel)` (root derived from `r.worktreeDir`), never `engineCmd` (whose `.` fallback re-resolves against the worktree) — a documented bug class.
- **Sequential-by-design concurrency.** All per-ticket and nested loops are sequential with the comment "tickets share one .git index … must not race". The only `parallel()` is read-only Query.

## Inconsistencies

- **No `runId` in the live orchestrator.** The questions assume `runId` is obtainable "at the point where a phase fires", but qrspi-batch.js has NO `runId` (Q2). The only producer is `qrspi_metrics_append.py --run-id`, fed by a caller that is NOT the autonomous batch. Project memory ("qrspi-batch-runid-datenow-bug") records a prior attempt to mint a runId with the forbidden `Date.now()`/`Math.random()`. A `runId` must be minted somewhere new, respecting the workflow determinism rules.
- **No span/trace concept (Q3).** The questions presuppose a held `span_id` / `parent_span_id` across nested calls; none exists. Nesting is plain JS call structure; the only correlation handle is the `label` string (`<action>:<ticket>#<index>`).
- **`committedDate` is never gathered (Q6).** The backoff formula needs the frontier head-commit timestamp, but the GraphQL `PR_QUERY` does not request `committedDate`/`authoredDate`, and no field surfaces it. It must be added to the query and threaded through.
- **`ciReviseAttempt` is computed but not re-emitted (Q6/Q9).** The resolver consumes it internally (cap check) but `qrspi_resolve.build_envelope` does NOT surface it at the envelope top level (unlike `ciFailing`/`ciFailingChecks`/`ciRedBranches`, which DO have re-emit helpers). A backoff consumer in JS would need a new re-emit helper.
- **Config reader cannot read nested blocks (Q4).** The proposed `observability.*` block cannot be read by the current single-flat-key `qrspi_config.py`, and the JS `parseConfigEnvelope` outright rejects non-string (object) values. The `.qrspi/config.example.json` has no `observability` block. Reading it is net-new work (nested-key support or a whole-object read + sub-parse).
- **No `flush`/`fsync` anywhere (Q15).** Durability is left to `with open(...)` close. There is no existing flush/fsync-failure precedent to mirror; the design must define those semantics fresh.
- **`.qrspi/observability/` does not exist and survives cleanup only ABOVE `.worktrees/` (Q8/Q11).** No such directory, no `events.schema.json`. `git worktree remove --force` destroys a worktree's own `.qrspi/<id>/`; a survive-teardown log must live in the MAIN checkout root's `.qrspi/observability/` (a level above `.worktrees/`), which cleanup never touches.
- **`observability`-term hits in `.qrspi/RUS-*/*.md` are prior-artifact noise**, not infrastructure — they are research/design/questions docs (including RUS-86's own `questions.md`) that mention the word; no code or config implements it.
