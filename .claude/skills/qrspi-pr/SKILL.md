---
name: qrspi-pr
description: Prepare a pull request summary after all slices are implemented. Use when implementation is complete.
command: /qrspi-pr
argument-hint: <ticket-id>
allowed-tools: Read, Bash(git diff:*), Bash(git log:*)
---

# PR Phase

Read:
1. `.qrspi/$ARGUMENTS/impl-log.md` (full)
2. `.qrspi/$ARGUMENTS/design.md` (for risk register)
3. `.qrspi/$ARGUMENTS/structure.md` (for contracts)
4. Git diff: run `git diff main...HEAD --stat` and `git diff main...HEAD`

Produce `.qrspi/$ARGUMENTS/pr-summary.md`.

## Required sections
1. **Summary** — 3-5 sentences: what changed, why, reviewer focus areas
2. **Acceptance Criteria Mapping** — table: criterion -> implementation file -> test
3. **Changes by Slice** — table per slice: file, change type, lines changed
4. **Testing Summary** — checklist of verification commands and results
5. **Deviations from Structure** — table (even if empty)
6. **Risks & Rollback** — from design.md risk register, updated with implementation findings
7. **Open Items** — deferred work, tech debt, follow-up tickets

## Rules
1. PR title under 72 characters.
2. Every acceptance criterion from the ticket maps to a file and a test.
3. Every file in the git diff is accounted for in Changes by Slice.

After writing, tell the user: "PR summary at `.qrspi/<id>/pr-summary.md`. Use this as your PR description. Read and own the code before merging."
