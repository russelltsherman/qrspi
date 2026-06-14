# Work Tree — qrspi-batch: single-ticket scope (input.ticket)

**Plan basis:** plan.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 (9 tasks)

> Single-slice plan (Slice 1, 9 steps). All edits are additive code/doc changes to
> `.claude/workflows/qrspi-batch.js` plus two doc files; no new automated tests. The whole
> slice fits comfortably in one session under the 40% budget, so no session boundary is needed.

## Session 1

**Load:** structure.md §Contracts, structure.md §Files-touched, plan.md §Slice 1,
        design.md §Decisions (Decision 1/2/3), design.md §Risk Register
**Estimated context:** ~18% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add normalized `TICKET_ARG` constant after `PROJECT_ARG` (trim; blank→undefined) | — | §1 | S | pending |
| T2 | Wrap existing `phase('Query')` scope-resolve/validate/sweep/order stretch (1919–2045) in a single `else`, preceded by an `if (TICKET_ARG)` arm; `else` body byte-for-byte unchanged | T1 | §2 | M | pending |
| T3 | Inside `if (TICKET_ARG)` arm: spawn one `mcp__linear__get_issue` agent (TICKETS_SCHEMA, pin status/createdAt), build `{id,title,status,createdAt}`, set `tickets=[el]`; throw on not-found | T2 | §3 | M | pending |
| T4 | Add single-ticket scope-mode `log()` line at the 1957 scope-log site | T3 | §4 | S | pending |
| T5 | Add `ticket?` to `--- args ---` header (109–147); update precedence comment to `input.ticket > input.allProjects > input.project > config linearProject > "QRSPI"` | T1 | §5 | S | pending |
| T6 | Update `meta` Query-phase `detail` precedence string (line 6) to head with `input.ticket`, identical to §5 | T5 | §6 | S | pending |
| T7 | Update `.claude/CLAUDE.md` (26–31): add `input.ticket` to precedence string + concrete `args: { ticket: "RUS-58" }` example | T6 | §7 | S | pending |
| T8 | Update `README.md` (lines 60 and 164, both sites in lockstep): add `input.ticket` precedence + concrete example | T7 | §8 | S | pending |
| T9 | **Verify Slice 1** — existing `python3 scripts/qrspi_*_test.py` green; manual e2e (single-ticket scope, absent-arg unchanged, gated→entry_blocked/wait, nonexistent→fail-loud); doc lockstep across all four surfaces | T4, T8 | §9 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** End of work tree. Slice 1 is the only slice; the slice completes when T9's
verification checklist passes and `pr-summary.md` is produced.
