# Design — qrspi-batch: deterministic within-phase ticket ordering by createdAt

**Ticket:** RUS-71
**Research basis:** research.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** draft

## Current State

The `qrspi-batch` workflow fans out one `agent()` per status (via `parallel`), and each
worker is instructed to call `mcp__linear__list_issues` with exactly four arguments —
`state`, `assignee: "me"`, `limit: 250`, and conditionally `project` — passing **no
`orderBy` / sort argument** (ref: Q1). Each worker returns every ticket as `{ id, title,
status }` and "Nothing else", so `createdAt` is neither requested from Linear nor returned
to the script (ref: Q1). `TICKETS_SCHEMA` declares each ticket with `required`
`['id','title','status']` and properties for exactly those three string fields;
`createdAt` is not present, and the schema does not set `additionalProperties: false`
(ref: Q2). The fields actually read downstream are `t.id`, `t.status`, and `t.title`, all
strings — `createdAt` is not part of the in-script ticket object today (ref: Q4).

After `parallel(...)` resolves to `batches` (one `{ tickets: [...] }` per status), a single
loop flattens all batches into one flat `tickets` array while deduplicating by `id` via a
`seen` Set — first occurrence wins, in `STATUSES` order — and **no sort is applied anywhere**
(ref: Q3, Q7). `STATUSES` is a module-level const defaulting to `['Selected','Design
Review','Plan Review','Code Review']`; its array order is the de-facto across-phase
processing order because tickets merge into `tickets` in that order during flatten (ref:
Q6). The sequential `for` loop at line 981 then consumes `tickets` strictly in array order,
so processing order equals final array order (ref: Q3).

There is no ticket-object comparator: the only `.sort()` in the file is a lexicographic
string sort on ticket-ID strings in the reconciliation path, not reusable for a `createdAt`
object sort and itself mis-ordering numeric suffixes (ref: Q5, plus Inconsistencies). The
flatten loop guards the batch object (`if (!b) continue`) but not `b.tickets`; per-ticket
field reads tolerate `undefined` values without throwing, so a naive `new Date(t.createdAt)`
sort would silently mis-order missing values rather than throw (ref: Q8). `PROJECT` defaults
to undefined ⇒ all projects/all teams, so the queue can legitimately mix team prefixes,
making any ID-suffix-based ordering team-unsafe; `createdAt` is the cross-team-safe key, with
`id` only a within-prefix tie-break (ref: Q9, Q10). There is no JS test harness; pure logic
is verified by Python `_test.py` siblings or by reasoning + manual e2e, and orchestration is
verified by a real `/qrspi-batch` run observing `log()` output (ref: Q11, Q12, Q13).

## Desired End State

The batch processes tickets within each phase group in creation order (FIFO, oldest first),
deterministically and reproducibly across runs, while the phase grouping and across-phase
order are unchanged. Mapping each acceptance criterion to system behavior:

- **AC1 — fetch `createdAt`:** The Query-phase prompt and `TICKETS_SCHEMA` both request and
  permit `createdAt` per ticket, so the in-script ticket object carries `t.createdAt`
  (ref: Q1, Q2). (An `orderBy` at query time is the rejected alternative — see Decision 1.)
- **AC2 — within-group `createdAt` ascending, deterministic ties:** After flatten+dedup,
  tickets are ordered by `createdAt` ascending, with `id` as the deterministic tie-break
  (ref: Q3, Q9).
- **AC3 — phase grouping/order unchanged:** `STATUSES` is untouched; the sort is applied
  per-status-group, preserving the across-phase order `STATUSES` produces (ref: Q6).
- **AC4 — dedup still works:** The existing `seen`-Set dedup runs before the sort, so a
  ticket appearing in two status batches is processed once (ref: Q7).
- **AC5 — missing/unparseable `createdAt` sorts last, no throw:** The comparator tolerates
  absent or unparseable `createdAt` by sorting such tickets last via an explicit fallback,
  never throwing (ref: Q8).
- **AC6 — comparator verified:** The comparator's pure logic is verified per repo convention
  (Python `_test.py` sibling if factored out, else reasoning + manual e2e), and one batch run
  is observed via the "Found …" log line and `[i/total]` progression (ref: Q11, Q12, Q13).

## Delta

**Modified file:** `.claude/workflows/qrspi-batch.js`, plus a **new** `scripts/qrspi_*` Python
helper and its `_test.py` sibling for the comparator (Decision 4 Option B — follows the repo's
established tested-Python pattern).

1. **Prompt (Query fan-out, ~lines 944-956):** add `createdAt` to the requested fields and
   relax the "Nothing else" instruction to include `createdAt` — e.g. return
   `{ id, title, status, createdAt }` (ref: Q1).
