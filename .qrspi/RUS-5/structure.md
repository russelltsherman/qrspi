# Structure Outline — Create a new agent skill called writing bash scripts

**Design basis:** design.md @ 2026-05-25
**Generated:** 2026-05-25
**Status:** draft

## New Types

None. This is a content-only skill (Markdown prose and a shell template). No application types are introduced.

## Modified Types

None. No existing project code is modified.

## Contracts

- `SKILL.md frontmatter` — must contain `name: writing-bash-scripts`, `description: <trigger string>`, `command: writing-bash-scripts`
- `SKILL.md body → references/` pointer contract — body must include explicit conditional Read instructions (e.g., "If writing a multi-command script, read `references/patterns.md`") so the consuming agent knows when to load detail
- `references/template.sh` — must pass `shellcheck` with zero warnings; must demonstrate: shebang, `set -euo pipefail`, constants block, helper functions, command functions, main dispatcher

## Slice 1: Author complete skill (SKILL.md + all references)

**Goal:** Deliver a fully functional `writing-bash-scripts` skill at `~/.agents/skills/writing-bash-scripts/` with valid frontmatter, concise body under 500 lines, and topic-split reference files — invocable via `/writing-bash-scripts` and auto-triggered on bash script creation/modification requests.

**Files touched:**

- ✨ `~/.agents/skills/writing-bash-scripts/SKILL.md` — Main skill definition: YAML frontmatter (`name`, `description`, `command`), trigger conditions, concise conventions summary (~150-200 lines), conditional pointers to reference files
- ✨ `~/.agents/skills/writing-bash-scripts/references/conventions.md` — Full bash conventions: quoting rules, variable handling, dependency checking, temp file management, exit codes, signal trapping
- ✨ `~/.agents/skills/writing-bash-scripts/references/patterns.md` — Subcommand dispatcher pattern, argument parsing (getopts and manual), logging helper library, function organization
- ✨ `~/.agents/skills/writing-bash-scripts/references/gotchas.md` — Portability notes (BSD vs GNU coreutils, bash 3.2 vs 4+), common ShellCheck warnings and fixes, pitfalls (word splitting, globbing, subshell variable scope)
- ✨ `~/.agents/skills/writing-bash-scripts/references/template.sh` — Canonical starter script demonstrating all structural conventions (shebang, strict mode, constants, helpers, commands, main)

**Verification:**

- [ ] `SKILL.md` has valid frontmatter with `name`, `description`, and `command` fields
- [ ] `SKILL.md` body is under 500 lines (target: 150-200)
- [ ] `SKILL.md` body contains conditional pointers to each reference file with clear trigger conditions
- [ ] `references/template.sh` passes `shellcheck` with zero warnings
- [ ] All code examples in reference files use proper quoting and `set -euo pipefail`
- [ ] Skill is invocable: placing files at target path makes `/writing-bash-scripts` available in Claude Code
- [ ] Run `skill-creator` eval/validation if available to confirm structural compliance

**Context cost:** M
**Depends on:** none

---

## Unverified Assumptions

1. **Placement path `~/.agents/skills/`** — The design recommends user-global placement. This was flagged as Open Question #1 in design.md. If the user decides project-local placement, the target path changes to `.claude/skills/writing-bash-scripts/`. The structure is identical either way.

2. **`command` field in frontmatter passes Claude Code discovery** — The design states all QRSPI skills use `command` and it works, but also notes `quick_validate.py` would reject it. We assume Claude Code's skill discovery mechanism (not `quick_validate.py`) is what matters at runtime. Cannot verify without testing.

3. **Trigger conditions are sufficient** — The design does not finalize which phrases/contexts auto-invoke this skill (Open Question #2). The `description` field in frontmatter must encode these triggers. The implementer will need to craft trigger language covering: writing new bash scripts, modifying `.sh` files, and possibly reviewing shell code.

4. **ShellCheck version compatibility** — The design says "ShellCheck-clean" but does not pin a version (Open Question #4). Template and examples will target ShellCheck 0.9+ conventions. If the user's environment runs an older version, some directives may differ.

5. **No existing scripts are retroactively modified** — Open Question #3 in design.md. This structure assumes the skill is forward-looking only and does not include a slice to refactor `run_loop.sh` or `post-start.sh`.
