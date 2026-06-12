# Questions — qrspi-batch: deterministic within-phase ticket ordering by createdAt

**Ticket:** RUS-71
**Generated:** 2026-06-11T00:00:00Z
**Status:** answered

> Each question's **Answer** is the resolved finding from the Research phase
> (`research.md`, evidence cited there against `.claude/workflows/qrspi-batch.js`),
> integrated here so the design rests on visibly-answered questions.

## Data Flow

- Q1: How does the `mcp__linear__list_issues` query in the Query phase currently shape its request — does it pass any `orderBy` or sort argument, and what fields per ticket does it request?
  **Target:** the Query phase prompt in `.claude/workflows/qrspi-batch.js`
  **Answer:** The Query phase fans out one `agent()` per status (via `parallel`) whose prompt calls `mcp__linear__list_issues` with exactly four arguments — `state`, `assignee: "me"`, `limit: 250`, and conditionally `project` — passing **no `orderBy` / sort argument**. Each worker returns every ticket as `{ id, title, status }` and "Nothing else", so `createdAt` is neither requested nor returned. (`.claude/workflows/qrspi-batch.js:944-956`.)
- Q2: What fields does `TICKETS_SCHEMA` declare for each ticket, and is `createdAt` already among them?
  **Target:** the `TICKETS_SCHEMA` definition in `.claude/workflows/qrspi-batch.js`
  **Answer:** `TICKETS_SCHEMA` declares each ticket with `required ['id','title','status']` and properties for exactly those three string fields. **`createdAt` is NOT present** (neither required nor optional), and the schema does not set `additionalProperties: false`. (`.claude/workflows/qrspi-batch.js:81-98`.)
- Q3: How are tickets flattened from the per-status query results into the `tickets` array around lines 916-939, and where in that flow would a sort be applied?
  **Target:** the ticket-flattening logic in `.claude/workflows/qrspi-batch.js` (~lines 916-939)
  **Answer:** After `parallel(...)` resolves to `batches`, a single loop flattens all batches into one `tickets` array, deduping by `id` via a `seen` Set (first occurrence wins, in `STATUSES` order); **no sort is applied**. The correct insertion point for a `createdAt` sort is immediately after that flatten loop (after line 967) and before the `log("Found …")` at line 969. (`.claude/workflows/qrspi-batch.js:958-969`.)

## API Surface

- Q4: What is the structure of each ticket object as returned by `mcp__linear__list_issues` (field names, value types, especially the `createdAt` representation)?
  **Target:** the ticket-consuming code paths in `.claude/workflows/qrspi-batch.js`
  **Answer:** In-script a ticket `t` carries only `t.id`, `t.title`, `t.status`, all strings. **`createdAt` is not part of the object today.** Linear does expose `createdAt` on issues (ISO-8601 by convention), but its on-wire shape is an EXTERNAL contract, NOT FOUND in the repo — to be confirmed against a live `list_issues` response (drives OQ1). (`.claude/workflows/qrspi-batch.js:88-94, 982-983`.)
- Q5: Does the workflow script have any helper or comparator already used for sorting or ordering tickets that could be extended or referenced?
  **Target:** `.claude/workflows/qrspi-batch.js`
  **Answer:** No ticket-object comparator exists. The only `.sort()` in the file is a default lexicographic sort on ticket-**ID strings** in the reconciliation path (line 904) — not on ticket objects, not by `createdAt`, and it mis-orders numeric suffixes — so it is not reusable as a precedent.

## State Management

- Q6: How is the `STATUSES` array defined and consumed to produce the phase grouping and across-phase order (referenced at line 66), so a within-group sort can be introduced without altering it?
  **Target:** the `STATUSES` constant and its consumers in `.claude/workflows/qrspi-batch.js`
  **Answer:** `STATUSES` is a module-level const defaulting to `['Selected','Design Review','Plan Review','Code Review']` (line 68). It drives the `STATUSES.map(...)` parallel query fan-out, which produces the implicit across-phase grouping because tickets merge into `tickets` in `STATUSES` order during flatten. `STATUSES` need not change to introduce a sort; a global sort would reorder across these groups unless the array is re-grouped by `status` first.
