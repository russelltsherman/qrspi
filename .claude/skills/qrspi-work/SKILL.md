---
name: qrspi-work
description: "Single entry point for autonomous QRSPI feature development. Use when the user asks to 'work on' a ticket (e.g., 'work on RUS-42'). Reads the ticket's Linear status, determines the current phase, and executes the appropriate action — planning, implementation, or review response — without manual phase-by-phase invocation. Trigger on any variant of: 'work on <ticket-id>', 'continue <ticket-id>', 'pick up <ticket-id>', or any reference to progressing a QRSPI ticket through its lifecycle."
command: /qrspi-work
argument-hint: <ticket-id>
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent, mcp__linear-russelltsherman__get_issue, mcp__linear-russelltsherman__get_issue_status, mcp__linear-russelltsherman__save_issue, mcp__linear-russelltsherman__list_issue_statuses, mcp__linear-russelltsherman__save_comment
---

# QRSPI Work Orchestrator

You are a state machine. Read the ticket's Linear status and execute the matching action. Run autonomously within a stage, but stop at the two human review gates — **Design Review** (after the design half: questions, research, design) and **Plan Review** (after the plan half: structure, plan, work tree). Print verbose progress so the operator can observe.

## Entry Point

1. Parse `$ARGUMENTS` to extract `<ticket-id>`.
2. **ALWAYS re-read the Linear ticket status, even if you have it in context from a prior invocation.** The ticket's state machine is authoritative and may have changed since the last call. Never skip this step or trust cached context.
3. Fetch the ticket: call `mcp__linear-russelltsherman__get_issue` with identifier `<ticket-id>`.
   - If the call fails, retry **once**.
   - If the retry fails, this is a **hard stop error** — print the exact error and exit. Do not proceed with any other work.
