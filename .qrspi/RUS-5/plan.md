# Implementation Plan — writing-bash-scripts agent skill

**Structure basis:** structure.md @ 2026-05-31
**Generated:** 2026-05-31T00:00:00Z
**Status:** draft
**Total steps:** 4

## Slice 1: Create writing-bash-scripts skill

### Setup

1. Verify `.claude/skills/writing-bash-scripts/references/` directory is empty (A1). Run `ls -la /workspaces/qrspi/.claude/skills/writing-bash-scripts/references/` and confirm zero files. If any files exist, document them for review before proceeding.

### Core Logic

2. ✨ Create `/workspaces/qrspi/.claude/skills/writing-bash-scripts/SKILL.md` — Complete skill document (~180-250 lines) with:
   - YAML frontmatter: `name: writing-bash-scripts`, `description`, `command: /writing-bash-scripts`, `argument-hint`, `allowed-tools: [Bash, Read, Write, Edit]`
   - Sections in this order: When to use, Code Organization (top-to-bottom), Strict Mode, Error Handling, Argument Parsing, Subcommand Dispatcher, Logging, Quoting & Variables, Dependency Checking, Usage/Help, Temp Files, Testing & Linting, Portability, Gotchas, Scope Guidance
   - Per structure.md contract: `SkillHarness(SKILL.md) => SkillFrontmatter + guidance body`
   - Each section includes a concrete bash code example
   - Gotchas section covers: unquoted variables, missing `--` in commands, `cd` without error check
   - BATS-core mentioned by name with inline example in Testing & Linting section
   - Dependency checking uses generic pattern (exit code 1, stderr message) -- no per-dependency mapping
   - Body stays under 500 lines / 5000 tokens target

3. ✨ Create `/workspaces/qrspi/.claude/skills/writing-bash-scripts/references/bash-template.sh` — Minimal working bash script (~60-80 lines) demonstrating all conventions in a single copy-paste base. Includes:
   - `#!/usr/bin/env bash` shebang (portability)
   - `set -euo pipefail` strict mode
   - Argument parsing with `getopts` or manual `$@` handling
   - Subcommand dispatcher pattern (`case "$1" in`)
   - Logging function (`log_info`, `log_error`)
   - Proper quoting throughout
   - Dependency check helper
   - Temp file cleanup with `trap`
   - Usage/help function
   - All conventions applied consistently

### Tests

4. Verify both files are syntactically valid and meet acceptance criteria:
   - Run: `bash -n /workspaces/qrspi/.claude/skills/writing-bash-scripts/references/bash-template.sh`
     - **Expected:** exit 0 (no syntax errors)
   - Run: `wc -l /workspaces/qrspi/.claude/skills/writing-bash-scripts/SKILL.md`
     - **Expected:** output between 180 and 500 lines
   - Grep SKILL.md for all 12 section headers: `## Strict Mode`, `## Error Handling`, `## Argument Parsing`, `## Subcommand Dispatcher`, `## Logging`, `## Quoting & Variables`, `## Dependency Checking`, `## Usage/Help`, `## Temp Files`, `## Testing & Linting`, `## Portability`, `## Gotchas`, `## Scope Guidance`, `## When to use`, `## Code Organization (top-to-bottom)`
     - **Expected:** all sections present
   - Grep SKILL.md frontmatter for YAML keys: `name:`, `description:`, `command:`, `argument-hint:`, `allowed-tools:`
     - **Expected:** all five keys present

### Verify Slice 1

5. **Checkpoint:** Full acceptance criteria pass
   - [ ] SKILL.md frontmatter parses correctly: `name`, `description`, `command: /writing-bash-scripts`, `argument-hint`, `allowed-tools` keys present
   - [ ] SKILL.md body is under 500 lines
   - [ ] SKILL.md covers all 12 convention sections from structure.md
   - [ ] Gotchas section covers: unquoted variables, missing `--` in commands, `cd` without error check
   - [ ] BATS-core is mentioned by name with an inline example
   - [ ] Dependency checking uses generic pattern (exit code 1, stderr message)
   - [ ] Bash template in `references/bash-template.sh` passes `bash -n` syntax check
   - [ ] Template demonstrates all conventions in a single working script

---

## Rollback Notes

- Step 2: Delete `/workspaces/qrspi/.claude/skills/writing-bash-scripts/SKILL.md` to remove the skill document.
- Step 3: Delete `/workspaces/qrspi/.claude/skills/writing-bash-scripts/references/bash-template.sh` to remove the template file.
- Step 1: No rollback needed -- verification-only step.
