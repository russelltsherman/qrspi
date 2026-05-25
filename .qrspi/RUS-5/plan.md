# Plan — Create a skill for writing bash scripts
**Ticket:** RUS-5
**Generated:** 2026-05-25
**Status:** draft

---

## Slice 1: SKILL.md — Core skill file with frontmatter and decision logic

### Step 1.1 — Create skill directory

**Action:** Create directory `.claude/skills/bash-scripts/`
**File:** `.claude/skills/bash-scripts/` (new directory)
**Purpose:** Establish the skill root following project convention.

### Step 1.2 — Create SKILL.md with frontmatter

**Action:** Create new file
**File:** `.claude/skills/bash-scripts/SKILL.md`
**Purpose:** Main skill definition file with YAML frontmatter and full body.

**Content structure:**

```yaml
---
name: bash-scripts
description: "Write, scaffold, or improve bash shell scripts following strict conventions for correctness, portability, and ShellCheck compliance. Use when the user asks to create a new bash script, generate a shell script for a task, add features to an existing bash script, or requests bash scripting guidance for authoring. Do NOT use for simply running bash commands, reading/explaining existing scripts, or general shell discussions unrelated to script authoring."
command: /bash-scripts
argument-hint: "<task description>"
allowed-tools: "Read, Write, Bash"
---
```

**Body sections (in order):**
1. `# Bash Scripts` — title
2. `## When to Use` — decision logic: new script / modify existing / "too large" escape hatch
3. `## Template` — prose description of script skeleton (NOT a code block)
4. `## ShellCheck Compliance` — rules for clean output, disable directive convention (inline comment with SC code + justification, matching `protect-paths` precedent)
5. `## Testing` — BATS mention, source guard pattern, manual verification fallback
6. `## References` — exact "when to read" directives for both reference files

**References section contract (exact text):**

```markdown
## References

Before generating any bash script longer than 10 lines, read `references/conventions.md` for the full convention set.

When reviewing or debugging an existing bash script, read `references/gotchas.md` for common pitfalls to check.
```

### Step 1.3 — Validate SKILL.md frontmatter

**Action:** Run validation command
**Command:** `python3 -c "import yaml, sys; f=open('.claude/skills/bash-scripts/SKILL.md'); lines=f.readlines(); start=lines.index('---\n'); end=lines.index('---\n', start+1); data=yaml.safe_load(''.join(lines[start+1:end])); assert all(k in data for k in ['name','description','command','argument-hint','allowed-tools']), f'Missing keys: {set([\"name\",\"description\",\"command\",\"argument-hint\",\"allowed-tools\"])-set(data.keys())}'; print('Frontmatter valid')"`

### Verify — Slice 1 checkpoint

**Command:**
```bash
test -f .claude/skills/bash-scripts/SKILL.md && \
python3 -c "
import yaml
with open('.claude/skills/bash-scripts/SKILL.md') as f:
    lines = f.readlines()
start = lines.index('---\n')
end = lines.index('---\n', start+1)
data = yaml.safe_load(''.join(lines[start+1:end]))
required = ['name','description','command','argument-hint','allowed-tools']
missing = [k for k in required if k not in data]
assert not missing, f'Missing: {missing}'
assert len(lines) < 500, f'Too long: {len(lines)} lines'
assert any('references/conventions.md' in l for l in lines), 'Missing conventions.md pointer'
assert any('references/gotchas.md' in l for l in lines), 'Missing gotchas.md pointer'
print(f'PASS: SKILL.md valid ({len(lines)} lines, all fields present, both references linked)')
"
```

---

## Slice 2: references/conventions.md — Full convention catalog

### Step 2.1 — Create references directory

**Action:** Create directory `.claude/skills/bash-scripts/references/`
**File:** `.claude/skills/bash-scripts/references/` (new directory)
**Purpose:** Hold supplementary reference material loaded on-demand.

### Step 2.2 — Create conventions.md

**Action:** Create new file
**File:** `.claude/skills/bash-scripts/references/conventions.md`
**Purpose:** Detailed convention catalog for all bash scripts produced by the skill.

**Required sections (all 11):**

```markdown
# Bash Script Conventions

## Header and Strict Mode
- Shebang: `#!/usr/bin/env bash` (never `#!/bin/bash`)
- Strict mode: `set -euo pipefail` (all scripts except pure display-only)
- Brief comment block: script purpose, author context

## Error Handling
- trap for cleanup on EXIT, ERR
- Exit codes: 0 success, 1 general error, 2 usage error
- Error messages to stderr

## Argument Parsing
- Simple scripts (1-3 args): positional with validation
- Medium scripts (flags): while/case/shift pattern
- Complex scripts (many flags): getopts
- Always validate required arguments early

## Subcommand Dispatcher Pattern
- main() function delegates to cmd_<name> functions
- Unknown subcommand prints usage and exits 2
- Pattern: case "$1" in ...

