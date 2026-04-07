# Work Tree — <Ticket Title>

**Plan basis:** plan.md @ <timestamp>
**Generated:** <ISO-8601 timestamp>
**Status:** draft | approved
**Total sessions:** <N>
**Critical path:** <T1 → T2 → T3 → ...>

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1
**Estimated context:** <% of window>

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | <description> | — | §1.1 | S | pending |
| T2 | <description> | T1 | §1.2 | S | pending |
| T3 | <description> | T2 | §1.3 | S | pending |
| T4 | **Verify Slice 1** | T3 | §1.7 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. Fresh context for Slice 2.

## Session 2

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 2,
        impl-log.md §Slice 1 (notes only)
**Estimated context:** <% of window>

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T5 | <description> | T4 | §2.1 | M | pending |
| T6 | <description> | T5 | §2.2 | S | pending |
| T7 | **Verify Slice 2** | T6 | §2.11 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** <why a fresh context is needed here>
