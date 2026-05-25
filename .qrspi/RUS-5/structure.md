# Structure — Create a skill for writing bash scripts
**Ticket:** RUS-5
**Generated:** 2026-05-25
**Status:** draft

## Types and Signatures

### SKILL.md Frontmatter (YAML)

```yaml
name: string          # "bash-scripts"
description: string   # Triggering description (~50-100 words)
command: string       # "/bash-scripts"
argument-hint: string # "<task description>"
allowed-tools: string # "Read, Write, Bash"
```

### SKILL.md Body (Markdown)

```
# <Skill Title>
## When to Use (decision logic: new script / modify existing / "too large" escape hatch)
## Template (prose description of script skeleton — NOT a code block per skill-creator rules)
## ShellCheck Compliance (rules for clean output, disable directive convention)
## Testing (BATS mention, source guard pattern, manual verification fallback)
## References (when-to-read guidance for each reference file)
```

### references/conventions.md (Markdown)

```
# Bash Script Conventions
## Header and Strict Mode
## Error Handling (trap, exit codes, stderr)
## Argument Parsing (getopts vs while/case/shift)
## Subcommand Dispatcher Pattern
## Logging Helpers
## Quoting and Variable Expansion
## Dependency Checking
## Usage/Help Function
## Temp File Handling
## Code Organization Order
## Portability Notes (bash 3.2 vs 4+ vs 5+)
```

### references/gotchas.md (Markdown)

```
# Common Bash Gotchas
## Unquoted Variables
## Missing -- in Commands
## cd Without Error Check
## Word Splitting in for Loops
## Process Substitution Portability
## Array Gotchas
```

---

## Vertical Slices

### Slice 1: SKILL.md — Core skill file with frontmatter and decision logic

**Goal:** Produce a functional `.claude/skills/bash-scripts/SKILL.md` with valid frontmatter and the main body sections (When to Use, Template, ShellCheck, Testing, References). This file alone delivers a working skill that Claude can discover and invoke.

**Files touched:**
| File | Action |
|------|--------|
| `.claude/skills/bash-scripts/SKILL.md` | new |

**Verification:**
- File exists at the correct path
- YAML frontmatter parses without error (validate with `python3 -c "import yaml; yaml.safe_load(open(...))"` on the frontmatter block)
- `name`, `description`, `command`, `argument-hint`, `allowed-tools` fields are present
- Body is under 500 lines
- Contains "when to read" instructions for both reference files
- Contains decision logic (when to write a new script vs modify vs escape to another language)
- Contains ShellCheck compliance rules including the disable-with-justification convention

**Context cost:** S (single file, ~200-300 lines)

**Dependencies:** None — this is the foundation slice.

---

### Slice 2: references/conventions.md — Full convention catalog

**Goal:** Produce the detailed reference file covering all bash scripting conventions (header, strict mode, error handling, argument parsing, subcommand dispatch, logging, quoting, deps, organization, portability). This file is loaded by Claude only when generating a script, keeping SKILL.md lean.

**Files touched:**
| File | Action |
|------|--------|
| `.claude/skills/bash-scripts/references/conventions.md` | new |

**Verification:**
- File exists at `references/conventions.md` relative to the skill directory
- All 11 sections from the Content Allocation in design.md are present (Header/Strict Mode, Error Handling, Argument Parsing, Subcommand Dispatcher, Logging, Quoting/Variables, Dependency Checking, Usage/Help, Temp Files, Code Organization, Portability)
- Conventions are consistent with existing project scripts (e.g., `#!/usr/bin/env bash`, `set -euo pipefail`)
- Portability section clearly marks bash 4+ features and notes the macOS 3.2 limitation
- File is 150-250 lines

**Context cost:** S (single file, ~150-250 lines)

**Dependencies:** Slice 1 (SKILL.md must exist first so the reference link target is valid; the "when to read" instruction in SKILL.md references this file)

---

### Slice 3: references/gotchas.md — Common pitfalls catalog

**Goal:** Produce the gotchas reference file listing common bash pitfalls with explanations and correct alternatives. This is a lookup table loaded when Claude needs to validate or review a script.

**Files touched:**
| File | Action |
|------|--------|
| `.claude/skills/bash-scripts/references/gotchas.md` | new |

**Verification:**
- File exists at `references/gotchas.md` relative to the skill directory
- All 6 gotcha categories from the design are present (Unquoted Variables, Missing `--`, cd Without Error Check, Word Splitting, Process Substitution Portability, Array Gotchas)
- Each gotcha includes: the problem, a bad example, the fix, and the relevant ShellCheck code (if applicable)
- File is 50-100 lines

