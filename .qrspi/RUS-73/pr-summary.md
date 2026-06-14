# PR: RUS-73 — qrspi-batch: single-ticket scope (input.ticket)

**Ticket:** RUS-73
**Design:** design.md @ 2026-06-13T00:00:00Z
**Structure:** structure.md @ 2026-06-14T00:00:00Z

## Summary

Adds an `input.ticket` single-ticket scope to the `qrspi-batch` Query phase: when
`{ ticket: "RUS-XX" }` is passed, the phase fetches that one issue via
`mcp__linear__get_issue`, sets `tickets = [that one]`, and skips project-scope
resolution, the `list_issues` sweep, and the ordering step — running just that ticket
through the identical existing loop body. This lets an operator drive one named ticket
through the critic pipeline without sweeping the whole project. The change is one
enclosing `if (TICKET_ARG) { … } else { …existing sweep… }` branch on a normalized
top-of-file constant plus lockstep documentation updates; no new types, no new module
boundary, no new Python helper. **Reviewer focus:** (1) the absent-`input.ticket` path
must be byte-for-byte unchanged — confirm the `else` arm encloses only the existing
scope/sweep/order stretch and the hoisted `let tickets` does not alter sweep logic;
(2) the fail-loud `throw` on a not-found id; (3) the four documentation surfaces all
carry the identical precedence string.

## Acceptance Criteria Mapping

| Criterion | Implementation | Test |
|-----------|---------------|------|
| AC1: `input.ticket` present → fetch one issue's `{id,title,status,createdAt}`, set `tickets=[that one]`, skip scope/sweep/order | `.claude/workflows/qrspi-batch.js` — `if (TICKET_ARG)` arm in `phase('Query')` | Manual e2e (single-ticket scope); not executed here — requires live Linear MCP |
| AC2: single ticket flows through the identical loop body, same `{ticketsProcessed,results,reconciliation}` envelope | `.claude/workflows/qrspi-batch.js` — unchanged loop body downstream of `tickets` | Manual e2e (envelope-parity check) |
| AC3: precedence `input.ticket > allProjects > project > config linearProject > "QRSPI"` as single scope source | `.claude/workflows/qrspi-batch.js` — `TICKET_ARG` constant + single branch point; precedence comment | `node --check` (syntax) + doc lockstep check |
| AC4: gated single-ticket target still surfaces `entry_blocked`/`wait` (resolver re-fetches/re-decides) | `.claude/workflows/qrspi-batch.js` — no entry-gate logic added; resolver path unchanged | Manual e2e (gated ticket → entry_blocked/wait) |
| AC5: absent `input.ticket` → sweep path byte-for-byte unchanged | `.claude/workflows/qrspi-batch.js` — `else` wraps only the 1919–2045 stretch; `let tickets` hoisted | Manual e2e (sweep-queue unchanged) + `node --check` |
| AC6: any pure decision logic gets a `_test.py`; this feature introduces none | `.claude/workflows/qrspi-batch.js` — JS-inline truthiness branch only (Decision 2) | `for f in scripts/qrspi_*_test.py; do python3 "$f"; done` → 20/20 (resolver tests unchanged) |
| AC7: docs add `input.ticket` (purpose, precedence head, concrete example) to every scoping surface | `.claude/workflows/qrspi-batch.js` (meta detail + `--- args ---` header), `.claude/CLAUDE.md`, `README.md` (×2) | Doc lockstep check — identical precedence string on all four surfaces |

## Changes by Slice

### Slice 1: input.ticket single-ticket scope branch + docs

| File | Change | Lines |
|------|--------|-------|
| `.claude/workflows/qrspi-batch.js` | ⚠️ modified | +50, -4 |
| `.claude/CLAUDE.md` | ⚠️ modified | +9, -2 |
| `README.md` | ⚠️ modified | +8, -2 |

Code change detail (`qrspi-batch.js`): (1) new normalized `TICKET_ARG` constant
mirroring `PROJECT_ARG`'s trim/normalize discipline; (2) `--- args ---` header gains
`ticket?` and the precedence comment is updated; (3) the `meta` Query `detail` string
puts `input.ticket` at the head of the precedence; (4) `phase('Query')` gains one
branch point — the `if (TICKET_ARG)` arm spawns one `mcp__linear__get_issue` agent
(with `TICKETS_SCHEMA` attached, `status`/`createdAt` pinned in the worker prompt),
builds the four-field element, and `throw`s on not-found; the existing
scope-resolve/sweep/order stretch is wrapped in `else`; (5) a single-ticket scope-mode
`log()` line. `let tickets` was hoisted above the branch and the inner sweep-arm
`let tickets = []` became a bare `tickets = []` reassignment so both arms write the
same scope→loop boundary variable (the minimal change to enclose the stretch; sweep
logic is unchanged).

