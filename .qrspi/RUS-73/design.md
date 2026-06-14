# Design — qrspi-batch: single-ticket scope (input.ticket)

**Ticket:** RUS-73
**Research basis:** research.md @ 2026-06-13T00:00:00Z
**Generated:** 2026-06-13T00:00:00Z
**Status:** draft

## Current State

The `qrspi-batch` Query phase is one contiguous linear stretch in `.claude/workflows/qrspi-batch.js`: resolve project scope, log scope, fail-loud project validation, sweep via `mcp__linear__list_issues`, flatten+dedup into a `let tickets` array, order via `qrspi_order_tickets.py`, then an empty-check short-circuit followed by the per-ticket loop (ref: Q1). The sweep attaches exactly four required string fields per element — `id`, `title`, `status`, `createdAt` — enforced by `TICKETS_SCHEMA`, which is attached only to the sweep agents and never to any single-fetch path (ref: Q2).

Scope arguments are normalized to top-of-file constants before `phase('Query')`: `ALL_PROJECTS = input?.allProjects === true` and `PROJECT_ARG` (trimmed, blank→undefined) (ref: Q3). The precedence chain `input.allProjects > input.project > config linearProject > "QRSPI"` is implemented **inline** in the Query phase (lines 1927–1955), with the `"QRSPI"` default supplied by `qrspi_config.py`; a non-ok config read is a hard `throw`, never a silent fall-through (ref: Q4). This precedence chain was **never extracted into a JS-side or dedicated scope-precedence unit test** — only the config rung (`select_value`/`read_config`) is unit-tested (`qrspi_config_test.py`); the `allProjects`/`project`/trim selection branch is JS-inline and has no automated test (ref: Q11). That is the established RUS-66 precedent: a trivial precedence conditional lives JS-inline and is verified by the resolver's existing tests plus a manual e2e, not by a new pure-logic helper.

The entry gate (assigned + Selected) is enforced **purely inside the resolver** (`qrspi_resolve_state.py::resolve`), independent of how a ticket entered the array; the RESOLVE worker re-reads live status + assignee from `mcp__linear__get_issue` per ticket, so the sweep filter is only a candidate selector and never gates (ref: Q5). Each loop iteration pushes one `{ ticketId, action, summary, ...}` result; the workflow returns `{ ticketsProcessed, results, reconciliation }`, and a per-ticket try/catch turns one ticket's throw into an `errored` result without aborting the run (ref: Q6).

A concrete project scope that matches no Linear project triggers an **unguarded** `throw` from the Query phase — fail-loud, aborting the whole run — a deliberately different posture from the guarded loop body (ref: Q7). Both `entry_blocked` and `wait` are legal resolver actions that dispatch to `skip()` and are recorded as results, never silently dropped (ref: Q8). Scope-mode selection is currently a single axis (`ALL_PROJECTS` vs concrete `PROJECT`) resolved in one block; everything after the order step reads only `tickets`, never scope, so `tickets` is the sole scope→loop boundary (ref: Q9).

There is **no** dedicated unit test for the JS-inline precedence chain; testable scope logic must live in a Python helper only when it is genuinely pure decision logic worth isolating — the trivial inline precedence branch was deliberately not extracted (ref: Q11, Q10). Scope mode is logged once at line 1957 and queue size once at line 2047; `log`/`phase` are runtime-injected globals (ref: Q12). Four-to-five user-facing surfaces restate the precedence string with no single source of truth: the `meta` Query detail, the `--- args ---` header comment, `.claude/CLAUDE.md`, and `README.md` (two sites). `qrspi-batch` is a **workflow** (`.claude/workflows/qrspi-batch.js`), not a skill — there is no `qrspi-batch` skill and no SKILL.md for it (none under `.claude/skills/`, and `.claude/CLAUDE.md` itself describes "The `qrspi-batch` workflow"); it is documented only as a workflow (ref: Q13).

## Desired End State

- **AC1** — When `input.ticket` is present, the Query phase fetches that one issue's `{id,title,status,createdAt}` via `mcp__linear__get_issue`, sets `tickets = [that one]`, and skips project-scope resolution, the `list_issues` sweep, and the ordering step (ref: Q1, Q9).
- **AC2** — The single ticket flows through the **identical** existing loop body (`resolveTicket → ensureRestacked → dispatch → critics → finalize → reconcile`), producing the same `{ ticketsProcessed, results, reconciliation }` envelope a one-ticket batch run produces (ref: Q6).
- **AC3** — Precedence becomes `input.ticket > input.allProjects > input.project > config linearProject > "QRSPI"`, as the single source of scope truth — one branch point, no second precedence path (ref: Q9, Q4).
- **AC4** — A gated single-ticket target is safe: the resolver still enforces the entry gate and surfaces `entry_blocked`/`wait` as recorded results, because `resolveTicket` re-fetches and re-decides regardless of entry path (ref: Q5, Q8).
- **AC5** — When `input.ticket` is absent, the sweep path runs byte-for-byte unchanged, guaranteed by wrapping the scope/sweep/order stretch in a single `else` branch that touches nothing downstream of `tickets` (ref: Q9).
- **AC6** — Any pure decision logic introduced has a stdlib-only `_test.py` sibling per the `scripts/qrspi_*_test.py` convention; orchestration is verified by a manual end-to-end run. **This feature introduces no such pure decision logic** (see Decision 2): the single-ticket selection is a one-line `if (TICKET_ARG) { fetch } else { sweep }` truthiness branch on one already-normalized top-of-file constant — not "pure decision logic" in the sense AC6 targets — so AC6 is satisfied by the resolver's existing tests plus the mandated manual e2e, exactly as the RUS-66 inline precedence was (ref: Q10, Q11).
- **AC7** — Product documentation is updated to add `input.ticket` (purpose, precedence position, concrete example) to every scoping surface (ref: Q13).

