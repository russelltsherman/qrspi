---
name: qrspi-pr
description: Prepare a pull request summary after all slices are implemented. Use when implementation is complete.
command: /qrspi-pr
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---

# /qrspi-pr

Thin wrapper that spawns the `qrspi-pr` agent. All prompt content lives in `.claude/agents/qrspi-pr.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-pr`
   - Prompt body containing the seven inputs:
     - `TICKET_ID = <ticket-id>`
     - `IMPL_LOG_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/impl-log.md`
     - `DESIGN_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/design.md`
     - `STRUCTURE_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/structure.md`
     - `PR_SUMMARY_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/pr-summary.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/pr-summary.md`
     - `REPO_ROOT = <REPO_ROOT>`
4. Verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/pr-summary.md`.
5. Tell the user: "PR summary at `.qrspi/<ticket-id>/pr-summary.md`. Use this as your PR description. Read and own the code before merging."
