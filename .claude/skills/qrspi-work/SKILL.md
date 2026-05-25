---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). Reads the ticket's Linear status, determines the current phase, and executes the appropriate action — planning, implementation, or review response — without manual phase-by-phase invocation. Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, mcp__linear-russelltsherman__get_issue_status, mcp__linear-russelltsherman__save_issue, mcp__linear-russelltsherman__list_issue_statuses, mcp__linear-russelltsherman__prepare_attachment_upload, mcp__linear-russelltsherman__create_attachment_from_upload
---

# QRSPI Work Orchestrator

You are a state machine. Read the ticket's Linear status and execute the matching action. Run autonomously — no approval gates between phases. Print verbose progress so the operator can observe.

## Entry Point

1. Parse `$ARGUMENTS` to extract `<ticket-id>`.
2. Fetch the ticket: call `mcp__linear-russelltsherman__get_issue` with identifier `<ticket-id>`.
3. Read the ticket's status name.
4. Dispatch to the matching state section below.
5. If the status doesn't match any known state, print the status and ask the user what to do.

## State Dispatch

| Linear Status | Action |
|---|---|
| `Backlog` or `Selected` | → [Run Planning](#state-backlog--selected--run-planning) |
| `Plan Review` | → [Address Planning Feedback](#state-plan-review--address-feedback) |
| `Plan Approved` | → [Run Implementation](#state-plan-approved--run-implementation) |
| `Code Review` | → [Address Implementation Feedback](#state-code-review--address-feedback) |
| `Code Approved` | → [Report Ready to Merge](#state-code-approved--ready-to-merge) |
| `Done` | Print: "Ticket `<ticket-id>` is already complete." and exit. |

---

## State: Backlog / Selected → Run Planning

Produce all six planning artifacts and submit a planning PR for review.

### Preflight

1. Check for existing planning branch:
   ```bash
   gt log short --no-interactive 2>/dev/null | grep -q '<ticket-id>/planning'
   ```
2. If the branch exists, checkout and resume from the last incomplete artifact (see [Resumability](#resumability)).
3. If not, ensure you're on trunk and synced:
   ```bash
   gt checkout main --no-interactive
   gt sync --force --no-interactive
   ```

### Phase execution

Run each phase by spawning a sub-agent. After each, verify the artifact exists and commit it.

Save the ticket content from the Linear fetch — you'll pass it to some sub-agents below.

**Phase 1 — Questions**

1. Read `.claude/skills/qrspi-questions/SKILL.md` for the phase instructions.
2. Spawn a sub-agent (Agent tool) with:
   - The core instructions from the skill file (omit frontmatter, approval messaging, and upload sections)
   - The ticket content
   - Instruction: "Write `.qrspi/<ticket-id>/questions.md`. Do not wait for approval. Do not upload to Linear. Do not run any git commands."
   - Instruction: "Generate questions FROM the ticket content only. Do NOT explore the codebase — that is the research phase's job. Do not use Read, Glob, Grep, or Bash to look at files. Your only input is the ticket. Your questions should ask what to investigate, not pre-answer by looking."
3. Verify `.qrspi/<ticket-id>/questions.md` exists and is non-empty.
4. Stage and create the planning branch:
   ```bash
   git add .qrspi/<ticket-id>/questions.md
   gt create <ticket-id>/planning --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Questions

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```
5. Print: "Questions generated. Moving to Research..."

**Phase 2 — Research**

1. Read `.claude/skills/qrspi-research/SKILL.md` for the phase instructions.
2. Spawn a sub-agent with:
   - The core instructions from the skill file
   - Path to `questions.md`
   - **DO NOT include the ticket content.** The research firewall is critical — the research agent works only from questions, never from the ticket. This prevents anchoring bias.
   - Instruction: "Write `.qrspi/<ticket-id>/research.md`. Do not call any Linear MCP tools. Do not wait for approval. Do not run any git commands."
3. Verify `research.md` exists and is non-empty.
4. Stage and commit:
   ```bash
   git add .qrspi/<ticket-id>/research.md
   gt modify -c --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Research

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```
5. Print: "Research complete. Moving to Design..."

**Phase 3 — Design**

1. Read `.claude/skills/qrspi-design/SKILL.md`.
2. Spawn a sub-agent with: ticket content, paths to `questions.md` and `research.md`.
3. Verify `design.md` exists.
4. Stage and commit: `git add .qrspi/<ticket-id>/design.md` then `gt modify -c --no-interactive -m "$(cat <<'EOF'`... `<ticket-id>: Design` ...`EOF`)"`
5. Print: "Design complete. Moving to Structure..."

**Phase 4 — Structure**

1. Read `.claude/skills/qrspi-structure/SKILL.md`.
2. Spawn a sub-agent with: path to `design.md`.
3. Verify `structure.md` exists.
4. Stage and commit: `git add .qrspi/<ticket-id>/structure.md` then commit with message `<ticket-id>: Structure`.
5. Print: "Structure complete. Moving to Plan..."

**Phase 5 — Plan**

1. Read `.claude/skills/qrspi-plan/SKILL.md`.
2. Spawn a sub-agent with: paths to `structure.md` and `design.md`.
3. Verify `plan.md` exists.
4. Stage and commit: `git add .qrspi/<ticket-id>/plan.md` then commit with message `<ticket-id>: Plan`.
5. Print: "Plan complete. Moving to Work Tree..."

**Phase 6 — Work Tree**

1. Read `.claude/skills/qrspi-worktree/SKILL.md`.
2. Spawn a sub-agent with: path to `plan.md`.
3. Verify `worktree.md` exists.
4. Stage and commit: `git add .qrspi/<ticket-id>/worktree.md` then commit with message `<ticket-id>: Work tree`.
5. Print: "Work tree complete. Submitting planning PR..."

### Submit and transition

1. Push and create the PR:
   ```bash
   gt submit --no-edit --no-interactive
   ```
2. Capture the PR URL from the output.
3. Update Linear status to `Plan Review`:
   Call `mcp__linear-russelltsherman__save_issue` with `id: "<ticket-id>"` and `state: "Plan Review"`.
4. Upload all six artifacts to Linear using the standard upload pattern (see [Artifact Upload](#artifact-upload)).
5. Print: "Planning complete. PR: `<url>`. Ticket moved to Plan Review."

---

## State: Plan Review → Address Feedback

Check the planning PR for review comments. If there are actionable comments, address them. Otherwise, report waiting.

1. Get the repo identifier:
   ```bash
   gh repo view --json nameWithOwner --jq '.nameWithOwner'
   ```

2. Find the planning PR:
   ```bash
   gh pr list --head <ticket-id>/planning --json number,reviewDecision --jq '.[0]'
   ```

3. If no PR exists, something went wrong — report the error and stop.

4. Read review comments:
   ```bash
   gh pr view <number> --json reviews,comments --jq '.reviews[] | select(.state != "APPROVED")'
   gh api repos/<owner>/<repo>/pulls/<number>/comments --jq '.[] | {path, body, line}'
   ```

5. If no reviews, or all reviews are approvals with no unresolved comments:
   Print: "Planning PR has no actionable feedback. Waiting for human review."
   Exit.

6. If there are actionable review comments:
   a. Checkout the planning branch: `gt checkout <ticket-id>/planning --no-interactive`
   b. Analyze which artifacts are affected by the feedback.
   c. Read `references/review-cascade.md` for cascade logic.
   d. Address feedback starting from the earliest affected artifact — read the cascade reference for the re-run rules.
   e. Stage and commit all updated artifacts:
      ```bash
      git add .qrspi/<ticket-id>/*.md
      gt modify -c --no-interactive -m "$(cat <<'EOF'
      <ticket-id>: Address planning review feedback

      Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
      EOF
      )"
      ```
   f. Push: `gt submit --no-edit --no-interactive`
   g. Print: "Review feedback addressed. Updated artifacts: `<list>`. PR updated."

---

## State: Plan Approved → Run Implementation

Implement all slices from `structure.md` and submit a stacked PR per slice.

### Preflight

1. Checkout the planning branch: `gt checkout <ticket-id>/planning --no-interactive`
2. Read `.qrspi/<ticket-id>/structure.md` to count slices and extract each slice's goal.
3. Read `.qrspi/<ticket-id>/plan.md` and `.qrspi/<ticket-id>/worktree.md`.
4. Check for existing slice branches (for resumability).

### Slice execution

For each slice N (starting from 1):

1. If slice branch already exists with code committed, skip to the next slice.

2. Ensure you're on the correct parent branch:
   - Slice 1: parent is `<ticket-id>/planning`
   - Slice N>1: parent is `<ticket-id>/slice-<N-1>`
   ```bash
   gt checkout <parent-branch> --no-interactive
   ```

3. Read `.claude/skills/qrspi-implement/SKILL.md` for implementation instructions.

4. Spawn a sub-agent with ONLY these inputs (context firewall):
   - From `structure.md`: the Types, Contracts, and Slice N sections only
   - From `plan.md`: the Slice N section only
   - From `worktree.md`: the session for this slice only
   - From `impl-log.md`: the "Notes for next session" from the previous slice (if exists)
   - Instruction: "Implement slice N. Write code, run tests, append results to `.qrspi/<ticket-id>/impl-log.md`. Do not commit. Do not run git commands."

5. After the sub-agent completes, stage its changes and create the slice branch:
   ```bash
   # Stage only files changed/created by this slice (use git status to identify them)
   git add <files changed by slice N>
   gt create <ticket-id>/slice-<N> --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Slice <N> — <slice goal>

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

6. Print: "Slice `<N>`/`<total>` complete — `<goal>`"

### Generate PR summary

After all slices are implemented, generate a PR summary for reviewers.

1. Read `.claude/skills/qrspi-pr/SKILL.md` for the PR summary instructions.
2. Spawn a sub-agent with:
   - The PR skill instructions (omit frontmatter, approval messaging, upload sections)
   - Paths to `impl-log.md`, `design.md` (risk register), `structure.md` (contracts)
   - Instruction: "Generate the PR summary. Write to `.qrspi/<ticket-id>/pr-summary.md`. Use `git diff main...HEAD --stat` and `git diff main...HEAD` to see all changes. Do not wait for approval. Do not upload to Linear."
3. Verify `pr-summary.md` exists.

### Submit and transition

1. Submit the entire stack:
   ```bash
   gt submit --stack --no-edit --no-interactive
   ```
2. Capture PR URLs and PR numbers from the output.
3. Set the PR summary as the body on the bottom slice PR (slice-1), which gives reviewers full context at the stack's entry point:
   ```bash
   gh pr edit <slice-1-pr-number> --body "$(cat .qrspi/<ticket-id>/pr-summary.md)"
   ```
4. For each subsequent slice PR, set a focused body with that slice's goal and impl-log entry:
   ```bash
   gh pr edit <slice-N-pr-number> --body "<slice N goal from structure.md and impl-log entry>"
   ```
5. Update Linear status to `Code Review`:
   Call `mcp__linear-russelltsherman__save_issue` with `id: "<ticket-id>"` and `state: "Code Review"`.
6. Upload `impl-log.md` and `pr-summary.md` to Linear.
7. Print: "Implementation complete. `<N>` PRs submitted. Ticket moved to Code Review."

---

## State: Code Review → Address Feedback

Check the implementation PR stack for review comments and address them.

1. Get the repo identifier (same as planning review).

2. Find all slice PRs:
   ```bash
   for branch in $(gt log short --no-interactive | grep '<ticket-id>/slice-'); do
     gh pr list --head "$branch" --json number,title,reviewDecision
   done
   ```

3. Read review comments for each PR:
   ```bash
   gh api repos/<owner>/<repo>/pulls/<number>/comments --jq '.[] | {path, body, line}'
   ```

4. If no actionable comments on any PR:
   Print: "Implementation PRs have no actionable feedback. Waiting for human review."
   Exit.

5. If there are actionable comments:
   a. Group comments by slice.
   b. Start from the **lowest-numbered** slice with feedback (changes propagate upward).
   c. For each affected slice:
      - Checkout: `gt checkout <ticket-id>/slice-<N> --no-interactive`
      - Spawn a sub-agent with the review comments and the relevant code context.
        Instruction: "Address these review comments. Modify the code as requested. Do not commit."
      - Stage and commit changes:
        ```bash
        git add <files modified to address feedback>
        gt modify --no-interactive -m "$(cat <<'EOF'
        <ticket-id>: Address review feedback on slice <N>

        Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
        EOF
        )"
        ```
      - `gt modify` automatically restacks all descendant branches.
   d. Re-submit the stack: `gt submit --stack --no-edit --no-interactive`
   e. Print: "Review feedback addressed on slices `<list>`. Stack updated."

---

## State: Code Approved → Ready to Merge

The code is approved. Merging and cleanup are human-owned operations.

Print the following instructions:

```
Ticket <ticket-id> is approved and ready to merge.

To merge:
1. Restack implementation onto main:
   gt checkout <ticket-id>/slice-1 --no-interactive
   gt move --onto main --no-interactive
   gt submit --stack --no-edit --no-interactive

2. Merge the stack:
   gt merge --confirm --no-interactive

3. Delete the planning branch:
   gt delete <ticket-id>/planning --force --no-interactive

4. Sync:
   gt sync --force --no-interactive

5. Update ticket status to Done in Linear.
```

---

## Resumability

Before creating any branch or artifact, check if it already exists:

- **Branch exists?** Check `gt log short --no-interactive` output.
- **Artifact exists?** Check if `.qrspi/<ticket-id>/<artifact>.md` is present and non-empty.

If the planning branch exists but not all artifacts are written:
1. Checkout the planning branch.
2. Find the last completed artifact (in order: questions, research, design, structure, plan, worktree).
3. Resume from the next incomplete phase.

If all artifacts exist but the PR hasn't been submitted, just submit.

If slice branches partially exist, resume from the first missing slice.

---

## Artifact Upload

To upload an artifact to the Linear issue:

1. Get file size: `wc -c < <filepath>` via Bash
2. Call `mcp__linear-russelltsherman__prepare_attachment_upload` with:
   - `issue: "<ticket-id>"`
   - `filename: "<filename>"`
   - `contentType: "text/markdown"`
   - `size: <byte count>`
3. Run curl: `curl -s -X PUT --data-binary @<filepath>` with all headers from the upload response, to the signed URL
4. Call `mcp__linear-russelltsherman__create_attachment_from_upload` with:
   - `issue: "<ticket-id>"`
   - `assetUrl` from step 2
   - `title: "<descriptive title>"`

If any upload step fails, report the error but continue — the local artifact is safe.

---

## Sub-Agent Rules

1. Read the per-phase SKILL.md for the phase you're about to run.
2. Extract core instructions — skip frontmatter, "After writing" approval messaging, and "Upload artifact" sections.
3. Build the prompt with the extracted instructions, specific inputs, and these directives:
   - "Write the artifact to `<exact path>`. Do not wait for approval. Do not upload to Linear. Do not commit or run any git/gt commands."
   - "Your working directory is `<absolute path to project root>`. Only read and write files within this directory. Do not access files outside the project."
4. Use the Agent tool with `mode: "auto"`.
5. After the sub-agent completes, verify the output file exists and is non-empty.
6. If the sub-agent fails, print the error and STOP. Do not update Linear status on failure.

### Error surfacing (MUST include verbatim in every sub-agent prompt)

Include this exact block in every sub-agent prompt:

> HARD CONSTRAINT: If any command fails with a permissions error, auth failure, config error, or tooling error (EACCES, permission denied, token expired, command not found, config inaccessible): STOP IMMEDIATELY. Print the exact failing command and exact error output. Do not execute any further commands. Do not investigate. Do not attempt workarounds. Do not use alternate tools. Do not modify configuration. Exit and report the error. This is non-negotiable — "let me just try one thing" is the exact failure mode this rule prevents.

### Project scope

All sub-agents are scoped to the current project directory. Include the absolute project root path in every sub-agent prompt. Sub-agents must not read, explore, or reference files outside the project. If the ticket references external systems or repos, the sub-agent should note the reference but not navigate to those locations.

### Questions phase — no codebase exploration

The questions sub-agent generates questions FROM the ticket content alone. It does not explore the codebase — that is the research phase's job. The questions agent should not use Read, Glob, Grep, or Bash to look at project files. Its only input is the ticket content, and its only output is questions about what to investigate.

### Research firewall

The research sub-agent must never receive ticket content or have access to Linear MCP tools. Its only input is `questions.md`. This is a deliberate design constraint to prevent anchoring bias — the research phase maps the codebase from questions alone.

---

## Git/Graphite Rules

- All `gt` commands include `--no-interactive`.
- All commit messages use heredoc format and include the co-authorship trailer.
- The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit.
- Never run raw `git` commands when a `gt` equivalent exists.
- After mutations, run `gt log short --no-interactive` to verify stack state.

### Staging — NEVER use `-a` flag

The `-a` flag stages ALL files in the working directory, including untracked files unrelated to this ticket. This will capture other work-in-progress and pollute the branch. Additionally, `gt undo` after a `-a` commit will **destroy** those untracked files.

Always stage specific files before committing:

```bash
# Stage only the artifact(s) for this ticket
git add .qrspi/<ticket-id>/questions.md

# Then create/modify without -a or -u
gt create <branch-name> --no-interactive -m "..."
gt modify -c --no-interactive -m "..."
```

For implementation slices, stage only the files the sub-agent wrote:
```bash
git add <specific files changed by the slice>
gt create <ticket-id>/slice-<N> --no-interactive -m "..."
```

Use `git status --short` after staging to verify only intended files are staged before committing.

---

## Error Handling

- If a sub-agent fails → print the error, stop, do not update Linear.
- If a `gt` command fails → print the command and error, stop.
- If the Linear status is unrecognized → print the status, ask the user.
- If a PR can't be found for a branch → report the error, suggest checking GitHub.
- Never partially update state — either a full phase transition succeeds or nothing changes.

### HARD STOP: Infrastructure Errors Are Not Puzzles To Solve

This is a non-negotiable constraint. There is NO exception.

When ANY operation fails due to permissions, authentication, configuration, or tooling errors (e.g., `EACCES`, `permission denied`, auth token expired, config file inaccessible, tool not found):

1. **STOP. Do not execute another command.** Not "one more try." Not "let me investigate." Not "let me try a different approach." STOP.
2. **Print the exact error verbatim** — the full command that failed and the full error output, unmodified.
3. **Exit the skill.** Do not continue to subsequent phases. Do not attempt partial progress.

**Explicitly forbidden responses to infrastructure errors:**
- Changing directory ownership or permissions (`chmod`, `chown`)
- Setting environment variables to route around config paths (`XDG_CONFIG_HOME`, etc.)
- Copying config files to alternate locations
- Deleting or recreating configuration directories
- Using an alternate tool (e.g., raw `git` instead of `gt`) to bypass the broken one
- Retrying with `sudo` or escalated permissions
- Any action whose purpose is "make the failing tool work again"

**Why this is absolute:** The orchestrator rationalizes "I'll just try one quick thing" — then tries 5 things, each more destructive than the last. The first workaround masks the root cause. The second corrupts state. The third deletes configuration another process depends on. By then the damage exceeds the original error by orders of magnitude. The ONLY safe response is to stop and let the human fix their environment.

**The internal rationalization "I know I should stop, but let me just..." is the exact failure mode this rule prevents. If you are thinking that thought, you are violating this rule.**
