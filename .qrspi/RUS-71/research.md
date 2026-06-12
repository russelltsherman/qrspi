# Research — Codebase Map

**Questions source:** questions.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

All evidence is from `.claude/workflows/qrspi-batch.js` in REPO_ROOT
`/workspaces/qrspi/.worktrees/RUS-71` (1046 lines total) unless noted.

## Q1: How does the `mcp__linear__list_issues` query in the Query phase currently shape its request — does it pass any `orderBy` or sort argument, and what fields per ticket does it request?

**Answer:** The Query phase fans out one `agent()` per status (via `parallel`) whose
prompt instructs the worker to call `mcp__linear__list_issues` with exactly four
arguments: `state`, `assignee: "me"`, `limit: 250`, and conditionally `project`.
**No `orderBy` / sort argument is passed.** Each agent is told to return every ticket
as `{ id, title, status }` and "Nothing else" — so `createdAt` is neither requested
from Linear nor returned to the script. Ordering is therefore whatever Linear's
`list_issues` returns by default (unspecified by this code).

**Evidence:**

```js
STATUSES.map(status => () =>
  agent(
    `Use mcp__linear__list_issues with:
- state: "${status}"
- assignee: "me"
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}

Return every ticket as { id, title, status } with id like "RUS-8" and status "${status}". Nothing else.`,
    { label: `list:${status.toLowerCase().replace(/\s+/g, '-')}`, phase: 'Query', schema: TICKETS_SCHEMA }
  )
)
```

— `.claude/workflows/qrspi-batch.js:944-956`
**Dependencies:** upstream → `mcp__linear__list_issues` (Linear MCP, external);
the prompt's requested fields are bounded by `TICKETS_SCHEMA` (Q2).
**Implicit contracts:** the worker must return only `id`/`title`/`status`; the prompt
explicitly forbids extra fields ("Nothing else"), so to obtain `createdAt` BOTH the
prompt text AND the schema would need to request/permit it. `id` is contracted to look
like `"RUS-8"`.

## Q2: What fields does `TICKETS_SCHEMA` declare for each ticket, and is `createdAt` already among them?

**Answer:** `TICKETS_SCHEMA` declares each ticket as an object with `required`
`['id', 'title', 'status']` and `properties` for exactly those three string fields.
**`createdAt` is NOT present** — neither required nor as an optional property. Note the
schema does not set `additionalProperties: false`, so an extra field a worker happened
to return would not be rejected by the schema; but the prompt ("Nothing else") tells the
worker not to include any.

**Evidence:**

```js
const TICKETS_SCHEMA = {
  type: 'object',
  required: ['tickets'],
  properties: {
    tickets: {
      type: 'array',
      items: {
        type: 'object',
        required: ['id', 'title', 'status'],
        properties: {
          id: { type: 'string' },
          title: { type: 'string' },
          status: { type: 'string' },
        },
      },
    },
  },
}
```

— `.claude/workflows/qrspi-batch.js:81-98`
**Dependencies:** consumed by the Query-phase `agent({ schema: TICKETS_SCHEMA })`
calls (Q1) as the StructuredOutput contract.
**Implicit contracts:** schema validation gates what the worker may return; adding
`createdAt` to the per-ticket consumed data requires adding it here (as a property,
and likely required) AND amending the prompt.

## Q3: How are tickets flattened from the per-status query results into the `tickets` array, and where in that flow would a sort be applied?

**Answer:** After `parallel(...)` resolves to `batches` (one result object per status,
each `{ tickets: [...] }`), a single loop flattens all batches into one flat `tickets`
array while deduplicating by `id` via a `seen` Set. The array is built in
batch-iteration order (i.e., `STATUSES` order, then per-batch return order) — **no sort
is applied anywhere.** The natural insertion point for a `createdAt` sort is immediately
after this flatten loop completes (after line 967) and before the `log("Found ...")` and
the sequential `for` processing loop at line 981 — sorting the assembled `tickets` array
in place. (Sorting per-batch before the dedup merge would NOT produce a global
`createdAt` order, since tickets are drawn from multiple status batches.)

**Evidence:**

```js
const seen = new Set()
const tickets = []
for (const b of batches) {
  if (!b) continue
  for (const t of b.tickets) {
    if (seen.has(t.id)) continue
    seen.add(t.id)
    tickets.push(t)
  }
}

log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
```

