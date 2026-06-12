# Implementation Log — qrspi-batch: deterministic within-phase ticket ordering by createdAt

## Session 1 — Slice 1

**Timestamp:** 2026-06-12T00:00:00Z
**Tasks completed:** T1, T2, T3, T4, T5, T6, T7
**Tasks failed:** none
**Tests:**

- `python3 scripts/qrspi_order_tickets_test.py` → 9 passed, 0 failed
- Manual checkpoint: `echo '{"tickets":[{"id":"RUS-71",…},{"id":"RUS-7",…}],"statuses":["Selected","Design Review"]}' | python3 scripts/qrspi_order_tickets.py` → emits `RUS-7` before `RUS-71` (ascending createdAt), no traceback

**Deviations from structure.md:**

- none — `sort_tickets(tickets, statuses)` and `created_at_key(ticket)` match the
  Contracts signatures; CLI reads `{tickets, statuses}` envelope on stdin, writes sorted
  tickets JSON on stdout.

**Deviations from plan.md:**

- none. Note (not a deviation): the 5 plan-mandated cases are covered, and I added 4
  extra defensive tests (unknown-status partition, missing-key no-raise, non-string
  createdAt, input-not-mutated) → 9 tests total. All five required cases (ascending,
  grouping, missing, unparseable, id tie-break) are present and passing.

**Notes for next session:**

- Helper path is `scripts/qrspi_order_tickets.py` (relative to repo root / worktree root).
- CLI contract for the Slice 2 shell-out: stdin JSON envelope is
  `{ "tickets": [...], "statuses": [...] }`; stdout is the sorted `tickets` ARRAY (not an
  envelope) as compact JSON. Pass `STATUSES` as `statuses`. Reassign `tickets` to the
  parsed stdout.
- `createdAt` is parsed as an ISO-8601 string (trailing `Z` accepted, naive treated as
  UTC). Absent / unparseable / non-string `createdAt` degrades to "sorts last within
  group" and never raises — so a `TICKETS_SCHEMA` `{type:'string'}` for `createdAt` is
  consistent with the comparator (the OQ1 wire-shape risk in structure.md still stands:
  confirm live `list_issues` returns an ISO-8601 string before relying on the e2e order).
- Stdlib-only (`json`, `sys`, `datetime`, `re`); no third-party deps.

---
