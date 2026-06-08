# Nygard Original ADR Template

Michael Nygard introduced ADRs in 2011 ("Documenting Architecture Decisions").
This is the original, minimal format. Prefer MADR 4.0 (the default); use the
Nygard format only when a project already standardizes on it or when maximum
brevity is wanted.

Source: https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions

---

## Template

```markdown
# NNNN. <Title>

Date: YYYY-MM-DD

## Status

Accepted

(Or: Proposed / Deprecated / Superseded by ADR-NNNN)

## Context

<The issue motivating this decision, and any context that influences or constrains
the decision. State the facts and the forces — technical, political, social,
project-local — value-neutral.>

## Decision

<The change we are actually proposing or have agreed to do. State it in full
sentences, in active voice: "We will ...".>

## Consequences

<What becomes easier or more difficult because of this change. List all
consequences — positive, negative, and neutral. They affect the team and future
decisions.>
```

---

## Notes

- Five parts only: Title, Status, Context, Decision, Consequences.
- "Decision" is written as an assertion: *"We will use ..."*.
- Consequences are deliberately neutral in framing — record them all, good or bad.
- Nygard ADRs are immutable once accepted: to change a decision you write a new ADR
  that supersedes the old one rather than editing it. (MADR allows light editing of
  status/links; both formats agree that the *substance* of an accepted decision is
  superseded, not rewritten.)
