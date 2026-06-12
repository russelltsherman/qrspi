# PR: RUS-71 qrspi-batch: deterministic within-phase ticket ordering by createdAt

**Ticket:** RUS-71
**Design:** design.md @ 2026-06-11T00:00:00Z
**Structure:** structure.md @ 2026-06-12T00:00:00Z

## Summary

The `qrspi-batch` Query phase previously processed tickets in whatever order Linear
returned them within each status group, making batch runs non-reproducible. This change
fetches each ticket's `createdAt`, then — after the existing flatten+dedup — sorts the
queue by `STATUSES` (phase) order and, within each group, by `createdAt` ascending with a
numeric `id`-suffix tie-break, so tickets are processed in within-phase FIFO (oldest-first)
order deterministically. The pure comparator lives in a new tested Python helper
(`scripts/qrspi_order_tickets.py`, the established `scripts/qrspi_*` + `_test.py` pattern);
the workflow's JS sandbox cannot run python, so a Query-phase worker agent runs the helper
over a `{tickets, statuses}` stdin envelope and returns the sorted array, which JS parses
and reassigns. **Reviewer focus:** (1) the JS→Python boundary realized as a worker `agent()`
rather than a literal `child_process` shell-out (a runtime constraint — see Deviations);
(2) `parseOrderedTickets()`'s permutation guard, which makes the sort order-only and
fail-safe (a garbled echo keeps the unsorted-but-complete queue, never adds/drops tickets);
(3) the unverified live wire shape of Linear's `createdAt` (see Risks / Open Items).

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: fetch `createdAt` per ticket | `qrspi-batch.js` Query fan-out prompt (`{ id, title, status, createdAt }`) + `TICKETS_SCHEMA` (`createdAt: {type:'string'}`, required) | `qrspi_order_tickets_test.py:test_ascending_created_at_within_a_group` (consumes `createdAt`); live `/qrspi-batch` e2e (deferred) |
| AC2: within-group `createdAt` ascending, deterministic ties | `qrspi_order_tickets.py:sort_tickets`, `created_at_key`, `_id_suffix` | `qrspi_order_tickets_test.py:test_ascending_created_at_within_a_group`, `test_id_numeric_suffix_tie_break` |
| AC3: phase grouping/order unchanged | `qrspi_order_tickets.py:sort_tickets` (stable-partition by `statuses` order); `STATUSES` untouched in `qrspi-batch.js` | `qrspi_order_tickets_test.py:test_grouping_and_status_order_preserved`, `test_unknown_status_partition_sorts_last` |
| AC4: dedup still works | `qrspi-batch.js` `seen`-Set flatten loop unchanged; sort runs after dedup; `parseOrderedTickets` permutation guard preserves the id-set | `qrspi_order_tickets_test.py:test_input_not_mutated`; `node --check`; live e2e (deferred) |
| AC5: missing/unparseable `createdAt` sorts last, no throw | `qrspi_order_tickets.py:_parse_created_at` + `created_at_key` fallback | `qrspi_order_tickets_test.py:test_missing_created_at_sorts_last`, `test_missing_key_does_not_raise`, `test_unparseable_created_at_sorts_last_no_raise`, `test_non_string_created_at_sorts_last` |
| AC6: comparator verified | `qrspi_order_tickets_test.py` (9 cases); JS↔Python sanity pipe | `python3 scripts/qrspi_order_tickets_test.py` → 9 passed; live `/qrspi-batch` "Found …" + `[i/total]` (deferred) |

## Changes by Slice

### Slice 1: Tested createdAt comparator helper (pure logic)

| File | Change | Lines |
|------|--------|-------|
| `scripts/qrspi_order_tickets.py` | ✨ new | +120 |
| `scripts/qrspi_order_tickets_test.py` | ✨ new | +119 |

### Slice 2: Wire createdAt into the Query phase and apply the sort in qrspi-batch.js

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +74, -3 |

Three coordinated edits in `qrspi-batch.js`: (1) `TICKETS_SCHEMA` adds `createdAt`
(property + required); (2) Query fan-out prompt requests `createdAt`; (3) after
flatten/dedup, a new `extractJsonArray()` + `parseOrderedTickets()` pair and an `order:tickets`
worker `agent()` apply the sort and reassign `tickets` (`const` → `let`).

## Testing Summary

