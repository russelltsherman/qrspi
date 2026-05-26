# Structure — using graphite cli

**Ticket:** RUS-6
**Generated:** 2026-05-26
**Phase:** Structure

## Types and Contracts

### New Skill Registration

The skill is registered in `.claude/CLAUDE.md` under the "Available skills" list. It follows the existing convention:

```
- `/using-graphite-cli <command>` — Full Graphite CLI workflow: create, submit, modify, sync stacked PRs
```

### SKILL.md Frontmatter

```yaml
---
name: using graphite cli
description: Full Graphite CLI workflow: create, submit, modify, sync stacked PRs. Trigger on any variant of: 'use graphite', 'use gt', 'Graphite CLI', 'gt command', stacked PRs, Graphite branches.
command: /using-graphite-cli
argument-hint: <command>
allowed-tools: Bash(gt:*), Bash(git status:*), Read
---
```

### SKILL.md Body (pseudo-code outline)

```
# Graphite CLI Skills

## When to Use This Skill

Trigger conditions: any mention of Graphite CLI, gt commands, stacked PRs,
graphite branches, gt create/modify/submit/sync, etc.

## The Single-Commit-Per-Branch Convention (Hard Rule)

- Use `gt create` to create branches (NOT `git branch`).
- Use `gt modify --all` to amend (NOT `git commit --amend`).
- Raw `git branch` or `git rebase` on Graphite-tracked branches corrupts stack state.

## Create -> Submit -> Modify -> Sync Loop

### Creating a Branch

```bash
gt checkout main --no-interactive
gt create <branch-name> --no-interactive
```

### Making Commits

```bash
# ... make changes ...
gt modify --all --no-interactive -m "conventional commit message"
```

### Submitting

```bash
gt submit --no-edit --publish --no-interactive
```

Flags: `--no-edit` (keep default message), `--publish` (create PR).
Shorthand: `--np` = `--no-edit --publish`.

### Syncing Upstack

```bash
gt sync --force --no-interactive
```

## Stack Navigation

| Command | Direction | Description |
|---|---|---|
| `gt bu` | up | Branch up (move current branch up one position) |
| `gt bd` | down | Branch down (move current branch down one position) |
| `gt stack top` | — | Show top of stack |
| `gt log short --no-interactive` | — | Compact stack log |

### Directionality

- **Downstack** = toward trunk (main).
- **Upstack** = away from trunk.

## Conflict Resolution

When a merge conflict occurs on a Graphite-tracked branch:

```bash
gt continue --no-interactive
```

**CRITICAL:** Never run `git rebase --continue` on a Graphite-tracked branch.
Always use `gt continue` which preserves stack metadata.

## Mixing Git and Graphite — Warning

Mixing raw git branch/rebase operations with Graphite-tracked branches corrupts
stack metadata. If you accidentally used `git branch` or `git rebase` on a
Graphite branch, the stack will be out of sync. Rescue: discard the branch and
recreate it with `gt create`.

## Reference Material

Full command reference and edge cases are in `references/cli-reference.md`.
```

### references/cli-reference.md (pseudo-code outline)

```markdown
# Graphite CLI Command Reference

> Snapshot of Graphite CLI v0.x. Commands may evolve — verify with `gt --help`.

## Core Workflow

### gt create
Create a new branch from the current position in the stack.

`gt create <name> [--no-interactive]`

- Creates branch from current branch's commit.
- Adds to stack ordering.
- DOES NOT switch to the new branch (use `gt checkout` after).

### gt checkout
Switch to a branch in the stack.

`gt checkout <name> [--no-interactive]`

- Accepts branch names, stack positions, or `main`.
- When switching branches, restacks descendants automatically.

### gt modify
Amend the current branch's tip commit.

`gt modify [--all] [-c] [-m <message>] [--no-interactive]`

- `--all` (`-a`): Stage all changes before amending.
- `-c`: Continue a previous amend (reuses last message).
- `-m`: Override commit message.
- WITHOUT `--all`: only amend staged files.

### gt submit
Push and create/update PR(s).

`gt submit [--stack] [--no-edit] [--publish] [--no-interactive]`

- `--stack`: Submit all open PRs in the stack.
- `--no-edit`: Use the current branch message as-is.
- `--publish`: Create a new PR (default when no PR exists).

### gt sync
Sync all branches in the stack with the latest trunk.

`gt sync [--force] [--no-interactive]`

- Rebases all stack branches onto updated trunk.

## Stack Navigation

### gt bu
Branch up — move current branch above its parent in stack order.

`gt bu [--no-interactive]`

### gt bd
Branch down — move current branch below its parent in stack order.

`gt bd [--no-interactive]`

### gt stack top
Show the topmost branch in the current stack.

### gt log short
Show a compact view of the stack.

`gt log short [--no-interactive]`

## Conflict Resolution

### gt continue
Continue an in-progress rebase or merge conflict resolution.

`gt continue [--no-interactive]`

**Always use this instead of `git rebase --continue` on Graphite branches.**

## Danger Zone

### gt delete
Delete a branch and its descendants.

`gt delete <name> [--force] [--no-interactive]`

### gt move
Move a branch to a different position in the stack.

`gt move --onto <target-branch> [--no-interactive]`

### gt merge
Merge a stack of PRs.

`gt merge [--confirm] [--no-interactive]`

## Edge Cases

- `gt create` on a branch that already exists: fails unless `--force`.
- `gt submit` on a branch with no local changes: creates an empty PR (warns).
- Switching to trunk while having uncommitted changes: Git's normal safety applies.
- Multiple agents working on the same stack: race conditions possible on sync.
```

