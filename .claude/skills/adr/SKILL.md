---
name: adr
description: "Author and manage Architecture Decision Records (ADRs) using MADR 4.0 by default. Use when the user wants to write, draft, record, or update an architecture/architectural decision, capture the rationale behind a design or technology choice, create an ADR or decision record, supersede or deprecate a prior decision, or set up docs/decisions/. Trigger on: 'write an ADR', 'record this decision', 'create an architecture decision record', 'document why we chose X', 'supersede ADR-NNNN', 'deprecate that decision', or any request to capture an architecturally significant choice and its trade-offs."
command: /adr
argument-hint: "[decision title]"
allowed-tools: Read, Write, Edit, Glob, Grep
---

# Architecture Decision Records (ADR)

Guide the author through writing and maintaining an Architecture Decision Record:
a short Markdown file that captures one architecturally significant decision, the
options weighed, the choice made, and its consequences. The default format is
**MADR 4.0**. Keep ADRs immutable in substance — to change a decision, write a new
ADR that supersedes the old one.

This skill is self-contained guidance. Heavy material lives on-demand in the
reference and asset files pointed to at the end; load them only when needed.

## When to write an ADR

Write an ADR when a decision is **architecturally significant** — i.e. it is costly
to reverse and affects the structure, qualities, or external dependencies of the
system. Concretely, write one when the decision:

- Changes the structure (modules, services, boundaries, data flow) of the system.
- Picks or drops a technology, framework, datastore, protocol, or vendor.
- Affects a cross-cutting quality attribute: security, performance, availability,
  cost, compliance, or operability.
- Establishes a convention others must follow (naming, layering, an API contract).
- Is hard or expensive to reverse later, or has already been debated more than once.

Do **not** write an ADR for routine, easily-reversed, or purely local choices
(variable names, a one-file refactor, formatting). When unsure, ask: "Would a new
team member six months from now need to know *why* we did this?" If yes, write it.

## Default format (MADR 4.0)

A MADR 4.0 ADR has these **eight required sections, in this order**:

1. **Title** — `# NNNN. <short present-tense decision phrase>`
2. **Status** — current lifecycle state (see the table below).
3. **Date** — `YYYY-MM-DD`, updated on any status change.
4. **Context and Problem Statement** — the forces and the problem, value-neutral.
5. **Decision Drivers** — the criteria the decision is judged against.
6. **Considered Options** — at least two real options ("do nothing" counts).
7. **Decision Outcome** — the chosen option, justified against the drivers.
8. **Consequences** — both positive and negative outcomes / accepted trade-offs.

Optional MADR sections (Confirmation, Pros and Cons of the Options, More
Information) and full per-section guidance live in the long-form reference; see
`references/madr-4.0.md`.

To start a new ADR, copy the starter `assets/NNNN-template.md`, rename it per the
naming rules below, and fill in each section. The starter already materializes the
eight ordered sections.

### Alternative formats

MADR 4.0 is the default. Use an alternative only when a project already
standardizes on it or when brevity is paramount:

- Nygard's original five-part template (Title, Status, Context, Decision,
  Consequences) — see `references/nygard.md`.
- Y-statements, a single-sentence decision capture, useful for spikes or embedded
  inside a MADR "Decision Outcome" — see `references/y-statements.md`.

For complete worked ADRs (including a supersede pair) see `references/examples.md`.

## Lifecycle and status transitions

ADR status follows this lifecycle. The only valid transitions are:

| From       | To                    | Action                                                              |
|------------|-----------------------|---------------------------------------------------------------------|
| _(none)_   | `proposed`            | Draft a new ADR; status starts as `proposed`.                       |
| `proposed` | `accepted`            | The decision is agreed and adopted.                                 |
| `proposed` | `rejected`            | The decision is declined; keep the ADR as a record of the debate.   |
| `accepted` | `deprecated`          | The decision no longer applies but is not replaced by a new one.    |
| `accepted` | `superseded by ADR-NNNN` | A newer ADR replaces this decision (see the supersede procedure). |

Rules:

- A `rejected` or `superseded` ADR is **never deleted or rewritten in substance** —
  it remains the historical record.
- `accepted` is the only status that can later become `deprecated` or `superseded`.
- Always update the **Date** when you change the **Status**.

## Numbering and naming

Use the adr-tools / log4brains compatible convention:

- **Location:** `docs/decisions/` (one Markdown file per ADR).
- **Filename:** `NNNN-kebab-case-title.md`, e.g. `0007-use-postgresql-for-orders.md`.
- **Numbering:** sequential, **zero-padded 4-digit** (`0001`, `0002`, …). The number
  never changes once assigned and is never reused, even if the ADR is rejected.
- **Next number:** find the highest existing `NNNN` in `docs/decisions/` (glob/grep
  the filenames) and add one. If the directory does not exist yet, create it and
  start at `0001`.
- The in-file Title heading mirrors the filename: `# 0007. Use PostgreSQL for orders`.

## Supersede, deprecate, and index maintenance

### Supersede (replace one decision with another)

When a new ADR replaces an old one, maintain the **bidirectional-link invariant** —
update **both** files:

1. In the **old** ADR: set Status to `superseded by ADR-NNNN` (the new number) and
   update its Date. Do not alter the old ADR's substance.
2. In the **new** ADR: add a line `Supersedes ADR-NNNN` (the old number) near its
   Status, and set its own Status (normally `accepted`).

Both directions are required: the old ADR points forward, the new one points back.
A worked supersede pair is in the examples reference linked above.

### Deprecate (retire without replacement)

Set the ADR's Status to `deprecated`, update its Date, and add a short note in the
ADR explaining why it no longer applies. There is no new ADR to link to.

### Index maintenance

Keep a `docs/decisions/README.md` index listing each ADR by number, title, and
status, so the set is browsable. Add a row when you create an ADR and update the
status column on any transition. Treat the index as derived from the ADR files —
the individual ADRs remain the source of truth.
