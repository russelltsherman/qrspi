# Structure Outline — qrspi-batch: single-ticket scope (input.ticket)

**Design basis:** design.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft

## New Types

None. The feature introduces no new data type. The single-ticket path builds the
same four-field record (`{ id, title, status, createdAt }`) the sweep already
produces, validated by the existing `TICKETS_SCHEMA` (ref: design §Delta, Decision 1).

## Modified Types

None. `TICKETS_SCHEMA` is reused as-is — attached to the new single-fetch agent
to give the single path the same four-field guarantee the sweep has, but its
shape is unchanged (ref: design Decision 1, Risk Register row 1).

## Contracts

No new function/module boundary is created. The feature is one inline branch
inside `phase('Query')` in `.claude/workflows/qrspi-batch.js`. The cross-slice
interface is the existing **`tickets` array** — the sole scope→loop boundary
(ref: design AC5, Q9). Both arms of the new branch must leave `tickets` holding
records of the existing shape so the unchanged loop body consumes them
identically:

- `tickets: Array<{ id: string, title: string, status: string, createdAt: string }>`
  — produced by **either** the single-fetch arm (`if (TICKET_ARG)`) **or** the
  existing scope/sweep/order arm (`else`); consumed unchanged by
  `resolveTicket → ensureRestacked → dispatch → critics → finalize → reconcile`
  (ref: design AC1, AC2, AC5).
- Per design Decision 2 / OQ1, **no** `qrspi_scope_mode.py` selector and **no**
  `_test.py` sibling are introduced — the single-ticket selection is a trivial
  truthiness branch on the already-normalized `TICKET_ARG` constant, not pure
  decision logic under AC6 (ref: design AC6, Decision 2, Q10, Q11).

## Slice 1: input.ticket single-ticket scope branch + docs

**Goal:** A `qrspi-batch` run invoked with `{ ticket: "RUS-XX" }` fetches that one
issue via `mcp__linear__get_issue`, sets `tickets = [that one]`, skips
project-scope resolution / the `list_issues` sweep / the ordering step, and runs
the single ticket through the identical existing loop body — producing the same
`{ ticketsProcessed, results, reconciliation }` envelope a one-ticket batch run
produces. When `input.ticket` is absent, the sweep path runs byte-for-byte
unchanged. All four scoping-documentation surfaces gain `input.ticket` in
lockstep. (ref: design AC1–AC5, AC7)

**Files touched:**

- ⚠️ `.claude/workflows/qrspi-batch.js` — (1) add normalized top-of-file constant
  `TICKET_ARG` near line 139, mirroring `PROJECT_ARG`'s trim/normalize discipline;
  (2) add the `--- args ---` header entry for `ticket?` and update the precedence
  comment (lines 109–147) to `input.ticket > input.allProjects > input.project >
  config linearProject > "QRSPI"`; (3) update the `meta` Query-phase `detail`
  string (line 6) to put `input.ticket` at the head of the precedence; (4) at the
  top of `phase('Query')`, wrap the existing scope-resolve + validate + sweep +
  order stretch (1919–2045) in a single `else`, with the new `if (TICKET_ARG)` arm
  spawning one `mcp__linear__get_issue` agent (with `TICKETS_SCHEMA` attached,
  `status`/`createdAt` pinned in the worker prompt) that builds the four-field
  element and `throw`s on not-found; (5) add a scope-mode `log()` line for the
  single-ticket path at the 1957 position
  (e.g. `Project scope: single ticket (input.ticket=RUS-XX)`).
  (ref: design §Delta, Decision 1, Decision 3, Q3, Q7, Q9, Q12)
- ⚠️ `.claude/CLAUDE.md` (lines 26–31) — add `input.ticket` to the precedence
  string and a concrete `Workflow({ name: "qrspi-batch", args: { ticket: "RUS-58" } })`
  example (ref: design §Delta, AC7, Q13).
- ⚠️ `README.md` (lines 60, 164) — add `input.ticket` to the precedence string and
  the concrete example at both sites (ref: design §Delta, AC7, Q13, OQ2).

**Verification:**

- [ ] Manual e2e: invoke `qrspi-batch` with `{ ticket: "<a real Selected,
  assigned ticket>" }`; confirm the Query log shows the single-ticket scope line,
  the `list_issues` sweep and order step are skipped, and exactly one element
  reaches the loop, yielding the same `{ ticketsProcessed, results,
  reconciliation }` envelope a one-ticket run produces (ref: AC1, AC2).
- [ ] Manual e2e: invoke `qrspi-batch` with **no** `ticket` arg; confirm the sweep
  queue and ordering are byte-for-byte unchanged from current behavior (ref: AC5,
  Risk Register row 2).
- [ ] Manual e2e: invoke with `{ ticket: "<a gated ticket — not Selected or
  unassigned>" }`; confirm the resolver still surfaces `entry_blocked`/`wait` as a
  recorded result (re-fetch/re-decide per ticket regardless of entry path)
  (ref: AC4, Q5, Q8).
- [ ] Manual e2e: invoke with `{ ticket: "<a nonexistent id>" }`; confirm the run
  aborts (fail-loud `throw`) rather than producing an empty queue (ref: AC ​Decision 3, Q7).
- [ ] Existing `scripts/qrspi_*_test.py` suite still passes (resolver tests
  unchanged — no pure-logic helper added, ref: AC6, Decision 2).
- [ ] Doc check: `input.ticket` (purpose, precedence head, concrete
  `args: { ticket: ... }` example) appears on all four surfaces — meta Query
  detail, `--- args ---` header comment, `.claude/CLAUDE.md`, `README.md` (×2) —
  with the identical precedence string (ref: AC7, Risk Register row 3, OQ2).

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- **`mcp__linear__get_issue` returns a byte-compatible 4-field record.** The
  design (Decision 1, Risk Register row 1, Q2) flags that `get_issue`'s
  byte-compatibility for `{ id, title, status, createdAt }` is **unproven
  in-repo** — the MCP response shape is external. Mitigation is in-design (attach
  `TICKETS_SCHEMA`, pin `status`/`createdAt` in the worker prompt, rely on the
  order helper tolerating a missing `createdAt`), but the actual field shape can
  only be confirmed at implementation/e2e time. This needs attention if the
  manual e2e shows a field mismatch.
- **Exact line numbers (139, 109–147, line 6, 1919–2045, 1957, CLAUDE.md 26–31,
  README 60/164) are from the design's reading of the current files.** They are
  anchors, not contracts; the implementer should locate by surrounding code
  (`PROJECT_ARG` constant, the `--- args ---` header, the `phase('Query')` scope
  block, the scope-mode `log()` call) rather than trusting absolute offsets, since
  the files may have drifted since the research snapshot.