— `.claude/workflows/qrspi-batch.js:958-969`
**Dependencies:** upstream `batches` from `parallel`; downstream the `for (let i…)`
processing loop at line 981 consumes `tickets` in array order.
**Implicit contracts:** `b.tickets` is assumed iterable (a missing `tickets` key on a
non-null batch would throw at `for (const t of b.tickets)` — see Q8); processing order
== final array order, so a sort here directly changes processing order.

## Q4: What is the structure of each ticket object as returned by `mcp__linear__list_issues` (field names, value types)?

**Answer:** Within this script a ticket object `t` carries only `t.id`, `t.title`,
`t.status` — all strings — per `TICKETS_SCHEMA` and the prompt. The fields actually
read downstream are `t.id` (e.g. `"RUS-8"`), `t.status` (one of `STATUSES`), and
`t.title` (logged). **`createdAt` is not part of the object today** (not requested, not
in schema). The Linear API does expose a `createdAt` on issues, but its representation is
not visible in this codebase because the script never requests it; its on-wire shape
(an ISO-8601 string is the Linear convention) is an EXTERNAL contract, NOT FOUND in
REPO_ROOT — to be confirmed against the Linear MCP `list_issues` response.

**Evidence:**

```js
const t = tickets[i]
log(`[${i + 1}/${tickets.length}] ${t.id} (${t.status}): ${t.title}`)
```

— `.claude/workflows/qrspi-batch.js:982-983`
(Field set defined at `.claude/workflows/qrspi-batch.js:88-94`.)
**Dependencies:** `mcp__linear__list_issues` shape (external).
**Implicit contracts:** every consumer assumes `t.id`/`t.status`/`t.title` are present
strings; `t.id` matches `RUS-N`.

## Q5: Does the workflow script have any helper or comparator already used for sorting or ordering tickets that could be extended or referenced?

**Answer:** No ticket-object comparator exists. The only `.sort()` in the file is in the
reconciliation path, applied to an array of ticket-ID **strings** (lexicographic default
sort) after dedup — not to ticket objects and not by `createdAt`. There is no
`localeCompare`, no custom comparator function, and no shared ordering helper.

**Evidence:**

```js
return [...new Set(out.tickets.filter(id => typeof id === 'string' && valid.test(id)))].sort()
```

— `.claude/workflows/qrspi-batch.js:904`
**Dependencies:** none reusable for the main-queue ordering.
**Implicit contracts:** this `.sort()` operates on strings (ticket ids in the
reconciliation envelope), not on the `{id,title,status}` objects of the main queue, so
it is not directly reusable for a `createdAt` object sort.

## Q6: How is the `STATUSES` array defined and consumed to produce the phase grouping and across-phase order, so a within-group sort can be introduced without altering it?

**Answer:** `STATUSES` is a module-level const defaulting to
`['Selected', 'Design Review', 'Plan Review', 'Code Review']` (overridable via
`input.statuses`). It is consumed in three places: (a) `STATUSES.map(status => …)` builds
the parallel per-status query fan-out (Q1) — this is what produces the implicit
across-phase grouping, because tickets are merged into `tickets` in `STATUSES` order
during flatten; (b) the empty-queue note `STATUSES.join(' / ')` (lines 974); (c) not
otherwise. Because grouping/order today is purely a side effect of (a)+(the Q3 flatten
order), a global `createdAt` sort applied to the assembled `tickets` array (post-flatten)
would REORDER across these groups — there is no separate "within-group" structure to
preserve unless one re-groups by `status` first. `STATUSES` itself need not change to
introduce a sort.

**Evidence:**

```js
const STATUSES = input?.statuses ?? ['Selected', 'Design Review', 'Plan Review', 'Code Review']
```

— `.claude/workflows/qrspi-batch.js:68`

```js
const batches = await parallel(
  STATUSES.map(status => () =>
    agent( … )
  )
)
```

— `.claude/workflows/qrspi-batch.js:944-956`
**Dependencies:** drives the Query fan-out and the implicit grouping.
**Implicit contracts:** array order of `STATUSES` currently determines the de-facto
across-phase processing order; any sort decision must declare whether it overrides this
ordering globally or only orders within each status group.

## Q7: Where and how is cross-phase-group deduplication implemented, and at what point relative to flattening does it run?

**Answer:** Dedup is implemented inline during the flatten loop using a `seen` Set keyed
on `t.id`: the first occurrence of an id wins and subsequent occurrences across batches
are skipped. It runs DURING flattening (same loop), not as a separate pass — so a ticket
returned by two status batches is kept once, in the position of its first-seen batch
(`STATUSES` order). A `createdAt` sort applied AFTER this loop would operate on the
already-deduplicated array, which is the correct order of operations (dedup → sort).

