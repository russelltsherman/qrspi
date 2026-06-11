# Research — Codebase Map

**Questions source:** questions_billing_migration.md @ 2026-06-11T00:00:00Z
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

> Scenario: PAY-733 — Migrate active subscriptions from the legacy billing
> table to the new billing schema. Findings are factual observations of the
> (fictional reference) codebase the eval harness models; every answer is
> backed by a `file:line` citation.

## Q1: How does an active subscription record travel from `subscriptions_v1` into a billing read today, and where is the dual-read across legacy and new schemas performed?

**Answer:** Billing reads call `Subscriptions.active(userId)`, which queries `billing_subscriptions` first and falls back to `subscriptions_v1` when the new-schema row is absent. The fallback is the only place legacy rows are read.
**Evidence:**

```
const row = await db('billing_subscriptions').where({ user_id }).first()
return row ?? legacyActive(user_id)
```

— `src/models/subscriptions.js:34`
**Dependencies:** `src/db/knex.js`, `src/models/legacy_subscriptions.js` (legacyActive)
**Implicit contracts:** a new-schema row always wins over a legacy row; callers never read `subscriptions_v1` directly.

## Q2: What is the field-by-field shape of a `subscriptions_v1` row versus a `billing_subscriptions` row, and which legacy columns have no direct new-schema equivalent?

**Answer:** `subscriptions_v1` has `id, user_id, plan, status, renew_at, created_at`; `billing_subscriptions` has `id, user_id, plan_code, state, next_renewal_at, source_legacy_id, created_at`. The legacy `plan` string maps to `plan_code` via `PLAN_CODES`; legacy has no `source_legacy_id` (it is populated on migration).
**Evidence:**

```
table.string('plan_code'); table.string('state'); table.integer('source_legacy_id')
```

— `migrations/20250301_billing_subscriptions.js:7`
**Dependencies:** `src/billing/plan_codes.js` (PLAN_CODES)
**Implicit contracts:** `source_legacy_id` is null for natively-created rows and set to the `subscriptions_v1.id` for migrated rows.

## Q3: How is `next_renewal_at` represented in each schema, and is there any timezone or precision difference that a copy must preserve exactly?

**Answer:** Legacy `renew_at` is a `timestamp` (no tz); new `next_renewal_at` is `timestamptz`. Both are stored UTC, so a copy preserves the instant if it is read and written without local-tz coercion.
**Evidence:**

```
table.timestamp('next_renewal_at', { useTz: true }).notNullable()
```

— `migrations/20250301_billing_subscriptions.js:9`
**Dependencies:** `src/db/knex.js`
**Implicit contracts:** all renewal timestamps are UTC at rest; the migration must not apply a tz offset when copying `renew_at` into `next_renewal_at`.

## Q4: What uniquely identifies "the same" subscription across the two tables so a backfill can detect an already-migrated row?

**Answer:** `billing_subscriptions.source_legacy_id` holds the originating `subscriptions_v1.id`; a legacy row is "already migrated" iff a `billing_subscriptions` row exists with that `source_legacy_id`.
**Evidence:**

```
table.integer('source_legacy_id').unique()
```

— `migrations/20250301_billing_subscriptions.js:11`
**Dependencies:** none
**Implicit contracts:** `source_legacy_id` is unique, so a second insert for the same legacy row is rejected by the DB.

## Q5: Is there an existing pattern for resumable batch jobs (checkpoint/cursor) in the codebase that the migration can reuse?

**Answer:** Yes — `runBatch(table, fn, { cursorKey })` iterates a table in id order, persisting the last processed id to the `job_cursors` table after each chunk so a re-run resumes from the watermark.
**Evidence:**

```
await db('job_cursors').insert({ key: cursorKey, last_id }).onConflict('key').merge()
```

— `src/jobs/run_batch.js:48`
**Dependencies:** `src/db/knex.js`, `job_cursors` table
**Implicit contracts:** `runBatch` processes ids strictly ascending; the cursor is the resume watermark.

## Q6: How would a re-run detect rows it already copied, and is there a unique constraint preventing a duplicate insert into `billing_subscriptions`?

**Answer:** The unique index on `source_legacy_id` makes a duplicate insert fail; the migration uses `onConflict('source_legacy_id').ignore()` so re-runs skip already-copied rows without erroring.
**Evidence:**

```
.insert(mapped).onConflict('source_legacy_id').ignore()
```

— `src/jobs/run_batch.js:61`
**Dependencies:** `migrations/20250301_billing_subscriptions.js` (unique index)
**Implicit contracts:** idempotency is enforced at the DB layer, not in application memory, so it survives a crash mid-chunk.

## Q7: Where would migration progress (last processed id or watermark) be stored so an interrupted run resumes rather than restarts?

**Answer:** In the `job_cursors` table keyed by the job name; `runBatch` reads it on start and writes it after each committed chunk.
**Evidence:**

```
const start = (await db('job_cursors').where({ key }).first())?.last_id ?? 0
```

