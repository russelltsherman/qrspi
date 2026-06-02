---
name: qrspi-questions
description: Generate 8-15 targeted technical questions from a feature ticket. Use when starting a new QRSPI feature workflow or when the user says "questions for" a ticket.
command: /qrspi-questions
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear__get_issue
---

# /qrspi-questions

Thin wrapper that fetches the ticket from Linear and spawns the `qrspi-questions` agent. All prompt content lives in `.claude/agents/qrspi-questions.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>` (e.g., `RUS-42`).
2. Fetch the ticket: call `mcp__linear__get_issue` with `id: "<ticket-id>"`. Capture `title` and `description` as `TICKET_CONTENT`.
3. Resolve `REPO_ROOT` from `pwd` (or the worktree path if running inside one).
4. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-questions`
   - Prompt body containing the four inputs:
     - `TICKET_ID = <ticket-id>`
     - `TICKET_CONTENT = <title + description>`
     - `ARTIFACT_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/questions.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/questions.md`
5. After the agent returns, verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/questions.md`. If missing or empty, report the error and stop.
6. Tell the user: "Questions written to `.qrspi/<ticket-id>/questions.md`. Review, edit, then tell me 'approved' to proceed to Research."