**Evidence:**

```js
const seen = new Set()
const tickets = []
for (const b of batches) {
  if (!b) continue
  for (const t of b.tickets) {
    if (seen.has(t.id)) continue
    seen.add(t.id)
    tickets.push(t)
  }
}
```

— `.claude/workflows/qrspi-batch.js:958-967`
**Dependencies:** none external; pure JS.
**Implicit contracts:** `t.id` is the dedup key and is assumed a stable, present string;
"first batch wins" means the surviving ticket carries the `status` from its first-seen
batch (relevant if the same ticket legitimately appears under two statuses — unlikely but
not guarded).

## Q8: How does the current flattening/iteration code behave when a ticket field it reads is missing or unparseable — does any existing access throw rather than tolerate `undefined`?

**Answer:** The flatten loop guards only the batch object (`if (!b) continue`). It does
NOT guard `b.tickets`: `for (const t of b.tickets)` throws a TypeError if a non-null
batch lacks a `tickets` array (schema validation should prevent this, since
`TICKETS_SCHEMA` requires `tickets`). Per-ticket field reads (`t.id`, `t.title`,
`t.status`) are unguarded — if absent they evaluate to `undefined` and do NOT throw at
access; `seen.has(undefined)`/`seen.add(undefined)` are valid, and template-string
logging of `undefined` is harmless. So today's code tolerates `undefined` field VALUES
(no throw) but assumes the `tickets` array itself is present. A future `createdAt` sort
that does `new Date(t.createdAt)` or string compares on `t.createdAt` would silently
mis-order (or produce `NaN` comparisons) for any ticket missing `createdAt`, rather than
throw — so a tolerant comparator with an explicit fallback is required.

**Evidence:**

```js
for (const b of batches) {
  if (!b) continue
  for (const t of b.tickets) {
```

— `.claude/workflows/qrspi-batch.js:960-962`
**Dependencies:** relies on `TICKETS_SCHEMA` validation upstream to guarantee `tickets`.
**Implicit contracts:** schema-validated input is assumed; the code does no defensive
parsing of individual field values.

## Q9: When two tickets share an identical `createdAt`, what tie-breaking field (e.g. `id`) is available on the ticket object to produce a deterministic secondary order?

**Answer:** The only fields present on a ticket object are `id`, `title`, `status`. The
natural deterministic tie-break is `id` (the `"RUS-N"` identifier), which is the dedup
key and guaranteed present/unique. `title` is non-unique and unsuitable. NOTE: `id` is a
string with a numeric suffix; a lexicographic compare of `"RUS-7"` vs `"RUS-71"` does NOT
match numeric order — see Q10 — so a tie-break on `id` should compare the numeric suffix
(and is only safe within one team prefix). Within a single team prefix, numeric-suffix
order on `id` is a stable, deterministic tie-break.

**Evidence:**

```js
id: { type: 'string' },
title: { type: 'string' },
status: { type: 'string' },
```

— `.claude/workflows/qrspi-batch.js:91-93`
**Dependencies:** none.
**Implicit contracts:** `id` is unique (dedup relies on it) and matches `RUS-N`.

## Q10: Can the batch span multiple projects/teams, and where is that scope determined — confirming why numeric ID-suffix sorting is unsafe across teams?

**Answer:** Yes. `PROJECT = input?.project` and the comment states `undefined ⇒ all
projects`. When `PROJECT` is undefined the per-status query prompt explicitly instructs
the worker to "do not pass a project argument — include every project". So a default batch
run spans ALL projects the assignee has matching tickets in. Linear ids are
`<TEAM-PREFIX>-<number>`; the prompt hard-codes the example prefix `"RUS-"`, but nothing
in the script restricts results to a single team prefix when project/team is unscoped.
Therefore sorting by the numeric ID suffix alone is unsafe across teams: two different
teams can both have an issue numbered e.g. `42`, and the suffix says nothing about
creation order across teams. This is the codebase evidence that `createdAt` (a
team-independent absolute timestamp) is the correct cross-team ordering key, with `id`
only a within-prefix tie-break.

**Evidence:**

```js
const PROJECT = input?.project // undefined ⇒ all projects
```

— `.claude/workflows/qrspi-batch.js:69`

```js
- limit: 250${PROJECT ? `\n- project: "${PROJECT}"` : '\n(do not pass a project argument — include every project)'}
```

