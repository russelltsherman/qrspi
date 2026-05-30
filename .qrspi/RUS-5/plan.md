# Implementation Plan — Refine writing-bash-scripts skill

**Structure basis:** structure.md @ 2026-05-30
**Generated:** 2026-05-30T00:00:00Z
**Status:** draft
**Total steps:** 18

## Slice 1: SKILL.md body refinement

### Setup

1. ✨ Add "Scope and When to Switch Languages" section to `~/.claude/skills/writing-bash-scripts/SKILL.md` -- Insert after the "When to load reference files" section (line 28). Content: script body should not exceed ~200 lines without strong justification; decision tree with concrete criteria: using more than 3 associative arrays, parsing JSON, building a web server, using a complex CLI framework. If two or more apply, write in Python or Go instead. Write as Markdown section with header.

2. ⚠️ Modify `~/.claude/skills/writing-bash-scripts/SKILL.md` -- Rename all logging helper calls from `log_info()`/`log_warn()`/`log_error()` to `info()`/`warn()`/`die()`.
   - **Current:** `log_info()`, `log_warn()`, `log_error()` appear in code examples at lines 45-46, 100, 153, 187, 188, 213, and 236
   - **After:** `info()`, `warn()`, `die()` -- the new naming convention specified in structure.md Contracts section

3. ⚠️ Modify `~/.claude/skills/writing-bash-scripts/SKILL.md` -- Consolidate the bash 4+ version check as a cross-reference.
   - **Current:** No mention of bash version check in SKILL.md body; `check_bash_version()` function lives only in `references/conventions.md` (lines 127-132)
   - **After:** Add a hard constraint paragraph stating bash 4+ is required, with `[check_bash_version()]` linked to `references/conventions.md` as the canonical implementation reference. This prevents the requirement from being missed by agents (design Decision 3, Option C).

4. ✨ Add "Gotchas" section to `~/.claude/skills/writing-bash-scripts/SKILL.md` -- Insert before the ShellCheck section (line 255). Content: inline summary of the most common bash pitfalls -- unquoted variables in conditionals (SC2086), subshell variable scope in pipes, bash 3.2 vs 4.0 feature gaps (BSD vs GNU coreutils, empty array expansion under `set -u`), quoting inside `[[ ]]`, `set -e` with expected failures. Reference `references/gotchas.md` for the full list.

### Verify Slice 1

5. **Checkpoint:** `wc -l ~/.claude/skills/writing-bash-scripts/SKILL.md`
   - [ ] Line count is <= 500
   - [ ] All four changes are present: scope guidance, logging names, bash version cross-ref, gotchas section
   - [ ] No remaining `log_info()`/`log_warn()`/`log_error()` calls anywhere in the file body

---

## Slice 2: conventions.md update + new scaffolding files

### Setup

6. ✨ Create `~/.claude/skills/writing-bash-scripts/references/bats-template.bats` -- BATS scaffolding with common patterns: setup/teardown hooks, assertion helpers (`assert_exit_code`, `assert_output_contains`, `assert_file_exists`), one example test group covering a typical bash script pattern (flag parsing via `getopts`, subcommand dispatch, error handling with `die()`, temp file cleanup via trap).

7. ✨ Create `~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` -- Cross-platform BATS installer. Homebrew on macOS (`brew install bats-core`), source install on Linux (clone `bats-core`, run `./install.sh /usr/local`). Idempotent: checks `command -v bats` before installing. Prints success/failure status. Uses `#!/usr/bin/env bash`, `set -euo pipefail`.

### Core Logic

8. ⚠️ Modify `~/.claude/skills/writing-bash-scripts/references/conventions.md` -- Rename all logging helper references to match the new naming convention.
   - **Current:** `log_info()` at line 213, `log_warn()` at line 218, `log_error()` at lines 113, 129, 200, 213
   - **After:** `info()` at lines 213, 218; `die()` at lines 113, 129, 200, 213 -- consistent with the `log()`/`info()`/`warn()`/`die()` convention defined in structure.md Contracts

### Tests

9. Run: `bash -n ~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` -- Syntax check the BATS installer script.
   - **Expected:** `bash -n` exits 0 (no syntax errors)

