# Work Tree — Create writing-bash-scripts agent skill

**Plan basis:** plan.md @ 2026-05-31
**Generated:** 2026-05-31
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 -> T2 -> T3 -> T4 -> T5 -> T6 -> T7 -> T8 -> T9 -> T10 -> T11 -> T12 -> T13 -> T14 -> T15

## Session 1

**Load:** structure.md §Types, structure.md §Contracts, plan.md §Slice 1 steps 1-5
**Estimated context:** 30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Create SKILL.md with YAML frontmatter (name, description, command, argument-hint, allowed-tools) | — | §1.1 | S | pending |
| T2 | Add H1 heading and Trigger section with "Use when..." language | T1 | §1.2 | S | pending |
| T3 | Add Strict Mode convention (set -euo pipefail, bash 3.2 portability, explain -e/-u/-o pipefail) | T2 | §1.3 | S | pending |
| T4 | Add Error Handling convention (trap EXIT/ERR/INT/TERM, explain each trap) | T3 | §1.4 | S | pending |
| T5 | Add Argument Parsing convention (getopts, positional args, argc validation, exit code 2) | T4 | §1.5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Session 1 complete. Core skill file structure and foundational conventions done. Fresh context for remaining convention sections.

## Session 2

**Load:** SKILL.md (from Session 1), structure.md §Contracts, plan.md §Slice 1 steps 6-15
**Estimated context:** 30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Add Logging convention (log_info/log_warn/log_error, prefix format, stderr/stdout separation) | T5 | §1.6 | S | pending |
| T7 | Add Quoting convention (double-quote expansions, $@ quoting, SC2086/SC2046 examples) | T6 | §1.7 | S | pending |
| T8 | Add Dependency Checking convention (command -v test, error + exit 1 on missing) | T7 | §1.8 | S | pending |
| T9 | Add Usage/Help convention (usage() function, --help/-h, EXIT trap prints usage) | T8 | §1.9 | S | pending |
| T10 | Add Temp Files convention (mktemp with trap cleanup, no hardcoded paths) | T9 | §1.10 | S | pending |
| T11 | Add Code Organization convention (function defs at top, main "$@" at bottom) | T10 | §1.11 | S | pending |
| T12 | Add Testing and Linting convention (ShellCheck rule IDs, shellcheck pass as gate) | T11 | §1.12 | S | pending |
| T13 | Add Portability convention (bash 3.2 limitations, POSIX fallbacks for assoc arrays/mapfile/here-strings) | T12 | §1.13 | S | pending |
| T14 | Add Scope Boundary section (bash-only scope, distinguish from using-graphite-cli and qrspi-* skills) | T13 | §1.14 | S | pending |
| T15 | Update CLAUDE.md Available skills section with /writing-bash-scripts entry (alphabetically between /qrspi-worktree and /qrspi-implement) | T14 | §1.15 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Session 2 complete. All convention sections and CLAUDE.md update done. Fresh context for verification to avoid carrying 14+ convention details into validation checks.

## Session 3

**Load:** SKILL.md (final), CLAUDE.md (from Session 2), scripts/check_scope.py, plan.md §Slice 1 steps 16-18
**Estimated context:** 20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T16 | Run check_scope.py validation script on SKILL.md | T15 | §1.16 | S | pending |
| T17 | Parse and verify SKILL.md frontmatter fields (name, description, command, argument-hint, allowed-tools) | T15 | §1.17 | S | pending |
| T18 | Verify SKILL.md body covers all 13 convention topics | T15 | §1.18 | S | pending |