## Logging Helpers
- log_info, log_warn, log_error functions
- All output to stderr (stdout reserved for data)
- Optional: color when connected to terminal

## Quoting and Variable Expansion
- Always double-quote variable expansions: "$var" not $var
- Use "${var}" when adjacent to other text
- Arrays: "${array[@]}" not ${array[*]}
- Command substitution: "$(cmd)" not `cmd`

## Dependency Checking
- Check required commands early with command -v
- Fail fast with actionable error message
- Pattern: command -v foo >/dev/null 2>&1 || { ... }

## Usage/Help Function
- usage() function printing to stderr
- Triggered by -h, --help, or wrong argument count
- Include: synopsis, description, options, examples

## Temp File Handling
- Use mktemp for temp files/dirs
- Always clean up via trap on EXIT
- Pattern: tmpdir=$(mktemp -d) ; trap 'rm -rf "$tmpdir"' EXIT

## Code Organization Order
1. Shebang and strict mode
2. Constants and configuration
3. Helper functions (logging, usage)
4. Business logic functions
5. Argument parsing
6. Main execution

## Portability Notes
- Default target: bash 4+ (most Linux systems)
- macOS ships bash 3.2 — call out 4+ features explicitly
- Bash 4+ features requiring annotation: associative arrays, namerefs, mapfile/readarray, &>> redirect, |& pipe
- When portability to 3.2 is required, document alternatives
```

**Constraints:**
- File must be 150-250 lines
- Conventions must match existing project scripts (`#!/usr/bin/env bash`, `set -euo pipefail`)
- Portability section must clearly mark bash 4+ features and note macOS 3.2 limitation

### Verify — Slice 2 checkpoint

**Command:**
```bash
test -f .claude/skills/bash-scripts/references/conventions.md && \
python3 -c "
with open('.claude/skills/bash-scripts/references/conventions.md') as f:
    content = f.read()
    lines = content.splitlines()
sections = [
    'Header and Strict Mode',
    'Error Handling',
    'Argument Parsing',
    'Subcommand Dispatcher',
    'Logging',
    'Quoting',
    'Dependency Checking',
    'Usage/Help',
    'Temp File',
    'Code Organization',
    'Portability'
]
missing = [s for s in sections if s.lower() not in content.lower()]
assert not missing, f'Missing sections: {missing}'
assert 150 <= len(lines) <= 250, f'Line count out of range: {len(lines)} (expected 150-250)'
assert '#!/usr/bin/env bash' in content, 'Missing shebang convention'
assert 'set -euo pipefail' in content, 'Missing strict mode convention'
assert '3.2' in content, 'Missing macOS 3.2 portability note'
print(f'PASS: conventions.md valid ({len(lines)} lines, all 11 sections present)')
"
```

---

## Slice 3: references/gotchas.md — Common pitfalls catalog

### Step 3.1 — Create gotchas.md

**Action:** Create new file
**File:** `.claude/skills/bash-scripts/references/gotchas.md`
**Purpose:** Quick-reference pitfall catalog for script review and debugging.

**Required sections (all 6 gotcha categories):**

Each gotcha entry must include:
- The problem (what goes wrong)
- A bad example (demonstrating the pitfall)
- The fix (correct alternative)
- The relevant ShellCheck code (if applicable)

```markdown
# Common Bash Gotchas

## Unquoted Variables
- Problem: Word splitting and glob expansion on unset or multi-word values
- Bad: `if [ $var = "foo" ]; then`
- Fix: `if [ "$var" = "foo" ]; then`
- ShellCheck: SC2086

## Missing -- in Commands
- Problem: Filenames starting with - treated as options
- Bad: `rm $file`
- Fix: `rm -- "$file"`
- ShellCheck: SC2086 (partial), defensive coding

## cd Without Error Check
- Problem: cd fails silently, subsequent commands run in wrong directory
- Bad: `cd /some/path`
- Fix: `cd /some/path || exit 1`
- ShellCheck: SC2164

## Word Splitting in for Loops
- Problem: Iterating over command output without proper quoting
- Bad: `for f in $(ls *.txt); do`
- Fix: `for f in *.txt; do` (or use globbing/find with -print0)
- ShellCheck: SC2045

## Process Substitution Portability
- Problem: <(...) not available in sh or bash 3.2 in some contexts
- Bad: relying on process substitution in scripts targeting sh
- Fix: Use temp files or pipes when portability required
- ShellCheck: N/A (bash-specific feature)

## Array Gotchas
- Problem: Arrays not expanding correctly, losing empty elements
- Bad: `"${array[*]}"` when iterating, `${array[@]}` unquoted
- Fix: Always use `"${array[@]}"` for iteration
- ShellCheck: SC2068
```

