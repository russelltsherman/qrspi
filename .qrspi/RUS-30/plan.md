# Implementation Plan — Create a new agent skill named using git worktrees

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: Author the using-git-worktrees skill (SKILL.md + scripts + references)

### Setup

1. ✨ Invoke the `skill-creator` skill to scaffold a new skill named `using-git-worktrees` under `.claude/skills/`. If skill-creator scaffolds into a different location, move/recreate the tree under `.claude/skills/using-git-worktrees/` (the in-repo project-scope boundary is mandatory; never leave it in a home-dir path).
2. ✨ Ensure the directory tree exists: `.claude/skills/using-git-worktrees/{,scripts/,references/}`.

### Core Logic

3. ✨ Create `.claude/skills/using-git-worktrees/SKILL.md` frontmatter — valid YAML: `name: using-git-worktrees`; a WHEN-to-use `description` (e.g., "Use when an agent needs to create, manage, or clean up git worktrees for parallel working directories — especially the bare-repo pattern for isolated parallel-agent workflows."); `allowed-tools: Read, Bash`. (ref: structure.md Contracts `SkillFrontmatter`)
4. ✨ Add SKILL.md body section "When to use" — one short paragraph; assume the agent already decided to use worktrees (scope: how, not why).
5. ✨ Add SKILL.md body section "Primary pattern: bare repository" — describe the `.bare/` + `.git` pointer + per-branch worktree tree; point to `scripts/bootstrap-bare-worktree.sh` for automated setup. (ref: structure.md Slice 1, design.md §Pattern Decision 3)
6. ✨ Add SKILL.md body section "Lifecycle" covering, in order: create (`git worktree add <path> -b <branch>` from an up-to-date base), work, PR (`gh pr ...`), merge, remove (`git worktree remove <path>`), prune (`git worktree prune`, with `--dry-run --verbose` preview). (ref: structure.md Contracts)
7. ✨ Add SKILL.md body section "Naming & layout" — lowercase-hyphen `<type>-<short-description>` convention; never nest worktrees; sibling/parent-dir placement.
8. ✨ Add SKILL.md body section "Parallel-agent isolation" — one worktree per agent; 3-5 concurrent limit; copy (not symlink) `.env`; `.env.local` port overrides; independent dependency installs (node_modules not shared). (ref: structure.md Slice 1 verification)
9. ✨ Add SKILL.md body section "Cleanup & maintenance" — `git worktree list` audits; remove+prune after merge; `git worktree lock` for removable/network media; iterate `git worktree list --porcelain` for merged-branch cleanup.
10. ✨ Add SKILL.md body section "Gotchas" — one-line warnings (submodules, shared `git stash`, shared hooks, IDE caveats) each linking to `references/gotchas.md`.
11. ✨ Add SKILL.md body section "Secondary pattern: single linked worktree" — brief note for adding one worktree to an existing checkout (the pattern this repo itself uses). (ref: design.md §Pattern Decision 3)
12. ✨ Create `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-worktree.sh` via the `writing-bash-scripts` skill — `#!/usr/bin/env bash`; `set -euo pipefail`; args `<repo-url> <project-dir>`; usage/arg validation; refuse if `<project-dir>` already exists; `git clone --bare <repo-url> <project-dir>/.bare`; write `<project-dir>/.git` containing `gitdir: ./.bare`; `git -C <project-dir> config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'`; fetch; add first worktree for the default branch. Make executable (`chmod +x`). (ref: structure.md Contracts `bootstrap-bare-worktree.sh`)
13. ✨ Create `.claude/skills/using-git-worktrees/references/gotchas.md` — submodule incompleteness (`--force` on removal, manual moves, per-worktree init), shared `git stash`, shared `.git/hooks/`, IDE support caveats (tool-agnostic), tools that walk up for `.git`. (ref: structure.md Contracts `gotchas.md`)
14. ✨ Create `.claude/skills/using-git-worktrees/references/cheatsheet.md` — full per-stage command transcripts for the lifecycle + an optional shell alias set for the bare-repo bootstrap. (ref: structure.md Contracts `cheatsheet.md`)

### Tests

15. Run: `shellcheck .claude/skills/using-git-worktrees/scripts/bootstrap-bare-worktree.sh`
    - **Expected:** exits 0 with no warnings. (If `shellcheck` is not installed, STOP and report the missing tool per the HARD STOP infra-error rule — do not skip the check.)
16. Run a bootstrap smoke test against a throwaway local source repo:
    - Create a temp source repo with at least one commit on the default branch.
    - Run `bootstrap-bare-worktree.sh <file-or-path-to-temp-source> <temp-project-dir>`.
    - **Expected:** `<temp-project-dir>/.bare` exists; `<temp-project-dir>/.git` contains `gitdir: ./.bare`; `git -C <temp-project-dir> config --get remote.origin.fetch` returns `+refs/heads/*:refs/remotes/origin/*`; a first worktree directory for the default branch exists.
    - Clean up the temp dirs afterward.

### Verify Slice 1

17. **Checkpoint:** structural + content validation
    - [ ] `head -1 ... | grep -q '^---'` and frontmatter parses; `name: using-git-worktrees`, `description`, `allowed-tools` all present.
    - [ ] `wc -l .claude/skills/using-git-worktrees/SKILL.md` < 500; token estimate under ~5000.
    - [ ] `shellcheck` clean (step 15) and bootstrap smoke test passed (step 16).
    - [ ] Body covers all six lifecycle stages, leads with bare-repo (primary), documents linked worktree (secondary), and links both reference files.
    - [ ] Parallel-isolation section covers env files, ports, and independent deps; gotchas cover submodules and shared stash.
    - [ ] All files reside under `.claude/skills/using-git-worktrees/`; no home-dir writes.
18. **Checkpoint:** run the `skill-creator` eval/triggering loop on `using-git-worktrees`.
    - [ ] skill-creator reports the skill well-formed and the description triggers acceptably (tune the `description` if the loop flags low triggering accuracy).

---

## Rollback Notes

- Steps 1-14 only add new files under `.claude/skills/using-git-worktrees/`. Rollback = delete that directory; no existing repo file is modified, so no other reversal is needed.
- Step 16 creates temp directories outside the repo for the smoke test — ensure they are removed after the test so they do not leak into the worktree or get committed.
- If `.claude/CLAUDE.md` is edited per OQ2 (not in current scope), rollback = revert that single-line addition.
