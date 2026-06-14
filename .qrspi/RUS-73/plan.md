# Implementation Plan — qrspi-batch: single-ticket scope (input.ticket)

**Structure basis:** structure.md @ 2026-06-14T00:00:00Z
**Generated:** 2026-06-14T00:00:00Z
**Status:** draft
**Total steps:** 9

> **Locate by anchor, not line number.** All line numbers below (139, 109–147, line 6,
> 1919–2045, 1957, CLAUDE.md 26–31, README 60/164) are anchors from the research snapshot,
> not contracts. Locate each edit by surrounding code (`PROJECT_ARG` constant, the
> `--- args ---` header, the `phase('Query')` scope block, the scope-mode `log()` call)
> rather than trusting absolute offsets (ref: structure Unverified Assumptions).

## Slice 1: input.ticket single-ticket scope branch + docs

### Setup

1. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a normalized top-of-file constant
   `TICKET_ARG` immediately after the `PROJECT_ARG` constant (near line 139), mirroring
   `PROJECT_ARG`'s trim/normalize discipline (trimmed; blank→undefined). (ref: structure
   Files-touched item 1, design Decision 1, Q3)
   - **Current:** `const PROJECT_ARG = …` exists; no `TICKET_ARG` constant.
   - **After:** `const TICKET_ARG = (typeof input?.ticket === "string" ? input.ticket.trim() : "") || undefined;`
     normalized constant present alongside `PROJECT_ARG`.

### Core Logic

2. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — at the top of `phase('Query')`, wrap the
   existing scope-resolve + validate + sweep + order stretch (1919–2045) in a single `else`,
   introducing **one** new branch point `if (TICKET_ARG) { … } else { …existing stretch… }`.
   The `else` arm must contain the existing 1919–2045 code byte-for-byte (single enclosing
   wrap, no edits inside it). (ref: structure Files-touched item 4, design Delta, AC5, Q9;
   Risk Register row 2)
   - **Current:** the scope-resolve + validate + sweep + order code runs unconditionally at
     the top of `phase('Query')`.
   - **After:** that same code runs only in the `else` arm; an `if (TICKET_ARG)` arm precedes it.

3. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — inside the new `if (TICKET_ARG)` arm, spawn
   one `mcp__linear__get_issue` agent (with `TICKETS_SCHEMA` attached, mirroring the sweep
   agent), pinning `status` and `createdAt` explicitly in the worker prompt; build the
   four-field element `{ id, title, status, createdAt }` and set `tickets = [el]`. On
   not-found, `throw` (fail-loud, matching the scope-block convention). (ref: structure
   Files-touched item 4, design Decision 1, Decision 3, Q1, Q2, Q7; Risk Register rows 1, 2)
   - **Current:** no single-fetch path; `TICKETS_SCHEMA` is attached only to the sweep agents.
   - **After:** `tickets: Array<{ id: string, title: string, status: string, createdAt: string }>`
     of length 1 produced by the single-fetch arm; not-found `throw`s.

4. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add a scope-mode `log()` line for the
   single-ticket path at the 1957 position (the existing scope-mode log site), e.g.
   `Project scope: single ticket (input.ticket=RUS-XX)`. (ref: structure Files-touched item 5,
   design Delta, Q12)
   - **Current:** scope mode is logged once at the 1957 position for the sweep path only.
   - **After:** the single-ticket arm emits its own scope-mode `log()` line.

5. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — add the `--- args ---` header entry for
   `ticket?` and update the precedence comment (lines 109–147) to
   `input.ticket > input.allProjects > input.project > config linearProject > "QRSPI"`.
   (ref: structure Files-touched item 2, design Delta, Q3, Q13; Risk Register row 3)
   - **Current:** `--- args ---` header documents `allProjects?` / `project?`; precedence
     comment reads `input.allProjects > input.project > config linearProject > "QRSPI"`.
   - **After:** header also documents `ticket?`; precedence comment puts `input.ticket` at head.

6. ⚠️ Modify `.claude/workflows/qrspi-batch.js` — update the `meta` Query-phase `detail`
   string (line 6) so `input.ticket` heads the precedence, with the identical precedence
   string used in step 5. (ref: structure Files-touched item 3, design Delta, Q13;
   Risk Register row 3)
   - **Current:** `meta` Query `detail` precedence string omits `input.ticket`.
   - **After:** precedence string begins with `input.ticket >`, matching steps 5/7/8 verbatim.