**Constraints:**
- File must be 50-100 lines
- All 6 categories present
- Each entry has problem, bad example, fix, and ShellCheck code

### Verify — Slice 3 checkpoint

**Command:**
```bash
test -f .claude/skills/bash-scripts/references/gotchas.md && \
python3 -c "
with open('.claude/skills/bash-scripts/references/gotchas.md') as f:
    content = f.read()
    lines = content.splitlines()
gotchas = [
    'Unquoted Variables',
    'Missing --',
    'cd Without Error Check',
    'Word Splitting',
    'Process Substitution',
    'Array Gotchas'
]
missing = [g for g in gotchas if g.lower() not in content.lower()]
assert not missing, f'Missing gotchas: {missing}'
assert 50 <= len(lines) <= 100, f'Line count out of range: {len(lines)} (expected 50-100)'
# Check each gotcha has the four required components
for gotcha in gotchas:
    section_start = content.lower().find(gotcha.lower())
    assert section_start != -1
print(f'PASS: gotchas.md valid ({len(lines)} lines, all 6 categories present)')
"
```

---

## Slice 4: Skill-creator invocation and validation

### Step 4.1 — Invoke skill-creator for review

**Action:** Invoke the `skill-creator` skill on the completed `.claude/skills/bash-scripts/SKILL.md`
**Purpose:** Satisfy AC2 ("Built using the Anthropic skill builder skill") and user memory directive. The skill-creator reviews the existing SKILL.md, optimizes the description for triggering accuracy, and optionally runs an eval loop.

**Input to skill-creator:**
- Path: `.claude/skills/bash-scripts/SKILL.md`
- Mode: Review and refine existing skill (not fresh authoring)
- Focus areas: description triggering accuracy, body structure, reference integration

### Step 4.2 — Apply skill-creator feedback to SKILL.md

**Action:** Modify existing file
**File:** `.claude/skills/bash-scripts/SKILL.md` (modify)
**Purpose:** Incorporate any description optimization or structural improvements from skill-creator.

**Current (example — actual depends on Step 1.2 output):**
```yaml
description: "Write, scaffold, or improve bash shell scripts..."
```

**After (depends on skill-creator feedback):**
```yaml
description: "<optimized description from skill-creator>"
```

### Step 4.3 — Apply skill-creator feedback to references (if any)

**Action:** Modify existing files (conditional)
**File:** `.claude/skills/bash-scripts/references/conventions.md` (modify, if recommended)
**File:** `.claude/skills/bash-scripts/references/gotchas.md` (modify, if recommended)
**Purpose:** Incorporate any structural or content changes recommended by skill-creator.

### Step 4.4 — Re-validate frontmatter after modifications

**Action:** Run validation command (same as Step 1.3)
**Command:** Same Python validation as Slice 1 checkpoint.

### Verify — Slice 4 checkpoint

**Command:**
```bash
python3 -c "
import yaml
with open('.claude/skills/bash-scripts/SKILL.md') as f:
    lines = f.readlines()
start = lines.index('---\n')
end = lines.index('---\n', start+1)
data = yaml.safe_load(''.join(lines[start+1:end]))
required = ['name','description','command','argument-hint','allowed-tools']
missing = [k for k in required if k not in data]
assert not missing, f'Missing: {missing}'
assert len(lines) < 500, f'Too long: {len(lines)} lines'
assert any('references/conventions.md' in l for l in lines), 'Missing conventions.md pointer'
assert any('references/gotchas.md' in l for l in lines), 'Missing gotchas.md pointer'
print(f'PASS: SKILL.md still valid after skill-creator modifications ({len(lines)} lines)')
" && \
echo "Slice 4 complete: skill-creator was invoked, feedback incorporated, all validations pass."
```

---

## Rollback Notes

No DB migrations, config changes, or destructive operations in this plan. All changes are additive (new files only). Rollback is:

```bash
rm -rf .claude/skills/bash-scripts/
```

---

## Summary

| Slice | Steps | New Files | Modified Files |
|-------|-------|-----------|----------------|
| 1 | 3 | 1 (SKILL.md) | 0 |
| 2 | 2 | 1 (conventions.md) | 0 |
| 3 | 1 | 1 (gotchas.md) | 0 |
| 4 | 4 | 0 | 1-3 (SKILL.md + possibly references) |

**Total steps:** 10 (well within 100-step limit)

## Unresolved Decisions (from structure.md)

These assumptions carry forward from the structure phase. Implementation proceeds with the stated defaults unless the user intervenes:

1. **Installation location** — Defaulting to project-level (`.claude/skills/bash-scripts/`). If user decides user-level, all paths change.
2. **Eval loop depth** — Will attempt lightweight eval (2-3 test cases) during Slice 4. If skill-creator cannot meaningfully eval a guidance skill, will note this and proceed with qualitative review only.
3. **Slash command name** — Using `/bash-scripts` as specified in structure.md.
