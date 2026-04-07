---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep
---

# Questions Phase (Q)

Read the ticket file at `.qrspi/$ARGUMENTS/ticket.md`.

Produce `.qrspi/$ARGUMENTS/questions.md` with 8-15 technical questions.

## Rules
1. Questions must be answerable by reading the codebase, not by speculation.
2. Categorize into: Data Flow, API Surface, State Management, Edge Cases, Testing, Observability.
3. Each question names a specific file, module, or "the module responsible for X".
4. Do NOT propose solutions or architectures.
5. Include at least 2 Edge Cases questions and 1 Observability question.
6. No question uses solution language: "should we", "we could", "best way to".

## Output format
```
# Questions — <ticket title>
**Ticket:** <ticket-id>
**Generated:** <ISO-8601>
**Status:** draft

## Data Flow
- Q1: <question>
  **Target:** <file or module>
...
```

After writing the file, tell the user: "Questions written to `.qrspi/<id>/questions.md`. Review, edit, then tell me 'approved' to proceed to Research."
