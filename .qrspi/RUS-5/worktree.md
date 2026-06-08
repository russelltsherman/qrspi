# Work Tree — Create a new agent skill called writing-bash-scripts

**Plan basis:** plan.md @ 2026-06-06T00:00:00Z
**Generated:** 2026-06-06T00:00:00Z
**Status:** draft
**Total sessions:** 1
**Critical path:** T1 → T2 → T3 → T8 → T9 → T10 → T13 → T14 (8 tasks)

> The plan is a single additive slice (14 steps, no DB/config/destructive work).
> All tasks fit in one implementation session well under the 40% context ceiling,
> so no mid-slice session boundary is required.

## Session 1

**Load:** structure.md §Types (`SkillFrontmatter`, `ReferenceCatalog`, `ReferenceFile`),
        structure.md §Contracts (`SKILL.md.body → references`, `→ size limit`,
        `description → trigger boundary`), plan.md §Slice 1
**Estimated context:** ~20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create skill root dir `.claude/skills/writing-bash-scripts/` | — | §1 | S | pending |
| T2 | Create `references/` subdirectory | T1 | §2 | S | pending |
| T3 | Create `references/strict-mode.md` (set -euo pipefail, IFS) | T2 | §3 | S | pending |
| T4 | Create `references/error-handling.md` (traps, cleanup, exit codes) | T2 | §4 | S | pending |
| T5 | Create `references/arguments.md` (getopts, positionals, subcommands) | T2 | §5 | S | pending |
| T6 | Create `references/quoting-and-portability.md` (quoting, logging, temp files, portability) | T2 | §6 | M | pending |
| T7 | Create `references/testing-and-linting.md` (ShellCheck-clean guidance) | T2 | §7 | S | pending |
| T8 | Create `SKILL.md` body (defaults, code-organization, gotchas, links to all references; <500 lines) | T3, T4, T5, T6, T7 | §8 | M | pending |
| T9 | Add YAML frontmatter — exactly the five in-repo keys, `name: writing-bash-scripts` | T8 | §9 | S | pending |
| T10 | Engineer `description` value — enumerated triggers + "Use when" + explicit skip clause | T9 | §10 | M | pending |
| T11 | Modify `README.md` — add skill table row + Project Structure tree node | T10 | §11 | S | pending |
| T12 | Modify `.claude/CLAUDE.md` — list skill under "Available skills" | T10 | §12 | S | pending |
| T13 | Run frontmatter + link + size validation script (expect `OK`) | T10 | §13 | S | pending |
| T14 | **Verify Slice 1** — checkpoint (five keys, <500 lines, no orphan/dangling links, trigger+skip clauses, doc mirrors, ShellCheck where available, skill-creator eval or noted deviation) | T11, T12, T13 | §14 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 is the only slice; no further implementation sessions. This boundary
marks feature completion — proceed to the PR phase, not a new context.
