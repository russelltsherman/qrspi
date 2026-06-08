# MADR 4.0 — Full Template and Per-Section Guidance

MADR (Markdown Any Decision Records) 4.0 is the default format for this skill.
This file is the authoritative long-form reference; `SKILL.md` carries only the
lean summary and points here for the complete template, optional sections, and
per-section guidance.

Source convention: https://adr.github.io/madr/ (MADR 4.0.0). Sections below are
ordered exactly as they must appear in a finished ADR.

---

## The eight required, ordered sections

A MADR 4.0 ADR MUST contain these eight items, in this order:

1. **Title** — `# NNNN. <short present-tense decision phrase>`
2. **Status** — current lifecycle state (see `../SKILL.md` lifecycle table)
3. **Date** — `YYYY-MM-DD` the decision was last meaningfully updated
4. **Context and Problem Statement**
5. **Decision Drivers**
6. **Considered Options**
7. **Decision Outcome**
8. **Consequences**

The starter `assets/NNNN-template.md` materializes exactly these eight in order.

---

## Full template

```markdown
---
status: "proposed"
date: 2026-06-07
decision-makers: [list everyone involved in the decision]
consulted: [list everyone whose opinions are sought, two-way communication]
informed: [list everyone kept up-to-date, one-way communication]
---

# NNNN. <short title of solved problem and solution>

## Status

proposed

## Date

2026-06-07

## Context and Problem Statement

<2–3 sentences describing the problem and its context. Articulate the problem as
a question if it helps. You may link prior ADRs, tickets, or docs.>

## Decision Drivers

- <driver 1, e.g. a force, a concern, a requirement>
- <driver 2>
- ...

## Considered Options

- <option 1>
- <option 2>
- <option 3>
- ...

## Decision Outcome

Chosen option: "<option N>", because <justification — which driver(s) it satisfies,
why it beats the others>.

### Consequences

- Good, because <positive consequence>
- Bad, because <negative consequence / accepted trade-off>
- ...
```

> Note: MADR 4.0 nests `Consequences` under `Decision Outcome` as `### Consequences`.
> Treat it as the eighth ordered top-level concern; the starter renders it as a
> `## Consequences` heading for clarity, which is an accepted MADR variation.

---

## Per-section guidance

### Title
- Present tense, names both the problem and the chosen direction
  (e.g. "Use PostgreSQL for primary storage"), not "Database decision".
- Prefix with the zero-padded 4-digit number: `# 0007. Use PostgreSQL ...`.

### Status
- One of: `proposed`, `accepted`, `rejected`, `deprecated`, `superseded`.
- When `superseded`, append `by ADR-NNNN`. See the lifecycle table in `../SKILL.md`.

### Date
- ISO `YYYY-MM-DD`. Update on any status change.

### Context and Problem Statement
- State the forces at play, value-neutral. The reader should grasp *why* a decision
  is needed before seeing the options. Avoid prescribing the answer here.

### Decision Drivers
- The criteria the decision is judged against (requirements, constraints, qualities).
- These should map onto how the chosen option is justified in Decision Outcome.

### Considered Options
- List at least two real options. "Do nothing" is a legitimate option.
- Keep to names here; detail goes in the optional "Pros and Cons of the Options".

### Decision Outcome
- State the chosen option explicitly and tie the choice back to the drivers.

### Consequences
- Both positive and negative. The negative/trade-off bullets are what make an ADR
  honest and useful later. Include follow-up work or risks accepted.

---

## Optional sections

These are NOT required but are part of MADR 4.0 and may be added when useful.
Insert them in the positions indicated:

- **Confirmation** (after Decision Outcome) — how compliance with the decision is
  verified (review, test, lint, fitness function).
- **Pros and Cons of the Options** (after Consequences) — per-option `### <option>`
  with `Good, because` / `Neutral, because` / `Bad, because` bullets.
- **More Information** (last) — links, related ADRs, notes, evidence, the team's
  confidence level, and when/how the decision should be revisited.

Front-matter keys `decision-makers`, `consulted`, `informed` (RACI-style) are
optional metadata and may be omitted for lightweight ADRs.
