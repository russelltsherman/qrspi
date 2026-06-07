# PRD Template (layout source-of-truth)

This file is the canonical layout asset for the `writing-prds` skill. The skill body
references it by relative path and reads it on demand at draft time. It holds two
skeletons (lean and expanded), the metadata-header convention, the SMART-metrics table
format, and the user-story block.

---

## Metadata header convention

Every produced PRD MUST open with this header block:

```
**Source:** <the verbatim source line / request that prompted this PRD>
**Generated:** <ISO-8601 timestamp, e.g. 2026-06-06T14:30:00Z>
**Status:** Draft | In Review | Approved
```

- `Source` — the originating request line, captured verbatim for traceability.
- `Generated` — ISO-8601 timestamp of authoring.
- `Status` — one of `Draft`, `In Review`, `Approved` (default `Draft` on first write).

---

## Lean skeleton (default — six core sections)

Use this skeleton by default. Every core section is mandatory; emit each one even when
the answer is "None" (never silently drop a section).

```markdown
# <Title>

**Source:** <source line>
**Generated:** <ISO-8601>
**Status:** Draft

## 1. Title & Metadata
Feature name, owner, date, and the header block above.

## 2. Problem Statement
The user/business problem in concrete terms. Who is affected, what pain exists,
and the evidence that it is real. No solution detail here.

## 3. Goals & Non-Goals
- **Goals:** what success makes true (outcomes, not features).
- **Non-Goals:** what is explicitly out of scope. If there are none, write "None".

## 4. Solution Overview
The proposed approach at a high level. What we will build and why it addresses the
problem. Link to user stories below.

## 5. Success Metrics
How we will know it worked — SMART metrics table (see format below).

## 6. Scope / Milestones / Open Questions
- **Scope:** what is in this iteration.
- **Milestones:** sequenced delivery checkpoints.
- **Open Questions:** unresolved decisions, each owned by someone.
```

---

## Expanded sections (expanded format only)

Append these AFTER the six core sections when the feature is large, cross-team, or
high-risk (see the skill body's format-selection rule). Clearly marked expanded-only;
omit them in a lean run.

```markdown
## 7. Personas (expanded format only)
Named user archetypes, their goals, and their context of use.

## 8. Technical Considerations (expanded format only)
Architecture, constraints, data, performance, and security notes.

## 9. Dependencies (expanded format only)
Upstream/downstream systems, teams, and external services this relies on.

## 10. Launch Plan (expanded format only)
Rollout strategy, phasing, feature flags, comms, and rollback plan.
```

---

## SMART metrics table format

Use under **Success Metrics**. Each row is Specific, Measurable, Achievable, Relevant,
Time-bound. Columns: `metric | baseline | target | timeframe`.

| Metric | Baseline | Target | Timeframe |
|--------|----------|--------|-----------|
| Checkout completion rate | 62% | 75% | Within 1 quarter of launch |

---

## User-story reference block

Capture key flows as user stories with Given/When/Then acceptance criteria. Include at
least one filled story.

```
As a <role>
I want <capability>
So that <outcome>

Acceptance criteria:
- Given <precondition>, When <action>, Then <expected result>.
```

Example:

```
As a returning shopper
I want my saved payment method pre-selected at checkout
So that I can complete a purchase without re-entering card details

Acceptance criteria:
- Given a shopper with a saved card, When they reach the payment step,
  Then the saved card is pre-selected and editable.
```
