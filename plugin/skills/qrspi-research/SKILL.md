---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---

# /qrspi-research

Thin wrapper that spawns the `qrspi-research` agent. All prompt content lives in `.claude/agents/qrspi-research.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd` (the repo root or worktree the user is currently in).
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-research`
   - Prompt body containing the five inputs:
     - `TICKET_ID = <ticket-id>`
     - `QUESTIONS_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/questions.md`
     - `RESEARCH_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/research.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/research.md`
     - `REPO_ROOT = <REPO_ROOT>`
4. Verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/research.md`. If missing or empty, report the error and stop.
5. Tell the user: "Research written to `.qrspi/<ticket-id>/research.md`. Review for factual accuracy, then tell me 'approved' to proceed to Design."
