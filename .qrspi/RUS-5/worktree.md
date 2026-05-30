# Work Tree — Refine writing-bash-scripts skill

**Plan basis:** plan.md @ 2026-05-30T00:00:00Z
**Generated:** 2026-05-30T00:00:00Z
**Status:** draft
**Total sessions:** 3
**Critical path:** T1 → T5 → T6 → T10 → T18

## Session 1

**Load:** SKILL.md (full body), structure.md §Contracts, plan.md §Slice 1
**Estimated context:** 15%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T1 | Add "Scope and When to Switch Languages" section to SKILL.md (after "When to load reference files" at line 28) -- decision tree: script body >200 lines, >3 associative arrays, parsing JSON, building web server, complex CLI framework; if 2+ apply, use Python or Go | — | §1.1 | S | pending |
| T2 | Rename all logging helpers in SKILL.md: `log_info()` → `info()`, `log_warn()` → `warn()`, `log_error()` → `die()` (affects lines 45-46, 100, 153, 187-188, 213, 236) | T1 | §1.2 | S | pending |
| T3 | Add bash 4+ hard-constraint paragraph with `[check_bash_version()]` linked to `references/conventions.md` as canonical implementation | T1 | §1.3 | S | pending |
| T4 | Add "Gotchas" section before ShellCheck section (at line 255) -- inline summary: unquoted vars in conditionals (SC2086), subshell scope in pipes, bash 3.2 vs 4.0 gaps, quoting inside `[[ ]]`, `set -e` with expected failures; reference `references/gotchas.md` for full list | T1 | §1.4 | S | pending |
| T5 | **Verify Slice 1:** Check SKILL.md line count ≤500, confirm all four changes present, zero remaining `log_info()`/`log_warn()`/`log_error()` calls | T1, T2, T3, T4 | §1.5 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 1 complete. SKILL.md edits finalized and verified. Fresh context needed to work with conventions.md, new files, and testing tooling.

## Session 2

**Load:** SKILL.md §final state (notes only, post-Slice 1), conventions.md (full), SKILL.md §logging references (context for rename), plan.md §Slice 2
**Estimated context:** 20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T6 | Create `references/bats-template.bats` -- BATS scaffolding: setup/teardown hooks, assertion helpers (`assert_exit_code`, `assert_output_contains`, `assert_file_exists`), example test group covering flag parsing via getopts, subcommand dispatch, error handling with `die()`, temp file cleanup via trap | T5 | §2.1 | M | pending |
| T7 | Create `scripts/install-bats.sh` -- Cross-platform BATS installer: Homebrew on macOS, source install on Linux, idempotent (`command -v bats` guard), success/failure output, `#!/usr/bin/env bash`, `set -euo pipefail` | T5 | §2.2 | M | pending |
| T8 | Rename all logging helpers in `references/conventions.md`: `log_info()` → `info()`, `log_warn()` → `warn()`, `log_error()` → `die()` (affects lines 113, 129, 200, 213, 218) | T5 | §2.3 | S | pending |
| T9 | Syntax check `scripts/install-bats.sh` via `bash -n` -- expect exit 0 | T7 | §2.4 | S | pending |
| T10 | Run `bats` on `references/bats-template.bats` -- expect all assertions pass. If BATS not installed, skip and note in verification | T6, T9 | §2.5 | S | pending |
| T11 | **Verify Slice 2:** Scan all skill files for old logging names (zero remaining), confirm BATS syntax check passed, verify bats-template.bats is valid BATS | T5, T8, T10 | §2.6 | S | pending |

--- SESSION BOUNDARY ---
**Reason:** Slice 2 complete. New scaffolding files created and verified, conventions.md updated. Fresh context for final validation pass to avoid stale state from previous edits.

## Session 3

**Load:** scripts/ (install-bats.sh), references/bats-template.bats, SKILL.md (final state, Slice 1 + rename), conventions.md (final state, Slice 2 rename), plan.md §Slice 3
**Estimated context:** 20%

| Task ID | Description | Depends On | Plan Step | Cost | Status |
|---------|-------------|------------|-----------|------|--------|
| T12 | Verify ShellCheck is available via `which shellcheck` -- note if not found for downstream skip decisions | T11 | §3.1 | S | pending |
| T13 | Run `shellcheck` on `scripts/install-bats.sh` -- expect exit 0, no warnings or errors | T11, T12 | §3.2 | S | pending |
| T14 | Run `shellcheck` on `references/bats-template.bats` -- add `shellcheck disable` directives for BATS-specific globals (`$output`, `$status`, `@test`, `run`) as needed | T11, T12 | §3.3 | S | pending |
| T15 | Re-check `wc -l` on SKILL.md to confirm final line count ≤500 | T11 | §3.4 | S | pending |
| T16 | Diff/comparison review of SKILL.md -- confirm all four changes present and consistent: scope guidance, logging renames, bash version cross-ref, gotchas section | T11, T15 | §3.5 | S | pending |
| T17 | Final scan: `grep -rn 'log_info\|log_warn\|log_error'` across all skill files -- expect zero matches | T11, T13 | §3.6 | S | pending |
| T18 | **Verify Slice 3:** Run `shellcheck -x` on conventions.md, confirm all four SKILL.md changes, zero old logging names, SKILL.md ≤500 lines | T13, T14, T16, T17 | §3.7 | S | pending |