- [x] Slice 1: unit tests — `python3 scripts/qrspi_order_tickets_test.py` — 9 passed, 0 failed (5 plan-mandated cases + 4 defensive)
- [x] Slice 1: manual CLI — `echo '{"tickets":[...],"statuses":[...]}' | python3 scripts/qrspi_order_tickets.py` — emits `RUS-7` before `RUS-71` (ascending createdAt / numeric tie-break), no traceback
- [x] Slice 2: syntax — `node --check .claude/workflows/qrspi-batch.js` — parses cleanly (PARSE_OK)
- [x] Slice 2: JS↔Python boundary sanity — piped the exact `{tickets, statuses}` envelope the workflow builds into the helper — returned `Selected: RUS-9 → RUS-7; then Design Review: RUS-71`, grouped then ascending, no traceback
- [ ] Manual e2e (DEFERRED): live `/qrspi-batch` run logging "Found …" grouped by `STATUSES` then ascending `createdAt`, with `[i/total]` consuming that order (AC6) — not runnable from a slice; must also confirm live `list_issues` returns `createdAt` as an ISO-8601 string (OQ1)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| JS sort mechanism | Structure §JS call site / plan §10: "the workflow **shells out** to `qrspi_order_tickets.py`" | A Query-phase worker `agent()` runs `python3 scripts/qrspi_order_tickets.py` over the `{tickets, statuses}` stdin heredoc and returns the sorted array (verbatim JSON), parsed via new `parseOrderedTickets()` | The JS sandbox cannot execute python (qrspi-batch.js header: it delegates all python mechanics to worker agents). A `child_process` call would not run. This is the SAME pattern the structure cites (`qrspi_resolve.py`); only the literal verb "shells out" becomes "worker-agent runs python", which every other python call in this workflow already does. CLI contract (stdin envelope → stdout sorted array) is honored exactly. |
| `tickets` binding | Plan §10: "reassign `tickets`" | Changed `const tickets` → `let tickets` | Mechanical; reassignment is impossible on a `const`, and the plan mandates the reassignment. |
| Extra defensive code | Not in plan text | Added `if (tickets.length > 1)` sort guard; `parseOrderedTickets()` returns null (keeping the deduped queue) on parse failure or id-set drift; 4 extra unit tests beyond the 5 mandated | Consistent with "order-only, AC4 dedup unaffected" intent and the resolver's "garbled echo → clean fallback" convention; defends the TDD-mandated branch-heavy paths. |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| Linear `createdAt` wire shape differs from assumed ISO-8601 string (external, NOT FOUND in repo) | **OPEN / discovered-unverified** — `TICKETS_SCHEMA` now REQUIRES `createdAt` as `{type:'string'}`; a non-string live shape would reject worker returns and stall the Query phase. Comparator degrades safely (missing/unparseable → last), but the schema gate is strict. Must verify against a live payload (OQ1). | Relax `TICKETS_SCHEMA` `createdAt` to optional, or remove the required entry, to unblock the Query phase if the live shape mismatches. |
| Workers omit `createdAt` despite prompt+schema | mitigated — `createdAt` is `required` in `TICKETS_SCHEMA` (fails fast); comparator still tolerates missing values (AC5) | Remove `'createdAt'` from `required`; comparator already sorts missing-value tickets last. |
| Comparator reorders across phase groups (violates AC3) | mitigated — group-then-sort via `sort_tickets` partition; covered by `test_grouping_and_status_order_preserved` | Revert Slice 2's sort block; queue falls back to flatten order. |
| Comparator regresses without an automated guard | mitigated — `scripts/qrspi_order_tickets_test.py` (9 cases) guards ascending / missing-last / tie-break | n/a (test-only). |
| Missing-value `createdAt` silently mis-orders instead of throwing | mitigated — explicit "sorts last" fallback in `_parse_created_at` / `created_at_key`, never raises; covered by 4 tests | n/a. |

**Whole-feature rollback:** revert commits `fb16d85` (Slice 2) then `157bf44` (Slice 1).
Slice 2 reverts independently (restores `const tickets` and flatten-order processing);
Slice 1's helper is then dead and can be deleted.

## Open Items

- **DEFERRED live e2e (AC6, OQ1):** confirm a real `mcp__linear__list_issues` response returns
  `createdAt` as an ISO-8601 **string** before relying on a batch run — the required
  `{type:'string'}` schema would reject a non-string live shape and stall the Query phase. Also
  observe the "Found …" log + `[i/total]` progression preserve `STATUSES` group boundaries with
  within-group ascending order. Not runnable from an implementation slice (plan §11).
- OQ2 (required `createdAt`), OQ3 (tested Python helper), OQ4 (first-batch-wins dedup retained):
  RESOLVED by reviewer during design; no follow-up.
- `orderBy`-rejection rationale (Decision 1) partly rests on undocumented MCP behavior; does not
  affect the chosen path (in-script sort), noted for completeness only.
