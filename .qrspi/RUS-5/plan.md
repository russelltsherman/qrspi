# Implementation Plan — Create writing-bash-scripts agent skill

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31
**Status:** draft
**Total steps:** 18

## Slice 1: Create writing-bash-scripts skill

### Core Logic

1. ✨ Create `/workspaces/qrspi/.claude/skills/writing-bash-scripts/SKILL.md` — frontmatter YAML block with `name: writing-bash-scripts`, `description` using "Use when..." language matching all trigger scenarios (bash script creation, editing, ShellCheck review; not generic "shell scripting"), `command: /writing-bash-scripts`, `argument-hint: <script-path>`, `allowed-tools: Read, Write, Edit, Bash`
2. ⚠️ Modify SKILL.md — add `# writing-bash-scripts` H1, then **Trigger** section with "Use when..." language covering all AC3 trigger scenarios: bash script creation, editing, ShellCheck code review
3. ⚠️ Modify SKILL.md — add **Strict Mode** convention: `set -euo pipefail` as first line; note bash 3.2 portability; explain `-e`, `-u`, `-o pipefail` individually
4. ⚠️ Modify SKILL.md — add **Error Handling** convention: `trap 'cleanup' EXIT ERR INT TERM`; EXIT for cleanup, ERR for failures, signal traps for interrupts; explain why each trap matters
5. ⚠️ Modify SKILL.md — add **Argument Parsing** convention: `getopts` for short flags with case statement; `$1` positional arg extraction; validate argc minimums; explain exit code 2 for usage errors
6. ⚠️ Modify SKILL.md — add **Logging** convention: `log_info`, `log_warn`, `log_error` functions; prefix format `[TIMESTAMP] LEVEL`; stderr for errors; stdout for data/commands
7. ⚠️ Modify SKILL.md — add **Quoting** convention: double-quote all variable expansions (`"$var"`); `$@` always quoted (`"$@"`); explain SC2086 and SC2046 warnings with concrete fix examples
8. ⚠️ Modify SKILL.md — add **Dependency Checking** convention: `command -v` test before use; `command -v` exits 0 if found; check before each external command; print error + exit 1 on missing dependency
9. ⚠️ Modify SKILL.md — add **Usage/Help** convention: `usage()` function; `--help` / `-h` flag handling; `set --help)` case in getopts loop; EXIT trap prints usage on failure; explain error code 2 convention
10. ⚠️ Modify SKILL.md — add **Temp Files** convention: `tmpfile=$(mktemp)` with trap cleanup; never hardcoded paths; handle race conditions; note `mktemp` bash 3.2 compatibility
11. ⚠️ Modify SKILL.md — add **Code Organization** convention: function defs at top; main logic at bottom in `main "$@"` call; argument parsing in main; functions encapsulate logic
12. ⚠️ Modify SKILL.md — add **Testing and Linting** convention: encode specific ShellCheck rule IDs — SC2034 (unused vars), SC2086 (unquoted variables), SC2006 (backtick style), SC2015 (AND/OR precedence), SC2046 (unquoted word splitting); require `shellcheck` pass as post-generation gate
13. ⚠️ Modify SKILL.md — add **Portability** convention: document bash 3.2 limitations — no associative arrays (use named file approach), no `mapfile` (use while-read loop), `<<<` works in bash 3.2 but with caveats; provide POSIX-compatible fallbacks for each
14. ⚠️ Modify SKILL.md — add **Scope Boundary** section: explicitly states scope is bash scripts only; note distinction from `using-graphite-cli` (git operations) and `qrspi-*` skills (QRSPI workflow); clarify when to delegate to which skill

### CLAUDE.md Update

15. ⚠️ Modify `/workspaces/qrspi/.claude/CLAUDE.md` — add `- /writing-bash-scripts <script-path> — Guide for writing robust, ShellCheck-clean bash scripts. Use whenever creating a new bash or shell script, modifying an existing bash script, writing shell functions or shell snippets longer than a few lines, or when the user asks for help with bash scripting, shell portability, or ShellCheck compliance.` in the Available skills section, alphabetically between `/qrspi-worktree` and `/qrspi-implement`

### Verify

16. Run: `python3 scripts/check_scope.py /workspaces/qrspi/.claude/skills/writing-bash-scripts/SKILL.md`
    - **Expected:** check_scope.py validates the SKILL.md structure and reports no violations
17. Verify frontmatter: parse SKILL.md frontmatter — confirm `name`, `description`, `command`, `argument-hint`, `allowed-tools` fields all present and correct
18. Verify body: confirm SKILL.md body covers all 13 convention topics: strict mode, error handling, argument parsing, subcommand dispatch, logging, quoting, dependency checking, usage/help, temp files, code organization, testing/linting, portability, ShellCheck compliance

### Verify Slice 1

- **Checkpoint:** `grep -c '/writing-bash-scripts' /workspaces/qrspi/.claude/CLAUDE.md && wc -l /workspaces/qrspi/.claude/skills/writing-bash-scripts/SKILL.md`
  - [ ] CLAUDE.md lists `/writing-bash-scripts` in the Available skills section
  - [ ] SKILL.md has valid YAML frontmatter with all required fields
  - [ ] SKILL.md body covers all 13 convention topics from structure contracts
  - [ ] `description` field uses "Use when..." language matching all trigger scenarios
  - [ ] SKILL.md follows agentskills.io standard pattern (H1, trigger, conventions, steps, scope boundary)

---

## Rollback Notes

- Step 1: Delete `.claude/skills/writing-bash-scripts/SKILL.md` to undo skill file creation
- Step 15: Remove the added bullet from CLAUDE.md Available skills section to undo CLAUDE.md update
