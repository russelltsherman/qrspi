# Structure Outline — qrspi-batch: deterministic within-phase ticket ordering by createdAt

**Design basis:** design.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft

## New Types

- `Ticket { id: string, title: string, status: string, createdAt: string }` — in-script
  ticket object, now extended with `createdAt` (was `{ id, title, status }`). Represented as
  a plain JS object in `qrspi-batch.js` and a plain dict in the Python helper; no class.

## Modified Types

- `TICKETS_SCHEMA` (~lines 81-98, `qrspi-batch.js`) — add `createdAt: { type: 'string' }` to
  the per-ticket `properties`, and add `'createdAt'` to the per-ticket `required` array
  (ref: design.md §Delta item 2; `createdAt` IS required — OQ2 RESOLVED).

## Contracts

- **Python helper (new):** `scripts/qrspi_order_tickets.py`
  - `sort_tickets(tickets: list[dict], statuses: list[str]) -> list[dict]` — group-then-sort:
    stable-partition `tickets` by `status` in `statuses` order, sort each partition by
    `createdAt` ascending with `id` numeric-suffix tie-break, concatenate (Decision 2 Option A).
  - `created_at_key(ticket: dict) -> tuple` — sort key: parsed `createdAt` ascending; absent or
    unparseable `createdAt` sorts LAST; numeric suffix of `id` as deterministic tie-break; never
    raises (Decision 3 Option A, AC5).
  - **CLI contract:** reads a JSON envelope `{ "tickets": [...], "statuses": [...] }` on stdin,
    writes the sorted `tickets` array as JSON to stdout. This is the JS↔Python boundary the
    workflow shells out across (same pattern as `qrspi_resolve.py` / `qrspi_persist.py` /
    `qrspi_pr_body.py`).
- **JS call site (modified):** immediately after the flatten/dedup loop (~after line 967,
  before `log("Found …")` at line 969) the workflow shells out to
  `scripts/qrspi_order_tickets.py`, passing the deduped `tickets` array and `STATUSES`, and
  replaces `tickets` with the helper's stdout. Order of operations: flatten → dedup → sort
  (Decision 1 Option A; ref: design.md §Delta item 3).

## Slice 1: Tested createdAt comparator helper (pure logic)

**Goal:** A standalone, unit-tested Python helper that takes the deduped tickets array + the
`STATUSES` order and returns it grouped-by-status then sorted by `createdAt` ascending with
`id` tie-break — verifiable end-to-end via its `_test.py` sibling and via a manual stdin/stdout
invocation, with zero dependency on the JS workflow.
**Files touched:**

- ✨ `scripts/qrspi_order_tickets.py` — `sort_tickets()` + `created_at_key()` and a
  stdlib-only `if __name__ == "__main__"` block reading the `{tickets, statuses}` JSON envelope
  from stdin and writing the sorted tickets JSON to stdout.
- ✨ `scripts/qrspi_order_tickets_test.py` — stdlib `unittest` sibling covering: (a) ascending
  `createdAt` within a group; (b) phase grouping/order preserved across `STATUSES` (AC3); (c)
  missing `createdAt` sorts last (AC5); (d) unparseable `createdAt` sorts last, no raise (AC5);
  (e) `id` numeric-suffix tie-break on equal `createdAt` (`RUS-7` before `RUS-71`, Decision 3).

**Verification:**
- [ ] `python3 scripts/qrspi_order_tickets_test.py` passes (all 5 cases above).
- [ ] Manual: `echo '{"tickets":[...],"statuses":["Selected","Design Review"]}' | python3 scripts/qrspi_order_tickets.py`
      emits the expected grouped+sorted ticket order on stdout.
**Context cost:** S
**Depends on:** none

## Slice 2: Wire createdAt into the Query phase and apply the sort in qrspi-batch.js

**Goal:** The batch fetches `createdAt` per ticket, validates it, and shells out to the Slice 1
helper after dedup so tickets are processed in within-phase FIFO order — verifiable end-to-end
by a real `/qrspi-batch` run whose "Found …" log line and `[i/total]` progression reflect the
created-order queue with phase boundaries intact.
**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — three coordinated edits: (1) Query fan-out prompt
  (~lines 944-956) requests `{ id, title, status, createdAt }` and relaxes the "Nothing else"
  instruction to include `createdAt` (Delta item 1); (2) `TICKETS_SCHEMA` (~lines 81-98) adds
  `createdAt: { type: 'string' }` to `properties` and `'createdAt'` to `required` (Delta item 2);
  (3) after the flatten/dedup loop (~after line 967, before line 969) shell out to
  `scripts/qrspi_order_tickets.py` with the deduped `tickets` + `STATUSES` and reassign `tickets`
  to its stdout (Delta item 3). No change to `STATUSES`, the reconciliation `.sort()` (line 904),
  the `seen` dedup, or the downstream loop (Delta item 4).

**Verification:**
- [ ] `node --check .claude/workflows/qrspi-batch.js` parses cleanly.
- [ ] Manual e2e: a real `/qrspi-batch` run logs "Found …" with tickets grouped by `STATUSES`
      order and, within each group, ascending `createdAt`; `[i/total]` progression consumes that
      order (AC6, ref: Q13).
- [ ] Worker-return validation still passes with `createdAt` present and required (AC4 dedup
      unaffected; schema fails fast if a worker omits `createdAt`).
**Context cost:** M
**Depends on:** Slice 1

---

## Unverified Assumptions

- **Linear `createdAt` wire shape (OQ1, NOT FOUND in repo):** the design assumes `createdAt`
  arrives as an ISO-8601 string from the `linear` MCP `list_issues` response. This is an external
  contract not verifiable from the repo. It drives `created_at_key()`'s parse strategy. The
  comparator parses defensively and falls back to "last" on unparseable values, so a shape
  mismatch degrades to missing-value behavior rather than a throw — but if the real shape is not a
  string, `TICKETS_SCHEMA`'s `{ type: 'string' }` would reject valid worker returns. Confirm
  against a live `list_issues` response before finalizing Slice 2.
- **`orderBy` rejection rests on undocumented MCP behavior:** Decision 1 rejects query-time
  `orderBy` partly because cross-batch merge breaks global order, which IS verifiable from the
  flatten logic — but the claim that MCP `orderBy` support is "undocumented/unreliable" is not
  mapped to repo code. Does not affect the chosen path (Option A), noted for completeness.
