# Questions — qrspi-batch: single-ticket scope (input.ticket)

**Ticket:** RUS-73
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Data Flow

- Q1: How does the Query phase currently transform resolved project scope into the `tickets` array — what is the exact sequence from scope resolution through `mcp__linear__list_issues`, dedup, and ordering, and where in that sequence would a single-ticket short-circuit have to be inserted?
  **Target:** the Query phase of `.claude/workflows/qrspi-batch.js` (above the per-ticket loop)
- Q2: What `{id,title,status,createdAt}` fields does the existing sweep attach to each element of the `tickets` array, and does `mcp__linear__get_issue` return those same fields in the same shape so a single-fetch element is byte-compatible with a swept one?
  **Target:** the module responsible for building ticket records in `.claude/workflows/qrspi-batch.js` and the `mcp__linear__get_issue` response

## API Surface

- Q3: What is the current `--- args ---` header block and the `meta` Query-phase `detail` string in `.claude/workflows/qrspi-batch.js`, and how are existing args (`allProjects`, `project`) declared and read there?
  **Target:** the `meta` / args declaration block of `.claude/workflows/qrspi-batch.js`
- Q4: How does the workflow currently read `input.project` and `input.allProjects` from the invocation args, and where is that precedence chain (`input.allProjects` > `input.project` > config `linearProject` > `"QRSPI"`) implemented today?
  **Target:** the scope-resolution code in the Query phase of `.claude/workflows/qrspi-batch.js`

## State Management

- Q5: Where does the resolver enforce the entry gate (assigned + Selected) — does `resolveTicket`/`scripts/qrspi_resolve.py` apply that gate independently of how a ticket entered the `tickets` array, or does any gating rely on the sweep's assigned+status filter?
  **Target:** `scripts/qrspi_resolve.py` and `scripts/qrspi_resolve_state.py`
- Q6: What is the structure of the per-ticket result envelope produced by the loop body (`resolveTicket -> ensureRestacked -> action dispatch -> finalize -> reconcile`), so a single-ticket run can produce the identical shape?
  **Target:** the per-ticket loop body (~lines 2059–2123) of `.claude/workflows/qrspi-batch.js`

## Edge Cases

- Q7: What does the Query phase currently do when a concrete project scope matches no Linear project (the documented "abort / fail loud" behavior), and how would a single-ticket scope path interact with or bypass that abort?
  **Target:** the scope-resolution / fail-loud code in the Query phase of `.claude/workflows/qrspi-batch.js`
- Q8: How does `resolveTicket`/the resolver currently represent a `gated` outcome (`entry_blocked` vs `wait`), and what does the loop do with each so a single-ticket fetch-by-ID surfaces those rather than silently skipping?
  **Target:** `scripts/qrspi_resolve_state.py` and the action-dispatch switch in `.claude/workflows/qrspi-batch.js`
- Q9: When `input.ticket` is absent, what guarantees the sweep path runs byte-for-byte unchanged — is scope selection a single branch point, or are there multiple sites that would each need a guard to avoid altering existing behavior (AC5)?
  **Target:** the Query phase scope-mode selection in `.claude/workflows/qrspi-batch.js`

## Testing

- Q10: What is the established pattern for a stdlib-only `_test.py` sibling under `scripts/qrspi_*_test.py` — how do existing tests (e.g. for the resolver) structure pure-decision-logic verification that a scope-mode resolver should follow?
  **Target:** existing `scripts/qrspi_*_test.py` files (e.g. `scripts/qrspi_resolve_state_test.py`)
- Q11: How was the RUS-66 `input.project`/`input.allProjects` precedence change verified — is there an existing scope-resolution unit test or helper that already isolates the precedence chain as testable pure logic?
  **Target:** the scope-resolution helper and any associated `_test.py` in `scripts/` or `.claude/workflows/`

## Observability

- Q12: How does the Query phase currently log or surface which scope mode was chosen and how many tickets entered the loop, so a single-ticket run is distinguishable from a sweep in run output?
  **Target:** the logging/reporting code in the Query phase of `.claude/workflows/qrspi-batch.js`

## Documentation

- Q13: Which user-facing surfaces currently document `qrspi-batch` scoping (the `qrspi-batch` `SKILL.md`, the workflow `meta` detail string and `--- args ---` block, and the QRSPI batch-scoping note in `.claude/CLAUDE.md`), and how is `input.project`/`input.allProjects` described in each as a template for the new `input.ticket` entry?
  **Target:** the `qrspi-batch` `SKILL.md`, `.claude/workflows/qrspi-batch.js` meta/args, and `.claude/CLAUDE.md`