**Context cost:** S (single file, ~50-100 lines)

**Dependencies:** Slice 1 (SKILL.md must exist first; the "when to read" instruction references this file)

---

### Slice 4: Skill-creator invocation and validation

**Goal:** Invoke the skill-creator skill to validate and refine the SKILL.md produced in Slice 1. This satisfies AC2 ("Built using the Anthropic skill builder skill") and the user memory directive requiring skill-creator involvement. The skill-creator may suggest improvements to the description (for triggering accuracy), body structure, or content split.

**Files touched:**
| File | Action |
|------|--------|
| `.claude/skills/bash-scripts/SKILL.md` | modify |
| `.claude/skills/bash-scripts/references/conventions.md` | modify (if skill-creator recommends changes) |
| `.claude/skills/bash-scripts/references/gotchas.md` | modify (if skill-creator recommends changes) |

**Verification:**
- Skill-creator was invoked (conversational evidence in session)
- Any description optimization feedback was incorporated
- SKILL.md still under 500 lines after modifications
- Frontmatter still valid
- If eval loop was run: test cases exist and pass at acceptable rate
- If eval loop was skipped: user explicitly opted out

**Context cost:** M (interactive session with skill-creator; may spawn subagents for eval)

**Dependencies:** Slices 1, 2, 3 (all files must exist before skill-creator can review the complete skill)

---

## Contracts

### Cross-Slice Interface: SKILL.md references/ pointers

SKILL.md must contain exactly two "when to read" directives that match the reference file paths:

```markdown
## References

Before generating any bash script longer than 10 lines, read `references/conventions.md` for the full convention set.

When reviewing or debugging an existing bash script, read `references/gotchas.md` for common pitfalls to check.
```

The exact paths (`references/conventions.md`, `references/gotchas.md`) are the contract between Slice 1 and Slices 2-3. If either reference file is renamed or restructured, the SKILL.md pointer must be updated in the same commit.

### Cross-Slice Interface: Frontmatter triggering contract

The `description` field in SKILL.md frontmatter must trigger on:
- "write a bash script"
- "create a shell script"
- "bash scripting guidance"
- "new bash script for X"

And must NOT trigger on:
- "run this bash command" (that is just using the Bash tool directly)
- "what does this bash script do" (that is code reading, not writing)
- Generic shell discussions not about script authoring

This contract is validated by Slice 4 (skill-creator description optimization loop).

### Cross-Slice Interface: Convention consistency contract

`references/conventions.md` must be consistent with observable facts from the existing codebase:
- Shebang: `#!/usr/bin/env bash` (not `#!/bin/bash`)
- Strict mode: `set -euo pipefail` (all scripts except pure display-only)
- ShellCheck disable convention: inline comment with SC code + justification (matches `protect-paths` precedent)
- Bash version target: 4+ by default, with explicit annotation when using 4+ features and a macOS 3.2 compatibility note

---

## Unverified Assumptions

1. **"Project-level" is the final installation location.** The design flags this as an open question (Decision 1) pending human input. The slices assume `.claude/skills/bash-scripts/` (project-level). If the user decides user-level (`~/.claude/skills/bash-scripts/`), all file paths in Slices 1-4 change. This assumption is explicitly unresolved in the design.

2. **Skill-creator will accept a pre-written SKILL.md for review.** The design assumes the skill-creator can be invoked on an already-written file to validate and refine it (rather than requiring it to author from scratch). The skill-creator documentation describes a "capture intent" phase that implies fresh authoring, but also supports "modify and improve existing skills" per its description. The exact interaction mode (fresh vs. review) is unverified.

3. **Slash command `/bash-scripts` does not conflict with existing skills.** No existing project skill uses this command name, but no systematic check was performed against user-level skills or system-level commands that might shadow it.

4. **The eval loop can meaningfully validate a guidance-only skill.** The design's Risk Register flags this (Risk 2): a skill that produces guidance rather than deterministic output is hard to eval quantitatively. The assumption is that structural assertions (shebang present, set -euo present, shellcheck-clean) are sufficient, but this is untested.

5. **Two reference files are the right granularity.** The design recommends Option B (SKILL.md + 2 references) over Option C (many small files). The assumption is that conventions.md and gotchas.md provide adequate progressive disclosure without over-fragmenting. If the content grows beyond estimates, a third file (e.g., `references/portability.md`) might be needed.

6. **`allowed-tools: Read, Write, Bash` is sufficient.** The design assumes the bash-scripts skill only needs to read references, write scripts, and execute them. If the skill needs to run ShellCheck validation or install dependencies, additional tool access (or documentation noting the user should add ShellCheck) may be required.
