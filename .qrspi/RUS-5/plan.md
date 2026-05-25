# Implementation Plan — Create a new agent skill called writing bash scripts

**Structure basis:** structure.md @ 2026-05-25
**Generated:** 2026-05-25
**Status:** draft

---

## Slice 1: Author complete skill (SKILL.md + all references)

### Step 1.1 — Create skill directory structure

**Action:** Create directory
**File:** `~/.agents/skills/writing-bash-scripts/references/`
**Purpose:** Establish the skill directory and nested references directory in user-global location.

```
mkdir -p ~/.agents/skills/writing-bash-scripts/references
```

---

### Step 1.2 — Create references/template.sh

**Action:** Create new file
**File:** `~/.agents/skills/writing-bash-scripts/references/template.sh`
**Purpose:** Canonical starter script demonstrating all structural conventions: shebang, `set -euo pipefail`, constants block, helper functions, command functions, main dispatcher. Must pass `shellcheck` with zero warnings.

**Contract enforced:**
- Shebang line (`#!/usr/bin/env bash`)
- `set -euo pipefail` immediately after shebang
- Constants block (uppercase, readonly)
- Helper functions section (logging, cleanup)
- Command functions section (one function per subcommand)
- Main dispatcher (argument parsing + dispatch)
- ShellCheck-clean (zero warnings)

---

### Step 1.3 — Create references/conventions.md

**Action:** Create new file
**File:** `~/.agents/skills/writing-bash-scripts/references/conventions.md`
**Purpose:** Full bash conventions reference covering: quoting rules, variable handling, dependency checking, temp file management, exit codes, signal trapping.

**Content sections:**
- Quoting (double-quote all variable expansions, when single quotes are appropriate)
- Variable handling (local in functions, readonly for constants, naming conventions)
- Dependency checking (command -v guards, version checks)
- Temp file management (mktemp, trap-based cleanup)
- Exit codes (standard meanings, custom ranges)
- Signal trapping (SIGINT, SIGTERM, cleanup patterns)

---

### Step 1.4 — Create references/patterns.md

**Action:** Create new file
**File:** `~/.agents/skills/writing-bash-scripts/references/patterns.md`
**Purpose:** Subcommand dispatcher pattern, argument parsing (getopts and manual), logging helper library, function organization.

**Content sections:**
- Subcommand dispatcher (case statement pattern, help generation)
- Argument parsing with getopts (short opts, long opts via manual parsing)
- Manual argument parsing (shift-based, positional args)
- Logging helpers (log_info, log_warn, log_error, log_debug with levels)
- Function organization (declaration order, naming conventions)

---

### Step 1.5 — Create references/gotchas.md

**Action:** Create new file
**File:** `~/.agents/skills/writing-bash-scripts/references/gotchas.md`
**Purpose:** Portability notes (BSD vs GNU coreutils, bash 3.2 vs 4+), common ShellCheck warnings and fixes, pitfalls (word splitting, globbing, subshell variable scope).

**Content sections:**
- BSD vs GNU coreutils differences (sed -i, date, readlink, find)
- Bash 3.2 vs 4+ (associative arrays, mapfile, &>> redirect)
- Common ShellCheck warnings (SC2086, SC2046, SC2155, SC2164) with fixes
- Word splitting pitfalls (unquoted expansions, IFS behavior)
- Globbing hazards (nullglob, set -f, quoting in loops)
- Subshell variable scope (pipes, process substitution, command substitution)

---

### Step 1.6 — Create SKILL.md

**Action:** Create new file
**File:** `~/.agents/skills/writing-bash-scripts/SKILL.md`
**Purpose:** Main skill definition with YAML frontmatter (`name: writing-bash-scripts`, `description: <trigger string>`, `command: writing-bash-scripts`), trigger conditions, concise conventions summary, and conditional pointers to reference files. Must stay under 500 lines (target 150-200).

**Contract enforced:**
- Frontmatter contains `name: writing-bash-scripts`
- Frontmatter contains `description:` with trigger language covering: writing new bash scripts, modifying .sh files, reviewing shell code
- Frontmatter contains `command: writing-bash-scripts`
- Body includes conditional Read instructions for each reference file with clear trigger conditions:
  - "If writing a multi-command script, read `references/patterns.md`"
  - "If dealing with portability or ShellCheck issues, read `references/gotchas.md`"
  - "If unsure about quoting, variables, or cleanup, read `references/conventions.md`"
  - "For a complete structural example, read `references/template.sh`"
- Body under 500 lines total

**Content outline:**
1. Frontmatter block
2. Trigger conditions (when this skill activates)
3. Script structure overview (shebang, strict mode, constants, helpers, commands, main)
4. Error handling essentials (set -euo pipefail semantics, trap patterns)
5. Argument parsing summary (getopts for simple, manual for complex)
6. Code organization rules (function naming, ordering, file layout)
7. Testing guidance (bats framework, test structure)
8. Conditional reference pointers (when to load each reference file)

---

### Step 1.7 — Verify: ShellCheck validation

**Action:** Verify checkpoint
**Command:**
```bash
shellcheck ~/.agents/skills/writing-bash-scripts/references/template.sh
```
**Expected:** Exit code 0, no warnings or errors.

---

### Step 1.8 — Verify: SKILL.md line count

**Action:** Verify checkpoint
**Command:**
```bash
wc -l ~/.agents/skills/writing-bash-scripts/SKILL.md
```
**Expected:** Line count under 500.

---

### Step 1.9 — Verify: Frontmatter fields present

**Action:** Verify checkpoint
**Command:**
```bash
head -20 ~/.agents/skills/writing-bash-scripts/SKILL.md | grep -E '^(name|description|command):'
```
**Expected:** All three fields (`name`, `description`, `command`) appear in output.

---

### Step 1.10 — Verify: Reference file pointers in SKILL.md body

**Action:** Verify checkpoint
**Command:**
```bash
grep -c 'references/' ~/.agents/skills/writing-bash-scripts/SKILL.md
```
**Expected:** At least 4 (one pointer per reference file: conventions.md, patterns.md, gotchas.md, template.sh).

---

### Step 1.11 — Verify: All reference files exist

**Action:** Verify checkpoint
**Command:**
```bash
ls ~/.agents/skills/writing-bash-scripts/references/conventions.md ~/.agents/skills/writing-bash-scripts/references/patterns.md ~/.agents/skills/writing-bash-scripts/references/gotchas.md ~/.agents/skills/writing-bash-scripts/references/template.sh
```
**Expected:** All four files listed without errors.

---

## Rollback Notes

No database migrations, config changes, or destructive operations in this slice. All files are net-new. Rollback is:

```bash
rm -rf ~/.agents/skills/writing-bash-scripts/
```

---

## Implementation Order Summary

| Step | File | Action |
|------|------|--------|
| 1.1 | `~/.agents/skills/writing-bash-scripts/references/` | Create directory |
| 1.2 | `references/template.sh` | Create new file |
| 1.3 | `references/conventions.md` | Create new file |
| 1.4 | `references/patterns.md` | Create new file |
| 1.5 | `references/gotchas.md` | Create new file |
| 1.6 | `SKILL.md` | Create new file |
| 1.7 | — | Verify: shellcheck template.sh |
| 1.8 | — | Verify: SKILL.md line count < 500 |
| 1.9 | — | Verify: frontmatter fields |
| 1.10 | — | Verify: reference pointers in body |
| 1.11 | — | Verify: all reference files exist |

**Total steps:** 11 (well within 100-step limit)
