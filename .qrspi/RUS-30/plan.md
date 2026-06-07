# Implementation Plan — Create a new agent skill: using git worktrees

**Structure basis:** structure.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft
**Total steps:** 13

## Slice 1: Authored `using-git-worktrees` skill (body + references + bootstrap script)

All files in this slice are mutually dependent and share one testability boundary (the skill must load with body, references, frontmatter, and bundled script all present). Per structure.md, references the `references/` topic split and `bootstrap-bare-repo.sh` CLI signature remain Unverified Assumptions — the steps below adopt the structure's contract (`<repo-url> [target-dir]`) and a single combined reference file as the working baseline; if reviewer/author input changes the topic split, steps 4–6 adjust file count only, not the slice boundary.

### Setup

1. ✨ Create `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` — establish the bundled-script subdirectory and the bootstrap script file. Shebang on line 1, `set -euo pipefail` on line 2, mirroring repo bash convention (ref: structure.md Contracts; design.md §Delta, Decision 4, Q8).

### Core Logic

2. ⚠️ Edit `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` — add the required-arg guard for the repo URL.
   - **Current:** empty body after shebang + `set -euo pipefail`
   - **After:** `repo_url="${1:?Usage: bootstrap-bare-repo.sh <repo-url> [target-dir]}"` plus an optional `target_dir="${2:-...}"` default derived from the repo URL basename (ref: structure.md Contracts; design.md Q8).

3. ⚠️ Edit `.claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` — add the bootstrap body: `git clone --bare`, write the `.git` pointer, configure the fetch refspec (`remote.origin.fetch = +refs/heads/*:refs/remotes/origin/*`), `git fetch`, and create the first worktree. Surface failures to stderr with an `error:` prefix and `exit 1`.
   - **Current:** arg guard only
   - **After:** complete bare-clone + fetch-refspec + first-worktree orchestration with `error:`-prefixed stderr on failure (ref: structure.md Contracts; design.md §Delta, Decision 4, Q8).

4. ✨ Create `.claude/skills/using-git-worktrees/references/worktrees.md` — long-form reference covering: bare-repo layout, full create→work→PR→merge→remove→prune lifecycle, parallel-agent isolation (per-worktree `.env`, `.env.local` port overrides, independent dep install, 3–5 worktree ceiling), shared-state/config, cleanup/maintenance for long-lived projects, CI/review integration, and the submodule + shared-stash gotchas. (Working baseline: one combined file; OQ4 topic split is an Unverified Assumption — ref: structure.md, design.md OQ4.)

5. ✨ Create `.claude/skills/using-git-worktrees/SKILL.md` — skill-schema frontmatter copied from an existing `SKILL.md` (e.g. `qrspi-research`), NOT the agent schema: fields `name`/`description`/`command`/`argument-hint`/`allowed-tools`, with `name: using-git-worktrees` exactly matching the directory slug, a single-line trigger `description`, and `allowed-tools` reflecting a guidance (non-agent-spawner) skill with no `Agent` tool (ref: structure.md Contracts; design.md Decision 1, Q4, Q5).

6. ⚠️ Edit `.claude/skills/using-git-worktrees/SKILL.md` — add the thin procedural body leading with the bare-repo + parallel-agent use case; reconcile this repo's linked-from-`main` model as a secondary note (Decision 2 Option A); cite `references/worktrees.md` and `scripts/bootstrap-bare-repo.sh` by relative path at the point of use. Keep under the 500-line / ~5000-token budget.
   - **Current:** frontmatter only
   - **After:** frontmatter + procedural body with reachable relative-path links to the reference file and bootstrap script (ref: structure.md Contracts; design.md Decision 2, Decision 3, Q7).

### Tests

7. ✨ Run: `shellcheck .claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh`
   - **Expected:** exits 0 with no warnings (no bash test harness exists in-repo; verification is shellcheck + manual e2e per structure.md, design.md Q10/Q11/Decision 4).

8. Run: `bash .claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh` (no args)
   - **Expected:** the `${1:?Usage…}` guard prints to stderr and the script exits non-zero (ref: design.md Q8, Q10).

9. Run (manual e2e against a throwaway remote): `bash .claude/skills/using-git-worktrees/scripts/bootstrap-bare-repo.sh <throwaway-repo-url> /tmp/wt-e2e`
   - **Expected:** produces a bare repo, a configured fetch refspec (`git -C /tmp/wt-e2e config --get remote.origin.fetch`), and a first worktree (ref: structure.md Verification; design.md Q8, Q10).

### Verify Slice 1

10. **Checkpoint:** `test -f .claude/skills/using-git-worktrees/SKILL.md && grep -q '^name: using-git-worktrees$' .claude/skills/using-git-worktrees/SKILL.md`
    - [ ] `name` in frontmatter exactly equals the directory slug `using-git-worktrees`, and the frontmatter uses the skill schema (`name`/`description`/`command`/`argument-hint`/`allowed-tools`), not the agent schema (ref: Q4, Q5).
    - [ ] `SKILL.md` body is under 500 lines and ~5000 tokens; the `references/worktrees.md` file and the bootstrap script are each reachable by a relative path actually written in the body — no dangling references (ref: Q7, Decision 3).

11. **Checkpoint:** `grep -RnoE 'references/[^ )]+\.md|scripts/bootstrap-bare-repo\.sh' .claude/skills/using-git-worktrees/SKILL.md | while IFS=: read -r f n p; do test -f ".claude/skills/using-git-worktrees/$p" || echo "DANGLING: $p"; done`
    - [ ] Every referenced relative path resolves to an existing file (no `DANGLING:` output).

12. **Checkpoint:** Manual review of `SKILL.md` + `references/worktrees.md` against §Desired End State.
    - [ ] All ten acceptance-criteria behaviors are present: bare-repo primary, full lifecycle, parallel isolation (env/ports/deps), submodule + shared-stash gotchas, naming/layout, cleanup/maintenance, references split, bundled `scripts/`, valid frontmatter, and the linked-from-`main` secondary note (ref: structure.md Verification; design.md §Desired End State).

13. **Checkpoint:** Skill loads under the skill loader without convention errors despite the novel bundled `scripts/` layout (manual e2e).
    - [ ] Skill is discoverable/loadable; authored via the global `skill-creator` skill + eval loop where available, otherwise frontmatter validated against an existing `SKILL.md` (ref: structure.md Verification; design.md Risk Register, Q1, Q3, OQ1).

---

## Rollback Notes

- Steps 1–6: New-files-only, no in-repo dependents (design.md §Delta — the skill is a leaf). To revert the entire slice: `rm -rf .claude/skills/using-git-worktrees/`. No existing skills, agents, scripts, or `.claude/CLAUDE.md` are modified, so no other file needs restoring.
- Step 9 (manual e2e): writes only to a throwaway target (`/tmp/wt-e2e`) and a throwaway remote. Clean up with `rm -rf /tmp/wt-e2e`. Not a repo mutation; no rollback affects tracked files.
- No DB migrations, config changes, or destructive in-repo operations are involved.
