---
name: qrspi-worktree
description: Build a session-aware task DAG from the plan. Use after plan is approved.
command: /qrspi-worktree
argument-hint: <ticket-id>
allowed-tools: Agent, Bash(pwd:*)
---

# /qrspi-worktree

Thin wrapper that spawns the `qrspi-worktree` agent. All prompt content lives in `.claude/agents/qrspi-worktree.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>`.
2. Resolve `REPO_ROOT` from `pwd`.
3. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-worktree`
   - Prompt body containing the four inputs:
     - `TICKET_ID = <ticket-id>`
     - `PLAN_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/plan.md`
     - `WORKTREE_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/worktree.md`
     - `TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/worktree.md`
4. Verify the artifact exists and is non-empty at `<REPO_ROOT>/.qrspi/<ticket-id>/worktree.md`.
5. Tell the user: "Work tree written to `.qrspi/<ticket-id>/worktree.md`. Review session boundaries — each session will be a fresh `/clear`. Tell me 'approved' to start implementation."
