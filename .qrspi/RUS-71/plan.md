# Implementation Plan — qrspi-batch: deterministic within-phase ticket ordering by createdAt

**Structure basis:** structure.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total steps:** 11

## Slice 1: Tested createdAt comparator helper (pure logic)

### Setup

1. ✨ Create `scripts/qrspi_order_tickets.py` — new stdlib-only Python helper module that
   will carry the pure comparator + the stdin/stdout CLI boundary. Add a module docstring
   stating its purpose: group-then-sort the deduped tickets array by `STATUSES` order, then
   by `createdAt` ascending with `id` tie-break (ref: structure.md Contracts; design.md
   Decision 2 Option A, Decision 4 Option B). Imports: `json`, `sys`, `datetime`, `re`.

### Core Logic

2. ✨ In `scripts/qrspi_order_tickets.py`, add
   `created_at_key(ticket: dict) -> tuple` — sort key returning a tuple
   `(missing_flag, parsed_createdAt, id_numeric_suffix)`: parse `ticket.get("createdAt")`
   as an ISO-8601 string (ascending); absent **or** unparseable `createdAt` sets the
   leading missing-flag so such tickets sort LAST; derive the `id` numeric-suffix tie-break
   by extracting the trailing integer of `ticket.get("id")` (e.g. `RUS-71` → `71`), defaulting
   to a sentinel when no suffix is present. Must never raise (ref: structure.md Contracts;
   design.md Decision 3 Option A, AC5).

3. ✨ In `scripts/qrspi_order_tickets.py`, add
   `sort_tickets(tickets: list[dict], statuses: list[str]) -> list[dict]` — stable-partition
   `tickets` by `status` in `statuses` order (tickets whose `status` is not in `statuses`
   form a final partition, order preserved), sort each partition by `created_at_key`,
   concatenate the partitions, and return the new list. Does not mutate the input
   (ref: structure.md Contracts; design.md Decision 2 Option A, AC3).

4. ✨ In `scripts/qrspi_order_tickets.py`, add an
   `if __name__ == "__main__":` block — read a JSON envelope
   `{ "tickets": [...], "statuses": [...] }` from `sys.stdin`, call
   `sort_tickets(envelope["tickets"], envelope["statuses"])`, and write the sorted
   `tickets` array as JSON to `sys.stdout` (ref: structure.md Contracts — CLI contract,
   mirrors `qrspi_resolve.py`/`qrspi_persist.py`/`qrspi_pr_body.py`).

### Tests

5. ✨ Create `scripts/qrspi_order_tickets_test.py` — stdlib `unittest` sibling importing
   `sort_tickets`/`created_at_key` from `qrspi_order_tickets`, covering all five cases:
   (a) ascending `createdAt` within a group; (b) phase grouping/order preserved across
   `STATUSES` (AC3); (c) missing `createdAt` sorts last (AC5); (d) unparseable `createdAt`
   sorts last with no raise (AC5); (e) `id` numeric-suffix tie-break on equal `createdAt`
   (`RUS-7` before `RUS-71`, Decision 3) (ref: structure.md Slice 1 Files touched).

6. Run: `python3 scripts/qrspi_order_tickets_test.py`
   - **Expected:** all five test cases pass, exit code 0.

### Verify Slice 1

7. **Checkpoint:** `python3 scripts/qrspi_order_tickets_test.py && echo '{"tickets":[{"id":"RUS-71","title":"b","status":"Selected","createdAt":"2026-01-02T00:00:00Z"},{"id":"RUS-7","title":"a","status":"Selected","createdAt":"2026-01-01T00:00:00Z"}],"statuses":["Selected","Design Review"]}' | python3 scripts/qrspi_order_tickets.py`
   - [ ] Unit test suite passes (all 5 cases).
   - [ ] Manual stdin/stdout invocation emits the grouped+sorted ticket order on stdout
         (`RUS-7` before `RUS-71` by ascending `createdAt`), with no traceback.

---

## Slice 2: Wire createdAt into the Query phase and apply the sort in qrspi-batch.js

### Setup

8. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — extend `TICKETS_SCHEMA` (~lines 81-98)
   so worker returns must carry `createdAt`.
   - **Current:** per-ticket `properties` are `{ id, title, status }` (string each);
     per-ticket `required` is `['id','title','status']`.
   - **After:** per-ticket `properties` adds `createdAt: { type: 'string' }`; per-ticket
     `required` adds `'createdAt'` → `['id','title','status','createdAt']`
     (ref: structure.md Modified Types; design.md Delta item 2 — OQ2 RESOLVED, required).

### Core Logic

9. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — update the Query fan-out prompt
   (~lines 944-956) so each worker requests and returns `createdAt`.
   - **Current:** prompt asks each worker to return `{ id, title, status }` and "Nothing else".
   - **After:** prompt asks each worker to return `{ id, title, status, createdAt }` and
     relaxes the "Nothing else" instruction to include `createdAt`
     (ref: structure.md Slice 2; design.md Delta item 1).

10. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — insert the sort shell-out immediately
    after the flatten/dedup loop (~after line 967, before the `log("Found …")` at line 969).
    - **Current:** after flatten+dedup, `tickets` is the deduped flat array consumed directly
      by `log("Found …")` and the downstream loop; no sort applied.
    - **After:** shell out to `scripts/qrspi_order_tickets.py`, passing
      `{ tickets, statuses: STATUSES }` as a JSON envelope on stdin, and reassign `tickets`
      to the parsed stdout (the sorted array). Order of operations: flatten → dedup → sort.
      No change to `STATUSES`, the reconciliation `.sort()` (line 904), the `seen` dedup, or
      the downstream loop (ref: structure.md JS call site; design.md Delta items 3 & 4).

### Verify Slice 2

11. **Checkpoint:** `node --check .claude/workflows/qrspi-batch.js`
    - [ ] `node --check` parses the workflow cleanly (no syntax error).
    - [ ] `TICKETS_SCHEMA` lists `createdAt` in both `properties` and `required`; the Query
          prompt requests `{ id, title, status, createdAt }`.
    - [ ] The sort shell-out to `scripts/qrspi_order_tickets.py` sits after the dedup loop and
          before `log("Found …")`, reassigning `tickets`.
    - [ ] Manual e2e (deferred to a live run): a real `/qrspi-batch` run logs "Found …" with
          tickets grouped by `STATUSES` order and ascending `createdAt` within each group, and
          the `[i/total]` progression consumes that order (AC6, ref: Q13). Confirm the live
          `list_issues` `createdAt` wire shape is an ISO-8601 string before relying on this
          (OQ1 / Risk Register — external contract NOT FOUND in repo).

---

## Rollback Notes

- Step 1-5 (Slice 1): new files only — `rm scripts/qrspi_order_tickets.py
  scripts/qrspi_order_tickets_test.py` fully reverts the slice. No DB/config/destructive ops.
- Steps 8-10 (Slice 2): edits are confined to `.claude/workflows/qrspi-batch.js`. Revert by
  removing `createdAt` from `TICKETS_SCHEMA` properties/required, restoring the
  `{ id, title, status }` / "Nothing else" prompt wording, and deleting the
  `qrspi_order_tickets.py` shell-out block — restoring flatten → dedup → (no sort). No DB
  migration, no config change, no destructive operation; the change only affects in-run
  processing order.
