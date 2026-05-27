---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(head:*), Bash(tail:*)
---

# Research Phase (R)

Read `.qrspi/$ARGUMENTS/questions.md`.

CRITICAL: Do NOT read the ticket. The ticket is intentionally hidden during this phase so you gather objective facts without forming implementation opinions. This means: do NOT read `.qrspi/$ARGUMENTS/ticket.md` AND do NOT call `mcp__linear-russelltsherman__get_issue`.

Produce `.qrspi/$ARGUMENTS/research.md`.

Read `.qrspi/templates/research.md` for the output format.

## Rules
1. Answer each question with FACTS: file paths, function signatures, data types, call chains.
2. Include code snippets (< 20 lines) as evidence with `file:line` citations.
3. Do NOT form opinions about what should change.
4. If a question can't be answered, state "NOT FOUND" with search queries attempted.
5. Document implicit contracts and dependency directions.
6. Note inconsistencies between code and comments/docs.
7. Include a "Discovered Patterns" section and an "Inconsistencies" section.

After writing, tell the user: "Research written to `.qrspi/<id>/research.md`. Review for factual accuracy, then tell me 'approved' to proceed to Design."
