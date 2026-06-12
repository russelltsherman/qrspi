# Work Tree — qrspi-batch: deterministic within-phase ticket ordering by createdAt

**Plan basis:** plan.md @ 2026-06-12T00:00:00Z
**Generated:** 2026-06-12T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11

## Session 1

**Load:** structure.md §Contracts, structure.md §Types, plan.md §Slice 1
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/qrspi_order_tickets.py` with module docstring + stdlib imports (`json`, `sys`, `datetime`, `re`) | — | §1 | S | pending |
| T2 | Add `created_at_key(ticket)` — `(missing_flag, parsed_createdAt, id_numeric_suffix)` sort key; missing/unparseable createdAt sorts last; never raises | T1 | §2 | M | pending |
| T3 | Add `sort_tickets(tickets, statuses)` — stable-partition by status order, sort each partition by `created_at_key`, concatenate, non-mutating | T2 | §3 | M | pending |
| T4 | Add `if __name__ == "__main__"` CLI block — read `{tickets, statuses}` envelope from stdin, write sorted tickets array to stdout | T3 | §4 | S | pending |
| T5 | Create `scripts/qrspi_order_tickets_test.py` — unittest sibling covering all 5 cases (ascending, grouping, missing, unparseable, id tie-break) | T4 | §5 | M | pending |
| T6 | Run `python3 scripts/qrspi_order_tickets_test.py` — expect all 5 cases pass, exit 0 | T5 | §6 | S | pending |
| T7 | **Verify Slice 1** — unit suite passes + manual stdin/stdout invocation emits grouped+sorted order (RUS-7 before RUS-71), no traceback | T6 | §7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete (pure Python helper + tests, self-contained new files). Fresh context for Slice 2, which switches languages/files (JS workflow edits) and only needs the helper's CLI contract, not its implementation detail.

## Session 2

**Load:** structure.md §Contracts (CLI contract), structure.md §Modified Types, plan.md §Slice 2, impl-log.md §Slice 1 (notes only — confirm helper path + envelope shape)
**Estimated context:** ~22% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T8 | Extend `TICKETS_SCHEMA` in `.claude/workflows/qrspi-batch.js` (~L81-98) — add `createdAt: {type:'string'}` to per-ticket properties and `'createdAt'` to required | T7 | §8 | S | pending |
| T9 | Update Query fan-out prompt (~L944-956) — request/return `{id, title, status, createdAt}`, relax "Nothing else" to include createdAt | T8 | §9 | S | pending |
| T10 | Insert sort shell-out to `scripts/qrspi_order_tickets.py` after flatten/dedup (~after L967, before L969 `log("Found …")`) — pass `{tickets, statuses: STATUSES}` on stdin, reassign `tickets` to parsed stdout | T9 | §10 | M | pending |
| T11 | **Verify Slice 2** — `node --check` parses cleanly; schema/prompt carry createdAt; sort shell-out sits after dedup, before log; live e2e deferred | T10 | §11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete — both slices implemented. No further sessions; remaining work (live `/qrspi-batch` e2e confirming the `list_issues` createdAt wire shape) is deferred to a real batch run outside this DAG.
