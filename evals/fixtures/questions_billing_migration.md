# Questions — Migrate active subscriptions from the legacy billing table to the new billing schema

**Ticket:** PAY-733
**Generated:** 2026-06-11T00:00:00Z
**Status:** approved

## Data Flow

- Q1: How does an active subscription record travel from `subscriptions_v1` into a billing read today, and where is the dual-read across legacy and new schemas performed?
  **Target:** the billing read path and the accessor that consults both `subscriptions_v1` and `billing_subscriptions`
- Q2: What is the field-by-field shape of a `subscriptions_v1` row versus a `billing_subscriptions` row, and which legacy columns have no direct new-schema equivalent?
  **Target:** the two schema/migration definitions and any mapping helper between them

## Schema Mapping

- Q3: How is `next_renewal_at` represented in each schema, and is there any timezone or precision difference that a copy must preserve exactly?
  **Target:** the column definitions for renewal timestamps in both schemas
- Q4: What uniquely identifies "the same" subscription across the two tables so a backfill can detect an already-migrated row?
  **Target:** the natural/foreign key linking `subscriptions_v1` to `billing_subscriptions`

## Idempotency & Resumability

- Q5: Is there an existing pattern for resumable batch jobs (checkpoint/cursor) in the codebase that the migration can reuse?
  **Target:** any existing batch/backfill runner or cursor-tracking table
- Q6: How would a re-run detect rows it already copied, and is there a unique constraint preventing a duplicate insert into `billing_subscriptions`?
  **Target:** the unique constraints/indexes on `billing_subscriptions`
- Q7: Where would migration progress (last processed id or watermark) be stored so an interrupted run resumes rather than restarts?
  **Target:** the job-state or checkpoint storage used by existing jobs

## Charging Safety

- Q8: What component triggers a charge on renewal, and how does it decide which schema to read so a freshly migrated row is not charged by both paths?
  **Target:** the renewal/charge scheduler and its source-of-truth selection
- Q9: Is there an idempotency key or charge-dedup mechanism on the payment side that prevents a double charge if both schemas briefly contain the same subscription?
  **Target:** the payment gateway client and any idempotency-key handling

## Testing

- Q10: What test harness and fixtures exist for billing reads and for the renewal scheduler that a migration test could reuse?
  **Target:** the billing test directory and its subscription fixtures
- Q11: Is there a way to seed both legacy and new-schema rows in a test to assert the no-double-charge invariant?
  **Target:** the test seed helpers for `subscriptions_v1` and `billing_subscriptions`

## Observability

- Q12: How are migration-style jobs logged and counted today, and what metric would surface migrated-row counts and failures?
  **Target:** the job logger and metrics emitter used by existing batch jobs
- Q13: How would an operator confirm mid-run that no subscription is being charged twice?
  **Target:** the charge-attempt logging and any dedup/conflict counter
