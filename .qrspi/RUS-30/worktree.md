# Work Tree — Create a new agent skill: using git worktrees

**Plan basis:** plan.md @ 2026-06-07T00:00:00Z
**Generated:** 2026-06-07T00:00:00Z
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8 → T9 → T10 → T11 → T12 → T13

## Session 1 — Author the skill (body + references + bootstrap script)

**Load:** structure.md §Contracts, structure.md §Types, plan.md §Slice 1 (Setup + Core Logic, steps 1–6), design.md §Delta Decisions 1–4 + Q4/Q5/Q7/Q8
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create `scripts/bootstrap-bare-repo.sh` with shebang + `set -euo pipefail` | — | §1 | S | pending |
| T2 | Add required-arg guard for repo URL (+ optional target_dir default) | T1 | §2 | S | pending |
| T3 | Add bootstrap body: bare clone, `.git` pointer, fetch refspec, fetch, first worktree, `error:`-prefixed stderr | T2 | §3 | M | pending |
| T4 | Create `references/worktrees.md` long-form reference (layout, lifecycle, parallel isolation, gotchas, cleanup, CI) | — | §4 | L | pending |
| T5 | Create `SKILL.md` with skill-schema frontmatter (`name: using-git-worktrees`, single-line description, `allowed-tools` sans `Agent`) | — | §5 | M | pending |
| T6 | Add `SKILL.md` procedural body; cite `references/worktrees.md` + `scripts/bootstrap-bare-repo.sh` by relative path; keep under 500-line / ~5000-token budget | T4, T5 | §6 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Authoring (steps 1–6) is complete and all files exist. Verification (steps 7–13) is a distinct testability boundary needing the bundled-script + frontmatter checks and manual e2e; a fresh context drops the authoring-decision detail and loads only the verification criteria, staying under the 40% ceiling.

## Session 2 — Verify Slice 1

**Load:** structure.md §Verification, plan.md §Slice 1 (Tests + Verify, steps 7–13), design.md §Desired End State + Risk Register + Q10/Q11, impl-log.md §Slice 1 (notes only)
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T7 | Run `shellcheck` on bootstrap script — expect exit 0, no warnings | T3 | §7 | S | pending |
| T8 | Run bootstrap script with no args — expect `Usage…` to stderr, non-zero exit | T3 | §8 | S | pending |
| T9 | Manual e2e: run against throwaway remote → `/tmp/wt-e2e`; verify bare repo, fetch refspec, first worktree | T7, T8 | §9 | M | pending |
| T10 | **Checkpoint:** `SKILL.md` present, `name` equals dir slug, skill-schema frontmatter, body under budget, references reachable | T6 | §10 | S | pending |
| T11 | **Checkpoint:** every referenced relative path resolves (no `DANGLING:` output) | T10 | §11 | S | pending |
| T12 | **Checkpoint:** manual review of `SKILL.md` + `references/worktrees.md` against the ten §Desired End State acceptance behaviors | T11 | §12 | S | pending |
| T13 | **Verify Slice 1:** skill loads under the loader without convention errors despite bundled `scripts/` layout (manual e2e) | T9, T12 | §13 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** End of plan. Slice 1 fully authored and verified; the feature is a single leaf slice with no downstream sessions.