- Q7: Where and how is cross-phase-group deduplication implemented (a ticket appearing in two status batches processed once), and at what point relative to flattening does it run?
  **Target:** the dedup logic in `.claude/workflows/qrspi-batch.js`
  **Answer:** Dedup is inline in the flatten loop via a `seen` Set keyed on `t.id` — first occurrence wins, subsequent cross-batch occurrences skipped (`STATUSES` order). It runs DURING flatten, so a `createdAt` sort applied AFTER the loop operates on the already-deduped array (correct order: flatten → dedup → sort). (`.claude/workflows/qrspi-batch.js:958-967`.)

## Edge Cases

- Q8: How does the current flattening/iteration code behave when a ticket field it reads is missing or unparseable — does any existing access throw rather than tolerate `undefined`?
  **Target:** the ticket-flattening/iteration logic in `.claude/workflows/qrspi-batch.js`
  **Answer:** The loop guards `if (!b) continue` but NOT `b.tickets` (a non-null batch lacking `tickets` would throw). Per-ticket field reads tolerate `undefined` without throwing. So a naive `new Date(t.createdAt)` sort would silently mis-order a missing `createdAt` rather than throw — a tolerant comparator with an explicit "missing/unparseable sorts last" fallback is required (AC5). (`.claude/workflows/qrspi-batch.js:960-962`.)
- Q9: When two tickets share an identical `createdAt`, what tie-breaking field (e.g. `id`) is available on the ticket object to produce a deterministic secondary order?
  **Target:** the ticket object fields consumed in `.claude/workflows/qrspi-batch.js`
  **Answer:** The only fields present are `id`, `title`, `status`. `id` (`"RUS-N"`, the dedup key, guaranteed present/unique) is the natural tie-break; `title` is non-unique and unsuitable. `id` must be compared by **numeric suffix** (lexicographic mis-orders `RUS-7` vs `RUS-71`) and is safe only within one team prefix.
- Q10: Can the batch span multiple projects/teams (e.g. `PROJECT` undefined ⇒ all projects), and where in the code is that scope determined — confirming why numeric ID-suffix sorting is unsafe across teams?
  **Target:** the project/team scoping logic in `.claude/workflows/qrspi-batch.js`
  **Answer:** Yes. `PROJECT = input?.project` and `undefined ⇒ all projects` (line 69); when unset the prompt instructs "include every project" (line 950), so a default run spans all teams the assignee has tickets in. Ids are `<TEAM>-<number>`, so an id-suffix sort is unsafe across teams (two teams can share number 42). `createdAt` (a team-independent absolute timestamp) is the correct cross-team key, with `id` only a within-prefix tie-break.

## Testing

- Q11: What pure-logic verification mechanism exists for the workflow script, given the repo convention that workflow scripts have no JS test harness, and how have prior comparators/logic in this file been verified?
  **Target:** the workflow script and `scripts/qrspi_*_test.py` siblings (per repo convention)
  **Answer:** There is NO JS test harness (no `*_test.js` anywhere). The convention is: pure logic ships as a `scripts/qrspi_*` Python helper with a `scripts/qrspi_*_test.py` stdlib sibling, and orchestration is verified by manual e2e; `evals/` is a non-functional placeholder. There are 12 such tested helper pairs today (resolver, pr_state, persist, restack, revise_amend, cleanup, comment_reply, pr_body, clear_stale_pr, resolve, …). This settles Decision 4 / OQ3 in favor of a tested Python comparator helper over inline JS.
- Q12: How is a single end-to-end batch run invoked manually for verification of ordering behavior?
  **Target:** the entrypoint/run path of `.claude/workflows/qrspi-batch.js`
  **Answer:** It is a Workflow-tool workflow (`export const meta = {...}`, `name: 'qrspi-batch'`), not a Node/CLI entrypoint — it uses runtime-injected globals (`agent`, `parallel`, `phase`, `log`, `args`) and cannot run under plain Node. Manual verification of ordering = a real `/qrspi-batch` run observing the `log()` output (Q13) against a live Linear queue; optional shaping via the `args`/`input` override.
- Q13: Does the batch workflow log or emit the ticket processing order (or per-ticket progress) anywhere, such that a reordering by `createdAt` would be visible in run output?
  **Target:** the logging/progress-reporting code in `.claude/workflows/qrspi-batch.js`
  **Answer:** Yes, in two places: (1) the post-flatten `Found N ticket(s): …` summary line (line 969) logs the queue in array order; (2) the sequential processing loop logs each ticket with a `[i/total]` index and again on completion (lines 982-983, 1034). A `createdAt` reorder of the `tickets` array is therefore directly observable in both.
