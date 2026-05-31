# Structure Outline — Create a new agent skill named using git worktrees

**Design basis:** design.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft

## New Types

This ticket produces documentation and a shell script, not code types. The closest analogues to "types" here are the file contracts each deliverable must satisfy:

- `SkillFrontmatter { name: string, description: string, allowed-tools: string }` — valid YAML at the top of SKILL.md (ref: design.md §Pattern Decision 2, §Delta).
- `BootstrapScript { shebang: "#!/usr/bin/env bash", strictMode: "set -euo pipefail", args: [repoUrl, projectDir] }` — the bare-repo bootstrap contract (ref: design.md §Delta, §Pattern Decision 4).

## Modified Types

- None. No existing repo file's structure changes. (`.claude/CLAUDE.md` skill-list edit is deferred to OQ2 and is not required.)

## Contracts

- `bootstrap-bare-worktree.sh <repo-url> <project-dir>` → creates `<project-dir>/.bare` (bare clone), `<project-dir>/.git` pointer file containing `gitdir: ./.bare`, configures `remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'`, fetches, and adds a first worktree for the default branch. Exits non-zero with a clear message on bad args or existing target. (ref: design.md §Delta, §Pattern Decision 4)
- `SKILL.md body` → references `scripts/bootstrap-bare-worktree.sh` and `references/gotchas.md` + `references/cheatsheet.md` by relative path; covers the full lifecycle create → work → PR → merge → remove → prune. (ref: design.md §Delta, §Desired End State)
- `references/gotchas.md` → submodules, shared `git stash`, shared hooks, IDE caveats, `.git`-walking tools. (ref: design.md §Delta)
- `references/cheatsheet.md` → per-stage command transcripts + optional bare-repo alias set. (ref: design.md §Delta)

## Slice 1: Author the using-git-worktrees skill (SKILL.md + scripts + references)

**Goal:** A complete, valid, in-repo skill at `.claude/skills/using-git-worktrees/` that satisfies every acceptance criterion: valid frontmatter, lifecycle-organized body under budget, a ShellCheck-clean bare-repo bootstrap script, and reference files for gotchas and the command cheatsheet. End-to-end verifiable: ShellCheck passes on the script, the script bootstraps a throwaway repo successfully, and the skill-creator eval loop confirms the skill is well-formed and triggers.

**Files touched:**

- ✨ `.claude/skills/using-git-worktrees/SKILL.md` — frontmatter (`name: using-git-worktrees`, WHEN-to-use description, minimal `allowed-tools`) + body sections: When to use; Primary pattern (bare-repo) pointing to bootstrap script; Lifecycle (create/work/PR/merge/remove/prune); Naming & layout; Parallel-agent isolation (env files, ports, deps); Cleanup/maintenance; Gotchas (one-line warnings linking references); Secondary pattern (single linked worktree). Target ~120-180 lines.
- ✨ `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-worktree.sh` — bare clone + `.git` pointer + fetch refspec + first worktree; `#!/usr/bin/env bash`, `set -euo pipefail`, executable, ShellCheck-clean. Authored via the `writing-bash-scripts` skill.
- ✨ `.claude/skills/using-git-worktrees/references/gotchas.md` — submodule incompleteness (`--force` on removal, manual moves), shared `git stash`, shared hooks, IDE caveats, tools walking up for `.git`.
- ✨ `.claude/skills/using-git-worktrees/references/cheatsheet.md` — full lifecycle command transcripts + optional shell alias set for the bare-repo bootstrap.

**Verification:**

- [ ] `SKILL.md` frontmatter is valid YAML with `name: using-git-worktrees`, a `description`, and `allowed-tools`.
- [ ] SKILL.md body is under 500 lines and under ~5000 tokens (`wc -l` < 500; spot-check token estimate).
- [ ] `shellcheck scripts/bootstrap-bare-worktree.sh` exits clean (zero warnings).
- [ ] Bootstrap script run against a throwaway local repo produces `.bare/`, a `.git` pointer file with `gitdir: ./.bare`, the configured fetch refspec (`git config --get remote.origin.fetch`), and a first worktree directory.
- [ ] Body covers all six lifecycle stages and links to both reference files; bare-repo is presented as primary, linked-worktree as secondary.
- [ ] Parallel-isolation section addresses env files, distinct ports, and independent dependency installs; gotchas cover submodules and shared stash.
- [ ] The `skill-creator` skill (and its eval/triggering loop) is invoked and reports the skill well-formed.
- [ ] All files live under `.claude/skills/using-git-worktrees/` — no home-dir writes.

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

- The global `skill-creator` skill is invocable from inside this worktree during implementation and its eval loop accepts a knowledge skill (design assumed this from environment availability + user memory, ref: design.md §Pattern Decision 4 / Q6, Q13 — not verifiable from repo files alone).
- `shellcheck` is installed in the implementation environment. If absent, the implement agent must surface the missing-tool error (per HARD STOP infra-error rule) rather than skipping the lint check; ShellCheck-cleanliness is still asserted via the `writing-bash-scripts` skill conventions.
- The bootstrap smoke test can create a throwaway repo locally (e.g., `git init --bare` of a temp source) without network access; if the script's example assumes a remote URL, the smoke test uses a `file://` or local path source instead of a real remote.