## Delta

**Modified — `.claude/workflows/qrspi-batch.js`:**
- Add a normalized top-of-file constant `TICKET_ARG` near line 139, mirroring the trim/normalize discipline of `PROJECT_ARG` (ref: Q3).
- Add the `--- args ---` header entry for `ticket?` and update the precedence comment (lines 109–147) (ref: Q3, Q13).
- Update the `meta` Query-phase `detail` string (line 6) to include `input.ticket` at the head of the precedence (ref: Q13).
- At the top of `phase('Query')`, introduce **one** branch point: `if (TICKET_ARG) { ...single fetch -> tickets = [el]... } else { ...existing scope-resolve + validate + sweep + order (1919–2045)... }`. The single-fetch arm spawns one `mcp__linear__get_issue` agent and builds a four-field element; on not-found it `throw`s (fail-loud, matching the scope-block convention) (ref: Q1, Q7, Q9).
- Add a scope-mode `log()` line for the single-ticket path at the 1957 position (e.g. `Project scope: single ticket (input.ticket=RUS-XX)`) (ref: Q12).

**No new Python helper, no new `_test.py` (see Decision 2).** The single-ticket selection is a trivial JS-inline `if`, matching the existing RUS-66 precedence treatment; no `scripts/qrspi_*.py` module or `_test.py` sibling is added by this feature (ref: Q10, Q11).

**Modified docs — `.claude/CLAUDE.md` (lines 26–31), `README.md` (lines 60, 164):** add `input.ticket` to the precedence string and a concrete `Workflow({ name: "qrspi-batch", args: { ticket: "RUS-58" } })` example (ref: Q13).

## Pattern Decisions

