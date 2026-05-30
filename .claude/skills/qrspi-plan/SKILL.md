---
name: qrspi-plan
description: Write atomic implementation steps per vertical slice. Use after structure is approved.
command: /qrspi-plan
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---

# /qrspi-plan

Thin wrapper that spawns the `qrspi-plan` agent. All prompt content lives in `.claude/agents/qrspi-plan.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-plan`
   - Prompt body containing the five inputs:
     - `TICKET_ID = <ticket-id>`
     - `STRUCTURE_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/structure.md`
     - `DESIGN_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/design.md`
     - `PLAN_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/plan.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/plan.md`
4. Verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/plan.md`.
5. Tell the user: "Plan written to `.qrspi/<ticket-id>/plan.md`. This should be a spot-check, not a deep review — alignment happened during Design. Tell me 'approved' to proceed to WorkTree."