— `.claude/workflows/qrspi-batch.js:950`
**Dependencies:** `input.project` (caller-supplied override); Linear MCP scoping.
**Implicit contracts:** unscoped runs aggregate across projects/teams; `assignee:"me"`
is the only universal filter, so the queue can mix team prefixes.

## Q11: What pure-logic verification mechanism exists for the workflow script, given the repo convention that workflow scripts have no JS test harness, and how have prior comparators/logic in this file been verified?

**Answer:** There is NO JS test harness in the repo (no `*.test.js` / `*_test.js`
anywhere; confirmed by search). The documented convention (`.claude/CLAUDE.md`,
"Codebase conventions") is: pure logic is verified by Python stdlib unit tests written as
`scripts/qrspi_*_test.py` siblings (run with `python3`), and orchestration changes are
verified by manual end-to-end runs; the `evals/` + `scripts/run_eval.py` harness is an
explicit "non-functional placeholder". The 10 existing `_test.py` files cover the Python
helpers (resolver, pr_state, persist, restack, revise_amend, cleanup, comment_reply,
pr_body, clear_stale_pr, resolve) — NOT the JS workflow. Prior JS logic in
qrspi-batch.js (e.g. the dedup/flatten, `reviewerFlags`, envelope parsers) has no unit
test in-file; the decision logic it depends on is deliberately delegated to the
Python-tested `qrspi_resolve_state.py` rather than re-implemented in JS (see the "Why
this exists" header). Implication for a `createdAt` comparator: to follow the repo's
TDD convention, the comparator's pure logic would either need to be factored into a
Python helper with a `_test.py` sibling, or — if kept in JS — verified by reasoning +
manual e2e, since no JS test runner exists.

**Evidence:**

```text
scripts/qrspi_cleanup_test.py        scripts/qrspi_pr_state_test.py
scripts/qrspi_clear_stale_pr_test.py scripts/qrspi_resolve_state_test.py
scripts/qrspi_comment_reply_test.py  scripts/qrspi_resolve_test.py
scripts/qrspi_persist_test.py        scripts/qrspi_restack_test.py
scripts/qrspi_pr_body_test.py        scripts/qrspi_revise_amend_test.py
```

— `scripts/qrspi_*_test.py` (10 files; `find` returned no `*_test.js`)
Convention source: `.claude/CLAUDE.md` "Codebase conventions" (stdlib-only `_test.py`
siblings; `evals/` is a placeholder).
**Dependencies:** `python3`; no JS runner.
**Implicit contracts:** new pure logic ships with a Python `_test.py` sibling; JS
orchestration is verified by manual e2e.

## Q12: How is a single end-to-end batch run invoked manually for verification of ordering behavior?

**Answer:** The script is a Workflow-tool workflow (`export const meta = {...}` with a
`name: 'qrspi-batch'`), not a standalone Node/CLI entrypoint. It is invoked through
Claude Code's Workflow tool / the `/qrspi-batch` skill, not via `node qrspi-batch.js`.
It uses runtime-injected globals — `agent()`, `parallel()`, `phase()`, `log()`, and
`args` — that are NOT defined or imported anywhere in the file (confirmed: no
`function log`, `const log`, `require`, or `import` for them), so it cannot run under
plain Node. Optional run-shaping is via the `args`/`input` JSON override
(`{ statuses?, project?, reconcile?, reconcileDryRun? }`), parsed at lines 62-64. The
docs describe invoking it as "the `qrspi-batch` workflow" to drive assigned tickets one
step forward (`docs/qrspi_complete_guide.md:155`, `docs/qrspi_claude_code_guide.md:327`).
`run_loop.sh` is unrelated — it is an eval-loop driver for skills
(`run_loop.sh <skill_path> <eval_suite>`), not the batch entrypoint. So manual
verification of ordering = a real `/qrspi-batch` run, observing the `log()` order output
(Q13), against a live Linear queue.

**Evidence:**

```js
export const meta = {
  name: 'qrspi-batch',
  …
  phases: [
    { title: 'Query', detail: 'List assigned Selected + in-flight (Design/Plan/Code Review) tickets' },
    …
  ],
}
```

— `.claude/workflows/qrspi-batch.js:1-15`

```js
const input = typeof args === 'string'
  ? (() => { try { return JSON.parse(args) } catch { return undefined } })()
  : args
```

— `.claude/workflows/qrspi-batch.js:62-64`
**Dependencies:** Workflow-tool runtime (provides `agent/parallel/phase/log/args`);
Linear MCP; Python worker scripts.
**Implicit contracts:** the file is driven by the Workflow runner, not executed directly;
no JS-level harness can run it offline, so ordering is observable only via a live run.

## Q13: Does the batch workflow log or emit the ticket processing order anywhere, such that a reordering by `createdAt` would be visible in run output?

**Answer:** Yes, in two places. (1) Right after flatten, a summary line logs the full
queue in array order: `Found N ticket(s): RUS-a (status), RUS-b (status), …` — this maps
directly to processing order. (2) The sequential processing loop logs each ticket with a
`[i/total]` index and again on completion with the chosen action. So a `createdAt`
reorder of the `tickets` array would be DIRECTLY visible: both the "Found …" list and the
`[i/total]` progression would reflect the new order. `log()` is the runtime-provided
logging sink (not defined in-file).

**Evidence:**

```js
log(`Found ${tickets.length} ticket(s): ${tickets.map(t => `${t.id} (${t.status})`).join(', ') || '(none)'}`)
```

— `.claude/workflows/qrspi-batch.js:969`

```js
const t = tickets[i]
log(`[${i + 1}/${tickets.length}] ${t.id} (${t.status}): ${t.title}`)
…
log(`[${i + 1}/${tickets.length}] ${t.id} → ${res.action}${res.newStatus ? ` (${res.newStatus})` : ''}`)
```

— `.claude/workflows/qrspi-batch.js:982-983, 1034`
**Dependencies:** runtime `log()` sink.
**Implicit contracts:** the "Found …" line is built from `tickets` in array order, so it
faithfully mirrors whatever ordering the array holds at line 969 — the ideal observation
point for verifying a `createdAt` sort.

---

## Discovered Patterns

- **Runtime-injected globals.** `agent()`, `parallel()`, `phase()`, `log()`, and `args`
  are provided by the Workflow tool runtime; none are imported or defined in
  qrspi-batch.js. The script cannot run under plain Node, which is why there is no JS
  unit test and why verification is "Python `_test.py` for pure logic, manual e2e for
  orchestration" (`.claude/CLAUDE.md`).
- **Logic delegation to tested Python.** The script deliberately avoids re-implementing
  decision logic in JS, delegating to `scripts/qrspi_resolve_state.py` and friends (the
  "Why this exists" header, lines 17-58). Pure logic that needs tests tends to live in a
  Python helper with a `_test.py` sibling (10 such pairs exist).
- **StructuredOutput schemas gate worker returns.** `TICKETS_SCHEMA`
  (lines 81-98) is the contract for what the Query worker may return; the prompt text
  ("Nothing else") and the schema must agree. Adding a consumed field (e.g. `createdAt`)
  is a two-place change: prompt + schema.
- **Dedup-then-process, no sort.** Tickets are flattened+deduped by `id` (first-seen
  wins, `STATUSES` order) and then processed strictly in array order; there is currently
  no ordering step, so processing order is an emergent property of `STATUSES` order plus
  Linear's default return order.
- **`PROJECT` defaults to all-projects/all-teams**, so the queue can legitimately mix
  team prefixes — making any id-suffix-based ordering team-unsafe.

## Inconsistencies

- **Prompt requests `id` format `"RUS-8"` but scope is all-teams.** The Query prompt
  hard-codes the example id prefix `"RUS-"` (line 952) while `PROJECT` defaults to *all*
  projects (line 69) and the prompt elsewhere says "include every project" (line 950).
  If the assignee has tickets under another team prefix, the example is misleading and
  any prefix-assuming ordering would be wrong. (Code vs. its own comment/example.)
- **Schema lacks `additionalProperties:false`, but prompt says "Nothing else."** The two
  guard rails disagree in strictness: the schema would tolerate an extra field, while the
  prompt forbids it. Not a bug today, but it means "createdAt is absent" is enforced only
  by the prompt, not the schema.
- **`b.tickets` is unguarded while `b` is guarded.** Line 961 guards `if (!b) continue`
  but line 962 assumes `b.tickets` is iterable; a non-null batch without a `tickets`
  array would throw. The code relies entirely on `TICKETS_SCHEMA` validation to uphold
  this invariant — a defensive-vs-trusting inconsistency within the same loop.
- **The only `.sort()` (line 904) is a lexicographic string sort on ticket IDs** in the
  reconciliation path. It is unrelated to creation order and would mis-order numeric
  suffixes (`RUS-10` before `RUS-9`); it is not reusable as a precedent for a correct
  `createdAt` (or numeric-id) comparator.
