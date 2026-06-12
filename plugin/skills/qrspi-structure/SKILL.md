---
name: qrspi-structure
description: Define vertical slices, types, and contracts from the approved design. Use after design is approved.
command: /qrspi-structure
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---

# /qrspi-structure

Thin wrapper that spawns the `qrspi-structure` agent. All prompt content lives in `.claude/agents/qrspi-structure.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-structure`
   - Prompt body containing the four inputs:
     - `TICKET_ID = <ticket-id>`
     - `DESIGN_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/design.md`
     - `STRUCTURE_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/structure.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/structure.md`
4. Verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/structure.md`.
5. Tell the user: "Structure written to `.qrspi/<ticket-id>/structure.md`. Check slice boundaries and contracts. If any slice is too large, I'll split it. Tell me 'approved' to proceed to Plan."
