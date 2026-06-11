# Ticket: PAY-733

## Title

Migrate active subscriptions from the legacy billing table to the new billing schema

## Description

Subscriptions are currently split across the legacy `subscriptions_v1` table
and the new `billing_subscriptions` schema. New sign-ups already write to the
new schema, but every subscription created before the cutover still lives only
in the legacy table, so billing reads must check both. We need a one-time,
resumable backfill that copies the legacy active subscriptions into the new
schema without double-charging anyone or dropping a renewal.

## Acceptance Criteria

- [ ] All active legacy subscriptions are copied into billing_subscriptions
- [ ] The migration is idempotent and resumable after an interruption
- [ ] No subscription is charged twice during or after the migration
- [ ] Migrated rows preserve the original next_renewal_at timestamp

## Constraints

- Must run against the live database without taking billing offline
- Must not modify the legacy subscriptions_v1 table (read-only source)

## Out of Scope

- Decommissioning the legacy subscriptions_v1 table (a later ticket)
- Migrating cancelled or expired subscriptions