Note: the diff against `main` also includes the QRSPI phase artifacts
(`.qrspi/RUS-73/{questions,research,design,structure,plan,worktree,impl-log}.md`),
committed in the earlier design/plan phase commits (`efc2d8e`, `1ceec91`) of this
stack — not part of the implementation slice. The implementation slice commit
(`4259e35`) touches only the three product files above.

## Testing Summary

- [x] Slice 1: unit suite — `for f in scripts/qrspi_*_test.py; do python3 "$f"; done` → 20 files passed, 0 failed (resolver tests unchanged — no pure-logic helper added per AC6/Decision 2)
- [x] Slice 1: syntax — `node --check .claude/workflows/qrspi-batch.js` → OK
- [x] Doc lockstep: identical precedence string `input.ticket > input.allProjects > input.project > config linearProject > "QRSPI"` present on all four surfaces (meta Query detail, `--- args ---` header, `.claude/CLAUDE.md`, `README.md` ×2), with concrete `args: { ticket: "RUS-58" }` example in CLAUDE.md and both README sites
- [ ] Manual e2e — single-ticket scope: one element reaches the loop, sweep/order skipped, same envelope (NOT executed here — requires live `mcp__linear__*` worker + a runnable workflow, neither available to the implement/PR agent)
- [ ] Manual e2e — absent-arg sweep byte-for-byte unchanged (NOT executed here)
- [ ] Manual e2e — gated ticket → `entry_blocked`/`wait` recorded result (NOT executed here)
- [ ] Manual e2e — nonexistent id → fail-loud `throw`, no empty queue (NOT executed here)

## Deviations from Structure

| Contract / Type | Expected | Actual | Justification |
|-----------------|----------|--------|---------------|
| `tickets` scope→loop boundary variable | both arms leave `tickets` of shape `{id,title,status,createdAt}` for the unchanged loop | `let tickets` hoisted above the branch; sweep arm's `let tickets = []` became bare `tickets = []` reassignment | Minimal change required to enclose the existing stretch in an `else` while keeping `tickets` in scope for the unchanged consuming loop; does not alter the sweep arm's logic (impl-log §Deviations) |
| README edit sites (plan named "lines 60 and 164") | full precedence string at both sites | site 1 (Query table row) got the full precedence string + concrete example; site 2 was prose, updated in lockstep with the precedence string + same concrete example | Site 2 was a prose sentence, not a precedence-string site; both updated in lockstep per the plan's intent (impl-log §Deviations from plan.md) |

## Risks & Rollback

| Risk (from design.md) | Status Post-Implementation | Rollback Step |
|------------------------|---------------------------|---------------|
| `get_issue` may not return a byte-compatible 4-field `{id,title,status,createdAt}` record (MCP shape external, unproven in-repo) | accepted / unverified — mitigated by attaching `TICKETS_SCHEMA` to the single-fetch agent and pinning `status`/`createdAt` in the worker prompt; actual shape confirmable only at e2e. If e2e shows a field mismatch (e.g. status as a state object not a name string), look at the single-fetch worker prompt | Revert commit `4259e35` — restores the sweep-only Query path |
| Absent-`input.ticket` path drifts from byte-for-byte sweep behavior (AC5) | mitigated — single branch point; the `else` wraps only the existing stretch; `node --check` passes. Final confirmation is the manual sweep-parity e2e | Revert commit `4259e35` |
| Precedence string drifts across the 4–5 documentation surfaces | mitigated — all surfaces edited in lockstep; the identical precedence string verified present on meta detail, args header, CLAUDE.md, README ×2 | Revert commit `4259e35` |

## Open Items

- **Manual e2e pass is deferred** and remains the real AC1/AC2/AC4/AC5/Decision-3 gate: the four end-to-end checks (single-ticket scope; absent-arg sweep unchanged; gated ticket → `entry_blocked`/`wait`; nonexistent id → fail-loud `throw`) require spawning live `mcp__linear__*` workers against a real Linear workspace and running the workflow — unavailable to the implement/PR agent. They must be run in an orchestrated/manual context before merge.
- **`get_issue` field-shape verification:** the one unverified in-repo assumption is that `mcp__linear__get_issue` returns a byte-compatible `{id,title,status,createdAt}` (design Risk Register row 1 / structure §Unverified Assumptions). Confirm at e2e; the single-fetch worker prompt is the place to adjust if `status` comes back as a state object rather than a name string.
- No follow-up tickets identified. No `qrspi_scope_mode.py` helper and no `_test.py` sibling were created (Decision 2 / OQ1 — dropped, not deferred). OQ2 (no `qrspi-batch` SKILL.md surface) and OQ3 (single id, not an array) were resolved by the reviewer; no tech debt tracked.