2. **`TICKETS_SCHEMA` (~lines 81-98):** add `createdAt: { type: 'string' }` to the per-ticket
   `properties` and to `required` so validation guarantees its presence (ref: Q2). `createdAt`
   IS required (reviewer-confirmed, OQ2 RESOLVED): validation fails fast on omission; AC5's
   missing-value tolerance remains as defense-in-depth for the unparseable-value path, not as a
   reason to leave the field optional.
3. **New comparator + sort (insertion point: immediately after the flatten loop, after line
   967, before the `log("Found …")` at line 969):** introduce a `byCreatedAt` comparator and
   apply it to group the assembled `tickets` array by status order, sorting within each group
   by `createdAt` ascending with `id` tie-break (ref: Q3, Q6). This placement runs after
   dedup, so order of operations is flatten → dedup → sort (ref: Q7).
4. **No change to** `STATUSES`, the reconciliation `.sort()` (line 904), the dedup `seen`
   logic, or the downstream processing loop — they consume `tickets` in array order, so the
   sort alone changes processing order (ref: Q3, Q5, Q6).
5. **Verification artifacts:** a new `scripts/qrspi_*` Python helper carrying the pure comparator,
   with a `scripts/qrspi_*_test.py` sibling covering ascending order, missing/unparseable-last, and
   the `id` tie-break; the JS workflow shells out to it (the established helper pattern). Manual e2e
   (the "Found …" line + `[i/total]` progression) is the integration check on top (Decision 4, ref: Q11).

## Pattern Decisions

### Decision 1: How to obtain creation order — fetch `createdAt` vs. query-time `orderBy`

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Fetch `createdAt` per ticket (prompt + schema) and sort in-script | Deterministic regardless of Linear default order; one global sort across merged batches; tie-break controllable; visible in logs | Two-place change (prompt + schema); depends on Linear `createdAt` wire shape (external, NOT FOUND in repo) |
| B | Pass `orderBy: createdAt` to `list_issues` per status | No schema change; less code | Each status batch is independently ordered, so the merged+deduped array is NOT globally `createdAt`-ordered across statuses; cannot tie-break or tolerate missing values in-script; relies on undocumented MCP `orderBy` support |

**Recommendation:** Option A
**Rationale:** Tickets are drawn from multiple status batches and merged; a per-query
`orderBy` cannot produce a global within-group order after the cross-batch dedup, and the
research explicitly identifies the post-flatten array as the only correct insertion point for
a global sort (ref: Q3). Option A also keeps tie-breaking and missing-value tolerance under
the script's control (ref: Q8, Q9). It follows the established "schema + prompt agree" pattern
for worker returns (ref: Q2).
**NEW PATTERN?** No — extends the existing two-place (prompt + `TICKETS_SCHEMA`) worker-return
contract (ref: Q1, Q2).

### Decision 2: Preserve phase grouping while sorting — group-then-sort vs. global sort

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Stable-partition `tickets` by `status` in `STATUSES` order, sort each partition by `createdAt`, concatenate | Across-phase order provably unchanged (AC3); within-group FIFO exact | Slightly more code than one `.sort()` |
| B | Single global `.sort()` by `createdAt` over the whole array | Minimal code | Reorders ACROSS phase groups — violates AC3, which requires phase grouping/order unchanged |

**Recommendation:** Option A
**Rationale:** A global sort would reorder across the `STATUSES` groups, and the ticket
explicitly requires phase grouping and across-phase order to stay exactly as-is (ref: Q6).
Partitioning by `STATUSES` order then sorting each partition is the only option that satisfies
AC3 while delivering within-group FIFO.
**NEW PATTERN?** No — reuses `STATUSES` as the grouping key it already implicitly is (ref: Q6).

### Decision 3: Tie-break and missing-value handling in the comparator

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Primary `createdAt` ascending; missing/unparseable sorts last; tie-break on numeric suffix of `id` | Deterministic, team-safe primary key; cross-team-safe; never throws (AC5) | Numeric-suffix parse of `id` needed for correct ties |
| B | Primary `createdAt`; tie-break on lexicographic `id` | Simpler | Lexicographic `id` mis-orders `RUS-7` vs `RUS-71`; only an issue within a prefix, but still non-creation order on ties |

**Recommendation:** Option A
**Rationale:** `createdAt` is the only cross-team-safe creation key (the batch can mix team
prefixes), and `id` is a within-prefix tie-break only (ref: Q9, Q10). Lexicographic `id`
compare mis-orders numeric suffixes (ref: Inconsistencies). A missing-value fallback to "last"
is mandated by AC5 and required because field reads tolerate `undefined` rather than throw
(ref: Q8).
**NEW PATTERN?** Yes — there is no existing ticket-object comparator; the one `.sort()` in the
file is an unrelated lexicographic string sort and is not a usable precedent (ref: Q5). The new
pattern is justified because no existing comparator handles object fields, `createdAt`, or
missing-value tolerance.