— `src/jobs/run_batch.js:29`
**Dependencies:** `job_cursors` table
**Implicit contracts:** the cursor is updated in the same transaction as the chunk insert, so progress and data stay consistent on a crash.

## Q8: What component triggers a charge on renewal, and how does it decide which schema to read so a freshly migrated row is not charged by both paths?

**Answer:** `RenewalScheduler` charges due subscriptions via `Subscriptions.active(userId)`, which (per Q1) prefers the new-schema row. Once a legacy row is migrated, the new-schema row wins, so the scheduler reads it exactly once per user.
**Evidence:**

```
for (const s of await Subscriptions.dueForRenewal()) await charge(s)
```

— `src/billing/renewal_scheduler.js:22`
**Dependencies:** `src/models/subscriptions.js`, `src/billing/charge.js`
**Implicit contracts:** the scheduler dedups by `user_id` because `active(userId)` returns a single row; it never iterates both tables.

## Q9: Is there an idempotency key or charge-dedup mechanism on the payment side that prevents a double charge if both schemas briefly contain the same subscription?

**Answer:** Yes — `charge()` sends an idempotency key of `renewal:{user_id}:{period}` to the gateway, so two charge attempts for the same user and billing period are collapsed into one by the provider.
**Evidence:**

```
gateway.charge(amount, { idempotencyKey: `renewal:${userId}:${period}` })
```

— `src/billing/charge.js:17`
**Dependencies:** `src/billing/gateway.js`
**Implicit contracts:** the period component makes the key stable across a migration window; the gateway treats a repeat key as a no-op returning the original charge.

## Q10: What test harness and fixtures exist for billing reads and for the renewal scheduler that a migration test could reuse?

**Answer:** Billing tests use an in-process knex against a transactional test DB with `seedLegacySub`/`seedBillingSub` helpers; the scheduler is exercised via `runScheduler()` against seeded due rows.
**Evidence:**

```
const sub = await seedLegacySub({ status: 'active', renew_at: tomorrow })
```

— `test/billing/subscriptions.test.js:19`
**Dependencies:** `test/helpers/billing_seed.js`
**Implicit contracts:** each test runs in a rolled-back transaction; no shared row state leaks between tests.

## Q11: Is there a way to seed both legacy and new-schema rows in a test to assert the no-double-charge invariant?

**Answer:** Yes — both `seedLegacySub` and `seedBillingSub` exist; a test can seed a legacy row, run the migration, then run the scheduler and assert exactly one `gateway.charge` call for that user.
**Evidence:**

```
export async function seedBillingSub(attrs) { return db('billing_subscriptions').insert(...) }
```

— `test/helpers/billing_seed.js:31`
**Dependencies:** `test/helpers/billing_seed.js`
**Implicit contracts:** the gateway is stubbed in tests so charge calls are countable.

## Q12: How are migration-style jobs logged and counted today, and what metric would surface migrated-row counts and failures?

**Answer:** `runBatch` logs a per-chunk summary via `logger.info({ event: 'batch.chunk' })` and increments `metrics.increment('batch.rows', n)`; failures bump `batch.errors`. There is no migration-specific counter yet.
**Evidence:**

```
logger.info({ event: 'batch.chunk', key, count }); metrics.increment('batch.rows', count)
```

— `src/jobs/run_batch.js:55`
**Dependencies:** `src/observability/logger.js`, `src/observability/metrics.js`
**Implicit contracts:** all batch jobs share the `batch.*` metric namespace keyed by `key`, so per-job counts come from the `key` label.

## Q13: How would an operator confirm mid-run that no subscription is being charged twice?

**Answer:** `charge()` logs every attempt with the idempotency key, and the gateway client logs `gateway.dedup` when a repeat key is collapsed; counting `gateway.dedup` for the renewal namespace shows any would-be double charges that were prevented.
**Evidence:**

```
logger.info({ event: 'gateway.dedup', idempotencyKey })
```

— `src/billing/gateway.js:40`
**Dependencies:** `src/observability/logger.js`
**Implicit contracts:** a nonzero `gateway.dedup` count is expected and safe during the migration window; it is the signal that dedup is working, not an error.

---

## Discovered Patterns

- A single accessor, `Subscriptions.active(userId)`, is the source of truth for both reads and renewals, and it prefers the new schema over legacy — so migrating a row automatically routes all future reads/charges through one path.
- Idempotency is enforced at two independent layers: the DB unique index on `source_legacy_id` (no duplicate row) and the gateway idempotency key `renewal:{user}:{period}` (no duplicate charge).
- Resumability is a reusable primitive: `runBatch` + the `job_cursors` watermark already give crash-safe, ascending-id batch processing the migration can adopt directly.

## Inconsistencies

- Legacy `renew_at` is a tz-naive `timestamp` while new `next_renewal_at` is `timestamptz`; both are documented as UTC, but nothing in the schema enforces it, so a careless copy applying a local offset would silently shift renewal instants.
- Batch metrics are emitted under the shared `batch.*` namespace keyed only by `key`, so a migration's row count is not distinguishable from other batch jobs except by the free-form `key` label — there is no dedicated migration counter.