4. Read the ticket's status name.
5. If status is `Done`, skip worktree setup and dispatch directly to [Cleanup](#state-done--cleanup).
6. Set up the worktree (see [Worktree Setup](#worktree-setup)).
7. Dispatch to the matching state section below.
8. If the status doesn't match any known state, print the status and ask the user what to do.

---

## Worktree Setup

Every ticket gets its own git worktree at `.worktrees/<ticket-id>/` (relative to the main repo root). This allows multiple agents to work on different tickets concurrently without branch checkout conflicts.

**Set `REPO_ROOT`** to the absolute path of the main repository (where `.git/` lives — NOT a worktree).

**Set `WORKTREE_PATH`** to `<REPO_ROOT>/.worktrees/<ticket-id>`.

### Case 1: Worktree already exists

```bash
if [ -d "<WORKTREE_PATH>" ]; then
  cd "<WORKTREE_PATH>"
fi
```

Print: "Using existing worktree at `.worktrees/<ticket-id>/`"

### Case 2: Branch exists, no worktree

Check if a ticket branch exists (planning or slice):
```bash
git branch --list '<ticket-id>/*' 2>/dev/null
```

If a branch is found but is currently checked out in the main repo, free it first:
```bash
# From REPO_ROOT — if main repo is on the ticket branch, return it to main
current_branch=$(git -C "<REPO_ROOT>" branch --show-current)
if echo "$current_branch" | grep -q '<ticket-id>'; then
  git -C "<REPO_ROOT>" checkout main
fi
```

Then create the worktree:
```bash
mkdir -p "<REPO_ROOT>/.worktrees"
git worktree add "<WORKTREE_PATH>" <ticket-id>/planning 2>/dev/null || \
git worktree add "<WORKTREE_PATH>" <ticket-id>/slice-1
cd "<WORKTREE_PATH>"
```

Print: "Created worktree for `<ticket-id>` from existing branch."

### Case 3: New ticket, no branch

```bash
mkdir -p "<REPO_ROOT>/.worktrees"
git worktree add -b <ticket-id>/planning "<WORKTREE_PATH>" main
cd "<WORKTREE_PATH>"
gt track --parent main --no-interactive
```

Print: "Created worktree for `<ticket-id>` with new planning branch."

### After setup

All subsequent commands in this skill run from **inside the worktree** (`WORKTREE_PATH`). The working directory must remain in the worktree for the duration of this invocation.

**CRITICAL — sub-agents do NOT inherit your cwd.** The Agent tool spawns a fresh context whose Bash session starts at the main repo root, not at your cd'd worktree. Every sub-agent prompt must include:
1. An explicit `cd <WORKTREE_PATH>` as its first Bash command
2. Absolute paths (prefixed with `<WORKTREE_PATH>/`) for ALL file operations (Read, Write, Edit, Glob, Grep)

Never pass relative paths like `.qrspi/<ticket-id>/...` to a sub-agent — always pass `<WORKTREE_PATH>/.qrspi/<ticket-id>/...`.

## State Dispatch

| Linear Status | Action |
|---|---|
| `Backlog` or `Selected` | → [Run Design](#state-backlog--selected--run-design) |
| `Design Review` | → [Address Design Feedback](#state-design-review--address-design-feedback) |
| `Design Approved` | → [Run Plan](#state-design-approved--run-plan) |
| `Plan Review` | → [Address Planning Feedback](#state-plan-review--address-feedback) |
| `Plan Approved` | → [Run Implementation](#state-plan-approved--run-implementation) |
| `Code Review` | → [Address Implementation Feedback](#state-code-review--address-feedback) |
| `Code Approved` | → [Report Ready to Merge](#state-code-approved--ready-to-merge) |
| `Done` | → [Cleanup](#state-done--cleanup) |

---

## State: Backlog / Selected → Run Design

Produce the three design-half artifacts (questions, research, design) and submit a planning PR for **design** review. Structure, Plan, and Work Tree are produced later, after the Design Review gate (see [Run Plan](#state-design-approved--run-plan)).

### Preflight

The worktree setup (above) has already placed you on the correct branch:
- New tickets: you're on a fresh `<ticket-id>/planning` branch tracked to main.
- Resuming: you're on the existing planning branch.

1. Verify you're in the worktree:
   ```bash
   pwd | grep -q '.worktrees/<ticket-id>' || { echo "ERROR: not in worktree"; exit 1; }
   ```
2. Sync the branch with remote (non-destructive — never use `gt sync` here; it deletes branches whose PRs are merged/closed, destroying ticket work-in-progress):
   ```bash
   gt get --no-interactive 2>&1 || true
   ```
3. Check for existing artifacts to determine resume point (see [Resumability](#resumability)).

### Phase execution

Run each phase by spawning a sub-agent. After each, verify the artifact exists and commit it.

Save the ticket content from the Linear fetch — you'll pass it to some sub-agents below.

**Phase 1 — Questions**

1. Spawn the questions agent via the Agent tool with `subagent_type: qrspi-questions` and `mode: "auto"`. Build the prompt as an input contract:
   - `TICKET_ID = <ticket-id>`
   - `TICKET_CONTENT = <title + description from the Linear fetch>`
   - `ARTIFACT_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/questions.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/questions.md`
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/questions.md` exists and is non-empty.
4. Stage and create the planning commit (this is the ONLY `gt modify -c` during planning — all subsequent artifacts amend this commit):
   ```bash
   git add .qrspi/<ticket-id>/questions.md
   gt modify -c --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Planning

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```
4. Print: "Questions generated. Moving to Research..."

**Phase 2 — Research**

1. Spawn the research agent via the Agent tool with `subagent_type: qrspi-research` and `mode: "auto"`. Build the prompt as an input contract — **DO NOT include the ticket content.** The research firewall is critical and is also enforced by the agent's tool definition (no Linear MCP, no ticket reads):
   - `TICKET_ID = <ticket-id>`
   - `QUESTIONS_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/questions.md`
   - `RESEARCH_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/research.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/research.md`
   - `REPO_ROOT = <WORKTREE_PATH>`
   - Append the project scope restriction block from the section below to the end of the prompt. Replace `REPO_ROOT_VALUE` with the actual `REPO_ROOT` path.
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/research.md` exists and is non-empty.
4. Stage and amend the planning commit:
   ```bash
   git add .qrspi/<ticket-id>/research.md
   gt modify --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Planning

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```
3. Print: "Research complete. Moving to Design..."

**Phase 3 — Design**

1. Spawn the design agent via the Agent tool with `subagent_type: qrspi-design` and `mode: "auto"`. Input contract:
   - `TICKET_ID = <ticket-id>`
   - `TICKET_CONTENT = <title + description from the Linear fetch>`
   - `QUESTIONS_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/questions.md`
   - `RESEARCH_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/research.md`
   - `DESIGN_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/design.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/design.md`
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/design.md` exists.
3. Stage and amend the planning commit: `git add .qrspi/<ticket-id>/design.md` then `gt modify --no-interactive -m "$(cat <<'EOF'`... `<ticket-id>: Planning` ...`EOF`)"`
4. Print: "Design half complete. Submitting for design review..."

### Submit and transition (design review)

1. Check for a stale PR association before submitting (handles a rejected/reworked ticket
   whose earlier planning PR was closed):
   ```bash
   gt info <ticket-id>/planning --no-interactive
   ```
   - If the output shows an associated PR marked `(Closed)` or `(Merged)`: follow
     [Resubmitting when the prior PR was closed or merged](#resubmitting-when-the-prior-pr-was-closed-or-merged)
     — that procedure detaches the dead PR **and** submits with `--force`. Then skip to step 3.
   - Otherwise (open PR, or no PR yet): continue to step 2 with a normal submit.
2. Push and create the PR:
   ```bash
   gt submit --no-edit --no-interactive
   ```
3. Capture the PR URL from the output.
4. Update Linear status to `Design Review`:
   Call `mcp__linear-russelltsherman__save_issue` with `id: "<ticket-id>"` and `state: "Design Review"`.
5. Print: "Design submitted for review. PR: `<url>`. Ticket moved to Design Review."

---

## State: Design Review → Address Design Feedback

Check the planning PR for review comments on the design-half artifacts. If there are
actionable comments, address them. The cascade at this gate is **bounded to Questions →
Research → Design** — Structure, Plan, and Work Tree do not exist yet. Otherwise, report
waiting or advance to the plan half.

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
   a. Re-check Linear status (it may have been updated by the human between calls):
      Call `mcp__linear-russelltsherman__get_issue` with the ticket ID and read the `status` field.
   b. If status is now `Design Approved`, print: "Design approved. Moving to the plan half…" and dispatch to [Run Plan](#state-design-approved--run-plan).
   c. If status is still `Design Review`, print: "Design PR approved with no comments. Waiting for Linear status to transition to Design Approved — update it manually in Linear, or the next invocation will proceed automatically."
   d. Exit.

6. If there are actionable review comments:
   a. Ensure you're on the planning branch:
      ```bash
      git branch --show-current | grep -q '<ticket-id>/planning' || gt checkout <ticket-id>/planning --no-interactive
      ```
   b. Analyze which design-half artifacts are affected (questions, research, design only).
   c. Read `references/review-cascade.md` for cascade logic. At this gate the cascade is bounded: there are no Structure/Plan/Work Tree artifacts to re-run yet.
   d. Address feedback starting from the earliest affected artifact (Questions → Research → Design).
   e. Stage and amend the planning commit:
      ```bash
      git add .qrspi/<ticket-id>/*.md
      gt modify --no-interactive -m "$(cat <<'EOF'
      <ticket-id>: Address design review feedback

      Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
      EOF
      )"
      ```
   f. Push: `gt submit --no-edit --no-interactive`
   g. Print: "Design review feedback addressed. Updated artifacts: `<list>`. PR updated."

---

## State: Design Approved → Run Plan

Produce the three plan-half artifacts (structure, plan, work tree) by amending the existing
planning commit, then submit the completed planning PR for plan review.

### Preflight

1. Ensure you're on the planning branch (worktree setup should have placed you there):
   ```bash
   git branch --show-current | grep -q '<ticket-id>/planning' || gt checkout <ticket-id>/planning --no-interactive
   ```
2. Sync non-destructively (never `gt sync` here — it deletes branches whose PRs are merged/closed):
   ```bash
   gt get --no-interactive 2>&1 || true
   ```
3. Verify the design-half artifacts exist and are non-empty:
   ```bash
   for f in questions.md research.md design.md; do
     if [ ! -f ".qrspi/<ticket-id>/$f" ] || [ ! -s ".qrspi/<ticket-id>/$f" ]; then
       echo "ERROR: Design-half artifact missing or empty: .qrspi/<ticket-id>/$f"
       echo "Ticket is Design Approved but design-half artifacts are missing — regenerate the design half by running /qrspi-work <ticket-id> against a Selected ticket."
       exit 1
     fi
   done
   ```
4. Check for existing plan-half artifacts to determine resume point (see [Resumability](#resumability)).

### Phase execution

Run each phase by spawning a sub-agent. After each, verify the artifact exists and amend the planning commit.

**Phase 4 — Structure**

1. Spawn the structure agent via the Agent tool with `subagent_type: qrspi-structure` and `mode: "auto"`. Input contract:
   - `TICKET_ID = <ticket-id>`
   - `DESIGN_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/design.md`
   - `STRUCTURE_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/structure.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/structure.md`
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/structure.md` exists.
3. Stage and amend the planning commit: `git add .qrspi/<ticket-id>/structure.md` then amend with message `<ticket-id>: Planning`.
4. Print: "Structure complete. Moving to Plan..."

**Phase 5 — Plan**

1. Spawn the plan agent via the Agent tool with `subagent_type: qrspi-plan` and `mode: "auto"`. Input contract:
   - `TICKET_ID = <ticket-id>`
   - `STRUCTURE_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/structure.md`
   - `DESIGN_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/design.md`
   - `PLAN_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/plan.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/plan.md`
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/plan.md` exists.
3. Stage and amend the planning commit: `git add .qrspi/<ticket-id>/plan.md` then amend with message `<ticket-id>: Planning`.
4. Print: "Plan complete. Moving to Work Tree..."

**Phase 6 — Work Tree**

1. Spawn the worktree agent via the Agent tool with `subagent_type: qrspi-worktree` and `mode: "auto"`. Input contract:
   - `TICKET_ID = <ticket-id>`
   - `PLAN_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/plan.md`
   - `WORKTREE_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/worktree.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/worktree.md`
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/worktree.md` exists.
3. Stage and amend the planning commit: `git add .qrspi/<ticket-id>/worktree.md` then amend with message `<ticket-id>: Planning`.
4. Print: "Work tree complete. Submitting planning PR..."

### Submit and transition

1. Check for a stale PR association before submitting (handles a rejected/reworked ticket
   whose earlier planning PR was closed):
   ```bash
   gt info <ticket-id>/planning --no-interactive
   ```
   - If the output shows an associated PR marked `(Closed)` or `(Merged)`: follow
     [Resubmitting when the prior PR was closed or merged](#resubmitting-when-the-prior-pr-was-closed-or-merged)
     — that procedure detaches the dead PR **and** submits with `--force`. Then skip to step 3.
   - Otherwise (open PR, or no PR yet): continue to step 2 with a normal submit.
2. Push and create the PR:
   ```bash
   gt submit --no-edit --no-interactive
   ```
3. Capture the PR URL from the output.
4. Update Linear status to `Plan Review`:
   Call `mcp__linear-russelltsherman__save_issue` with `id: "<ticket-id>"` and `state: "Plan Review"`.
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
   a. Re-check Linear status (it may have been updated by the human between calls):
      ```bash
      mcp__linear-russelltsherman__get_issue --id "<ticket-id>"
      ```
      (Call `mcp__linear-russelltsherman__get_issue` with the ticket ID and read the `status` field.)
   b. If status is now `Plan Approved`, print: "PR approved. Moving to implementation…" and dispatch to [Run Implementation](#state-plan-approved--run-implementation).
   c. If status is still `Plan Review`, print: "Planning PR approved with no comments. Waiting for Linear status to transition to Plan Approved — update it manually in Linear, or the next invocation will proceed automatically."
   d. Exit.

6. If there are actionable review comments:
   a. Ensure you're on the planning branch:
      ```bash
      git branch --show-current | grep -q '<ticket-id>/planning' || gt checkout <ticket-id>/planning --no-interactive
      ```
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

1. Ensure you're on the planning branch (worktree setup should have placed you there):
   ```bash
   git branch --show-current | grep -q '<ticket-id>/planning' || gt checkout <ticket-id>/planning --no-interactive
   ```
2. Validate planning artifacts exist:
   ```bash
   for f in structure.md plan.md worktree.md; do
     if [ ! -f ".qrspi/<ticket-id>/$f" ] || [ ! -s ".qrspi/<ticket-id>/$f" ]; then
       echo "ERROR: Planning artifact missing or empty: .qrspi/<ticket-id>/$f"
       echo "Ticket status is Plan Approved but planning artifacts are missing."
       echo "This can happen if the planning branch was deleted by gt sync."
       echo "Please regenerate planning artifacts by running /qrspi-work <ticket-id> again."
       exit 1
     fi
   done
   ```
3. Read `.qrspi/<ticket-id>/structure.md` to count slices and extract each slice's goal.
4. Read `.qrspi/<ticket-id>/plan.md` and `.qrspi/<ticket-id>/worktree.md`.
5. Check for existing slice branches (for resumability).

### Slice execution

For each slice N (starting from 1):

1. If slice branch already exists with code committed, skip to the next slice.

2. Ensure you're on the correct parent branch:
   - Slice 1: parent is `<ticket-id>/planning`
   - Slice N>1: parent is `<ticket-id>/slice-<N-1>`
   ```bash
   gt checkout <parent-branch> --no-interactive
   ```

3. Extract slice-scoped sections from the planning artifacts:
   - `STRUCTURE_SLICE` ← Types + Contracts + Slice N sections from `<WORKTREE_PATH>/.qrspi/<ticket-id>/structure.md`
   - `PLAN_SLICE` ← Slice N section from `<WORKTREE_PATH>/.qrspi/<ticket-id>/plan.md`
   - `WORKTREE_SESSION` ← session for slice N from `<WORKTREE_PATH>/.qrspi/<ticket-id>/worktree.md`
   - `PREVIOUS_NOTES` ← "Notes for next session" from the previous slice's impl-log entry, or empty for slice 1

4. Spawn the implement agent via the Agent tool with `subagent_type: qrspi-implement` and `mode: "auto"`. Input contract (see [Project scope](#project-scope) for the scope restriction block to append):
   - `TICKET_ID = <ticket-id>`
   - `SLICE_NUMBER = N`
   - `WORKTREE_DIR = <WORKTREE_PATH>`
   - `STRUCTURE_SLICE = <extracted text>`
   - `PLAN_SLICE = <extracted text>`
   - `WORKTREE_SESSION = <extracted text>`
   - `PREVIOUS_NOTES = <extracted text or empty>`
   - `IMPL_LOG_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/impl-log.md`
   - `IMPL_LOG_TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/impl-log.md`

5. After the sub-agent completes, identify ALL changed files, stage them, and create the slice branch:
   ```bash
   # List every modified, added, and untracked file
   git status --short
   ```
   Parse the output. Stage EVERY file shown (modified `M`, added `A`, untracked `??`) — these are all products of this slice. Do NOT cherry-pick only `.qrspi/` files; the implementation code IS the deliverable.
   ```bash
   git add <every file from git status output>
   ```
   Verify staging is correct before committing:
   ```bash
   git status --short
   # All files should show as staged (green). If any unstaged files remain, stage them.
   ```
   Then create the branch:
   ```bash
   gt create <ticket-id>/slice-<N> --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Slice <N> — <slice goal>

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

6. Print: "Slice `<N>`/`<total>` complete — `<goal>`"

### Generate PR summary

After all slices are implemented, generate a PR summary for reviewers.

1. Spawn the PR agent via the Agent tool with `subagent_type: qrspi-pr` and `mode: "auto"`. Input contract:
   - `TICKET_ID = <ticket-id>`
   - `IMPL_LOG_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/impl-log.md`
   - `DESIGN_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/design.md`
   - `STRUCTURE_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/structure.md`
   - `PR_SUMMARY_PATH = <WORKTREE_PATH>/.qrspi/<ticket-id>/pr-summary.md`
   - `TEMPLATE_PATH = <WORKTREE_PATH>/.qrspi/templates/pr-summary.md`
   - `REPO_ROOT = <WORKTREE_PATH>`
2. Verify `<WORKTREE_PATH>/.qrspi/<ticket-id>/pr-summary.md` exists.
4. Stage and amend the PR summary into the last slice commit:
   ```bash
   git add .qrspi/<ticket-id>/pr-summary.md
   gt modify --no-interactive
   ```

### Submit and transition

1. Check each stack branch for a stale PR association before submitting (handles a reworked
   ticket whose earlier slice PRs were closed):
   ```bash
   for branch in $(gt log short --no-interactive | grep -oE '<ticket-id>/(planning|slice-[0-9]+)'); do
     gt info "$branch" --no-interactive | grep -qE '\((Closed|Merged)\)' && echo "STALE: $branch"
   done
   ```
   For every branch printed as `STALE`, checkout that branch and run the rename-detach cycle from
   [Resubmitting when the prior PR was closed or merged](#resubmitting-when-the-prior-pr-was-closed-or-merged)
   (rename away, rename back). You do not need to submit each one individually — the stack submit
   in step 2 covers them, but it must use `--force` if ANY branch was detached (the deleted remote
   branches leave stale force-with-lease refs). Leave branches with an **open** PR untouched.
2. Submit the entire stack (add `--force` if step 1 detached any stale branch):
   ```bash
   gt submit --stack --no-edit --no-interactive            # normal case
   gt submit --stack --force --no-edit --no-interactive    # if any branch was detached in step 1
   ```
3. Capture PR URLs and PR numbers from the output.
4. Set the PR summary as the body on the bottom slice PR (slice-1), which gives reviewers full context at the stack's entry point:
   ```bash
   gh pr edit <slice-1-pr-number> --body "$(cat .qrspi/<ticket-id>/pr-summary.md)"
   ```
5. For each subsequent slice PR, set a focused body with that slice's goal and impl-log entry:
   ```bash
   gh pr edit <slice-N-pr-number> --body "<slice N goal from structure.md and impl-log entry>"
   ```
6. Update Linear status to `Code Review`:
   Call `mcp__linear-russelltsherman__save_issue` with `id: "<ticket-id>"` and `state: "Code Review"`.
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
   a. Re-check Linear status (it may have been updated by the human between calls):
      ```bash
      mcp__linear-russelltsherman__get_issue --id "<ticket-id>"
      ```
      (Call `mcp__linear-russelltsherman__get_issue` with the ticket ID and read the `status` field.)
   b. If status is now `Code Approved`, print: "PRs approved. Moving to merge instructions…" and dispatch to [Report Ready to Merge](#state-code-approved--ready-to-merge).
   c. If status is still `Code Review`, print: "Implementation PRs have no actionable feedback. Waiting for Linear status to transition to Code Approved — update it manually in Linear, or the next invocation will proceed automatically."
   d. Exit.

5. If there are actionable comments:
   a. Group comments by slice.
   b. Start from the **lowest-numbered** slice with feedback (changes propagate upward).
   c. For each affected slice:
      - Checkout: `gt checkout <ticket-id>/slice-<N> --no-interactive`
      - Spawn a sub-agent with the review comments and the relevant code context.
        Instruction: "Before any other command, run: `cd <WORKTREE_PATH>`. ALL file paths must be absolute, prefixed with `<WORKTREE_PATH>/`. Address these review comments. Modify the code as requested. Do not commit."
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
1. Return to main repo (worktree operations need the main checkout):
   cd <REPO_ROOT>

2. Restack implementation onto main:
   gt checkout <ticket-id>/slice-1 --no-interactive
   gt move --onto main --no-interactive
   gt submit --stack --no-edit --no-interactive

3. Merge the stack:
   gt merge --confirm --no-interactive

4. Delete the planning branch:
   gt delete <ticket-id>/planning --force --no-interactive

5. Sync:
   gt sync --force --no-interactive

6. Update ticket status to Done in Linear.

After marking Done, run `work on <ticket-id>` to clean up artifacts and worktree.
```

---

## State: Done → Cleanup

Remove planning artifacts, impl-log, and PR summary from the repo after the ticket's PRs have been merged. This runs from `REPO_ROOT` on `main` — no worktree needed.

1. Ensure you are on `main` in the main repo:
   ```bash
   cd "<REPO_ROOT>"
   git checkout main
   gt sync --force --no-interactive
   ```

2. Check whether artifacts still exist:
   ```bash
   ls -d .qrspi/<ticket-id>/ 2>/dev/null
   ```
   If the directory does not exist, print: "Ticket `<ticket-id>` is complete. No artifacts to clean up." and exit.

3. Remove the artifact directory:
   ```bash
   git rm -r .qrspi/<ticket-id>/
   ```

4. Commit the removal:
   ```bash
   gt create <ticket-id>/cleanup --no-interactive -m "$(cat <<'EOF'
   <ticket-id>: Remove planning artifacts

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
   EOF
   )"
   ```

5. Submit and merge the cleanup PR:
   ```bash
   gt submit --no-edit --no-interactive
   gt merge --confirm --no-interactive
   gt sync --force --no-interactive
   ```

6. Clean up the worktree if it still exists:
   ```bash
   if [ -d "<REPO_ROOT>/.worktrees/<ticket-id>" ]; then
     git worktree remove "<REPO_ROOT>/.worktrees/<ticket-id>" --force
     git worktree prune
   fi
   ```

7. Print: "Ticket `<ticket-id>` cleanup complete. Artifacts removed, worktree pruned."

---

## Resumability

Before creating any branch or artifact, check if it already exists:

- **Branch exists?** Check `gt log short --no-interactive` output.
- **Artifact exists?** Check if `<WORKTREE_PATH>/.qrspi/<ticket-id>/<artifact>.md` is present and non-empty.

**The planning artifacts are gated into two halves.** The Linear status — not artifact presence — decides which half to run: `Backlog`/`Selected` → design half (questions, research, design); `Design Approved` → plan half (structure, plan, work tree). `Design Review` and `Plan Review` are human turns — wait or address feedback, never advance autonomously. Never produce a plan-half artifact while the status is still `Selected` or `Design Review`.

If the planning branch exists but not all artifacts in the current half are written:
1. The worktree setup already placed you on the planning branch.
2. Find the last completed artifact within the current half (design half: questions → research → design; plan half: structure → plan → work tree).
3. Resume from the next incomplete phase in that half.

If all artifacts exist but the PR hasn't been submitted, just submit.

If slice branches partially exist, resume from the first missing slice.

---

## Sub-Agent Rules

The orchestrator dispatches each phase to a purpose-built agent defined in `.claude/agents/qrspi-<phase>.md`. Each agent has its own tool lockdown and hard-constraint block. The orchestrator does NOT read phase SKILL.md files or hand-engineer prompts — it spawns by `subagent_type` with a structured input contract.

1. Spawn via the `Agent` tool with `subagent_type: qrspi-<phase>` and `mode: "auto"`.
2. Build the prompt as a labelled input contract — see each phase section above for the exact inputs that agent expects.
3. Use absolute paths prefixed with `<WORKTREE_PATH>/` for every artifact, template, and repo-root reference.
4. After the agent returns, verify the output artifact exists at its absolute worktree path and is non-empty.
5. If the sub-agent fails or its artifact is missing, print the error and STOP. Do not update Linear status on failure.

### Research firewall

The research agent's tool definition includes no Linear MCP and forbids reading the ticket. The orchestrator must also NOT include `TICKET_CONTENT` in the research agent's input contract — only `QUESTIONS_PATH`, `RESEARCH_PATH`, `TEMPLATE_PATH`, and `REPO_ROOT`. Defense in depth.

### Project scope firewall (research)

The research agent MUST NOT read files outside the project repo. When building the research agent prompt, append this constraint block. **Replace all occurrences of `REPO_ROOT_VALUE` with the actual `REPO_ROOT` value** (e.g., `/workspaces/qrspi/.worktrees/RUS-5`) before including it.

```
## Project scope restriction

You are researching the codebase for a specific ticket. ALL file reads must be inside the project repository at REPO_ROOT_VALUE/.

BEFORE reading ANY file, validate its path starts with REPO_ROOT_VALUE/. If it does not, skip it and note the gap.

DO NOT read:
- ~/.claude/, ~/.config/, ~/ (home directory)
- System config files (/etc/, /usr/, /var/)
- Files in any other project's directories
- Global skill definitions outside the repo
- Any path that does not start with REPO_ROOT_VALUE/

This is a hard boundary. If the questions imply information that may live outside the repo, note it as an unanswerable gap rather than escaping the project.
```

Always include this block in every research agent prompt. It is the orchestrator-level complement to the agent's own tool-level restrictions.

### Questions firewall

The questions agent's tool definition excludes `Glob`, `Grep`, and `Bash` so codebase exploration is structurally impossible. No special orchestrator handling required.

### Project scope

Every agent's hard-constraints block forbids reads outside its inputs. Pass absolute worktree-prefixed paths only; do not pass relative paths to sub-agents.

**When spawning implement agents, append this constraint block to their prompt. Replace all occurrences of `WORKTREE_DIR_VALUE` with the actual `WORKTREE_DIR` value before including it.**

```
## Project scope restriction

You are implementing work for a ticket. ALL file reads and modifications must be inside the project repository at WORKTREE_DIR_VALUE/.

BEFORE reading or writing ANY file, validate its path starts with WORKTREE_DIR_VALUE/. If it does not, skip it and report the error.

DO NOT modify:
- ~/.claude/, ~/.config/, ~/ (home directory)
- System config files (/etc/, /usr/, /var/)
- Global skill definitions in ~/.claude/skills/
- Any path that does not start with WORKTREE_DIR_VALUE/

The plan may contain paths like `~/.claude/skills/...`. If the plan targets global scope, refuse to make those changes and report the issue. The deliverable for a ticket must live within the project repo.

This is a hard boundary. If the plan references files outside the project, report the error and STOP.
```

---

## Git/Graphite Rules

- All `gt` commands include `--no-interactive`.
- All commit messages use heredoc format and include the co-authorship trailer.
- The orchestrator is the ONLY place git/graphite operations happen — sub-agents never commit.
- Never run raw `git` commands when a `gt` equivalent exists.
- After mutations, run `gt log short --no-interactive` to verify stack state.
- **Planning uses a single commit.** Phase 1 (Questions) creates the commit with `gt modify -c`. Phases 2–6 amend it with `gt modify` (no `-c`). The commit message is always `<ticket-id>: Planning`.

### Resubmitting when the prior PR was closed or merged

Graphite pins each branch to the first PR it created for it, in `.git/.graphite_pr_info`.
When a task is **rejected and reworked** (PR closed) or a PR was squash-merged and its
remote branch deleted, that association becomes stale: the local branch still points at a
dead PR. `gt submit` then refuses to open a fresh PR — it tries to reuse the closed/merged
one and fails (e.g. `PR ... has already been merged or closed`). `gt untrack` + `gt track`
does **not** clear this; the association survives.

Recovery takes **two** steps — both are required (verified empirically):

1. **Detach the dead PR with `gt rename`.** GitHub PR branch names are immutable, so renaming a
   branch drops its PR association; renaming straight back restores the canonical name with the
   stale PR cleared. (`gt submit --force` alone does NOT work — Graphite rejects the closed-PR
   association during stack validation, *before* any push, so force-push never runs.)
2. **Submit with `--force`.** Because the old remote branch was deleted, a plain `gt submit`
   fails with `Force-with-lease push failed due to external changes to the remote branch`. The
   `--force` flag bypasses the stale force-with-lease ref. (`--force` here is safe: the remote
   branch is gone, so there is nothing of value to overwrite.)

```bash
# Run from the worktree, on the branch being submitted.
gt rename <branch>-stale --no-interactive   # 1a. detaches the dead PR
gt rename <branch>        --no-interactive   # 1b. restores the canonical name
gt info <branch> --no-interactive            #     confirm: no "PR #… (Closed)/(Merged)" line remains
gt submit --force --no-edit --no-interactive #  2. creates a brand-new PR
```

**Run the four commands as one uninterrupted sequence.** The detach clears the in-memory
association, but `.git/.graphite_pr_info` still holds the branch→PR mapping; any other `gt`
command run between the rename-back and the submit can re-hydrate the closed-PR association and
re-block the submit. Detach, confirm, submit — nothing else in between.

**This is a recognized workflow state, not an infrastructure error — the HARD STOP rule does
not apply here.** Only apply this when `gt info` shows an associated PR in state `(Closed)` or
`(Merged)`; never rename a branch with an **open** PR (that would orphan the open PR), and never
use `--force` on the normal (non-recovery) submit path — that path relies on `--force-with-lease`
for safety.

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

For implementation slices, run `git status --short` after the sub-agent completes, then stage EVERY file shown — implementation code, test files, and artifacts are all products of the slice:
```bash
git status --short                    # identify all changed/new files
git add <every file from the output>  # stage ALL of them
git status --short                    # verify everything is staged
gt create <ticket-id>/slice-<N> --no-interactive -m "..."
```

Use `git status --short` after staging to verify only intended files are staged before committing.

---

## Worktree Management

### Invariants

- One worktree per ticket. Path is always `<REPO_ROOT>/.worktrees/<ticket-id>/`.
- `.worktrees/` is gitignored — worktrees are local-only and ephemeral.
- A worktree is a full checkout. All files (source, .qrspi/ artifacts, configs) exist there.
- Multiple worktrees share the same `.git/` metadata (branches, graphite stack info).
- You cannot have the same branch checked out in two worktrees simultaneously.

### Creating worktrees from the main repo

All `git worktree add` commands must run from the main repo root (`REPO_ROOT`), NOT from inside an existing worktree. The `cd` into the worktree happens AFTER creation.

### gt in worktrees

Graphite commands work normally in worktrees. The one requirement is that new branches must be tracked:
```bash
gt track --parent <parent-branch> --no-interactive
```
This is only needed once per branch — when first created via `git worktree add -b`.

### Stale worktree recovery

If `git worktree add` fails because a worktree path already exists but is broken:
```bash
git worktree remove "<WORKTREE_PATH>" --force 2>/dev/null
git worktree prune
git worktree add ...  # retry
```

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
