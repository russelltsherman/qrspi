---
name: qrspi-structure
description: Define vertical slices, types, and contracts from the approved design. Use after design is approved.
command: /qrspi-structure
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(wc:*), Bash(curl:*), mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---

# Structure Outline Phase (S)

Read `.qrspi/$ARGUMENTS/design.md` (must have Status: approved in it or user must have said approved).

Produce `.qrspi/$ARGUMENTS/structure.md`.

## Rules
1. Define new/modified types and function signatures (pseudo-code, not implementations).
2. Organize into VERTICAL SLICES — each delivers a testable end-to-end path.
   - CORRECT: "Slice 1: Mock API → UI component → hardcoded data"
   - WRONG: "Phase 1: All database changes"
3. Each slice has: Goal, Files touched (new/modify marked), Verification step, Context cost (S/M/L), Dependencies.
4. No slice touches > 10 files. Split if it does.
5. Order slices so dependencies flow forward.
6. Include a Contracts section for cross-slice interfaces.
7. Include an Unverified Assumptions section — claims from design.md you can't map to concrete code.

After writing, tell the user: "Structure written to `.qrspi/<id>/structure.md`. Check slice boundaries and contracts. If any slice is too large, I'll split it. Tell me 'approved' to proceed to Plan."

## Upload artifact

After the closing message, upload the artifact to the Linear issue:
1. Get the file size: run `wc -c < .qrspi/$ARGUMENTS/structure.md` via Bash
2. Call `mcp__linear-russelltsherman__prepare_attachment_upload` with `issue: "$ARGUMENTS"`, `filename: "structure.md"`, `contentType: "text/markdown"`, `size: <byte count from step 1>`
3. Run the curl PUT via Bash: `curl -s -X PUT --data-binary @.qrspi/$ARGUMENTS/structure.md` with all headers from the upload response, to the signed upload URL
4. Call `mcp__linear-russelltsherman__create_attachment_from_upload` with `issue: "$ARGUMENTS"`, `assetUrl` from step 2, and `title: "Structure — $ARGUMENTS"`

If any upload step fails, report the error but do NOT fail the phase — the local artifact is already written.
