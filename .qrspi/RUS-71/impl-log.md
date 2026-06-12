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

## Session 2 — Slice 2

**Timestamp:** 2026-06-12T01:47:12Z
**Tasks completed:** T8, T9, T10, T11
**Tasks failed:** none
**Tests:**

- `node --check .claude/workflows/qrspi-batch.js` → parses cleanly (PARSE_OK), 0 errors
- Sanity e2e of the JS↔Python boundary: piped the exact `{tickets, statuses}` envelope
  the workflow now builds into `python3 scripts/qrspi_order_tickets.py` → returns the
  tickets ARRAY grouped by `STATUSES` order then ascending `createdAt`
  (Selected: RUS-9 → RUS-7; then Design Review: RUS-71), no traceback
- Live `/qrspi-batch` e2e (Found-line grouping + `[i/total]` progression, AC6) deferred to
  a real batch run per plan §11 — not runnable from this slice

**Deviations from structure.md:**

- **Sort step mechanism (structure §JS call site / plan §10 say "the workflow shells
  out").** The workflow's JS sandbox **cannot execute python** (qrspi-batch.js header,
  lines 24-25: it "delegate[s] the git/gh/Linear/python mechanics (which the JS sandbox
  cannot run) to worker agents"). A Node `child_process`/`execFileSync` call to
  `qrspi_order_tickets.py` would not run. So I implemented the sort exactly as the cited
  reference pattern actually works in this file — the SAME `qrspi_resolve.py` pattern the
  structure names: a Query-phase worker `agent()` runs
  `python3 scripts/qrspi_order_tickets.py` over the `{tickets, statuses: STATUSES}`
  envelope (heredoc on stdin) and returns the sorted tickets ARRAY as verbatim JSON, which
  the JS parses via a new `parseOrderedTickets()` and reassigns to `tickets`. This honors
  the structure's contract intent (stdin envelope → stdout sorted array, "same pattern as
  qrspi_resolve.py") while respecting the runtime constraint; only the literal verb
  "shells out" changes to "worker-agent runs python", which is what every other python
  call in this workflow already does.
- Added a guard `if (tickets.length > 1)` around the sort (a 0/1-ticket queue needs no
  sort) and a defensive `parseOrderedTickets()` that returns null — keeping the deduped,
  unsorted-but-complete queue — on any parse failure or id-set drift, so a garbled worker
  echo degrades to "unsorted" and can never add/drop/mutate tickets. Not in the plan text
  but consistent with the "order-only, AC4 dedup unaffected" intent (structure §Slice 2
  Verification) and the resolver's "garbled echo → clean fallback" convention.

**Deviations from plan.md:**

- Changed `const tickets` to `let tickets` (plan §10 says "reassign `tickets`", which is
  impossible on a `const`). Mechanical, required by the reassignment the plan mandates.
- Added a `parseOrderedTickets()` + `extractJsonArray()` helper pair next to
  `parseResolveEnvelope`/`extractJsonObject` (the helper emits a JSON ARRAY, not an object,
  so the existing `extractJsonObject` did not apply). Same deviation as the structure one
  above — see that note for rationale.

**Notes for next session:**

- Slice 2 complete; both slices implemented. No further implementation sessions.
- The ONLY remaining work is the deferred live `/qrspi-batch` e2e (plan §11): confirm the
  real `mcp__linear__list_issues` response returns `createdAt` as an ISO-8601 **string**
  (OQ1 / Risk Register — external contract NOT FOUND in repo). The schema now REQUIRES
  `createdAt` as `{type:'string'}`, so a non-string live shape would reject worker returns
  and stall the Query phase — this must be verified against a live payload before relying
  on the run. The comparator itself degrades safely (missing/unparseable → sorts last,
  never raises), but the schema gate is strict by design (OQ2 RESOLVED: required).
- Sort is wired AFTER flatten+dedup and BEFORE `log("Found …")`; downstream loop, `seen`
  dedup, reconciliation `.sort()`, and `STATUSES` are untouched (Delta item 4).