### CLAUDE.md Update

Add one line to the "Available skills" list in `.claude/CLAUDE.md`, maintaining alphabetical order relative to the `qrspi-*` entries:

```
- `/using-graphite-cli <command>` — Full Graphite CLI workflow: create, submit, modify, sync stacked PRs
```

The line is inserted after the last `/qrspi-*` entry, preserving the existing convention.

## Vertical Slices

### Slice 1: Create the using-graphite-cli skill

**Goal:** Ship a complete, loadable skill that encodes the Graphite CLI workflow — create, submit, modify, sync, conflict resolution, and stack navigation — plus a reference document and CLAUDE.md registration.

**Files:**

| File | Action |
|---|---|
| `.claude/skills/using-graphite-cli/SKILL.md` | **New** — primary skill definition (~150-200 lines body) |
| `.claude/skills/using-graphite-cli/references/cli-reference.md` | **New** — comprehensive command reference (~100-150 lines) |
| `.claude/CLAUDE.md` | **Modify** — add skill to "Available skills" list |

**Verification step:** Validate the SKILL.md frontmatter has all 5 required fields (name, description, command, argument-hint, allowed-tools). Confirm the skill body is under 500 lines / 5000 tokens. Confirm CLAUDE.md lists the new skill in the "Available skills" section using the established format.

**Context cost:** S — all changes are directly related and self-contained.

**Dependencies:** None.

## Contracts

### Cross-slice interface

There is only one slice, so the only contract is the skill's file-level interface:

1. **SKILL.md `allowed-tools`** declares `Bash(gt:*)`, `Bash(git status:*)`, and `Read`. Any implementer must ensure these tool permissions are granted by the harness for the skill to function.

2. **CLAUDE.md "Available skills" entry** must follow the exact format: `- /<command> <description>` with a tab separator. This is how the harness discovers and auto-invokes the skill.

3. **references/cli-reference.md** is a supporting document. The `Read` tool in `allowed-tools` enables the agent to load it. The skill body references it as the source of detailed command syntax.

### Skill registration contract

The skill name in frontmatter (`using graphite cli`) must match the skill directory name (`using-graphite-cli`) per the project convention. The command (`/using-graphite-cli`) must match the directory name with `/` prefix.

## Unverified Assumptions

| # | Claim from design.md | Status |
|---|---|---|
| A1 | The Graphite CLI `gt` binary is installed and available in the agent environment | Unverified — design says "referenced externally" but does not confirm installation |
| A2 | `Bash(gt:*)` glob is sufficient to cover all needed `gt` subcommands | Unverified — `gt` has many subcommands and flags; some may need explicit globs if not matched by `*` |
| A3 | `Bash(git status:*)` is sufficient — no other raw git commands are needed | Unverified — stack navigation commands like `gt log short` produce output that the skill body references; no bare `git` commands appear in the skill body itself |
| A4 | The 500-line / 5000-token body limit is achievable with the outlined content | Partially verified — the outline targets ~150-200 lines, well under the limit, but the actual implementation will determine if the content exceeds this |
| A5 | The `using graphite cli` name (with space, not hyphen) is the correct frontmatter `name` value | Unverified — all existing skills use hyphenated names (`qrspi-implement`, `qrspi-work`) but the design explicitly states this skill uses a space in the name |
| A6 | The design does not require using the `skill-creator` skill to generate the SKILL.md — it can be written directly | Unverified — design says "The Anthropic skill builder skill is available" but does not mandate its use; this is a design choice, not a requirement |
| A7 | The `Read` tool is needed for the skill to load `references/cli-reference.md` | Verified — other skills with references/ files (e.g., `qrspi-work`) include `Read` in `allowed-tools` |
