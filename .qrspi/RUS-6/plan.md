# Plan — using graphite cli skill

**Design basis:** design.md @ 2026-05-27
**Structure basis:** structure.md @ 2026-05-27
**Generated:** 2026-05-27
**Status:** draft

## Slice 1: Create using-graphite-cli SKILL.md

**Goal:** Produce the complete `using-graphite-cli` skill file with YAML frontmatter and 11 content sections covering the full Graphite CLI reference needed by QRSPI agents.

**Step 1.1: Write SKILL.md**

Create `.claude/skills/using-graphite-cli/SKILL.md` with:

1. **YAML frontmatter** (matching existing skill convention, e.g., qrspi-work):
   - `name: using-graphite-cli`
   - `description`: "Guide for using the Graphite CLI (`gt`) for stacked PR workflows. Covers initialization, core workflow, branch navigation, stacking, PR submission, and merging."
   - `command: /using-graphite-cli`
   - `argument-hint: none`
   - `allowed-tools: Bash, Read`

2. **Graphite CLI Primer** — Explain core concepts: trunk (main), stacks (branch sequences), upstack/downstack relationships, and the `gt` philosophy of treating branches as a stack data structure. Reference `gt log` for visualizing the stack.

3. **Initialization** — Document `gt init` (no flags needed, sets up Graphite tracking in the repo) and `gt auth --token` (for headless/CI authentication). Include the prerequisite that the repo must be a git repository.

4. **Core Workflow** — Codify the create-modify-submit loop:
   - `gt create <branch> --no-interactive -m "..."` to start work on a new branch
   - `gt modify -c --no-interactive -m "..."` for the planning commit (first commit on branch)
   - `gt modify --no-interactive` for subsequent amends (no `-c`)
   - `gt submit --no-edit --no-interactive` to push and update the PR

5. **Branch Navigation** — Document stack traversal:
   - `gt checkout <branch> --no-interactive` to switch to a specific branch
   - `gt up` / `gt down` to move one level in the stack
   - `gt bottom` / `gt top` to jump to the first or last branch
   - `gt trunk` to return to the trunk branch

6. **Single Commit Per Branch** — Encode the project convention:
   - Planning phase: `gt modify -c` creates the single commit
   - Subsequent phases: `gt modify` (no `-c`) amends the existing commit
   - This keeps the branch history linear and the PR clean

7. **Restacking** — Explain two restacking mechanisms:
   - Automatic: `gt modify` automatically restacks all descendant branches after a commit
   - Explicit: `gt sync --force --no-interactive` to restack the entire stack (e.g., after manual git operations)
   - When to use each (modify for normal workflow, sync for recovery)

8. **Submitting PRs** — Distinguish submit modes:
   - `gt submit --no-edit --no-interactive` submits the current branch plus its downstack
   - `gt submit --stack --no-edit --no-interactive` submits the entire stack as one PR
   - Flag summary: `--no-edit` (skip editor), `--no-interactive` (no prompts)

9. **Downstack/Upstack Operations** — Cover structural changes:
   - `gt move --onto <new-parent> --no-interactive` to re-parent a branch in the stack
   - `gt delete <branch> --force --no-interactive` to remove a branch
   - `--downstack` / `--upstack` flags where applicable

10. **Merging Stacks** — Document the merge workflow:
    - `gt merge --confirm --no-interactive` to merge the entire stack into trunk
    - `gt delete <branch> --force --no-interactive` for cleanup of merged branches
    - `gt sync --force --no-interactive` to finalize

11. **Integration with GitHub** — Define the division of labor:
    - `gt` handles stack-aware operations (branch creation, stacking, PR creation/update via submit)
    - `gh` handles GitHub-specific read operations (review comments, PR views via `gh pr view`, `gh api`)
    - `gt` never directly edits GitHub PR descriptions — that is `gh pr edit`'s job

12. **Scope Guidance** — Provide a decision table:
    - Stack-aware operations (create, modify, stack, submit, merge) → `gt`
    - GitHub API interactions (review comments, PR details) → `gh`
    - Worktree management (the one `gt` cannot handle) → raw `git`
    - Reminder: `gt` commands always include `--no-interactive`

**Current:** No file exists at `.claude/skills/using-graphite-cli/SKILL.md` (directory may exist but is empty).

**After:** `.claude/skills/using-graphite-cli/SKILL.md` contains the complete skill with frontmatter and 11 sections, following the format of existing skills (qrspi-work as reference).

**Files created:**
- `.claude/skills/using-graphite-cli/SKILL.md`

**Rollback Notes:** None. This is a new file — deletion is the only rollback action needed.

**Verify:**
- [ ] File exists at `.claude/skills/using-graphite-cli/SKILL.md`
- [ ] YAML frontmatter contains all 5 required keys: name, description, command, argument-hint, allowed-tools
- [ ] All 11 sections are present with clear headings
- [ ] Inline code blocks show exact commands with `--no-interactive` flag
- [ ] Content matches acceptance criteria from design.md (AC1 through AC11)

```bash
# Verify the file exists and has the expected structure
test -f .claude/skills/using-graphite-cli/SKILL.md && \
  grep -c '^---$' .claude/skills/using-graphite-cli/SKILL.md | grep -q '^2$' && \
  grep -q 'using-graphite-cli' .claude/skills/using-graphite-cli/SKILL.md && \
  grep -q 'Graphite CLI Primer' .claude/skills/using-graphite-cli/SKILL.md && \
  echo "OK: SKILL.md exists with valid frontmatter and sections"
```

**AC coverage:** All 11 acceptance criteria from design.md are addressed:
- AC1 (Initialization) → Section "Initialization"
- AC2 (Core Workflow) → Section "Core Workflow"
- AC3 (Branch Navigation) → Section "Branch Navigation"
- AC4 (Single Commit Per Branch) → Section "Single Commit Per Branch"
- AC5 (Restacking) → Section "Restacking"
- AC6 (Submitting PRs) → Section "Submitting PRs"
- AC7 (Downstack/Upstack Operations) → Section "Downstack/Upstack Operations"
- AC8 (Merging Stacks) → Section "Merging Stacks"
- AC9 (Integration with GitHub) → Section "Integration with GitHub"
- AC10 (Scope Guidance) → Section "Scope Guidance"
- AC11 (Acceptance Criteria Met) → All sections collectively cover all ACs

**Context cost:** S (single file, no code changes)

**Depends on:** none
