---
name: qrspi-worktree
description: Build a session-aware task DAG from the plan. Use after plan is approved.
command: /qrspi-worktree
argument-hint: <ticket-id>
allowed-tools: Read
---

# Work Tree Phase (W)

Read `.qrspi/$ARGUMENTS/plan.md`.

Produce `.qrspi/$ARGUMENTS/worktree.md`.

Read `.qrspi/templates/worktree.md` for the output format.

## Rules
1. Each plan step maps to one task with: ID, Description, Depends On, Plan Step ref, Cost (S/M/L), Status.
2. Group tasks into sessions. Each session has a Load manifest listing ONLY the artifacts needed.
3. Load manifests reference sections, not whole files (e.g., "structure.md Contracts").
4. Estimated context per session must stay under 40%.
5. Insert SESSION BOUNDARY markers with a Reason between sessions.
6. Identify and list the critical path at the top.

After writing, tell the user: "Work tree written to `.qrspi/<id>/worktree.md`. Review session boundaries — each session will be a fresh `/clear`. Tell me 'approved' to start implementation."
