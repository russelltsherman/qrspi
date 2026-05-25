---
name: qrspi-worktree
description: Build a session-aware task DAG from the plan. Use after plan is approved.
command: /qrspi-worktree
argument-hint: <ticket-id>
allowed-tools: Read, Bash(wc:*), Bash(curl:*), mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---

# Work Tree Phase (W)

Read `.qrspi/$ARGUMENTS/plan.md`.

Produce `.qrspi/$ARGUMENTS/worktree.md`.

## Rules
1. Each plan step maps to one task with: ID, Description, Depends On, Plan Step ref, Cost (S/M/L), Status.
2. Group tasks into sessions. Each session has a Load manifest listing ONLY the artifacts needed.
3. Load manifests reference sections, not whole files (e.g., "structure.md Contracts").
4. Estimated context per session must stay under 40%.
5. Insert SESSION BOUNDARY markers with a Reason between sessions.
6. Identify and list the critical path at the top.

After writing, tell the user: "Work tree written to `.qrspi/<id>/worktree.md`. Review session boundaries — each session will be a fresh `/clear`. Tell me 'approved' to start implementation."

## Upload artifact

After the closing message, upload the artifact to the Linear issue:
1. Get the file size: run `wc -c < .qrspi/$ARGUMENTS/worktree.md` via Bash
2. Call `mcp__linear-russelltsherman__prepare_attachment_upload` with `issue: "$ARGUMENTS"`, `filename: "worktree.md"`, `contentType: "text/markdown"`, `size: <byte count from step 1>`
3. Run the curl PUT via Bash: `curl -s -X PUT --data-binary @.qrspi/$ARGUMENTS/worktree.md` with all headers from the upload response, to the signed upload URL
4. Call `mcp__linear-russelltsherman__create_attachment_from_upload` with `issue: "$ARGUMENTS"`, `assetUrl` from step 2, and `title: "WorkTree — $ARGUMENTS"`

If any upload step fails, report the error but do NOT fail the phase — the local artifact is already written.
