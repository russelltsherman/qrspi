# Design — Migrate active subscriptions from the legacy billing table to the new billing schema

**Ticket:** PAY-733
**Research basis:** research_billing_migration.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

## Current State

Billing reads go through a single accessor, `Subscriptions.active(userId)`, which queries `billing_subscriptions` first and falls back to `subscriptions_v1` only when the new-schema row is absent; that fallback is the one place legacy rows are read (ref: Q1). The two tables differ in shape: legacy carries `plan, status, renew_at` while the new schema carries `plan_code, state, next_renewal_at, source_legacy_id`, with the legacy `plan` string mapping to `plan_code` and `source_legacy_id` left null for natively-created rows (ref: Q2).

Renewal timestamps are the delicate field: legacy `renew_at` is a tz-naive `timestamp` while new `next_renewal_at` is `timestamptz`, both stored UTC, so a copy preserves the instant only if it neither reads nor writes with a local-tz offset (ref: Q3). The identity link across tables is `billing_subscriptions.source_legacy_id`, which holds the originating `subscriptions_v1.id` and is uniquely indexed, making "already migrated" a checkable, DB-enforced condition (ref: Q4).

Resumability already exists as a primitive: `runBatch` iterates a table in ascending id order and persists the last processed id to `job_cursors` after each chunk, so an interrupted run resumes from the watermark (ref: Q5). Duplicate-insert protection is likewise in place — the unique index on `source_legacy_id` lets the job use conflict-ignore semantics so re-runs skip copied rows without erroring (ref: Q6), and the cursor watermark is written in the same transaction as the chunk so progress and data stay consistent on a crash (ref: Q7).

Charging is centralized: `RenewalScheduler` charges due subscriptions via the same `Subscriptions.active(userId)` accessor, so once a legacy row is migrated the new-schema row wins and the scheduler reads each user exactly once (ref: Q8). Even during the overlap window, `charge()` sends an idempotency key of `renewal:{user}:{period}` so the gateway collapses any repeat attempt for the same user and period into a single charge (ref: Q9).

Test scaffolding supports the invariants we must protect: billing tests run against a transactional test DB with `seedLegacySub`/`seedBillingSub` helpers and a stubbed gateway (ref: Q10), and both seed helpers exist so a test can seed a legacy row, run the migration, run the scheduler, and assert exactly one charge for that user (ref: Q11). Observability is partial: `runBatch` logs per-chunk summaries and increments the shared `batch.*` metrics keyed by job `key`, but there is no migration-specific counter (ref: Q12); operators can confirm safety mid-run by counting `gateway.dedup` log events, which signal prevented double charges rather than errors (ref: Q13).

## Desired End State

A one-time, resumable migration job copies every active `subscriptions_v1` row into `billing_subscriptions`, runs against the live database, and leaves charging behavior unchanged. Each acceptance criterion maps to a concrete behavior:

- "all active legacy subscriptions copied" → the job selects `subscriptions_v1` rows with `status = 'active'`, maps `plan → plan_code` and `renew_at → next_renewal_at`, sets `source_legacy_id` to the legacy id, and inserts into `billing_subscriptions` (ref: Q2, Q4).
- "idempotent and resumable" → the job runs on `runBatch` with a `job_cursors` watermark and `onConflict('source_legacy_id').ignore()`, so a re-run resumes from the cursor and skips already-copied rows (ref: Q5, Q6, Q7).
- "no subscription charged twice" → reads and renewals both flow through `Subscriptions.active`, which prefers the migrated row, and the gateway idempotency key collapses any overlap-window repeat (ref: Q8, Q9).
- "preserve next_renewal_at" → the copy reads and writes the timestamp as UTC with no local offset, mapping tz-naive `renew_at` to `timestamptz next_renewal_at` without coercion (ref: Q3).

## Delta

- New file `src/jobs/migrate_billing.js` — the migration job: selects active legacy rows, maps fields via `PLAN_CODES`, sets `source_legacy_id`, and inserts through `runBatch` with conflict-ignore (ref: Q2, Q5, Q6).
- New entry in the job registry — registers `migrate_billing` with a stable `cursorKey` so its `job_cursors` watermark is isolated from other batch jobs (ref: Q7).
- New test file `test/jobs/migrate_billing.test.js` — covers copy correctness, resumability after a simulated interruption, the no-double-charge invariant via the scheduler, and exact `next_renewal_at` preservation (ref: Q10, Q11).
- No schema change: `billing_subscriptions` and its `source_legacy_id` unique index already exist; `subscriptions_v1` is read-only per the constraint (ref: Q4, Q6).

## Pattern Decisions

### Decision 1: Reuse `runBatch` vs. a bespoke migration loop

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Run the copy through the existing `runBatch` + `job_cursors` primitive | Crash-safe resumability for free; matches established batch pattern; minimal new code | Inherits the shared `batch.*` metric namespace, so migration counts need a `key` filter |
| B | Write a dedicated migration loop with its own cursor and metrics | Migration-specific metrics out of the box | Re-implements a tested primitive; more surface to get wrong on crash-consistency |

**Recommendation:** Option A
**Rationale:** `runBatch` already provides ascending-id, watermark-resumable, conflict-ignore batch processing that exactly matches the idempotency and resumability criteria, so reusing it is both smaller and safer than re-deriving the same guarantees (ref: Q5, Q6, Q7).
**NEW PATTERN?** No — it composes the existing batch runner, the `source_legacy_id` unique index, and the single `active` accessor.

### Decision 2: How to guarantee the no-double-charge invariant during the overlap window

| Option | Approach | Pros | Cons |
|--------|----------|------|------|
| A | Rely on the existing `active`-prefers-new read plus the gateway idempotency key | Zero new code; defense in depth (row dedup + charge dedup) | Correctness depends on the period component of the idempotency key staying stable across the window |
| B | Pause `RenewalScheduler` for the migration duration | Eliminates any concurrent-charge possibility | Requires taking part of billing offline, violating the live-run constraint |

**Recommendation:** Option A
**Rationale:** The accessor already routes each user to exactly one row and the gateway already collapses repeat keys, so the invariant holds without pausing billing, satisfying the live-run constraint (ref: Q8, Q9).
**NEW PATTERN?** No — both the single-accessor read and the idempotency-key dedup are pre-existing behaviors the migration leans on rather than introduces.

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| A local-tz offset is applied while copying `renew_at` into `next_renewal_at`, shifting renewal instants (ref: Q3) | med | high | Read and write the timestamp as UTC explicitly; add a test asserting the migrated `next_renewal_at` equals the source instant to the second |
| Migration row counts are indistinguishable from other batch jobs in the shared `batch.*` namespace (ref: Q12) | med | low | Use a distinct, stable `key`/`cursorKey` so the migration's counts and cursor are filterable and isolated |
| A crash mid-chunk leaves the cursor and inserted rows inconsistent | low | high | Keep the cursor write in the same transaction as the chunk insert, as `runBatch` already does (ref: Q7) |

## Open Questions

- OQ1: Should a migration-specific metric be added now to count migrated rows distinctly, or is filtering the shared `batch.*` namespace by `key` sufficient for this one-time job (ref: Q12)?
- OQ2: For the overlap window, what `period` granularity makes the `renewal:{user}:{period}` idempotency key safest against a renewal that falls exactly on the migration boundary (ref: Q9)?