### Decision 4: Where the comparator's pure logic lives and how it is verified

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Keep comparator inline in `qrspi-batch.js`; verify by reasoning + manual e2e | No new file; matches existing in-file JS logic (dedup) that has no unit test | No automated regression guard; cannot run under plain Node (ref: Q12); does NOT follow the repo's established tested-Python-helper pattern; conflicts with the TDD directive |
| B | Factor pure comparator into a `scripts/qrspi_*` Python helper with a `_test.py` sibling | Follows the repo's established tested-Python convention (12 such `scripts/qrspi_*_test.py` pairs) and the TDD directive; guards the comparator's branch-heavy logic (missing-value, tie-break) | Crosses a JS→Python boundary — but this is the same shell-out pattern already used for `qrspi_resolve.py`/`qrspi_persist.py`/`qrspi_pr_body.py` |

**Recommendation:** Option B
**Rationale:** The repo's established pattern for pure logic is a `scripts/qrspi_*` Python helper
with a `_test.py` sibling — there are 12 such tested pairs (`scripts/qrspi_*_test.py`), and CLAUDE.md
states it as a convention ("All of the above have stdlib-only unit tests as `_test.py` siblings").
The user's TDD directive ("a coding task is never complete without tests that verify it works") makes
the automated regression guard a requirement, not a nice-to-have. The comparator is exactly the kind
of pure, branch-heavy logic (ascending `createdAt`, missing/unparseable sorts last, numeric-suffix
`id` tie-break — Decision 3) that the Python `_test.py` convention exists to guard; verifying it by
"reasoning + manual e2e" alone would leave the trickiest paths (AC5 missing-value tolerance, tie-break
correctness) untested. The JS workflow shells out to the helper exactly as it already shells out to
`qrspi_resolve.py`, `qrspi_persist.py`, `qrspi_pr_body.py`, etc., so the JS→Python boundary is itself
the established orchestration pattern, not new cost. Manual e2e (the "Found …" line + `[i/total]`
progression, ref: Q13) remains as an integration check on top of the unit tests.
**NEW PATTERN?** No — a `scripts/qrspi_*` Python helper with a `_test.py` sibling, invoked from the
JS workflow, is the established pattern (12 existing pairs; CLAUDE.md convention; ref: Q11).

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Linear `createdAt` wire shape differs from assumed ISO-8601 string (external contract, NOT FOUND in repo) | med | med | Confirm shape against a live `list_issues` response before finalizing; comparator parses defensively and falls back to "last" on unparseable values (ref: Q4, Q8) |
| Worker returns omit `createdAt` despite prompt+schema (weak model, schema lacks `additionalProperties:false`) | low | med | Make `createdAt` required in `TICKETS_SCHEMA` so validation fails fast; comparator still tolerates missing values per AC5 (ref: Q2, Q8) |
| Comparator inadvertently reorders across phase groups, violating AC3 | low | high | Use group-then-sort (Decision 2); verify the "Found …" log preserves `STATUSES` group boundaries in a manual e2e run (ref: Q6, Q13) |
| Comparator regresses without an automated guard | low | med | Decision 4 Option B: a `scripts/qrspi_*_test.py` sibling unit-tests the comparator (ascending, missing-last, tie-break) per the repo's established tested-Python pattern; manual e2e is the integration check on top (ref: Q11) |
| Missing-value `createdAt` sort silently mis-orders instead of throwing | low | med | Explicit fallback sorting absent/unparseable `createdAt` last; assert behavior in the e2e observation (ref: Q8) |

## Open Questions

- OQ1: What is the exact wire representation of `createdAt` from the `linear` MCP
  `list_issues` response (ISO-8601 string assumed but NOT FOUND in repo)? This determines the
  comparator's parse strategy (ref: Q4).
- OQ2: RESOLVED (reviewer: "yes required"). `createdAt` IS `required` in `TICKETS_SCHEMA` —
  validation fails fast on omission (the strict-validation arm). AC5's missing-value tolerance
  is retained as defense-in-depth for unparseable values, not as grounds for an optional field
  (ref: Q2, Q8).
- OQ3: RESOLVED (reviewer: "follow existing pattern"). The comparator follows the repo's established
  pattern — a `scripts/qrspi_*` Python helper with a `_test.py` sibling, invoked from the JS workflow
  (Decision 4 Option B). The TDD directive and the 12 existing tested pairs settle this in favor of
  the tested helper over inline JS + manual e2e (ref: Q11).
- OQ4: RESOLVED (reviewer: "fine, stay with first batch wins"). When the same ticket legitimately
  appears under two statuses, the existing "first batch wins" dedup assigns it the earlier
  `STATUSES` group, and that group is retained for the now-sorted queue (the dedup runs before the
  sort, so the ticket sorts within its first-seen group). No change to the `seen`-Set dedup is made
  (ref: Q7).
