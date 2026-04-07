---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep
---

# Design Discussion Phase (D)

Read ALL THREE inputs:
1. `.qrspi/$ARGUMENTS/ticket.md`
2. `.qrspi/$ARGUMENTS/questions.md`
3. `.qrspi/$ARGUMENTS/research.md`

Produce `.qrspi/$ARGUMENTS/design.md` — target ~200 lines, hard max 300.

## Required sections
1. **Current State** — every claim cites research.md: "(ref: Q1)"
2. **Desired End State** — maps every acceptance criterion to system behavior
3. **Delta** — concrete changes: new files, modified files, new queries
4. **Pattern Decisions** — 2+ options per decision, table format, mark recommendation, flag any NEW PATTERN
5. **Risk Register** — table with likelihood/impact/mitigation, minimum 2 entries
6. **Open Questions** — things only a human can answer

## Rules
1. No code blocks. Prose and tables only.
2. Every Current State sentence must have a `(ref: QN)` citation.
3. Every acceptance criterion from the ticket appears in Desired End State.
4. Pattern Decisions must reference existing codebase patterns from research. Flag new patterns explicitly.
5. Write for editability, not persuasion. The human will rewrite sections.

After writing, tell the user: "Design written to `.qrspi/<id>/design.md`. This is the highest-leverage review — check Pattern Decisions and Current State citations carefully. Edit anything that's wrong, then tell me 'approved'."
