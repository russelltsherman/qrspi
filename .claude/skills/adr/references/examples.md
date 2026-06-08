# Worked Example ADRs

Concrete, end-to-end examples. Use these to see the format applied, including a
supersede pair that demonstrates the bidirectional-link invariant.

---

## Example 1 — A complete MADR 4.0 ADR (accepted)

```markdown
---
status: "accepted"
date: 2026-05-02
decision-makers: [platform-team]
consulted: [security, data-eng]
informed: [all-engineering]
---

# 0003. Use PostgreSQL as the primary datastore

## Status

accepted

## Date

2026-05-02

## Context and Problem Statement

The service needs a primary store for transactional order data. We require ACID
guarantees, mature operational tooling, and a managed cloud offering. Which
database should back the order service?

## Decision Drivers

- Strong transactional consistency for orders
- Managed offering on our cloud (operational cost)
- Team familiarity and hiring pool
- Rich query capability (reporting joins)

## Considered Options

- PostgreSQL (managed, e.g. RDS/Cloud SQL)
- MySQL (managed)
- DynamoDB (key-value, managed)

## Decision Outcome

Chosen option: "PostgreSQL (managed)", because it satisfies ACID and rich-query
drivers, has the strongest team familiarity, and a first-class managed offering.

### Consequences

- Good, because transactional integrity and relational reporting are native.
- Good, because the team already operates Postgres elsewhere.
- Bad, because horizontal write scaling will need future work (sharding/read replicas).
```

---

## Example 2 — A supersede pair (bidirectional links)

### Old ADR — becomes superseded

```markdown
# 0003. Use PostgreSQL as the primary datastore

## Status

superseded by ADR-0009

## Date

2026-06-01

## Context and Problem Statement

(unchanged — historical record preserved)
...
```

### New ADR — supersedes the old one

```markdown
# 0009. Move primary datastore to a distributed SQL engine

## Status

accepted

Supersedes ADR-0003

## Date

2026-06-01

## Context and Problem Statement

Order volume now exceeds single-primary write throughput on PostgreSQL (ADR-0003).
We need horizontal write scaling while keeping SQL semantics. ...
```

> The invariant: ADR-0003 gains `superseded by ADR-0009` **and** ADR-0009 gains
> `Supersedes ADR-0003`. Never delete or rewrite the substance of the old ADR — it
> stays as the historical record. See the supersede procedure in `../SKILL.md`.

---

## Example 3 — Nygard-format ADR (brief)

```markdown
# 0001. Record architecture decisions

Date: 2026-04-10

## Status

Accepted

## Context

We need to capture the motivation behind significant architectural choices so
future contributors understand why the system is built as it is.

## Decision

We will use Architecture Decision Records, stored in `docs/decisions/`, one
Markdown file per decision, numbered sequentially.

## Consequences

We gain a durable, reviewable history of decisions. Authors must spend a little
time writing an ADR for each architecturally significant change.
```

---

## Example 4 — Y-statement (one-liner)

> In the context of **inter-service communication**, facing **the need for loose
> coupling and independent deployability**, we decided for **asynchronous events
> over a message broker** and neglected **synchronous REST calls between services**,
> to achieve **resilience to downstream outages**, accepting that **end-to-end
> flows become eventually consistent and harder to trace**.