10. Run: `bats ~/.claude/skills/writing-bash-scripts/references/bats-template.bats` -- Validate the BATS template. If BATS is not installed, skip this test and note it in the verification criteria.
   - **Expected:** BATS exits 0, all assertions pass, template is valid BATS syntax

### Verify Slice 2

11. **Checkpoint:** `grep -rn 'log_info\|log_warn\|log_error' ~/.claude/skills/writing-bash-scripts/` -- Scan all skill files for old logging names.
   - [ ] Zero remaining references to `log_info()`/`log_warn()`/`log_error()` across all skill files (SKILL.md body, conventions.md, patterns.md, template.sh)
   - [ ] BATS syntax check passed (or BATS not available -- noted)
   - [ ] `bats-template.bats` is valid BATS (loadable by `bats bats-template.bats` if BATS installed)

---

## Slice 3: Validation pass

### Core Logic

12. Run: `which shellcheck` -- Verify ShellCheck is available in the environment.
   - **Expected:** `which shellcheck` returns a path (e.g., `/usr/bin/shellcheck`). If not found, note that ShellCheck validation will be skipped and recommend installation.

13. Run: `shellcheck ~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` -- Validate the BATS installer script against ShellCheck rules.
   - **Expected:** exits 0 (no warnings or errors)

14. Run: `shellcheck ~/.claude/skills/writing-bash-scripts/references/bats-template.bats` -- Validate the BATS template file. ShellCheck may flag BATS-specific globals (`$output`, `$status`, `@test`, `run`) as undefined. This is expected -- add appropriate `shellcheck disable` directives if needed.
   - **Expected:** exits 0 after adding any necessary `shellcheck disable` directives for BATS-specific syntax, OR skips if ShellCheck not installed

15. Run: `wc -l ~/.claude/skills/writing-bash-scripts/SKILL.md` -- Verify the final SKILL.md is within the 500-line budget.
   - **Expected:** line count <= 500

16. Run: `diff` comparison or manual review of SKILL.md -- Confirm all four changes are present and consistent:
   - [ ] Scope guidance section with language-switching decision tree
   - [ ] Logging helpers use new names (`info()`, `warn()`, `die()`) throughout
   - [ ] Bash version check cross-reference to conventions.md
   - [ ] Gotchas section with inline summary

17. Run: `grep -rn 'log_info\|log_warn\|log_error' ~/.claude/skills/writing-bash-scripts/` -- Final scan across all skill files.
   - **Expected:** Zero matches. All instances have been renamed.

### Verify Slice 3

18. **Checkpoint:** `shellcheck -x ~/.claude/skills/writing-bash-scripts/references/conventions.md` -- Run ShellCheck on the updated conventions file to ensure no warnings from the renaming changes.
   - [ ] ShellCheck exits 0 (or issues only SKIPPED warnings if ShellCheck not installed)
   - [ ] All four SKILL.md changes verified present
   - [ ] Zero `log_info`/`log_warn`/`log_error` references anywhere in the skill
   - [ ] SKILL.md <= 500 lines

---

## Rollback Notes

- **Steps 1-4:** Edit `~/.claude/skills/writing-bash-scripts/SKILL.md`. Rollback: `git checkout -- ~/.claude/skills/writing-bash-scripts/SKILL.md` or restore from backup. The scope guidance and gotchas sections can be removed by deleting the added Markdown blocks.
- **Step 6:** New file `~/.claude/skills/writing-bash-scripts/references/bats-template.bats`. Rollback: `rm ~/.claude/skills/writing-bash-scripts/references/bats-template.bats`.
- **Step 7:** New file `~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh`. Rollback: `rm ~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` and `rm -rf ~/.claude/skills/writing-bash-scripts/scripts/` if the scripts directory was not previously present.
- **Step 8:** Edit `~/.claude/skills/writing-bash-scripts/references/conventions.md`. Rollback: revert the `info()`/`warn()`/`die()` renames back to `log_info()`/`log_warn()`/`log_error()`.
- **Steps 15-16:** ShellCheck fixes to `install-bats.sh` or `bats-template.bats`. Rollback: revert any `shellcheck disable` directives added.
