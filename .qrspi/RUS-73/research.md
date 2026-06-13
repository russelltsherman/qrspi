# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

All paths are relative to the worktree root `/workspaces/qrspi/.worktrees/RUS-73`.

## Q1: How does the Query phase currently transform resolved project scope into the `tickets` array — what is the exact sequence from scope resolution through `mcp__linear__list_issues`, dedup, and ordering, and where in that sequence would a single-ticket short-circuit have to be inserted?

**Answer:** The Query phase is a single linear stretch in `.claude/workflows/qrspi-batch.js` starting at `phase('Query')` (line 1917). The exact sequence is:

1. **Resolve scope** (1919–1955): compute `PROJECT` (or leave undefined when `ALL_PROJECTS`).
2. **Log scope** (1957): `log(\`Project scope: ...\`)`.
3. **Fail-loud project validation** (1959–1988): for a concrete scope, spawn a validator agent (`mcp__linear__list_projects`) and `throw` if no exact name match.
4. **Sweep** (1990–2002): `parallel()` over `STATUSES`, each spawning a `mcp__linear__list_issues` agent (`assignee:"me"`, `project:"${PROJECT}"` unless `ALL_PROJECTS`) validated against `TICKETS_SCHEMA`.
5. **Flatten + dedup** (2004–2013): a `seen` Set keyed on `t.id` builds `tickets`.
6. **Order** (2024–2045): if `tickets.length > 1`, spawn the `qrspi_order_tickets.py` worker and reassign `tickets` to the sorted permutation (order-only; falls back to deduped order if parse fails).
7. **Found log + empty short-circuit** (2047–2053): logs the queue; `if (tickets.length === 0)` returns early (optionally running reconciliation).
8. **Per-ticket loop** (2056–2123).

A single-ticket short-circuit would naturally insert **after `phase('Query')` (1917) and before / in place of the scope-resolution + sweep block**: when `input.ticket` is present, build a one-element `tickets` array via `mcp__linear__get_issue` and skip the scope-resolve (1919–1955), project-validation (1959–1988), sweep (1990–2002), and ordering (2024–2045) blocks, then fall into the existing empty-check (2048) and per-ticket loop (2056) unchanged.

**Evidence:**

```javascript
const batches = await parallel(
  STATUSES.map(status => () =>
    agent(
      `Use mcp__linear__list_issues with:
- state: "${status}"
- assignee: "me"
- limit: 250${ALL_PROJECTS ? '\n(do not pass a project argument — include every project)' : `\n- project: "${PROJECT}"`}
...`,
      { label: `list:${status.toLowerCase().replace(/\s+/g, '-')}`, phase: 'Query', schema: TICKETS_SCHEMA }
    )))
const seen = new Set()
let tickets = []
for (const b of batches) {
  if (!b) continue
  for (const t of b.tickets) {
    if (seen.has(t.id)) continue
    seen.add(t.id); tickets.push(t)
  }
}
```

— `.claude/workflows/qrspi-batch.js:1990-2013`
**Dependencies:** Upstream: `STATUSES` (1132), `ALL_PROJECTS`/`PROJECT_ARG` (134–139), `PROJECT` (1927), `TICKETS_SCHEMA` (151), `parseConfigEnvelope` (316). Downstream: `tickets` feeds the order worker (2024) and the per-ticket loop (2059). `mcp__linear__list_issues` (sweep), `mcp__linear__list_projects` (validate), `qrspi_order_tickets.py` (sort).
**Implicit contracts:** `tickets` is a `let` reassigned by ordering (2044) — a short-circuit must produce the same `let tickets` shape. The empty short-circuit at 2048 and the loop at 2059 are the only two consumers; both key only on `t.id`, `t.title`, `t.status`, `t.createdAt`. The loop is *sequential* (comment 2055: tickets share one `.git` index).

## Q2: What `{id,title,status,createdAt}` fields does the existing sweep attach to each element of the `tickets` array, and does `mcp__linear__get_issue` return those same fields in the same shape so a single-fetch element is byte-compatible with a swept one?

**Answer:** The sweep attaches exactly four string fields per ticket, enforced by `TICKETS_SCHEMA`: `id` (e.g. `"RUS-8"`), `title`, `status` (the queried status name, e.g. `"Selected"`), `createdAt` (ISO-8601 creation timestamp). The schema marks all four `required` and typed `string`. The sweep agent prompt (1998) instructs the worker to return `{ id, title, status, createdAt }` with `status` pinned to the queried `${status}` value.

