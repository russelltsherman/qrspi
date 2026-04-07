---
name: qrspi-plan
description: Write atomic implementation steps per vertical slice. Use after structure is approved.
command: /qrspi-plan
argument-hint: <ticket-id>
allowed-tools: Read
---

# Plan Phase (P)

Read:
1. `.qrspi/$ARGUMENTS/structure.md`
2. `.qrspi/$ARGUMENTS/design.md` (for reference only)

Produce `.qrspi/$ARGUMENTS/plan.md`.

## Rules
1. Each step is atomic: one file, one action.
2. Steps reference exact types/signatures from structure.md.
3. Steps that modify existing code include Current and After signatures.
4. Steps that create new files name the file and its purpose.
5. Each slice ends with a Verify checkpoint with a runnable command.
6. Total steps must be 100 or fewer. If exceeded, structure slices are too large — stop and say so.
7. Include Rollback Notes for DB migrations, config changes, destructive ops.

After writing, tell the user: "Plan written to `.qrspi/<id>/plan.md`. This should be a spot-check, not a deep review — alignment happened during Design. Tell me 'approved' to proceed to WorkTree."
