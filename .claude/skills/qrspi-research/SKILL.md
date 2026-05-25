---
name: qrspi-research
description: Map codebase facts by answering questions from the Questions phase. The feature ticket is intentionally hidden. Use after questions are approved.
command: /qrspi-research
argument-hint: <ticket-id>
allowed-tools: Read, Glob, Grep, Bash(find:*), Bash(wc:*), Bash(head:*), Bash(tail:*), Bash(curl:*), mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---

# Research Phase (R)

Read `.qrspi/$ARGUMENTS/questions.md`.

CRITICAL: Do NOT read the ticket. The ticket is intentionally hidden during this phase so you gather objective facts without forming implementation opinions. This means: do NOT read `.qrspi/$ARGUMENTS/ticket.md` AND do NOT call `mcp__linear-russelltsherman__get_issue`.

Produce `.qrspi/$ARGUMENTS/research.md`.

## Rules
1. Answer each question with FACTS: file paths, function signatures, data types, call chains.
2. Include code snippets (< 20 lines) as evidence with `file:line` citations.
3. Do NOT form opinions about what should change.
4. If a question can't be answered, state "NOT FOUND" with search queries attempted.
5. Document implicit contracts and dependency directions.
6. Note inconsistencies between code and comments/docs.
7. Include a "Discovered Patterns" section and an "Inconsistencies" section.

## Output format
```
# Research — Codebase Map
**Questions source:** questions.md @ <timestamp>
**Generated:** <ISO-8601>
**Status:** draft

## Q1: <question text>
**Answer:** <facts>
**Evidence:** <code + file:line>
**Dependencies:** <upstream/downstream>
**Implicit contracts:** <conventions>
...

## Discovered Patterns
...

## Inconsistencies
...
```

After writing, tell the user: "Research written to `.qrspi/<id>/research.md`. Review for factual accuracy, then tell me 'approved' to proceed to Design."

## Upload artifact

After the closing message, upload the artifact to the Linear issue:
1. Get the file size: run `wc -c < .qrspi/$ARGUMENTS/research.md` via Bash
2. Call `mcp__linear-russelltsherman__prepare_attachment_upload` with `issue: "$ARGUMENTS"`, `filename: "research.md"`, `contentType: "text/markdown"`, `size: <byte count from step 1>`
3. Run the curl PUT via Bash: `curl -s -X PUT --data-binary @.qrspi/$ARGUMENTS/research.md` with all headers from the upload response, to the signed upload URL
4. Call `mcp__linear-russelltsherman__create_attachment_from_upload` with `issue: "$ARGUMENTS"`, `assetUrl` from step 2, and `title: "Research — $ARGUMENTS"`

If any upload step fails, report the error but do NOT fail the phase — the local artifact is already written.