`mcp__linear__get_issue` is already used by the RESOLVE worker (1228) but only to read *status name*, *assignee non-null*, and *blockedBy relations* — it does **not** currently extract `{id,title,status,createdAt}` as a record. Whether `get_issue` returns a `createdAt` field in the same shape is **NOT FOUND in the codebase** (it is an MCP-server response shape, external to this repo; I cannot read the MCP schema under `REPO_ROOT`). What the code *requires* is byte-compatibility only at the four-field `TICKETS_SCHEMA` level: a single-fetch element must populate `id`, `title`, `status` (a status *name* string, which `list_issues` pins to the queried status but `get_issue` would carry as the issue's live status name), and `createdAt`. The orchestrator never validates a single-fetch element against `TICKETS_SCHEMA` today — that schema is only attached to the `parallel`/`list_issues` agents (1999).

**Evidence:**

```javascript
const TICKETS_SCHEMA = {
  type: 'object', required: ['tickets'],
  properties: { tickets: { type: 'array', items: { type: 'object',
    required: ['id', 'title', 'status', 'createdAt'],
    properties: { id: {type:'string'}, title: {type:'string'},
                  status: {type:'string'}, createdAt: {type:'string'} } } } } }
```

— `.claude/workflows/qrspi-batch.js:151-169`
**Dependencies:** `TICKETS_SCHEMA` consumed only by the sweep agents (1999). Downstream consumers of each element: the order worker envelope `{tickets, statuses}` (2025) and `qrspi_order_tickets.py` (`created_at_key` reads `createdAt`/`id`; `sort_tickets` reads `status`); the loop reads `t.id`, `t.title`, `t.status` (2061) and passes `t` to `resolveTicket(t)` which uses only `t.id` (1219, 1228).
**Implicit contracts:** `status` must be a Linear status *name* (`"Selected"`, `"Design Review"`, ...) for the order worker's status grouping (qrspi_order_tickets.py `sort_tickets`, line 100) and the `[i/total]` log to read sensibly. `createdAt` may be absent/unparseable — the order helper tolerates it (sorts such tickets last, `_parse_created_at` returns None, line 47–68) — so a single-fetch element missing `createdAt` would still sort, just last. `resolveTicket` re-fetches the issue itself via `get_issue` (1228), so the loop does NOT trust the array's `status` for the entry gate — it re-reads live status from Linear.

## Q3: What is the current `--- args ---` header block and the `meta` Query-phase `detail` string in `.claude/workflows/qrspi-batch.js`, and how are existing args (`allProjects`, `project`) declared and read there?

**Answer:** The `meta` object (lines 1–15) has a `phases` array; the Query phase `detail` (line 6) is:
`'List assigned Selected + in-flight (Design/Plan/Code Review) tickets, scoped to the mapped Linear project (input.allProjects > input.project > config linearProject > "QRSPI")'`.

The `--- args ---` header is a comment block at lines 109–147. It documents the optional override object `{ statuses?, project?, allProjects?, reconcile?, reconcileDryRun? }` (110–112) and the RUS-66 PROJECT SCOPE precedence (114–125). Args are parsed once: `input` (126–128) is `JSON.parse(args)` when `args` is a string else `args`. Each arg is then read into a module constant:

- `STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']` (132)
- `ALL_PROJECTS = input?.allProjects === true` (134)
- `PROJECT_ARG = (typeof input?.project === 'string' && input.project.trim() !== '') ? input.project.trim() : undefined` (137–139)
- `RECONCILE`, `RECONCILE_DRY_RUN` (146–147)

**Evidence:**

```javascript
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
const ALL_PROJECTS = input?.allProjects === true
const PROJECT_ARG = (typeof input?.project === 'string' && input.project.trim() !== '')
  ? input.project.trim() : undefined
```

— `.claude/workflows/qrspi-batch.js:126-139`
**Dependencies:** `input` derived from the runtime `args` global. `meta` (1–15) is read by the Workflow tool registry. A new `input.ticket` arg follows the same pattern: a `const TICKET_ARG = ...` near 139, documented in the 109–147 header and the line-6 detail.
**Implicit contracts:** Every arg is normalized to a constant at top-of-file before `phase('Query')`. `project` is trimmed and blank→undefined; `allProjects` is strictly `=== true` (any other value is false). A new ticket arg should mirror the trim/normalize discipline (e.g. `RUS-73` id validation).

## Q4: How does the workflow currently read `input.project` and `input.allProjects`, and where is the precedence chain (`input.allProjects` > `input.project` > config `linearProject` > `"QRSPI"`) implemented?

**Answer:** Reading happens at the arg-constant layer (134, 137–139, Q3). The precedence chain is implemented in the Query phase at lines 1927–1955:

1. `if (!ALL_PROJECTS)` — when `allProjects` is the explicit opt-in, `PROJECT` stays `undefined` (all projects). (1928)
2. else `if (PROJECT_ARG !== undefined) PROJECT = PROJECT_ARG` — concrete project from the arg. (1929–1930)
3. else spawn the CONFIG worker running `python3 scripts/qrspi_config.py --key linearProject`, parse via `parseConfigEnvelope`, and set `PROJECT = cfg.value`. (1932–1953)
4. `qrspi_config.py` itself applies the `"QRSPI"` default via `DEFAULTS = {"linearProject": "QRSPI"}` and `select_value` (config.py 33, 36–42).

A non-ok config read is a HARD FAILURE — `throw new Error(...)` (1951), never a silent fall-through.

**Evidence:**

```javascript
let PROJECT // undefined when ALL_PROJECTS
if (!ALL_PROJECTS) {
  if (PROJECT_ARG !== undefined) { PROJECT = PROJECT_ARG }
  else {
    const cfgOut = await agent(`... python3 ${engineCmd('scripts/qrspi_config.py')} --key linearProject ...`, ...)
    const cfg = parseConfigEnvelope(cfgOut, 'linearProject')
    if (!cfg.ok) throw new Error(`qrspi-batch: could not resolve project scope from config — ${cfg.error ?? 'unknown error'}`)
    PROJECT = cfg.value
  }
}
```

— `.claude/workflows/qrspi-batch.js:1927-1955`
**Dependencies:** `qrspi_config.py` (the `"QRSPI"` default, single-top-level-key), `parseConfigEnvelope` (316–326, requires string `value`), `engineCmd` (76). The config-read agent is gated on `!ALL_PROJECTS && PROJECT_ARG === undefined`.
**Implicit contracts:** `PROJECT === undefined` is the sentinel for "all projects" — used at 1957, 1965, 1996. `qrspi_config.py` is single-top-level-key only (per project memory) — it cannot read a nested key. A new `input.ticket` precedence is *orthogonal*: ticket scope vs project scope is a different axis — ticket fetch-by-id bypasses project scope entirely (the ticket is fetched by id, not swept under a project).

## Q5: Where does the resolver enforce the entry gate (assigned + Selected) — does `resolveTicket`/`qrspi_resolve.py` apply that gate independently of how a ticket entered the `tickets` array, or does any gating rely on the sweep's assigned+status filter?

**Answer:** The entry gate is enforced **purely inside the resolver**, independent of how the ticket entered the array. The pure-logic gate lives in `qrspi_resolve_state.py::resolve` (142), step "1. Entry gate" (160–184): it requires `state.get("assigned") and state.get("linearStatus") == "Selected"` to emit `run_design`, else `entry_blocked`. Those state fields come from `build_state(... args.assigned, args.linear_status ...)` (resolve.py 386–388), which are **caller-supplied CLI flags** (`--assigned`, `--linear-status`) the RESOLVE worker reads *live* from `mcp__linear__get_issue` (batch.js 1228–1259), NOT from the swept array's `status` field.

So the sweep's `assignee:"me"` + status filter is merely a *candidate selector*; it does not gate. The resolver re-reads assignment + status from Linear per ticket and gates there. A single-ticket fetch-by-id therefore inherits the same gate automatically — the resolve worker re-fetches and the resolver re-decides regardless of entry path.

**Evidence:**

```python
if "design" not in existing and not (design_already_landed(state) and existing):
    if state.get("assigned") and state.get("linearStatus") == "Selected":
        if state.get("blockedOpen"): ... return decision("entry_blocked", ...)
        return decision("run_design", phase="design",
                        reason="Entry gate satisfied (assigned + Selected); no design branch yet.")
    return decision("entry_blocked",
                    reason="No design branch and ticket is not assigned+Selected; nothing begins.")
```

— `scripts/qrspi_resolve_state.py:170-184`
**Dependencies:** `build_state` consumes `args.assigned` / `args.linear_status` (resolve.py 386). The RESOLVE worker prompt instructs reading status + assignee from `get_issue` and appending `--assigned`/`--linear-status` flags (batch.js 1256–1259). `resolve()` reads Linear ONLY in step 1 (comment 160).
**Implicit contracts:** The orchestrator does NOT trust the array's `status` for gating — `resolveTicket` re-fetches. This means a single-ticket path that fetches a ticket in any status (even one outside `STATUSES`) is gated correctly: a non-Selected, unassigned ticket resolves to `entry_blocked` and is skipped (batch.js 2105–2108), not silently advanced.

## Q6: What is the structure of the per-ticket result envelope produced by the loop body (`resolveTicket -> ensureRestacked -> action dispatch -> finalize -> reconcile`), so a single-ticket run can produce the identical shape?

**Answer:** The loop (2059–2123) pushes one result object per ticket into `results`, and the workflow returns `{ ticketsProcessed: results.length, results, reconciliation }` (2129). Each result object has the canonical shape `{ ticketId, action, ... }`:

- Resolve failure: `{ ticketId, action: 'resolve_failed', summary }` (2071)
- Restack conflict: `{ ticketId, action: 'restack_conflict', summary }` (2086)
- `skip()`: `{ ticketId, action: <decision.action>, summary }` (601)
- Most action handlers go through `finalizeResult` returning `{ ticketId, action, newStatus, summary, prUrl }` (1831) or on failure `{ ticketId, action, summary }` (1829)
- `doReset`: `{ ticketId, action: 'reset', newStatus, summary }` (1561)
- `doRevise`: `{ ticketId, action: 'revise', summary, prUrl }` (1618)
- Thrown error: `{ ticketId, action: 'errored', summary }` (2121)

The minimal common shape every consumer relies on is `{ ticketId, action, summary }`, with optional `newStatus`/`prUrl`/`reconcileRetry`. A single-ticket run can wrap the same loop body and return `{ ticketsProcessed, results, reconciliation }`.

**Evidence:**

```javascript
function skip(t, decision, note) { return { ticketId: t.id, action: decision.action, summary: note } }
// finalizeResult tail:
return { ticketId: t.id, action, newStatus: fin.newStatus, summary: fin.summary, prUrl: fin.prUrl }
// workflow return:
return { ticketsProcessed: results.length, results, reconciliation }
```

— `.claude/workflows/qrspi-batch.js:600-601, 1831, 2129`
**Dependencies:** Loop calls `resolveTicket` (2068), `ensureRestacked` (2083), then dispatches on `r.decision.action` (2093–2109) to `doDesign`/`doPlan`/`doImplementation`/`doSubmit`/`doReset`/`doRevise`/`doLand`/`skip`. `processed` Set (2058) tracks reconciliation exclusions (2116). `reconciliation` from `runReconciliation(processed)` (2127, opt-in).
**Implicit contracts:** Every result carries `ticketId` + `action`; the final-line log (2117) reads `res.action`, optional `res.newStatus`, `res.reconcileRetry`. A `reconcileRetry:true` result is excluded from `processed` (2116). A single-ticket run that reuses this loop body inherits the shape verbatim. Per-ticket `try/catch` (2067–2122) guarantees one ticket's throw becomes an `errored` result, never aborting the batch — a single-ticket run's lone result would be that same object.

## Q7: What does the Query phase do when a concrete project scope matches no Linear project (the "abort / fail loud" behavior), and how would a single-ticket scope path interact with or bypass that abort?

**Answer:** After resolving a concrete `PROJECT` (non-`ALL_PROJECTS`), the Query phase validates it against the live Linear project list before sweeping (1965–1988): it spawns a PROJECT-SCOPE validator agent calling `mcp__linear__list_projects` for an *exact, case-sensitive* name match, parses `{exists:boolean}`, and if not matched `throw new Error(...)` naming the project and instructing the user to check config / pass `{"project":...}` / `{"allProjects":true}`. The scope `log()` (1957) fires *before* the validation so the resolved name is visible even on abort. All-projects skips validation (comment 1964).

A single-ticket path fetches a specific ticket by id and is **orthogonal to project scope** — it would not resolve `PROJECT`, validate it, or sweep, so it would naturally bypass the 1965–1988 abort. The fail-loud equivalent for a single-ticket path would be a *ticket-not-found* abort, not a project-mismatch abort.

**Evidence:**

```javascript
if (!ALL_PROJECTS) {
  const matchOut = await agent(`... Use mcp__linear__list_projects ... EXACTLY "${PROJECT}" ...
    { "exists": true } ... otherwise { "exists": false }`, { label: 'validate:project-scope', ... })
  let matched = false
  try { const raw = extractJsonObject(matchOut); if (raw) matched = JSON.parse(raw).exists === true } catch { matched = false }
  if (!matched) throw new Error(`qrspi-batch: resolved project scope "${PROJECT}" matches no Linear project — aborting rather than sweeping an empty set ...`)
}
```

— `.claude/workflows/qrspi-batch.js:1965-1988`
**Dependencies:** `mcp__linear__list_projects`, `extractJsonObject` (190), `PROJECT` (1927). Gated on `!ALL_PROJECTS`.
**Implicit contracts:** Fail-loud means a `throw` from the Query phase (uncaught — there is no try/catch around the Query scope block, unlike the per-ticket loop body 2067), aborting the whole run. A single-ticket path must decide its own fail-loud posture: a fetch-by-id returning no ticket should similarly `throw` (the scope-block convention) rather than silently producing an empty queue.

## Q8: How does `resolveTicket`/the resolver represent a `gated` outcome (`entry_blocked` vs `wait`), and what does the loop do with each so a single-ticket fetch-by-ID surfaces those rather than silently skipping?

**Answer:** Both `entry_blocked` and `wait` are legal `decision.action` values in `RESOLVE_ACTIONS` (batch.js 184–186) and `qrspi_resolve_state.ACTIONS` (state.py 69–72). The resolver emits:
- `entry_blocked` — not assigned+Selected and no design branch, OR satisfied gate but an open Linear blocker (state.py 178–184).
- `wait` — an active phase PR exists but is not autonomously actionable: awaiting review, or thread-only with no change request / no unaddressed comment (state.py 241–247, 285, 289; module docstring 28–33).

In the dispatch switch (2093–2109), **both** fall into the shared default arm together with the explicit `case 'wait':` / `case 'entry_blocked':` labels (2104–2108): they call `skip(t, r.decision, ...)` and `log` `skipped (${a})`. So they are *recorded* as a result (`{ticketId, action, summary}`), not silently dropped — they appear in `results` with their action and reason.

A single-ticket fetch-by-id surfaces these the same way: because `resolveTicket` re-fetches and re-decides (Q5), a fetched ticket that is e.g. unassigned resolves `entry_blocked`, dispatches to `skip`, and appears in `results` as `{action:'entry_blocked', summary:reason}` — visible, not silent.

**Evidence:**

```javascript
switch (a) {
  ...
  case 'wait':         // not-yet-approved (or thread-only PR awaiting reviewer): nothing to do
  case 'entry_blocked':
  default:
    res = skip(t, r.decision, `Skipped (${a}): ${r.decision.reason}`)
    log(`  ${t.id}: skipped (${a})`)
}
results.push(res)
```

— `.claude/workflows/qrspi-batch.js:2104-2110`
**Dependencies:** `resolve()` step 1 (state.py 160–184) for `entry_blocked`; steps 3/4 (state.py 241–289) for `wait`. `skip()` (601). `RESOLVE_ACTIONS` validation (parseResolveEnvelope 223–224) — an action outside the set becomes `ok:false`.
**Implicit contracts:** `skip()` preserves `decision.action` verbatim into the result, so `entry_blocked`/`wait` are distinguishable in `results`. The per-ticket log line (2117) and `[i/total]` framing make them visible in run output. A single-ticket run reusing this dispatch inherits the surfacing.

## Q9: When `input.ticket` is absent, what guarantees the sweep path runs byte-for-byte unchanged — is scope selection a single branch point, or are there multiple sites that would each need a guard to avoid altering existing behavior (AC5)?

**Answer:** Scope *mode* selection is currently a **single axis** (`ALL_PROJECTS` vs concrete `PROJECT`) resolved in one contiguous block (1919–1988), and the sweep itself is one `parallel()` call (1990–2002). There is no `input.ticket` today. To preserve the sweep byte-for-byte when `input.ticket` is absent, a single-ticket short-circuit needs **one** branch point — a top-of-Query `if (TICKET_ARG) { ...single fetch...; } else { ...existing scope-resolve + validate + sweep + order... }`. The existing scope/sweep/order code (1919–2045) is self-contained: it reads only `ALL_PROJECTS`, `PROJECT_ARG`, `STATUSES`, and writes only `PROJECT` and `tickets`. Nothing downstream of the order step (2047 onward: empty-check, loop, reconciliation) references scope at all — they read only `tickets`. So a single guard wrapping 1919–2045 leaves the sweep path untouched when `input.ticket` is unset.

The one caveat: the `parallel` sweep, scope-resolve, project-validate, and order are **four separate agent spawns** (1932, 1966, 1990, 2026) — but they are sequential statements inside the same block, so one enclosing `else` (or an early-`if` that returns/falls into the loop) guards all four at once; they do not each need individual guards.

**Evidence:**

```javascript
log(`Found ${tickets.length} ticket(s): ...`)
if (tickets.length === 0) { ... return { ticketsProcessed: 0, ... } }
// Sequential: tickets share one .git index ...
const results = []
const processed = new Set()
for (let i = 0; i < tickets.length; i++) { ... }   // reads only tickets
```

— `.claude/workflows/qrspi-batch.js:2047-2059`
**Dependencies:** The loop (2059) and empty-check (2048) depend ONLY on `tickets` — never on `PROJECT`/`ALL_PROJECTS`/`STATUSES`. Reconciliation (2051, 2127) is scope-independent.
**Implicit contracts:** `tickets` is the single hand-off boundary between scope-mode and the loop. AC5 (sweep unchanged) is satisfied by producing `tickets` identically in the absent-`input.ticket` branch. A short-circuit must NOT touch `STATUSES`, the empty-check, the loop, or reconciliation — only the `tickets`-construction stretch (1919–2045).

## Q10: What is the established pattern for a stdlib-only `_test.py` sibling under `scripts/qrspi_*_test.py` — how do existing tests structure pure-decision-logic verification?

**Answer:** Two stdlib-only conventions coexist:

1. **Assert/case-table** (`qrspi_resolve_state_test.py`): module docstring states "Stdlib-only, assert-based (no pytest)... Run with: python3 scripts/qrspi_resolve_state_test.py. Exits 0 if all pass, 1 on the first failure." (3–7). Builders `_phase`/`_impl`/`_slice`/`state` construct in-memory state dicts (14–47); a `case(name, st, expect)` helper appends to a `CASES` list (60–61); `run()` iterates, compares `resolve(st)[key]` to expected (340–364), prints `ok:`/`FAIL:`, returns 1 on any failure. Imports the pure function directly: `from qrspi_resolve_state import resolve` (11).

2. **unittest** (`qrspi_order_tickets_test.py`, `qrspi_config_test.py`): standard `unittest.TestCase` subclasses, `sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))` then `from qrspi_order_tickets import created_at_key, sort_tickets` (order test 14–16); in-memory dict builders (`_t`, 21); each AC mapped to a `test_*` method.

A scope-mode resolver test should mirror either — pure function imported directly, in-memory inputs, no I/O, no network. The order/config tests are the closest precedent for a *precedence/selection* pure function (`select_value`, `sort_tickets`).

**Evidence:**

```python
from qrspi_resolve_state import resolve
def case(name, st, expect): CASES.append((name, st, expect))
case("entry: assigned + Selected -> run_design",
     state(assigned=True, linear="Selected", phases={}),
     {"action": "run_design", "phase": "design"})
def run():
    failures = 0
    for name, st, expect in CASES:
        got = resolve(st)
        for key, want in expect.items(): ...
```

— `scripts/qrspi_resolve_state_test.py:11, 60-61, 73-75, 338-342`
**Dependencies:** Tests import the production module by name (sibling in `scripts/`). The resolver test has NO third-party imports (only `sys`); config/order tests use `unittest` + `tempfile`/`os` (stdlib).
**Implicit contracts:** "stdlib-only" + "run with `python3`" + "exit 0/1". Pure decision functions take in-memory dicts/lists, do no I/O. The CLAUDE.md convention: "All of the above have stdlib-only unit tests as `_test.py` siblings (`scripts/qrspi_*_test.py`, run with python3)."

## Q11: How was the RUS-66 `input.project`/`input.allProjects` precedence change verified — is there an existing scope-resolution unit test that isolates the precedence chain as testable pure logic?

**Answer:** There is **no JS-side or dedicated scope-precedence unit test** for the `ALL_PROJECTS > PROJECT_ARG > config > "QRSPI"` chain — that precedence lives inline in the JS Query phase (1927–1955), which the JS sandbox cannot unit-test (it delegates to worker agents). What WAS extracted as testable pure logic is the **config-read seam only**: `qrspi_config.py::select_value` (the `config[key] || default` selector) and `read_config`, verified by `scripts/qrspi_config_test.py` (`SelectValueTests`, `read_config` tempfile tests, 19–40). That covers precedence rung 3→4 (config value vs `"QRSPI"` default) but NOT rungs 1–2 (`allProjects` vs `project` vs config), which remain JS-inline and unverified by an automated test.

So the RUS-66 precedence chain is only *partially* isolated as pure logic: the `"QRSPI"` default and truthy-selection are unit-tested in `qrspi_config_test.py`; the `allProjects`/`project`/trim normalization (batch.js 134–139) has no test. A new scope-mode resolver (e.g. choosing single-ticket vs sweep vs project) that wants test coverage would have to *extract* the branch logic into a pure helper (Python, like `qrspi_config.py`/`qrspi_order_tickets.py`) to follow the established testable pattern, since inline JS is not unit-tested anywhere in this repo.

**Evidence:**

```python
def select_value(config: dict, key: str, default: str) -> str:
    """Pure selector: return config[key] when present and truthy, else default."""
    value = config.get(key)
    return value if value else default
```

— `scripts/qrspi_config.py:36-42`

```python
class SelectValueTests(unittest.TestCase):
    def test_key_present_and_truthy_returns_value(self):
        self.assertEqual(select_value({"linearProject": "Acme"}, "linearProject", "QRSPI"), "Acme")
    def test_key_absent_returns_default(self):
        self.assertEqual(select_value({}, "linearProject", "QRSPI"), "QRSPI")
```

— `scripts/qrspi_config_test.py:19-30`
**Dependencies:** `qrspi_config_test.py` → `qrspi_config.{read_config,select_value}`. No test imports the JS precedence.
**Implicit contracts:** Testable scope logic must live in a Python helper (the JS sandbox is untestable here). The repo's pattern for a new pure scope decision is "extract to `scripts/qrspi_*.py` + `_test.py` sibling, JS shells out via a worker agent" — exactly how `qrspi_config.py` and `qrspi_order_tickets.py` were built.

## Q12: How does the Query phase log/surface which scope mode was chosen and how many tickets entered the loop, so a single-ticket run is distinguishable from a sweep?

**Answer:** Two `log()` lines exist:
- **Scope mode** (1957): `log(\`Project scope: ${ALL_PROJECTS ? 'all projects (input.allProjects)' : \`"${PROJECT}"\`}\`)` — prints `all projects (input.allProjects)` or the concrete project name.
- **Queue size + contents** (2047): `log(\`Found ${tickets.length} ticket(s): ${tickets.map(t => \`${t.id} (${t.status})\`).join(', ') || '(none)'}\`)`.

Plus a per-iteration `log(\`[${i+1}/${tickets.length}] ${t.id} (${t.status}): ${t.title}\`)` (2061) and a per-ticket completion line (2117). `log` is a **workflow-runtime global** — it is *not* declared anywhere in qrspi-batch.js (confirmed: `grep -E "^(const|let|var|function) (log|phase)" ` returns nothing); the Workflow tool provides `log()`, `phase()`, `agent()`, `parallel()`. `phase('Query')` (1917) tags the run-output section.

A single-ticket run is distinguishable by adding a third scope-mode log variant (e.g. `Project scope: single ticket (input.ticket=RUS-73)`) parallel to the 1957 line, plus the existing `Found 1 ticket(s)` line, which already surfaces the count.

**Evidence:**

```javascript
log(`Project scope: ${ALL_PROJECTS ? 'all projects (input.allProjects)' : `"${PROJECT}"`}`)
...
log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
...
log(`[${i + 1}/${tickets.length}] ${t.id} (${t.status}): ${t.title}`)
```

— `.claude/workflows/qrspi-batch.js:1957, 2047, 2061`
**Dependencies:** `log`/`phase` are runtime-injected (not imported/declared). `ALL_PROJECTS`, `PROJECT`, `tickets` feed the strings.
**Implicit contracts:** Scope mode is logged ONCE before the sweep (1957) and the queue size ONCE after dedup/order (2047). A single-ticket mode should log its own scope line at the 1957 position so run output is self-describing. The `Found N ticket(s)` line is the count surface; `N=1` for a single-ticket run.

## Q13: Which user-facing surfaces document `qrspi-batch` scoping (the SKILL.md, the workflow `meta` detail / `--- args ---` block, and the `.claude/CLAUDE.md` batch-scoping note), and how is `input.project`/`input.allProjects` described in each?

**Answer:** Four surfaces document batch scoping; a `qrspi-batch/SKILL.md` does **NOT exist in this repo**:

1. **No `qrspi-batch` SKILL.md under `REPO_ROOT`.** `find` for a SKILL.md with `name: qrspi-batch` returns nothing; `.claude/skills/` has no `qrspi-batch/` dir (only qrspi-critic/design/feature/implement/plan/pr/questions/research/structure/ticket/work/worktree). The `qrspi-batch` skill is registered at runtime (it appears in the available-skills list) but its SKILL.md is **NOT FOUND — outside `REPO_ROOT`** (likely a plugin/global skill). The workflow file `.claude/workflows/qrspi-batch.js` is the in-repo definition.

2. **Workflow `meta` Query detail** (batch.js 6): `'... scoped to the mapped Linear project (input.allProjects > input.project > config linearProject > "QRSPI")'`.

3. **Workflow `--- args ---` header + PROJECT SCOPE comment** (batch.js 109–147): documents `{ project?, allProjects? }` (110–112) and the full 4-rung precedence with the "explicit opt-in" and "fail loud on non-match" semantics (114–125).

4. **`.claude/CLAUDE.md` batch-scoping note** (26–31): "`linearProject` scopes both ticket creation and `qrspi-batch` runs ... precedence `input.allProjects > input.project > config linearProject > QRSPI`. Pass `{"project":"..."}` to override ... `{"allProjects":true}` to restore the all-projects sweep ... A concrete scope that matches no Linear project aborts the run (fail loud) rather than sweeping empty."

5. **`README.md`** (60, 164): the Query-phase table row repeats the precedence; line 164 says `linearProject` scopes "which tickets `qrspi-batch` sweeps."

**Evidence:**

```
`linearProject` scopes **both** ticket creation **and** `qrspi-batch` runs: by default the
batch Query phase sweeps only the mapped project's assigned tickets (precedence
`input.allProjects` > `input.project` > config `linearProject` > `QRSPI`). Pass
`{"project":"..."}` to override for one run, or `{"allProjects":true}` to restore the
all-projects sweep ...
```

— `.claude/CLAUDE.md:26-31`
**Dependencies:** All four in-repo surfaces (meta detail, args header, CLAUDE.md note, README table+§Linear) restate the same precedence template. The `meta` block is consumed by the Workflow registry; CLAUDE.md/README are human docs.
**Implicit contracts:** The precedence string `input.allProjects > input.project > config linearProject > "QRSPI"` is duplicated verbatim across meta detail (6), header comment (116–123), CLAUDE.md (28), and README (60) — a new `input.ticket` entry must be added consistently to all four (plus README §Linear 164) to stay in sync. There is no single source of truth doc — these are parallel restatements (see Inconsistencies).

---

## Discovered Patterns

- **JS↔Python shell-out via worker agents.** The JS sandbox cannot run python/git/gh/Linear; every such mechanic is delegated to a worker `agent()` that runs ONE verbatim command and returns stdout as plain text, which the JS parses with a brace/bracket-scanning extractor + validator (`extractJsonObject` 190, `extractJsonArray` 231) then a typed parser (`parseResolveEnvelope` 212, `parseConfigEnvelope` 316, `parseRestackEnvelope` 269, `parseOrderedTickets` 254). A new single-ticket fetch could either reuse the existing `mcp__linear__get_issue` agent pattern (inline, like the sweep) or shell out to a helper.
- **Self-locating stdlib-only Python helpers.** `qrspi_config.py`, `qrspi_order_tickets.py`, `qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py` all derive their repo root from `__file__` (config.py 29) and are invoked via `engineCmd`/`engineCmdFor` so the engine path survives relocation (batch.js 76, 105). Each has a `_test.py` sibling.
- **Decision logic is centralized and re-derived per-ticket.** The resolver (`qrspi_resolve_state.resolve`) is the SINGLE source of truth for the action; the orchestrator never re-derives it in JS (comment batch.js 33–34). The entry gate re-reads Linear live per ticket, so candidate-selection (the sweep filter) and gating are fully decoupled — this is what makes a single-ticket entry path safe (Q5/Q8).
- **`tickets` is the sole scope→loop boundary.** Everything after the order step reads only `tickets` (an array of 4-field records); scope mode (`ALL_PROJECTS`/`PROJECT`) is never consulted downstream (Q9). This makes a single-branch short-circuit feasible without per-site guards.
- **Per-ticket isolation via try/catch.** The loop body is wrapped so one ticket's throw becomes an `errored` result, never aborting the run (2067–2122). Scope-phase throws (project-mismatch, config-fail) are deliberately UNGUARDED and abort the whole run (fail loud) — a different posture from the loop.
- **Args normalized to top-of-file constants** before `phase('Query')`: `STATUSES`/`ALL_PROJECTS`/`PROJECT_ARG`/`RECONCILE`/`RECONCILE_DRY_RUN` (132–147), each strictly typed (`=== true`, trim-or-undefined).

## Inconsistencies

- **No `qrspi-batch` SKILL.md in the repo, but the questions (Q13) and the available-skills list both reference one.** The skill is registered at runtime (appears in the skill list) yet has no SKILL.md under `REPO_ROOT` — it is out-of-scope to read. The in-repo definition is the workflow `.claude/workflows/qrspi-batch.js` only. A doc-update task targeting "the qrspi-batch SKILL.md" would find no such file here.
- **The scoping precedence string is duplicated across 4–5 surfaces with no single source of truth:** meta detail (batch.js:6), args header comment (batch.js:116–123), `.claude/CLAUDE.md:28`, `README.md:60`, and `README.md:164`. They are currently consistent, but adding `input.ticket` requires editing all of them in lockstep — a drift risk.
- **RUS-66 precedence is only partially unit-tested.** The config rung (`select_value`/`read_config`) has tests (`qrspi_config_test.py`), but the `allProjects`/`project`/trim-normalization branch (batch.js 134–139, 1927–1955) is JS-inline and has NO automated test (Q11). Comments claim the chain is verified, but only its config tail is.
- **Code vs comment on `get_issue` field coverage (Q2).** The RESOLVE worker prompt (batch.js 1228) uses `get_issue` for status/assignee/blockers only and never reads `createdAt`/`title` as a record; the sweep schema (`TICKETS_SCHEMA`) requires all four. So `get_issue`'s ability to produce a byte-compatible 4-field element is unproven in-repo (the MCP response shape is external/NOT FOUND under `REPO_ROOT`).
