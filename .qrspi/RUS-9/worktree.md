# Work Tree — RUS-9: Create the `using-claude-cli` skill

**Plan basis:** plan.md @ 2026-05-26
**Generated:** 2026-05-26
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10 -> T11

## Session 1

**Load:** structure.md §Types & Signatures, structure.md §Contracts, structure.md §Slice 1, plan.md §Slice 1
**Estimated context:** 30% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Scaffold `.claude/skills/using-claude-cli/` and `references/` directories | — | §1.1 | S | pending |
| T2 | Invoke skill-creator for SKILL.md scaffold; review and hand-edit frontmatter to five-field pattern | T1 | §1.2 | S | pending |
| T3 | Write SKILL.md body: five core topics (CLI modes, sub-agents, sessions, output formats, cost control) with Read instructions to four reference files | T2 | §1.3 | L | pending |
| T4 | Write `references/advanced-flags.md` — mode-dependent flag tables, exclusive flags, mutually exclusive combinations | T3 | §1.4 | M | pending |
| T5 | Write `references/hooks-config.md` — hook events, config schema, exit codes, use cases | T3 | §1.5 | M | pending |
| T6 | Write `references/agent-teams.md` — multi-agent patterns, worktree parallelism, background agents, experimental warning | T3 | §1.6 | M | pending |
| T7 | Write `references/permission-patterns.md` — permission syntax, settings hierarchy, CI/CD examples | T3 | §1.7 | M | pending |
| T8 | Update `.claude/CLAUDE.md` — append using-claude-cli to available skills list | T3 | §1.8 | S | pending |
| T9 | Verify Slice 1: line count, frontmatter fields, reference existence, Read coverage, CLAUDE.md registration | T4,T5,T6,T7,T8 | §1.9 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. All skill files authored and verified. Fresh context needed for Slice 2 eval cases.

## Session 2

**Load:** structure.md §Types & Signatures, structure.md §Contracts, plan.md §Slice 2, evals/graphite-evals.json (schema reference)
**Estimated context:** 20% of window

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Create `evals/claude-cli-evals.json` with 5 test cases (CLI modes, sub-agents, sessions, output formats, cost control) | T9 | §2.10 | M | done |
| T11 | Verify Slice 2: valid JSON, 5+ cases, assertion types, distinct section coverage | T10 | §2.11 | S | done |
