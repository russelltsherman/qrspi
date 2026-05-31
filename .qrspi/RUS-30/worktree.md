# Work Tree — Create a new agent skill named using git worktrees

**Plan basis:** plan.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T12 → T15 → T16 → T17 → T18

## Session 1

**Load:** structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1, design.md §Pattern Decisions (1-4)
**Estimated context:** ~25% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Invoke skill-creator to scaffold `using-git-worktrees` under `.claude/skills/` (move into repo path if scaffolded elsewhere) | — | §1.1 | M | pending |
| T2 | Ensure dir tree `using-git-worktrees/{,scripts/,references/}` | T1 | §1.2 | S | pending |
| T3 | Write SKILL.md frontmatter (name, description, allowed-tools) | T2 | §1.3 | S | pending |
| T4 | Body: "When to use" | T3 | §1.4 | S | pending |
| T5 | Body: "Primary pattern: bare repository" (points to bootstrap script) | T3 | §1.5 | S | pending |
| T6 | Body: "Lifecycle" (create/work/PR/merge/remove/prune) | T3 | §1.6 | S | pending |
| T7 | Body: "Naming & layout" | T3 | §1.7 | S | pending |
| T8 | Body: "Parallel-agent isolation" (env, ports, deps) | T3 | §1.8 | S | pending |
| T9 | Body: "Cleanup & maintenance" | T3 | §1.9 | S | pending |
| T10 | Body: "Gotchas" (one-liners linking references/gotchas.md) | T3 | §1.10 | S | pending |
| T11 | Body: "Secondary pattern: single linked worktree" | T3 | §1.11 | S | pending |
| T12 | Create `scripts/bootstrap-bare-worktree.sh` via writing-bash-scripts skill; chmod +x | T2 | §1.12 | M | pending |
| T13 | Create `references/gotchas.md` | T2 | §1.13 | S | pending |
| T14 | Create `references/cheatsheet.md` | T2 | §1.14 | S | pending |
| T15 | Run ShellCheck on bootstrap script (STOP if shellcheck missing) | T12 | §1.15 | S | pending |
| T16 | Bootstrap smoke test against throwaway local repo; verify `.bare/`, `.git` pointer, fetch refspec, first worktree; clean up temp dirs | T12 | §1.16 | M | pending |
| T17 | **Verify Slice 1** — frontmatter valid, body < 500 lines / ~5000 tokens, lifecycle + isolation + gotchas coverage, in-repo only, ShellCheck + smoke test passed | T4,T5,T6,T7,T8,T9,T10,T11,T13,T14,T15,T16 | §1.17 | S | pending |
| T18 | **Verify Slice 1** — run skill-creator eval/triggering loop; tune description if needed | T17 | §1.18 | M | pending |

--- SESSION BOUNDARY ---
**Reason:** Single cohesive slice (one skill deliverable). All tasks share the same small artifact set and fit in one session under 40% context, so no further boundary is needed. Implementation completes here.
