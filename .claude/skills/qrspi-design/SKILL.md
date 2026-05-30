---
name: qrspi-design
description: Produce a design document by combining the ticket, answered questions, and codebase research. Use after research is approved. This is the brain-surgery phase.
command: /qrspi-design
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*), mcp__linear-russelltsherman__get_issue
---

# /qrspi-design

Thin wrapper that fetches the ticket from Linear and spawns the `qrspi-design` agent. All prompt content lives in `.claude/agents/qrspi-design.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Fetch the ticket: call `mcp__linear-russelltsherman__get_issue` with `id: "<ticket-id>"`. Capture `title` and `description` as `TICKET_CONTENT`.
3. Resolve `REPO_ROOT` from `pwd`.
4. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-design`
   - Prompt body containing the six inputs:
     - `TICKET_ID = <ticket-id>`
     - `TICKET_CONTENT = <title + description>`
     - `QUESTIONS_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/questions.md`
     - `RESEARCH_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/research.md`
     - `DESIGN_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/design.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/design.md`
5. Verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/design.md`.
6. Tell the user: "Design written to `.qrspi/<ticket-id>/design.md`. This is the highest-leverage review — check Pattern Decisions and Current State citations carefully. Edit anything that's wrong, then tell me 'approved'."