### Decision 1: How to fetch the single ticket element

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Inline `agent()` calling `mcp__linear__get_issue`, validated against `TICKETS_SCHEMA`, mirroring the sweep agent | Reuses the existing JS↔Linear worker pattern; one schema validates both paths; no new file | `get_issue`'s byte-compatibility for the 4-field record is unproven in-repo (ref: Q2) — needs the worker prompt to pin `status`/`createdAt` explicitly |
| B | Shell out to a new Python helper that calls Linear | — | Python helpers here are self-locating and pure; they do **not** call Linear (that is the JS-agent's job) — this breaks the JS↔Python seam (ref: Discovered Patterns) |

**Recommendation:** Option A.
**Rationale:** The Discovered Patterns section establishes that every Linear interaction is delegated to a JS worker `agent()`, and `mcp__linear__get_issue` is already invoked this way by the RESOLVE worker (ref: Q2, Q5). Attaching `TICKETS_SCHEMA` to the single-fetch agent gives the single path the same four-field guarantee the sweep enjoys today, closing the unproven-compatibility gap (ref: Q2).
**NEW PATTERN?** No — reuses the existing inline-`agent()` + `TICKETS_SCHEMA` + `extractJsonObject` seam.

### Decision 2: Where the scope-mode branch logic lives (and whether it is unit-tested)

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep the `if (TICKET_ARG)` branch JS-inline only, exactly like the existing RUS-66 precedence; no new helper, no new test | Matches the established RUS-66 precedent exactly (a trivial precedence conditional left JS-inline, never unit-tested, ref: Q11); minimal change; no worker round-trip; nothing to drift | The trivial branch carries no isolated unit test — but it is not "pure decision logic" in AC6's sense, and the resolver's existing tests + the mandated manual e2e already cover the only behavior that matters (the right `tickets` array reaches the loop) |
| B | Extract a pure `qrspi_scope_mode.py` selector (single/all/project/config) + `_test.py`, JS shells out via a worker | Would give the classification an isolated unit test | A new Python module + `_test.py` + worker round-trip + parse-envelope path is **disproportionate to a one-line conditional**: the helper "only classifies" while the JS `if` is "still the thing that acts" (pure overhead); contradicts the RUS-66 precedent (Q11) that the analogous precedence branch was left JS-inline; over-builds against the project's one-resolver/one-persist minimalism |

**Recommendation:** Option A — keep the `if (TICKET_ARG) { fetch } else { sweep }` branch JS-inline; introduce **no** `qrspi_scope_mode.py` and **no** `_test.py` sibling.
**Rationale:** What the feature adds is a single truthiness branch on one already-normalized top-of-file constant (`TICKET_ARG`), selecting *which array-construction path runs* — it is not a precedence *computation* with multiple competing rungs, and the actual decision logic (the entry gate, the action choice) already lives in the tested resolver and is re-run per ticket regardless of entry path (ref: Q5). This is precisely the RUS-66 shape: the `allProjects > project > config > "QRSPI"` precedence is itself JS-inline and was deliberately **not** extracted into a pure helper or unit-tested (only the config rung is) (ref: Q11). Following that precedent, the trivial single-ticket branch does **not** constitute "pure decision logic introduced" under AC6; AC6 is satisfied by the resolver's existing test suite plus the mandated manual end-to-end run that confirms a one-element `tickets` array reaches the unchanged loop. Option B's helper would be pure overhead — it would only classify while the JS `if` still acts — and would add a worker round-trip and an envelope-parse path disproportionate to a one-line conditional, against this project's explicit one-resolver/one-persist/one-decision-core minimalism (ref: Constraints, Q11).
**OQ1 resolution:** OQ1 is resolved here in favor of **no new helper** — the inline `if` is trivial enough that AC6 is met without `qrspi_scope_mode.py`. Decision 2 Option B is **dropped**, not deferred.
**NEW PATTERN?** No — applies the existing RUS-66 JS-inline-trivial-branch precedent unchanged.

### Decision 3: Fail-loud posture for a not-found single ticket

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | `throw` from the single-fetch arm (uncaught by Query), aborting the run | Matches the scope-block fail-loud convention (project-mismatch throws, ref: Q7); operator sees the abort immediately | Aborts rather than producing an empty queue — but that is the intended posture |
| B | Produce an empty `tickets` array and fall into the existing empty short-circuit | Reuses the empty-check path | Silently swallows a bad ticket id — violates the fail-loud convention the Query scope block establishes (ref: Q7) |

**Recommendation:** Option A.
**Rationale:** The Query scope block deliberately uses unguarded `throw` for unrecoverable scope errors (project-mismatch), distinct from the guarded per-ticket loop (ref: Q7, Discovered Patterns). A bad `input.ticket` is the single-ticket analogue of a project mismatch and should fail loud the same way (ref: Q7).
**NEW PATTERN?** No — applies the existing Query-phase fail-loud convention.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `get_issue` does not return a byte-compatible 4-field `{id,title,status,createdAt}` record (unproven in-repo, MCP shape external) (ref: Q2) | med | med | Attach `TICKETS_SCHEMA` to the single-fetch agent and pin `status`/`createdAt` in the worker prompt; the order helper tolerates a missing `createdAt` (sorts last) so a single element never breaks (ref: Q2) |
| Absent-`input.ticket` path drifts from byte-for-byte sweep behavior (AC5) | low | high | Wrap scope/sweep/order in one enclosing `else` touching only the 1919–2045 stretch (single branch point, ref: Q9); verify with a manual batch e2e run that the sweep queue is unchanged |
| Precedence string drifts across the 4–5 documentation surfaces when `input.ticket` is added (ref: Q13, Inconsistencies) | med | low | Edit all surfaces in lockstep (meta detail, args header, CLAUDE.md, README ×2) in the same slice; enumerate them in the plan as a checklist |

## Open Questions

- OQ1: **Resolved (see Decision 2).** The single-ticket branch (`if (TICKET_ARG) { fetch } else { sweep }`) is a trivial truthiness conditional on one normalized constant, not "pure decision logic" under AC6 — so **no** `qrspi_scope_mode.py` is required and Decision 2 Option B is dropped. AC6 is satisfied by the resolver's existing tests plus the mandated manual e2e, matching the RUS-66 precedence which is itself JS-inline and never unit-tested (ref: Q11).
- OQ2: **Resolved (reviewer).** There is **no** `qrspi-batch` SKILL.md doc surface to update: `qrspi-batch` is a **workflow** (`.claude/workflows/qrspi-batch.js`), not a skill (no `qrspi-batch` entry under `.claude/skills/`, and `.claude/CLAUDE.md` calls it "The `qrspi-batch` workflow"). AC7's "every scoping surface" therefore means the four real in-repo surfaces — the `meta` Query detail, the `--- args ---` header comment, `.claude/CLAUDE.md`, and `README.md` (two sites) — all of which document it as a workflow; no SKILL.md is created, referenced, or tracked as a follow-up (ref: Q13).
- OQ3: **Resolved (reviewer).** `input.ticket` is strictly a **single** ticket id — not an array / "named subset" — per reviewer direction and the ticket's "one named ticket" framing. This confirms the design's existing single-ticket shape (`mcp__linear__get_issue` for one issue → `tickets = [that one]`, AC1) with no multi-id precedence/fetch path to build; a future named-subset run would be a separate feature.
