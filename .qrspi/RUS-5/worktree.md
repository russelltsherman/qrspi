# Work Tree — writing-bash-scripts skill update

**Plan basis:** plan.md @ 2026-05-27
**Generated:** 2026-05-27
**Status:** draft
**Total sessions:** 2
**Critical path:** T1 → T2 → T3 → T4 → T5 → T6 → T7 → T8

## Session 1

**Load:** structure.md §Slice 1, plan.md §Slice 1, `/home/vscode/.claude/skills/writing-bash-scripts/SKILL.md` (full file)
**Estimated context:** 30%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Fix `command` frontmatter: `writing-bash-scripts` → `/writing-bash-scripts` | — | §1.1 | S | pending |
| T2 | Add 7-section ordered list to Script Structure (compact: numbered bullet list) | T1 | §1.2 | S | pending |
| T3 | Add Usage/Help section: heredoc `usage()` with `${0##*/}` and column alignment | T2 | §1.3 | S | pending |
| T4 | Add Logging section: `[[ -t 2 ]]` color detection pattern with console-only colors | T3 | §1.4 | S | pending |
| T5 | Add debugging trap pattern: `trap 'echo "Error on line $LINENO"' ERR` | T4 | §1.5 | S | pending |
| T6 | Add ~200-line language choice guidance | T5 | §1.6 | S | pending |
| T7 | Add Gotchas section: 3-bullet callouts referencing `references/gotchas.md` | T6 | §1.7 | S | pending |
| T8 | Add `declare -f "cmd_${1}"` dynamic dispatch pattern to Function Conventions | T7 | §1.8 | S | pending |
| T9 | **Verify Slice 1**: Confirm line count < 500, all sections present, frontmatter correct | T8 | §1.9 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** SKILL.md is now complete with all 7 new additions. Slice 1 is self-contained and testable — fresh context for template.sh edits in Slice 2.

## Session 2

**Load:** plan.md §Slice 2, `/home/vscode/.claude/skills/writing-bash-scripts/references/template.sh` (full file), plan.md §Slice 1 (rollback notes only)
**Estimated context:** 15%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T10 | Add debugging trap `trap 'echo "Error on line $LINENO"'` to template.sh Helpers section | T9 | §2.1 | S | pending |
| T11 | Add inline comment on `${0##*/}` in constants section explaining basename extraction | T10 | §2.2 | S | pending |
| T12 | Add `[[ -t 2 ]]` color detection block to template.sh Helpers section | T11 | §2.3 | S | pending |
| T13 | **Verify Slice 2**: `bash -n` syntax check + `shellcheck -x` zero warnings | T12 | §2.4 | S | pending |
