# Structure Outline — Refine writing-bash-scripts skill

**Design basis:** design.md @ 2026-05-30
**Generated:** 2026-05-30
**Status:** draft

## New Types

None. This is a content-only refinement of an existing skill -- no new types, interfaces, or function signatures are introduced.

## Modified Types

None. No existing code is refactored; the skill SKILL.md body and reference files are updated in place.

## Contracts

- `check_bash_version()` -> `boolean` -- Returns exit 0 if bash >= 4.0, exit 1 otherwise. Declared in `references/conventions.md`, cross-referenced from SKILL.md body.
- `die(message)` -> `never` -- Prints message to stderr and calls `exit 1`. Canonical logging helper name in the skill convention.
- `info(message)` -> `void` -- Prints message to stdout (or to file if LOG_FILE is set).
- `warn(message)` -> `void` -- Prints message prefixed with WARNING to stderr.
- `log(message)` -> `void` -- Prints message to stdout. Alias for `info` in the new naming convention.

## Slice 1: SKILL.md body refinement

**Goal:** Update the SKILL.md body with scope guidance (~200-line threshold with language-switching criteria), reconcile logging helper names to the ticket spec (`log()`/`info()`/`warn()`/`die()`), and move the bash version check from references into the SKILL.md body with a cross-reference to conventions.md for the implementation.

**Files touched:**

- ⚠️ `~/.claude/skills/writing-bash-scripts/SKILL.md` -- Add scope guidance section with concrete decision tree for bash vs Python/Go switching; rename logging helper references from `log_info()`/`log_warn()`/`log_error()` to `info()`/`warn()`/`die()`; add bash version check paragraph with link to `references/conventions.md`; add `die()` function signature to the convention section.
**Verification:**
- [ ] SKILL.md body remains under 500 lines (current 273 + additions estimated at ~40-50 lines of new content)
- [ ] All logging helper references in the body use new names (`log()`, `info()`, `warn()`, `die()`) -- no remaining `log_info()`/`log_warn()`/`log_error()` calls
- [ ] Bash version check appears in SKILL.md body as a hard constraint with link to conventions.md
- [ ] Scope guidance section includes concrete criteria: JSON parsing, associative arrays, web server, CLI framework
**Context cost:** S
**Depends on:** none

## Slice 2: conventions.md and new scaffolding files

**Goal:** Update `references/conventions.md` to reconcile logging naming and remove the duplicated bash version check (now in SKILL.md body). Add BATS scaffolding file (`references/bats-template.bats`) and cross-platform BATS install script (`scripts/install-bats.sh`).

**Files touched:**

- ⚠️ `~/.claude/skills/writing-bash-scripts/references/conventions.md` -- Rename `log_info()`/`log_warn()`/`log_error()` references to `info()`/`warn()`/`die()`; remove duplicated bash version check paragraph (already in SKILL.md body); keep `check_bash_version()` function implementation as the canonical reference.
- ✨ `~/.claude/skills/writing-bash-scripts/references/bats-template.bats` -- BATS scaffolding with common patterns: setup/teardown hooks, assertion helpers (assert_exit_code, assert_output_contains, assert_file_exists), example test group covering a typical bash script pattern (flag parsing, subcommands, error handling).
- ✨ `~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` -- Cross-platform BATS installer supporting Homebrew (macOS) and source install (Linux). Idempotent with version check, prints success/failure status.
**Verification:**
- [ ] `references/conventions.md` has zero remaining references to `log_info()`/`log_warn()`/`log_error()`
- [ ] BASH_VERSION_CHECK is mentioned in SKILL.md body but the full implementation lives only in conventions.md (no duplication)
- [ ] `bats-template.bats` is valid BATS syntax (can be loaded by `bats bats-template.bats` without error)
- [ ] `install-bats.sh` runs cleanly under bash 4+ and detects installed BATS without errors (idempotent)
**Context cost:** S
**Depends on:** Slice 1

## Slice 3: Validation pass

**Goal:** Run ShellCheck on all bash files in the skill to confirm the skill produces ShellCheck-clean output when an agent follows its guidance. Verify SKILL.md line count and overall consistency.

**Files touched:**

- ✨ `~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` -- (refined by ShellCheck fixes if any found)
- ✨ `~/.claude/skills/writing-bash-scripts/references/bats-template.bats` -- (refined by ShellCheck fixes if any found)
**Verification:**
- [ ] `shellcheck ~/.claude/skills/writing-bash-scripts/scripts/install-bats.sh` exits 0 (no warnings)
- [ ] `shellcheck ~/.claude/skills/writing-bash-scripts/references/bats-template.bats` exits 0 (no warnings -- or excludes BATS-specific directives if applicable)
- [ ] `wc -l ~/.claude/skills/writing-bash-scripts/SKILL.md` reports <= 500
- [ ] Final pass: `diff` of SKILL.md shows all three intended changes (scope section, logging names, bash version) are present and consistent
**Context cost:** S
**Depends on:** Slice 2

---

## Unverified Assumptions

1. **Global vs. project skill location.** The design does not resolve OQ2 (should this be a global or project skill). The structure assumes the existing global location `~/.claude/skills/writing-bash-scripts/` is correct. If the decision shifts to a project skill, all file paths in these slices would need to change.
2. **Skill-creator workflow for refinement.** OQ3 asks whether to invoke the skill-creator for this refinement. The structure treats this as manual editing. If skill-creator should be used, the validation slice would need to include running `skill-creator` against the result.
3. **ShellCheck availability.** The design notes ShellCheck may not be installed in the environment. The validation slice assumes it is present. If absent, the verification step becomes "confirm ShellCheck is installed and re-run validation later."
4. **Backwards compatibility not required.** The structure assumes existing scripts using `log_info()`/`log_warn()`/`log_error()` should adopt the new naming on their next rewrite, rather than maintaining aliases. This follows the design's recommendation but has not been validated against actual script usage.
5. **BATS scaffolding scope.** The design recommends Option B (minimal scaffold) for BATS scaffolding. The exact content of `bats-template.bats` (which patterns to include) is left to implementation judgment. If the agent produces a scaffold that exceeds the reference file size budget, it may need to be trimmed.