### Tests

(No new automated tests. Per design Decision 2 / AC6 / OQ1, this feature introduces **no**
pure decision logic — the single-ticket selection is a one-line truthiness branch on the
already-normalized `TICKET_ARG`, matching the RUS-66 JS-inline precedent. **No**
`qrspi_scope_mode.py` and **no** `_test.py` sibling are added; AC6 is satisfied by the
resolver's existing tests plus the mandated manual e2e below. ref: structure Contracts bullet 2,
design Decision 2, OQ1.)

### Docs

7. ⚠️ Modify `.claude/CLAUDE.md` (lines 26–31) — add `input.ticket` to the precedence string
   and add a concrete `Workflow({ name: "qrspi-batch", args: { ticket: "RUS-58" } })` example.
   Use the identical precedence string as steps 5/6/8. (ref: structure Files-touched item 2,
   design Delta, AC7, Q13; Risk Register row 3)
   - **Current:** precedence string omits `input.ticket`; no single-ticket example.
   - **After:** precedence string headed by `input.ticket`; concrete `args: { ticket: ... }` example present.

8. ⚠️ Modify `README.md` (lines 60 and 164 — **both** sites) — add `input.ticket` to the
   precedence string and the concrete `Workflow({ name: "qrspi-batch", args: { ticket: "RUS-58" } })`
   example at each site. Use the identical precedence string as steps 5/6/7. (ref: structure
   Files-touched item 3, design Delta, AC7, Q13, OQ2; Risk Register row 3)
   - **Current:** both README sites carry the precedence string without `input.ticket`.
   - **After:** both sites updated in lockstep — same precedence string, same concrete example.

### Verify Slice 1

9. **Checkpoint:** run the manual end-to-end and doc-consistency checks below (this feature's
   verification is manual-e2e + doc lockstep; the existing unit suite must remain green).
   - [ ] `python3 scripts/qrspi_*_test.py` (or the repo's standard test invocation) — existing
     suite passes; resolver tests unchanged, no pure-logic helper added (ref: AC6, Decision 2).
   - [ ] Manual e2e — invoke `qrspi-batch` with `{ ticket: "<a real Selected, assigned ticket>" }`;
     confirm the Query log shows the single-ticket scope line, the `list_issues` sweep and order
     step are skipped, and exactly one element reaches the loop, yielding the same
     `{ ticketsProcessed, results, reconciliation }` envelope a one-ticket run produces
     (ref: AC1, AC2).
   - [ ] Manual e2e — invoke `qrspi-batch` with **no** `ticket` arg; confirm the sweep queue and
     ordering are byte-for-byte unchanged from current behavior (ref: AC5, Risk Register row 2).
   - [ ] Manual e2e — invoke with `{ ticket: "<a gated ticket — not Selected or unassigned>" }`;
     confirm the resolver still surfaces `entry_blocked`/`wait` as a recorded result (re-fetch /
     re-decide per ticket regardless of entry path) (ref: AC4, Q5, Q8).
   - [ ] Manual e2e — invoke with `{ ticket: "<a nonexistent id>" }`; confirm the run aborts
     (fail-loud `throw`) rather than producing an empty queue (ref: Decision 3, Q7).
   - [ ] Doc check — `input.ticket` (purpose, precedence head, concrete `args: { ticket: ... }`
     example) appears on all four surfaces with the **identical** precedence string: the `meta`
     Query detail (step 6), the `--- args ---` header comment (step 5), `.claude/CLAUDE.md`
     (step 7), and `README.md` ×2 (step 8) (ref: AC7, Risk Register row 3, OQ2).

---

## Rollback Notes

- No DB migrations, config-schema changes, or destructive operations are introduced — this
  slice is additive code/docs edits to one workflow file and two doc files, all reversible by
  reverting the slice commit.
- Steps 2–4 are the one behavioral change: a single enclosing `else` wrap plus a new
  `if (TICKET_ARG)` arm in `phase('Query')`. Rollback = revert the wrap so the 1919–2045 scope
  stretch runs unconditionally again and drop the `TICKET_ARG` constant (step 1); the absent-arg
  sweep path is byte-for-byte unchanged, so reverting restores prior behavior exactly (ref: AC5).
- Steps 5–8 are documentation/header edits only; rollback = revert the doc edits, no runtime impact.
