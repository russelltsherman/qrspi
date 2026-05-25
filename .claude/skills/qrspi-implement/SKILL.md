---
name: qrspi-implement
description: Implement one vertical slice per invocation. Always start with a fresh context. Use after worktree is approved or after completing the previous slice.
command: /qrspi-implement
argument-hint: <ticket-id> <slice-number>
allowed-tools: Read, Write, Edit, Glob, Grep, Bash, mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---

# Implement Phase (I)

Parse $ARGUMENTS to extract <ticket-id> and <slice-number>.

Read ONLY these files (context firewall):
1. `.qrspi/<ticket-id>/structure.md` — only the Types, Contracts, and Slice <slice-number> sections
2. `.qrspi/<ticket-id>/plan.md` — only the Slice <slice-number> section
3. `.qrspi/<ticket-id>/worktree.md` — only the session for this slice
4. `.qrspi/<ticket-id>/impl-log.md` — only the "Notes for next session" from the previous slice (if any)

Do NOT read the full design, full plan, or earlier slice details beyond the notes.

## Rules
1. Implement ONLY the tasks in this session. Do not anticipate future slices.
2. Match types and signatures from structure.md exactly. If you must deviate, STOP and report before changing.
3. After completing tasks, run the verification command from the plan.
4. If tests fail: fix (max 2 retries). If still failing, report failure with output, hypothesis, and whether it's your code or upstream.
5. Follow existing codebase conventions.
6. Do NOT refactor code outside your slice scope.
7. Append results to `.qrspi/<ticket-id>/impl-log.md`.
8. **HARD STOP on infrastructure errors.** If ANY command fails with permissions, auth, config, or tooling errors (EACCES, permission denied, token expired, command not found, config inaccessible): print the exact failing command and exact error output, then STOP. Do not execute another command. Do not investigate. Do not attempt workarounds of any kind — no alternate tools, no config changes, no env var overrides, no retries. Exit immediately. "Let me just try one thing" is explicitly forbidden.

## impl-log entry format
```
## Slice <N> — <ISO-8601>
**Tasks completed:** T1, T2, ...
**Tasks failed:** none
**Tests:** <command> → N passed, N failed
**Deviations from structure.md:** none
**Deviations from plan.md:** <describe or "none">
**Notes for next session:** <facts the next slice needs>
```

After completing, tell the user: "Slice <N> implemented. Tests: <result>. Run `/clear` then `/qrspi-implement <ticket-id> <next-slice>` for the next slice, or review the code first."

## Upload artifact

After the closing message, upload the implementation log to the Linear issue:
1. Get the file size: run `wc -c < .qrspi/<ticket-id>/impl-log.md` via Bash
2. Call `mcp__linear-russelltsherman__prepare_attachment_upload` with `issue: "<ticket-id>"`, `filename: "impl-log.md"`, `contentType: "text/markdown"`, `size: <byte count from step 1>`
3. Run the curl PUT via Bash: `curl -s -X PUT --data-binary @.qrspi/<ticket-id>/impl-log.md` with all headers from the upload response, to the signed upload URL
4. Call `mcp__linear-russelltsherman__create_attachment_from_upload` with `issue: "<ticket-id>"`, `assetUrl` from step 2, and `title: "Implementation Log — <ticket-id>"`

If any upload step fails, report the error but do NOT fail the phase — the local artifact is already written.
