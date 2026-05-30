---
name: qrspi-implement
description: Implement one vertical slice per invocation. Always start with a fresh context. Use after worktree is approved or after completing the previous slice.
command: /qrspi-implement
argument-hint: <ticket-id> <slice-number>
allowed-tools: Agent, Read, Bash(pwd:*)
---

# /qrspi-implement

Thin wrapper that extracts slice-scoped sections from the planning artifacts and spawns the `qrspi-implement` agent in a fresh context. All implementation logic lives in `.claude/agents/qrspi-implement.md`.

## Steps

1. Parse `$ARGUMENTS` to get `<ticket-id>` and `<slice-number>`.
2. Resolve `REPO_ROOT` from `pwd`. The wrapper expects to be invoked from the worktree directory; `REPO_ROOT` equals the worktree path.
3. Read these files and extract only the slice-scoped sections:
   - `.qrspi/<ticket-id>/structure.md` → Types + Contracts + Slice `<slice-number>` sections → `STRUCTURE_SLICE`
   - `.qrspi/<ticket-id>/plan.md` → Slice `<slice-number>` section → `PLAN_SLICE`
   - `.qrspi/<ticket-id>/worktree.md` → session for this slice → `WORKTREE_SESSION`
   - `.qrspi/<ticket-id>/impl-log.md` → "Notes for next session" from the previous slice's entry, if any → `PREVIOUS_NOTES`
4. Spawn the agent via the `Agent` tool:
   - `subagent_type: qrspi-implement`
   - Prompt body containing the nine inputs:
     - `TICKET_ID = <ticket-id>`
     - `SLICE_NUMBER = <slice-number>`
     - `WORKTREE_DIR = <REPO_ROOT>`
     - `STRUCTURE_SLICE = <extracted text>`
     - `PLAN_SLICE = <extracted text>`
     - `WORKTREE_SESSION = <extracted text>`
     - `PREVIOUS_NOTES = <extracted text or empty>`
     - `IMPL_LOG_PATH = <REPO_ROOT>/.qrspi/<ticket-id>/impl-log.md`
     - `IMPL_LOG_TEMPLATE_PATH = <REPO_ROOT>/.qrspi/templates/impl-log.md`
5. After the agent returns, verify `<REPO_ROOT>/.qrspi/<ticket-id>/impl-log.md` was updated with a new entry for this slice.
6. Tell the user: "Slice `<slice-number>` implemented. Tests: `<result from agent summary>`. Run `/clear` then `/qrspi-implement <ticket-id> <next-slice>` for the next slice, or review the code first."
